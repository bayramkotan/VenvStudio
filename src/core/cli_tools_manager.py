"""
VenvStudio — CLI/TUI Tools Manager
Manages installation of Starship, Oh My Posh, Rich, Textual, Prompt Toolkit.
Also handles Nerd Font download and installation.
"""

import os
import sys
import json
import shutil
import platform
import subprocess
import zipfile
import tarfile
import tempfile
from pathlib import Path
from typing import Optional, Callable

from PySide6.QtCore import QThread, Signal

# ── Constants ────────────────────────────────────────────────────────────────

SYSTEM = platform.system()  # "Windows", "Linux", "Darwin"
ARCH   = platform.machine().lower()  # "amd64", "x86_64", "arm64", "aarch64"

# Starship GitHub releases
STARSHIP_RELEASES = "https://github.com/starship/starship/releases/latest/download/"
STARSHIP_BINS = {
    ("Windows", "amd64"):   "starship-x86_64-pc-windows-msvc.zip",
    ("Windows", "x86_64"):  "starship-x86_64-pc-windows-msvc.zip",
    ("Linux",   "x86_64"):  "starship-x86_64-unknown-linux-musl.tar.gz",
    ("Linux",   "aarch64"): "starship-aarch64-unknown-linux-musl.tar.gz",
    ("Darwin",  "x86_64"):  "starship-x86_64-apple-darwin.tar.gz",
    ("Darwin",  "arm64"):   "starship-aarch64-apple-darwin.tar.gz",
}

# Oh My Posh GitHub releases
OMP_RELEASES = "https://github.com/JanDeDobbeleer/oh-my-posh/releases/latest/download/"
OMP_THEMES_URL = "https://github.com/JanDeDobbeleer/oh-my-posh/releases/latest/download/themes.zip"
OMP_BINS = {
    ("Windows", "amd64"):   "posh-windows-amd64.exe",
    ("Windows", "x86_64"):  "posh-windows-amd64.exe",
    ("Linux",   "x86_64"):  "posh-linux-amd64",
    ("Linux",   "aarch64"): "posh-linux-arm64",
    ("Darwin",  "x86_64"):  "posh-darwin-amd64",
    ("Darwin",  "arm64"):   "posh-darwin-arm64",
}

# Oh My Posh themes list (popular ones)
OMP_THEMES = [
    "agnoster", "aliens", "amro", "atomic", "avit", "blueish",
    "blue-owl", "bubblesextra", "capr4n", "catppuccin", "catppuccin_frappe",
    "catppuccin_latte", "catppuccin_macchiato", "catppuccin_mocha",
    "chips", "clean-detailed", "cloud-native-azure", "craver",
    "darkblood", "di4am0nd", "dracula", "easy-term", "emodipt-extend",
    "fish", "free-ukraine", "gmay", "gruvbox", "half-life", "honukai",
    "hotstick.minimal", "hul10", "huvix", "if_tea", "iterm2",
    "jandedobbeleer", "jblab_2021", "jonnychipz", "json", "jtracey93",
    "juanillo", "kali", "lambdageneration", "larserikfinholt",
    "lightgreen", "lima", "M365Princess", "marcduiker", "markbull",
    "material", "microverse-power", "mojada", "montys", "mt",
    "negligible", "neko", "night-owl", "nordtron", "nu4a", "onehalf.minimal",
    "paradox", "pararussel", "patriksvensson", "peru", "pixelrobots",
    "plague", "poshmon", "powerlevel10k_classic", "powerlevel10k_lean",
    "powerlevel10k_modern", "powerlevel10k_rainbow", "probua.minimal",
    "pure", "quick-term", "remk", "robbyrussell", "rudolfs.minimal",
    "schema", "sim-web", "slim", "smoothie", "sonicboom", "sorin",
    "space", "spaceship", "star", "stelbent", "takuya", "thecyberden",
    "the-unnamed", "tokyonight_storm", "tonybaloney", "unicorn",
    "uvarain", "velvet", "wholespace", "wopian", "xtoys", "ys", "zash",
]

# Starship presets (id → description)
STARSHIP_PRESETS = {
    "no-nerd-font":          "🔤 Works without Nerd Font — uses plain Unicode",
    "bracketed-segments":    "[ ] Wraps each module in brackets",
    "plain-text-symbols":    "📝 Text-only symbols (no special glyphs)",
    "no-runtime-versions":   "🚫 Hides runtime versions (node, python, rust...)",
    "no-empty-icons":        "🧹 Hides icons when module has no content",
    "gruvbox-rainbow":       "🌈 Gruvbox colors with rainbow powerline",
    "jetpack":               "🚀 Futuristic prompt with powerline arrows",
    "tokyo-night":           "🌃 Tokyo Night color scheme",
    "pastel-powerline":      "🎨 Soft pastel colors with powerline glyphs",
    "nerd-font-symbols":     "🔣 Replaces text with Nerd Font symbols",
}
STARSHIP_PRESET_NAMES = list(STARSHIP_PRESETS.keys())


def get_starship_toml_path() -> Path:
    """Return the path to starship.toml config file."""
    return _get_config_dir() / "starship.toml"


def read_starship_toml() -> str:
    """Read starship.toml content. Returns empty string if not found."""
    p = get_starship_toml_path()
    if p.exists():
        try:
            return p.read_text(encoding="utf-8")
        except Exception:
            return ""
    return ""


def write_starship_toml(content: str) -> bool:
    """Write content to starship.toml. Returns True on success."""
    p = get_starship_toml_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return True
    except Exception:
        return False

# Nerd Fonts (popular)
NERD_FONTS = [
    ("JetBrainsMono", "JetBrains Mono"),
    ("FiraCode",      "Fira Code"),
    ("Hack",          "Hack"),
    ("SourceCodePro", "Source Code Pro"),
    ("CascadiaCode",  "Cascadia Code"),
    ("Meslo",         "Meslo LG"),
    ("RobotoMono",    "Roboto Mono"),
    ("UbuntuMono",    "Ubuntu Mono"),
    ("Mononoki",      "Mononoki"),
    ("NerdFontsSymbolsOnly", "Symbols Only"),
]
NERD_FONTS_BASE = "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/"

# pip-based tools
# ── Terminal Emulators ────────────────────────────────────────────────────────
TERMINAL_APPS = {
    "wezterm": {
        "name":  "WezTerm",
        "icon":  "⚡",
        "desc":  "GPU-accelerated, Lua config, built-in multiplexer. The power user's choice.",
        "url":   "https://wezfurlong.org/wezterm/",
        "install": {
            "linux":   "curl -fsSL https://apt.fury.io/wez/gpg.key | sudo gpg --yes --dearmor -o /usr/share/keyrings/wezterm-fury.gpg && echo 'deb [signed-by=/usr/share/keyrings/wezterm-fury.gpg] https://apt.fury.io/wez/ * *' | sudo tee /etc/apt/sources.list.d/wezterm.list && sudo apt update && sudo apt install -y wezterm",
            "arch":    "yay -S wezterm || paru -S wezterm || sudo pacman -S wezterm",
            "fedora":  "sudo dnf install -y wezterm",
            "macos":   "brew install --cask wezterm",
            "windows": "winget install wez.wezterm",
        },
        "check_cmd":   ["wezterm", "--version"],
        "uninstall": {
            "linux":   "sudo apt remove -y wezterm",
            "arch":    "sudo pacman -R --noconfirm wezterm",
            "fedora":  "sudo dnf remove -y wezterm",
            "macos":   "brew uninstall --cask wezterm",
            "windows": "winget uninstall wez.wezterm",
        },
    },
    "alacritty": {
        "name":  "Alacritty",
        "icon":  "🚀",
        "desc":  "The fastest terminal emulator. GPU-accelerated, minimal, blazing fast.",
        "url":   "https://alacritty.org/",
        "install": {
            "linux":   "sudo apt install -y alacritty",
            "arch":    "sudo pacman -S --noconfirm alacritty",
            "fedora":  "sudo dnf install -y alacritty",
            "macos":   "brew install --cask alacritty",
            "windows": "winget install Alacritty.Alacritty",
        },
        "check_cmd":   ["alacritty", "--version"],
        "uninstall": {
            "linux":   "sudo apt remove -y alacritty",
            "arch":    "sudo pacman -R --noconfirm alacritty",
            "fedora":  "sudo dnf remove -y alacritty",
            "macos":   "brew uninstall --cask alacritty",
            "windows": "winget uninstall Alacritty.Alacritty",
        },
    },
    "tabby": {
        "name":  "Tabby",
        "icon":  "🔷",
        "desc":  "Modern, feature-rich terminal with SSH/Telnet/Serial built-in. Plugin ecosystem.",
        "url":   "https://tabby.sh/",
        "install": {
            "linux":   "curl -sL https://packagecloud.io/eugeny/tabby/gpgkey | sudo apt-key add - && sudo sh -c 'echo deb https://packagecloud.io/eugeny/tabby/ubuntu/ focal main > /etc/apt/sources.list.d/tabby.list' && sudo apt update && sudo apt install -y tabby-terminal",
            "arch":    "yay -S tabby-bin || paru -S tabby-bin",
            "macos":   "brew install --cask tabby",
            "windows": "winget install eugeny.tabby",
        },
        "check_cmd":   ["tabby", "--version"],
        "uninstall": {
            "linux":   "sudo apt remove -y tabby-terminal",
            "arch":    "sudo pacman -R --noconfirm tabby-bin",
            "macos":   "brew uninstall --cask tabby",
            "windows": "winget uninstall eugeny.tabby",
        },
    },
    "ghostty": {
        "name":  "Ghostty",
        "icon":  "👻",
        "desc":  "Native, fast, and modern. Zig-powered with platform-native feel.",
        "url":   "https://ghostty.org/",
        "install": {
            "linux":   "# Download from https://ghostty.org/download",
            "arch":    "yay -S ghostty || paru -S ghostty",
            "macos":   "brew install --cask ghostty",
            "windows": "winget install ghostty",
        },
        "check_cmd":   ["ghostty", "--version"],
        "uninstall": {
            "arch":    "sudo pacman -R --noconfirm ghostty",
            "macos":   "brew uninstall --cask ghostty",
            "windows": "winget uninstall ghostty",
        },
    },
    "hyper": {
        "name":  "Hyper",
        "icon":  "💜",
        "desc":  "JS/HTML/CSS based terminal. Highly customizable with plugins and themes.",
        "url":   "https://hyper.is/",
        "install": {
            "linux":   "sudo apt install -y hyper",
            "arch":    "yay -S hyper || paru -S hyper",
            "macos":   "brew install --cask hyper",
            "windows": "winget install Vercel.Hyper",
        },
        "check_cmd":   ["hyper", "--version"],
        "uninstall": {
            "linux":   "sudo apt remove -y hyper",
            "arch":    "sudo pacman -R --noconfirm hyper",
            "macos":   "brew uninstall --cask hyper",
            "windows": "winget uninstall Vercel.Hyper",
        },
    },
}

def get_terminal_version(terminal_id: str) -> Optional[str]:
    """Return installed version of a terminal emulator, or None."""
    app = TERMINAL_APPS.get(terminal_id)
    if not app:
        return None
    try:
        import shutil, platform as _plat
        exe = app["check_cmd"][0]

        # Find executable: shutil.which first, then Windows-specific paths
        exe_path = shutil.which(exe)
        if not exe_path and _plat.system() == "Windows":
            # Common Windows install paths
            import os
            win_paths = [
                os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), exe.split(".")[0], exe + ".exe"),
                os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), exe.split(".")[0], exe.title() + ".exe"),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", exe, exe + ".exe"),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), exe, exe + ".exe"),
            ]
            # Also try winget installed locations
            for wp in win_paths:
                if os.path.isfile(wp):
                    exe_path = wp
                    break

        if not exe_path:
            # Last resort: try running directly (may be in PATH via refresh)
            try:
                r = subprocess.run(app["check_cmd"], capture_output=True, text=True, timeout=5)
                if r.returncode == 0:
                    out = (r.stdout or r.stderr).strip().split("\n")[0]
                    return out if out else "installed"
            except Exception:
                pass
            return None

        cmd = [exe_path] + app["check_cmd"][1:]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            out = (r.stdout or r.stderr).strip().split("\n")[0]
            return out if out else "installed"
    except Exception:
        pass
    return None

def install_terminal(terminal_id: str, callback=None) -> tuple:
    """Install a terminal emulator. Returns (success, message)."""
    import platform as _plat
    app = TERMINAL_APPS.get(terminal_id)
    if not app:
        return False, f"Unknown terminal: {terminal_id}"

    sys_name = _plat.system().lower()
    # Detect Linux distro
    if sys_name == "linux":
        try:
            with open("/etc/os-release") as f:
                os_rel = f.read().lower()
            if "arch" in os_rel or "manjaro" in os_rel or "cachyos" in os_rel:
                distro = "arch"
            elif "fedora" in os_rel or "rhel" in os_rel or "centos" in os_rel:
                distro = "fedora"
            else:
                distro = "linux"
        except Exception:
            distro = "linux"
        install_cmd = app["install"].get(distro) or app["install"].get("linux")
    elif sys_name == "darwin":
        install_cmd = app["install"].get("macos")
    else:
        install_cmd = app["install"].get("windows")

    if not install_cmd or install_cmd.startswith("#"):
        url = app.get("url", "")
        return False, f"Automatic install not available.\nDownload from: {url}"

    if callback:
        callback(f"Installing {app['name']}...")
    try:
        from src.utils.platform_utils import subprocess_args
        result = subprocess.run(
            install_cmd, shell=True, timeout=300,
            **subprocess_args(capture_output=True, text=True)
        )
        if result.returncode == 0:
            return True, f"✅ {app['name']} installed successfully"
        else:
            return False, f"Install failed:\n{result.stderr[:400] or result.stdout[:400]}"
    except subprocess.TimeoutExpired:
        return False, "Install timed out (300s)"
    except Exception as e:
        return False, f"Error: {e}"

def uninstall_terminal(terminal_id: str, callback=None) -> tuple:
    """Uninstall a terminal emulator. Returns (success, message)."""
    import platform as _plat
    app = TERMINAL_APPS.get(terminal_id)
    if not app:
        return False, f"Unknown terminal: {terminal_id}"

    sys_name = _plat.system().lower()
    if sys_name == "linux":
        try:
            with open("/etc/os-release") as f:
                os_rel = f.read().lower()
            if "arch" in os_rel or "manjaro" in os_rel or "cachyos" in os_rel:
                distro = "arch"
            elif "fedora" in os_rel or "rhel" in os_rel:
                distro = "fedora"
            else:
                distro = "linux"
        except Exception:
            distro = "linux"
        uninstall_cmd = app.get("uninstall", {}).get(distro) or app.get("uninstall", {}).get("linux")
    elif sys_name == "darwin":
        uninstall_cmd = app.get("uninstall", {}).get("macos")
    else:
        uninstall_cmd = app.get("uninstall", {}).get("windows")

    if not uninstall_cmd:
        return False, f"Uninstall command not available for this platform."

    if callback:
        callback(f"Uninstalling {app['name']}...")
    try:
        from src.utils.platform_utils import subprocess_args
        result = subprocess.run(
            uninstall_cmd, shell=True, timeout=120,
            **subprocess_args(capture_output=True, text=True)
        )
        if result.returncode == 0:
            return True, f"✅ {app['name']} uninstalled"
        else:
            return False, f"Uninstall failed:\n{result.stderr[:400] or result.stdout[:400]}"
    except Exception as e:
        return False, f"Error: {e}"


PIP_TOOLS = {
    "rich":           {"pip": "rich",           "desc": "Rich text and beautiful formatting in the terminal"},
    "textual":        {"pip": "textual",         "desc": "Rapid framework for terminal-based UIs"},
    "prompt_toolkit": {"pip": "prompt_toolkit",  "desc": "Library for building interactive CLI applications"},
}

# ── Install dirs ──────────────────────────────────────────────────────────────

def _get_bin_dir() -> Path:
    """Return user-level bin directory for CLI tool binaries."""
    if SYSTEM == "Windows":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "VenvStudio" / "bin"
    return Path.home() / ".local" / "bin"


def _get_config_dir() -> Path:
    """Return config directory for CLI tools."""
    if SYSTEM == "Windows":
        return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    return Path.home() / ".config"


def _get_omp_dir() -> Path:
    """Return the user-level oh-my-posh installation directory.

    Layout (B181 fix):
        ~/.posh/                       (Linux/macOS)
        %USERPROFILE%\\.posh\\          (Windows)
            ├── oh-my-posh(.exe)       — binary
            └── themes/                — *.omp.json files
                ├── jandedobbeleer.omp.json
                ├── agnoster.omp.json
                └── ...

    Previously the binary went to ~/.local/bin and themes lived wherever
    `oh-my-posh env home` reported (a command that no longer exists in
    recent oh-my-posh releases), which broke `configure` with
    `Error: unknown command "env" for "oh-my-posh"`.
    """
    return Path.home() / ".posh"


def _get_omp_themes_dir() -> Path:
    return _get_omp_dir() / "themes"


# ── Detection ─────────────────────────────────────────────────────────────────

def get_tool_version(tool: str) -> Optional[str]:
    """Return installed version string or None."""
    try:
        if tool == "starship":
            # Try PATH first, then VenvStudio bin dir
            for cmd in ["starship", str(_get_bin_dir() / "starship")]:
                try:
                    r = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=5)
                    if r.returncode == 0:
                        return r.stdout.strip().split("\n")[0]
                except (FileNotFoundError, OSError):
                    continue
            return None
        elif tool == "oh-my-posh":
            exe = "oh-my-posh" if SYSTEM != "Windows" else "oh-my-posh.exe"
            # B181 fix: check ~/.posh/ FIRST (new layout), then PATH and
            # legacy ~/.local/bin location for backward compat.
            for cmd in [str(_get_omp_dir() / exe), exe, str(_get_bin_dir() / exe)]:
                try:
                    r = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=5)
                    if r.returncode == 0:
                        return r.stdout.strip()
                except (FileNotFoundError, OSError):
                    continue
            return None
        elif tool in PIP_TOOLS:
            pkg_name = PIP_TOOLS[tool]["pip"]
            # 1. Try importlib.metadata (fast, works if installed in same Python)
            try:
                import importlib.metadata
                return importlib.metadata.version(pkg_name)
            except Exception:
                pass
            # 2. Try importlib.util.find_spec
            import importlib.util
            if importlib.util.find_spec(tool.replace("-", "_")):
                return "installed"
            # 3. Fall back to pip show (slower but cross-environment)
            try:
                r = subprocess.run(
                    [sys.executable, "-m", "pip", "show", pkg_name],
                    capture_output=True, text=True, timeout=10
                )
                if r.returncode == 0:
                    for line in r.stdout.splitlines():
                        if line.startswith("Version:"):
                            return line.split(":", 1)[1].strip()
                    return "installed"
            except Exception:
                pass
        return None
    except Exception:
        return None


def is_tool_installed(tool: str) -> bool:
    return get_tool_version(tool) is not None


# ── Shell config ──────────────────────────────────────────────────────────────

def _get_shell_configs() -> list[Path]:
    """Return list of shell config files that exist."""
    configs = []
    home = Path.home()
    candidates = [
        home / ".bashrc",
        home / ".bash_profile",
        home / ".zshrc",
        home / ".config" / "fish" / "config.fish",
    ]
    if SYSTEM == "Windows":
        # PowerShell profile
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "echo $PROFILE"],
            capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0 and r.stdout.strip():
            ps_profile = Path(r.stdout.strip())
            if not ps_profile.exists():
                ps_profile.parent.mkdir(parents=True, exist_ok=True)
                ps_profile.touch()
            candidates.append(ps_profile)
    return [p for p in candidates if p.exists()]


def _inject_shell_config(config_path: Path, marker: str, snippet: str):
    """Add snippet to shell config. If a block with the same marker already
    exists, REPLACE it (so configure-with-different-theme actually updates
    the file instead of leaving the old line behind)."""
    content = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    if marker in content:
        # Remove the old block first so we can write the new snippet
        _remove_shell_config(config_path, marker)
    with open(config_path, "a", encoding="utf-8") as f:
        f.write(f"\n# Added by VenvStudio — {marker}\n{snippet}\n")


def _remove_shell_config(config_path: Path, marker: str):
    """Remove snippet from shell config."""
    if not config_path.exists():
        return
    lines = config_path.read_text(encoding="utf-8").splitlines(keepends=True)
    new_lines = []
    skip = False
    for line in lines:
        if f"# Added by VenvStudio — {marker}" in line:
            skip = True
            continue
        if skip and line.strip() == "":
            skip = False
            continue
        if skip:
            continue
        new_lines.append(line)
    config_path.write_text("".join(new_lines), encoding="utf-8")


def configure_starship(preset: Optional[str] = None) -> list[str]:
    """Write starship init to shell configs. Returns list of configured files."""
    configured = []
    for cfg in _get_shell_configs():
        name = cfg.name
        if name in (".bashrc", ".bash_profile"):
            snippet = 'command -v starship &>/dev/null && eval "$(starship init bash)"'
        elif name == ".zshrc":
            snippet = 'command -v starship &>/dev/null && eval "$(starship init zsh)"'
        elif name == "config.fish":
            snippet = "type -q starship; and starship init fish | source"
        elif name.endswith(".ps1"):
            snippet = 'if (Get-Command starship -ErrorAction SilentlyContinue) { Invoke-Expression (&starship init powershell) }'
        else:
            continue
        _inject_shell_config(cfg, "starship", snippet)
        configured.append(str(cfg))

    # Apply preset if given
    if preset:
        try:
            subprocess.run(
                ["starship", "preset", preset, "-o",
                 str(get_starship_toml_path())],
                timeout=10
            )
        except Exception:
            pass
    return configured


def configure_omp(theme: str = "jandedobbeleer") -> list[str]:
    """Write oh-my-posh init to shell configs.

    B181 fix: previously this used `$(oh-my-posh env home)/themes/...`,
    but `env home` was removed from oh-my-posh in newer releases and
    crashes with "unknown command env". We now write the absolute path
    to ~/.posh/themes/<theme>.omp.json that _install_binary_omp creates.
    """
    configured = []
    omp_dir = _get_omp_dir()
    themes_dir = _get_omp_themes_dir()
    if SYSTEM == "Windows":
        exe = str(omp_dir / "oh-my-posh.exe")
        theme_path = str(themes_dir / f"{theme}.omp.json")
    else:
        exe = str(omp_dir / "oh-my-posh")
        theme_path = str(themes_dir / f"{theme}.omp.json")

    for cfg in _get_shell_configs():
        name = cfg.name
        if name in (".bashrc", ".bash_profile"):
            snippet = f'command -v "{exe}" >/dev/null 2>&1 && eval "$("{exe}" init bash --config \'{theme_path}\')"'
        elif name == ".zshrc":
            snippet = f'command -v "{exe}" >/dev/null 2>&1 && eval "$("{exe}" init zsh --config \'{theme_path}\')"'
        elif name == "config.fish":
            snippet = f'type -q "{exe}"; and "{exe}" init fish --config \'{theme_path}\' | source'
        elif name.endswith(".ps1"):
            snippet = (
                f'if (Test-Path "{exe}") {{ '
                f'& "{exe}" init pwsh --config "{theme_path}" | Invoke-Expression '
                f'}}'
            )
        else:
            continue
        _inject_shell_config(cfg, "oh-my-posh", snippet)
        configured.append(str(cfg))
    return configured


def remove_shell_config(tool: str):
    """Remove tool's shell config from all shell files."""
    marker = "starship" if tool == "starship" else "oh-my-posh"
    for cfg in _get_shell_configs():
        _remove_shell_config(cfg, marker)


# ── Background worker ─────────────────────────────────────────────────────────

class CliToolWorker(QThread):
    progress = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, action: str, tool: str, extra: dict = None, parent=None):
        super().__init__(parent)
        self.action = action   # "install", "uninstall", "install_font", "configure"
        self.tool   = tool
        self.extra  = extra or {}

    def run(self):
        try:
            if self.action == "install":
                self._install()
            elif self.action == "uninstall":
                self._uninstall()
            elif self.action == "install_font":
                self._install_font()
            elif self.action == "configure":
                self._configure()
        except Exception as e:
            self.finished.emit(False, str(e))

    # ── install ──

    def _install(self):
        tool = self.tool
        if tool in PIP_TOOLS:
            self._pip_install(PIP_TOOLS[tool]["pip"])
        elif tool == "starship":
            self._install_binary_starship()
        elif tool == "oh-my-posh":
            self._install_binary_omp()
        else:
            self.finished.emit(False, f"Unknown tool: {tool}")

    def _pip_install(self, pkg: str):
        self.progress.emit(f"📦 Installing {pkg} via pip...")
        python = sys.executable
        r = subprocess.run(
            [python, "-m", "pip", "install", "--upgrade", pkg],
            capture_output=True, text=True, timeout=120
        )
        if r.returncode == 0:
            self.finished.emit(True, f"✅ {pkg} installed successfully")
        else:
            self.finished.emit(False, r.stderr[-500:] or r.stdout[-500:])

    def _install_binary_starship(self):
        key = (SYSTEM, ARCH if ARCH != "amd64" else "x86_64")
        filename = STARSHIP_BINS.get(key) or STARSHIP_BINS.get((SYSTEM, "x86_64"))
        if not filename:
            self.finished.emit(False, f"No binary for {SYSTEM}/{ARCH}")
            return
        url = STARSHIP_RELEASES + filename
        self.progress.emit(f"⬇️ Downloading starship ({filename})...")
        self._download_and_extract(url, filename, "starship")

    def _install_binary_omp(self):
        key = (SYSTEM, ARCH if ARCH != "amd64" else "x86_64")
        filename = OMP_BINS.get(key) or OMP_BINS.get((SYSTEM, "x86_64"))
        if not filename:
            self.finished.emit(False, f"No binary for {SYSTEM}/{ARCH}")
            return
        url = OMP_RELEASES + filename
        self.progress.emit(f"⬇️ Downloading oh-my-posh ({filename})...")
        # B181 fix: install binary into ~/.posh/ (not ~/.local/bin/) so it
        # lives next to its themes/ folder.
        try:
            self._download_omp_binary(url, filename)
            self.progress.emit("⬇️ Downloading themes pack...")
            self._download_omp_themes()
            omp_dir = _get_omp_dir()
            self._ensure_path(omp_dir)
            self.finished.emit(
                True,
                f"✅ oh-my-posh installed to {omp_dir}\n"
                f"   • Binary: {omp_dir / ('oh-my-posh.exe' if SYSTEM == 'Windows' else 'oh-my-posh')}\n"
                f"   • Themes: {_get_omp_themes_dir()}\n"
                f"   • Next: select a theme and click Configure to enable it"
            )
        except Exception as _e:
            self.finished.emit(False, f"❌ oh-my-posh install failed: {_e}")

    def _download_omp_binary(self, url: str, filename: str):
        """Download the oh-my-posh executable into ~/.posh/."""
        import urllib.request, ssl
        omp_dir = _get_omp_dir()
        omp_dir.mkdir(parents=True, exist_ok=True)
        exe_name = "oh-my-posh.exe" if SYSTEM == "Windows" else "oh-my-posh"
        out = omp_dir / exe_name
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers={"User-Agent": "VenvStudio"})
        self.progress.emit(f"⬇️ Fetching {url}")
        with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            with open(out, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = min(100, int(downloaded * 100 / total))
                        self.progress.emit(f"⬇️ Downloading binary... {pct}%")
        if SYSTEM != "Windows":
            os.chmod(out, 0o755)
        self.progress.emit(f"✅ Binary installed: {out}")

    def _download_omp_themes(self):
        """Download and extract the official oh-my-posh themes pack into
        ~/.posh/themes/. This replaces the broken `oh-my-posh env home`
        lookup that older configure code relied on."""
        import urllib.request, ssl
        themes_dir = _get_omp_themes_dir()
        themes_dir.mkdir(parents=True, exist_ok=True)
        ctx = ssl.create_default_context()
        req = urllib.request.Request(OMP_THEMES_URL, headers={"User-Agent": "VenvStudio"})
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "themes.zip"
            with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                with open(zip_path, "wb") as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            pct = min(100, int(downloaded * 100 / total))
                            self.progress.emit(f"⬇️ Downloading themes... {pct}%")
            self.progress.emit("📦 Extracting themes...")
            with zipfile.ZipFile(zip_path) as z:
                # Themes pack contains *.omp.json files at root or in a subdir
                for member in z.namelist():
                    if member.endswith(".omp.json"):
                        # Strip any leading directory, write flat under themes/
                        target = themes_dir / Path(member).name
                        with z.open(member) as src, open(target, "wb") as dst:
                            shutil.copyfileobj(src, dst)
        # Count what we extracted
        count = len(list(themes_dir.glob("*.omp.json")))
        self.progress.emit(f"✅ {count} themes installed to {themes_dir}")

    def _download_and_extract(self, url: str, filename: str, tool_name: str):
        import urllib.request, ssl
        bin_dir = _get_bin_dir()
        bin_dir.mkdir(parents=True, exist_ok=True)
        _ctx = ssl.create_default_context()

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / filename
            self.progress.emit(f"⬇️ Fetching {url}")
            req = urllib.request.Request(url, headers={"User-Agent": "VenvStudio"})
            with urllib.request.urlopen(req, timeout=60, context=_ctx) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                with open(dest, "wb") as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            pct = min(100, int(downloaded * 100 / total))
                            self.progress.emit(f"⬇️ Downloading... {pct}%")
            self.progress.emit("📦 Extracting...")

            if filename.endswith(".zip"):
                with zipfile.ZipFile(dest) as z:
                    z.extractall(tmp)
            elif filename.endswith(".tar.gz"):
                with tarfile.open(dest) as t:
                    t.extractall(tmp)

            # Find the binary
            exe_name = tool_name + (".exe" if SYSTEM == "Windows" else "")
            found = None
            for f in Path(tmp).rglob("*"):
                if f.name == exe_name or (tool_name == "oh-my-posh" and f.name.startswith("posh")):
                    found = f
                    break
            if not found:
                # Try root
                candidates = [Path(tmp) / exe_name, dest]
                for c in candidates:
                    if c.exists():
                        found = c
                        break

            if not found:
                self.finished.emit(False, f"Binary not found after extraction")
                return

            out = bin_dir / exe_name
            shutil.copy2(found, out)
            if SYSTEM != "Windows":
                os.chmod(out, 0o755)

            # Add bin_dir to PATH hint
            self.progress.emit(f"✅ Installed to {out}")
            self._ensure_path(bin_dir)
            self.finished.emit(True, f"✅ {tool_name} installed to {out}")

    def _ensure_path(self, bin_dir: Path):
        """Ensure bin_dir is in PATH in shell configs.

        Skips the injection entirely if bin_dir is already on PATH (the
        usual case for ~/.local/bin on Linux, which is added by
        ~/.profile or pipx). Avoids duplicate `export PATH=...` lines
        accumulating in .bashrc on every install.
        """
        bin_str = str(bin_dir)
        try:
            current = os.environ.get("PATH", "")
            sep = ";" if SYSTEM == "Windows" else ":"
            entries = [e.rstrip("/\\") for e in current.split(sep) if e]
            if bin_dir.resolve() and str(bin_dir.resolve()).rstrip("/\\") in entries:
                # Already on PATH — nothing to add.
                return
        except Exception:
            pass
        if SYSTEM == "Windows":
            snippet = f'$env:PATH = "{bin_str};" + $env:PATH'
            marker = f"venvstudio-path-{bin_dir.name}"
        else:
            snippet = f'export PATH="{bin_str}:$PATH"'
            marker = f"venvstudio-path-{bin_dir.name}"
        for cfg in _get_shell_configs():
            _inject_shell_config(cfg, marker, snippet)

    # ── uninstall ──

    def _uninstall(self):
        tool = self.tool
        if tool in PIP_TOOLS:
            python = sys.executable
            r = subprocess.run(
                [python, "-m", "pip", "uninstall", "-y", PIP_TOOLS[tool]["pip"]],
                capture_output=True, text=True, timeout=60
            )
            if r.returncode == 0:
                self.finished.emit(True, f"✅ {tool} uninstalled")
            else:
                self.finished.emit(False, r.stderr[-300:])
        elif tool in ("starship", "oh-my-posh"):
            exe = tool + (".exe" if SYSTEM == "Windows" else "")
            removed = []
            # Legacy bin location
            bin_path = _get_bin_dir() / exe
            if bin_path.exists():
                try:
                    bin_path.unlink()
                    removed.append(str(bin_path))
                except Exception:
                    pass
            # B181 fix: oh-my-posh now lives in ~/.posh/ — remove the
            # whole directory (binary + themes/) when uninstalling.
            # NOTE: fonts are intentionally NOT removed — the user may
            # still want them for other terminals or applications.
            if tool == "oh-my-posh":
                omp_dir = _get_omp_dir()
                if omp_dir.exists():
                    try:
                        shutil.rmtree(omp_dir)
                        removed.append(str(omp_dir))
                    except Exception as _e:
                        self.progress.emit(f"⚠️ Could not remove {omp_dir}: {_e}")
            # Remove the tool's init snippet (`# Added by VenvStudio — oh-my-posh`)
            remove_shell_config(tool)
            # B181 fix: also remove the PATH-export snippets we wrote during
            # install. Two markers may exist depending on which install path
            # was taken: the new ~/.posh layout AND the legacy ~/.local/bin.
            for path_marker in (f"venvstudio-path-{_get_omp_dir().name}",
                                f"venvstudio-path-{_get_bin_dir().name}"):
                for cfg in _get_shell_configs():
                    _remove_shell_config(cfg, path_marker)
            msg = f"✅ {tool} removed"
            if removed:
                msg += "\n   • " + "\n   • ".join(removed)
            msg += "\n   • Shell init + PATH lines cleaned from .bashrc / .zshrc / fish / PowerShell profile"
            msg += "\n   • Fonts left intact (use Settings → Appearance to manage fonts separately)"
            self.finished.emit(True, msg)
        else:
            self.finished.emit(False, f"Unknown tool: {tool}")

    # ── configure ──

    def _configure(self):
        tool  = self.tool
        theme = self.extra.get("theme", "")
        if tool == "starship":
            files = configure_starship(preset=theme or None)
            msg = f"✅ Starship configured in: {', '.join(files) or 'no shell configs found'}"
            self.finished.emit(True, msg)
        elif tool == "oh-my-posh":
            files = configure_omp(theme=theme or "jandedobbeleer")
            msg = f"✅ Oh My Posh configured in: {', '.join(files) or 'no shell configs found'}"
            self.finished.emit(True, msg)
        else:
            self.finished.emit(False, f"No configuration needed for {tool}")

    # ── font install ──

    def _install_font(self):
        import urllib.request
        font_id   = self.extra.get("font_id", "JetBrainsMono")
        font_name = self.extra.get("font_name", font_id)
        filename  = f"{font_id}.zip"
        url       = NERD_FONTS_BASE + filename

        self.progress.emit(f"⬇️ Downloading {font_name} Nerd Font...")

        import ssl as _ssl
        _ctx = _ssl.create_default_context()
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / filename
            req = urllib.request.Request(url, headers={"User-Agent": "VenvStudio"})
            with urllib.request.urlopen(req, timeout=60, context=_ctx) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                with open(dest, "wb") as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            pct = min(100, int(downloaded * 100 / total))
                            self.progress.emit(f"⬇️ Downloading font... {pct}%")
            self.progress.emit("📦 Extracting font...")
            with zipfile.ZipFile(dest) as z:
                z.extractall(tmp)

            font_files = list(Path(tmp).glob("*.ttf")) + list(Path(tmp).glob("*.otf"))
            if not font_files:
                self.finished.emit(False, "No font files found in archive")
                return

            self.progress.emit(f"🖋️ Installing {len(font_files)} font files...")
            self._do_install_fonts(font_files)

    def _do_install_fonts(self, font_files: list):
        if SYSTEM == "Windows":
            font_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Windows" / "Fonts"
            font_dir.mkdir(parents=True, exist_ok=True)
            import ctypes
            for ff in font_files:
                dest = font_dir / ff.name
                shutil.copy2(ff, dest)
                # Register font
                try:
                    ctypes.windll.gdi32.AddFontResourceExW(str(dest), 0x10, 0)
                except Exception:
                    pass
            self.finished.emit(True, f"✅ {len(font_files)} fonts installed to {font_dir}")

        elif SYSTEM == "Darwin":
            font_dir = Path.home() / "Library" / "Fonts"
            font_dir.mkdir(parents=True, exist_ok=True)
            for ff in font_files:
                shutil.copy2(ff, font_dir / ff.name)
            self.finished.emit(True, f"✅ {len(font_files)} fonts installed to {font_dir}")

        else:  # Linux
            font_dir = Path.home() / ".local" / "share" / "fonts" / "NerdFonts"
            font_dir.mkdir(parents=True, exist_ok=True)
            for ff in font_files:
                shutil.copy2(ff, font_dir / ff.name)
            try:
                subprocess.run(["fc-cache", "-fv"], timeout=30)
            except Exception:
                pass
            self.finished.emit(True, f"✅ {len(font_files)} fonts installed to {font_dir}")
