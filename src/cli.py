"""VenvStudio - Command Line Interface

Qt-free CLI over the same core the GUI uses (VenvManager / PipManager).
Dispatched from src.main:main when subcommand arguments are present, so it
works identically for `pip install venvstudio` and frozen builds
(AppImage / .exe launched with arguments).

Usage examples:
    venvstudio list
    venvstudio create ml
    venvstudio create fast --python /usr/bin/python3.12
    venvstudio packages ml
    venvstudio install ml numpy pandas
    venvstudio uninstall ml numpy
    venvstudio delete ml -y
    venvstudio version
"""
import argparse
import sys

COMMANDS = ("list", "create", "delete", "packages", "install", "uninstall", "version")


def is_cli_invocation(argv) -> bool:
    """True if argv asks for CLI mode (subcommand present)."""
    return len(argv) > 1 and argv[1] in COMMANDS


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


def _cmd_create(args) -> int:
    _config, vm = _managers()
    if _find_env(vm, args.name):
        print(f"Error: environment '{args.name}' already exists.")
        return 1
    ok, msg = vm.create_venv(
        args.name,
        python_path=args.python,
        with_pip=not args.no_pip,
        system_site_packages=args.system_site_packages,
    )
    print(msg)
    return 0 if ok else 1


def _cmd_delete(args) -> int:
    _config, vm = _managers()
    info = _find_env(vm, args.name)
    if not info:
        print(f"Error: environment '{args.name}' not found. Try: venvstudio list")
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
        print(f"Error: environment '{args.env}' not found. Try: venvstudio list")
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
        print(f"Error: environment '{args.env}' not found. Try: venvstudio list")
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
    parser = argparse.ArgumentParser(
        prog="venvstudio",
        description="VenvStudio CLI — manage Python environments without the GUI.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List all environments").set_defaults(func=_cmd_list)

    p = sub.add_parser("create", help="Create a new venv environment")
    p.add_argument("name")
    p.add_argument("--python", help="Path to the Python interpreter to use")
    p.add_argument("--no-pip", action="store_true", help="Create without pip")
    p.add_argument("--system-site-packages", action="store_true")
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

    args = parser.parse_args((argv or sys.argv)[1:])
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nAborted.")
        return 130
