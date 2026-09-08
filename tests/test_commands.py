"""The commands each tool takes, and which tool an environment is sent to.

B34/B67. Two bugs in one session came from a command table nobody had ever
run: `poetry lock --check`, which Poetry 2 answers with "The option --check
does not exist", and `hatch add`, which is not a command at all. Both looked
plausible. These tests pin the tables that were afterwards verified against
the real tools, so a plausible-looking edit cannot quietly reintroduce one.

They do NOT run the tools -- that needs five package managers installed and
a network. They check the tables and the routing, which is where the
mistakes actually were.
"""

import pytest

from src.core import pip_manager as pm
from src.gui import projects_page as pp


# ── Project command tables (projects_page) ───────────────────────────────

def test_hatch_has_no_add_command():
    """hatch cannot add a dependency; the table must not claim it can.

    B65: `hatch add` was in _ADD_CMD and pressing Add Package on a hatch
    project answered "Error: No such command 'add'". Verified against hatch
    1.18.0 -- its command list has no add and no remove.
    """
    assert "hatch" not in pp.ProjectsPageMixin._ADD_CMD


@pytest.mark.parametrize("tool,expected", [
    ("uv", ["uv", "add"]),
    ("poetry", ["poetry", "add"]),
    ("pdm", ["pdm", "add"]),
    ("pixi", ["pixi", "add"]),
])
def test_add_commands(tool, expected):
    assert pp.ProjectsPageMixin._ADD_CMD[tool] == expected


@pytest.mark.parametrize("tool,expected", [
    ("uv", ["uv", "sync"]),
    ("poetry", ["poetry", "install"]),
    ("pdm", ["pdm", "install"]),
    ("pixi", ["pixi", "install"]),
    ("hatch", ["hatch", "env", "create"]),
])
def test_sync_commands(tool, expected):
    """Every one of these was RUN against a real scaffolded project."""
    assert pp.ProjectsPageMixin._SYNC_CMD[tool] == expected


def test_sync_and_env_create_are_not_two_tables():
    """B69: _ENV_CREATE held a second copy of _SYNC_CMD.

    Nothing had broken because the copies happened to be equal -- the Sync
    button read one and the right-click Create Environment entry read the
    other. A fix to one would have missed the other.
    """
    assert not hasattr(pp.ProjectsPageMixin, "_ENV_CREATE")


# NOT YET IN THE CODE: _LOCK_CHECK and _BUILD_CMD belong to the Update/Build
# work (B46) that was written, measured and then reverted after an unrelated
# regression. The verified commands are recorded in the TODO under B46 --
# notably that Poetry 2 has no `lock --check` (it is `check --lock`), that
# `pixi lock --check` WRITES pixi.lock so a status check needs --dry-run, and
# that `pixi build` is deprecated and produces a conda package. Tests for them
# go here when the tables land.
#
# Leaving the tests in place against absent attributes would have meant a red
# suite from day one, which teaches people to ignore red suites. They were
# removed the moment the first run showed them failing -- which is itself the
# suite doing its job: it caught me asserting against code that was not there.


# ── Install/uninstall routing (pip_manager) ──────────────────────────────

class _Recorder(pm.PipManager):
    """A PipManager that records which tool it would have used."""

    def __init__(self, env_type, tmp_path):
        self.env_type = env_type
        self.venv_path = tmp_path
        self._backend = "pip"
        self.calls = []

    # install side
    def _install_hatch(self, packages, **kw):
        self.calls.append("hatch")
        return True, ""

    def _install_pdm(self, packages, **kw):
        self.calls.append("pdm")
        return True, ""

    def _install_pixi(self, packages, **kw):
        self.calls.append("pixi")
        return True, ""

    def _install_poetry(self, packages, **kw):
        self.calls.append("poetry")
        return True, ""

    # uninstall side
    def _uninstall_with_tool(self, tool, args, packages, callback=None):
        self.calls.append(tool)
        return True, ""

    def _uninstall_hatch_note(self, packages, callback=None):
        self.calls.append("hatch-refused")
        return False, ""


@pytest.mark.parametrize("env_type,tool", [
    ("poetry", "poetry"),
    ("pdm", "pdm"),
    ("pixi", "pixi"),
    ("hatch", "hatch"),
])
def test_install_routes_to_the_tool(env_type, tool, tmp_path):
    """B44: poetry fell through to pip, so pyproject.toml never heard of it."""
    r = _Recorder(env_type, tmp_path)
    try:
        r.install_packages(["requests"])
    except Exception:
        pass                     # pip path may fail; only routing matters
    assert r.calls[:1] == [tool]


@pytest.mark.parametrize("env_type,tool", [
    ("poetry", "poetry"),
    ("pdm", "pdm"),
    ("pixi", "pixi"),
])
def test_uninstall_routes_to_the_tool(env_type, tool, tmp_path):
    """B44: uninstall routed nothing, so pip left the manifest untouched."""
    r = _Recorder(env_type, tmp_path)
    r.uninstall_packages(["requests"])
    assert r.calls == [tool]


def test_uninstall_refuses_for_hatch(tmp_path):
    """hatch has no remove; pip uninstall would be undone by hatch itself."""
    r = _Recorder("hatch", tmp_path)
    ok, _ = r.uninstall_packages(["requests"])
    assert r.calls == ["hatch-refused"]
    assert ok is False


@pytest.mark.parametrize("env_type", ["venv", "conda"])
def test_plain_environments_still_use_pip(env_type, tmp_path):
    """Routing must not swallow the environments where pip IS correct."""
    r = _Recorder(env_type, tmp_path)
    r.uninstall_packages(["requests"])
    assert r.calls == []


def test_install_and_uninstall_agree(tmp_path):
    """Whatever installs a package must be what removes it.

    B44: `pdm add` writes the manifest and `pip uninstall` does not, so a
    removed package came back on the next install. uv is deliberately in
    NEITHER table -- env_type "uv" is a plain venv that may have no
    pyproject.toml at all, and `uv remove` would fail there.
    """
    for env_type in ("poetry", "pdm", "pixi", "hatch", "uv", "venv", "conda"):
        inst = _Recorder(env_type, tmp_path)
        try:
            inst.install_packages(["x"])
        except Exception:
            pass
        rem = _Recorder(env_type, tmp_path)
        rem.uninstall_packages(["x"])
        routed_in = inst.calls[:1]
        routed_out = [c.replace("-refused", "") for c in rem.calls[:1]]
        assert routed_in == routed_out, (
            f"{env_type}: installs via {routed_in}, removes via {routed_out}")
