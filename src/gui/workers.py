"""
VenvStudio — Background worker threads.

QThread workers extracted from main_window.py to keep that module focused on
the window/UI. Each worker wraps a long-running VenvManager operation (clone,
delete, rename, detail-fetch) and reports progress/results via Qt signals so
the GUI stays responsive.

These classes depend only on a VenvManager instance passed in at construction
— they hold no reference to MainWindow, which is what makes them safe to live
in their own module.
"""

from PySide6.QtCore import QThread, Signal


class CloneWorker(QThread):
    """Worker thread for cloning environments with progress."""
    progress = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, venv_manager, source, target):
        super().__init__()
        self.venv_manager = venv_manager
        self.source = source
        self.target = target
        self._cancelled = False

    def run(self):
        success, msg = self.venv_manager.clone_venv(
            self.source, self.target, callback=self._on_progress
        )
        if self._cancelled:
            import shutil
            target_path = self.venv_manager.base_dir / self.target
            if target_path.exists():
                shutil.rmtree(target_path, ignore_errors=True)
            self.finished.emit(False, "Clone cancelled by user")
        else:
            self.finished.emit(success, msg)

    def _on_progress(self, message):
        if not self._cancelled:
            self.progress.emit(message)

    def cancel(self):
        self._cancelled = True


class EnvDetailWorker(QThread):
    """Background worker to load env details only for envs missing cache.
    Uses ThreadPoolExecutor so large envs don't block each other.
    """
    env_detail_ready = Signal(int, str, int, str)  # row, python_ver, pkg_count, size
    all_done = Signal()

    def __init__(self, venv_manager, env_names):
        super().__init__()
        self.venv_manager = venv_manager
        self.env_names = env_names

    def _fetch_one(self, args):
        i, name = args
        venv_path = self.venv_manager.base_dir / name
        # Skip marker-based envs — already resolved by list_venvs_fast
        marker = venv_path / ".venvstudio_env"
        if marker.exists():
            return None
        cached = self.venv_manager._read_cache(venv_path)
        if cached:
            return None  # already loaded by list_venvs_fast
        info = self.venv_manager.get_venv_info(name, use_cache=False)
        if info:
            return (i, info.python_version, info.package_count, info.size)
        return None

    def run(self):
        from concurrent.futures import ThreadPoolExecutor, as_completed
        args = list(enumerate(self.env_names))
        # Max 4 threads — avoids hammering disk with too many simultaneous pip list calls
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(self._fetch_one, a): a for a in args}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    self.env_detail_ready.emit(*result)
        self.all_done.emit()


class DeleteWorker(QThread):
    """Worker thread for deleting environments with progress."""
    progress = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, venv_manager, name, env_path=None, env_type="venv"):
        super().__init__()
        self.venv_manager = venv_manager
        self.name = name
        self.env_path = env_path
        self.env_type = env_type

    def run(self):
        success, msg = self.venv_manager.delete_venv(
            self.name, callback=self.progress.emit,
            env_path=self.env_path, env_type=self.env_type
        )
        self.finished.emit(success, msg)


class RenameOnlyWorker(QThread):
    """Worker thread for fast rename — folder rename only."""
    progress = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, venv_manager, old_name, new_name):
        super().__init__()
        self.venv_manager = venv_manager
        self.old_name = old_name
        self.new_name = new_name

    def run(self):
        self.progress.emit(f"Renaming '{self.old_name}' → '{self.new_name}'...")
        success, msg = self.venv_manager.rename_venv(self.old_name, self.new_name)
        self.finished.emit(success, msg)


class RenameFullWorker(QThread):
    """Worker thread for full rename — clone + delete with same packages."""
    progress = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, venv_manager, old_name, new_name):
        super().__init__()
        self.venv_manager = venv_manager
        self.old_name = old_name
        self.new_name = new_name

    def run(self):
        success, msg = self.venv_manager.rename_full_venv(
            self.old_name, self.new_name, callback=self.progress.emit
        )
        self.finished.emit(success, msg)
