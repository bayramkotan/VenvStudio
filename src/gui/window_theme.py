"""VenvStudio - MainWindow: Theme Mixin
Theme/font application, sidebar restyling, screen-change handling
(moved from main_window.py).
"""
from PySide6.QtWidgets import (
    QComboBox, QHeaderView, QTableWidget, QAbstractItemView, QPushButton,
)
from PySide6.QtCore import Qt, QTimer

from src.core.config_manager import ConfigManager
from src.gui.styles import get_theme


class WindowThemeMixin:
    """Mixin for MainWindow: theme/font application and screen-change handling."""

    def _set_theme(self, theme_name):
        # B184 fix: ConfigManager.set() already auto-saves to disk, but
        # call save() explicitly anyway as a belt-and-suspenders move.
        # The real bug for this issue was in AppearanceMixin's
        # _on_theme_cb_toggled, which silently reset the theme to "dark"
        # whenever the Settings page loaded with the theme checkbox off.
        #
        # B184 v2: View menu sends "light"/"dark", but the styles module
        # only registers specific names like "light-latte", "light-github",
        # "dark" (= Catppuccin Mocha). A bare "light" silently fell back
        # to dark on the next app start. Map the menu shortcut to a real
        # theme id here so what's saved is what's loaded.
        _menu_alias = {
            "light": "light-latte",  # default light variant
        }
        theme_name = _menu_alias.get(theme_name, theme_name)
        self.config.set("theme", theme_name)
        for _save_attr in ("save", "_save", "save_config", "flush", "write"):
            _fn = getattr(self.config, _save_attr, None)
            if callable(_fn):
                try:
                    _fn()
                    break
                except Exception:
                    continue
        self._apply_theme()

    def _apply_theme(self):
        """Apply current theme. Guarded against re-entrant calls and
        RuntimeError during screen transitions (dual-monitor DPI changes).
        """
        if self._applying_theme:
            return  # prevent re-entrant calls during screen change
        self._applying_theme = True
        try:
            theme = self.config.get("theme", "dark")
            font_family = self.config.get("font_secondary_family", "") or self.config.get("font_family", "")
            font_size = self.config.get("font_secondary_size", 13) or self.config.get("font_size", 13)
            primary_family = self.config.get("font_primary_family", "")
            primary_size = self.config.get("font_primary_size", 22)
            tertiary_family = self.config.get("font_tertiary_family", "")
            tertiary_size = self.config.get("font_tertiary_size", 11)
            self.setStyleSheet(get_theme(
                theme, font_family=font_family, font_size=font_size,
                primary_family=primary_family, primary_size=primary_size,
                tertiary_family=tertiary_family, tertiary_size=tertiary_size
            ))
            if hasattr(self, "package_panel"):
                if self.package_panel is not None: self.package_panel.apply_theme(theme)
            if hasattr(self, "settings_page"):
                if self.settings_page is not None:
                    try:
                        self.settings_page._refresh_styles()
                    except Exception:
                        pass
            # B183 fix: learn_page was previously skipped during theme switch,
            # so it stayed in dark colours when the user picked light theme.
            # Try multiple known refresh entry points to stay compatible if
            # the LearnPage API changes.
            if hasattr(self, "learn_page") and self.learn_page is not None:
                try:
                    if hasattr(self.learn_page, "apply_theme"):
                        self.learn_page.apply_theme(theme)
                    elif hasattr(self.learn_page, "_refresh_styles"):
                        self.learn_page._refresh_styles()
                    else:
                        # Last resort: re-apply the global stylesheet to force a repaint
                        self.learn_page.setStyleSheet(self.learn_page.styleSheet())
                except Exception:
                    pass
            # B183 fix: env_table item colours (uv yellow, poetry purple, etc.)
            # are baked into items at refresh time. Without re-running
            # _refresh_env_list after a theme switch, items keep the old
            # palette's pastel colours and look unreadable on light themes.
            if hasattr(self, "env_table") and self.env_table is not None:
                try:
                    self.env_table.setStyleSheet(
                        f"QTableWidget {{ font-size: 16px; "
                        f"color: {self._c()['fg']}; }}"
                        f"QTableWidget::item {{ padding: 8px 12px; font-weight: bold; font-size: 16px; }}"
                        f"QHeaderView::section {{ font-size: 15px; "
                        f"font-weight: bold; padding: 10px; }}"
                    )
                    # Re-render rows with the new theme's colours. Use the
                    # cached env list so this is cheap (no subprocess).
                    self._refresh_env_list(force=False)
                except Exception:
                    pass
            self._refresh_sidebar_styles()
        except RuntimeError:
            # Widget may be in an unstable state during screen transition
            pass
        finally:
            self._applying_theme = False

    def _refresh_sidebar_styles(self):
        """Re-apply inline styles on sidebar widgets that don't inherit QSS."""
        try:
            c = self._c()
            if hasattr(self, "ql_sep"):
                self.ql_sep.setStyleSheet(f"background-color: {c['border']}; max-height: 1px;")
            if hasattr(self, "ql_title"):
                self.ql_title.setStyleSheet(f"color: {c['fg_muted']}; font-size: {self._c()['fs_tiny']}px; padding: 2px 0;")
            if hasattr(self, "ql_env_selector"):
                self.ql_env_selector.setStyleSheet(
                    f"background-color: {c['input_bg']}; color: {c['fg']}; "
                    f"border: 1px solid {c['border']}; border-radius: 6px; padding: 4px 8px; "
                    f"QComboBox QAbstractItemView {{ background-color: {c['card']}; color: {c['fg']}; "
                    f"selection-background-color: {c['accent']}; selection-color: {c['accent_fg']}; }}"
                )
            if hasattr(self, "ql_buttons_widget"):
                for btn in self.ql_buttons_widget.findChildren(__import__("PySide6.QtWidgets", fromlist=["QPushButton"]).QPushButton):
                    btn.setStyleSheet(
                        f"QPushButton {{ text-align: left; padding: 6px 10px; border-radius: 6px; "
                        f"background-color: {c['sidebar']}; color: {c['fg']}; "
                        f"border: 1px solid {c['border']}; }}"
                        f"QPushButton:hover {{ background-color: {c['hover']}; border-color: {c['accent']}; }}"
                    )
            if hasattr(self, "version_label"):
                self.version_label.setStyleSheet(f"color: {c['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
            if hasattr(self, "footer_label"):
                self.footer_label.setStyleSheet(f"color: {c['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        except Exception:
            pass

    def _connect_screen_changed(self):
        """Connect to windowHandle().screenChanged so theme is re-applied
        safely when the window moves between monitors with different DPI.
        """
        try:
            handle = self.windowHandle()
            if handle:
                handle.screenChanged.connect(self._on_screen_changed)
        except Exception:
            pass  # windowHandle() can return None before show()

    def _on_screen_changed(self, new_screen):
        """Re-apply theme after a short delay so Qt finishes its internal
        DPI recalculation before we touch stylesheets.
        """
        from PySide6.QtCore import QTimer
        QTimer.singleShot(150, self._apply_theme)

    def _on_theme_changed(self, theme_name):
        """Handle theme change from settings page."""
        self._apply_theme()

    def _on_font_changed(self, family, size):
        """Handle font change from settings page — rebuild stylesheet with new font."""
        self._apply_theme()

