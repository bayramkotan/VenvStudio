"""Tests for counting packages and sizing environments — B205.

Listing environments ran `pip list --format=json` once per environment, so
a full rescan ran one subprocess per environment in a row.
invalidate_memory_cache's own docstring records the cost: "observed taking
30-40+ seconds with several envs". The number it wanted is on disk, one
.dist-info directory per package (PEP 376), which is what B199's
count_installed_packages already reads.

MEASURED against real environments on 2026-11-24:

    normal venv              pip  15 (186.1 ms)   disk  15 (1.09 ms)
    editable install         pip   2 (182.3 ms)   disk   2 (0.61 ms)
    --system-site-packages   pip 172 (284.4 ms)   disk   1

The last line is why count_packages_fast can say None: a venv that sees
the interpreter's own packages is one pip counts and the disk does not,
and the Installed tab lists packages with pip -- so taking the disk count
there would put a different number in the table than in the tab.

The environments here are built by hand rather than with `python -m venv`:
a .dist-info directory is all PEP 376 requires, and a fabricated one makes
the tests deterministic and keeps the suite under a second.
"""
import os

import pytest

from src.core.venv_manager_common import count_packages_fast
from src.utils.platform_utils import get_venv_size


def make_venv(root, packages=(), system_site=False, cfg=True):
    """A venv-shaped directory: pyvenv.cfg plus one .dist-info per package."""
    root.mkdir(parents=True, exist_ok=True)
    if cfg:
        (root / "pyvenv.cfg").write_text(
            "home = /usr/bin\n"
            f"include-system-site-packages = {'true' if system_site else 'false'}\n"
            "version = 3.12.13\n",
            encoding="utf-8")
    site = root / "lib" / "python3.12" / "site-packages"
    site.mkdir(parents=True, exist_ok=True)
    for _name in packages:
        (site / _name).mkdir(exist_ok=True)
    return root


# ── the count ──────────────────────────────────────────────────────────

def test_packages_are_counted_off_disk(tmp_path):
    make_venv(tmp_path / "e", ["requests-2.31.0.dist-info",
                               "click-8.1.7.dist-info",
                               "rich-13.7.0.dist-info"])
    assert count_packages_fast(tmp_path / "e") == 3


def test_egg_info_counts_too(tmp_path):
    """setuptools-era installs leave .egg-info instead."""
    make_venv(tmp_path / "e", ["old_pkg-1.0.egg-info",
                               "new_pkg-2.0.dist-info"])
    assert count_packages_fast(tmp_path / "e") == 2


def test_one_package_with_both_shapes_is_one_package(tmp_path):
    """A name carrying both must not be counted twice — the user is being
    asked to trust this number against what the Installed tab lists."""
    make_venv(tmp_path / "e", ["thing-1.0.dist-info", "thing-1.0.egg-info"])
    assert count_packages_fast(tmp_path / "e") == 1


def test_loose_modules_are_not_packages(tmp_path):
    """site-packages holds plenty that pip does not list: __pycache__, a
    bare .py dropped in, the directory an installed package unpacks to."""
    _root = make_venv(tmp_path / "e", ["real-1.0.dist-info"])
    _site = _root / "lib" / "python3.12" / "site-packages"
    (_site / "__pycache__").mkdir()
    (_site / "real").mkdir()
    (_site / "stray.py").write_text("", encoding="utf-8")
    assert count_packages_fast(tmp_path / "e") == 1


def test_the_windows_layout_is_read_too(tmp_path):
    _root = tmp_path / "e"
    _root.mkdir()
    (_root / "pyvenv.cfg").write_text(
        "include-system-site-packages = false\n", encoding="utf-8")
    _site = _root / "Lib" / "site-packages"
    _site.mkdir(parents=True)
    for _n in ("a-1.0.dist-info", "b-2.0.dist-info"):
        (_site / _n).mkdir()
    assert count_packages_fast(_root) == 2


# ── when it must refuse to answer ──────────────────────────────────────

def test_system_site_packages_falls_back_to_pip(tmp_path):
    """The one case that matters.

    MEASURED on a real --system-site-packages venv: pip listed 172
    packages, the disk held 1. Answering 1 would disagree with the
    Installed tab, which lists with pip.
    """
    make_venv(tmp_path / "e", ["only-1.0.dist-info"], system_site=True)
    assert count_packages_fast(tmp_path / "e") is None


def test_the_flag_is_read_case_and_space_insensitively(tmp_path):
    _root = tmp_path / "e"
    _root.mkdir()
    (_root / "pyvenv.cfg").write_text(
        "Include-System-Site-Packages   =   TRUE\n", encoding="utf-8")
    (_root / "lib" / "python3.12" / "site-packages").mkdir(parents=True)
    assert count_packages_fast(_root) is None


def test_an_empty_venv_falls_back_to_pip(tmp_path):
    """Zero could mean empty, or it could mean a layout this cannot read.
    pip is cheap on an empty environment and right on both."""
    make_venv(tmp_path / "e")
    assert count_packages_fast(tmp_path / "e") is None


def test_a_directory_that_is_not_a_venv_says_nothing(tmp_path):
    (tmp_path / "plain").mkdir()
    assert count_packages_fast(tmp_path / "plain") is None


def test_a_missing_path_does_not_raise(tmp_path):
    assert count_packages_fast(tmp_path / "nope") is None


def test_an_unreadable_pyvenv_cfg_does_not_raise(tmp_path):
    _root = tmp_path / "e"
    _root.mkdir()
    (_root / "pyvenv.cfg").mkdir()        # a directory where a file belongs
    assert count_packages_fast(_root) is None


# ── the size ───────────────────────────────────────────────────────────

def _human_to_bytes(text):
    _n, _unit = text.split()
    return float(_n) * {"B": 1, "KB": 1024, "MB": 1024 ** 2,
                        "GB": 1024 ** 3, "TB": 1024 ** 4}[_unit]


def test_size_counts_every_regular_file(tmp_path):
    (tmp_path / "sub" / "deeper").mkdir(parents=True)
    (tmp_path / "a.bin").write_bytes(b"x" * 5000)
    (tmp_path / "sub" / "b.bin").write_bytes(b"y" * 3000)
    (tmp_path / "sub" / "deeper" / "c.bin").write_bytes(b"z" * 1000)
    assert _human_to_bytes(get_venv_size(tmp_path)) == pytest.approx(9000, rel=0.01)


@pytest.mark.skipif(os.name == "nt", reason="symlinks need privileges on Windows")
def test_symlinks_are_not_followed_or_counted(tmp_path):
    """A pipx home symlinks site-packages into shared/. Following those
    would count the same bytes several times; counting the link itself
    would add bytes that are not there."""
    (tmp_path / "real").mkdir()
    (tmp_path / "real" / "big.bin").write_bytes(b"x" * 4096)
    os.symlink(tmp_path / "real" / "big.bin", tmp_path / "link_to_file")
    os.symlink(tmp_path / "real", tmp_path / "link_to_dir")
    assert _human_to_bytes(get_venv_size(tmp_path)) == pytest.approx(4096, rel=0.01)


def test_a_broken_symlink_does_not_abandon_the_total(tmp_path):
    (tmp_path / "keep.bin").write_bytes(b"x" * 2048)
    try:
        os.symlink(tmp_path / "gone", tmp_path / "dangling")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    assert _human_to_bytes(get_venv_size(tmp_path)) == pytest.approx(2048, rel=0.01)


def test_an_empty_directory_is_zero_not_na(tmp_path):
    assert get_venv_size(tmp_path) == "0.0 B"


def test_a_missing_directory_does_not_raise(tmp_path):
    get_venv_size(tmp_path / "nope")


def test_the_unit_grows_with_the_total(tmp_path):
    (tmp_path / "f.bin").write_bytes(b"x" * (3 * 1024 * 1024))
    assert get_venv_size(tmp_path).endswith(" MB")
