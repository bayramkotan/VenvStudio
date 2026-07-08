"""VenvStudio - Package Panel: Tab Builders Mixin
Installed/Catalog/Presets/Manual tab construction (moved from package_panel.py).
"""
import os
import sys
import subprocess
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout, QComboBox, QLineEdit,
    QTableWidget, QHeaderView, QTextEdit, QMenu,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from src.utils.i18n import tr
from src.utils.platform_utils import get_platform, get_python_executable, subprocess_args
from src.utils.constants import (
    PACKAGE_CATALOG, PRESETS, PRESET_DESCRIPTIONS, UI_TOOLTIPS,
)


class TabBuildersMixin:
    """Mixin for PackagePanel: Installed/Catalog/Presets/Manual tab construction."""

    def _create_installed_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)

        toolbar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Filter installed packages...")
        self.search_input.textChanged.connect(self._filter_installed)
        toolbar.addWidget(self.search_input, 1)

        refresh_btn = QPushButton(f"🔄 {tr('refresh')}")
        refresh_btn.setObjectName("secondary")
        refresh_btn.clicked.connect(self.refresh_packages)
        toolbar.addWidget(refresh_btn)

        self.update_btn = QPushButton(f"⬆️ {tr('check_outdated')}")
        self.update_btn.setObjectName("secondary")
        self.update_btn.clicked.connect(self._check_outdated)
        toolbar.addWidget(self.update_btn)

        self.uninstall_btn = QPushButton(f"🗑️ {tr('uninstall_selected')}")
        self.uninstall_btn.setObjectName("danger")
        self.uninstall_btn.clicked.connect(self._uninstall_selected)
        toolbar.addWidget(self.uninstall_btn)

        # Export dropdown button (in toolbar for visibility)
        export_btn = QPushButton("📤 Export ▾")
        export_btn.setObjectName("secondary")
        export_menu = QMenu(export_btn)
        export_menu.addAction("📄 requirements.txt", self._export_requirements)
        export_menu.addAction("🐳 Dockerfile", self._export_dockerfile)
        export_menu.addAction("🐳 docker-compose.yml", self._export_docker_compose)
        export_menu.addAction("📦 pyproject.toml", self._export_pyproject)
        export_menu.addAction("🐍 environment.yml (Conda)", self._export_conda_yml)
        export_menu.addSeparator()
        export_menu.addAction("📋 Copy to Clipboard", self._export_clipboard)
        export_btn.setMenu(export_menu)
        toolbar.addWidget(export_btn)

        import_btn = QPushButton("📥 Import")
        import_btn.setObjectName("secondary")
        import_btn.setToolTip("Import packages from requirements.txt")
        import_btn.clicked.connect(self._import_requirements)
        toolbar.addWidget(import_btn)

        layout.addLayout(toolbar)

        self.packages_table = QTableWidget()
        self.packages_table.setColumnCount(3)
        self.packages_table.setHorizontalHeaderLabels(["Package", "Version", ""])
        # B180: PySide6 6.10.2 + Python 3.13.x has a C-level enum→int
        # conversion bug that crashes ANY Qt enum call with the short
        # deprecated form (e.g. Qt.ScrollBarAsNeeded, QHeaderView.Stretch)
        # with `SystemError: longobject.c:1481`. The fix is to use the
        # explicit nested enum path (Qt.ScrollBarPolicy.ScrollBarAsNeeded,
        # QHeaderView.ResizeMode.Stretch) AND wrap in try/except for safety.
        try:
            _hdr = self.packages_table.horizontalHeader()
            _hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            _hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            _hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            self.packages_table.setColumnWidth(2, 40)
            _hdr.setStretchLastSection(False)
            self.packages_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.packages_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.packages_table.setAlternatingRowColors(True)
            self.packages_table.verticalHeader().setVisible(False)
            self.packages_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        except (SystemError, TypeError, AttributeError) as _e:
            try:
                from src.utils.logger import get_logger
                get_logger("venvstudio.qt").warning(
                    f"[B180] Installed table enum setup failed (PySide6/Python 3.13 compat): {_e} "
                    f"— table will use default Qt behaviour"
                )
            except Exception:
                pass
        self.packages_table.customContextMenuRequested.connect(self._pkg_table_context_menu)
        layout.addWidget(self.packages_table)

        bottom = QHBoxLayout()
        self.pkg_count_label = QLabel("0 packages")
        self.pkg_count_label.setStyleSheet("color: #a6adc8;")
        bottom.addWidget(self.pkg_count_label)
        bottom.addStretch()

        layout.addLayout(bottom)
        return widget

    def _create_catalog_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)

        cat_layout = QHBoxLayout()
        cat_label = QLabel("Category:")
        cat_layout.addWidget(cat_label)

        self.category_combo = QComboBox()
        self.category_combo.addItem(tr("all_categories"), "all")
        for cat_name in PACKAGE_CATALOG:
            self.category_combo.addItem(cat_name, cat_name)
        # Add custom categories from config
        from src.core.config_manager import ConfigManager
        try:
            _cfg = self.config if self.config else __import__("src.core.config_manager", fromlist=["ConfigManager"]).ConfigManager()
            custom_cats = _cfg.get("custom_categories", [])
            for c in custom_cats:
                name = c.get("name", "")
                icon = c.get("icon", "⭐")
                full = f"{icon} {name}"
                if full not in [self.category_combo.itemData(i) for i in range(self.category_combo.count())]:
                    self.category_combo.addItem(full, full)
        except Exception:
            pass
        if self.category_combo.findData("⭐ Custom") < 0:
            self.category_combo.addItem("⭐ Custom", "⭐ Custom")
        self.category_combo.currentIndexChanged.connect(self._populate_catalog)
        cat_layout.addWidget(self.category_combo, 1)

        self.catalog_search = QLineEdit()
        self.catalog_search.setPlaceholderText("🔍 Search catalog...")
        self.catalog_search.setFixedWidth(200)
        self.catalog_search.textChanged.connect(self._filter_catalog)
        cat_layout.addWidget(self.catalog_search)

        layout.addLayout(cat_layout)

        legend = QLabel("☑ installed  |  Check→install  Uncheck→remove")
        legend.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        self._legend_label = legend
        layout.addWidget(legend)

        self.catalog_table = QTableWidget()
        self.catalog_table.setColumnCount(5)
        self.catalog_table.setHorizontalHeaderLabels(["Install", "Package", "Description", "Category", "Links"])
        # B180: see Installed tab — same PySide6 6.10.2/Python 3.13 enum bug
        try:
            _hdr = self.catalog_table.horizontalHeader()
            _hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            self.catalog_table.setColumnWidth(0, 28)
            _hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            _hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            _hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            _hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
            self.catalog_table.setColumnWidth(4, 80)
            _hdr.setStretchLastSection(False)
            self.catalog_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        except (SystemError, TypeError, AttributeError) as _e:
            try:
                from src.utils.logger import get_logger
                get_logger("venvstudio.qt").warning(
                    f"[B180] catalog table enum setup failed: {_e}"
                )
            except Exception:
                pass
        self.catalog_table.setAlternatingRowColors(True)
        self.catalog_table.verticalHeader().setVisible(False)
        try:
            self.catalog_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        except (SystemError, TypeError, AttributeError):
            pass
        self.catalog_table.customContextMenuRequested.connect(self._catalog_table_context_menu)
        layout.addWidget(self.catalog_table)

        # Bottom: changes summary + Apply button
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        self.changes_label = QLabel("")
        self.changes_label.setStyleSheet(f"color: {self._c().get('warning', '#f9e2af')}; font-size: {self._c()['fs_small']}px;")
        bottom_layout.addWidget(self.changes_label)

        self.apply_btn = QPushButton("  ✅ Apply Changes  ")
        self.apply_btn.setObjectName("success")
        self.apply_btn.setFixedHeight(38)
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._apply_catalog_changes)
        bottom_layout.addWidget(self.apply_btn)

        layout.addLayout(bottom_layout)

        self._populate_catalog()
        return widget

    def reload_presets_tab(self):
        """Reload presets tab — called after settings saved to show new custom presets."""
        new_widget = self._create_presets_tab()
        new_label = f"⚡ {tr('presets')}"
        new_tooltip = UI_TOOLTIPS.get("tab_presets", "")

        # Update _tab_defs
        if hasattr(self, "_tab_defs"):
            for idx, (key, label, widget, tooltip) in enumerate(self._tab_defs):
                if key == "presets":
                    old_widget = widget
                    self._tab_defs[idx] = ("presets", new_label, new_widget, new_tooltip)
                    if old_widget:
                        old_widget.deleteLater()
                    break

        # Re-apply tab visibility (will rebuild tabs with new presets widget)
        self._update_tabs_for_env_type()
        self._update_preset_badges()

    def _create_presets_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        self._presets_grid = QGridLayout(container)
        self._presets_grid.setSpacing(12)
        self._presets_grid.setContentsMargins(12, 12, 12, 12)

        # Merge built-in + custom presets
        from src.core.config_manager import ConfigManager
        _custom_presets = self._get_config("custom_presets", {})
        _all_presets = {**PRESETS, **_custom_presets}

        self._preset_cards = {}
        row = 0
        for preset_name, packages in _all_presets.items():
            card = QFrame()
            card.setObjectName("card")
            card_layout = QVBoxLayout(card)

            # Header with name + installed badge
            header = QHBoxLayout()
            name_label = QLabel(preset_name)
            name_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
            header.addWidget(name_label, 1)

            badge = QLabel("")
            badge.setStyleSheet(f"color: {self._c()['success']}; font-size: {self._c()['fs_tiny']}px; font-weight: bold;")
            header.addWidget(badge)
            card_layout.addLayout(header)

            # Educational: Preset description — explains what this preset is for
            preset_desc = PRESET_DESCRIPTIONS.get(preset_name, "")
            if preset_desc:
                desc_label = QLabel(preset_desc)
                desc_label.setWordWrap(True)
                desc_label.setStyleSheet(
                    f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px; font-style: italic; "
                    "padding: 4px 0px; line-height: 1.3;"
                )
                card_layout.addWidget(desc_label)

            pkg_text = ", ".join(packages)
            pkg_label = QLabel(pkg_text)
            pkg_label.setWordWrap(True)
            pkg_label.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_small']}px;")
            card_layout.addWidget(pkg_label)

            install_btn = QPushButton(f"{tr('install')} ({len(packages)} packages)")
            install_btn.setObjectName("success")
            install_btn.setToolTip(f"Install all {len(packages)} packages in this preset into the selected environment")
            install_btn.clicked.connect(
                lambda checked, pkgs=packages, name=preset_name: self._install_packages(pkgs, hint_name=name)
            )
            card_layout.addWidget(install_btn)

            uninstall_btn = QPushButton(f"🗑 {tr('uninstall') if tr('uninstall') != 'uninstall' else 'Uninstall'}")
            uninstall_btn.setObjectName("danger")
            uninstall_btn.setVisible(False)
            uninstall_btn.setToolTip("Remove all packages in this preset from the selected environment")
            uninstall_btn.clicked.connect(
                lambda checked, pkgs=packages, name=preset_name: self._uninstall_preset(pkgs, name)
            )
            card_layout.addWidget(uninstall_btn)

            copy_btn = QPushButton(f"📋 {tr('copy_command')}")
            copy_btn.setObjectName("secondary")
            copy_btn._preset_packages = packages  # store for dynamic tooltip update
            copy_btn.clicked.connect(
                lambda checked, pkgs=packages: self._copy_preset_command(pkgs)
            )
            card_layout.addWidget(copy_btn)

            self._preset_cards[preset_name] = {
                "badge": badge,
                "install_btn": install_btn,
                "uninstall_btn": uninstall_btn,
                "copy_btn": copy_btn,
                "packages": packages,
            }

            self._presets_grid.addWidget(card, row // 2, row % 2)
            row += 1

        self._presets_grid.setRowStretch(row // 2 + 1, 1)
        scroll.setWidget(container)
        return scroll

    def _update_preset_badges(self):
        """Update 'Installed' badge on presets."""
        if not hasattr(self, '_preset_cards'):
            return

        # Normalize installed names once
        if self.installed_package_names:
            normalized_installed = set()
            for p in self.installed_package_names:
                normalized_installed.add(p.lower().replace("-", "_").replace(".", "_"))
        else:
            normalized_installed = set()

        for preset_name, info in self._preset_cards.items():
            packages = info["packages"]
            badge = info["badge"]
            install_btn = info["install_btn"]
            uninstall_btn = info.get("uninstall_btn")

            if not normalized_installed:
                badge.setText("")
                install_btn.setText(f"{tr('install')} ({len(packages)} packages)")
                install_btn.setEnabled(True)
                install_btn.setObjectName("success")
                install_btn.setStyleSheet("")
                if uninstall_btn:
                    uninstall_btn.setVisible(False)
                continue

            installed_count = sum(
                1 for p in packages
                if p.lower().replace("-", "_").replace(".", "_") in normalized_installed
            )

            if installed_count == len(packages):
                badge.setText("✅ Installed")
                badge.setStyleSheet(f"color: {self._c()['success']}; font-size: {self._c()['fs_small']}px; font-weight: bold;")
                install_btn.setText(f"✅ {tr('installed') if tr('installed') != 'installed' else 'Installed'}")
                install_btn.setEnabled(False)
                # B183: was hardcoded "background:#313244; color:#a6e3a1"
                # (Catppuccin Mocha surface + pastel green) which stayed
                # dark on light themes. Use palette `secondary` (slightly
                # darker than card) + `success` (theme's "good" colour).
                _bg = self._c().get("secondary", "#313244")
                _fg = self._c().get("success", "#a6e3a1")
                install_btn.setStyleSheet(
                    f"background-color: {_bg}; color: {_fg}; "
                    f"font-weight: bold; border: 1px solid {self._c().get('border', _bg)}; "
                    f"border-radius: 6px; padding: 6px 12px;"
                )
                if uninstall_btn:
                    uninstall_btn.setVisible(True)
            elif installed_count > 0:
                badge.setText(f"⚡ {installed_count}/{len(packages)}")
                badge.setStyleSheet(f"color: {self._c().get('warning', '#f9e2af')}; font-size: {self._c()['fs_small']}px; font-weight: bold;")
                remaining = len(packages) - installed_count
                install_btn.setText(f"{tr('install')} ({remaining} remaining)")
                install_btn.setEnabled(True)
                install_btn.setObjectName("success")
                install_btn.setStyleSheet("")
                if uninstall_btn:
                    uninstall_btn.setVisible(True)
            else:
                badge.setText("")
                install_btn.setText(f"{tr('install')} ({len(packages)} packages)")
                install_btn.setEnabled(True)
                install_btn.setObjectName("success")
                install_btn.setStyleSheet("")
                if uninstall_btn:
                    uninstall_btn.setVisible(False)

    def _create_manual_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)

        self.manual_info_label = QLabel(
            "Enter package names separated by spaces or newlines.\n"
            "You can specify versions like: numpy==1.24.0 or pandas>=2.0"
        )
        self.manual_info_label.setObjectName("subheader")
        self.manual_info_label.setWordWrap(True)
        layout.addWidget(self.manual_info_label)

        self.manual_input = QTextEdit()
        self.manual_input.setPlaceholderText(
            "numpy pandas matplotlib\nscikit-learn==1.3.0\nrequests>=2.28"
        )
        layout.addWidget(self.manual_input)

        btn_layout = QHBoxLayout()

        copy_cmd_btn = QPushButton("📋 Copy Command")
        copy_cmd_btn.setObjectName("secondary")
        copy_cmd_btn.setToolTip("Copy the install command to clipboard")
        copy_cmd_btn.clicked.connect(self._copy_install_command)
        btn_layout.addWidget(copy_cmd_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("secondary")
        clear_btn.clicked.connect(self.manual_input.clear)
        btn_layout.addWidget(clear_btn)

        btn_layout.addStretch()

        install_btn = QPushButton("⚡ Install Packages")
        install_btn.setObjectName("success")
        install_btn.clicked.connect(self._install_manual)
        btn_layout.addWidget(install_btn)

        layout.addLayout(btn_layout)

        self.output_log = QTextEdit()
        self.output_log.setReadOnly(True)
        self.output_log.setMaximumHeight(200)
        self.output_log.setPlaceholderText("Installation output will appear here...")
        self.output_log.setStyleSheet(
            f"QTextEdit {{ background-color: {self._c()['card']}; color: {self._c()['fg']}; "
            f"font-family: 'Consolas', 'Courier New', monospace; font-size: {self._c()['fs_small']}px; "
            f"border: 1px solid {self._c()['border']}; border-radius: 4px; padding: 4px; }}"
        )
        layout.addWidget(self.output_log)

        # Copy log button
        copy_log_row = QHBoxLayout()
        self._copy_log_btn = QPushButton("📋 Copy Log")
        self._copy_log_btn.setObjectName("secondary")
        self._copy_log_btn.setFixedHeight(26)
        self._copy_log_btn.clicked.connect(self._copy_output_log)
        copy_log_row.addWidget(self._copy_log_btn)
        copy_log_row.addStretch()
        layout.addLayout(copy_log_row)

        return widget

