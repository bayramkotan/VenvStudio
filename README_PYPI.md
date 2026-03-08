<div align="center">

# 🐍 VenvStudio

**Lightweight Python Virtual Environment Manager**  
Create, manage, and launch your Python environments — all from a modern GUI

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
- **13+ one-click launchers** — see full list below
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
- CLI/TUI Tools: **Starship** (preset preview, inline config editor, test terminal), **Oh My Posh**, **Nerd Fonts**
- Auto-check for updates on startup

---

---

## 🚀 Supported Launchers

*Launch any of these tools directly from VenvStudio — if installed in the active environment, it appears in the sidebar automatically.*

| | Tool | Description | Category | Website |
|:---:|:-----|:-----------|:--------:|:-------:|
| ![Jupyter](https://img.shields.io/badge/-F37626?style=flat-square&logo=jupyter&logoColor=white) | **JupyterLab** | Next-gen interactive development environment for notebooks | 📓 Notebooks | [jupyter.org](https://jupyter.org/) |
| ![Jupyter](https://img.shields.io/badge/-F37626?style=flat-square&logo=jupyter&logoColor=white) | **Jupyter Notebook** | Classic notebook interface for interactive computing | 📓 Notebooks | [jupyter.org](https://jupyter.org/) |
| ![Streamlit](https://img.shields.io/badge/-FF4B4B?style=flat-square&logo=streamlit&logoColor=white) | **Streamlit** | Build data apps in minutes with pure Python | 🌐 Web Apps | [streamlit.io](https://streamlit.io/) |
| ![Gradio](https://img.shields.io/badge/-F97316?style=flat-square&logo=gradio&logoColor=white) | **Gradio** | Build and share ML demos and web apps | 🌐 Web Apps | [gradio.app](https://gradio.app/) |
| ![Dash](https://img.shields.io/badge/-3F4F75?style=flat-square&logo=plotly&logoColor=white) | **Plotly Dash** | Analytical web applications with Python | 🌐 Web Apps | [dash.plotly.com](https://dash.plotly.com/) |
| ![Panel](https://img.shields.io/badge/-4E8BBE?style=flat-square) | **Panel** | High-level app and dashboarding framework | 🌐 Web Apps | [panel.holoviz.org](https://panel.holoviz.org/) |
| ![Voilà](https://img.shields.io/badge/-5B4B8A?style=flat-square) | **Voilà** | Turn Jupyter notebooks into standalone web apps | 🌐 Web Apps | [voila.readthedocs.io](https://voila.readthedocs.io/) |
| ![FastAPI](https://img.shields.io/badge/-009688?style=flat-square&logo=fastapi&logoColor=white) | **FastAPI** | Modern, fast web framework for building APIs | ⚡ API | [fastapi.tiangolo.com](https://fastapi.tiangolo.com/) |
| ![TensorBoard](https://img.shields.io/badge/-FF6F00?style=flat-square&logo=tensorflow&logoColor=white) | **TensorBoard** | Visualization toolkit for machine learning experiments | 📊 ML Ops | [tensorflow.org/tensorboard](https://www.tensorflow.org/tensorboard) |
| ![MLflow](https://img.shields.io/badge/-0194E2?style=flat-square&logo=mlflow&logoColor=white) | **MLflow** | Platform for the complete ML lifecycle | 📊 ML Ops | [mlflow.org](https://mlflow.org/) |
| ![Spyder](https://img.shields.io/badge/-838485?style=flat-square&logo=spyderide&logoColor=white) | **Spyder IDE** | Scientific Python development environment | 🔬 IDE | [spyder-ide.org](https://www.spyder-ide.org/) |
| ![Orange](https://img.shields.io/badge/-E6812C?style=flat-square) | **Orange Data Mining** | Visual programming for data analysis and ML | 🔬 Data Science | [orangedatamining.com](https://orangedatamining.com/) |
| ![Datasette](https://img.shields.io/badge/-4A8B6E?style=flat-square) | **Datasette** | Explore and publish data with instant JSON API | 🗄️ Data | [datasette.io](https://datasette.io/) |
| ![IPython](https://img.shields.io/badge/-3776AB?style=flat-square&logo=python&logoColor=white) | **IPython** | Enhanced interactive Python shell | 🐍 Shell | [ipython.org](https://ipython.org/) |

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
