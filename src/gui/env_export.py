"""VenvStudio - MainWindow: Environment Export Mixin
Export selected environment to requirements.txt, Dockerfile, pyproject.toml,
conda env.yml, clipboard, or JSON (moved from main_window.py).
"""
from pathlib import Path

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox


class EnvExportMixin:
    """Mixin for MainWindow: environment export helpers."""

    # ── Export helpers (Environments page) ──

    def _get_env_type(self, venv_path) -> str:
        """Read the environment type from its .venvstudio_env marker."""
        try:
            import json
            marker = Path(venv_path) / ".venvstudio_env"
            if marker.exists():
                with open(marker, encoding="utf-8") as fh:
                    return (json.load(fh).get("type") or "venv").lower()
        except Exception:
            pass
        return "venv"

    def _get_env_pip_manager(self):
        """Get PipManager for the selected environment.

        The backend matters: a uv environment exports through `uv pip freeze`,
        not `pip freeze`. This page used to hard-code plain pip for every
        environment type, so the same environment exported differently
        depending on which page you started from.
        """
        name = self._get_selected_env_name()
        if not name:
            QMessageBox.warning(self, "Warning", "No environment selected.")
            return None
        from src.core.pip_manager import PipManager
        venv_path = self._get_env_path(name) or (self.venv_manager.base_dir / name)
        _backend = "uv" if self._get_env_type(venv_path) == "uv" else "pip"
        return PipManager(venv_path, backend=_backend)

    def _freeze_command_for_env(self, suffix: str = "") -> str:
        """The command this page actually runs to list packages."""
        name = self._get_selected_env_name() or ""
        venv_path = self._get_env_path(name) or (self.venv_manager.base_dir / name)
        _et = self._get_env_type(venv_path)
        if _et == "pipx":
            # pipx apps live in separate environments under the pipx home, so
            # the list comes from pipx. Its --short output is "name version",
            # so it needs converting before it is a valid requirements file --
            # a bare redirect would teach a command that writes something pip
            # cannot read back.
            if suffix:
                return "pipx list --short | sed 's/ /==/'" + suffix
            return "pipx list --short"
        if _et == "conda":
            # conda-installed packages are invisible to pip freeze; the real
            # list comes from micromamba (VenvStudio manages conda via it).
            return "micromamba list --export" + suffix
        if _et == "poetry":
            # poetry exports from its lock, not from whatever is installed.
            if suffix:
                return "poetry export -f requirements.txt --without-hashes" + suffix
            return "poetry export -f requirements.txt --without-hashes"
        _base = "uv pip freeze" if _et == "uv" else "pip freeze"
        return f"{_base}{suffix}"

    def _get_env_freeze_and_version(self):
        """Helper: get freeze content and python version for selected env."""
        import subprocess
        from src.utils.platform_utils import get_python_executable, subprocess_args
        pm = self._get_env_pip_manager()
        if not pm:
            return None, None
        freeze = pm.freeze()
        if not freeze:
            QMessageBox.warning(self, "Warning", "No packages to export.")
            return None, None
        py_ver = "3.12"
        try:
            exe = get_python_executable(pm.venv_path)
            result = subprocess.run(
                [str(exe), "--version"],
                capture_output=True, text=True, timeout=10,
                **subprocess_args()
            )
            ver = (result.stdout.strip() or result.stderr.strip()).replace("Python ", "")
            py_ver = ".".join(ver.split(".")[:2])
        except Exception:
            pass
        return freeze, py_ver

    def _export_cmd(self, action: str, command: str):
        """Show the command behind an export.

        Every export here starts from PipManager.freeze(), i.e. `pip freeze`;
        the rest is VenvStudio writing a file. Naming the action in the
        context keeps that honest: no shell command emits a Dockerfile, but
        one does produce the package list it is built from, and that is the
        part worth learning.
        """
        try:
            _env = self._get_selected_env_name() or ""
            self.show_command(
                command, context=f"{action} (env: {_env})" if _env else action)
        except Exception:
            pass

    def _export_requirements(self):
        freeze, _ = self._get_env_freeze_and_version()
        if not freeze:
            return
        self._export_cmd("Export requirements.txt",
                         self._freeze_command_for_env(" > requirements.txt"))
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Requirements", "requirements.txt", "Text Files (*.txt)"
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(freeze)
                QMessageBox.information(self, "✅ Success", f"Exported to:\n{filepath}")
            except IOError as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_dockerfile(self):
        freeze, py_ver = self._get_env_freeze_and_version()
        if not freeze:
            return
        self._export_cmd("Export Dockerfile",
                         self._freeze_command_for_env(" > requirements.txt"))
        dockerfile = (
            f"# Auto-generated by VenvStudio\n"
            f"FROM python:{py_ver}-slim\n\n"
            f"WORKDIR /app\n\n"
            f"RUN apt-get update && apt-get install -y --no-install-recommends \\\n"
            f"    gcc \\\n"
            f"    && rm -rf /var/lib/apt/lists/*\n\n"
            f"COPY requirements.txt .\n"
            f"RUN pip install --no-cache-dir -r requirements.txt\n\n"
            f"COPY . .\n\n"
            f"# CMD [\"python\", \"main.py\"]\n"
        )
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Dockerfile", "Dockerfile", "All Files (*)"
        )
        if filepath:
            req_path = Path(filepath).parent / "requirements.txt"
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(dockerfile)
                with open(req_path, "w", encoding="utf-8") as f:
                    f.write(freeze)
                QMessageBox.information(
                    self, "✅ Success",
                    f"Exported:\n  📄 {filepath}\n  📄 {req_path}\n\n"
                    f"Build: docker build -t myapp ."
                )
            except IOError as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_docker_compose(self):
        freeze, py_ver = self._get_env_freeze_and_version()
        if not freeze:
            return
        self._export_cmd("Export docker-compose.yml",
                         self._freeze_command_for_env(" > requirements.txt"))
        compose = (
            f"# Auto-generated by VenvStudio\n"
            f"version: '3.8'\n\n"
            f"services:\n"
            f"  app:\n"
            f"    build: .\n"
            f"    container_name: myapp\n"
            f"    ports:\n"
            f"      - \"8000:8000\"\n"
            f"    volumes:\n"
            f"      - .:/app\n"
            f"    environment:\n"
            f"      - PYTHONUNBUFFERED=1\n"
        )
        dockerfile = (
            f"FROM python:{py_ver}-slim\n"
            f"WORKDIR /app\n"
            f"COPY requirements.txt .\n"
            f"RUN pip install --no-cache-dir -r requirements.txt\n"
            f"COPY . .\n"
        )
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export docker-compose.yml", "docker-compose.yml",
            "YAML Files (*.yml);;All Files (*)"
        )
        if filepath:
            base = Path(filepath).parent
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(compose)
                with open(base / "Dockerfile", "w", encoding="utf-8") as f:
                    f.write(dockerfile)
                with open(base / "requirements.txt", "w", encoding="utf-8") as f:
                    f.write(freeze)
                QMessageBox.information(
                    self, "✅ Success",
                    f"Exported 3 files to {base}\n\nRun: docker-compose up --build"
                )
            except IOError as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_pyproject(self):
        freeze, py_ver = self._get_env_freeze_and_version()
        if not freeze:
            return
        self._export_cmd("Export pyproject.toml", self._freeze_command_for_env())
        deps = "\n".join(f'    "{l.strip()}",' for l in freeze.strip().splitlines()
                         if l.strip() and not l.startswith("#"))
        content = (
            f'[build-system]\nrequires = ["setuptools>=68.0", "wheel"]\n'
            f'build-backend = "setuptools.backends._legacy:_Backend"\n\n'
            f'[project]\nname = "myproject"\nversion = "0.1.0"\n'
            f'requires-python = ">={py_ver}"\n'
            f'dependencies = [\n{deps}\n]\n'
        )
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export pyproject.toml", "pyproject.toml",
            "TOML Files (*.toml);;All Files (*)"
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                QMessageBox.information(self, "✅ Success", f"Exported to:\n{filepath}")
            except IOError as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_conda_yml(self):
        freeze, py_ver = self._get_env_freeze_and_version()
        if not freeze:
            return
        self._export_cmd("Export environment.yml", self._freeze_command_for_env())
        pip_deps = "\n".join(f"    - {l.strip()}" for l in freeze.strip().splitlines()
                             if l.strip() and not l.startswith("#"))
        content = (
            f"name: myenv\nchannels:\n  - defaults\n  - conda-forge\n"
            f"dependencies:\n  - python={py_ver}\n  - pip\n  - pip:\n{pip_deps}\n"
        )
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export environment.yml", "environment.yml",
            "YAML Files (*.yml);;All Files (*)"
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                QMessageBox.information(
                    self, "✅ Success",
                    f"Exported to:\n{filepath}\n\nCreate: conda env create -f environment.yml"
                )
            except IOError as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_clipboard(self):
        freeze, _ = self._get_env_freeze_and_version()
        if not freeze:
            return
        self._export_cmd("Copy package list", self._freeze_command_for_env())
        QApplication.clipboard().setText(freeze)
        count = len(freeze.strip().splitlines())
        self.statusBar().showMessage(f"📋 {count} packages copied to clipboard!")
        QMessageBox.information(self, "✅ Copied", f"{count} packages copied to clipboard.")

    def _export_frozen(self):
        """Export requirements with SHA-256 hashes (--require-hashes compatible)."""
        name = self._get_selected_env_name()
        if not name:
            return
        venv_path = self.venv_manager.base_dir / name
        import subprocess, os, tempfile, hashlib, glob
        from src.utils.platform_utils import subprocess_args
        if os.name == "nt":
            pip_exe = venv_path / "Scripts" / "pip.exe"
        else:
            pip_exe = venv_path / "bin" / "pip"
        if not pip_exe.exists():
            QMessageBox.warning(self, "Error", "pip not found in this environment.")
            return

        # Step 1: get plain freeze list
        try:
            result = subprocess.run(
                [str(pip_exe), "freeze"],
                **subprocess_args(capture_output=True, text=True, timeout=30)
            )
            freeze_lines = [l for l in result.stdout.strip().splitlines() if l and not l.startswith("#")]
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        if not freeze_lines:
            QMessageBox.information(self, "Info", "No packages installed.")
            return
        self._export_cmd(
            "Export requirements-frozen.txt",
            "pip freeze && pip download --no-deps  # hashed per package")

        # Step 2: download wheels into tmp dir and hash them
        progress = QMessageBox(self)
        progress.setWindowTitle("Generating Hashes")
        progress.setText(f"Downloading {len(freeze_lines)} packages to compute hashes...\nThis may take a moment.")
        progress.setStandardButtons(QMessageBox.NoButton)
        progress.show()
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

        hashed_lines = []
        failed = []
        with tempfile.TemporaryDirectory() as tmp_dir:
            for pkg_spec in freeze_lines:
                try:
                    dl = subprocess.run(
                        [str(pip_exe), "download", "--no-deps", "--dest", tmp_dir, pkg_spec],
                        **subprocess_args(capture_output=True, text=True, timeout=120)
                    )
                    # Find the downloaded file(s) for this package
                    pkg_name = pkg_spec.split("==")[0].strip() if "==" in pkg_spec else pkg_spec.strip()
                    downloaded = glob.glob(os.path.join(tmp_dir, f"{pkg_name.replace('-','_')}*")) + \
                                 glob.glob(os.path.join(tmp_dir, f"{pkg_name}*"))
                    # Pick the newest file
                    downloaded = sorted(set(downloaded), key=os.path.getmtime, reverse=True)
                    if downloaded:
                        fpath = downloaded[0]
                        sha256 = hashlib.sha256(open(fpath, "rb").read()).hexdigest()
                        hashed_lines.append(f"{pkg_spec} \\\n    --hash=sha256:{sha256}")
                        os.remove(fpath)
                    else:
                        # Download failed or not found — add without hash with comment
                        hashed_lines.append(f"{pkg_spec}  # hash unavailable")
                        failed.append(pkg_spec)
                except Exception:
                    hashed_lines.append(f"{pkg_spec}  # hash unavailable")
                    failed.append(pkg_spec)

        progress.close()

        header = (
            "# Generated by VenvStudio — requirements with SHA-256 hashes\n"
            "# Install with: pip install --require-hashes -r requirements-frozen.txt\n"
            "#\n"
        )
        content = header + "\n".join(hashed_lines) + "\n"

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Frozen Requirements", "requirements-frozen.txt", "Text Files (*.txt)"
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                msg = f"Exported {len(freeze_lines)} packages to:\n{filepath}"
                if failed:
                    msg += f"\n\n⚠️ {len(failed)} package(s) could not be hashed (marked in file)."
                QMessageBox.information(self, "✅ Success", msg)
            except IOError as e:
                QMessageBox.critical(self, "Error", str(e))



    def _export_json(self):
        """Export environment info as JSON."""
        import json
        name = self._get_selected_env_name()
        if not name:
            return
        freeze, py_ver = self._get_env_freeze_and_version()
        if not freeze:
            return
        self._export_cmd("Export JSON", self._freeze_command_for_env())
        packages = []
        for line in freeze.strip().splitlines():
            if "==" in line:
                pkg, ver = line.split("==", 1)
                packages.append({"name": pkg.strip(), "version": ver.strip()})
            else:
                packages.append({"name": line.strip(), "version": ""})
        data = {
            "environment": name,
            "python_version": py_ver,
            "package_count": len(packages),
            "packages": packages,
        }
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export JSON", f"{name}.json", "JSON Files (*.json)"
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                QMessageBox.information(self, "✅ Success", f"Exported to:\n{filepath}")
            except IOError as e:
                QMessageBox.critical(self, "Error", str(e))

