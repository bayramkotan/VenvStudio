#!/usr/bin/env python3
"""
VenvStudio CLI — Command-line interface for VenvStudio
Usage:
    vs create <name> [--python <path>]
    vs delete <name> [--yes]
    vs list
    vs clone <source> <target>
    vs activate <name>
    vs install <name> <packages...>
    vs uninstall <name> <packages...>
    vs freeze <name>
    vs gui
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.venv_manager import VenvManager
from src.core.config_manager import ConfigManager
from src.utils.platform_utils import get_platform


def print_status(msg):
    print(f"  → {msg}")


def cmd_list(args, mgr):
    """List all environments."""
    envs = mgr.list_envs()
    if not envs:
        print("No virtual environments found.")
        return
    print(f"\n{'Name':<25} {'Python':<12} {'Packages':<10} {'Size':<10}")
    print("─" * 60)
    for e in envs:
        print(f"  {e.name:<23} {e.python_version:<12} {e.package_count:<10} {e.size_display:<10}")
    print(f"\n  Total: {len(envs)} environments")
    print(f"  Location: {mgr.base_dir}\n")


def cmd_create(args, mgr):
    """Create a new environment."""
    name = args.name
    print(f"\n  Creating environment '{name}'...")

    def cb(msg):
        print_status(msg)

    python_path = args.python if args.python else None
    success, msg = mgr.create_venv(name, python_path=python_path, callback=cb)
    if success:
        print(f"  ✅ Environment '{name}' created successfully!\n")
    else:
        print(f"  ❌ Failed: {msg}\n")
        sys.exit(1)


def cmd_delete(args, mgr):
    """Delete an environment."""
    name = args.name
    if not args.yes:
        confirm = input(f"  Delete environment '{name}'? [y/N]: ").strip().lower()
        if confirm != "y":
            print("  Cancelled.")
            return

    success, msg = mgr.delete_venv(name)
    if success:
        print(f"  ✅ Environment '{name}' deleted.\n")
    else:
        print(f"  ❌ Failed: {msg}\n")
        sys.exit(1)


def cmd_clone(args, mgr):
    """Clone an environment."""
    print(f"\n  Cloning '{args.source}' → '{args.target}'...")

    def cb(msg):
        print_status(msg)

    success, msg = mgr.clone_venv(args.source, args.target, callback=cb)
    if success:
        print(f"  ✅ Cloned successfully!\n")
    else:
        print(f"  ❌ Failed: {msg}\n")
        sys.exit(1)


def cmd_activate(args, mgr):
    """Print activation command."""
    env_path = mgr.base_dir / args.name
    if not env_path.exists():
        print(f"  ❌ Environment '{args.name}' not found.")
        sys.exit(1)

    if get_platform() == "windows":
        cmd = f"{env_path}\\Scripts\\Activate.ps1"
    else:
        cmd = f"source {env_path}/bin/activate"
    print(f"\n  Run this command to activate:\n  {cmd}\n")


def cmd_install(args, mgr):
    """Install packages in an environment."""
    from src.core.pip_manager import PipManager
    env_path = mgr.base_dir / args.name
    if not env_path.exists():
        print(f"  ❌ Environment '{args.name}' not found.")
        sys.exit(1)

    pip = PipManager(env_path)
    print(f"\n  Installing {', '.join(args.packages)} into '{args.name}'...")
    success, output = pip.install_packages(args.packages)
    if success:
        print(f"  ✅ Installed successfully!\n")
    else:
        print(f"  ❌ {output}\n")
        sys.exit(1)


def cmd_uninstall(args, mgr):
    """Uninstall packages from an environment."""
    from src.core.pip_manager import PipManager
    env_path = mgr.base_dir / args.name
    if not env_path.exists():
        print(f"  ❌ Environment '{args.name}' not found.")
        sys.exit(1)

    pip = PipManager(env_path)
    print(f"\n  Uninstalling {', '.join(args.packages)} from '{args.name}'...")
    success, output = pip.uninstall_packages(args.packages)
    if success:
        print(f"  ✅ Uninstalled successfully!\n")
    else:
        print(f"  ❌ {output}\n")
        sys.exit(1)


def cmd_freeze(args, mgr):
    """Show pip freeze for an environment."""
    from src.core.pip_manager import PipManager
    env_path = mgr.base_dir / args.name
    if not env_path.exists():
        print(f"  ❌ Environment '{args.name}' not found.")
        sys.exit(1)

    pip = PipManager(env_path)
    output = pip.freeze()
    if output:
        print(output)
    else:
        print("  No packages installed.")


def cmd_gui(args, mgr):
    """Launch the GUI."""
    import subprocess
    subprocess.Popen([sys.executable, str(PROJECT_ROOT / "main.py")])
    print("  VenvStudio GUI launched.")


def main():
    parser = argparse.ArgumentParser(
        prog="vs",
        description="VenvStudio CLI — Python Virtual Environment Manager",
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # list
    sub.add_parser("list", aliases=["ls"], help="List all environments")

    # create
    p = sub.add_parser("create", aliases=["new"], help="Create a new environment")
    p.add_argument("name", help="Environment name")
    p.add_argument("--python", help="Python executable path", default=None)

    # delete
    p = sub.add_parser("delete", aliases=["rm"], help="Delete an environment")
    p.add_argument("name", help="Environment name")
    p.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")

    # clone
    p = sub.add_parser("clone", help="Clone an environment")
    p.add_argument("source", help="Source environment name")
    p.add_argument("target", help="Target environment name")

    # activate
    p = sub.add_parser("activate", help="Show activation command")
    p.add_argument("name", help="Environment name")

    # install
    p = sub.add_parser("install", help="Install packages")
    p.add_argument("name", help="Environment name")
    p.add_argument("packages", nargs="+", help="Package names")

    # uninstall
    p = sub.add_parser("uninstall", help="Uninstall packages")
    p.add_argument("name", help="Environment name")
    p.add_argument("packages", nargs="+", help="Package names")

    # freeze
    p = sub.add_parser("freeze", help="Show installed packages")
    p.add_argument("name", help="Environment name")

    # gui
    sub.add_parser("gui", help="Launch the graphical interface")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    config = ConfigManager()
    mgr = VenvManager(config)

    commands = {
        "list": cmd_list, "ls": cmd_list,
        "create": cmd_create, "new": cmd_create,
        "delete": cmd_delete, "rm": cmd_delete,
        "clone": cmd_clone,
        "activate": cmd_activate,
        "install": cmd_install,
        "uninstall": cmd_uninstall,
        "freeze": cmd_freeze,
        "gui": cmd_gui,
    }

    func = commands.get(args.command)
    if func:
        func(args, mgr)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
