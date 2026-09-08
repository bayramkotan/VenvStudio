"""Shared setup for VenvStudio's tests.

B34. The first thing this project needed was not more tests of Qt widgets --
it was tests of the parts that decide things. Every bug found by hand on
2026-09-05..08 lived in pure logic: which command a tool takes, which
terminal a setting means, whether a symlink counts towards a directory's
size, whether install and uninstall route to the same tool. Not one of them
needed a window to reproduce.

So these tests import GUI modules with a stub in place of PySide6. That is
not a trick to avoid testing the interface; it is what lets the decisions be
tested at all, in CI, on a machine with no display. Widget behaviour is a
separate job and is not attempted here.

The stub answers any attribute with a dummy that accepts any call, which is
enough for a module to IMPORT. A test that needs real widget behaviour will
fail loudly rather than pass on a stub -- that is deliberate.
"""

import sys
import types
from pathlib import Path

import pytest

# The package lives one level up from tests/.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


class _Any:
    """Accepts anything, returns itself. Enough to import a Qt module."""

    def __init__(self, *a, **k):
        pass

    def __call__(self, *a, **k):
        return _Any()

    def __getattr__(self, name):
        return _Any()

    def __or__(self, other):
        return _Any()

    def __eq__(self, other):
        return False

    def __hash__(self):
        return id(self)


def _stub_pyside():
    """Put a stand-in for PySide6 in sys.modules, if it is not really there."""
    try:
        import PySide6  # noqa: F401
        return                      # the real thing is installed; use it
    except ImportError:
        pass
    for name in ("PySide6", "PySide6.QtWidgets", "PySide6.QtCore",
                 "PySide6.QtGui"):
        mod = types.ModuleType(name)
        mod.__getattr__ = lambda _n: _Any()      # type: ignore[attr-defined]
        sys.modules[name] = mod


_stub_pyside()


@pytest.fixture
def fake_config():
    """A ConfigManager stand-in whose contents the test sets.

    Returned object has `.data`; assign to it and the code under test sees
    it. Installed into sys.modules so a lazy `from src.core.config_manager
    import ConfigManager` inside a function picks it up.
    """
    class _Cfg:
        data = {}

        def get(self, key, default=None):
            return _Cfg.data.get(key, default)

        def set(self, key, value):
            _Cfg.data[key] = value

    mod = types.ModuleType("src.core.config_manager")
    mod.ConfigManager = _Cfg
    _saved = sys.modules.get("src.core.config_manager")
    sys.modules["src.core.config_manager"] = mod
    _Cfg.data = {}
    yield _Cfg
    if _saved is not None:
        sys.modules["src.core.config_manager"] = _saved
    else:
        sys.modules.pop("src.core.config_manager", None)


@pytest.fixture
def tmp_env(tmp_path):
    """A directory shaped like a virtual environment, POSIX layout."""
    env = tmp_path / "env"
    (env / "bin").mkdir(parents=True)
    (env / "lib").mkdir()
    (env / "bin" / "python").write_text("#!/bin/sh\n")
    return env
