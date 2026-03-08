<div align="center">

# 🐍 VenvStudio

**Lightweight Python Virtual Environment Manager**  
Create, manage, and launch your Python environments — all from a modern GUI

[![PyPI](https://img.shields.io/pypi/v/venvstudio?style=for-the-badge&color=a6e3a1&logo=pypi&logoColor=white)](https://pypi.org/project/venvstudio/)
[![License](https://img.shields.io/badge/License-LGPL--3.0-cba6f7?style=for-the-badge)](https://github.com/bayramkotan/VenvStudio/blob/main/LICENSE)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-f9e2af?style=for-the-badge)

</div>

---

## 📦 Install

```bash
pip install venvstudio
venvstudio
```

Or download the standalone binary — **no Python required:**

| Platform | File | Notes |
|:--------:|:-----|:------|
| 🪟 **Windows** | [`VenvStudio.exe`](https://github.com/bayramkotan/VenvStudio/releases/latest) | Portable — just run |
| 🐧 **Linux** | [`VenvStudio-x86_64.AppImage`](https://github.com/bayramkotan/VenvStudio/releases/latest) | `chmod +x` then run |
| 🍎 **macOS** | [`VenvStudio-macOS`](https://github.com/bayramkotan/VenvStudio/releases/latest) | Apple Silicon + Rosetta 2 |

---

## ✨ Features

### 🗂️ Environment Management
- Create, rename, clone, delete virtual environments with a modern GUI
- Auto-detect existing environments on disk at startup
- Per-environment cache — instant load, no subprocess delays
- Set a **Default Environment** that opens automatically on launch
- Open terminal with environment pre-activated (cmd, PowerShell, pwsh, bash, zsh, fish...)
- Export as `requirements.txt`, `Dockerfile`, `docker-compose.yml`, `pyproject.toml`, `environment.yml`

### 📦 Package Management
- **Installed** tab — filter, select, uninstall, export, import packages
- **Catalog** tab — 200+ curated packages across 15 categories with PyPI & Docs links
- **Presets** tab — one-click install bundles (Data Science, Web API, Django, Flask, ML, NLP, CV, Testing...)
- **Manual Install** tab — paste package names or version specs (`numpy==1.24`, `pandas>=2.0`)
- pip or **uv** backend (uv is 10–100× faster)

### 🚀 Quick Launch
- Sidebar shows installed apps for the active environment
- One-click launch: JupyterLab, Jupyter Notebook, Spyder IDE, IPython, Orange Data Mining, Streamlit, Gradio, Dash, FastAPI, TensorBoard, MLflow, and more
- **Jupyter Working Directory** — configurable (Home / Env Folder / Custom Path)
- **Create Desktop Shortcut** for any app
- Instant sync between sidebar dropdown, environment table, and package panel

### 🐍 Python Management
- Auto-detect all system Python installations
- Add custom Python paths
- Set **User Default** or **System Default** Python (PATH management with optional admin elevation)
- Download standalone Python builds from [python-build-standalone](https://github.com/astral-sh/python-build-standalone)

### ⚙️ Settings & Customization
- 🌙 Dark (Catppuccin) and ☀️ Light themes
- Font family and size customization
- 🌍 Interface language: English / Turkish
- Custom venv base directory
- Custom terminal, catalog categories, and packages
- CLI/TUI Tools: **Starship**, **Oh My Posh**, **Nerd Fonts**
- Auto-check for updates on startup

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

Download standalone Python builds from [python-build-standalone](https://github.com/astral-sh/python-build-standalone) (same builds used by `uv`):

- **User Install** — no admin required, stored in VenvStudio config
- **System Install** — Windows (`C:\Program Files`), Linux (`/opt/python`), macOS (`/usr/local/python`)

---

## 🏗️ Build from Source

```bash
pip install pyinstaller PySide6 Pillow
python build.py
```

---

## 📝 License

[LGPL-3.0](https://github.com/bayramkotan/VenvStudio/blob/main/LICENSE)

---

<div align="center">

**Made with ❤️ by [Bayram Kotan](https://github.com/bayramkotan)**

[GitHub](https://github.com/bayramkotan/VenvStudio) · [Releases](https://github.com/bayramkotan/VenvStudio/releases) · [Issues](https://github.com/bayramkotan/VenvStudio/issues) · [Screenshots](https://github.com/bayramkotan/VenvStudio#-screenshots)

⭐ **If VenvStudio helps you, give it a star!** ⭐

</div>
