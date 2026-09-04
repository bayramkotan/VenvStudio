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
