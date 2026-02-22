"""
VenvStudio - Qt Stylesheets
Modern dark and light themes
"""

DARK_THEME = """
QMainWindow, QDialog {
    background-color: #1e1e2e;
    color: #cdd6f4;
}

QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", "SF Pro Display", "Ubuntu", "Noto Color Emoji", sans-serif;
    font-size: 13px;
}

/* Sidebar */
#sidebar {
    background-color: #181825;
    border-right: 1px solid #313244;
}

#sidebar QPushButton {
    background-color: transparent;
    color: #cdd6f4;
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    text-align: left;
    font-size: 13px;
}

#sidebar QPushButton:hover {
    background-color: #313244;
}

#sidebar QPushButton:checked, #sidebar QPushButton[active="true"] {
    background-color: #45475a;
    color: #89b4fa;
    font-weight: bold;
}

/* Headers */
QLabel#header {
    font-size: 22px;
    font-weight: bold;
    color: #cdd6f4;
    padding: 8px 0;
}

QLabel#subheader {
    font-size: 14px;
    color: #a6adc8;
    padding: 4px 0;
}

/* Buttons */
QPushButton {
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
    border-radius: 8px;
    padding: 8px 20px;
    font-weight: bold;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #b4d0fb;
}

QPushButton:pressed {
    background-color: #74c7ec;
}

QPushButton:disabled {
    background-color: #45475a;
    color: #6c7086;
}

QPushButton#danger {
    background-color: #f38ba8;
    color: #1e1e2e;
}

QPushButton#danger:hover {
    background-color: #f5a3b8;
}

QPushButton#secondary {
    background-color: #45475a;
    color: #cdd6f4;
}

QPushButton#secondary:hover {
    background-color: #585b70;
}

QPushButton#success {
    background-color: #a6e3a1;
    color: #1e1e2e;
}

QPushButton#success:hover {
    background-color: #b8eab4;
}

/* Input Fields */
QLineEdit, QComboBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 2px solid #45475a;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: #89b4fa;
}

QLineEdit:focus, QComboBox:focus {
    border-color: #89b4fa;
}

QComboBox::drop-down {
    border: none;
    padding-right: 10px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #cdd6f4;
    margin-right: 10px;
}

QComboBox QAbstractItemView {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 8px;
    selection-background-color: #45475a;
}

/* Tables */
QTableWidget, QTreeWidget, QListWidget {
    background-color: #1e1e2e;
    alternate-background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 8px;
    gridline-color: #313244;
    selection-background-color: #45475a;
    selection-color: #cdd6f4;
}

QTableWidget::item, QTreeWidget::item, QListWidget::item {
    padding: 6px;
}

QHeaderView::section {
    background-color: #181825;
    color: #a6adc8;
    border: none;
    border-bottom: 2px solid #313244;
    padding: 8px;
    font-weight: bold;
}

/* Scrollbar */
QScrollBar:vertical {
    background-color: #1e1e2e;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #45475a;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #585b70;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: #1e1e2e;
    height: 10px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background-color: #45475a;
    border-radius: 5px;
    min-width: 30px;
}

/* GroupBox */
QGroupBox {
    border: 1px solid #313244;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
    color: #a6adc8;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #313244;
    border-radius: 8px;
    background-color: #1e1e2e;
}

QTabBar::tab {
    background-color: #181825;
    color: #a6adc8;
    border: none;
    padding: 10px 20px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #1e1e2e;
    color: #89b4fa;
    font-weight: bold;
}

QTabBar::tab:hover:!selected {
    background-color: #313244;
}

/* Progress Bar */
QProgressBar {
    background-color: #313244;
    border: none;
    border-radius: 6px;
    height: 8px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #89b4fa;
    border-radius: 6px;
}

/* Checkbox */
QCheckBox {
    spacing: 8px;
    color: #cdd6f4;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #45475a;
    border-radius: 4px;
    background-color: #313244;
}

QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
}

/* Tooltip */
QToolTip {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px;
}

/* StatusBar */
QStatusBar {
    background-color: #181825;
    color: #a6adc8;
    border-top: 1px solid #313244;
}

/* TextEdit / PlainTextEdit */
QTextEdit, QPlainTextEdit {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 8px;
    padding: 8px;
    font-family: "Cascadia Code", "Fira Code", "JetBrains Mono", "Consolas", monospace;
    font-size: 12px;
}

/* Menu */
QMenuBar {
    background-color: #181825;
    color: #cdd6f4;
    border-bottom: 1px solid #313244;
}

QMenuBar::item:selected {
    background-color: #313244;
}

QMenu {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 8px;
    padding: 4px;
}

QMenu::item:selected {
    background-color: #45475a;
    border-radius: 4px;
}

/* Splitter */
QSplitter::handle {
    background-color: #313244;
}

/* Card-like frames */
QFrame#card {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 12px;
    padding: 16px;
}
"""

LIGHT_THEME = """
QMainWindow, QDialog {
    background-color: #eff1f5;
    color: #4c4f69;
}

QWidget {
    background-color: #eff1f5;
    color: #4c4f69;
    font-family: "Segoe UI", "SF Pro Display", "Ubuntu", "Noto Color Emoji", sans-serif;
    font-size: 13px;
}

#sidebar {
    background-color: #e6e9ef;
    border-right: 1px solid #ccd0da;
}

#sidebar QPushButton {
    background-color: transparent;
    color: #4c4f69;
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    text-align: left;
    font-size: 13px;
}

#sidebar QPushButton:hover {
    background-color: #ccd0da;
}

#sidebar QPushButton:checked, #sidebar QPushButton[active="true"] {
    background-color: #bcc0cc;
    color: #1e66f5;
    font-weight: bold;
}

QLabel#header {
    font-size: 22px;
    font-weight: bold;
    color: #4c4f69;
    padding: 8px 0;
}

QLabel#subheader {
    font-size: 14px;
    color: #6c6f85;
    padding: 4px 0;
}

QPushButton {
    background-color: #1e66f5;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 8px 20px;
    font-weight: bold;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #4080f7;
}

QPushButton:pressed {
    background-color: #1a5ce0;
}

QPushButton:disabled {
    background-color: #ccd0da;
    color: #9ca0b0;
}

QPushButton#danger {
    background-color: #d20f39;
    color: #ffffff;
}

QPushButton#secondary {
    background-color: #ccd0da;
    color: #4c4f69;
}

QPushButton#success {
    background-color: #40a02b;
    color: #ffffff;
}

QLineEdit, QComboBox {
    background-color: #ffffff;
    color: #4c4f69;
    border: 2px solid #ccd0da;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
}

QLineEdit:focus, QComboBox:focus {
    border-color: #1e66f5;
}

QTableWidget, QTreeWidget, QListWidget {
    background-color: #ffffff;
    alternate-background-color: #eff1f5;
    color: #4c4f69;
    border: 1px solid #ccd0da;
    border-radius: 8px;
    gridline-color: #ccd0da;
    selection-background-color: #dce0e8;
    selection-color: #4c4f69;
}

QHeaderView::section {
    background-color: #e6e9ef;
    color: #6c6f85;
    border: none;
    border-bottom: 2px solid #ccd0da;
    padding: 8px;
    font-weight: bold;
}

QScrollBar:vertical {
    background-color: #eff1f5;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #ccd0da;
    border-radius: 5px;
    min-height: 30px;
}

QGroupBox {
    border: 1px solid #ccd0da;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
    color: #6c6f85;
}

QTabBar::tab {
    background-color: #e6e9ef;
    color: #6c6f85;
    border: none;
    padding: 10px 20px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #eff1f5;
    color: #1e66f5;
    font-weight: bold;
}

QProgressBar {
    background-color: #ccd0da;
    border: none;
    border-radius: 6px;
    height: 8px;
}

QProgressBar::chunk {
    background-color: #1e66f5;
    border-radius: 6px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #ccd0da;
    border-radius: 4px;
    background-color: #ffffff;
}

QCheckBox::indicator:checked {
    background-color: #1e66f5;
    border-color: #1e66f5;
}

QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    color: #4c4f69;
    border: 1px solid #ccd0da;
    border-radius: 8px;
    padding: 8px;
    font-family: "Cascadia Code", "Fira Code", "JetBrains Mono", "Consolas", monospace;
    font-size: 12px;
}

QStatusBar {
    background-color: #e6e9ef;
    color: #6c6f85;
    border-top: 1px solid #ccd0da;
}

QFrame#card {
    background-color: #ffffff;
    border: 1px solid #ccd0da;
    border-radius: 12px;
    padding: 16px;
}
"""


def get_theme(name: str = "dark") -> str:
    """Return stylesheet for the given theme name."""
    if name == "light":
        return LIGHT_THEME
    return DARK_THEME
