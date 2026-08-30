"""VenvStudio - Manual Install output history (B31).

The Manual Install tab used to show one thing: whatever the current install
printed. Every new run called `output_log.clear()`, and closing VenvStudio
threw the lot away -- so the answer to "what did that install actually say?"
survived only as long as you stayed on that screen and did not install
anything else.

That output is worth keeping. It records what pip resolved, what it skipped,
what warned, and which versions it settled on; a week later that is exactly
what you want when an environment starts behaving oddly.

Kept per environment, because that is the only grouping that means anything:
the output of installing into `ml` says nothing about `nlp`.

WHAT IT IS NOT: this is not the application log. venvstudio.log keeps the
permanent, complete record. This is the readable slice for one environment,
shown where the user already is.
"""
import json
import os
from pathlib import Path

from src.utils.logger import get_logger

_log = get_logger("venvstudio.install_history")

# Ten runs per environment. Runs rather than lines: someone looking here asks
# "what happened last time", not "show me two thousand lines". Ten covers a
# session's worth of experimentation and keeps the file small enough to read
# and write without thinking about it.
MAX_RUNS_PER_ENV = 10

# A single pip install of something large (torch, tensorflow) can print
# thousands of lines. Past a point the tail is all that matters, and an
# unbounded file would eventually be slow to load on startup.
MAX_LINES_PER_RUN = 400


def _history_file() -> Path:
    """Beside the config, not in the log directory -- logs are rotated."""
    from src.utils.platform_utils import get_config_dir
    return Path(get_config_dir()) / "install_history.json"


def _load_all() -> dict:
    try:
        fp = _history_file()
        if not fp.is_file():
            return {}
        with open(fp, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        # A damaged file costs the history, never the application.
        _log.warning(f"[InstallHistory] could not read: {e!r}")
        return {}


def _save_all(data: dict) -> None:
    try:
        fp = _history_file()
        fp.parent.mkdir(parents=True, exist_ok=True)
        tmp = str(fp) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, fp)     # atomic; a crash mid-write keeps the old file
    except Exception as e:
        _log.warning(f"[InstallHistory] could not write: {e!r}")


def _key(env_path) -> str:
    """Normalised environment path, so Windows case differences do not split
    one environment's history into two."""
    return os.path.normcase(os.path.abspath(str(env_path)))


def load_runs(env_path) -> list:
    """Past runs for this environment, oldest first. [] when there are none."""
    if not env_path:
        return []
    runs = _load_all().get(_key(env_path), [])
    return runs if isinstance(runs, list) else []


def add_run(env_path, title: str, lines: list) -> None:
    """Record one install/uninstall run."""
    if not env_path or not lines:
        return
    import datetime

    if len(lines) > MAX_LINES_PER_RUN:
        _dropped = len(lines) - MAX_LINES_PER_RUN
        # Keep the tail: the result of an install is at its end, and saying
        # what was dropped is better than silently showing a partial log.
        lines = ([f"… {_dropped} earlier lines not kept …"]
                 + lines[-MAX_LINES_PER_RUN:])

    data = _load_all()
    k = _key(env_path)
    runs = data.get(k, [])
    if not isinstance(runs, list):
        runs = []
    runs.append({
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "title": title or "",
        "lines": lines,
    })
    data[k] = runs[-MAX_RUNS_PER_ENV:]
    _save_all(data)


def clear_env(env_path) -> int:
    """Forget this environment's history. Returns how many runs were dropped."""
    if not env_path:
        return 0
    data = _load_all()
    k = _key(env_path)
    n = len(data.get(k, []) or [])
    if k in data:
        del data[k]
        _save_all(data)
    return n


def forget_env(env_path) -> None:
    """Drop the history when the environment itself is deleted.

    Without this the file would accumulate entries for environments that no
    longer exist, and a rebuilt environment of the same name would inherit the
    previous one's output.
    """
    clear_env(env_path)
