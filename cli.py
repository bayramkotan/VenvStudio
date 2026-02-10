#!/usr/bin/env python3
"""
VenvStudio CLI - Command-line interface for quick venv operations.

Usage:
    python cli.py create <name>         Create a new virtual environment
    python cli.py delete <name>         Delete an environment
    python cli.py list                  List all environments
    python cli.py clone <src> <dst>     Clone an environment
    python cli.py install <env> <pkgs>  Install packages into an environment
    python cli.py activate <name>       Print activation command

Alias setup (optional):
    Windows PowerShell:
        Set-Alias venv "python C:\\path\\to\\VenvStudio\\cli.py"
    Linux/macOS:
        alias venv="python3 /path/to/VenvStudio/cli.py"
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.venv_manager import VenvManager
from src.core.config_manager import ConfigManager
from src.utils.platform_utils import get_platform


def main():
    config = ConfigManager()
    manager = VenvManager(config.get_venv_base_dir())

    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1].lower()

    if command == "create":
        if len(sys.argv) < 3:
            print("Usage: cli.py create <name>")
            return
        name = sys.argv[2]
        print(f"Creating environment '{name}'...")
        success, msg = manager.create_venv(name, callback=print)
        print(f"{'✅' if success else '❌'} {msg}")

    elif command == "delete":
        if len(sys.argv) < 3:
            print("Usage: cli.py delete <name>")
            return
        name = sys.argv[2]
        confirm = input(f"Delete '{name}'? (y/N): ")
        if confirm.lower() == 'y':
            success, msg = manager.delete_venv(name, callback=print)
            print(f"{'✅' if success else '❌'} {msg}")

    elif command == "list" or command == "ls":
        envs = manager.list_venvs_fast()
        if not envs:
            print("No environments found.")
            return
        print(f"{'Name':<25} {'Python':<12} {'Valid'}")
        print("-" * 45)
        for env in envs:
            valid = "✅" if env.is_valid else "❌"
            print(f"{env.name:<25} {env.python_version:<12} {valid}")

    elif command == "clone":
        if len(sys.argv) < 4:
            print("Usage: cli.py clone <source> <target>")
            return
        source, target = sys.argv[2], sys.argv[3]
        print(f"Cloning '{source}' → '{target}'...")
        success, msg = manager.clone_venv(source, target, callback=print)
        print(f"{'✅' if success else '❌'} {msg}")

    elif command == "install":
        if len(sys.argv) < 4:
            print("Usage: cli.py install <env-name> <pkg1> [pkg2] ...")
            return
        env_name = sys.argv[2]
        packages = sys.argv[3:]
        env_path = manager.base_dir / env_name
        if not env_path.exists():
            print(f"❌ Environment '{env_name}' not found")
            return
        from src.core.pip_manager import PipManager
        pip = PipManager(env_path)
        print(f"Installing {', '.join(packages)} into '{env_name}'...")
        success, msg = pip.install_packages(packages, callback=print)
        print(f"{'✅' if success else '❌'} {msg[:300]}")

    elif command == "activate":
        if len(sys.argv) < 3:
            print("Usage: cli.py activate <name>")
            return
        name = sys.argv[2]
        env_path = manager.base_dir / name
        if not env_path.exists():
            print(f"❌ Environment '{name}' not found")
            return
        platform = get_platform()
        if platform == "windows":
            print(f"# Run this command:")
            print(f"{env_path}\\Scripts\\Activate.ps1")
        else:
            print(f"# Run this command:")
            print(f"source {env_path}/bin/activate")

    elif command == "help" or command == "--help" or command == "-h":
        print(__doc__)

    else:
        print(f"Unknown command: {command}")
        print("Use 'cli.py help' for usage information.")


if __name__ == "__main__":
    main()
