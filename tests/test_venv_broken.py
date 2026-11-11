"""Tests for B199 — reading an environment whose interpreter is gone.

venv_manager had no tests at all, which is part of why this went unnoticed:
Bayram's `ml` was listed as a tools folder with 0 packages for over two
hours while 1.6 GB of packages sat in it, and nothing anywhere asserted
what a venv with a missing Python should look like.

These three helpers are the right place to start. They take a directory and
return plain data, they never run a subprocess -- that is the whole point of
them -- so every branch is reachable from a tmp_path.
"""
import os
import sys

import pytest

from src.core.venv_manager_common import (
    broken_venv_reason,
    count_installed_packages,
    venv_cfg_version,
    venv_python_home,
)

_WIN = sys.platform == "win32"


def _mkvenv(root, name, *, home="/opt/python/3.13.13/bin",
            version="3.13.13.final.0", cfg=True,
            link=None, real_python=False, dist=(), egg=()):
    """A venv-shaped directory, with whatever is being tested missing."""
    d = root / name
    (d / ("Scripts" if _WIN else "bin")).mkdir(parents=True)
    sp = (d / "Lib" / "site-packages") if _WIN else (
        d / "lib" / "python3.13" / "site-packages")
    sp.mkdir(parents=True)
    for p in dist:
        (sp / f"{p}-1.0.0.dist-info").mkdir()
    for p in egg:
        (sp / f"{p}-1.0.0.egg-info").mkdir()
    if cfg:
        (d / "pyvenv.cfg").write_text(f"home = {home}\nversion = {version}\n",
                                      encoding="utf-8")
    _py = d / ("Scripts/python.exe" if _WIN else "bin/python")
    if link:
        os.symlink(link, _py)
    elif real_python:
        _py.write_text("#!/bin/sh\n", encoding="utf-8")
    return d


# ── broken_venv_reason ─────────────────────────────────────────────────────

def test_a_working_venv_is_not_broken(tmp_path):
    assert broken_venv_reason(
        _mkvenv(tmp_path, "ok", real_python=True, dist=("numpy",))) == ""


@pytest.mark.skipif(_WIN, reason="symlinks need privileges on Windows")
def test_dangling_interpreter_link_names_the_target(tmp_path):
    """The commonest case: the Python was upgraded or uninstalled.

    MEASURED (Bayram, 2026-11-01): /usr/local/bin/python3.13 pointed at
    /opt/python/3.13.13/bin/python3; that directory went away, and every
    venv built on it stopped having an interpreter.
    """
    _r = broken_venv_reason(
        _mkvenv(tmp_path, "ml", link="/opt/python/9.9.9/bin/python3"))
    assert _r
    assert "/opt/python/9.9.9/bin/python3" in _r


def test_missing_interpreter_falls_back_to_pyvenv_cfg(tmp_path):
    _r = broken_venv_reason(_mkvenv(tmp_path, "dl"))
    assert _r
    assert "/opt/python/3.13.13/bin" in _r


def test_a_directory_with_no_pyvenv_cfg_is_not_a_broken_venv(tmp_path):
    """A tools folder has no interpreter either, and that is not a fault.

    This is the line the old code could not draw, so it called every
    interpreter-less directory a tools folder -- including real venvs.
    """
    assert broken_venv_reason(_mkvenv(tmp_path, "tools", cfg=False)) == ""


def test_a_missing_directory_says_nothing(tmp_path):
    assert broken_venv_reason(tmp_path / "nope") == ""


# ── count_installed_packages ───────────────────────────────────────────────

def test_packages_are_counted_without_an_interpreter(tmp_path):
    """The number that would have stopped the deletion."""
    d = _mkvenv(tmp_path, "ml", link="/nowhere/python",
                dist=("numpy", "pandas", "torch"))
    assert count_installed_packages(d) == 3


def test_dist_info_and_egg_info_for_one_package_count_once(tmp_path):
    d = _mkvenv(tmp_path, "mixed", link="/nowhere/python",
                dist=("numpy",), egg=("numpy", "six"))
    assert count_installed_packages(d) == 2


def test_no_site_packages_is_zero_not_an_error(tmp_path):
    assert count_installed_packages(_mkvenv(tmp_path, "t", cfg=False)) == 0
    assert count_installed_packages(tmp_path / "missing") == 0


# ── pyvenv.cfg readers ─────────────────────────────────────────────────────

@pytest.mark.parametrize("given,want", [
    ("3.13.13.final.0", "3.13.13"),
    ("3.12.1", "3.12.1"),
    ("3.14", "3.14"),
])
def test_version_is_read_from_pyvenv_cfg(tmp_path, given, want):
    """No interpreter is run: a broken venv can still say what it needs."""
    assert venv_cfg_version(_mkvenv(tmp_path, given, version=given)) == want


def test_version_of_a_non_venv_is_empty(tmp_path):
    assert venv_cfg_version(_mkvenv(tmp_path, "t", cfg=False)) == ""


def test_home_is_read_from_pyvenv_cfg(tmp_path):
    d = _mkvenv(tmp_path, "h", home="/opt/python/3.10.20/bin")
    assert venv_python_home(d) == "/opt/python/3.10.20/bin"


def test_home_of_a_non_venv_is_empty(tmp_path):
    assert venv_python_home(_mkvenv(tmp_path, "t", cfg=False)) == ""
