"""VenvStudio - Tools -> External Apps.

B107 (Bayram, 2026-09-09: "ya o zaman da bir anlami kalmaz ki. bunlari
kaldirip tools -> apps gibi bir menunun altina koyalim").

Four apps -- RStudio, DBeaver, jamovi and JASP -- used to sit on the Launch
tab claiming they could be installed. They cannot: measured with micromamba
2.9.0 on 2026-09-09, none of them exists in conda-forge, bioconda, defaults,
r or anaconda. `rstudio` alone exists in Anaconda's `defaults`, which needs a
licence for commercial use, so VenvStudio does not install from there.
Pressing Launch answered with the solver saying the package does not exist.

He was right that a card which only opens a download page has no business on
a tab about running things inside an environment. But removing them outright
would have cost something real: the card also DETECTED an app already on the
system and launched it. This window keeps that half and drops the pretence:

    B116 follow-up (Bayram, 2026-09-10): the detect-and-launch half was
    removed. It reported VS Code, Jan, Code::Blocks, GPT4All, jamovi and
    JASP as missing while all of them were installed, because the executable
    name was a guess -- on Windows most of these never reach PATH at all --
    and a launcher that cannot find installed software is worse than no
    launcher. What is left is honest: the download page, and the reason the
    application cannot be installed from here.

    Detection is worth doing properly later: registry lookups on Windows,
    .app bundles on macOS, .desktop files on Linux. Guessing an executable
    name is not that.

The definitions are NOT copied here. They come from PackagePanel's
app_definitions, filtered by `download_url`, so this window and the Launch
tab cannot disagree about what exists.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QWidget, QMessageBox,
)
from PySide6.QtCore import Qt

from src.utils.logger import get_logger

_log = get_logger("venvstudio.external_apps")


class ExternalAppsDialog(QDialog):
    """Tools -> External Apps."""

    def __init__(self, app_defs, parent=None):
        super().__init__(parent)
        self.setWindowTitle("\U0001f4ca  External Apps")
        # Qt.Window rather than an OR onto windowFlags(): a dialog that keeps
        # minimise but is not a real top-level window drags the main window
        # down with it on Windows.
        self.setWindowFlags(Qt.Window)
        self.resize(720, 520)
        self._apps = [a for a in app_defs if a.get("download_url")]

        root = QVBoxLayout(self)
        intro = QLabel(
            "Applications VenvStudio cannot install, because they are not "
            "published in any conda channel or on PyPI as the application "
            "itself.\n\n"
            "These open the vendor's download page. Detecting which of them "
            "are already on this machine is a separate job \u2014 the "
            "executable name is not the application name on Windows, and "
            "guessing it reported installed software as missing.")
        intro.setWordWrap(True)
        root.addWidget(intro)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        self._rows = QVBoxLayout(inner)
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        btns = QHBoxLayout()
        btns.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        btns.addWidget(close_btn)
        root.addLayout(btns)

        self._fill()

    def _fill(self):
        while self._rows.count():
            _it = self._rows.takeAt(0)
            if _it.widget():
                _it.widget().deleteLater()

        for app in self._apps:
            row = QFrame()
            row.setFrameShape(QFrame.StyledPanel)
            rl = QVBoxLayout(row)

            title = QLabel(f"{app.get('icon', '')}  <b>{app['name']}</b>")
            title.setTextFormat(Qt.RichText)
            rl.addWidget(title)

            desc = QLabel(app.get("desc", ""))
            desc.setWordWrap(True)
            rl.addWidget(desc)

            note = app.get("install_note", "")
            if note:
                nl = QLabel(note)
                nl.setWordWrap(True)
                nl.setStyleSheet("color: palette(mid);")
                rl.addWidget(nl)

            act = QHBoxLayout()
            b = QPushButton(f"\u2b07\ufe0f Download {app['name']}")
            b.clicked.connect(lambda _=None, a=app: self._download(a))
            act.addWidget(b)
            act.addStretch()
            rl.addLayout(act)

            self._rows.addWidget(row)
        self._rows.addStretch()

    def _download(self, app_def):
        url = app_def.get("download_url", "")
        if not url:
            return
        if QMessageBox.question(
                self, f"Download {app_def['name']}",
                f"Open the download page?\n\n{url}",
                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        from src.utils.platform_utils import open_url
        open_url(url)
