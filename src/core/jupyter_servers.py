"""VenvStudio - find the Jupyter servers that are running, and stop them.

B80 (Bayram, 2026-09-06: "tools altinda -> working jupyter instance gibi
birsey ekleyebilir miyiz? Calisanlari kapatmak/yeniden calistirmak icin").

A launched JupyterLab keeps running after its window is closed, and with
``--no-browser`` it never had a window to begin with. Ports stay taken, the
next launch lands on 8889 then 8890, and nothing in the application says any
of this is happening.

HOW SERVERS ARE FOUND. Every Jupyter server writes a JSON file into its
runtime directory while it runs:

    ~/.local/share/jupyter/runtime/jpserver-<pid>.json

    {"base_url": "/", "hostname": "localhost", "pid": 580, "port": 8899,
     "root_dir": "/tmp/nbdir", "token": "abc",
     "url": "http://localhost:8899/", "version": "2.21.0"}

That path holds no virtualenv component, so servers started from ANY
environment land in the same directory -- one scan finds all of them, and it
finds servers VenvStudio did not start as well.

WHY LIVENESS IS CHECKED SEPARATELY, and why it is an HTTP request rather
than a PID check. Killing a server leaves its JSON file behind; this was
reproduced, and `jupyter server list` also ignores such files, which is how
it was noticed. A PID check is not enough either: the number is reused, and
a stale file whose PID now belongs to something else would read as alive.
Asking the server itself is the only answer that cannot be wrong -- and it
is cheap, measured at about 30 ms, and returns the running kernel count and
last activity as a bonus.

All of this is Qt-free so it can be tested without a display.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import List

__all__ = ["runtime_dirs", "list_servers", "shutdown_server", "server_url"]

PROBE_TIMEOUT = 1.5


def runtime_dirs() -> List[Path]:
    """Directories that may hold jpserver-*.json files.

    JUPYTER_RUNTIME_DIR wins when set, as it does for Jupyter itself. The
    per-environment paths are included because an environment that sets
    JUPYTER_DATA_DIR writes there instead; they cost one isdir() each.
    """
    out: List[Path] = []
    env = os.environ.get("JUPYTER_RUNTIME_DIR")
    if env:
        out.append(Path(env))
    data = os.environ.get("JUPYTER_DATA_DIR")
    if data:
        out.append(Path(data) / "runtime")
    home = Path.home()
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if appdata:
            out.append(Path(appdata) / "jupyter" / "runtime")
    else:
        out.append(home / ".local" / "share" / "jupyter" / "runtime")
        out.append(home / "Library" / "Jupyter" / "runtime")   # macOS
    seen, uniq = set(), []
    for d in out:
        k = str(d).lower()
        if k not in seen and d.is_dir():
            seen.add(k)
            uniq.append(d)
    return uniq


def server_url(info: dict, path: str = "") -> str:
    """The URL for this server, with its token attached when there is one."""
    base = info.get("url") or ""
    if not base.endswith("/"):
        base += "/"
    url = base + path.lstrip("/")
    token = info.get("token") or ""
    if token:
        url += ("&" if "?" in url else "?") + "token=" + token
    return url


def _probe(info: dict) -> dict:
    """Ask the server whether it is there. Returns {} when it is not."""
    try:
        with urllib.request.urlopen(server_url(info, "api/status"),
                                    timeout=PROBE_TIMEOUT) as r:
            if r.status != 200:
                return {}
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return {}


def list_servers(include_dead: bool = False) -> List[dict]:
    """Every running Jupyter server, newest first.

    Each entry is the file's JSON plus:
        ``file``          the jpserver-*.json path
        ``alive``         the server answered
        ``kernels``       running kernel count, from api/status
        ``last_activity`` ISO timestamp, from api/status
        ``started_at``    the JSON file's mtime, as a float

    `include_dead=True` also returns the stale files, so a dialog can offer
    to tidy them up rather than pretending they were never there.
    """
    out: List[dict] = []
    for d in runtime_dirs():
        try:
            files = sorted(d.glob("jpserver-*.json"))
        except OSError:
            continue
        for f in files:
            try:
                info = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(info, dict) or "url" not in info:
                continue
            info["file"] = str(f)
            try:
                info["started_at"] = f.stat().st_mtime
            except OSError:
                info["started_at"] = 0.0
            status = _probe(info)
            info["alive"] = bool(status)
            info["kernels"] = status.get("kernels", 0)
            info["last_activity"] = status.get("last_activity", "")
            if info["alive"] or include_dead:
                out.append(info)
    out.sort(key=lambda i: i.get("started_at", 0), reverse=True)
    return out


def _pid_gone(pid, deadline: float) -> bool:
    """Wait, up to `deadline`, for the process to actually leave.

    os.kill(pid, 0) is the portable existence test and does not signal. It
    cannot be trusted on its own to decide a server is ALIVE -- PIDs are
    reused -- but it is exactly right for deciding one has GONE, which is
    all this is used for.
    """
    if not isinstance(pid, int) or pid <= 0:
        return True
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except OSError:
            return True
        time.sleep(0.2)
    return False


def shutdown_server(info: dict, wait: float = 8.0) -> tuple:
    """Ask a server to stop. Returns ``(ok, message)``.

    POSTs to the server's own api/shutdown, which lets it close its kernels
    and save state, rather than killing the process. NOTE, measured: the
    server closes the socket as it goes down, so the POST itself usually
    raises a connection error even when it worked. That is why success is
    decided by polling the server afterwards and not by the response.

    Killing the process is the fallback, and only if the polite request got
    nowhere.
    """
    try:
        req = urllib.request.Request(
            server_url(info, "api/shutdown"), data=b"", method="POST")
        urllib.request.urlopen(req, timeout=PROBE_TIMEOUT)
    except Exception:
        pass                      # expected; the server may already be gone

    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        if not _probe(info):
            # Measured: the socket stops answering the instant the shutdown
            # begins, while the process is still closing kernels. Returning
            # "stopped" there is a lie the user can act on -- they relaunch,
            # and the port is still taken. So wait for the process too.
            if _pid_gone(info.get("pid"), deadline):
                return True, "stopped"
            return True, "shutting down (still closing)"
        time.sleep(0.3)

    pid = info.get("pid")
    if isinstance(pid, int) and pid > 0:
        try:
            os.kill(pid, 15)      # SIGTERM; on Windows this terminates
            time.sleep(1.0)
            if not _probe(info):
                return True, "stopped (had to terminate the process)"
        except OSError as e:
            return False, f"could not stop it: {e}"
    return False, "it did not respond to a shutdown request"


def forget_dead(info: dict) -> bool:
    """Delete the leftover jpserver-*.json of a server that is gone.

    Jupyter leaves these behind when a server is killed rather than asked to
    stop, which is why the list has to probe at all.
    """
    f = info.get("file")
    if not f:
        return False
    try:
        Path(f).unlink()
        return True
    except OSError:
        return False
