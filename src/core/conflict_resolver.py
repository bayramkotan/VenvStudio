"""VenvStudio - will this install work, asked before it runs.

F151. Bayram marked this the highest open item: Orange3, MLflow, TensorFlow
and half the preset failures are the same shape -- pip runs, pip fails, and
the reader is handed a resolver's parting words.

Three things existed before this module and none of them talked to each
other:

  CONFLICT_RULES        218 hand-written entries in constants.py, looked up
                        by package_ops.py and again by window_menu.py, each
                        with its own copy of the alias/normalise/compare
                        logic. Two copies of one job is the fault this
                        codebase repeats most.

  pip install --dry-run package_ops.py ran it and read only the exit code,
                        so it could say "these cannot be installed together"
                        and nothing else.

  will_build_from_source  package_check.py, written for B153 with
                        --dry-run --report, which names every package that
                        would be COMPILED and whether the user asked for it.
                        Never called from anywhere.

The one that answers the question that actually bit -- `pip install
pandas_ta` failing on numba, a package the user never typed -- was the one
nothing called.

WHAT THIS IS: one Qt-free entry point, check_compatibility(), returning a
ConflictReport the caller can render however it likes. No dialogs here; the
GUI owns those, and this module is testable precisely because it has none.

WHAT THIS IS NOT: a resolver. pip is the resolver. This asks pip, plus a
table of things pip will not tell you (that PyQt5 has no 3.13 wheel, that
Orange3 cannot live in a pipx environment).
"""


# ── Name handling ──────────────────────────────────────────────────────────

def normalise(name: str) -> str:
    """A package name in the form CONFLICT_RULES keys are written in.

    PEP 503 says `_` and `-` are the same character for a project name, and
    the table is lowercase. Both call sites did this inline and one of them
    did it slightly differently, which is why it lives here now.
    """
    try:
        from src.core.package_check import strip_specifier as _strip
        _n = _strip(name)
    except Exception:
        _n = str(name or "").strip()
        for _sep in ("==", ">=", "<=", "~=", "!=", ">", "<", "[", ";", "@"):
            if _sep in _n:
                _n = _n.split(_sep, 1)[0].strip()
    return _n.lower().replace("_", "-")


def rule_for(name: str):
    """The CONFLICT_RULES entry for this package, or None.

    Tries the name as written, then normalised, through the alias table
    both times -- `PyQt5`, `pyqt5`, `tensorflow_gpu` and `tf` all have to
    land on the same rule, and the alias table is keyed inconsistently
    because it grew by hand.
    """
    try:
        from src.utils.constants import CONFLICT_RULES, CONFLICT_RULES_ALIASES
    except Exception:
        return None
    _raw = str(name or "").strip()
    _key = normalise(_raw)
    for _probe in (_raw, _key):
        _alias = CONFLICT_RULES_ALIASES.get(_probe)
        if _alias and _alias in CONFLICT_RULES:
            return CONFLICT_RULES[_alias]
    return CONFLICT_RULES.get(_key)


# ── Python version comparison ──────────────────────────────────────────────

def _py_tuple(v):
    """"3.13.2" -> (3, 13). Returns None for anything unreadable.

    Only major.minor matters: every rule in the table is written to a minor
    version, because that is the granularity wheels are built for.

    Deliberately not packaging.version: this runs against whatever Python
    the user picked, and a comparison of two X.Y pairs does not need a
    dependency. The version-sort lesson from v1.6.97 was about sorting
    RELEASE numbers as text -- 1.6.100 < 1.6.97 -- which is a different
    problem; these are two integers.
    """
    if not v:
        return None
    _parts = str(v).strip().split(".")
    try:
        return (int(_parts[0]), int(_parts[1]) if len(_parts) > 1 else 0)
    except (ValueError, IndexError):
        return None


# ── The report ─────────────────────────────────────────────────────────────

class ConflictReport:
    """What was found, in the order a reader needs it.

    `blocks`    severity "error" -- a rule says this will not work here
    `warnings`  severity "warning" -- it may not
    `builds`    packages pip would compile rather than download
    `resolve_error`  pip gave up before choosing anything; its own words
    `dynamic`   True ran, False skipped by env type, None could not run

    A finding is a plain dict so the dialog can add to it without this
    module growing a Qt-shaped API.
    """

    def __init__(self):
        self.blocks = []
        self.warnings = []
        self.builds = []
        self.resolve_error = ""
        self.dynamic = None

    @property
    def ok(self) -> bool:
        """Nothing worth stopping for. Warnings alone do not stop anything."""
        return not self.blocks and not self.resolve_error

    @property
    def empty(self) -> bool:
        return not (self.blocks or self.warnings or self.builds
                    or self.resolve_error)

    def summary(self) -> str:
        """The findings as prose. Empty string when there is nothing to say.

        Built here rather than in the dialog because the launcher cards, the
        Manual Install tab and the preset installer all need the same words,
        and B120 was the lesson about what happens when they each write
        their own.
        """
        _out = []
        for _f in self.blocks + self.warnings:
            # The REASON THAT FIRED leads, and the table's note follows as
            # context.
            #
            # MEASURED while testing: numpy at Python 3.13 in a pipx
            # environment fires on blocked_envs, but its note reads
            # "Requires Python 3.12+". Printing the note alone told the
            # reader their Python was wrong when it was fine -- a wrong
            # explanation is worse than none, because it sends them to fix
            # the wrong thing.
            _mark = "⛔" if _f.get("severity") == "error" else "⚠️"
            _line = f"{_mark} {_f['name']}: " + "; ".join(_f["reasons"])
            if _f.get("note"):
                _line += f"\n     {_f['note']}"
            if _f.get("alternative"):
                _line += f"\n     Alternative: {_f['alternative']}"
            _out.append(_line)
        if self.resolve_error:
            _out.append("⛔ pip could not work out how to install these and "
                        "stopped before downloading anything.\n\n"
                        "--- pip said ---\n" + self.resolve_error)
        elif self.builds:
            try:
                from src.core.package_check import source_build_warning
                _out.append(source_build_warning(self.builds))
            except Exception:
                _names = ", ".join(
                    f"{_b.get('name')} {_b.get('version', '')}".strip()
                    for _b in self.builds)
                _out.append("No ready-made package exists for: " + _names)
        return "\n\n".join(_out)


# ── Layer 1: the table ─────────────────────────────────────────────────────

def check_static(packages, python_version: str = "",
                 env_type: str = "") -> ConflictReport:
    """CONFLICT_RULES, applied once, in one place.

    Costs nothing and needs no network, so it runs first and can stop a
    hopeless install before pip is started at all.

    MEASURED, and the reason the dynamic layer below exists: this can only
    judge names it was GIVEN. `pip install pandas_ta` broke on numba, which
    the user never typed and the table has no entry for.
    """
    _rep = ConflictReport()
    _py = _py_tuple(python_version)
    _env = (env_type or "").strip().lower()

    for _spec in (packages or []):
        if not str(_spec).strip():
            continue
        _rule = rule_for(_spec)
        if not _rule:
            continue
        _name = normalise(_spec)
        _note = _rule.get("note") or ""
        _hits = []

        _max = _py_tuple(_rule.get("max_python"))
        if _py and _max and _py > _max:
            _hits.append(
                f"needs Python {_rule['max_python']} or older; "
                f"this environment is {python_version}")

        _min = _py_tuple(_rule.get("min_python"))
        if _py and _min and _py < _min:
            _hits.append(
                f"needs Python {_rule['min_python']} or newer; "
                f"this environment is {python_version}")

        if _env and _env in [str(_e).lower()
                             for _e in (_rule.get("blocked_envs") or [])]:
            _hits.append(f"cannot be installed into a {_env} environment")

        if not _hits:
            continue

        _finding = {
            "name": _name,
            # Kept apart on purpose: `reasons` is what fired here and now,
            # `note` is what the table says about the package in general.
            # They are often different things -- see summary().
            "note": _note,
            "reasons": _hits,
            "severity": _rule.get("severity") or "warning",
            "category": _rule.get("category") or "",
            "alternative": _rule.get("alternative") or "",
        }
        if _finding["severity"] == "error":
            _rep.blocks.append(_finding)
        else:
            _rep.warnings.append(_finding)

    return _rep


# ── Layer 2: pip's own resolver ────────────────────────────────────────────

# Only where pip is genuinely the installer. uv, poetry, pdm, pixi, conda and
# pipx each resolve their own way, and running pip's resolver against their
# environment answers a question nobody asked. hatch is here because it
# delegates to pip. This list was inline in package_ops.py; it is named here
# so the call sites cannot drift apart.
PIP_DRIVEN = ("venv", "uv", "hatch")


def dynamic_applies(env_type: str) -> bool:
    return (env_type or "").strip().lower() in PIP_DRIVEN


def check_dynamic(python_exe, packages, env_type: str = "",
                  timeout: float = 90.0) -> ConflictReport:
    """Ask pip what it would actually do, without letting it do it.

    Wraps package_check.will_build_from_source, which was written for B153
    and never called. It runs `pip install --dry-run --report`, so unlike the
    bare --dry-run that package_ops.py used it can name the packages that
    would be COMPILED and say whether the user asked for them.
    """
    _rep = ConflictReport()
    if not dynamic_applies(env_type):
        _rep.dynamic = False
        return _rep
    try:
        from src.core.package_check import will_build_from_source
    except Exception:
        _rep.dynamic = None
        return _rep

    _state, _findings = will_build_from_source(python_exe, packages,
                                               timeout=timeout)
    if _state is None:
        _rep.dynamic = None
        return _rep

    _rep.dynamic = True
    _failed = [_f for _f in _findings if _f.get("resolve_failed")]
    if _failed:
        _rep.resolve_error = _failed[0].get("error") or ""
    else:
        _rep.builds = list(_findings)
    return _rep


# ── Both layers, one call ──────────────────────────────────────────────────

def check_compatibility(packages, python_version: str = "", env_type: str = "",
                        python_exe="", dynamic: bool = True,
                        timeout: float = 90.0) -> ConflictReport:
    """The whole pre-flight check. This is what callers should use.

    Static first because it is free. If it finds something that will fail
    outright, pip is not started: there is no point spending a network round
    trip to confirm what the table already knows.
    """
    _rep = check_static(packages, python_version=python_version,
                        env_type=env_type)
    if _rep.blocks or not dynamic or not python_exe:
        _rep.dynamic = False if _rep.blocks else _rep.dynamic
        return _rep

    _dyn = check_dynamic(python_exe, packages, env_type=env_type,
                         timeout=timeout)
    _rep.dynamic = _dyn.dynamic
    _rep.builds = _dyn.builds
    _rep.resolve_error = _dyn.resolve_error
    return _rep
