# Code Map — src

86 files · 55,767 lines · 1133 definitions

## What to look at

Nothing here is an error on its own. Static analysis cannot see `getattr` calls, Qt signal connections or anything dispatched through a string, so judge each one.

### ⚠️ Defined more than once, and the copies DIFFER (6)

A fix written to one of these does not reach the other.

- **banner_error** (function) — `core/venv_manager_common.py`:41 · `gui/env_dialog.py`:24 · `gui/env_dialog_create.py`:19 · `utils/logger.py`:578
- **banner_start** (function) — `core/venv_manager_common.py`:39 · `gui/env_dialog.py`:22 · `gui/env_dialog_create.py`:17 · `utils/logger.py`:566
- **banner_success** (function) — `core/venv_manager_common.py`:40 · `gui/env_dialog.py`:23 · `gui/env_dialog_create.py`:18 · `utils/logger.py`:572
- **banner_warning** (function) — `core/venv_manager_common.py`:42 · `utils/logger.py`:584
- **main** (function) — `main.py`:21 · `src_main.py`:21
- **subprocess_args** (function) — `gui/env_dialog.py`:30 · `gui/env_dialog_create.py`:25 · `gui/env_dialog_tools.py`:10 · `gui/env_dialog_ui.py`:17 · `utils/platform_utils.py`:49

### Defined more than once, copies identical (4)

- **NoScrollComboBox** (class) — `gui/settings_common.py`:11 · `gui/settings_page.py`:83
- **NoScrollComboBox.focusOutEvent** (method) — `gui/settings_common.py`:29 · `gui/settings_page.py`:101
- **NoScrollComboBox.mousePressEvent** (method) — `gui/settings_common.py`:19 · `gui/settings_page.py`:91
- **NoScrollComboBox.wheelEvent** (method) — `gui/settings_common.py`:23 · `gui/settings_page.py`:95

### ⚠️ Class method hides a base's method (2)

The class's own copy wins. Editing the base changes nothing, and nothing warns you.

- `SettingsPage._setup_toolchain_ui_section` in `gui/settings_page.py` hides `ToolchainMixin._setup_toolchain_ui_section` in `gui/settings_toolchain.py`
- `SettingsPage._setup_cliops_section` in `gui/settings_page.py` hides `ToolchainMixin._setup_cliops_section` in `gui/settings_toolchain.py`

### ⚠️ Same data under two names (1)

- `gui/settings_common.py`:LANGUAGES · `gui/settings_page.py`:LANGUAGES
  - `{'en': 'English', 'tr': 'Türkçe', 'de': 'Deutsch', 'fr': 'Français', '...`

### No static caller found (59)

Possibly dead — or reached by a signal, a `getattr`, or a name built at runtime. Check before removing anything.

- `core/code_map.py` — _Reader.visit_Import
- `core/code_map.py` — _Reader.visit_ImportFrom
- `core/code_map.py` — _Reader.visit_ClassDef
- `core/code_map.py` — _Reader.visit_Assign
- `core/micromamba_installer.py` — is_conda_env
- `core/pip_manager.py` — PipManager._check_ssl
- `core/pip_manager.py` — PipManager.search_pypi
- `core/pip_manager.py` — PipManager.get_package_info
- `core/system_tools_installer.py` — RInstaller
- `core/system_tools_installer.py` — RStudioInstaller
- `core/system_tools_installer.py` — OllamaInstaller
- `core/system_tools_installer.py` — DBeaverInstaller
- `core/system_tools_installer.py` — JamoviInstaller
- `core/system_tools_installer.py` — JASPInstaller
- `core/tool_registry.py` — ToolRegistry.get_scope
- `core/tool_registry.py` — ToolRegistry.get_version
- `core/tool_registry.py` — ToolRegistry.get_info
- `core/tool_registry.py` — ToolRegistry.list_all
- `core/tool_registry.py` — ToolRegistry.update_version
- `core/venv_manager.py` — VenvInfo.to_dict
- `core/venv_manager.py` — VenvManager.invalidate_cache_by_name
- `core/venv_manager_cache.py` — _CacheMixin.remove_custom_location
- `core/venv_manager_rename.py` — _RenameMixin.set_poetry_display_name
- `gui/env_dialog_create.py` — EnvCreateMixin
- `gui/env_dialog_tools.py` — EnvDialogToolsMixin
- `gui/env_dialog_ui.py` — EnvDialogUIMixin
- `gui/env_list.py` — EnvListMixin._update_info_label_fast
- `gui/env_list.py` — EnvListMixin._update_info_label
- `gui/env_operations.py` — EnvOperationsMixin._rename_env
- `gui/learn_page.py` — LearnPage.refresh_theme
- `gui/package_misc.py` — PackageMiscMixin._skip_conda_mirror
- `gui/package_ops.py` — PackageOpsMixin._get_catalog_lookup
- `gui/package_ops.py` — PackageOpsMixin._refresh_packages_sync_legacy
- `gui/package_panel.py` — PackagePanel._restore_install_log
- `gui/quicklaunch.py` — QuickLaunchMixin._ql_load_env_packages
- `gui/quicklaunch.py` — QuickLaunchMixin._get_installed_from_cache
- `gui/settings_catalog.py` — CatalogMixin._set_vscode_interpreter
- `gui/settings_toolchain.py` — ToolchainMixin._make_pm_tool_row
- `gui/settings_toolchain.py` — ToolchainMixin._make_pm_conda_row
- `gui/settings_toolchain.py` — ToolchainMixin._tc_do_verify
- `gui/settings_toolchain.py` — ToolchainMixin._tc_do_default
- `gui/styles.py` — invalidate_style_cache
- `gui/syntax_highlighter.py` — PythonHighlighter.highlightBlock
- `utils/i18n.py` — set_language
- `utils/i18n.py` — get_language
- `utils/logger.py` — safe_slot
- `utils/logger.py` — logged_subprocess
- `utils/logger.py` — log_perf
- `utils/logger.py` — SafeWorkerMixin
- `utils/logger.py` — SafeWorkerMixin.safe_run
- `utils/logger.py` — open_log_directory
- `utils/logger.py` — get_recent_crash_logs
- `utils/platform_utils.py` — setup_application_font
- `utils/platform_utils.py` — terminal_icon
- `utils/platform_utils.py` — bold_font_from
- `utils/platform_utils.py` — get_default_pipx_home
- `utils/platform_utils.py` — get_default_conda_envs_dir
- `utils/platform_utils.py` — get_poetry_venvs_path
- `utils/platform_utils.py` — get_conda_envs_dir
