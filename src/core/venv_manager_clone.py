"""
venv_manager clone mixin — split from venv_manager.py.

Holds clone_venv (venv/uv/poetry/conda/pipx cloning). Mixed into
VenvManager; uses self.base_dir and self.create_venv from the base class,
and module-level helpers imported below.
"""

import sys
import json
import shutil
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from src.utils.platform_utils import (
    get_python_executable,
    get_pip_executable,
)
from src.core.venv_manager_common import _run, banner_start, banner_success, banner_error, banner_warning

_log = logging.getLogger("venvstudio.core.venv_manager")


class _CloneMixin:
    """Environment cloning. Mixed into VenvManager."""

    def clone_venv(self, source_name: str, target_name: str, callback=None,
                   source_path: Optional[str] = None, source_type: str = "venv") -> tuple[bool, str]:
        _log.info(f"clone_venv: {source_name!r} → {target_name!r} "
                  f"source_type={source_type!r} source_path={source_path!r}")
        banner_start(
            f"Cloning '{source_name}' → '{target_name}'",
            details=[
                f"Type: {source_type}",
                f"Source: {source_path or (self.base_dir / source_name)}",
                f"Target: {self.base_dir / target_name}",
            ],
        )
        # ── Env-type guards: pipx / poetry not supported via Clone ─────────
        if source_type == "pipx":
            banner_warning(
                f"Cloning a pipx env is not supported",
                details=["pipx apps are single-binary installs.", "Use: pipx install <pkg>"],
            )
            return False, (
                "Cloning a pipx environment is not supported.\n\n"
                "pipx manages its own isolated environments per CLI app.\n"
                "To replicate a pipx app elsewhere, run:\n\n"
                f"    pipx install {source_name}\n"
                "    pipx reinstall-all\n\n"
                "Or list installed apps with:\n\n"
                "    pipx list"
            )
        if source_type == "poetry":
            # ── Poetry clone: pip freeze from real venv → new poetry project → install ─
            try:
                import shutil as _sh
                poetry_bin = _sh.which("poetry") or _sh.which("poetry.exe")
                if not poetry_bin:
                    banner_warning(
                        "poetry not found — cannot clone Poetry env",
                        details=["Install poetry via Settings → Toolchain Manager"],
                    )
                    return False, (
                        "poetry not found in PATH.\n\n"
                        "Install it via Settings → Toolchain Manager, or manually:\n"
                        "    pip install poetry"
                    )

                # Resolve real venv path (may be in .cache/pypoetry/virtualenvs/)
                source_path_obj = Path(source_path) if source_path else (self.base_dir / source_name)
                real_venv = source_path_obj
                # If source_path is a poetry virtualenvs path, use it directly
                # Otherwise look for pyvenv.cfg to confirm it's a real venv
                if not (real_venv / "pyvenv.cfg").exists():
                    banner_error(
                        f"Could not find valid Poetry venv at {real_venv}",
                        details=["pyvenv.cfg not found"],
                    )
                    return False, f"Could not find valid Poetry environment at {real_venv}"

                # Get Python from the real venv
                _po_py = real_venv / ("Scripts" if sys.platform == "win32" else "bin") / (
                    "python.exe" if sys.platform == "win32" else "python"
                )
                if not _po_py.exists():
                    return False, f"Python interpreter not found in Poetry env at {_po_py}"

                # pip freeze from real venv
                if callback:
                    callback(f"Reading packages from '{source_name}' (pip freeze)...")
                _pip = real_venv / ("Scripts" if sys.platform == "win32" else "bin") / (
                    "pip.exe" if sys.platform == "win32" else "pip"
                )
                if _pip.exists():
                    _freeze_r = _run([str(_pip), "freeze"],
                                     capture_output=True, text=True, timeout=30)
                else:
                    _freeze_r = _run([str(_po_py), "-m", "pip", "freeze"],
                                     capture_output=True, text=True, timeout=30)
                requirements = _freeze_r.stdout if _freeze_r.returncode == 0 else ""

                # Detect Python version
                _pyver_str = ""
                try:
                    _pv = _run([str(_po_py), "--version"],
                               capture_output=True, text=True, timeout=5)
                    _pyver_str = (_pv.stdout.strip() or _pv.stderr.strip()).replace("Python ", "")
                except Exception:
                    pass

                # Create new poetry project
                target_path = self.base_dir / target_name
                if callback:
                    callback(f"Creating new Poetry project '{target_name}'...")
                target_path.mkdir(parents=True, exist_ok=True)
                _new_r = _run([poetry_bin, "new", str(target_path)],
                              capture_output=True, text=True, timeout=120,
                              cwd=str(target_path.parent))
                if _new_r.returncode != 0:
                    # Try init if new fails (dir already exists etc.)
                    _init_r = _run([poetry_bin, "init", "--no-interaction", "--name", target_name],
                                   capture_output=True, text=True, timeout=60,
                                   cwd=str(target_path))
                    if _init_r.returncode != 0:
                        shutil.rmtree(target_path, ignore_errors=True)
                        return False, f"poetry new/init failed:\n{_new_r.stderr[:400]}"

                # Use same Python version
                if _pyver_str:
                    _use_r = _run([poetry_bin, "env", "use", str(_po_py)],
                                  capture_output=True, text=True, timeout=60,
                                  cwd=str(target_path))

                # Install packages
                if requirements.strip():
                    if callback:
                        callback(f"Installing packages into '{target_name}'...")
                    req_file = target_path / "requirements_clone.txt"
                    req_file.write_text(requirements)
                    _inst_r = _run([poetry_bin, "run", "pip", "install", "-r", str(req_file)],
                                   capture_output=True, text=True, timeout=600,
                                   cwd=str(target_path))
                    req_file.unlink(missing_ok=True)
                    if _inst_r.returncode != 0:
                        # Non-fatal — env created but some packages may have failed
                        if callback:
                            callback("⚠ Some packages may not have installed — check manually")
                else:
                    # No packages — just run poetry install to create the venv
                    _run([poetry_bin, "install", "--no-root"],
                         capture_output=True, text=True, timeout=120,
                         cwd=str(target_path))

                # Get real venv path
                _po_venv_path = None
                try:
                    _einfo = _run([poetry_bin, "env", "info", "--path"],
                                  capture_output=True, text=True, timeout=30,
                                  cwd=str(target_path))
                    _ep = _einfo.stdout.strip()
                    if _ep and Path(_ep).exists():
                        _po_venv_path = _ep
                except Exception:
                    pass

                # Write marker
                import json as _json, datetime as _dt
                with open(target_path / ".venvstudio_env", "w") as _f:
                    _json.dump({
                        "type": "poetry",
                        "name": target_name,
                        "python_version": _pyver_str,
                        "poetry_venv_path": _po_venv_path or "",
                        "created": _dt.datetime.now().isoformat(),
                    }, _f, indent=2)

                banner_success(
                    f"Poetry env cloned to '{target_name}'",
                    details=[
                        f"Source: {real_venv}",
                        f"Target project: {target_path}",
                        f"Python: {_pyver_str or 'unknown'}",
                    ],
                )
                return True, f"Poetry environment '{source_name}' cloned to '{target_name}' successfully"

            except Exception as e:
                banner_error(f"Could not clone Poetry env '{source_name}'", details=[str(e)])
                return False, f"Error cloning Poetry environment: {e}"

        source_path_obj = Path(source_path) if source_path else (self.base_dir / source_name)
        if not source_path_obj.exists():
            return False, f"Source environment '{source_name}' not found at {source_path_obj}"

        target_path = self.base_dir / target_name
        if target_path.exists():
            return False, f"Target environment '{target_name}' already exists"

        # ── conda clone via micromamba create --clone ──────────────────────
        if source_type == "conda":
            try:
                from src.core.micromamba_installer import get_micromamba_exe, write_conda_marker
                mm = get_micromamba_exe()
                if not mm:
                    return False, (
                        "micromamba not found. Install it via Settings → Toolchain Manager, "
                        "or clone manually:\n\n"
                        f"    micromamba env export -p {source_path_obj} > env.yml\n"
                        f"    micromamba create -p {target_path} --file env.yml"
                    )
                if callback:
                    callback(f"Cloning conda env to '{target_name}'...")
                result = _run(
                    [str(mm), "create", "-p", str(target_path),
                     "--clone", str(source_path_obj), "--yes"],
                    capture_output=True, text=True, timeout=600,
                )
                if result.returncode != 0:
                    return False, f"micromamba clone failed:\n{result.stderr.strip() or result.stdout.strip()}"

                # Write marker so VenvStudio recognizes it as conda
                # Try to detect python version from the new env
                _pyver = ""
                try:
                    _py = get_python_executable(target_path)
                    if _py.exists():
                        _r = _run([str(_py), "--version"],
                                  capture_output=True, text=True, timeout=5)
                        _pyver = (_r.stdout or _r.stderr).strip().replace("Python", "").strip()
                except Exception:
                    pass
                try:
                    write_conda_marker(target_path, python_version=_pyver or "3.12")
                except Exception:
                    pass

                banner_success(
                    f"Conda env cloned to '{target_name}'",
                    details=[
                        f"Source: {source_path_obj}",
                        f"Target: {target_path}",
                        f"Python: {_pyver or 'unknown'}",
                    ],
                )
                return True, f"Conda environment '{source_name}' cloned to '{target_name}' successfully"
            except Exception as e:
                banner_error(f"Could not clone conda env '{source_name}'", details=[str(e)])
                return False, f"Error cloning conda env: {e}"

        # ── uv clone: uv pip freeze → uv venv → uv pip install ─────────────
        if source_type == "uv":
            try:
                import shutil as _sh
                uv_bin = _sh.which("uv")
                if not uv_bin:
                    # Platform-aware manual command example
                    from src.utils.platform_utils import get_platform as _gp
                    if _gp() == "windows":
                        _src_py_hint = f"{source_path_obj}\\Scripts\\python.exe"
                        _tgt_py_hint = f"{target_path}\\Scripts\\python.exe"
                    else:
                        _src_py_hint = f"{source_path_obj}/bin/python"
                        _tgt_py_hint = f"{target_path}/bin/python"
                    return False, (
                        "uv not found in PATH. Install it via Settings → Toolchain Manager,\n"
                        "or clone manually:\n\n"
                        f"    uv pip freeze --python {_src_py_hint} > req.txt\n"
                        f"    uv venv {target_path}\n"
                        f"    uv pip install -r req.txt --python {_tgt_py_hint}"
                    )

                src_py = get_python_executable(source_path_obj)
                if not src_py.exists():
                    return False, f"Source Python interpreter not found at {src_py}"

                if callback:
                    callback(f"Reading packages from '{source_name}' (uv pip freeze)...")
                result = _run(
                    [uv_bin, "pip", "freeze", "--python", str(src_py)],
                    capture_output=True, text=True, timeout=30,
                )
                if result.returncode != 0:
                    return False, f"uv pip freeze failed:\n{result.stderr.strip()}"
                requirements = result.stdout

                if callback:
                    callback(f"Creating new uv env '{target_name}'...")
                # Use the same Python as source to preserve version
                result = _run(
                    [uv_bin, "venv", str(target_path), "--python", str(src_py)],
                    capture_output=True, text=True, timeout=60,
                )
                if result.returncode != 0:
                    # Retry without --python in case the source interp isn't discoverable
                    result = _run(
                        [uv_bin, "venv", str(target_path)],
                        capture_output=True, text=True, timeout=60,
                    )
                    if result.returncode != 0:
                        return False, f"uv venv failed:\n{result.stderr.strip()}"

                if requirements.strip():
                    req_file = target_path / "requirements_clone.txt"
                    with open(req_file, "w") as f:
                        f.write(requirements)

                    target_py = get_python_executable(target_path)
                    if callback:
                        callback(f"Installing packages into '{target_name}' (uv pip install)...")
                    result = _run(
                        [uv_bin, "pip", "install", "-r", str(req_file),
                         "--python", str(target_py)],
                        capture_output=True, text=True, timeout=600,
                    )
                    req_file.unlink(missing_ok=True)
                    if result.returncode != 0:
                        return False, f"Created env but failed to install some packages:\n{result.stderr.strip()}"

                banner_success(
                    f"uv env cloned to '{target_name}'",
                    details=[f"Source: {source_path_obj}", f"Target: {target_path}"],
                )
                return True, f"uv environment '{source_name}' cloned to '{target_name}' successfully"
            except Exception as e:
                banner_error(f"Could not clone uv env '{source_name}'", details=[str(e)])
                return False, f"Error cloning uv env: {e}"

        # ── venv clone (default): pip freeze → create → pip install -r ─────
        source_pip = get_pip_executable(source_path_obj)

        # Resolve a python interpreter in the source env as a fallback for
        # reading packages. A folder-renamed env can have a pip whose shebang
        # still points at the old path (so `source_pip freeze` dies with
        # "No such file or directory"), but `python -m pip freeze` via the
        # interpreter still works. We try pip first, then python -m pip.
        _src_py = source_path_obj / (
            "Scripts" if sys.platform == "win32" else "bin"
        ) / ("python.exe" if sys.platform == "win32" else "python")

        if not source_pip.exists() and not _src_py.exists():
            return False, (
                f"Source pip not found at {source_pip}.\n\n"
                f"This env appears to have no pip installed. Install pip first, or\n"
                f"recreate the env with '--with-pip' and try again."
            )

        try:
            requirements = ""
            _freeze_ok = False
            _last_err = ""

            # 1) Try the pip executable directly (fast path). exists() can be
            #    True for a DANGLING symlink (the link file exists but its
            #    target doesn't), in which case running it raises FileNotFound —
            #    so we guard the call in try/except and fall through on any
            #    failure instead of aborting the whole clone.
            if source_pip.exists():
                try:
                    result = _run(
                        [str(source_pip), "freeze"],
                        capture_output=True, text=True, timeout=15,
                    )
                    if result.returncode == 0:
                        requirements = result.stdout
                        _freeze_ok = True
                    else:
                        _last_err = (result.stderr or "").strip()
                except (FileNotFoundError, OSError) as e:
                    _last_err = str(e)  # dangling pip symlink → try python next

            # 2) Fall back to `python -m pip freeze` via the interpreter when
            #    the pip script is missing or broken (e.g. stale/dangling after
            #    a folder rename). The python symlink usually still resolves.
            if not _freeze_ok and _src_py.exists():
                if callback:
                    callback(f"Reading packages from '{source_name}' (python -m pip)...")
                try:
                    result = _run(
                        [str(_src_py), "-m", "pip", "freeze"],
                        capture_output=True, text=True, timeout=20,
                    )
                    if result.returncode == 0:
                        requirements = result.stdout
                        _freeze_ok = True
                    else:
                        _last_err = (result.stderr or "").strip() or _last_err
                except (FileNotFoundError, OSError) as e:
                    _last_err = str(e) or _last_err

            if not _freeze_ok:
                return False, (
                    f"Could not read packages from '{source_name}'.\n\n"
                    f"{_last_err or 'pip freeze failed'}\n\n"
                    f"The env's pip/python may be broken (e.g. a dangling symlink "
                    f"after a folder-only rename). Recreate the env, or delete it "
                    f"and start fresh."
                )

            success, msg = self.create_venv(target_name, callback=callback)
            if not success:
                return False, msg

            if requirements.strip():
                req_file = target_path / "requirements_clone.txt"
                with open(req_file, "w") as f:
                    f.write(requirements)

                target_pip = get_pip_executable(target_path)
                if callback:
                    callback(f"Installing packages into '{target_name}'...")

                result = _run(
                    [str(target_pip), "install", "-r", str(req_file)],
                    capture_output=True, text=True, timeout=300,
                )
                req_file.unlink(missing_ok=True)

                if result.returncode != 0:
                    banner_error(
                        f"Clone completed but some packages failed",
                        details=[f"Target: {target_path}", "Check pip output below"],
                    )
                    return False, f"Created env but failed to install some packages:\n{result.stderr}"

            # Count packages for nice summary
            _pkg_count = 0
            try:
                _pkg_count = len([l for l in requirements.splitlines() if l and not l.startswith("#")])
            except Exception:
                pass
            banner_success(
                f"Environment '{target_name}' ready!",
                details=[
                    f"Cloned from: {source_name}",
                    f"Path: {target_path}",
                    f"Packages reinstalled: {_pkg_count}" if _pkg_count else f"Packages reinstalled: ok",
                ],
            )
            return True, f"Environment '{source_name}' cloned to '{target_name}' successfully"

        except Exception as e:
            banner_error(f"Could not clone '{source_name}'", details=[str(e)])
            return False, f"Error cloning environment: {str(e)}"
