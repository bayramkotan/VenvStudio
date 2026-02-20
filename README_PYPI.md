# VenvStudio

**Lightweight Python Virtual Environment Manager**  
A modern, cross-platform virtual environment manager

[![Release](https://img.shields.io/github/v/release/bayramkotan/VenvStudio?style=for-the-badge&color=89b4fa&logo=github)](https://github.com/bayramkotan/VenvStudio/releases/latest)
[![PyPI](https://img.shields.io/pypi/v/venvstudio?style=for-the-badge&color=a6e3a1&logo=pypi&logoColor=white)](https://pypi.org/project/venvstudio/)
[![Python](https://img.shields.io/pypi/pyversions/venvstudio?style=for-the-badge&color=f9e2af&logo=python&logoColor=white)](https://pypi.org/project/venvstudio/)
[![License](https://img.shields.io/github/license/bayramkotan/VenvStudio?style=for-the-badge&color=cba6f7)](LICENSE)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-blue?style=for-the-badge)

---

## 📦 Install

```bash
pip install venvstudio
```

Or download the standalone binary from [GitHub Releases](https://github.com/bayramkotan/VenvStudio/releases/latest):

| Platform | File |
|----------|------|
| Windows | `VenvStudio.exe` |
| Linux | `VenvStudio-x86_64.AppImage` |
| macOS | `VenvStudio-macOS` |
| PyPI | `pip install venvstudio` |

---

## ✨ Features

- **Create & manage** Python virtual environments with a modern GUI
- **Package management** — install, uninstall, update packages via pip or uv
- **200+ package catalog** with categories (Data Science, Web, ML, NLP, DevOps...)
- **Quick presets** — Data Science Starter, Web API, Django, Flask, ML, NLP, Testing...
- **Launch apps** — JupyterLab, Orange Data Mining, Spyder, IPython, Streamlit with one click
- **Desktop shortcuts** — create `.lnk` shortcuts with app-specific icons
- **Export** — requirements.txt, Dockerfile, docker-compose.yml, pyproject.toml, Conda environment.yml
- **Python downloader** — download standalone Python builds (astral-sh/python-build-standalone)
- **PATH management** — set User/System default Python with admin elevation
- **Auto-update** — check PyPI for new versions on startup
- **Cross-platform** — Windows, macOS, Linux
- **Dark theme** — modern Catppuccin-based UI
- **Multilingual** — English & Turkish

---

## 🚀 Quick Start

### From PyPI

```bash
pip install venvstudio
venvstudio
```

### From Source

```bash
git clone https://github.com/bayramkotan/VenvStudio.git
cd VenvStudio
pip install PySide6
python main.py
```

### CLI

```bash
venvstudio          # Launch GUI
venvstudio -V       # Show version
venvstudio -h       # Help
```

---

## 📤 Export Formats

Export your environment in multiple formats from the **Export ▾** dropdown:

| Format | File(s) | Use Case |
|--------|---------|----------|
| 📄 requirements.txt | `requirements.txt` | Standard pip |
| 🐳 Dockerfile | `Dockerfile` + `requirements.txt` | Docker container |
| 🐳 docker-compose.yml | 3 files | Docker Compose |
| 📦 pyproject.toml | `pyproject.toml` | Modern Python packaging |
| 🐍 environment.yml | `environment.yml` | Conda compatibility |
| 📋 Clipboard | — | Quick copy-paste |

---

## ⬇️ Python Downloader

Download standalone Python builds from [astral-sh/python-build-standalone](https://github.com/astral-sh/python-build-standalone) (same builds used by `uv`):

- **User Install** — no admin required, stored in VenvStudio config
- **System Install** — Windows (`C:\Program Files`), Linux (`/opt/python`), macOS (`/usr/local/python`)

---

## 🐍 PATH Management

Manage which Python is the default on your system:

- **Set User Default** — adds to User PATH, removes conflicting entries
- **Set System Default** — adds to System PATH with admin elevation
- Both modes clean conflicting Python entries from both User and System PATH

---

## 🔧 Settings

- Theme: Dark (Catppuccin), Light
- Language: English, Turkish
- Default package manager: pip or uv
- Custom venv base directory (default: `C:\venv` on Windows, `~/venv` on Linux/macOS)
- Python version management
- Check for updates on startup
- Export/Import settings

---

## 🏗️ Build from Source

```bash
pip install pyinstaller PySide6 Pillow
python build.py
```

This creates platform-specific binaries in the `dist/` folder.

---

## 📝 License

[LGPL-3.0](https://github.com/bayramkotan/VenvStudio/blob/main/LICENSE)

---

## 🔗 Links

- [GitHub Repository](https://github.com/bayramkotan/VenvStudio)
- [PyPI Package](https://pypi.org/project/venvstudio/)
- [Releases](https://github.com/bayramkotan/VenvStudio/releases)
- [Issues](https://github.com/bayramkotan/VenvStudio/issues)
- [Screenshots](https://github.com/bayramkotan/VenvStudio#-screenshots)
