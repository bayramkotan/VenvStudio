"""
learn_install_dialog.py — LearnInstallDialog
Shown when user clicks "Install" on a Learn topic card. Asks which env to use.

Options:
  - Current selected env (default)
  - Default env (if set and different from current)
  - Pick from dropdown of all envs
  - Create a new env for this install

Returns a decision describing the target env (existing path OR new env spec).
"""
from __future__ import annotations
from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QComboBox, QLineEdit, QCheckBox, QFrame,
    QButtonGroup, QWidget, QSizePolicy,
)
from PySide6.QtCore import Qt


# Known pipx-friendly CLI apps — hint the user to use pipx for isolation
_PIPX_FRIENDLY = {
    "streamlit", "httpie", "http-prompt", "black", "ruff", "mypy",
    "poetry", "pre-commit", "pipenv", "rye", "uv", "pdm",
    "jupyter", "jupyterlab", "notebook",
    "ipython", "bpython", "ptpython",
    "cookiecutter", "copier",
    "awscli", "gcloud", "azure-cli",
    "youtube-dl", "yt-dlp",
    "pyinstaller", "py-spy",
    "icecream", "rich-cli",
}


class LearnInstallDecision:
    """Result returned by LearnInstallDialog."""

    MODE_EXISTING = "existing"
    MODE_NEW_VENV = "new_venv"
    MODE_PIPX = "pipx"

    def __init__(self, mode: str, env_name: str = "", env_path: Optional[Path] = None,
                 new_env_name: str = "", switch_after: bool = True):
        self.mode = mode                  # "existing" | "new_venv" | "pipx"
        self.env_name = env_name          # target existing env name
        self.env_path = env_path          # target existing env path (may be None)
        self.new_env_name = new_env_name  # for MODE_NEW_VENV
        self.switch_after = switch_after  # switch to Packages tab after install


class LearnInstallDialog(QDialog):
    """Ask user where to install packages requested from the Learn page."""

    def __init__(
        self,
        packages: List[str],
        envs: List[dict],          # each: {"name": str, "path": Path, "type": str, "python": str}
        current_env_name: str = "",
        default_env_name: str = "",
        colors: Optional[dict] = None,
        parent=None,
    ):
        super().__init__(parent)
        self._packages = packages
        self._envs = envs
        self._current = current_env_name
        self._default = default_env_name
        self._c = colors or self._default_colors()
        self.decision: Optional[LearnInstallDecision] = None  # set on accept

        self.setWindowTitle("Install Packages")
        self.setMinimumSize(560, 460)
        self._setup_ui()

    @staticmethod
    def _default_colors() -> dict:
        return {
            "bg": "#1e1e2e", "card": "#181825", "border": "#313244",
            "fg": "#cdd6f4", "fg_muted": "#a6adc8",
            "accent": "#89b4fa", "accent_fg": "#1e1e2e",
            "danger": "#f38ba8", "success": "#a6e3a1",
        }

    # ── UI ────────────────────────────────────────────────────────────

    def _setup_ui(self):
        c = self._c
        self.setStyleSheet(f"QDialog {{ background: {c['bg']}; color: {c['fg']}; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # ── Header ─────────────────────────────────────────────────
        header_lbl = QLabel(f"Install {len(self._packages)} package(s)")
        header_lbl.setStyleSheet(
            f"color: {c['fg']}; font-size: 18px; font-weight: bold; border: none;"
        )
        layout.addWidget(header_lbl)

        pkg_str = ", ".join(self._packages[:6])
        if len(self._packages) > 6:
            pkg_str += f", … (+{len(self._packages) - 6} more)"
        pkg_lbl = QLabel(pkg_str)
        pkg_lbl.setWordWrap(True)
        pkg_lbl.setStyleSheet(
            f"color: {c['accent']}; font-size: 14px; font-family: Consolas, monospace; "
            f"border: none; padding: 4px 0;"
        )
        layout.addWidget(pkg_lbl)

        # ── Pipx hint ──────────────────────────────────────────────
        self._is_pipx_friendly = any(
            p.split("[")[0].split("=")[0].split(">")[0].strip() in _PIPX_FRIENDLY
            for p in self._packages
        )
        if self._is_pipx_friendly:
            pipx_lbl = QLabel(
                "💡 One or more of these packages are standalone CLI tools. "
                "Consider installing with <b>pipx</b> for system-wide access "
                "without polluting a venv."
            )
            pipx_lbl.setWordWrap(True)
            pipx_lbl.setStyleSheet(
                f"color: {c['fg_muted']}; font-size: 13px; "
                f"background: {c['card']}; border: 1px solid {c['border']}; "
                f"border-radius: 6px; padding: 10px;"
            )
            layout.addWidget(pipx_lbl)

        # ── Choice header ──────────────────────────────────────────
        choice_lbl = QLabel("Where should we install?")
        choice_lbl.setStyleSheet(
            f"color: {c['fg']}; font-size: 14px; font-weight: bold; "
            f"border: none; padding-top: 6px;"
        )
        layout.addWidget(choice_lbl)

        # ── Options ────────────────────────────────────────────────
        self._group = QButtonGroup(self)

        # Radio: Current env
        if self._current:
            self.rb_current = QRadioButton(f"✔ Current env: {self._current}")
            self.rb_current.setStyleSheet(self._radio_style())
            self.rb_current.setChecked(True)
            self._group.addButton(self.rb_current, 0)
            layout.addWidget(self.rb_current)
        else:
            self.rb_current = None

        # Radio: Default env (if different)
        if self._default and self._default != self._current:
            self.rb_default = QRadioButton(f"⭐ Default env: {self._default}")
            self.rb_default.setStyleSheet(self._radio_style())
            self._group.addButton(self.rb_default, 1)
            if not self._current:
                self.rb_default.setChecked(True)
            layout.addWidget(self.rb_default)
        else:
            self.rb_default = None

        # Radio: Pick from dropdown
        pick_row = QHBoxLayout()
        self.rb_pick = QRadioButton("Pick an env:")
        self.rb_pick.setStyleSheet(self._radio_style())
        self._group.addButton(self.rb_pick, 2)
        pick_row.addWidget(self.rb_pick)

        self.env_dropdown = QComboBox()
        self.env_dropdown.setStyleSheet(
            f"QComboBox {{ background: {c['card']}; color: {c['fg']}; "
            f"border: 1px solid {c['border']}; border-radius: 4px; "
            f"padding: 4px 8px; font-size: 13px; min-width: 220px; }}"
        )
        for env in self._envs:
            label = f"{env['name']}  ({env.get('type', 'venv')}, Python {env.get('python', '?')})"
            self.env_dropdown.addItem(label, env)
        self.env_dropdown.currentIndexChanged.connect(self._on_dropdown_changed)
        pick_row.addWidget(self.env_dropdown, 1)
        layout.addLayout(pick_row)

        # Radio: Create new venv
        new_row = QHBoxLayout()
        self.rb_new = QRadioButton("➕ Create a new env:")
        self.rb_new.setStyleSheet(self._radio_style())
        self._group.addButton(self.rb_new, 3)
        new_row.addWidget(self.rb_new)

        self.new_name_input = QLineEdit()
        self.new_name_input.setPlaceholderText("e.g. ml-project")
        self.new_name_input.setStyleSheet(
            f"QLineEdit {{ background: {c['card']}; color: {c['fg']}; "
            f"border: 1px solid {c['border']}; border-radius: 4px; "
            f"padding: 4px 8px; font-size: 13px; min-width: 220px; }}"
        )
        self.new_name_input.textEdited.connect(lambda _: self.rb_new.setChecked(True))
        new_row.addWidget(self.new_name_input, 1)
        layout.addLayout(new_row)

        # Radio: pipx (only if friendly)
        if self._is_pipx_friendly:
            self.rb_pipx = QRadioButton("📦 Install as pipx app (isolated, system-wide)")
            self.rb_pipx.setStyleSheet(self._radio_style())
            self._group.addButton(self.rb_pipx, 4)
            layout.addWidget(self.rb_pipx)
        else:
            self.rb_pipx = None

        layout.addStretch()

        # ── Options row ────────────────────────────────────────────
        self.switch_check = QCheckBox("Switch to Packages tab after install")
        self.switch_check.setChecked(True)
        self.switch_check.setStyleSheet(
            f"QCheckBox {{ color: {c['fg_muted']}; font-size: 13px; }}"
        )
        layout.addWidget(self.switch_check)

        # ── Buttons ────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background: {c['border']}; max-height: 1px; border: none;")
        layout.addWidget(sep)

        btn_row = QHBoxLayout()

        # Copy Command button (left side — utility action)
        copy_btn = QPushButton("📋 Copy Command")
        copy_btn.setFixedHeight(34)
        copy_btn.setToolTip("Copy the install command to clipboard")
        copy_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {c['fg_muted']}; "
            f"border: 1px solid {c['border']}; border-radius: 6px; padding: 0 14px; "
            f"font-size: 13px; }} "
            f"QPushButton:hover {{ color: {c['accent']}; border-color: {c['accent']}; }}"
        )
        copy_btn.clicked.connect(self._on_copy_command)
        btn_row.addWidget(copy_btn)

        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(34)
        cancel_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {c['fg_muted']}; "
            f"border: 1px solid {c['border']}; border-radius: 6px; padding: 0 18px; "
            f"font-size: 13px; }} "
            f"QPushButton:hover {{ color: {c['fg']}; border-color: {c['accent']}; }}"
        )
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self.install_btn = QPushButton(f"⬇ Install to selected")
        self.install_btn.setFixedHeight(34)
        self.install_btn.setStyleSheet(
            f"QPushButton {{ background: {c['accent']}; color: {c['accent_fg']}; "
            f"border: none; border-radius: 6px; padding: 0 20px; "
            f"font-size: 13px; font-weight: bold; }} "
            f"QPushButton:hover {{ background: {c['accent']}dd; }}"
        )
        self.install_btn.clicked.connect(self._on_install_clicked)
        btn_row.addWidget(self.install_btn)

        layout.addLayout(btn_row)

        # Preselect dropdown to match current/default if available
        if self.env_dropdown.count():
            for i, env in enumerate(self._envs):
                if env["name"] == self._current:
                    self.env_dropdown.setCurrentIndex(i)
                    break

    def _radio_style(self) -> str:
        c = self._c
        return (
            f"QRadioButton {{ color: {c['fg']}; font-size: 14px; "
            f"padding: 6px 4px; border: none; }} "
            f"QRadioButton:hover {{ color: {c['accent']}; }}"
        )

    def _on_dropdown_changed(self, _idx):
        if self.rb_pick:
            self.rb_pick.setChecked(True)

    # ── Command building for Copy ─────────────────────────────────────

    def _build_install_command(self) -> str:
        """Build the shell install command based on current selection.

        Single-line form (no env activation) — user is expected to have the
        env active or run from an IDE that manages activation.
        """
        decision = self._build_decision()
        pkgs = " ".join(self._packages)

        if decision is None:
            # No valid selection → fall back to generic pip install
            return f"pip install {pkgs}"

        # New env → full two-step command
        if decision.mode == LearnInstallDecision.MODE_NEW_VENV:
            name = decision.new_env_name
            # Cross-platform friendly: generic create + pip install
            return (
                f"python -m venv {name}\n"
                f"# Activate it, then:\n"
                f"pip install {pkgs}"
            )

        # pipx → one line per package
        if decision.mode == LearnInstallDecision.MODE_PIPX:
            lines = [f"pipx install {pkg}" for pkg in self._packages]
            return "\n".join(lines)

        # MODE_EXISTING — look up env type from selected env
        env_name = decision.env_name
        env_type = "venv"
        for env in self._envs:
            if env.get("name") == env_name:
                env_type = env.get("type", "venv")
                break

        if env_type == "conda":
            return f"micromamba install -n {env_name} -c conda-forge {pkgs}"
        if env_type == "pipx":
            lines = [f"pipx install {pkg}" for pkg in self._packages]
            return "\n".join(lines)
        if env_type == "poetry":
            return f"poetry add {pkgs}"
        # Default: venv / uv → plain pip install (assumes env active)
        return f"pip install {pkgs}"

    def _on_copy_command(self):
        """Copy the generated install command to clipboard + status feedback."""
        from PySide6.QtWidgets import QApplication
        cmd = self._build_install_command()
        QApplication.clipboard().setText(cmd)

        # Toast-style feedback: reuse the copy button's text briefly
        sender = self.sender()
        if sender is not None:
            original_text = sender.text()
            sender.setText("✓ Copied!")
            sender.setEnabled(False)
            from PySide6.QtCore import QTimer
            QTimer.singleShot(
                1200,
                lambda: (sender.setText(original_text), sender.setEnabled(True)),
            )

    # ── Result handling ───────────────────────────────────────────────

    def _on_install_clicked(self):
        decision = self._build_decision()
        if decision is None:
            return  # validation failed
        self.decision = decision
        self.accept()

    def _build_decision(self) -> Optional[LearnInstallDecision]:
        checked = self._group.checkedButton()
        if checked is None:
            return None
        switch = self.switch_check.isChecked()

        # Current env
        if self.rb_current is not None and checked is self.rb_current:
            env = next((e for e in self._envs if e["name"] == self._current), None)
            return LearnInstallDecision(
                LearnInstallDecision.MODE_EXISTING,
                env_name=self._current,
                env_path=env["path"] if env else None,
                switch_after=switch,
            )

        # Default env
        if self.rb_default is not None and checked is self.rb_default:
            env = next((e for e in self._envs if e["name"] == self._default), None)
            return LearnInstallDecision(
                LearnInstallDecision.MODE_EXISTING,
                env_name=self._default,
                env_path=env["path"] if env else None,
                switch_after=switch,
            )

        # Pick from dropdown
        if checked is self.rb_pick:
            env = self.env_dropdown.currentData()
            if not env:
                return None
            return LearnInstallDecision(
                LearnInstallDecision.MODE_EXISTING,
                env_name=env["name"],
                env_path=env.get("path"),
                switch_after=switch,
            )

        # New venv
        if checked is self.rb_new:
            name = self.new_name_input.text().strip()
            if not name:
                self.new_name_input.setFocus()
                self.new_name_input.setStyleSheet(
                    self.new_name_input.styleSheet() +
                    " QLineEdit { border: 1px solid #f38ba8; }"
                )
                return None
            # Basic sanity: no spaces, no path separators
            if any(ch in name for ch in " /\\:*?\"<>|"):
                self.new_name_input.setFocus()
                return None
            # Duplicate check
            if any(e["name"] == name for e in self._envs):
                self.new_name_input.setFocus()
                return None
            return LearnInstallDecision(
                LearnInstallDecision.MODE_NEW_VENV,
                new_env_name=name,
                switch_after=switch,
            )

        # pipx
        if self.rb_pipx is not None and checked is self.rb_pipx:
            return LearnInstallDecision(
                LearnInstallDecision.MODE_PIPX,
                switch_after=switch,
            )

        return None
