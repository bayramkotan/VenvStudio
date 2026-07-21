"""
venv_manager rename mixin — split from venv_manager.py.

Holds rename_venv, _relocate_venv_paths, rename_full_venv and
set_poetry_display_name. Mixed into VenvManager; uses self.base_dir,
self.clone_venv and self.delete_venv from the composed class.
"""

import os
import logging
from pathlib import Path
from typing import Optional

from src.core.venv_manager_common import banner_start, banner_success, banner_error, banner_warning

_log = logging.getLogger("venvstudio.core.venv_manager")


class _RenameMixin:
    """Environment rename / relocate. Mixed into VenvManager."""

    def rename_venv(self, old_name: str, new_name: str,
                    old_path: Optional[str] = None, env_type: str = "venv") -> tuple[bool, str]:
        _log.info(f"rename_venv: {old_name!r} → {new_name!r} env_type={env_type!r}")
        banner_start(
            f"Renaming '{old_name}' → '{new_name}' (folder-only)",
            details=[f"Type: {env_type}", f"Path: {old_path or (self.base_dir / old_name)}"],
        )
        # ── Env-type guards ────────────────────────────────────────────────
        if env_type == "pipx":
            banner_warning(
                "Rename not supported for pipx",
                details=["Use: pipx uninstall + pipx install"],
            )
            return False, (
                "Renaming a pipx environment is not supported.\n\n"
                "pipx apps are identified by their package name. To 'rename':\n\n"
                f"    pipx uninstall {old_name}\n"
                f"    pipx install {new_name}"
            )
        if env_type == "poetry":
            banner_warning(
                "Rename not supported for Poetry",
                details=["Edit pyproject.toml name + poetry install"],
            )
            return False, (
                "Renaming a Poetry environment by folder is not supported.\n\n"
                "Poetry env names are derived from the project name in pyproject.toml.\n"
                "To rename, update the 'name' field in your pyproject.toml, then run:\n\n"
                "    poetry env remove --all\n"
                "    poetry install"
            )
        if env_type == "conda":
            banner_warning(
                "In-place rename not supported for conda",
                details=["Use Rename (Full) instead — safe clone + delete"],
            )
            return False, (
                "Renaming a conda environment in place is not supported by micromamba.\n\n"
                "Use the 'Rename (Full)' option instead, which will:\n"
                "  1. Export packages from the old env\n"
                "  2. Create a new env with the desired name\n"
                "  3. Delete the old env\n\n"
                "Or do it manually:\n\n"
                f"    micromamba env export -n {old_name} > env.yml\n"
                f"    micromamba create -n {new_name} --file env.yml\n"
                f"    micromamba env remove -n {old_name} --yes"
            )

        # ── venv / uv: folder rename ───────────────────────────────────────
        old_path_obj = Path(old_path) if old_path else (self.base_dir / old_name)
        new_path_obj = self.base_dir / new_name

        if not old_path_obj.exists():
            banner_error(f"Source env '{old_name}' not found", details=[f"Looked at: {old_path_obj}"])
            return False, f"Environment '{old_name}' not found at {old_path_obj}"
        if new_path_obj.exists():
            banner_error(f"Target '{new_name}' already exists", details=[f"Path: {new_path_obj}"])
            return False, f"Environment '{new_name}' already exists"

        try:
            old_path_obj.rename(new_path_obj)

            # ── Relocate the venv so it keeps working after the move ──
            # A bare folder rename leaves the old absolute path baked into
            # pyvenv.cfg and the shebang lines of bin/* scripts (pip, etc.),
            # so `new_env/bin/pip` still points at the OLD path and fails with
            # "No such file or directory" on the next operation. Rewrite those
            # references to the new location. venv/uv only; best-effort.
            relocated, reloc_note = self._relocate_venv_paths(
                new_path_obj, old_path_obj, new_path_obj
            )

            _details = [
                f"Old path: {old_path_obj}",
                f"New path: {new_path_obj}",
            ]
            if relocated:
                _details.append("Scripts + pyvenv.cfg updated to new path")
            else:
                _details.append(
                    "⚠ Note: activate scripts may contain old path — "
                    "run Rename (Full) for a full rewrite"
                )
            banner_success(f"Renamed '{old_name}' → '{new_name}'", details=_details)
            return True, f"Environment '{old_name}' renamed to '{new_name}'"
        except Exception as e:
            banner_error(f"Could not rename '{old_name}'", details=[str(e)])
            return False, f"Error renaming environment: {str(e)}"

    def _relocate_venv_paths(self, venv_dir, old_base, new_base) -> tuple[bool, str]:
        """Rewrite absolute paths inside a moved venv so it keeps working.

        Updates ``pyvenv.cfg`` and the shebang / path references in ``bin/``
        (or ``Scripts/`` on Windows) that still point at the old location.
        Best-effort and non-fatal: returns (ok, note). venv/uv layouts only.
        """
        import os as _os
        old_s = str(old_base)
        new_s = str(new_base)
        if old_s == new_s:
            return True, "no change needed"
        try:
            changed = 0

            # pyvenv.cfg — home = /old/path/bin  (and possibly others)
            cfg = venv_dir / "pyvenv.cfg"
            if cfg.exists():
                txt = cfg.read_text(encoding="utf-8", errors="replace")
                if old_s in txt:
                    cfg.write_text(txt.replace(old_s, new_s), encoding="utf-8")
                    changed += 1

            # bin/ (POSIX) or Scripts/ (Windows) — shebangs + activate scripts
            scripts_dir = venv_dir / ("Scripts" if _os.name == "nt" else "bin")
            if scripts_dir.is_dir():
                for entry in scripts_dir.iterdir():
                    if not entry.is_file():
                        continue
                    try:
                        raw = entry.read_bytes()
                    except Exception:
                        continue
                    # Skip real binaries: only rewrite text-ish files that
                    # actually contain the old path.
                    if old_s.encode() not in raw:
                        continue
                    try:
                        new_raw = raw.replace(old_s.encode(), new_s.encode())
                        entry.write_bytes(new_raw)
                        changed += 1
                    except Exception:
                        # e.g. permission / busy — leave that file as-is
                        continue

            if changed:
                return True, f"relocated {changed} file(s)"
            return True, "nothing to rewrite"
        except Exception as e:
            _log.debug(f"_relocate_venv_paths failed: {e}")
            return False, str(e)

    def rename_full_venv(self, old_name: str, new_name: str, callback=None,
                         old_path: Optional[str] = None, env_type: str = "venv") -> tuple[bool, str]:
        """
        Full rename: clone old env to new name, then delete old.
        Slower but safe — all packages reinstalled, paths correct.
        """
        _log.info(f"rename_full_venv: {old_name!r} → {new_name!r} env_type={env_type!r}")
        banner_start(
            f"Full rename '{old_name}' → '{new_name}'",
            details=[
                f"Type: {env_type}",
                "Step 1/2: Clone with new name",
                "Step 2/2: Delete old env",
                "⏳ This may take a while (packages reinstalled)",
            ],
        )
        # pipx full rename not supported — clone_venv will return helpful error
        if env_type == "pipx":
            return self.clone_venv(old_name, new_name, callback=callback,
                                   source_path=old_path, source_type=env_type)

        if callback:
            callback(f"Cloning '{old_name}' → '{new_name}'...")
        success, msg = self.clone_venv(old_name, new_name, callback=callback,
                                       source_path=old_path, source_type=env_type)
        if not success:
            banner_error(
                f"Full rename aborted",
                details=[f"Could not clone '{old_name}'", "Old env is untouched", msg.splitlines()[0] if msg else ""],
            )
            return False, f"Failed to create '{new_name}': {msg}"

        if callback:
            callback(f"Deleting old environment '{old_name}'...")
        try:
            # Use delete_venv so conda/marker handling is correct
            success, msg = self.delete_venv(old_name, callback=callback,
                                            env_path=old_path, env_type=env_type)
            if not success:
                banner_warning(
                    f"New env created but old env remains",
                    details=[f"'{new_name}' is ready", f"Could not delete '{old_name}' — delete manually"],
                )
                return False, f"'{new_name}' created but could not delete '{old_name}': {msg}"
        except Exception as e:
            banner_warning(
                f"New env created but old env remains",
                details=[f"'{new_name}' is ready", f"Delete '{old_name}' failed: {e}"],
            )
            return False, f"'{new_name}' created but could not delete '{old_name}': {e}"

        banner_success(
            f"Full rename complete: '{old_name}' → '{new_name}'",
            details=["All packages reinstalled with correct paths", "Old env deleted"],
        )
        return True, f"Environment '{old_name}' fully renamed to '{new_name}'"

    def set_poetry_display_name(self, env_path, new_display_name: str) -> tuple[bool, str]:
        """Set a display name override for a Poetry env (VenvStudio-only, doesn't touch Poetry itself).
        The override is stored in a .venvstudio_display_name file inside the poetry env dir.
        """
        _log.info(f"set_poetry_display_name: path={env_path} new_name={new_display_name!r}")
        try:
            _p = Path(env_path)
            if not _p.exists() or not _p.is_dir():
                banner_error("Poetry env path not found", details=[f"Path: {env_path}"])
                return False, f"Poetry environment path not found: {env_path}"
            marker = _p / ".venvstudio_display_name"
            if new_display_name.strip():
                marker.write_text(new_display_name.strip(), encoding="utf-8")
                banner_success(
                    "Display name set",
                    details=[f"Env: {_p.name}", f"New display name: {new_display_name.strip()}"],
                )
                return True, f"Display name set to '{new_display_name.strip()}'"
            else:
                # Empty → remove override (revert to default stripped name)
                if marker.exists():
                    marker.unlink()
                banner_success(
                    "Display name override cleared",
                    details=[f"Env: {_p.name}", "Reverted to default poetry name"],
                )
                return True, "Display name override cleared"
        except Exception as e:
            banner_error("Could not set display name", details=[str(e)])
            return False, f"Could not set display name: {e}"
