<p align="center">
  <img src="assets/icon.png" alt="VenvStudio" width="128" height="128">
</p>

<h1 align="center">🐍 VenvStudio</h1>

<p align="center">
  <strong>Lightweight Python Virtual Environment Manager</strong><br>
  <sub>Create, manage, and launch your Python environments — all from a modern GUI</sub>
</p>

<p align="center">
  <a href="https://github.com/bayramkotan/VenvStudio/releases/latest">
    <img src="https://img.shields.io/github/v/release/bayramkotan/VenvStudio?style=for-the-badge&color=89b4fa&logo=github" alt="Release">
  </a>
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-f9e2af?style=for-the-badge" alt="Platform">
  <a href="https://github.com/bayramkotan/VenvStudio/stargazers">
    <img src="https://img.shields.io/github/stars/bayramkotan/VenvStudio?style=for-the-badge&color=f5c2e7&logo=github" alt="Stars">
  </a>
</p>

<p align="center">
  <a href="#-educational-by-design">Educational</a> •
  <a href="#-install">Install</a> •
  <a href="#-features">Features</a> •
  <a href="#-supported-environment-types">Env Types</a> •
  <a href="#-conflict-manager">Conflict Manager</a> •
  <a href="#-screenshots">Screenshots</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-export-formats">Export</a> •
  <a href="#-build-from-source">Build</a>
</p>

---

## 🎓 Educational by Design

VenvStudio never hides the command it's actually running. Whether you're
creating an environment, installing a package, deleting one, or
launching an app, you see the **exact, real shell command** behind the
action — not just a spinner. Click Copy and reuse it in a terminal,
a script, or `requirements.txt` — or just read it and learn what's
really happening under the hood.

<p align="center">
  <img src="assets/screenshots/Educational_1.png" alt="Create Environment — real python -m venv / activate / install commands shown live" width="800">
</p>
<p align="center">
  <img src="assets/screenshots/Educational_2.png" alt="Create Environment (PDM) — real pdm init / pdm add commands shown live" width="800">
</p>
<p align="center">
  <img src="assets/screenshots/Educational_3.png" alt="Environments — Command Reference panel shows the real rm -rf delete command" width="800">
</p>
<p align="center">
  <img src="assets/screenshots/Educational_4.png" alt="Launch — the real install command (e.g. pdm add PyQt5 ...) shown with a Copy button" width="800">
</p>
<p align="center">
  <img src="assets/screenshots/Educational_5.png" alt="Log Viewer — every command run this session, logged verbatim" width="800">
</p>

This shows up throughout the app:
- **Create New Environment** — the Progress panel prints the real
  command for the chosen backend (`python -m venv`, `uv venv`,
  `pdm init`, `poetry new`, `hatch new`, `pixi init`, `conda create`,
  `pipx install`) plus activate/deactivate commands, live as it runs
- **Environments page** — a Command Reference panel shows the exact
  command behind delete, clone, rename, and export actions
- **Launch / Install** — the real install command (`pip install`,
  `uv pip install`, `pdm add`, `poetry add`, `hatch run pip install`,
  `conda install`, `pixi add`, `pipx install` — whichever fits the
  environment) is shown with a one-click **Copy** button before it runs
- **Command History** and **Log Viewer** — every command run this
  session is logged verbatim, filterable, and copyable — a running,
  searchable record of exactly what VenvStudio has done
- **🧩 Conflict Manager** — the detail panel shows the exact install
  command for the package + environment type you're looking at (see
  below)

---

## 📦 Install

```bash
pip install venvstudio
venvstudio
```

<details>
<summary><b>🐧 On Linux, pip may refuse to install</b></summary>
<br>

Most current distributions mark the system Python as *externally managed*
(PEP 668), so a plain `pip install` stops with
`error: externally-managed-environment`. Two ways around it:

```bash
# Isolated — recommended, no system packages touched
pipx install venvstudio

# Into the system Python — needs the override flag
sudo pip install venvstudio --break-system-packages --no-cache-dir -U
```

The same flag applies when upgrading a system-wide install later on.

</details>

Or download the standalone binary — **no Python required:**

| Platform | File | Notes |
|:--------:|:-----|:------|
| 🪟 **Windows** | [`VenvStudio.exe`](https://github.com/bayramkotan/VenvStudio/releases/latest) | Portable — just run |
| 🐧 **Linux** | [`VenvStudio-x86_64.AppImage`](https://github.com/bayramkotan/VenvStudio/releases/latest) | `chmod +x` then run |
| 🍎 **macOS** | [`VenvStudio-macOS`](https://github.com/bayramkotan/VenvStudio/releases/latest) | Apple Silicon + Rosetta 2 |

---

## ✨ Features

<table>
<tr>
<td width="50%" valign="top">

### 🗂️ Environment Management
- **8 environment types** — venv, uv, Poetry, Conda, pipx, Hatch, PDM, Pixi
- Create, rename, clone, delete environments with a modern GUI
- **Type** column in the environment table — see each env's manager at a glance
- Auto-detect existing environments at startup
- Per-environment cache — instant load, zero delays
- **Default Environment** — opens automatically on launch
- Open terminal with env pre-activated
- **Command History** — every command run this session, filterable, copy to clipboard
- Export to 6+ formats (see below)

</td>
<td width="50%" valign="top">

### 📦 Package Management
- **Installed** — filter, select, uninstall, export, import
- **Catalog** — 64 curated packages across 32 categories
- **48 Presets** — one-click bundles, including modern AI/data stacks: **LLM App Starter** (openai, anthropic, langchain, chromadb), **RAG/NLP** (transformers, datasets, spacy, torch), **Data Engineering** (polars, duckdb, pyarrow, prefect), plus Data Science, Web API, Django, Flask, Computer Vision, Deep Learning (PyTorch/JAX), Financial Analysis, and more
- **Manual Install** — paste package names or version specs
- pip or **uv** backend (10–100× faster)
- Check for package updates

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🚀 Quick Launch
- Sidebar shows installed apps for active env
- **26 one-click launchers** — [see full list below](#-supported-launchers)
- **Install Launcher** (File menu) — pick any app, VenvStudio finds a compatible environment automatically or offers to create one
- **System tools** — R, RStudio, Ollama, DBeaver, jamovi, JASP via Conda
- **Jupyter Working Directory** — configurable per launch
- **Create Desktop Shortcut** for any app
- Instant sync across sidebar, table, and panel

</td>
<td width="50%" valign="top">

### 🐍 Python Management
- Auto-detect all system Python installations
- Add custom Python paths
- Set **User** or **System Default** Python (PATH management)
- Download standalone builds from [python-build-standalone](https://github.com/astral-sh/python-build-standalone)
- **Log Viewer** — live, filterable application log, right from the app

</td>
</tr>
<tr>
<td width="50%" valign="top">

### ⚙️ Settings
- 🌙 13 themes (8 dark + 5 light, Catppuccin-based)
- 3-level font system (Headings / UI & Menus / Details)
- 🌍 11 languages: EN, TR, DE, ES, RU, JA, AR, FR, PT, ZH, KO
- **Conda mirrors** — reorderable list, automatic failover, `Skip Mirror` mid-install
- **pipx interpreter** — pin the Python your CLI apps are installed with
- Custom venv directory, terminal, catalog, presets
- Export/Import settings
- Auto-check for updates

</td>
<td width="50%" valign="top">

### 🖥️ CLI/TUI Tools
- Install & configure **Starship** prompt
  - Preset preview with descriptions
  - Inline `starship.toml` editor
  - "Test in terminal" button
- Install & configure **Oh My Posh** prompt
- Install **Nerd Fonts** for proper rendering
- pip-installable: **Rich**, **Textual**, **Prompt Toolkit**

</td>
</tr>
</table>

---

## 🔧 Supported Environment Types

VenvStudio supports **8 environment types**, each with its own icon and color in the environment table:

| Icon | Type | Backend | Description |
|:----:|:-----|:--------|:------------|
| 🐍 | **Python venv** | `python -m venv` | Standard Python virtual environment with pip |
| ⚡ | **uv** | `uv venv` | Rust-powered — 10–100× faster than pip |
| 📜 | **Poetry** | `poetry new` | Dependency management with lock file and pyproject.toml |
| 📦 | **pipx** | `pipx install` | Install Python CLI apps in isolated environments |
| 🦎 | **Conda** | micromamba | conda-forge powered — R, RStudio, jamovi, JASP, DBeaver and 25,000+ packages |
| 🏗️ | **Hatch** | `hatch new` | Modern Python project manager by PyPA with pyproject.toml |
| 📦 | **PDM** | `pdm init` | PEP 582 / pyproject.toml based package manager |
| 🌊 | **Pixi** | `pixi init` | conda-forge + PyPI, blazing fast Rust-powered environment |

Each environment is tracked with a `.venvstudio_env` marker file, and the **Runtime** column shows the actual Python version detected from the environment's binary.

---

## 🧩 Conflict Manager

VenvStudio checks packages against a curated compatibility list **before** installing them — every install path (Catalog, Presets, Manual Install, Install Launcher) goes through the same check, so nothing slips through.

- **218 curated rules** — packages with known Python-version limits, environment restrictions, or that need a native/conda build instead of a plain pip wheel
- **Live PyPI fallback** — for packages not on the curated list, VenvStudio checks PyPI directly for a matching wheel before installing
- Click any package for a **detail panel**: plain-English explanation, the exact install command for your environment type, and one-click actions:
  - 🚀 **Install** — into the current environment, if compatible
  - 🌱 **Create New Environment…** — if it isn't
  - 🔄 **Try Alternative** — swap in a known-good replacement (e.g. PyQt5 → PySide6) and install it directly
  - 📚 **Open in Learn** — jump to the matching tutorial, if one exists
- **Scan Environment** — check every package already installed, not just new ones
- **Export** — save the full compatibility table as CSV or JSON

---

## 📸 Screenshots

<details open>
<summary><b>🗂️ Environments</b></summary>
<br>
<p align="center">
  <img src="assets/screenshots/virtual_environments.png" alt="Virtual Environments — full table" width="800">
</p>
<p align="center">
  <img src="assets/screenshots/environments_right_click.png" alt="Environments — right-click context menu" width="800">
</p>
</details>

<details>
<summary><b>🚀 Launch Apps</b></summary>
<br>
<p align="center">
  <img src="assets/screenshots/launch_apps.png" alt="Launch Applications — Links expanded" width="800">
</p>
</details>

<details>
<summary><b>📦 Installed Packages</b></summary>
<br>
<p align="center">
  <img src="assets/screenshots/installed_apps_1.png" alt="Package Info dialog" width="800">
</p>
<p align="center">
  <img src="assets/screenshots/installed_apps_2.png" alt="Right-click menu — copy install commands, open on PyPI" width="800">
</p>
</details>

<details>
<summary><b>📚 Package Catalog</b></summary>
<br>
<p align="center">
  <img src="assets/screenshots/catalog_1.png" alt="Package Catalog — browsing by category" width="800">
</p>
<p align="center">
  <img src="assets/screenshots/catalog_2.png" alt="Package Catalog — category filter" width="800">
</p>
</details>

<details>
<summary><b>⚡ Presets</b></summary>
<br>

48 one-click bundles — from classic (Data Science, Web API, Django) to
modern AI/data stacks: **LLM App Starter**, **RAG/NLP**, **Deep
Learning (PyTorch/JAX)**, **Data Engineering (Polars/DuckDB)**,
**Computer Vision**, **Financial Analysis**, and more.

<p align="center">
  <img src="assets/screenshots/presets.png" alt="Presets — install progress" width="800">
</p>
<p align="center">
  <img src="assets/screenshots/presets1.png" alt="Presets — Time Series, Financial Analysis, Financial LLM" width="800">
</p>
<p align="center">
  <img src="assets/screenshots/presets2.png" alt="Presets — Web Scraping, Async Backend, LLM App Starter, Deep Learning (PyTorch)" width="800">
</p>
<p align="center">
  <img src="assets/screenshots/presets3.png" alt="Presets — Deep Learning (JAX), Audio/Video Processing, Geospatial, Bioinformatics, Game Dev" width="800">
</p>
</details>

<details>
<summary><b>📝 Manual Install</b></summary>
<br>
<p align="center">
  <img src="assets/screenshots/manual_install.png" alt="Manual Install — installing in progress" width="800">
</p>
</details>

<details>
<summary><b>🧩 Conflict Manager</b></summary>
<br>
<p align="center">
  <img src="assets/screenshots/conflict_manager.png" alt="Conflict Manager — All Known Rules" width="800">
</p>
</details>

<details>
<summary><b>🚀 Install Launcher</b></summary>
<br>
<p align="center">
  <img src="assets/screenshots/install_launcher.png" alt="Install Launcher — pick an app, auto-detect a compatible environment" width="800">
</p>
</details>

<details>
<summary><b>📖 Learn</b></summary>
<br>
<p align="center">
  <img src="assets/screenshots/learn.png" alt="Learn — tutorials with runnable code" width="800">
</p>
</details>

<details>
<summary><b>🕘 Command History</b></summary>
<br>
<p align="center">
  <img src="assets/screenshots/command_history.png" alt="Command History — every command run this session" width="800">
</p>
</details>

<details>
<summary><b>📜 Log Viewer</b></summary>
<br>
<p align="center">
  <img src="assets/screenshots/log_viewer.png" alt="Log Viewer — live, filterable application log" width="800">
</p>
</details>

<details>
<summary><b>⚙️ Settings</b></summary>
<br>
<p align="center">
  <img src="assets/screenshots/settings-1.png" alt="Settings — Appearance, fonts, language" width="800">
</p>
<p align="center">
  <img src="assets/screenshots/settings-2.png" alt="Settings — Python Versions & Paths" width="800">
</p>
<p align="center">
  <img src="assets/screenshots/settings-3.png" alt="Settings — pipx Python & Conda Mirrors" width="800">
</p>
<p align="center">
  <img src="assets/screenshots/settings-4.png" alt="Settings — Toolchain Manager" width="800">
</p>
<p align="center">
  <img src="assets/screenshots/settings-5.png" alt="Settings — Themes & Terminal Emulators" width="800">
</p>
<p align="center">
  <img src="assets/screenshots/settings-6.png" alt="Settings — Custom Terminals & Nerd Fonts" width="800">
</p>
<p align="center">
  <img src="assets/screenshots/settings-7.png" alt="Settings — Editor Integration & Custom Categories" width="800">
</p>
<p align="center">
  <img src="assets/screenshots/settings-8.png" alt="Settings — Preset Manager & Custom Catalog Packages" width="800">
</p>
<p align="center">
  <img src="assets/screenshots/settings-9.png" alt="Settings — General & Command Line" width="800">
</p>
<p align="center">
  <img src="assets/screenshots/settings_python_install.png" alt="Settings — Download Python (standalone builds)" width="800">
</p>
</details>

---

## 🚀 Supported Launchers

<div align="center">

*Launch any of these tools directly from VenvStudio — if installed in the active environment, it appears in the sidebar automatically.*

</div>

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
| **R** | Statistical computing language | Conda (`r-base`) or system NSIS installer |
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

Export your environment from the **Export ▾** dropdown:

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

GitHub Actions automatically builds Windows, Linux (AppImage), and macOS binaries on every tagged release.

---

## 📝 License

[LGPL-3.0](LICENSE)

---

<div align="center">

**Made with ❤️ by [Bayram Kotan](https://github.com/bayramkotan)**

[GitHub](https://github.com/bayramkotan/VenvStudio) · [PyPI](https://pypi.org/project/venvstudio/) · [Releases](https://github.com/bayramkotan/VenvStudio/releases) · [Issues](https://github.com/bayramkotan/VenvStudio/issues)

⭐ **If VenvStudio helps you, give it a star!** ⭐

</div>
