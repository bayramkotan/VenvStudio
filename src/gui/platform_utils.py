"""VenvStudio - launching a command in a new terminal window.

B70 (2026-09-05). This file used to be 455 lines and a COPY of
src/utils/platform_utils.py: ten of its eleven functions were duplicates of
functions defined there, and five of those ten had already drifted apart --
subprocess_args, get_python_executable, get_pip_executable,
find_system_pythons and open_terminal_at behaved differently in the two
files. Nothing imported any of them. A repo-wide grep found exactly three
imports from this module, all of them `launch_in_terminal`, all from
launcher_run.py.

The duplicated copies are gone. get_platform is imported from the one place
that defines it rather than defined a second time here, which is the whole
point of the exercise: this module now has one function and no opinions of
its own about paths, pythons or subprocess flags.

Keeping the file rather than folding launch_in_terminal into
src/utils/platform_utils.py is deliberate for now -- moving it would mean
editing launcher_run.py's three import lines as well, and that file was not
read in this session. The move is worth doing later; the duplication was
worth removing today.
"""

import shutil
import subprocess

from src.utils.platform_utils import get_platform, get_configured_terminal


def launch_in_terminal(cmd: list, cwd: str = "", terminal_type: str = "",
                       env: dict = None) -> bool:
    """Launch a command in a new terminal window (for console apps like IPython).
    Uses the same terminal auto-detection as open_terminal_at.
    Returns True if launched successfully.

    B79 (Bayram, 2026-09-06: "Launcher dan calistirdigimda eski hatayi
    verdi"). `env` carries the ACTIVATED environment. _launch_app builds one
    with the environment's bin directory first on PATH, VIRTUAL_ENV set and
    PYTHONHOME dropped -- and passed it to the console-less branch only. Apps
    launched WITH a console went through here instead and got nothing, so the
    new terminal inherited VenvStudio's own environment: inside JupyterLab,
    `!python --version` answered 3.14 from /usr/bin while the kernel itself
    was correctly the environment's 3.10. One branch activated, its sibling
    did not -- the same shape as the shortcut bug fixed alongside it.

    None means "inherit", which is what every existing caller does.
    """
    # B70: same rule as open_terminal_at gained in v1.6.82 -- an empty
    # terminal_type means "use the one the user chose in Settings", not
    # "guess". This copy never had it, so a launcher app opened in whatever
    # auto-detection found first even when the setting said otherwise.
    if not terminal_type:
        terminal_type = get_configured_terminal()
    system = get_platform()
    cmd_str = " ".join(f'"{c}"' for c in cmd)
    bash_cmd = f"{cmd_str}; echo ''; read -p 'Press Enter to close...'"

    if system == "windows":
        try:
            subprocess.Popen(
                cmd,
                cwd=cwd or None,
                env=env,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            return True
        except Exception:
            return False

    elif system == "macos":
        try:
            # Terminal.app starts its own login shell, so the environment
            # has to travel inside the script rather than on osascript.
            _exports = ""
            if env:
                for _k in ("VIRTUAL_ENV", "PATH"):
                    if env.get(_k):
                        _exports += f"export {_k}=\'{env[_k]}\' && "
                if "PYTHONHOME" not in env:
                    _exports = "unset PYTHONHOME && " + _exports
            script = f'tell application "Terminal" to do script "cd \'{cwd}\' && {_exports}{cmd_str}"'
            subprocess.Popen(["osascript", "-e", script])
            return True
        except Exception:
            return False

    else:  # linux
        # Clean AppImage env vars so terminal processes don't inherit LD_LIBRARY_PATH etc.
        try:
            from src.utils.platform_utils import appimage_clean_env as _ace
            _term_env = _ace()
        except Exception:
            _term_env = None
        # B79: the caller's activated environment wins; the AppImage cleanup
        # is the fallback for when there is none.
        if env is not None:
            _term_kw = {"env": env}
        elif _term_env is not None:
            _term_kw = {"env": _term_env}
        else:
            _term_kw = {}

        def _try_term(term: str) -> bool:
            if not shutil.which(term):
                return False
            try:
                if term == "gnome-terminal":
                    subprocess.Popen([term, "--", "bash", "-c", bash_cmd], cwd=cwd or None, **_term_kw)
                elif term in ("konsole", "yakuake"):
                    subprocess.Popen([term, "--noclose", "-e", "bash", "-c", bash_cmd], cwd=cwd or None, **_term_kw)
                elif term in ("xfce4-terminal", "mate-terminal", "lxterminal", "tilix"):
                    subprocess.Popen([term, "-e", f"bash -c '{bash_cmd}'"], cwd=cwd or None, **_term_kw)
                elif term == "kitty":
                    subprocess.Popen([term, "bash", "-c", bash_cmd], cwd=cwd or None, **_term_kw)
                elif term == "alacritty":
                    subprocess.Popen([term, "-e", "bash", "-c", bash_cmd], cwd=cwd or None, **_term_kw)
                elif term == "wezterm":
                    subprocess.Popen([term, "start", "--", "bash", "-c", bash_cmd], cwd=cwd or None, **_term_kw)
                else:
                    subprocess.Popen([term, "-e", f"bash -c '{bash_cmd}'"], cwd=cwd or None, **_term_kw)
                return True
            except Exception:
                return False

        # Try explicit terminal first
        if terminal_type and terminal_type not in ("", "default"):
            if _try_term(terminal_type):
                return True

        # Auto-detect
        auto_order = [
            "gnome-terminal", "konsole", "xfce4-terminal",
            "tilix", "mate-terminal", "alacritty", "kitty",
            "wezterm", "lxterminal", "xterm", "x-terminal-emulator",
        ]
        for term in auto_order:
            if _try_term(term):
                return True

        # Last resort: run in-place (blocks but better than nothing)
        try:
            subprocess.Popen(cmd, cwd=cwd or None, **_term_kw)
            return True
        except Exception:
            return False
