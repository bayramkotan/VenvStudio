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

# Starship presets
STARSHIP_PRESETS = [
    "no-nerd-font", "bracketed-segments", "plain-text-symbols",
    "no-runtime-versions", "no-empty-icons", "gruvbox-rainbow",
    "jetpack", "tokyo-night", "pastel-powerline", "nerd-font-symbols",
]

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


# ── Detection ─────────────────────────────────────────────────────────────────

def get_tool_version(tool: str) -> Optional[str]:
    """Return installed version string or None."""
    try:
        if tool == "starship":
            r = subprocess.run(["starship", "--version"], capture_output=True, text=True, timeout=5)
            return r.stdout.strip().split("\n")[0] if r.returncode == 0 else None
        elif tool == "oh-my-posh":
            exe = "oh-my-posh" if SYSTEM != "Windows" else "oh-my-posh.exe"
            r = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=5)
            return r.stdout.strip() if r.returncode == 0 else None
        elif tool in PIP_TOOLS:
            import importlib.util
            spec = importlib.util.find_spec(tool.replace("-", "_"))
            if spec:
                import importlib.metadata
                try:
                    return importlib.metadata.version(PIP_TOOLS[tool]["pip"])
                except Exception:
                    return "installed"
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
    """Add snippet to shell config if not already present."""
    content = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    if marker in content:
        return  # already injected
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
            snippet = 'eval "$(starship init bash)"'
        elif name == ".zshrc":
            snippet = 'eval "$(starship init zsh)"'
        elif name == "config.fish":
            snippet = "starship init fish | source"
        elif name.endswith(".ps1"):
            snippet = 'Invoke-Expression (&starship init powershell)'
        else:
            continue
        _inject_shell_config(cfg, "starship", snippet)
        configured.append(str(cfg))

    # Apply preset if given
    if preset:
        try:
            subprocess.run(
                ["starship", "preset", preset, "-o",
                 str(_get_config_dir() / "starship.toml")],
                timeout=10
            )
        except Exception:
            pass
    return configured


def configure_omp(theme: str = "jandedobbeleer") -> list[str]:
    """Write oh-my-posh init to shell configs."""
    configured = []
    exe = "oh-my-posh" if SYSTEM != "Windows" else \
          str(_get_bin_dir() / "oh-my-posh.exe")

    theme_path = f"$(oh-my-posh env home)/themes/{theme}.omp.json"
    if SYSTEM == "Windows":
        theme_path = f"$env:POSH_THEMES_PATH\\{theme}.omp.json"

    for cfg in _get_shell_configs():
        name = cfg.name
        if name in (".bashrc", ".bash_profile"):
            snippet = f'eval "$({exe} init bash --config {theme_path})"'
        elif name == ".zshrc":
            snippet = f'eval "$({exe} init zsh --config {theme_path})"'
        elif name == "config.fish":
            snippet = f'{exe} init fish --config {theme_path} | source'
        elif name.endswith(".ps1"):
            snippet = f'oh-my-posh init pwsh --config {theme_path} | Invoke-Expression'
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
        self._download_and_extract(url, filename, "oh-my-posh")

    def _download_and_extract(self, url: str, filename: str, tool_name: str):
        import urllib.request
        bin_dir = _get_bin_dir()
        bin_dir.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / filename
            self.progress.emit(f"⬇️ Fetching {url}")

            def _reporthook(count, block, total):
                if total > 0:
                    pct = min(100, int(count * block * 100 / total))
                    self.progress.emit(f"⬇️ Downloading... {pct}%")

            urllib.request.urlretrieve(url, dest, reporthook=_reporthook)
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
        """Ensure bin_dir is in PATH in shell configs."""
        bin_str = str(bin_dir)
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
            bin_path = _get_bin_dir() / exe
            if bin_path.exists():
                bin_path.unlink()
            remove_shell_config(tool)
            self.finished.emit(True, f"✅ {tool} removed")
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

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / filename

            def _reporthook(count, block, total):
                if total > 0:
                    pct = min(100, int(count * block * 100 / total))
                    self.progress.emit(f"⬇️ Downloading font... {pct}%")

            urllib.request.urlretrieve(url, dest, reporthook=_reporthook)
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
