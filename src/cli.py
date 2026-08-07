"""VenvStudio - Command Line Interface

Qt-free CLI over the same core the GUI uses (VenvManager / PipManager).
Dispatched from src.main:main when subcommand arguments are present, so it
works identically for `pip install venvstudio` and frozen builds
(AppImage / .exe launched with arguments). Both `vs` and `venvstudio`
install as entry points and behave identically -- `vs` is just shorter.

Usage examples:
    vs list
    vs create ml
    vs create fast --python /usr/bin/python3.12
    vs create web --type uv
    vs create api --type poetry --python /usr/bin/python3.12
    vs create cnd --type conda --python 3.13
    vs packages ml
    vs install ml numpy pandas
    vs uninstall ml numpy
    vs delete ml -y
    vs version
"""
import argparse
import sys

COMMANDS = ("list", "create", "delete", "packages", "install", "uninstall", "version")


def _normalize_argv(argv):
    """Accept `--create NAME` as an alias for `create NAME` (and the
    same for every other subcommand). argparse subparsers are
    positional by nature, so `--create` alone would be rejected as an
    unrecognized flag -- rewrite it to the positional form first.
    Only argv[1] is ever touched, and only on an exact --<command>
    match, so unrelated flags (including genuinely unknown ones) are
    left alone and still reach argparse's own error message."""
    if len(argv) > 1 and argv[1].startswith("--") and argv[1][2:] in COMMANDS:
        argv = list(argv)
        argv[1] = argv[1][2:]
    return argv


def is_cli_invocation(argv) -> bool:
    """True if argv asks for CLI mode: a known subcommand, or ANY
    dash-prefixed argument. The latter matters because an unrecognized
    flag (a typo, or one that doesn't exist) used to fall straight
    through to launching the GUI silently -- now it reaches argparse,
    which reports the invalid choice and lists what IS available
    instead. This also routes -h/--help/-V/--version through argparse
    (one consistent place) instead of main.py's separate hardcoded
    handling of those two.
    """
    return len(argv) > 1 and (argv[1] in COMMANDS or argv[1].startswith("-"))


def _managers():
    """Build core managers exactly like the GUI does (shared config)."""
    from src.core.config_manager import ConfigManager
    from src.core.venv_manager import VenvManager
    config = ConfigManager()
    return config, VenvManager(config.get_venv_base_dir())


def _find_env(vm, name: str):
    """Resolve an environment by name; returns VenvInfo or None."""
    for info in vm.list_venvs_fast(skip_calc=True):
        if info.name == name:
            return info
    return None


def _cmd_list(args) -> int:
    _config, vm = _managers()
    envs = vm.list_venvs_fast(skip_calc=True)
    if not envs:
        print("No environments found.")
        return 0
    w = max(len(e.name) for e in envs) + 2
    print(f"{'NAME':<{w}}{'TYPE':<8}{'PYTHON':<10}{'PACKAGES':<10}PATH")
    for e in envs:
        etype = getattr(e, "env_type", "") or "venv"
        py = getattr(e, "python_version", "") or "?"
        pkgs = getattr(e, "package_count", "")
        print(f"{e.name:<{w}}{etype:<8}{py:<10}{str(pkgs):<10}{e.path}")
    return 0


def _find_tool(name: str) -> str:
    """Look up a CLI tool (uv/poetry) on PATH. Unlike the GUI, the CLI
    does not auto-install a missing tool -- it reports how to install
    it and stops, which is what CLI users generally expect (no surprise
    background pip installs from a non-interactive command)."""
    import shutil
    return shutil.which(name) or ""


def _create_uv_env(name: str, path, python: str = None):
    """Create a uv-managed venv. Returns (ok, message)."""
    import subprocess
    from src.utils.platform_utils import subprocess_args
    uv_exe = _find_tool("uv")
    if not uv_exe:
        return False, "uv is not installed. Install it with: pip install uv"
    cmd = [uv_exe, "venv", str(path)]
    if python:
        cmd += ["--python", python]
    print(f"$ {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                        **subprocess_args())
    if r.returncode != 0:
        return False, r.stderr[:400] or "uv venv failed"
    # Same marker the GUI writes, so opening VenvStudio later recognises
    # this env as uv-managed instead of a plain venv.
    import json, datetime
    try:
        (path / ".venvstudio_env").write_text(json.dumps({
            "type": "uv", "name": name,
            "created": datetime.datetime.now().isoformat(),
        }, indent=2), encoding="utf-8")
    except Exception:
        pass
    return True, f"uv environment '{name}' created at {path}"


def _create_poetry_env(name: str, path, python: str = None):
    """Create a Poetry-managed venv. Covers the common path (poetry new
    + relax requires-python for the chosen Python + poetry env use);
    the GUI has extra retry/fallback branches for edge cases this
    simpler CLI version does not replicate."""
    import subprocess, re, json, datetime
    from pathlib import Path
    from src.utils.platform_utils import subprocess_args
    poetry_exe = _find_tool("poetry")
    if not poetry_exe:
        return False, "Poetry is not installed. Install it with: pip install poetry"
    path.mkdir(parents=True, exist_ok=True)
    cmd = [poetry_exe, "new", str(path)]
    print(f"$ {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                        cwd=str(path.parent), **subprocess_args())
    if r.returncode != 0:
        return False, r.stderr[:400] or "poetry new failed"

    if python:
        # An unbounded requires-python (">=X.Y") makes Poetry's
        # resolver reject packages carrying version exclusions later
        # (e.g. torchvision "!=3.14.1") -- cap at the next minor so
        # the range matches the ONE Python the env is built with.
        pyproject = path / "pyproject.toml"
        sel_xy = ""
        try:
            vr = subprocess.run(
                [python, "-c", "import sys;print('%d.%d'%sys.version_info[:2])"],
                capture_output=True, text=True, timeout=8, **subprocess_args())
            sel_xy = (vr.stdout.strip() or vr.stderr.strip())
        except Exception:
            pass
        if sel_xy:
            try:
                maj, minr = sel_xy.split(".")
                new_req = f">={sel_xy},<{maj}.{int(minr) + 1}"
            except Exception:
                new_req = f">={sel_xy}"
        else:
            new_req = ">=3.0"
        if pyproject.exists():
            try:
                txt = pyproject.read_text(encoding="utf-8")
                txt2 = re.sub(
                    r'(?m)^(\s*requires-python\s*=\s*)"[^"]*"',
                    lambda m: m.group(1) + f'"{new_req}"', txt)
                if txt2 != txt:
                    pyproject.write_text(txt2, encoding="utf-8")
            except Exception:
                pass
        cmd2 = [poetry_exe, "env", "use", python]
        print(f"$ {' '.join(cmd2)}")
        r2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=60,
                             cwd=str(path), **subprocess_args())
        if r2.returncode != 0:
            print(f"Warning: poetry env use failed: {r2.stderr[:200]}")

    # Resolve + record the REAL venv path (poetry keeps it in its own
    # cache, not inside the project dir), same dual-marker approach
    # the GUI uses so features like Open Terminal can find it later.
    real_venv = ""
    try:
        vr = subprocess.run([poetry_exe, "env", "info", "--path"],
                             capture_output=True, text=True, timeout=10,
                             cwd=str(path), **subprocess_args())
        real_venv = vr.stdout.strip().splitlines()[-1].strip() if vr.stdout.strip() else ""
    except Exception:
        pass
    marker = {
        "type": "poetry", "name": name,
        "poetry_project_dir": str(path),
        "poetry_venv_path": real_venv,
        "created": datetime.datetime.now().isoformat(),
    }
    try:
        (path / ".venvstudio_env").write_text(json.dumps(marker, indent=2), encoding="utf-8")
        if real_venv:
            (Path(real_venv) / ".venvstudio_env").write_text(
                json.dumps(marker, indent=2), encoding="utf-8")
    except Exception:
        pass
    return True, f"poetry environment '{name}' created at {path}"


def _create_conda_env(name: str, path, python: str = None):
    """Create a conda-managed venv via micromamba. Returns (ok, message).
    Reuses the exact same core.micromamba_installer functions the GUI
    uses (create_conda_env / write_conda_marker) -- no subprocess logic
    duplicated here, including mirror rotation and error handling."""
    import subprocess, re
    from src.core.micromamba_installer import (
        get_micromamba_exe, create_conda_env, write_conda_marker,
    )
    if not get_micromamba_exe():
        return False, ("micromamba is not installed. Open VenvStudio once "
                        "and it will download it automatically, or put a "
                        "micromamba binary on PATH yourself.")
    py_version = ""
    if python:
        # Accept a bare version ("3.13") directly, or a Python executable
        # path (extract its version), since conda wants a version tag,
        # not a path -- unlike uv/poetry's --python.
        if re.match(r"^\d+\.\d+$", python):
            py_version = python
        else:
            try:
                from src.utils.platform_utils import subprocess_args
                vr = subprocess.run(
                    [python, "-c", "import sys;print('%d.%d'%sys.version_info[:2])"],
                    capture_output=True, text=True, timeout=8, **subprocess_args())
                py_version = (vr.stdout.strip() or vr.stderr.strip())
            except Exception:
                pass
    _pyspec = f" python={py_version}" if py_version else ""
    print(f"$ micromamba create --prefix {path} -c conda-forge{_pyspec}")
    ok = create_conda_env(path, python_version=py_version,
                          progress_cb=lambda m: print(f"  {m}"))
    if not ok:
        return False, "conda environment creation failed"
    try:
        write_conda_marker(path, python_version=py_version)
    except Exception:
        pass
    return True, f"conda environment '{name}' created at {path}"


def _create_modern_env(name: str, path, env_type: str, python: str = None):
    """Create a Hatch, PDM, or Pixi environment via CLI. Returns (ok, message)."""
    import subprocess, shutil, json, datetime, os
    from src.utils.platform_utils import subprocess_args

    _tool_install_hints = {
        "hatch": "pip install hatch",
        "pdm":   "pip install pdm",
        "pixi":  "curl -fsSL https://pixi.sh/install.sh | bash  (or iwr -useb https://pixi.sh/install.ps1 | iex on Windows)",
    }

    # Find tool executable
    if env_type == "pixi":
        _pixi_cands = [
            os.path.expanduser("~/.pixi/bin/pixi"),
            os.path.join(os.environ.get("USERPROFILE", ""), ".pixi", "bin", "pixi.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), ".pixi", "bin", "pixi.exe"),
        ]
        tool_exe = next((c for c in _pixi_cands if os.path.isfile(c)), None) \
                   or shutil.which("pixi")
    else:
        tool_exe = shutil.which(env_type)

    if not tool_exe:
        return False, (
            f"{env_type} is not installed or not on PATH.\n"
            f"Install it with: {_tool_install_hints.get(env_type, f'pip install {env_type}')}"
        )

    os.makedirs(str(path), exist_ok=True)

    if env_type == "hatch":
        cmd = [tool_exe, "new", name]
        print(f"$ hatch new {name}")
        r = subprocess.run(cmd, capture_output=True, text=True,
                           cwd=str(path.parent), **subprocess_args())
    elif env_type == "pdm":
        cmd = [tool_exe, "init", "--non-interactive"]
        if python:
            cmd += ["--python", python]
        print(f"$ pdm init --non-interactive" + (f" --python {python}" if python else ""))
        r = subprocess.run(cmd, capture_output=True, text=True,
                           cwd=str(path), **subprocess_args())
    elif env_type == "pixi":
        cmd = [tool_exe, "init", str(path)]
        print(f"$ pixi init {path}")
        r = subprocess.run(cmd, capture_output=True, text=True,
                           cwd=str(path.parent), **subprocess_args())

    if r.returncode != 0:
        return False, f"{env_type} init failed:\n{r.stderr or r.stdout or 'unknown error'}"

    # Write marker
    marker = path / ".venvstudio_env"
    try:
        import sys
        _pyver = ""
        if python:
            try:
                _rv = subprocess.run([python, "--version"], capture_output=True,
                                     text=True, timeout=5)
                _pyver = (_rv.stdout.strip() or _rv.stderr.strip()).replace("Python ", "")
            except Exception:
                pass
        if not _pyver:
            _pyver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        with open(str(marker), "w") as f:
            json.dump({
                "type": env_type, "name": name,
                "created": datetime.datetime.now().isoformat(),
                "python": python or "",
                "python_version": _pyver,
            }, f, indent=2)
    except Exception:
        pass

    return True, f"{env_type} environment '{name}' created at {path}"


def _cmd_create(args) -> int:
    _config, vm = _managers()
    if _find_env(vm, args.name):
        print(f"Error: environment '{args.name}' already exists.")
        return 1
    etype = getattr(args, "type", "venv") or "venv"
    if etype == "venv":
        ok, msg = vm.create_venv(
            args.name,
            python_path=args.python,
            with_pip=not args.no_pip,
            system_site_packages=args.system_site_packages,
        )
    else:
        from pathlib import Path
        path = Path(vm.base_dir) / args.name
        if etype == "uv":
            ok, msg = _create_uv_env(args.name, path, args.python)
        elif etype == "poetry":
            ok, msg = _create_poetry_env(args.name, path, args.python)
        elif etype == "conda":
            ok, msg = _create_conda_env(args.name, path, args.python)
        elif etype in ("hatch", "pdm", "pixi"):
            ok, msg = _create_modern_env(args.name, path, etype, args.python)
        else:
            ok, msg = False, f"--type {etype} is not supported yet"
    print(msg)
    return 0 if ok else 1


def _cmd_delete(args) -> int:
    _config, vm = _managers()
    info = _find_env(vm, args.name)
    if not info:
        print(f"Error: environment '{args.name}' not found. Try: vs list")
        return 1
    if not args.yes:
        reply = input(f"Delete environment '{args.name}' at {info.path}? [y/N] ")
        if reply.strip().lower() not in ("y", "yes", "e", "evet"):
            print("Aborted.")
            return 1
    ok, msg = vm.delete_venv(
        args.name,
        env_path=str(info.path),
        env_type=getattr(info, "env_type", "venv") or "venv",
    )
    print(msg)
    return 0 if ok else 1


def _pip_manager_for(info):
    from pathlib import Path
    from src.core.pip_manager import PipManager
    backend_map = {"uv": "uv", "poetry": "pip", "conda": "pip", "pipx": "pip"}
    etype = getattr(info, "env_type", "venv") or "venv"
    return PipManager(Path(info.path), backend=backend_map.get(etype, "pip"))


def _cmd_packages(args) -> int:
    _config, vm = _managers()
    info = _find_env(vm, args.env)
    if not info:
        print(f"Error: environment '{args.env}' not found. Try: vs list")
        return 1
    pm = _pip_manager_for(info)
    pkgs = pm.list_packages()
    if not pkgs:
        print("(no packages)")
        return 0
    for p in pkgs:
        name = p.get("name") if isinstance(p, dict) else getattr(p, "name", str(p))
        ver = p.get("version") if isinstance(p, dict) else getattr(p, "version", "")
        print(f"{name}=={ver}" if ver else name)
    return 0


def _cmd_install(args) -> int:
    return _pkg_op(args, install=True)


def _cmd_uninstall(args) -> int:
    return _pkg_op(args, install=False)


def _pkg_op(args, install: bool) -> int:
    _config, vm = _managers()
    info = _find_env(vm, args.env)
    if not info:
        print(f"Error: environment '{args.env}' not found. Try: vs list")
        return 1
    pm = _pip_manager_for(info)
    verb = "Installing" if install else "Uninstalling"
    print(f"{verb} in '{args.env}': {' '.join(args.packages)}")
    fn = pm.install_packages if install else pm.uninstall_packages
    ok, output = fn(args.packages)
    if output:
        print(output.strip())
    print("OK" if ok else "FAILED")
    return 0 if ok else 1


def _cmd_version(args) -> int:
    from src.utils.constants import APP_VERSION
    print(f"VenvStudio v{APP_VERSION}")
    return 0


def run_cli(argv=None) -> int:
    """Parse arguments and run the requested subcommand. Returns exit code."""
    from src.utils.constants import APP_VERSION
    parser = argparse.ArgumentParser(
        prog="vs",
        description="VenvStudio CLI — manage Python environments without the GUI.",
        epilog=(
            "Examples:\n"
            "  vs                                Launch GUI\n"
            "  vs list                           List all environments\n"
            "  vs create NAME                    Create a plain venv\n"
            "  vs create NAME -t uv              Create a uv-managed venv\n"
            "  vs create NAME -t poetry --python PATH\n"
            "                                     Create a Poetry-managed venv\n"
            "  vs create NAME -t conda --python 3.13\n"
            "                                     Create a conda-managed venv\n"
            "  vs delete NAME [-y]               Delete an environment\n"
            "  vs packages ENV                   List packages in an environment\n"
            "  vs install ENV PKG [PKG ...]      Install packages\n"
            "  vs uninstall ENV PKG [PKG ...]    Uninstall packages\n"
            "  vs version                        Show version\n"
            "\n"
            "Every subcommand also works as --<command>, e.g.\n"
            "  vs --create NAME  is the same as  vs create NAME"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-V", "--version", action="version",
        version=f"VenvStudio v{APP_VERSION}",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List all environments").set_defaults(func=_cmd_list)

    p = sub.add_parser("create", help="Create a new environment")
    p.add_argument("name")
    p.add_argument("-t", "--type", choices=["venv", "uv", "poetry", "conda", "hatch", "pdm", "pixi"], default="venv",
                    help="Environment type (default: venv). pipx not supported here.")
    p.add_argument("--python", help="Path to the Python interpreter to use")
    p.add_argument("--no-pip", action="store_true", help="Create without pip (venv type only)")
    p.add_argument("--system-site-packages", action="store_true", help="venv type only")
    p.set_defaults(func=_cmd_create)

    p = sub.add_parser("delete", help="Delete an environment")
    p.add_argument("name")
    p.add_argument("-y", "--yes", action="store_true", help="Do not ask for confirmation")
    p.set_defaults(func=_cmd_delete)

    p = sub.add_parser("packages", help="List packages in an environment")
    p.add_argument("env")
    p.set_defaults(func=_cmd_packages)

    p = sub.add_parser("install", help="Install packages into an environment")
    p.add_argument("env")
    p.add_argument("packages", nargs="+")
    p.set_defaults(func=_cmd_install)

    p = sub.add_parser("uninstall", help="Uninstall packages from an environment")
    p.add_argument("env")
    p.add_argument("packages", nargs="+")
    p.set_defaults(func=_cmd_uninstall)

    sub.add_parser("version", help="Show VenvStudio version").set_defaults(func=_cmd_version)

    _argv = _normalize_argv(list(argv or sys.argv))
    args = parser.parse_args(_argv[1:])
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nAborted.")
        return 130
