"""Sizing a directory, resolving a terminal, and finding a project.

B34. Three pieces of pure logic that were each wrong in a way nobody could
see from the interface: a size that silently counted the wrong bytes, a
setting that was read from a key nothing wrote, and a project directory that
could not be found for environments VenvStudio had not created.
"""

import os
import sys
import textwrap

import pytest

from src.gui.projects_page import dir_size


# ── dir_size ─────────────────────────────────────────────────────────────

@pytest.mark.skipif(os.name == "nt", reason="symlink creation needs privileges")
def test_symlink_counts_as_the_link_not_the_target(tmp_path):
    """B66. This is the whole bug, in four lines.

    os.path.getsize follows a symlink and returns the size of its TARGET. A
    uv environment has three of them, one being .venv/bin/python, so a 54 MB
    environment reported 386 MB on Bayram's machine; pixi links 1163 files
    conda-style and reported 533 MB for 237 MB. pdm and hatch have no
    symlinks, which is exactly why those two rows agreed with du and hid it.
    """
    target = tmp_path / "huge.bin"
    target.write_bytes(b"x" * 200_000)
    env = tmp_path / "env"
    env.mkdir()
    (env / "small.txt").write_bytes(b"y" * 1_000)
    os.symlink(target, env / "python")

    size = dir_size(env, skip_caches=False)
    assert size < 10_000, (
        f"{size} bytes -- the 200 KB symlink target is being counted")


def test_source_skips_caches_but_environment_does_not(tmp_path):
    """B66. The skip list describes a SOURCE tree, not an environment.

    __pycache__ next to your code is derived clutter; inside an environment
    it is part of what the environment occupies. Applying the list to both
    made a hatch environment report 5.5 MB against du's 9.9 MB, the missing
    4.4 MB being compiled bytecode.
    """
    d = tmp_path / "thing"
    (d / "__pycache__").mkdir(parents=True)
    (d / "__pycache__" / "x.pyc").write_bytes(b"z" * 50_000)
    (d / "real.txt").write_bytes(b"z" * 1_000)

    assert dir_size(d, skip_caches=True) < 5_000
    assert dir_size(d, skip_caches=False) > 45_000


def test_dir_size_of_a_missing_path_is_zero(tmp_path):
    assert dir_size(tmp_path / "not-there") == 0
    assert dir_size("") == 0


# ── the terminal setting ─────────────────────────────────────────────────

@pytest.mark.parametrize("config,expected", [
    ({}, ""),
    ({"default_terminal": "wt"}, "wt"),
    ({"terminal_type": "pwsh"}, "pwsh"),
    ({"default_terminal": "cmd", "terminal_type": "pwsh"}, "cmd"),
    ({"default_terminal": ""}, ""),
    ({"default_terminal": "", "terminal_type": "git-bash"}, ""),
])
def test_configured_terminal(config, expected, fake_config):
    """B76. Settings writes `default_terminal`; every reader asked for
    `terminal_type`, so the read always came back empty and each path fell
    to its own auto-detection -- one route opened cmd, another PowerShell.

    The last two rows are the distinction a bare `or` cannot make: a MISSING
    key means never configured, so the legacy name is worth trying; an EMPTY
    one means the user unticked the box and asked for auto-detection, and a
    stale value must not override that.
    """
    from src.utils.platform_utils import get_configured_terminal
    fake_config.data = dict(config)
    assert get_configured_terminal() == expected


# ── poetry environment -> project ────────────────────────────────────────

def _make_project(root, dir_name, project_name):
    d = root / dir_name
    d.mkdir(parents=True)
    (d / "pyproject.toml").write_text(
        textwrap.dedent(f"""\
            [project]
            name = "{project_name}"
            version = "0.1.0"
            """), encoding="utf-8")
    return d


def test_poetry_env_maps_back_to_its_project(tmp_path, fake_config,
                                             monkeypatch):
    """B44. Poetry names an environment after its project, so the mapping
    runs backwards -- which matters because environments VenvStudio did not
    create carry no marker, and `poetry add` then ran in the virtualenvs
    directory and answered "could not find a pyproject.toml file".

    Note the two names differ: the directory is `ptr_project` and poetry
    calls the project `ptr-project`. Matching on the directory name alone
    would miss it, which is why pyproject's own `name` is compared first.
    """
    from src.core.pip_manager import PipManager

    projects = tmp_path / "vs_projects"
    _make_project(projects, "ptr_project", "ptr-project")
    _make_project(projects, "other_thing", "ptr-project-copy")
    fake_config.data = {"recent_projects": [
        {"path": str(projects / "ptr_project")},
        {"path": str(projects / "other_thing")},
    ]}

    env = tmp_path / "virtualenvs" / "ptr-project-fm2xxDZ4-py3.14"
    env.mkdir(parents=True)
    pm = PipManager(env, env_type="poetry")
    assert pm._project_dir() == str(projects / "ptr_project")


def test_similar_project_names_do_not_collide(tmp_path, fake_config):
    """`ptr-project` and `ptr-project-copy` must not be confused."""
    from src.core.pip_manager import PipManager

    projects = tmp_path / "vs_projects"
    _make_project(projects, "ptr_project", "ptr-project")
    _make_project(projects, "ptr_project_copy", "ptr-project-copy")
    fake_config.data = {"recent_projects": [
        {"path": str(projects / "ptr_project")},
        {"path": str(projects / "ptr_project_copy")},
    ]}

    env = tmp_path / "venvs" / "ptr-project-copy-LpmC3EnV-py3.14"
    env.mkdir(parents=True)
    pm = PipManager(env, env_type="poetry")
    assert pm._project_dir() == str(projects / "ptr_project_copy")


def test_unknown_environment_falls_back_to_itself(tmp_path, fake_config):
    """No marker, no matching project: the env path is the best guess left."""
    from src.core.pip_manager import PipManager

    fake_config.data = {"recent_projects": []}
    env = tmp_path / "venvs" / "something-AbCdEfGh-py3.11"
    env.mkdir(parents=True)
    pm = PipManager(env, env_type="poetry")
    assert pm._project_dir() == str(env)


def test_marker_wins_over_name_matching(tmp_path, fake_config):
    """A marker is the environment saying where its project is; believe it."""
    import json
    from src.core.pip_manager import PipManager

    proj = _make_project(tmp_path, "elsewhere", "unrelated-name")
    fake_config.data = {"recent_projects": []}
    env = tmp_path / "venvs" / "elsewhere-AbCdEfGh-py3.11"
    env.mkdir(parents=True)
    (env / ".venvstudio_env").write_text(
        json.dumps({"poetry_project_dir": str(proj)}), encoding="utf-8")
    pm = PipManager(env, env_type="poetry")
    assert pm._project_dir() == str(proj)


# ── the project a tool-managed environment belongs to ────────────────────

def test_poetry_env_outside_the_project_tree(tmp_path, fake_config):
    """B137. Poetry keeps its environments in a cache far from the project.

    Bayram's case: right-clicking a poetry environment and asking for the
    command list answered

        Poetry could not find a pyproject.toml file in
        ~/.cache/pypoetry/virtualenvs/pppp-InEhWoJ9-py3.14 or its parents

    because the command ran in the environment. The environment name carries
    the project name, and the project is findable from it -- which is what
    _project_dir does, and what the Environments page now asks rather than
    working out again for itself.
    """
    from src.core.pip_manager import PipManager

    projects = tmp_path / "projects"
    _make_project(projects, "pppp", "pppp")
    fake_config.data = {"recent_projects": [{"path": str(projects / "pppp")}]}

    env = tmp_path / ".cache" / "pypoetry" / "virtualenvs" / "pppp-InEhWoJ9-py3.14"
    env.mkdir(parents=True)
    assert PipManager(env, env_type="poetry")._project_dir() == str(projects / "pppp")
