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


# ── B195: wheel tag reading ────────────────────────────────────────────────
#
# These do not touch the network. The tag parser is the part that was wrong,
# and it is a pure function of a filename, so it is tested as one.

from src.core import package_check as pc


@pytest.mark.parametrize("fn,minor,want", [
    # abi3: ONE file serves that version and every later one. Reading the
    # literal cp310 as "3.10 only" is what blocked PyQt6 on Python 3.14.
    ("PyQt6-6.11.0-cp310-abi3-manylinux_2_28_x86_64.whl", 14, True),
    ("PyQt6-6.11.0-cp310-abi3-manylinux_2_28_x86_64.whl", 10, True),
    ("PyQt6-6.11.0-cp310-abi3-manylinux_2_28_x86_64.whl", 9,  False),
    ("astropy-8.0.1-cp311-abi3-manylinux_2_17_x86_64.whl", 14, True),
    # pure Python, with and without a platform
    ("requests-2.34.2-py3-none-any.whl", 14, True),
    ("wandb-0.30.0-py3-none-manylinux_2_17_x86_64.whl", 14, True),
    ("six-1.17.0-py2.py3-none-any.whl", 14, True),
    # version-specific builds
    ("numpy-2.3.0-cp314-cp314-manylinux_2_17_x86_64.whl", 14, True),
    ("numpy-2.3.0-cp313-cp313-manylinux_2_17_x86_64.whl", 14, False),
    # compound python tag
    ("thing-1.0-cp313.cp314-cp313-manylinux_2_17_x86_64.whl", 14, True),
])
def test_wheel_tag_reading(fn, minor, want):
    parts = fn[:-4].split("-")
    py, abi, plat = parts[-3], parts[-2], parts[-1]
    assert pc._plat_ok(plat, "linux")
    assert pc._py_ok(py, abi, 3, minor) is want


def test_platform_is_respected():
    assert pc._plat_ok("win_amd64", "win")
    assert not pc._plat_ok("win_amd64", "linux")
    assert pc._plat_ok("any", "linux")
    assert pc._plat_ok("manylinux_2_17_x86_64", "linux")
    assert not pc._plat_ok("macosx_11_0_arm64", "linux")


@pytest.mark.parametrize("spec,minor,want", [
    ("", 14, True),
    (">=3.9", 14, True),
    (">=3.9", 8, False),
    ("<3.14", 14, False),
    ("<3.14", 13, True),
    (">=3.9,<3.14", 13, True),
    (">=3.9,<3.14", 14, False),
    ("nonsense", 14, True),      # unparseable is no opinion, never a refusal
])
def test_requires_python(spec, minor, want):
    assert pc._req_python_ok(spec, 3, minor) is want


def _rel(*files):
    return list(files)


def _whl(fn, rp=""):
    return {"packagetype": "bdist_wheel", "filename": fn, "requires_python": rp}


def _sdist(rp=""):
    return {"packagetype": "sdist", "filename": "x-1.0.tar.gz",
            "requires_python": rp}


def test_sdist_installs_but_is_not_a_wheel():
    """The distinction the old single verdict lost.

    vpython, fiona, pyaudio and kivy cap their wheels at cp312/cp313 and
    still ship an sdist, so on 3.14 pip CAN install them -- by compiling.
    Saying 'no matching distribution' there would be wrong, and so would
    saying 'a wheel exists'.
    """
    files = _rel(_whl("x-1.0-cp313-cp313-manylinux_2_17_x86_64.whl"), _sdist())
    assert pc._files_support(files, 3, 14, "linux") is True
    assert pc._files_support(files, 3, 14, "linux", wheels_only=True) is False
    assert pc._files_support(files, 3, 13, "linux", wheels_only=True) is True


def test_nothing_at_all():
    files = _rel(_whl("x-1.0-cp313-cp313-manylinux_2_17_x86_64.whl"))
    assert pc._files_support(files, 3, 14, "linux") is False


def test_requires_python_excludes_the_sdist_too():
    """ruptures: declares python<3.14, so even its sdist is out."""
    files = _rel(_sdist(rp=">=3.9,<3.14"))
    assert pc._files_support(files, 3, 13, "linux") is True
    assert pc._files_support(files, 3, 14, "linux") is False


# ── F151 phase 3: the alternative nobody was being told about ──────────────
#
# 16 of the 218 rules name a package to use INSTEAD. package_ops.py wrote
# its own pass over CONFLICT_RULES and never read that key, so a user
# blocked on PyQt5 was told the install would fail and left to find PySide6
# themselves. These assert the three pieces the install dialog now uses.

def test_the_alternative_is_offered_not_just_the_refusal():
    rep = cr.check_static(["PyQt5"], python_version="3.13")
    assert rep.alternatives() == [("pyqt5", "PySide6")]


def test_alternatives_is_empty_when_the_table_names_none():
    rep = cr.check_static(["numpy"], python_version="3.13", env_type="pipx")
    assert rep.warnings           # it did fire
    assert rep.alternatives() == []


def test_blocking_alternatives_covers_every_blocker_or_none():
    """All or nothing.

    Swapping two of three blockers leaves the install just as doomed, so an
    offer that cannot fix the problem is not made at all.
    """
    rep = cr.check_static(["PyQt5"], python_version="3.13")
    assert rep.blocking_alternatives() == {"pyqt5": "PySide6"}

    # orange3 blocks in a pipx environment and has no alternative; the
    # offer has to disappear entirely rather than cover PyQt5 alone.
    rep2 = cr.check_static(["PyQt5", "orange3"], python_version="3.13",
                           env_type="pipx")
    assert len(rep2.blocks) >= 2
    assert rep2.blocking_alternatives() == {}


def test_blocking_alternatives_ignores_warnings():
    """A warning is not a blocker, so its alternative is not an escape."""
    rep = cr.check_static(["numpy"], python_version="3.13", env_type="pipx")
    assert not rep.blocks
    assert rep.blocking_alternatives() == {}


def test_render_findings_says_what_to_use_instead():
    rep = cr.check_static(["PyQt5"], python_version="3.13")
    out = cr.render_findings(rep.blocks)
    assert "Use instead: PySide6" in out
    assert "pyqt5" in out


def test_render_findings_is_the_only_formatter():
    """summary() must not grow a second way of describing a finding."""
    rep = cr.check_static(["PyQt5"], python_version="3.13")
    assert cr.render_findings(rep.blocks + rep.warnings) in rep.summary()


def test_render_findings_survives_a_finding_with_nothing_optional():
    """The live-PyPI pass builds findings by hand; they have no note."""
    assert cr.render_findings([{"name": "x", "severity": "error",
                                "reasons": ["no wheel"]}]) == "⛔ x: no wheel"


def test_render_findings_of_nothing_is_empty():
    assert cr.render_findings([]) == ""
    assert cr.render_findings(None) == ""
