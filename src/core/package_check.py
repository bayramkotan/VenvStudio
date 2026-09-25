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
            for _pkg in _cat:
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
