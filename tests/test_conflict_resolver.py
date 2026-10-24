"""Tests for src/core/conflict_resolver.py (F151).

B34 calls the missing test suite the project's largest gap, and names the
three areas worth covering first; this module is squarely in the first one.
It has no Qt, takes plain data and returns plain data, so every branch here
is reachable without a display or an environment.

The dynamic layer shells out to pip. Those tests replace
will_build_from_source with a stub rather than running pip: what is being
tested is how conflict_resolver treats each of its three answers, not
whether pip works.
"""
import pytest

from src.core import conflict_resolver as cr


# ── normalise / rule_for ───────────────────────────────────────────────────

@pytest.mark.parametrize("given,want", [
    ("PyQt5", "pyqt5"),
    ("Scikit_Learn>=1.0", "scikit-learn"),
    ("rich[jupyter]", "rich"),
    ("numpy==2.1.0", "numpy"),
    ("django;python_version<'3.13'", "django"),
    ("  Pillow  ", "pillow"),
    ("", ""),
])
def test_normalise(given, want):
    assert cr.normalise(given) == want


@pytest.mark.parametrize("given", [
    "PyQt5", "pyqt5", "tf", "tensorflow_gpu", "tensorflow-gpu",
    "TensorFlow", "zipline", "rdkit_pypi", "talib",
])
def test_rule_for_finds_known_names(given):
    """Every spelling the alias table knows has to land on a rule.

    Both former call sites wrote this lookup themselves, and they did not
    agree: one tried the raw name against the aliases, the other the
    lowercased one. Names like PyQt5 are keyed both ways.
    """
    assert cr.rule_for(given) is not None


def test_rule_for_unknown_is_none():
    assert cr.rule_for("a-package-nobody-has-written") is None


def test_rule_for_survives_a_version_specifier():
    assert cr.rule_for("tensorflow==2.15.0") is not None


# ── _py_tuple ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("given,want", [
    ("3.13", (3, 13)), ("3.13.2", (3, 13)), ("3", (3, 0)),
    ("", None), (None, None), ("abc", None), ("3.x", None),
])
def test_py_tuple(given, want):
    assert cr._py_tuple(given) == want


# ── Layer 1: the table ─────────────────────────────────────────────────────

def test_max_python_blocks():
    """PyQt5 has no 3.13 wheel; the table says so and severity is error."""
    rep = cr.check_static(["PyQt5"], python_version="3.13")
    assert rep.blocks and not rep.ok
    assert rep.blocks[0]["name"] == "pyqt5"
    assert any("3.12" in r for r in rep.blocks[0]["reasons"])


def test_max_python_silent_when_old_enough():
    assert cr.check_static(["PyQt5"], python_version="3.11").empty


def test_min_python_blocks():
    rep = cr.check_static(["tensorflow"], python_version="3.8")
    assert rep.blocks
    assert any("newer" in r for r in rep.blocks[0]["reasons"])


def test_blocked_env_is_caught():
    rep = cr.check_static(["tensorflow"], python_version="3.11",
                          env_type="pipx")
    assert rep.blocks
    assert any("pipx" in r for r in rep.blocks[0]["reasons"])


def test_env_type_is_case_insensitive():
    assert cr.check_static(["tensorflow"], python_version="3.11",
                           env_type="PIPX").blocks


def test_warning_does_not_block():
    """A warning is a warning. 190 of the 218 rules are this kind, and
    treating them as refusals would make the installer unusable."""
    rep = cr.check_static(["numpy"], python_version="3.13", env_type="pipx")
    assert not rep.blocks
    assert rep.ok


def test_unknown_package_says_nothing():
    assert cr.check_static(["a-package-nobody-has-written"],
                           python_version="3.13").empty


def test_no_python_version_skips_version_rules():
    """An unknown Python must not be read as an incompatible one."""
    rep = cr.check_static(["PyQt5"], python_version="")
    assert not rep.blocks


def test_empty_and_blank_inputs():
    assert cr.check_static([], python_version="3.13").empty
    assert cr.check_static(["", "   "], python_version="3.13").empty


def test_several_packages_are_all_reported():
    rep = cr.check_static(["PyQt5", "tensorflow", "numpy"],
                          python_version="3.13", env_type="venv")
    assert len(rep.blocks) == 2


# ── Layer 2: which env types pip speaks for ────────────────────────────────

@pytest.mark.parametrize("env_type,want", [
    ("venv", True), ("uv", True), ("hatch", True), ("VENV", True),
    ("conda", False), ("pipx", False), ("poetry", False),
    ("pdm", False), ("pixi", False), ("", False),
])
def test_dynamic_applies(env_type, want):
    assert cr.dynamic_applies(env_type) is want


def _stub(monkeypatch, result):
    import src.core.package_check as pc
    monkeypatch.setattr(pc, "will_build_from_source",
                        lambda *a, **k: result, raising=True)


def test_dynamic_clean_resolve(monkeypatch):
    _stub(monkeypatch, (True, []))
    rep = cr.check_dynamic("/usr/bin/python3", ["requests"], env_type="venv")
    assert rep.dynamic is True and rep.ok and not rep.builds


def test_dynamic_reports_source_builds(monkeypatch):
    """The numba case: a package the user never typed, compiled on their
    behalf. The old bare --dry-run could not see this at all."""
    _stub(monkeypatch, (False, [
        {"name": "numba", "version": "0.61.2", "direct": False},
    ]))
    rep = cr.check_dynamic("/usr/bin/python3", ["pandas_ta"], env_type="venv")
    assert rep.builds and rep.builds[0]["name"] == "numba"
    assert rep.ok          # a source build is a warning, not a refusal


def test_dynamic_resolve_failure_blocks(monkeypatch):
    """pyfolio: pip cannot read the metadata at all. Its words are the
    message, and the install should stop."""
    _stub(monkeypatch, (False, [
        {"name": "pyfolio", "resolve_failed": True,
         "error": "SafeConfigParser was removed in Python 3.12"},
    ]))
    rep = cr.check_dynamic("/usr/bin/python3", ["pyfolio"], env_type="venv")
    assert not rep.ok
    assert "SafeConfigParser" in rep.resolve_error


def test_dynamic_unknown_is_not_a_refusal(monkeypatch):
    """Offline, or pip too old. Unknown is not the same as no -- the same
    rule package_check.verify already follows."""
    _stub(monkeypatch, (None, []))
    rep = cr.check_dynamic("/usr/bin/python3", ["requests"], env_type="venv")
    assert rep.dynamic is None and rep.ok


def test_dynamic_skipped_for_other_tools(monkeypatch):
    _stub(monkeypatch, (False, [{"name": "x", "resolve_failed": True,
                                 "error": "should never be read"}]))
    rep = cr.check_dynamic("/usr/bin/python3", ["x"], env_type="poetry")
    assert rep.dynamic is False and rep.ok


# ── Both layers together ───────────────────────────────────────────────────

def test_static_block_skips_pip(monkeypatch):
    """No point spending a network round trip to confirm what the table
    already knows."""
    called = []
    import src.core.package_check as pc
    monkeypatch.setattr(pc, "will_build_from_source",
                        lambda *a, **k: called.append(1) or (True, []))
    rep = cr.check_compatibility(["PyQt5"], python_version="3.13",
                                 env_type="venv", python_exe="/usr/bin/python3")
    assert rep.blocks and not called


def test_both_layers_run_when_table_is_quiet(monkeypatch):
    _stub(monkeypatch, (False, [{"name": "numba", "version": "0.61.2",
                                 "direct": False}]))
    rep = cr.check_compatibility(["pandas-ta"], python_version="3.14",
                                 env_type="venv", python_exe="/usr/bin/python3")
    assert rep.dynamic is True and rep.builds


def test_no_python_exe_means_static_only(monkeypatch):
    _stub(monkeypatch, (False, [{"name": "x", "resolve_failed": True,
                                 "error": "should never be read"}]))
    rep = cr.check_compatibility(["requests"], python_version="3.13",
                                 env_type="venv", python_exe="")
    assert not rep.resolve_error


def test_dynamic_can_be_turned_off(monkeypatch):
    _stub(monkeypatch, (False, [{"name": "x", "resolve_failed": True,
                                 "error": "should never be read"}]))
    rep = cr.check_compatibility(["requests"], python_version="3.13",
                                 env_type="venv", python_exe="/usr/bin/python3",
                                 dynamic=False)
    assert not rep.resolve_error


# ── summary() ──────────────────────────────────────────────────────────────

def test_summary_empty_when_nothing_found():
    assert cr.check_static(["requests"], python_version="3.13").summary() == ""


def test_summary_names_the_package_and_the_alternative():
    out = cr.check_static(["PyQt5"], python_version="3.13").summary()
    assert "pyqt5" in out and "PySide6" in out


def test_summary_carries_pips_own_words(monkeypatch):
    _stub(monkeypatch, (False, [
        {"name": "pyfolio", "resolve_failed": True,
         "error": "SafeConfigParser was removed in Python 3.12"},
    ]))
    out = cr.check_dynamic("/usr/bin/python3", ["pyfolio"],
                           env_type="venv").summary()
    assert "SafeConfigParser" in out


def test_summary_survives_a_rule_without_an_alternative():
    """46 of the 218 rules have no `alternative` key. Reading it with []
    would raise, and this is the only place that touches it."""
    rep = cr.check_static(["orange3"], python_version="3.9", env_type="pipx")
    rep.summary()


def test_summary_states_the_reason_that_fired_not_the_table_note():
    """A wrong explanation is worse than none.

    MEASURED: numpy at Python 3.13 in a pipx environment fires on
    blocked_envs, and its CONFLICT_RULES note reads "Requires Python
    3.12+". An earlier summary() printed the note alone, which told the
    reader to fix a Python version that was already fine.
    """
    out = cr.check_static(["numpy"], python_version="3.13",
                          env_type="pipx").summary()
    assert "pipx" in out
    assert not out.startswith("⚠️ numpy: Requires Python")


def test_summary_marks_errors_and_warnings_differently():
    rep = cr.check_static(["PyQt5", "numpy"], python_version="3.13",
                          env_type="pipx")
    out = rep.summary()
    assert "⛔" in out and "⚠️" in out
