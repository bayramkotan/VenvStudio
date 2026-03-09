"""
VenvStudio - Qt Stylesheets
Modern dark and light themes with multiple variants.

Themes:
  - dark           : Catppuccin Mocha (default)
  - light-latte    : Catppuccin Latte (soft, warm)
  - light-github   : GitHub Light (clean, minimal)
  - light-vscode   : VS Code Light (professional)
  - light-nord     : Nord Light (cool, muted)
"""


def _build_theme(c: dict) -> str:
    """Build a complete QSS stylesheet from a color palette dict."""
    return f"""
/* ── Base ── */
QMainWindow, QDialog {{
    background-color: {c['bg']};
    color: {c['fg']};
}}

QWidget {{
    background-color: {c['bg']};
    color: {c['fg']};
    font-family: "Segoe UI", "SF Pro Display", "Ubuntu", sans-serif;
    font-size: 13px;
}}

/* ── Sidebar ── */
#sidebar {{
    background-color: {c['sidebar']};
    border-right: 1px solid {c['border']};
}}

#sidebar QPushButton {{
    background-color: transparent;
    color: {c['fg']};
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    text-align: left;
    font-size: 13px;
}}

#sidebar QPushButton:hover {{
    background-color: {c['hover']};
}}

#sidebar QPushButton:checked, #sidebar QPushButton[active="true"] {{
    background-color: {c['active']};
    color: {c['accent']};
    font-weight: bold;
}}

/* ── Headers ── */
QLabel#header {{
    font-size: 22px;
    font-weight: bold;
    color: {c['fg']};
    padding: 8px 0;
}}

QLabel#subheader {{
    font-size: 14px;
    color: {c['fg_muted']};
    padding: 4px 0;
}}

/* ── Buttons ── */
QPushButton {{
    background-color: {c['accent']};
    color: {c['accent_fg']};
    border: none;
    border-radius: 8px;
    padding: 8px 20px;
    font-weight: bold;
    font-size: 13px;
}}

QPushButton:hover {{
    background-color: {c['accent_hover']};
}}

QPushButton:pressed {{
    background-color: {c['accent_press']};
}}

QPushButton:disabled {{
    background-color: {c['disabled_bg']};
    color: {c['disabled_fg']};
}}

QPushButton#danger {{
    background-color: {c['danger']};
    color: {c['danger_fg']};
}}

QPushButton#danger:hover {{
    background-color: {c['danger_hover']};
}}

QPushButton#secondary {{
    background-color: {c['secondary']};
    color: {c['secondary_fg']};
}}

QPushButton#secondary:hover {{
    background-color: {c['secondary_hover']};
}}

QPushButton#success {{
    background-color: {c['success']};
    color: {c['success_fg']};
}}

QPushButton#success:hover {{
    background-color: {c['success_hover']};
}}

/* ── Input Fields ── */
QLineEdit, QComboBox {{
    background-color: {c['input_bg']};
    color: {c['fg']};
    border: 2px solid {c['border']};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: {c['accent']};
    selection-color: {c['accent_fg']};
}}

QLineEdit:focus, QComboBox:focus {{
    border-color: {c['accent']};
}}

QComboBox::drop-down {{
    border: none;
    padding-right: 10px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {c['fg_muted']};
    margin-right: 10px;
}}

QComboBox QAbstractItemView {{
    background-color: {c['input_bg']};
    color: {c['fg']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    selection-background-color: {c['active']};
    selection-color: {c['fg']};
}}

/* ── Tables ── */
QTableWidget, QTreeWidget, QListWidget {{
    background-color: {c['card']};
    alternate-background-color: {c['bg']};
    color: {c['fg']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    gridline-color: {c['border']};
    selection-background-color: {c['active']};
    selection-color: {c['fg']};
}}

QTableWidget::item, QTreeWidget::item, QListWidget::item {{
    padding: 6px;
}}

QHeaderView::section {{
    background-color: {c['sidebar']};
    color: {c['fg_muted']};
    border: none;
    border-bottom: 2px solid {c['border']};
    padding: 8px;
    font-weight: bold;
}}

/* ── Scrollbar ── */
QScrollBar:vertical {{
    background-color: {c['bg']};
    width: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background-color: {c['scrollbar']};
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {c['scrollbar_hover']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background-color: {c['bg']};
    height: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal {{
    background-color: {c['scrollbar']};
    border-radius: 5px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {c['scrollbar_hover']};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── GroupBox ── */
QGroupBox {{
    border: 1px solid {c['border']};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
    color: {c['fg_muted']};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
}}

/* ── Tabs ── */
QTabWidget::pane {{
    border: 1px solid {c['border']};
    border-radius: 8px;
    background-color: {c['bg']};
}}

QTabBar::tab {{
    background-color: {c['sidebar']};
    color: {c['fg_muted']};
    border: none;
    padding: 10px 20px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background-color: {c['bg']};
    color: {c['accent']};
    font-weight: bold;
}}

QTabBar::tab:hover:!selected {{
    background-color: {c['hover']};
}}

/* ── Progress Bar ── */
QProgressBar {{
    background-color: {c['border']};
    border: none;
    border-radius: 6px;
    height: 8px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {c['accent']};
    border-radius: 6px;
}}

/* ── Checkbox ── */
QCheckBox {{
    spacing: 8px;
    color: {c['fg']};
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {c['border']};
    border-radius: 4px;
    background-color: {c['input_bg']};
}}

QCheckBox::indicator:checked {{
    background-color: {c['accent']};
    border-color: {c['accent']};
}}

/* ── Spin Box ── */
QSpinBox {{
    background-color: {c['input_bg']};
    color: {c['fg']};
    border: 2px solid {c['border']};
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 13px;
}}

QSpinBox:focus {{
    border-color: {c['accent']};
}}

/* ── Tooltip ── */
QToolTip {{
    background-color: {c['input_bg']};
    color: {c['fg']};
    border: 1px solid {c['border']};
    border-radius: 6px;
    padding: 6px;
}}

/* ── StatusBar ── */
QStatusBar {{
    background-color: {c['sidebar']};
    color: {c['fg_muted']};
    border-top: 1px solid {c['border']};
}}

/* ── TextEdit / PlainTextEdit ── */
QTextEdit, QPlainTextEdit {{
    background-color: {c['sidebar']};
    color: {c['fg']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    padding: 8px;
    font-family: "Cascadia Code", "Fira Code", "JetBrains Mono", "Consolas", monospace;
    font-size: 12px;
}}

/* ── Menu ── */
QMenuBar {{
    background-color: {c['sidebar']};
    color: {c['fg']};
    border-bottom: 1px solid {c['border']};
}}

QMenuBar::item:selected {{
    background-color: {c['hover']};
    border-radius: 4px;
}}

QMenu {{
    background-color: {c['card']};
    color: {c['fg']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    padding: 4px;
}}

QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {c['active']};
}}

QMenu::separator {{
    height: 1px;
    background: {c['border']};
    margin: 4px 8px;
}}

/* ── Splitter ── */
QSplitter::handle {{
    background-color: {c['border']};
}}

/* ── Card-like frames ── */
QFrame#card {{
    background-color: {c['card']};
    border: 1px solid {c['border']};
    border-radius: 12px;
    padding: 16px;
}}

/* ── Progress Dialog ── */
QProgressDialog {{
    background-color: {c['bg']};
}}

/* ── Input Dialog ── */
QInputDialog {{
    background-color: {c['bg']};
}}
"""


# ═══════════════════════════════════════════════════════════════════════════════
# Color Palettes
# ═══════════════════════════════════════════════════════════════════════════════

_DARK_CATPPUCCIN = {
    'bg': '#1e1e2e', 'fg': '#cdd6f4', 'fg_muted': '#a6adc8',
    'sidebar': '#181825', 'border': '#313244',
    'hover': '#313244', 'active': '#45475a',
    'card': '#1e1e2e', 'input_bg': '#313244',
    'scrollbar': '#45475a', 'scrollbar_hover': '#585b70',
    'accent': '#89b4fa', 'accent_fg': '#1e1e2e',
    'accent_hover': '#b4d0fb', 'accent_press': '#74c7ec',
    'danger': '#f38ba8', 'danger_fg': '#1e1e2e', 'danger_hover': '#f5a3b8',
    'success': '#a6e3a1', 'success_fg': '#1e1e2e', 'success_hover': '#b8eab4',
    'secondary': '#45475a', 'secondary_fg': '#cdd6f4', 'secondary_hover': '#585b70',
    'disabled_bg': '#45475a', 'disabled_fg': '#6c7086',
}

_LIGHT_LATTE = {
    'bg': '#eff1f5', 'fg': '#4c4f69', 'fg_muted': '#6c6f85',
    'sidebar': '#e6e9ef', 'border': '#ccd0da',
    'hover': '#dce0e8', 'active': '#bcc0cc',
    'card': '#ffffff', 'input_bg': '#ffffff',
    'scrollbar': '#bcc0cc', 'scrollbar_hover': '#acb0be',
    'accent': '#1e66f5', 'accent_fg': '#ffffff',
    'accent_hover': '#4080f7', 'accent_press': '#1a5ce0',
    'danger': '#d20f39', 'danger_fg': '#ffffff', 'danger_hover': '#e03e5c',
    'success': '#40a02b', 'success_fg': '#ffffff', 'success_hover': '#56b343',
    'secondary': '#ccd0da', 'secondary_fg': '#4c4f69', 'secondary_hover': '#bcc0cc',
    'disabled_bg': '#dce0e8', 'disabled_fg': '#9ca0b0',
}

_LIGHT_GITHUB = {
    'bg': '#ffffff', 'fg': '#1f2328', 'fg_muted': '#656d76',
    'sidebar': '#f6f8fa', 'border': '#d1d9e0',
    'hover': '#eaeef2', 'active': '#ddf4ff',
    'card': '#ffffff', 'input_bg': '#ffffff',
    'scrollbar': '#d1d9e0', 'scrollbar_hover': '#afb8c1',
    'accent': '#0969da', 'accent_fg': '#ffffff',
    'accent_hover': '#0550ae', 'accent_press': '#033d8b',
    'danger': '#cf222e', 'danger_fg': '#ffffff', 'danger_hover': '#a40e26',
    'success': '#1a7f37', 'success_fg': '#ffffff', 'success_hover': '#2da44e',
    'secondary': '#f3f4f6', 'secondary_fg': '#1f2328', 'secondary_hover': '#eaeef2',
    'disabled_bg': '#f3f4f6', 'disabled_fg': '#8b949e',
}

_LIGHT_VSCODE = {
    'bg': '#f3f3f3', 'fg': '#333333', 'fg_muted': '#616161',
    'sidebar': '#e8e8e8', 'border': '#c8c8c8',
    'hover': '#e0e0e0', 'active': '#d6ebff',
    'card': '#ffffff', 'input_bg': '#ffffff',
    'scrollbar': '#c1c1c1', 'scrollbar_hover': '#a0a0a0',
    'accent': '#005fb8', 'accent_fg': '#ffffff',
    'accent_hover': '#0070d1', 'accent_press': '#004f9a',
    'danger': '#c72e42', 'danger_fg': '#ffffff', 'danger_hover': '#d44a5c',
    'success': '#388a34', 'success_fg': '#ffffff', 'success_hover': '#4caf50',
    'secondary': '#e1e1e1', 'secondary_fg': '#333333', 'secondary_hover': '#d4d4d4',
    'disabled_bg': '#e8e8e8', 'disabled_fg': '#a0a0a0',
}

_LIGHT_NORD = {
    'bg': '#eceff4', 'fg': '#2e3440', 'fg_muted': '#4c566a',
    'sidebar': '#e5e9f0', 'border': '#d8dee9',
    'hover': '#dde1e9', 'active': '#d2d8e4',
    'card': '#ffffff', 'input_bg': '#ffffff',
    'scrollbar': '#d8dee9', 'scrollbar_hover': '#c2c9d6',
    'accent': '#5e81ac', 'accent_fg': '#ffffff',
    'accent_hover': '#6e91bc', 'accent_press': '#4e719c',
    'danger': '#bf616a', 'danger_fg': '#ffffff', 'danger_hover': '#d08770',
    'success': '#a3be8c', 'success_fg': '#2e3440', 'success_hover': '#b3ce9c',
    'secondary': '#d8dee9', 'secondary_fg': '#2e3440', 'secondary_hover': '#c8ced9',
    'disabled_bg': '#dde1e9', 'disabled_fg': '#7b88a1',
}


# ═══════════════════════════════════════════════════════════════════════════════
# Pre-build themes (done once at import time)
# ═══════════════════════════════════════════════════════════════════════════════

THEMES = {
    'dark':         _build_theme(_DARK_CATPPUCCIN),
    'light-latte':  _build_theme(_LIGHT_LATTE),
    'light-github': _build_theme(_LIGHT_GITHUB),
    'light-vscode': _build_theme(_LIGHT_VSCODE),
    'light-nord':   _build_theme(_LIGHT_NORD),
    # Legacy alias — old "light" maps to Catppuccin Latte
    'light':        _build_theme(_LIGHT_LATTE),
}

# Theme display names for UI
THEME_OPTIONS = [
    ('dark',         '🌙 Dark — Catppuccin Mocha'),
    ('light-latte',  '☀️ Light — Catppuccin Latte'),
    ('light-github', '☀️ Light — GitHub'),
    ('light-vscode', '☀️ Light — VS Code'),
    ('light-nord',   '❄️ Light — Nord'),
]


def get_theme(name: str = "dark") -> str:
    """Return stylesheet for the given theme name."""
    return THEMES.get(name, THEMES['dark'])
