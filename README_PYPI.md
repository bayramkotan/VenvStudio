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

**🐧 On Linux, pip may refuse to install.** Most current distributions mark the
system Python as *externally managed* (PEP 668), so a plain `pip install` stops
with `error: externally-managed-environment`. Two ways around it:

```bash
# Isolated — recommended, no system packages touched
pipx install venvstudio

# Into the system Python — needs the override flag
sudo pip install venvstudio --break-system-packages --no-cache-dir -U
```

The same flag applies when upgrading a system-wide install later on.

Or download the standalone binary — **no Python required:**

| Platform | File | Notes |
|:--------:|:-----|:------|
| 🪟 **Windows** | [`VenvStudio.exe`](https://github.com/bayramkotan/VenvStudio/releases/latest) | Portable — just run |
| 🐧 **Linux** | [`VenvStudio-x86_64.AppImage`](https://github.com/bayramkotan/VenvStudio/releases/latest) | `chmod +x` then run |
| 🍎 **macOS** | [`VenvStudio-macOS`](https://github.com/bayramkotan/VenvStudio/releases/latest) | Apple Silicon + Rosetta 2 |

---

## ✨ Features

### 🗂️ Environment Management
- **8 environment types** — Python venv, uv, Poetry, Conda (micromamba), pipx, Hatch, PDM, Pixi
- Create, rename, clone, delete virtual environments with a modern GUI
- **Type** column — see each env's package manager at a glance (🐍 venv, ⚡ uv, 📜 Poetry, 🦎 Conda, 📦 pipx, 🏗️ Hatch, 📦 PDM, 🌊 Pixi)
- **Runtime** column — actual Python version detected from each environment's binary
- Auto-detect existing environments on disk at startup
- Per-environment cache — instant load, no subprocess delays
- Set a **Default Environment** that opens automatically on launch
- Open terminal with environment pre-activated (cmd, PowerShell, pwsh, bash, zsh, fish...)
- Export as `requirements.txt`, `requirements-frozen.txt` (SHA-256 hashes), JSON, `Dockerfile`, `docker-compose.yml`, `pyproject.toml`, `environment.yml`

### 🔧 Supported Environment Types

| Icon | Type | Backend | Description |
|:----:|:-----|:--------|:------------|
| 🐍 | **Python venv** | `python -m venv` | Standard virtual environment with pip |
| ⚡ | **uv** | `uv venv` | Rust-powered — 10–100× faster than pip |
| 📜 | **Poetry** | `poetry new` | Dependency management with lock file |
| 📦 | **pipx** | `pipx install` | Isolated CLI applications |
| 🦎 | **Conda** | micromamba | conda-forge — R, RStudio, jamovi, JASP, DBeaver and 25,000+ packages |
| 🏗️ | **Hatch** | `hatch new` | Modern Python project manager by PyPA with pyproject.toml |
| 📦 | **PDM** | `pdm init` | PEP 582 / pyproject.toml based package manager |
| 🌊 | **Pixi** | `pixi init` | conda-forge + PyPI, blazing fast Rust-powered environment |

### 🧩 Conflict Manager

VenvStudio checks packages against a curated compatibility list **before**
installing them — every install path (Catalog, Presets, Manual Install,
Install Launcher) goes through the same check, so nothing slips through.

- **218 curated rules** — packages with known Python-version limits,
  environment restrictions, or that need a native/conda build instead
  of a plain pip wheel
- **Live PyPI fallback** — for packages not on the curated list,
  VenvStudio checks PyPI directly for a matching wheel before installing
- Click any package for a **detail panel**: plain-English explanation,
  the exact install command for your environment type, and one-click
  actions — 🚀 Install, 🌱 Create New Environment, 🔄 Try Alternative
  (swap in a known-good replacement, e.g. PyQt5 → PySide6), 📚 Open in
  Learn
- **Scan Environment** — check every package already installed, not
  just new ones
- **Export** — save the full compatibility table as CSV or JSON

### 📦 Package Management
- **Installed** tab — filter, select, uninstall, export, import packages
- **Catalog** tab — 64 curated packages across 32 categories with PyPI & Docs links
- **Presets** tab — one-click install bundles (Data Science, Web API, Django, Flask, ML, NLP, CV, Testing...)
- **Manual Install** tab — paste package names or version specs (`numpy==1.24`, `pandas>=2.0`)
- pip or **uv** backend (uv is 10–100× faster)

### 🚀 Quick Launch
- Sidebar shows installed apps for the active environment
- **26 one-click launchers** — see full list below
- **Install Launcher** (File menu) — pick any app, VenvStudio finds a compatible environment automatically or offers to create one
- **System tools** — R, RStudio, Ollama, DBeaver, jamovi, JASP via Conda
- **Jupyter Working Directory** — configurable (Home / Env Folder / Custom Path)
- **Create Desktop Shortcut** for any app
- Instant sync between sidebar dropdown, environment table, and package panel

### 🐍 Python Management
- Auto-detect all system Python installations
- Add custom Python paths
- Set **User Default** or **System Default** Python (PATH management with optional admin elevation)
- Download standalone Python builds from [python-build-standalone](https://github.com/astral-sh/python-build-standalone)

### ⚙️ Settings & Customization
- 🌙 13 themes (8 dark + 5 light, Catppuccin-based)
- 3-level font system (Headings / UI & Menus / Details)
- 🌍 11 languages: EN, TR, DE, ES, RU, JA, AR, FR, PT, ZH, KO
- **Conda mirrors** — reorderable list with automatic failover; a `Skip Mirror` button jumps to the next one mid-install instead of waiting out a slow server
- **pipx interpreter** — pin which Python your CLI apps get installed with, useful when the newest release is ahead of the tools you need
- Custom venv base directory
- Custom terminal, catalog categories, and packages
- CLI/TUI Tools: **Starship** (preset preview, inline config editor, test terminal), **Oh My Posh**, **Nerd Fonts**
- Auto-check for updates on startup

---

## 🚀 Supported Launchers

*Launch any of these tools directly from VenvStudio — if installed in the active environment, it appears in the sidebar automatically.*

### 📓 Python Launchers (venv, uv, Hatch, PDM, Poetry)

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
| ![Marimo](https://img.shields.io/badge/-8B5CF6?style=flat-square) | **Marimo** | Reactive notebook — no hidden state, runs as an app | 📓 Notebooks | [marimo.io](https://marimo.io/) |
| ![Quarto](https://img.shields.io/badge/-75AADB?style=flat-square&logo=quarto&logoColor=white) | **Quarto** | Publish documents, reports and dashboards | 📄 Publishing | [quarto.org](https://quarto.org/) |
| ![IPython](https://img.shields.io/badge/-3776AB?style=flat-square&logo=python&logoColor=white) | **IPython** | Enhanced interactive Python shell | 🐍 Shell | [ipython.org](https://ipython.org/) |
| ![Chainlit](https://img.shields.io/badge/-000000?style=flat-square) | **Chainlit** | Build conversational AI / LLM chat apps | 🗣️ LLM & GenAI | [chainlit.io](https://chainlit.io/) |
| ![Shiny](https://img.shields.io/badge/-4E9BCD?style=flat-square) | **Shiny** | Python web apps for data science, R-inspired | 🌐 Web Apps | [shiny.posit.co](https://shiny.posit.co/py/) |
| ![NiceGUI](https://img.shields.io/badge/-5898D4?style=flat-square) | **NiceGUI** | Python-only web UIs, no HTML/CSS/JS needed | 🌐 Web Apps | [nicegui.io](https://nicegui.io/) |
| ![Bokeh](https://img.shields.io/badge/-2E7D9E?style=flat-square) | **Bokeh** | Interactive visualization for modern browsers | 📊 ML Ops | [bokeh.org](https://bokeh.org/) |

### 🛠️ System Tools (Conda / Portable)

*Available in Conda environments — installed via conda-forge or detected on system.*

| Tool | Description | Install Method |
|:-----|:-----------|:--------------|
| **R** | Statistical computing language | Conda (`r-base`) or system installer |
| **RStudio** | IDE for R | Conda (`rstudio-desktop`) or portable download |
| **Ollama** | Run large language models locally | Portable binary |
| **DBeaver** | Universal database tool | Conda or portable ZIP |
| **jamovi** | Statistical spreadsheet | Conda or AppImage (Linux) |
| **JASP** | Bayesian statistics | Conda or AppImage (Linux) |

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

### Linux — System Dependencies

Before running VenvStudio on Linux, install the required Qt/XCB libraries:

**Debian / Ubuntu / Pardus / Linux Mint:**
```bash
sudo apt update
sudo apt install libxcb-xinerama0 libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
                 libxcb-keysyms1 libxcb-render-util0 libxcb-shape0 libxkbcommon-x11-0
```

**Arch Linux / CachyOS / Manjaro:**
```bash
sudo pacman -S xcb-util-cursor xcb-util-icccm xcb-util-image \
               xcb-util-keysyms xcb-util-renderutil libxkbcommon-x11
```

**Fedora / RHEL / CentOS:**
```bash
sudo dnf install libxcb xcb-util-cursor xcb-util-icccm xcb-util-image \
                 xcb-util-keysyms xcb-util-renderutil libxkbcommon-x11
```

**openSUSE Leap / Tumbleweed:**
```bash
sudo zypper install libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
                    libxcb-keysyms1 libxcb-render-util0 libxkbcommon-x11-0 libgthread-2_0-0
```

> **Note:** If the AppImage fails with `Could not load the Qt platform plugin "xcb"`, installing these packages will fix it.

### CLI

VenvStudio is a GUI first, but the core actions work headless too — handy over SSH,
in scripts, or when you just want one quick thing done.

Installing with pip gives you two names for the same tool: **`vs`** to type and
**`venvstudio`** to read. Use whichever you like.

| Short | Full | What it does |
|:------|:-----|:-------------|
| `vs` | `venvstudio` | Launch the GUI |
| `vs list` | `venvstudio list` | List every detected environment |
| `vs create NAME` | `venvstudio create NAME` | Create a venv environment |
| `vs create NAME -t uv` | `venvstudio create NAME -t uv` | Create a uv environment |
| `vs create NAME -t poetry` | `venvstudio create NAME -t poetry` | Create a Poetry environment |
| `vs create NAME -t conda` | `venvstudio create NAME -t conda` | Create a Conda environment |
| `vs create NAME -t hatch` | `venvstudio create NAME -t hatch` | Create a Hatch environment |
| `vs create NAME -t pdm` | `venvstudio create NAME -t pdm` | Create a PDM environment |
| `vs create NAME -t pixi` | `venvstudio create NAME -t pixi` | Create a Pixi environment |
| `vs delete NAME` | `venvstudio delete NAME` | Delete an environment (asks first) |
| `vs delete NAME -y` | `venvstudio delete NAME -y` | Delete without the confirmation prompt |
| `vs packages ENV` | `venvstudio packages ENV` | List packages installed in ENV |
| `vs install ENV PKG...` | `venvstudio install ENV PKG...` | Install one or more packages into ENV |
| `vs uninstall ENV PKG...` | `venvstudio uninstall ENV PKG...` | Uninstall packages from ENV |
| `vs -V` | `venvstudio -V` | Show version (also: `version`) |
| `vs -h` | `venvstudio -h` | Show help |

```bash
vs                        # short and sweet
venvstudio list           # or spell it out
vs install myenv requests httpx
```

On Windows, `venvstudio-gui` starts the GUI without a console window.

---

## 📤 Export Formats

Export your environment in multiple formats from the **Export ▾** dropdown:

| Format | File(s) | Use Case |
|--------|---------|----------|
| 📄 requirements.txt | `requirements.txt` | Standard pip |
| 🔒 requirements-frozen.txt | `requirements-frozen.txt` | Reproducible install with SHA-256 hashes |
| 📋 JSON | `packages.json` | Machine-readable package list |
| 🐳 Dockerfile | `Dockerfile` + `requirements.txt` | Docker container |
| 🐳 docker-compose.yml | 3 files | Docker Compose |
| 📦 pyproject.toml | `pyproject.toml` | Modern Python packaging |
| 🐍 environment.yml | `environment.yml` | Conda compatibility |
| 📋 Clipboard | — | Quick copy-paste |

---

## ⬇️ Python Downloader

Download standalone Python builds straight from VenvStudio — no system install,
no admin rights needed.

**Five sources, tried in order until one answers:**

| Source | What it serves |
|:-------|:---------------|
| **Astral** *(default)* | [python-build-standalone](https://github.com/astral-sh/python-build-standalone) via GitHub Releases — the same builds `uv` uses |
| **GitHub Releases** | Same builds, fetched directly |
| **python.org** | Official CPython source tarballs |
| **SourceForge** | Mirror — often faster in some regions |
| **Custom URL** | Point it anywhere you like |

The default chain is Astral → GitHub → python.org: if one is unreachable or slow,
VenvStudio moves to the next on its own. Pick your preferred source in
**Settings → Python**.

**Install target:**

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
