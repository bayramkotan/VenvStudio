"""Tests for src/cli.py — B200 and B201.

cli.py had no tests. Both bugs here are the kind a test would have caught
the day they were written: one is a pair of functions disagreeing about
what a subcommand is, the other is a question asked of the wrong subject.

The module imports only argparse and sys at import time, so none of this
needs an environment, a network or Qt.
"""
import importlib.metadata as md
import sys

import pytest

from src import cli


# ── B200: `vs LIST` opened the GUI ─────────────────────────────────────────
#
# MEASURED before the fix:
#     vs list -> True    vs LIST   -> False
#     vs update -> True  vs UPDATE -> False
# `vs --LIST` worked, but only because anything starting with a dash is
# treated as CLI -- not because the case was handled.

@pytest.mark.parametrize("arg", [
    "list", "LIST", "List",
    "update", "UPDATE", "Update",
    "preset", "PRESET",
    "create", "CREATE",
])
def test_a_subcommand_is_a_subcommand_in_any_case(arg):
    assert cli.is_cli_invocation(["vs", arg]) is True


@pytest.mark.parametrize("arg", [
    "-V", "-v", "-h", "-H", "--version", "--VERSION",
    "--list", "--LIST", "--Create",
])
def test_flags_still_route_to_the_cli(arg):
    assert cli.is_cli_invocation(["vs", arg]) is True


@pytest.mark.parametrize("arg", ["ml", "notacommand", "listt", "lis"])
def test_anything_that_is_not_a_command_still_opens_the_gui(arg):
    """The GUI is the default, and must stay the default.

    Folding case must not turn a stray word into a subcommand -- someone
    typing an environment name by mistake should still get the window.
    """
    assert cli.is_cli_invocation(["vs", arg]) is False


def test_no_arguments_opens_the_gui():
    assert cli.is_cli_invocation(["vs"]) is False
    assert cli.is_cli_invocation([]) is False


def test_is_cli_invocation_does_not_modify_its_argument():
    """It asks a question; it is not allowed to answer by rewriting."""
    _argv = ["vs", "LIST"]
    cli.is_cli_invocation(_argv)
    assert _argv == ["vs", "LIST"]


@pytest.mark.parametrize("given,want", [
    (["vs", "LIST"], "list"),
    (["vs", "--Create", "x"], "create"),
    (["vs", "-v"], "-V"),
    (["vs", "--HELP"], "--help"),
    (["vs", "ml"], "ml"),
])
def test_normalize_argv(given, want):
    assert cli._normalize_argv(given)[1] == want


def test_the_two_agree():
    """The actual defect: is_cli_invocation and run_cli judged differently.

    run_cli parses _normalize_argv(argv); is_cli_invocation read argv
    directly. Whatever one accepts as a subcommand, the other must.
    """
    for _a in ("list", "LIST", "Update", "--LIST", "-v"):
        _norm = cli._normalize_argv(["vs", _a])[1]
        _routed = cli.is_cli_invocation(["vs", _a])
        assert _routed is (_norm in cli.COMMANDS or _norm.startswith("-"))


# ── B201: which copy is `vs update` talking about ──────────────────────────

def _method_with(monkeypatch, tmp_path, *, module_at, dist_root, git=False):
    """Run _install_method as if the module and the distribution were there."""
    _mod = tmp_path / module_at
    _mod.parent.mkdir(parents=True, exist_ok=True)
    _mod.write_text("", encoding="utf-8")
    if git:
        (_mod.parent.parent / ".git").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cli, "__file__", str(_mod))

    if dist_root is None:
        def _fail(_name):
            raise md.PackageNotFoundError(_name)
        monkeypatch.setattr(md, "distribution", _fail)
    else:
        _root = tmp_path / dist_root
        _root.mkdir(parents=True, exist_ok=True)

        class _D:
            def locate_file(self, _p):
                return _root
        monkeypatch.setattr(md, "distribution", lambda _n: _D())
    return cli._install_method()


def test_a_checkout_is_a_checkout_even_when_venvstudio_is_installed(
        monkeypatch, tmp_path):
    """The whole bug.

    Every development machine has VenvStudio installed AND a checkout.
    The old test was "does a distribution named venvstudio exist", which
    is true on all of them, so running `vs update` from the checkout
    reported "pip" and offered to upgrade a copy that was not running.
    """
    _m, _where, _cmd = _method_with(
        monkeypatch, tmp_path,
        module_at="Github/VenvStudio/src/cli.py",
        dist_root="site-packages", git=True)
    assert _m == "source"
    assert _where.endswith("VenvStudio")
    assert _cmd == ["git", "pull"]


def test_a_checkout_with_no_git_is_not_told_to_pull(monkeypatch, tmp_path):
    """A downloaded zip has no remote; `git pull` there fails confusingly."""
    _m, _where, _cmd = _method_with(
        monkeypatch, tmp_path,
        module_at="downloads/VenvStudio/src/cli.py",
        dist_root="site-packages", git=False)
    assert _m == "source"
    assert _cmd == []


def test_nothing_installed_at_all_is_a_checkout(monkeypatch, tmp_path):
    _m, _, _cmd = _method_with(
        monkeypatch, tmp_path,
        module_at="Github/VenvStudio/src/cli.py",
        dist_root=None, git=True)
    assert _m == "source"
    assert _cmd == ["git", "pull"]


def test_a_real_pip_copy_is_still_recognised(monkeypatch, tmp_path):
    """The module lives INSIDE the distribution -- that is a pip install."""
    _m, _where, _cmd = _method_with(
        monkeypatch, tmp_path,
        module_at="site-packages/src/cli.py",
        dist_root="site-packages")
    assert _m in ("pip", "pip-root")
    assert _cmd[:4] == [sys.executable, "-m", "pip", "install"]
    assert _cmd[-1] == "venvstudio"


def test_a_frozen_build_is_never_a_pip_upgrade(monkeypatch):
    """An AppImage cannot be upgraded by pip, and must not offer to try."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    _m, _, _cmd = cli._install_method()
    assert _m == "frozen"
    assert _cmd == []


# ── version comparison: the v1.6.97 lesson ─────────────────────────────────

def test_versions_compare_as_numbers_not_as_text():
    """1.6.100 is newer than 1.6.97. As strings it is the other way round,
    which is how a release once went out believing it was up to date."""
    assert cli._version_key("1.6.100") > cli._version_key("1.6.97")
    assert cli._version_key("1.6.113") > cli._version_key("1.6.99")
    assert cli._version_key("2.0.0") > cli._version_key("1.9.9")


def test_equal_versions_are_equal():
    assert cli._version_key("1.6.112") == cli._version_key("1.6.112")


def test_an_unreadable_version_does_not_raise():
    cli._version_key("")
    cli._version_key("not-a-version")
