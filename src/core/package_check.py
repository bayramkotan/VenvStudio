"""VenvStudio - does this package actually exist?

B55 (Bayram, 2026-09-04): `pdm add klllklklkl` ran, failed, and left the reader
with a raw resolver error. Whether a package exists is knowable BEFORE running
anything, and a typo deserves "did you mean" rather than a stack of output from
a tool that has already given up.

It lives here rather than in projects_page.py, where it started, because
Bayram's next words were "tamamda diger env tipleri icin yapmamissin" -- the
Manual Install tab and the environments side install packages too, and had no
check at all. Two places doing the same job differently is the failure this
codebase repeats most; one module, two callers.

WHAT IT IS NOT: a resolver. It answers "is there a package by this name", not
"can it be installed here". Version ranges, Python compatibility and platform
wheels are the tool's business, and it is better at them.
"""
import difflib
import urllib.error
import urllib.parse
import urllib.request

from src.utils.logger import get_logger

_log = get_logger("venvstudio.pkgcheck")

# Answers are kept for the session. Typing three package names into Manual
# Install should not mean three round trips every time the field is submitted,
# and a package does not stop existing while the window is open.
_SEEN: dict = {}


def strip_specifier(name: str) -> str:
    """The bare name out of a requirement string.

    `requests==2.31.0`, `numpy>=1.26`, `rich[jupyter]`, `django;python_version<'3.13'`
    all name a package that PyPI knows by its first token.
    """
    _n = (name or "").strip()
    for _sep in ("==", ">=", "<=", "~=", "!=", ">", "<", "[", ";", "@"):
        if _sep in _n:
            _n = _n.split(_sep, 1)[0].strip()
    return _n


def catalog_names() -> list:
    """Every package name VenvStudio's own catalog knows.

    Used only for suggestions: similarity needs a list to compare against, and
    PyPI has no cheap endpoint that provides one.
    """
    try:
        from src.utils.constants import PACKAGE_CATALOG
    except Exception:
        return []
    out = []
    try:
        for _cat in (PACKAGE_CATALOG or {}).values():
            # B190: `.get("packages", [])`, not `_cat`.
            #
            # A category is {"icon": ..., "packages": [...]}, so iterating it
            # yields its KEYS. This function returned ['icon', 'packages']
            # and nothing else, for every catalog, since the day the icon key
            # was added. The isinstance guard below hid it: the keys are
            # strings, so they fell through the dict branch and were appended
            # as if they were package names.
            #
            # MEASURED: suggest("nunpy") -> [], suggest("pandsa") -> []. The
            # did-you-mean this was written for in B55 has never once
            # suggested anything. With B189 the catalog is 518 names.
            for _pkg in (_cat.get("packages", [])
                         if isinstance(_cat, dict) else _cat):
                _n = _pkg.get("name") if isinstance(_pkg, dict) else _pkg
                if _n:
                    out.append(str(_n))
    except Exception:
        return []
    return sorted(set(out))


def suggest(name: str, limit: int = 5) -> list:
    """Catalog names that look like a typo of `name`."""
    _names = catalog_names()
    if not _names:
        return []
    return difflib.get_close_matches(name.lower(), _names, n=limit, cutoff=0.6)


def verify(name: str, timeout: float = 4.0):
    """Does this package exist? Returns (state, suggestions).

        (True,  [])          it exists
        (False, [names])     it does not; these look close
        (None,  [names])     could not check -- offline, blocked, slow

    The third state is not a failure to be treated as absence. On a network
    that blocks PyPI, refusing to install would be worse than the raw error
    this replaces, so callers install anyway and say they could not check.
    Unknown is not the same as no.
    """
    _n = strip_specifier(name)
    if not _n:
        return False, []

    _key = _n.lower()
    if _key in _SEEN:
        return _SEEN[_key]

    try:
        _req = urllib.request.Request(
            f"https://pypi.org/pypi/{urllib.parse.quote(_n)}/json",
            headers={"User-Agent": "VenvStudio"})
        with urllib.request.urlopen(_req, timeout=timeout) as _r:
            if _r.status == 200:
                _SEEN[_key] = (True, [])
                return _SEEN[_key]
    except urllib.error.HTTPError as e:
        if e.code == 404:
            _SEEN[_key] = (False, suggest(_n))
            return _SEEN[_key]
        _log.info(f"[PkgCheck] {_n!r}: HTTP {e.code}")
        # Not cached: a 500 today may be a 200 in a minute.
        return None, suggest(_n)
    except Exception as e:
        _log.info(f"[PkgCheck] could not reach PyPI for {_n!r}: {e!r}")
        return None, suggest(_n)

    return None, suggest(_n)


def verify_many(names, ask_fn, tool: str = ""):
    """Check a list of names, letting the caller resolve each problem.

    `ask_fn(name, suggestions)` is called only for names PyPI says do not
    exist. It returns the name to use instead, or None to abort the whole
    operation. The dialogs belong to the caller -- this module has no Qt.

    `tool`: pixi and conda resolve against conda-forge, where the package set
    differs and PyPI is simply the wrong authority. Those are returned
    untouched rather than being told they do not exist.

    Returns the resolved list, or None if the caller aborted.
    """
    if tool in ("pixi", "conda", "micromamba"):
        return list(names)

    out = []
    for _n in names:
        _state, _sug = verify(_n)
        if _state is True:
            out.append(_n)
        elif _state is None:
            _log.info(f"[PkgCheck] {_n!r}: unverified, keeping it")
            out.append(_n)
        else:
            _choice = ask_fn(_n, _sug)
            if _choice is None:
                return None
            out.append(_choice)
    return out


# ── B195: which Pythons a package actually has a file for ──────────────────

# Wheel filename: {name}-{ver}(-{build})?-{pytag}-{abitag}-{plattag}.whl
# Any of the three tags may be compound, joined with dots: a single file can
# declare cp310.cp311 or py2.py3.
_PLAT_MARKERS = {
    "win":   ("win32", "win_amd64", "win_arm64", "win-"),
    "linux": ("manylinux", "musllinux", "linux_"),
    "macos": ("macosx",),
}


def _plat_ok(plat_tag: str, platform_tag: str) -> bool:
    if "any" in plat_tag.split("."):
        return True
    _markers = _PLAT_MARKERS.get(platform_tag, ())
    return any(_m in plat_tag for _m in _markers)


def _py_ok(py_tag: str, abi_tag: str, major: int, minor: int) -> bool:
    """Does this file's python/abi pair cover Python major.minor?

    B195. The old check asked only whether the literal string `cp314`
    appeared in the filename, which is wrong in the two commonest cases:

      PyQt6-6.11.0-cp310-abi3-manylinux_x86_64.whl
      astropy-8.0.1-cp311-abi3-...

    abi3 is the stable ABI: ONE file serves that version and every later
    one. Reading those as "cp310 only" is how VenvStudio came to refuse to
    install PyQt6 on Python 3.14, with a dialog, measured against live PyPI.

      wandb-0.30.0-py3-none-macosx_11_0_arm64.whl

    py3 with a platform is still pure Python -- the old check only
    recognised purity from the literal "-none-any.whl", so a
    platform-specific pure wheel was read as incompatible too.
    """
    _pys = py_tag.split(".")
    _abis = abi_tag.split(".")

    # Pure Python: py3, or py3X with X <= minor.
    for _p in _pys:
        if _p in ("py3", f"py{major}"):
            return True
        if _p.startswith(f"py{major}") and len(_p) > 2:
            _d = _p[2 + len(str(major)):]
            if _d.isdigit() and int(_d) <= minor:
                return True

    # Stable ABI: cp3Y-abi3 covers 3.Y and everything after it.
    if "abi3" in _abis:
        for _p in _pys:
            if _p.startswith(f"cp{major}"):
                _d = _p[2 + len(str(major)):]
                if _d.isdigit() and int(_d) <= minor:
                    return True

    # Version-specific build.
    return f"cp{major}{minor}" in _pys or f"cp{major}.{minor}" in _pys


def _req_python_ok(spec: str, major: int, minor: int) -> bool:
    """A coarse but honest reading of a Requires-Python string.

    Only the bounds that matter for an X.Y question are applied; anything
    unparseable is treated as "no opinion" rather than as a refusal,
    because guessing a refusal here would block a working install.
    """
    if not spec:
        return True
    _v = (major, minor)
    for _part in str(spec).split(","):
        _part = _part.strip()
        if not _part:
            continue
        for _op in (">=", "<=", "!=", "==", "~=", ">", "<"):
            if _part.startswith(_op):
                _num = _part[len(_op):].strip().rstrip("*").rstrip(".")
                _bits = [b for b in _num.split(".") if b.isdigit()]
                if not _bits:
                    break
                _t = (int(_bits[0]), int(_bits[1]) if len(_bits) > 1 else 0)
                if _op == ">=" and _v < _t:
                    return False
                if _op == ">" and _v <= _t:
                    return False
                if _op == "<=" and _v > _t:
                    return False
                if _op == "<" and _v >= _t:
                    return False
                if _op == "==" and _v != _t:
                    return False
                if _op == "!=" and _v == _t:
                    return False
                break
    return True


def _files_support(files, major: int, minor: int, platform_tag: str,
                   wheels_only: bool = False) -> bool:
    """Is there a file in this release that installs on this Python?

    Two different questions share this code, and keeping them apart
    matters:

      wheels_only=False  anything pip could install, sdist included.
                         This is what "No matching distribution" means --
                         pip found NOTHING, not even source.
      wheels_only=True   a prebuilt wheel exists. An sdist means a
                         compiler runs, which is a warning worth giving
                         and not the same as being unable to install.

    MEASURED while building this: vpython, fiona, pyaudio and kivy all
    cap their wheels at cp312 or cp313 and still ship an sdist, so on
    Python 3.14 the first question answers yes and the second no. Folding
    them into one verdict loses exactly the distinction the reader needs.
    """
    for _f in files:
        if not _req_python_ok(_f.get("requires_python") or "", major, minor):
            continue
        if _f.get("packagetype") == "sdist":
            if wheels_only:
                continue
            return True
        _fn = _f.get("filename") or ""
        if not _fn.endswith(".whl"):
            continue
        _parts = _fn[:-4].split("-")
        if len(_parts) < 3:
            continue
        _py, _abi, _plat = _parts[-3], _parts[-2], _parts[-1]
        if _plat_ok(_plat, platform_tag) and _py_ok(_py, _abi, major, minor):
            return True
    return False


def wheel_availability(pkg_name: str, py_major: int, py_minor: int,
                       platform_tag: str, timeout: float = 6.0) -> dict:
    """Can this package install on this Python, and if not, where can it?

    B195. Replaces the per-caller copies: package_ops.py had its own
    version used as the fallback tier of the pre-flight check, and
    pip_manager.py had none at all and blamed the package name instead.

    The supported versions are produced by running the SAME per-file test
    over 3.8 to 3.15, so the list and the verdict can never disagree --
    the old code derived them separately and they did.

    Returns, and never raises:
      {"checked": bool,              did the query succeed
       "exists": bool,               PyPI knows this name
       "compatible": bool | None,    anything installs, sdist included
       "wheel_compatible": bool,     a PREBUILT wheel exists for it
       "available_pyvers": [str],    versions something installs on
       "wheel_pyvers": [str],        versions with a prebuilt wheel
       "has_wheel": bool, "has_sdist": bool,
       "latest": str, "requires_python": str, "error": str | None}
    """
    _out = {"checked": False, "exists": False, "compatible": None,
            "wheel_compatible": None, "available_pyvers": [],
            "wheel_pyvers": [], "has_wheel": False, "has_sdist": False,
            "latest": "", "requires_python": "", "error": None}
    _n = strip_specifier(pkg_name)
    if not _n:
        return _out
    try:
        import json as _json
        _req = urllib.request.Request(
            f"https://pypi.org/pypi/{urllib.parse.quote(_n)}/json",
            headers={"User-Agent": "VenvStudio"})
        with urllib.request.urlopen(_req, timeout=timeout) as _r:
            _data = _json.load(_r)
    except urllib.error.HTTPError as _e:
        _out["checked"] = True
        if _e.code == 404:
            return _out                      # exists stays False
        _out["checked"] = False
        _out["error"] = f"HTTP {_e.code}"
        return _out
    except Exception as _e:
        _out["error"] = repr(_e)[:120]
        return _out

    _out["checked"] = True
    _out["exists"] = True
    _latest = str(_data["info"].get("version") or "")
    _out["latest"] = _latest
    _out["requires_python"] = str(_data["info"].get("requires_python") or "")
    _files = _data.get("releases", {}).get(_latest, []) or []
    if not _files:
        return _out

    _out["has_wheel"] = any(_f.get("packagetype") == "bdist_wheel"
                            for _f in _files)
    _out["has_sdist"] = any(_f.get("packagetype") == "sdist" for _f in _files)
    _out["compatible"] = _files_support(_files, py_major, py_minor,
                                        platform_tag)
    _out["wheel_compatible"] = _files_support(_files, py_major, py_minor,
                                              platform_tag, wheels_only=True)
    _out["available_pyvers"] = [
        f"{py_major}.{_m}" for _m in range(8, 16)
        if _files_support(_files, py_major, _m, platform_tag)]
    _out["wheel_pyvers"] = [
        f"{py_major}.{_m}" for _m in range(8, 16)
        if _files_support(_files, py_major, _m, platform_tag,
                          wheels_only=True)]
    return _out


def explain_no_distribution(packages, py_major: int, py_minor: int,
                            platform_tag: str, pip_output: str = "") -> str:
    """Why pip said "No matching distribution", in words that are true.

    B194/F206. pip says the same sentence whether the name is wrong or the
    name is right and no file fits this Python, and VenvStudio read it as
    the first one every time:

        "One or more packages could not be found on PyPI.
         Please check the package names and try again."

    Bayram, 2026-07-24: tensorflow on Python 3.14.5. The name was correct;
    there was no 3.14 wheel. He went looking for a typo. Telling someone to
    check something that is already right is worse than saying nothing,
    because it sends them away from the real cause.

    So each name is asked about separately, and the answer says which of
    the two it is -- with a "did you mean" for a genuine typo, which only
    started working in B190, and with the Python versions that DO have a
    file for the other case.
    """
    _lines = []
    _unknown = []
    for _spec in (packages or []):
        _n = strip_specifier(_spec)
        if not _n:
            continue
        _a = wheel_availability(_n, py_major, py_minor, platform_tag)
        if not _a["checked"]:
            _unknown.append(_n)
            continue
        if not _a["exists"]:
            _sug = suggest(_n)
            _line = f"  {_n} -- no package by this name on PyPI."
            if _sug:
                _line += "  Did you mean: " + ", ".join(_sug) + "?"
            _lines.append(_line)
            continue
        if _a["compatible"]:
            # The name is fine and this Python is fine, so the failure is
            # something else -- a version pin, a conflict, a network error.
            # Saying nothing specific is correct here.
            continue
        _vers = _a["available_pyvers"]
        _line = (f"  {_n} {_a['latest']} -- exists, but has no file for "
                 f"Python {py_major}.{py_minor} on {platform_tag}.")
        if _vers:
            _line += ("\n      Available for Python "
                      + ", ".join(_vers) + ".")
        elif not _a["has_wheel"]:
            _line += "\n      It ships source only, with no prebuilt wheel."
        _lines.append(_line)

    if not _lines and not _unknown:
        return ""

    _out = ["pip could not find a matching distribution.", ""]
    _out += _lines
    if _unknown:
        _out += ["", "  Could not check on PyPI (offline?): "
                 + ", ".join(_unknown)]
    if any("no file for Python" in _l for _l in _lines):
        _out += ["",
                 "A package with no file for this Python cannot be installed "
                 "here. Creating an environment on one of the Python versions "
                 "listed above is the way round it."]
    if pip_output:
        _out += ["", "--- pip said ---", pip_output.strip()[-1200:]]
    return "\n".join(_out)


# ── B153: what will actually be BUILT, not just what was asked for ──────────

def will_build_from_source(python_exe, packages, timeout: float = 90.0):
    """Which packages pip would have to compile, and why that matters.

    Returns (state, findings):

        (True,  [])                 everything resolves to a ready-made wheel
        (False, [{...}, ...])       these would be built from source
        (None,  [])                 could not check -- offline, pip too old,
                                    timed out; the caller installs anyway

    Bayram, 2026-09-25: `pip install pandas_ta yfinance` failed on Python
    3.14 and the Conflict Manager had said nothing. It could not have: it
    checks the names it was GIVEN against a table written by hand, and the
    package that broke was `numba`, pulled in by pandas_ta and pinned to a
    version with no 3.14 wheel. The same day, `pyfolio` failed because it has
    no wheel at all -- sdist only since 2019.

    Both are the same question, and pip can answer it without installing
    anything: `--dry-run --report` resolves the whole tree and says, for every
    package, which file it would fetch. A name ending in .tar.gz or .zip is a
    source distribution, which means a compiler runs and may fail.

    This is not a guarantee of failure -- plenty of sdists build fine. It is
    a warning with the reason attached, which is what was missing.

    ⚠️ It costs a network round trip and a few seconds. Callers run it before
    an install, not on every keystroke.
    """
    import json as _json
    import subprocess as _sp
    from src.utils.platform_utils import subprocess_args as _sa

    _pkgs = [p for p in (packages or []) if str(p).strip()]
    if not _pkgs or not python_exe:
        return None, []

    try:
        _r = _sp.run(
            [str(python_exe), "-m", "pip", "install", "--dry-run",
             "--quiet", "--report", "-", *_pkgs],
            **_sa(capture_output=True, text=True, timeout=timeout))
    except Exception as _e:
        _log.info(f"[PkgCheck] dry-run could not run: {_e!r}")
        return None, []

    if _r.returncode != 0:
        # Resolution itself failed. MEASURED: this is what happens with
        # pyfolio -- pip cannot even read its metadata without running its
        # setup.py, which dies on Python 3.12 and later. Returning "could not
        # check" here would throw away the answer: the resolve failed, so the
        # install will fail, for this reason, and the user can be told now
        # instead of after a download.
        _err = (_r.stderr or _r.stdout or "").strip()
        _log.info(f"[PkgCheck] dry-run refused: rc={_r.returncode}")
        return False, [{
            "name": ", ".join(strip_specifier(p) for p in _pkgs),
            "version": "",
            "direct": True,
            "resolve_failed": True,
            # The END of pip's output: the reason is always last, and the
            # first lines are download progress (B154, same lesson).
            "error": _err[-1500:],
        }]

    try:
        _report = _json.loads(_r.stdout or "{}")
    except Exception as _e:
        _log.info(f"[PkgCheck] dry-run report unreadable: {_e!r}")
        return None, []

    _asked = {strip_specifier(p).lower().replace("_", "-") for p in _pkgs}
    _out = []
    for _item in _report.get("install", []):
        _url = ((_item.get("download_info") or {}).get("url") or "")
        if not _url.endswith((".tar.gz", ".zip")):
            continue
        _meta = _item.get("metadata") or {}
        _name = str(_meta.get("name") or "?")
        _key = _name.lower().replace("_", "-")
        _out.append({
            "name": _name,
            "version": str(_meta.get("version") or "?"),
            # Whether the user named it themselves changes the advice: a
            # direct one can be swapped, an indirect one usually cannot.
            "direct": _key in _asked,
            "url": _url,
        })

    if _out:
        _log.info("[PkgCheck] would build from source: "
                  + ", ".join(f"{d['name']} {d['version']}" for d in _out))
    return (not _out), _out


def source_build_warning(findings, python_version: str = "") -> str:
    """The findings as something worth reading. Empty when there is nothing.

    Kept here rather than in the dialog because both the Manual Install tab
    and the launcher cards need the same words, and this codebase's most
    repeated fault is two places saying the same thing differently.
    """
    if not findings:
        return ""

    # The resolver gave up before choosing anything: pip's own words are the
    # whole message, and nothing here improves on them.
    _failed = [d for d in findings if d.get("resolve_failed")]
    if _failed:
        _d = _failed[0]
        return ("pip could not work out how to install "
                f"{_d['name']} and stopped before downloading anything.\n\n"
                "It usually means a package has no ready-made build for this "
                "Python and could not be compiled either.\n\n"
                "--- pip said ---\n" + (_d.get("error") or ""))

    _direct = [d for d in findings if d.get("direct")]
    _indirect = [d for d in findings if not d.get("direct")]

    _py = f" for Python {python_version}" if python_version else ""
    _lines = [f"No ready-made package exists{_py} for:", ""]
    for _d in _direct:
        _lines.append(f"    {_d['name']} {_d['version']}")
    for _d in _indirect:
        _lines.append(f"    {_d['name']} {_d['version']}   "
                      f"(not asked for -- something else requires it)")
    _lines += [
        "",
        "pip will try to compile these. That needs a working compiler and "
        "often fails on a Python newer than the package.",
        "",
    ]
    if _indirect:
        _lines.append(
            "An indirect one cannot be swapped out: the package that "
            "requires it has pinned that version.")
    _lines.append("Installing into an environment with an older Python "
                  "usually works.")
    return "\n".join(_lines)
