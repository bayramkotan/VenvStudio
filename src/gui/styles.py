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


def _build_theme(c: dict, font_family: str = "", font_size: int = 13,
                 primary_family: str = "", primary_size: int = 22,
                 tertiary_family: str = "", tertiary_size: int = 11) -> str:
    """Build a complete QSS stylesheet from a color palette dict.
    3-level font system: primary (headers), secondary (base), tertiary (small).
    """
    _fallback = '"Segoe UI", "SF Pro Display", "Ubuntu", sans-serif'

    def _resolve_font(family):
        if not family:
            return _fallback
        if '"' not in family:
            return f'"{family}", {_fallback}'
        return family

    font_family = _resolve_font(font_family)          # secondary = base
    primary_family = _resolve_font(primary_family)     # headers
    tertiary_family = _resolve_font(tertiary_family)   # small text

    # Font sizes
    fs_header = primary_size                              # 22px default
    fs_subheader = max(primary_size - 8, font_size + 1)   # 14px default
    fs_base = font_size                                   # 13px default
    fs_small = max(tertiary_size, 8)                      # 11px default
    fs_tiny = max(tertiary_size, 8)                        # 11px default

    _stylesheet = f"""
/* ── Base ── */
QMainWindow, QDialog {{
    background-color: {c['bg']};
    color: {c['fg']};
}}

QWidget {{
    background-color: {c['bg']};
    color: {c['fg']};
    font-family: {font_family};
    font-size: {font_size}px;
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
    font-size: {font_size}px;
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
    font-family: {primary_family};
    font-size: {fs_header}px;
    font-weight: bold;
    color: {c['fg']};
    padding: 8px 0;
}}

QLabel#subheader {{
    font-family: {primary_family};
    font-size: {fs_subheader}px;
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
    font-size: {font_size}px;
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
    font-size: {font_size}px;
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
    margin-top: -1px;
}}

QTabBar::tab {{
    background-color: {c['sidebar']};
    color: {c['fg_muted']};
    border: 1px solid {c['border']};
    border-bottom: 2px solid {c['border']};
    padding: 10px 20px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background-color: {c['bg']};
    color: {c['accent']};
    font-weight: bold;
    border-bottom: 3px solid {c['accent']};
}}

QTabBar::tab:hover:!selected {{
    background-color: {c['hover']};
    color: {c['fg']};
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
    padding: 8px 12px;
    min-height: 18px;
    font-size: {font_size}px;
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
    font-size: {fs_small}px;
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

    # ── B63: Linux input height fix ────────────────────────────────────────
    # On Linux, Qt uses a different font metrics engine (fontconfig/freetype)
    # which results in QLineEdit / QComboBox / QSpinBox being rendered shorter
    # than on Windows. Enforce a comfortable minimum height platform-wide.
    import sys as _sys
    if _sys.platform == "linux":
        _linux_input_height = max(font_size + 18, 32)   # scales with font size
        _linux_text_height  = max(font_size + 16, 28)
        _stylesheet = _stylesheet + f"""
/* ── Linux input height fix (B63) ── */
QLineEdit, QComboBox {{
    min-height: {_linux_input_height}px;
    padding-top: 4px;
    padding-bottom: 4px;
}}
QSpinBox {{
    min-height: {_linux_input_height}px;
    padding-top: 4px;
    padding-bottom: 4px;
}}
QTextEdit, QPlainTextEdit {{
    min-height: {_linux_text_height * 3}px;
}}
QComboBox::drop-down {{
    min-height: {_linux_input_height}px;
}}
"""
    return _stylesheet


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

_DARK_DRACULA = {
    'bg': '#282a36', 'fg': '#f8f8f2', 'fg_muted': '#6272a4',
    'sidebar': '#21222c', 'border': '#44475a',
    'hover': '#44475a', 'active': '#44475a',
    'card': '#282a36', 'input_bg': '#44475a',
    'scrollbar': '#44475a', 'scrollbar_hover': '#6272a4',
    'accent': '#bd93f9', 'accent_fg': '#282a36',
    'accent_hover': '#caa9fa', 'accent_press': '#a679f8',
    'danger': '#ff5555', 'danger_fg': '#f8f8f2', 'danger_hover': '#ff7777',
    'success': '#50fa7b', 'success_fg': '#282a36', 'success_hover': '#70fa93',
    'secondary': '#44475a', 'secondary_fg': '#f8f8f2', 'secondary_hover': '#6272a4',
    'disabled_bg': '#44475a', 'disabled_fg': '#6272a4',
}

_DARK_TOKYO_NIGHT = {
    'bg': '#1a1b26', 'fg': '#c0caf5', 'fg_muted': '#565f89',
    'sidebar': '#16161e', 'border': '#292e42',
    'hover': '#292e42', 'active': '#364a82',
    'card': '#1a1b26', 'input_bg': '#292e42',
    'scrollbar': '#292e42', 'scrollbar_hover': '#364a82',
    'accent': '#7aa2f7', 'accent_fg': '#1a1b26',
    'accent_hover': '#90b4f8', 'accent_press': '#6690f6',
    'danger': '#f7768e', 'danger_fg': '#1a1b26', 'danger_hover': '#f98ba0',
    'success': '#9ece6a', 'success_fg': '#1a1b26', 'success_hover': '#b0d880',
    'secondary': '#292e42', 'secondary_fg': '#c0caf5', 'secondary_hover': '#364a82',
    'disabled_bg': '#292e42', 'disabled_fg': '#565f89',
}

_DARK_ONE_DARK = {
    'bg': '#282c34', 'fg': '#abb2bf', 'fg_muted': '#5c6370',
    'sidebar': '#21252b', 'border': '#3e4451',
    'hover': '#2c313c', 'active': '#3e4451',
    'card': '#282c34', 'input_bg': '#3e4451',
    'scrollbar': '#3e4451', 'scrollbar_hover': '#4b5263',
    'accent': '#61afef', 'accent_fg': '#282c34',
    'accent_hover': '#7bbef1', 'accent_press': '#4d9edd',
    'danger': '#e06c75', 'danger_fg': '#282c34', 'danger_hover': '#e88891',
    'success': '#98c379', 'success_fg': '#282c34', 'success_hover': '#a8cf8d',
    'secondary': '#3e4451', 'secondary_fg': '#abb2bf', 'secondary_hover': '#4b5263',
    'disabled_bg': '#3e4451', 'disabled_fg': '#5c6370',
}

_DARK_GRUVBOX = {
    'bg': '#282828', 'fg': '#ebdbb2', 'fg_muted': '#a89984',
    'sidebar': '#1d2021', 'border': '#3c3836',
    'hover': '#3c3836', 'active': '#504945',
    'card': '#282828', 'input_bg': '#3c3836',
    'scrollbar': '#504945', 'scrollbar_hover': '#665c54',
    'accent': '#83a598', 'accent_fg': '#282828',
    'accent_hover': '#9ab5a8', 'accent_press': '#689d8d',
    'danger': '#fb4934', 'danger_fg': '#282828', 'danger_hover': '#fc6355',
    'success': '#b8bb26', 'success_fg': '#282828', 'success_hover': '#c8cb48',
    'secondary': '#504945', 'secondary_fg': '#ebdbb2', 'secondary_hover': '#665c54',
    'disabled_bg': '#3c3836', 'disabled_fg': '#7c6f64',
}

_DARK_SOLARIZED = {
    'bg': '#002b36', 'fg': '#839496', 'fg_muted': '#657b83',
    'sidebar': '#073642', 'border': '#073642',
    'hover': '#073642', 'active': '#0d4f63',
    'card': '#002b36', 'input_bg': '#073642',
    'scrollbar': '#073642', 'scrollbar_hover': '#0d4f63',
    'accent': '#268bd2', 'accent_fg': '#fdf6e3',
    'accent_hover': '#3a9dde', 'accent_press': '#1a79be',
    'danger': '#dc322f', 'danger_fg': '#fdf6e3', 'danger_hover': '#e84d4a',
    'success': '#859900', 'success_fg': '#fdf6e3', 'success_hover': '#9ab100',
    'secondary': '#073642', 'secondary_fg': '#839496', 'secondary_hover': '#0d4f63',
    'disabled_bg': '#073642', 'disabled_fg': '#586e75',
}

_DARK_MATERIAL = {
    'bg': '#212121', 'fg': '#eeffff', 'fg_muted': '#546e7a',
    'sidebar': '#1a1a1a', 'border': '#2d2d2d',
    'hover': '#2d2d2d', 'active': '#3d3d3d',
    'card': '#212121', 'input_bg': '#2d2d2d',
    'scrollbar': '#3d3d3d', 'scrollbar_hover': '#546e7a',
    'accent': '#82aaff', 'accent_fg': '#212121',
    'accent_hover': '#9ab8ff', 'accent_press': '#6a8eee',
    'danger': '#f07178', 'danger_fg': '#212121', 'danger_hover': '#f48a90',
    'success': '#c3e88d', 'success_fg': '#212121', 'success_hover': '#cfed9e',
    'secondary': '#2d2d2d', 'secondary_fg': '#eeffff', 'secondary_hover': '#3d3d3d',
    'disabled_bg': '#2d2d2d', 'disabled_fg': '#546e7a',
}

_LIGHT_SOLARIZED = {
    'bg': '#fdf6e3', 'fg': '#657b83', 'fg_muted': '#93a1a1',
    'sidebar': '#eee8d5', 'border': '#ddd6bf',
    'hover': '#e8e2cf', 'active': '#cfc9b8',
    'card': '#fdf6e3', 'input_bg': '#ffffff',
    'scrollbar': '#ddd6bf', 'scrollbar_hover': '#ccc5aa',
    'accent': '#268bd2', 'accent_fg': '#fdf6e3',
    'accent_hover': '#3a9dde', 'accent_press': '#1a79be',
    'danger': '#dc322f', 'danger_fg': '#fdf6e3', 'danger_hover': '#e84d4a',
    'success': '#859900', 'success_fg': '#fdf6e3', 'success_hover': '#9ab100',
    'secondary': '#ddd6bf', 'secondary_fg': '#657b83', 'secondary_hover': '#ccc5aa',
    'disabled_bg': '#eee8d5', 'disabled_fg': '#93a1a1',
}

_DARK_ROSE_PINE = {
    'bg': '#191724', 'fg': '#e0def4', 'fg_muted': '#6e6a86',
    'sidebar': '#1f1d2e', 'border': '#26233a',
    'hover': '#26233a', 'active': '#403d52',
    'card': '#191724', 'input_bg': '#26233a',
    'scrollbar': '#403d52', 'scrollbar_hover': '#524f67',
    'accent': '#c4a7e7', 'accent_fg': '#191724',
    'accent_hover': '#d2b8eb', 'accent_press': '#b596e3',
    'danger': '#eb6f92', 'danger_fg': '#191724', 'danger_hover': '#ef87a6',
    'success': '#9ccfd8', 'success_fg': '#191724', 'success_hover': '#aad8e0',
    'secondary': '#26233a', 'secondary_fg': '#e0def4', 'secondary_hover': '#403d52',
    'disabled_bg': '#26233a', 'disabled_fg': '#6e6a86',
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
# Color palette registry (themes built on demand with font params)
# ═══════════════════════════════════════════════════════════════════════════════

_PALETTES = {
    'dark':              _DARK_CATPPUCCIN,
    'dark-dracula':      _DARK_DRACULA,
    'dark-tokyo-night':  _DARK_TOKYO_NIGHT,
    'dark-one-dark':     _DARK_ONE_DARK,
    'dark-gruvbox':      _DARK_GRUVBOX,
    'dark-solarized':    _DARK_SOLARIZED,
    'dark-material':     _DARK_MATERIAL,
    'dark-rose-pine':    _DARK_ROSE_PINE,
    'light-latte':       _LIGHT_LATTE,
    'light-github':      _LIGHT_GITHUB,
    'light-vscode':      _LIGHT_VSCODE,
    'light-nord':        _LIGHT_NORD,
    'light-solarized':   _LIGHT_SOLARIZED,
    'light':             _LIGHT_LATTE,
}

THEME_OPTIONS = [
    # Dark
    ('dark',             '🌙 Dark — Catppuccin Mocha'),
    ('dark-dracula',     '🧛 Dark — Dracula'),
    ('dark-tokyo-night', '🗼 Dark — Tokyo Night'),
    ('dark-one-dark',    '⚛️ Dark — One Dark'),
    ('dark-gruvbox',     '🪵 Dark — Gruvbox'),
    ('dark-solarized',   '🌊 Dark — Solarized'),
    ('dark-material',    '🎨 Dark — Material'),
    ('dark-rose-pine',   '🌹 Dark — Rosé Pine'),
    # Light
    ('light-latte',      '☀️ Light — Catppuccin Latte'),
    ('light-github',     '🐙 Light — GitHub'),
    ('light-vscode',     '💙 Light — VS Code'),
    ('light-nord',       '❄️ Light — Nord'),
    ('light-solarized',  '🌞 Light — Solarized'),
]


def get_theme(name: str = "dark", font_family: str = "", font_size: int = 13,
              primary_family: str = "", primary_size: int = 22,
              tertiary_family: str = "", tertiary_size: int = 11) -> str:
    """Return stylesheet for the given theme name with 3-level font settings."""
    palette = _PALETTES.get(name, _PALETTES['dark'])
    return _build_theme(palette, font_family=font_family, font_size=font_size,
                        primary_family=primary_family, primary_size=primary_size,
                        tertiary_family=tertiary_family, tertiary_size=tertiary_size)


def get_colors(name: str = "dark", font_size: int = 13,
               primary_size: int = 22, tertiary_size: int = 11) -> dict:
    """Return the color palette dict for the given theme name.
    Use this in widgets that apply inline styles.
    Includes font size hierarchy values.
    """
    palettes = {
        'dark':             _DARK_CATPPUCCIN,
        'dark-dracula':     _DARK_DRACULA,
        'dark-tokyo-night': _DARK_TOKYO_NIGHT,
        'dark-one-dark':    _DARK_ONE_DARK,
        'dark-gruvbox':     _DARK_GRUVBOX,
        'dark-solarized':   _DARK_SOLARIZED,
        'dark-material':    _DARK_MATERIAL,
        'dark-rose-pine':   _DARK_ROSE_PINE,
        'light-latte':      _LIGHT_LATTE,
        'light-github':     _LIGHT_GITHUB,
        'light-vscode':     _LIGHT_VSCODE,
        'light-nord':       _LIGHT_NORD,
        'light-solarized':  _LIGHT_SOLARIZED,
        'light':            _LIGHT_LATTE,
    }
    result = palettes.get(name, _DARK_CATPPUCCIN).copy()
    result['fs_header'] = primary_size
    result['fs_subheader'] = max(primary_size - 8, font_size + 1)
    result['fs_base'] = font_size
    result['fs_small'] = max(tertiary_size, 8)
    result['fs_tiny'] = max(tertiary_size, 8)
    return result
