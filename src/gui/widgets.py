"""VenvStudio - Shared GUI Widgets
Small reusable widget/delegate classes used across multiple GUI modules
(moved from main_window.py).
"""
from PySide6.QtWidgets import QStyledItemDelegate, QPushButton
from PySide6.QtCore import Qt


class PathElideMiddleDelegate(QStyledItemDelegate):
    """
    Renders a table cell's text with middle-elision (e.g. ``C:\\Users\\…\\pppp-py3.13``)
    instead of the default right-elision Qt applies to QTableWidgetItem.

    Used for the Path column of the environment table where Poetry / pipx
    paths are long and the meaningful part (env name) is at the end, while
    the drive letter / Linux root at the start is also useful for context.
    The full path is preserved in the item's tooltip and accessible via
    ``item.toolTip()`` / ``item.text()`` regardless of how it's drawn.
    """
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        # Replace the text with a middle-elided version so Qt's normal
        # painter draws bold/foreground/selection like every other column.
        text = option.text
        if not text:
            return
        # Reserve a small margin (matches the QSS ::item padding 8px 12px)
        # so the ellipsis doesn't kiss the cell border.
        avail = max(0, option.rect.width() - 24)
        if avail <= 0:
            return
        option.text = option.fontMetrics.elidedText(text, Qt.ElideMiddle, avail)
        option.textElideMode = Qt.ElideMiddle


class SidebarButton(QPushButton):
    """Custom sidebar navigation button."""

    def __init__(self, text, icon_text="", parent=None):
        display = f"  {icon_text}  {text}" if icon_text else f"  {text}"
        super().__init__(display, parent)
        self.setCheckable(True)
        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)




