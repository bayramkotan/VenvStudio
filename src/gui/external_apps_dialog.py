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

    installed      ->  Launch it
    not installed  ->  open the vendor's download page

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


def _detect(app_def) -> str:
    """Path to the app's executable if it is on this system, else "".

    Uses the same system_commands table the Launch tab uses, so a change
    there is picked up here without a second list to maintain.
    """
    import shutil
    from src.utils.platform_utils import get_platform
    cmds = app_def.get("system_commands", {})
    entry = cmds.get(get_platform()) or cmds.get("linux") or []
    if not entry:
        return ""
    exe = entry[0]
    # macOS entries are `open -a Something`; `open` always resolves and would
    # report every app as installed, so the app name is what matters there.
    if exe == "open" and len(entry) > 2:
        exe = entry[2]
        from pathlib import Path
        for _p in (Path("/Applications") / f"{exe}.app",
                   Path.home() / "Applications" / f"{exe}.app"):
            if _p.exists():
                return str(_p)
        return ""
    return shutil.which(exe) or ""


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
            "published in any conda channel. If one is already on this "
            "system it can be started from here; otherwise this opens the "
            "vendor's download page.")
        intro.setWordWrap(True)
        root.addWidget(intro)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        self._rows = QVBoxLayout(inner)
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        btns = QHBoxLayout()
        self.refresh_btn = QPushButton("\u21bb  Re-check")
        self.refresh_btn.setObjectName("secondary")
        self.refresh_btn.clicked.connect(self._fill)
        btns.addWidget(self.refresh_btn)
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
            found = _detect(app)
            row = QFrame()
            row.setFrameShape(QFrame.StyledPanel)
            rl = QVBoxLayout(row)

            title = QLabel(f"{app.get('icon', '')}  <b>{app['name']}</b>")
            title.setTextFormat(Qt.RichText)
            rl.addWidget(title)

            desc = QLabel(app.get("desc", ""))
            desc.setWordWrap(True)
            rl.addWidget(desc)

            state = QLabel(f"\u2705 Found: {found}" if found
                           else "\u2b07\ufe0f Not installed on this system")
            state.setWordWrap(True)
            rl.addWidget(state)

            # Why it is not installable is worth saying once, here, rather
            # than leaving the user to wonder why this window exists.
            note = app.get("install_note", "")
            if note:
                nl = QLabel(note)
                nl.setWordWrap(True)
                nl.setStyleSheet("color: palette(mid);")
                rl.addWidget(nl)

            act = QHBoxLayout()
            if found:
                b = QPushButton(f"\u25b6 Launch {app['name']}")
                b.clicked.connect(lambda _=None, a=app: self._launch(a))
            else:
                b = QPushButton(f"\u2b07\ufe0f Download {app['name']}")
                b.clicked.connect(lambda _=None, a=app: self._download(a))
            act.addWidget(b)
            act.addStretch()
            rl.addLayout(act)

            self._rows.addWidget(row)
        self._rows.addStretch()

    def _launch(self, app_def):
        import subprocess
        from src.utils.platform_utils import get_platform, subprocess_args
        cmds = app_def.get("system_commands", {})
        cmd = list(cmds.get(get_platform()) or cmds.get("linux") or [])
        if not cmd:
            QMessageBox.warning(self, app_def["name"],
                                "No launch command is defined for this "
                                "platform.")
            return
        try:
            _log.info(f"[External] launching {app_def['name']}: {cmd}")
            subprocess.Popen(cmd, **subprocess_args())
        except Exception as e:
            QMessageBox.warning(
                self, app_def["name"],
                f"{app_def['name']} could not be started:\n{e}")

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
