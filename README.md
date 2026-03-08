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
  <a href="#-install">Install</a> •
  <a href="#-features">Features</a> •
  <a href="#-screenshots">Screenshots</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-export-formats">Export</a> •
  <a href="#-build-from-source">Build</a>
</p>

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

<table>
<tr>
<td width="50%" valign="top">

### 🗂️ Environment Management
- Create, rename, clone, delete virtual environments
- Auto-detect existing environments at startup
- Per-environment cache — instant load, zero delays
- **Default Environment** — opens automatically on launch
- Open terminal with env pre-activated
- Export to 6 formats (see below)

</td>
<td width="50%" valign="top">

### 📦 Package Management
- **Installed** — filter, select, uninstall, export, import
- **Catalog** — 200+ curated packages across 15 categories
- **Presets** — one-click bundles (Data Science, Web API, Django, ML, NLP...)
- **Manual Install** — paste package names or version specs
- pip or **uv** backend (10–100× faster)
- Check for package updates

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🚀 Quick Launch
- Sidebar shows installed apps for active env
- **13+ one-click launchers** — [see full list below](#-supported-launchers)
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

</td>
</tr>
<tr>
<td width="50%" valign="top">

### ⚙️ Settings
- 🌙 Dark (Catppuccin) and ☀️ Light themes
- Font family and size customization
- 🌍 English & Turkish
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

## 📸 Screenshots

<details open>
<summary><b>🗂️ Environments</b></summary>
<br>
<p align="center">
  <img src="assets/screenshots/environment1.png" alt="Virtual Environments" width="800">
</p>
</details>

<details>
<summary><b>🚀 Launch Apps</b></summary>
<br>
<p align="center">
  <img src="assets/screenshots/packages-launch1.png" alt="Launch Applications" width="800">
</p>
</details>

<details>
<summary><b>📦 Installed Packages</b></summary>
<br>
<p align="center">
  <img src="assets/screenshots/packages1.png" alt="Installed Packages" width="800">
</p>
<p align="center">
  <img src="assets/screenshots/packages2.png" alt="Right-click Context Menu" width="800">
</p>
<p align="center">
  <img src="assets/screenshots/packages3.png" alt="Package Info (pip show)" width="800">
</p>
</details>

<details>
<summary><b>📚 Package Catalog</b></summary>
<br>
<p align="center">
  <img src="assets/screenshots/packages-catalog1.png" alt="Package Catalog" width="800">
</p>
</details>

<details>
<summary><b>⚡ Presets</b></summary>
<br>
<p align="center">
  <img src="assets/screenshots/packages-presets1.png" alt="Presets" width="800">
</p>
<p align="center">
  <img src="assets/screenshots/packages-presets2.png" alt="Preset Install" width="800">
</p>
</details>

<details>
<summary><b>📝 Manual Install</b></summary>
<br>
<p align="center">
  <img src="assets/screenshots/packages-manual_install_1.png" alt="Manual Install" width="800">
</p>
</details>

<details>
<summary><b>⚙️ Settings</b></summary>
<br>
<p align="center">
  <img src="assets/screenshots/settings1.png" alt="Settings - Appearance & Language" width="800">
</p>
<p align="center">
  <img src="assets/screenshots/settings2_python_install.png" alt="Settings - Python & Paths" width="800">
</p>
<p align="center">
  <img src="assets/screenshots/settings3.png" alt="Settings - Custom Catalog & Diagnostics" width="800">
</p>
</details>

---

## 🚀 Supported Launchers

<div align="center">

*Launch any of these tools directly from VenvStudio — if installed in the active environment, it appears in the sidebar automatically.*

</div>

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

Export your environment from the **Export ▾** dropdown:

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
