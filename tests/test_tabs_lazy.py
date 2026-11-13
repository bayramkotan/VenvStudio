"""Tests for the lazy tab machinery — B204.

The bug: opening an environment built all five tabs, every time.

package_panel._setup_ui builds ONE tab and leaves the other four as empty
placeholders, so that a tab costs nothing until somebody clicks it. Then
env_state._update_tabs_for_env_type removed every tab from the bar and
added them back — and QTabWidget.addTab needs a widget, so it built all
four on the spot. MEASURED from Bayram's log on v1.6.111, selecting one
environment:

    [Tabs] 'catalog' built in 471 ms, inserted in 296 ms
    [Tabs] 'presets' built in 158 ms, inserted in 108 ms

out of 2263 ms for the whole refresh. The lazy design was paid for and
never used.

Unlike the rest of this suite, these tests need REAL Qt: what broke was
the relationship between a position on the tab bar and a position in
_tab_defs, and a stub cannot have that wrong. conftest uses the real
PySide6 whenever it is installed, so these run on a development machine
and skip where there is none.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_qtw = pytest.importorskip("PySide6.QtWidgets")
if not isinstance(getattr(_qtw, "QTabWidget", None), type):
    # conftest's stub is in place — PySide6 is not really installed.
    pytest.skip("real PySide6 required", allow_module_level=True)

from PySide6.QtWidgets import (  # noqa: E402
    QApplication, QComboBox, QLabel, QPlainTextEdit, QTableWidget,
    QTabWidget, QWidget)

from src.gui.env_state import EnvStateMixin        # noqa: E402
from src.gui.package_misc import PackageMiscMixin  # noqa: E402
from src.gui.package_ops import PackageOpsMixin    # noqa: E402

TAB_KEYS = ["launcher", "installed", "catalog", "presets", "manual"]


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


class _Panel(PackageMiscMixin, EnvStateMixin, PackageOpsMixin):
    """The smallest thing that has a tab bar.

    Only the attributes the tab code actually reaches are provided. A
    creator records that it ran and hands back a widget that can be told
    apart from a placeholder, which is the whole measurement: a test that
    cannot see WHICH tabs were built cannot see this bug.
    """

    def __init__(self):
        self.built = []
        self.filled = 0
        self.tabs = QTabWidget()
        self._tab_defs = [(k, k.title(), None, f"tip-{k}") for k in TAB_KEYS]
        self._tab_built = {}
        self._current_env_type = "venv"
        self.app_definitions = []
        # The same stub widgets PackagePanel.__init__ installs, so that
        # code reaching into an unbuilt tab fails here for the reason it
        # fails there -- on the widgets that have NO stub.
        self.packages_table = QTableWidget()
        self.pkg_count_label = QLabel()
        self.catalog_table = QTableWidget()
        self.category_combo = QComboBox()
        self.manual_input = QPlainTextEdit()
        self.manual_info_label = QLabel()
        self.output_log = QPlainTextEdit()
        for _i, (_k, _lab, _w, _tt) in enumerate(self._tab_defs):
            self.tabs.addTab(self._tab_placeholder(_k), _lab)
            self.tabs.setTabToolTip(_i, _tt)
        self._ensure_tab_built(0)
        self.tabs.currentChanged.connect(self._on_tab_changed)

    # ── the parts of PackagePanel the tab code touches ──────────────────
    def _set_env_cmd_strip(self, _text):
        pass

    def _make(self, key):
        self.built.append(key)
        _w = QWidget()
        _w.setObjectName("real-" + key)
        return _w

    def _create_launcher_tab(self):
        return self._make("launcher")

    def _create_installed_tab(self):
        return self._make("installed")

    def _create_catalog_tab(self):
        return self._make("catalog")

    def _create_presets_tab(self):
        return self._make("presets")

    def _create_manual_tab(self):
        # The real creator builds its own label and input with generic
        # wording, discarding whatever the stubs were holding.
        self.manual_info_label = QLabel("generic")
        self.manual_input = QPlainTextEdit()
        self.manual_input.setPlaceholderText("generic")
        self.output_log = QPlainTextEdit()
        return self._make("manual")

    def _fill_packages_table_from_cache(self):
        self.filled += 1
        return True

    def _update_preset_badges(self):
        pass

    # ── helpers for the tests ───────────────────────────────────────────
    def bar(self):
        return [self._tab_key_at(i) for i in range(self.tabs.count())]

    def hide_tab(self, key):
        """Take one tab off the bar, the way a future env type would."""
        self.tabs.blockSignals(True)
        while self.tabs.count():
            self.tabs.removeTab(0)
        for _k, _lab, _w, _tt in self._tab_defs:
            if _k != key:
                self.tabs.addTab(_w if _w is not None
                                 else self._tab_placeholder(_k), _lab)
        self.tabs.blockSignals(False)


@pytest.fixture
def panel(qapp):
    return _Panel()


# ── what the window costs before anyone clicks anything ────────────────

def test_only_the_first_tab_is_built_at_startup(panel):
    assert panel.built == ["launcher"]
    assert panel.bar() == TAB_KEYS


def test_opening_an_environment_builds_nothing(panel):
    """The defect itself.

    Before the fix this left ['installed', 'catalog', 'presets', 'manual']
    in `built` — four tabs constructed while the user waited for one
    environment to open.
    """
    panel.built.clear()
    panel._update_tabs_for_env_type()
    assert panel.built == []
    assert panel.bar() == TAB_KEYS


def test_switching_environment_type_builds_nothing_either(panel):
    for _t in ("conda", "poetry", "pipx", "uv", "venv"):
        panel._current_env_type = _t
        panel.built.clear()
        panel._update_tabs_for_env_type()
        assert panel.built == [], f"{_t} built {panel.built}"


def test_a_tab_is_built_when_it_is_clicked(panel):
    panel._update_tabs_for_env_type()
    panel.built.clear()
    panel.tabs.setCurrentIndex(1)
    assert panel.built == ["installed"]
    assert panel.tabs.widget(1).objectName() == "real-installed"


def test_a_tab_is_built_once_however_often_it_is_visited(panel):
    panel.tabs.setCurrentIndex(2)
    panel.tabs.setCurrentIndex(0)
    panel.tabs.setCurrentIndex(2)
    panel._update_tabs_for_env_type()
    assert panel.built.count("catalog") == 1


# ── the tooltips, which are the only env-dependent part ────────────────

def test_tooltips_follow_the_environment_type(panel):
    panel._current_env_type = "venv"
    panel._update_tabs_for_env_type()
    assert "pip packages" in panel.tabs.tabToolTip(1)
    panel._current_env_type = "conda"
    panel._update_tabs_for_env_type()
    assert "conda packages" in panel.tabs.tabToolTip(1)
    assert panel.tabs.tabToolTip(2).startswith("\U0001f6d2")


def test_building_a_tab_keeps_the_environment_aware_tooltip(panel):
    """The generic tooltip in _tab_defs must not overwrite the live one."""
    panel._current_env_type = "conda"
    panel._update_tabs_for_env_type()
    panel.tabs.setCurrentIndex(1)
    assert "conda packages" in panel.tabs.tabToolTip(1)


# ── bar positions are not _tab_defs positions ──────────────────────────

def test_a_shifted_tab_builds_the_tab_that_is_actually_there(panel):
    """What made the eager build load-bearing.

    _ensure_tab_built read its argument as an index into _tab_defs as well
    as into the tab bar. Those agree only while every tab is visible —
    which was always true precisely BECAUSE every tab was being built. Hide
    one and the two part company: bar position 2 is 'presets', _tab_defs
    position 2 is 'catalog'.
    """
    panel.hide_tab("catalog")
    assert panel.bar() == ["launcher", "installed", "presets", "manual"]
    panel.built.clear()
    panel.tabs.setCurrentIndex(2)
    assert panel.built == ["presets"]
    assert panel.tabs.widget(2).objectName() == "real-presets"


def test_a_shifted_build_writes_to_the_right_tab_defs_slot(panel):
    panel.hide_tab("catalog")
    panel.tabs.setCurrentIndex(2)
    _by_key = {d[0]: d[2] for d in panel._tab_defs}
    assert _by_key["presets"].objectName() == "real-presets"
    assert _by_key["catalog"] is None
    assert _by_key["manual"] is None


def test_a_swapped_widget_reaches_the_tab_bar(panel):
    """reload_presets_tab replaces the widget in _tab_defs and then relies
    on _update_tabs_for_env_type to put it on the bar.

    Skipping the rebuild when the tab bar is unchanged must not skip this:
    the KEYS are the same, the widget is not. _tab_key_at answers None for
    a widget that no longer appears in _tab_defs, which is what makes the
    comparison notice.
    """
    panel.tabs.setCurrentIndex(3)
    _fresh = QWidget()
    _fresh.setObjectName("reloaded-presets")
    panel._tab_defs[3] = ("presets", "Presets", _fresh, "tip-presets")
    panel._update_tabs_for_env_type()
    assert panel.tabs.widget(3) is _fresh
    assert panel.bar() == TAB_KEYS


def test_a_hidden_tab_comes_back_without_being_built(panel):
    panel.hide_tab("catalog")
    panel.built.clear()
    panel._update_tabs_for_env_type()
    assert panel.bar() == TAB_KEYS
    assert panel.built == []


# ── the tab the user ends up on must have content ──────────────────────

def test_the_current_tab_is_always_built(panel):
    for _t in ("venv", "conda", "pipx"):
        panel._current_env_type = _t
        panel._update_tabs_for_env_type()
        _cur = panel.tabs.currentIndex()
        assert panel._tab_built.get(panel._tab_key_at(_cur)) is True


def test_the_selected_tab_survives_an_environment_change(panel):
    panel.tabs.setCurrentIndex(3)
    panel._current_env_type = "conda"
    panel._update_tabs_for_env_type()
    assert panel._tab_key_at(panel.tabs.currentIndex()) == "presets"


def test_a_late_installed_tab_is_filled_from_the_cache(panel):
    """A tab built after the packages loaded has missed its own data.

    _on_packages_loaded wrote rows into the stub table; building the tab
    then threw that stub away, so Installed opened empty on an environment
    whose package count was right everywhere else in the window.
    """
    panel._update_tabs_for_env_type()
    assert panel.filled == 0
    panel.tabs.setCurrentIndex(1)
    assert panel.filled == 1


def test_a_late_manual_tab_describes_the_right_environment(panel):
    """_create_manual_tab writes generic wording of its own.

    The env-aware description went to the stub label, which the build then
    threw away — so a conda environment's Manual tab explained pip.
    """
    panel._current_env_type = "conda"
    panel._update_tabs_for_env_type()
    panel.tabs.setCurrentIndex(4)
    assert "conda-forge" in panel.manual_info_label.text()
    assert "r-base" in panel.manual_input.placeholderText()


def test_the_manual_tab_follows_later_environment_changes(panel):
    panel.tabs.setCurrentIndex(4)
    panel._current_env_type = "pipx"
    panel._update_tabs_for_env_type()
    assert "pipx" in panel.manual_info_label.text()


# ── what runs while the tabs are still placeholders ────────────────────
#
# This is the half of B204 that only showed up on a real machine. Making
# the tabs lazy did not just postpone their widgets -- it put every piece
# of code that reaches into a tab from outside in a new position, where
# the widget it wants may not exist yet. MEASURED on Bayram's machine,
# first run of the patch, before the window had finished opening:
#
#     UNHANDLED: AttributeError: 'PackagePanel' object has no attribute
#     'apply_btn'
#       _on_packages_loaded -> _populate_catalog -> _update_apply_button
#
# catalog_table and category_combo have stubs in PackagePanel.__init__.
# apply_btn and changes_label do not, and nothing had ever needed them to.

def test_populating_the_catalog_before_its_tab_exists_does_not_crash(panel):
    panel._update_tabs_for_env_type()
    assert not hasattr(panel, "apply_btn")
    panel._populate_catalog()               # must not raise
    assert panel._catalog_initial_state == {}


def test_the_whole_post_load_sequence_survives_unbuilt_tabs(panel):
    """Everything _on_packages_loaded calls after writing its rows.

    Each of these reaches into a different tab, and on startup three of
    the four tabs do not exist yet.
    """
    panel._update_tabs_for_env_type()
    panel._populate_catalog()
    panel._update_preset_badges()
    panel._fill_packages_table_from_cache()


def test_an_install_log_written_before_the_manual_tab_survives(panel):
    """An install started from Catalog or Presets writes to output_log.

    That log lived on the stub, and building the Manual tab discarded the
    stub — so the record of what pip just did disappeared the first time
    the user went to look at it.
    """
    panel._update_tabs_for_env_type()
    panel.output_log.setPlainText("Installing numpy...\nSuccessfully installed")
    panel.tabs.setCurrentIndex(4)
    assert "Successfully installed" in panel.output_log.toPlainText()


# ── placeholders ───────────────────────────────────────────────────────

def test_a_placeholder_is_reused_not_recreated(panel):
    """A fresh QWidget per rebuild would be a slow leak."""
    _first = panel._tab_placeholder("manual")
    for _ in range(5):
        panel._update_tabs_for_env_type()
    assert panel._tab_placeholder("manual") is _first


def test_a_placeholder_knows_which_tab_it_is_holding(panel):
    for _k in TAB_KEYS:
        assert panel._tab_placeholder(_k).property("vsTabKey") == _k


def test_tab_key_at_prefers_the_real_widget_over_a_placeholder(panel):
    panel.tabs.setCurrentIndex(2)
    assert panel._tab_key_at(2) == "catalog"
    assert panel.tabs.widget(2).objectName() == "real-catalog"


def test_tab_key_at_is_safe_off_the_end(panel):
    assert panel._tab_key_at(99) is None
    assert panel._tab_key_at(-1) is None
