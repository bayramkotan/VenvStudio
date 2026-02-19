<p align="center">
  <img src="assets/icon.png" alt="VenvStudio" width="128" height="128">
</p>

<h1 align="center">VenvStudio</h1>

<p align="center">
  <strong>Lightweight Python Virtual Environment Manager</strong><br>
  A modern, cross-platform virtual environment manager
</p>

<p align="center">
  <a href="https://github.com/bayramkotan/VenvStudio/releases/latest">
    <img src="https://img.shields.io/github/v/release/bayramkotan/VenvStudio?style=for-the-badge&color=89b4fa&logo=github" alt="Release">
  </a>
  <img src="https://img.shields.io/badge/Python-3.8+-3776ab?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/License-LGPL--3.0-a6e3a1?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-cdd6f4?style=for-the-badge" alt="Platform">
</p>

<p align="center">
  <a href="#-download">Download</a> •
  <a href="#-features">Features</a> •
  <a href="#-installation-from-source">Install from Source</a> •
  <a href="#-cli-usage">CLI</a> •
  <a href="#-türkçe">Türkçe</a>
</p>

---

## 📥 Download

**No Python installation required** — download the binary for your platform and double-click to run:

| Platform | Download | Notes |
|----------|----------|-------|
| **Windows** | [VenvStudio.exe](https://github.com/bayramkotan/VenvStudio/releases/latest/download/VenvStudio.exe) | Double-click to run. No terminal window. |
| **Linux** | [VenvStudio AppImage](https://github.com/bayramkotan/VenvStudio/releases/latest/download/VenvStudio-x86_64.AppImage) | `chmod +x` then run. No dependencies needed. |
| **macOS** | [VenvStudio-macOS](https://github.com/bayramkotan/VenvStudio/releases/latest/download/VenvStudio-macOS) | `chmod +x` then run. |

> **All releases:** [github.com/bayramkotan/VenvStudio/releases](https://github.com/bayramkotan/VenvStudio/releases)

---

## ✨ Features

**Environment Management**
- Create, delete, clone, and rename virtual environments
- Auto-detect system Python installations
- Add custom Python interpreters
- VS Code integration — open environments directly

**Package Management**
- Browse 70+ popular packages organized in 14 categories
- Quick install presets (Data Science, Web Dev, ML, NLP, etc.)
- Install, uninstall, search, and update packages
- Import/export requirements.txt
- Custom package catalog with user-defined categories

**App Launcher**
- Launch JupyterLab, Jupyter Notebook, Spyder, Streamlit, Orange, IPython
- One-click install if not present — no terminal window

**Internationalization**
- 11 languages: English, Türkçe, Deutsch, Français, Español, Italiano, Português, 日本語, 한국어, 中文, العربية

**Customization**
- Dark & Light themes (Catppuccin-inspired design)
- Custom fonts and sizes
- Export/import settings
- Built-in diagnostics

**CLI Tool**
- `vs list`, `vs create`, `vs install`, `vs freeze`, `vs delete`, `vs clone`

---

## 🖥️ Installation from Source

### Windows

```powershell
git clone https://github.com/bayramkotan/VenvStudio.git
cd VenvStudio
pip install PySide6
python main.py
```

Or double-click `main.pyw` for no terminal window.

### Linux (Debian / Ubuntu)

```bash
# System dependencies for Qt
sudo apt install python3 python3-pip python3-venv \
  libxcb-cursor0 libxcb-xinerama0 libxcb-icccm4 \
  libxkbcommon-x11-0 libxcb-keysyms1 libxcb-image0 \
  libxcb-render-util0 libegl1

# Clone and run
git clone https://github.com/bayramkotan/VenvStudio.git
cd VenvStudio
pip install PySide6 --break-system-packages
python3 main.py
```

### macOS

```bash
git clone https://github.com/bayramkotan/VenvStudio.git
cd VenvStudio
pip3 install PySide6
python3 main.py
```

---

## ⌨️ CLI Usage

After enabling CLI from Settings, use the `vs` command from any terminal:

```bash
vs list                              # List all environments
vs create myenv                      # Create new environment
vs create myenv --python /usr/bin/python3.11  # With specific Python
vs install myenv numpy pandas flask  # Install packages
vs freeze myenv                      # Show installed packages
vs clone myenv myenv-backup          # Clone environment
vs delete myenv -y                   # Delete without confirmation
vs gui                               # Launch GUI
```

---

## 🏗️ Project Structure

```
VenvStudio/
├── main.py                    # Entry point
├── main.pyw                   # Windows no-console launcher
├── vs.py                      # CLI tool
├── vs.bat                     # CLI Windows wrapper
├── build.py                   # Cross-platform build script
├── requirements.txt           # Dependencies (PySide6)
├── assets/
│   ├── icon.png               # App icon (512x512)
│   └── icon.ico               # Windows icon
├── src/
│   ├── gui/
│   │   ├── main_window.py     # Main application window
│   │   ├── env_dialog.py      # Environment creation dialog
│   │   ├── package_panel.py   # Package management + App Launcher
│   │   ├── settings_page.py   # Settings, diagnostics, custom catalog
│   │   └── styles.py          # Dark/Light theme stylesheets
│   ├── core/
│   │   ├── venv_manager.py    # Virtual environment operations
│   │   ├── pip_manager.py     # Package (pip) operations
│   │   └── config_manager.py  # Settings persistence (JSON)
│   └── utils/
│       ├── platform_utils.py  # Cross-platform utilities
│       ├── constants.py       # Package catalog & presets
│       ├── i18n.py            # Internationalization (11 languages)
│       └── logger.py          # Logging system
├── config/
│   └── settings.json          # User settings (auto-generated)
└── .github/
    └── workflows/
        └── build.yml          # CI/CD: auto-build for 3 platforms
```

---

## 📋 Package Catalog

| Category | Examples |
|----------|---------|
| 🔬 Data Science | numpy, pandas, scipy, matplotlib, seaborn |
| 🤖 Machine Learning & AI | tensorflow, pytorch, scikit-learn, transformers |
| 🌐 Web Development | flask, django, fastapi, requests |
| 🗄️ Database | sqlalchemy, psycopg2, pymongo, redis |
| 🛠️ Development Tools | pytest, black, flake8, mypy, jupyter |
| ☁️ Cloud & DevOps | boto3, azure, docker, kubernetes |
| 📦 Utilities | click, pydantic, rich, pillow |
| 🔒 Security & Networking | cryptography, scapy, paramiko |
| 📊 Visualization | plotly, bokeh, altair, dash |
| 🕸️ Web Scraping | beautifulsoup4, scrapy, selenium |
| 🎮 Game Development | pygame, arcade, pyglet |
| 🤖 Automation | pyautogui, schedule, watchdog |
| 📐 Math & Science | sympy, networkx, biopython |
| 🔧 System & CLI | psutil, tqdm, colorama, typer |

---

## ⚡ Quick Install Presets

One-click installation of curated package bundles:

- 📊 **Data Science Starter** — numpy, pandas, matplotlib, jupyter
- 🌐 **Web API (FastAPI)** — fastapi, uvicorn, pydantic
- 🌐 **Web App (Django)** — django, djangorestframework, celery
- 🌐 **Web App (Flask)** — flask, flask-sqlalchemy, gunicorn
- 🤖 **ML Starter** — scikit-learn, tensorflow, jupyter
- 🧪 **Testing Suite** — pytest, coverage, tox, mock
- 🛠️ **Dev Essentials** — black, flake8, mypy, pre-commit
- 🔬 **NLP Toolkit** — nltk, spacy, transformers

---

## 🔧 Configuration

Settings are stored in platform-appropriate locations:

| Platform | Config Path |
|----------|------------|
| Windows | `%APPDATA%\VenvStudio\settings.json` |
| macOS | `~/Library/Application Support/VenvStudio/settings.json` |
| Linux | `~/.config/VenvStudio/settings.json` |

### Default Environment Locations

| Platform | Default Path |
|----------|-------------|
| Windows | `C:\venvstudio_envs` |
| macOS | `~/venvstudio_envs` |
| Linux | `~/venvstudio_envs` |

---

## 🔨 Building from Source

```bash
pip install pyinstaller PySide6 Pillow

# Build for current platform
python build.py

# Build with console (for debugging)
python build.py --debug

# Generate GitHub Actions CI/CD workflow
python build.py --ci

# Create Windows installer script
python build.py --installer
```

### Automated Builds (CI/CD)

Push a version tag to trigger automatic builds for all platforms:

```bash
git tag v1.2.7
git push origin v1.2.7
```

GitHub Actions will build and publish binaries to [Releases](https://github.com/bayramkotan/VenvStudio/releases).

---

## 📄 License

This project is licensed under the **LGPL-3.0 License** — you are free to use, modify, and distribute it.

PySide6 is used under the LGPL license (Qt for Python, official Qt binding).

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 🇹🇷 Türkçe

### İndirme

Python kurmanıza gerek yok — platformunuza göre dosyayı indirip çift tıklayın:

| Platform | İndir |
|----------|-------|
| **Windows** | [VenvStudio.exe](https://github.com/bayramkotan/VenvStudio/releases/latest/download/VenvStudio.exe) |
| **Linux** | [VenvStudio AppImage](https://github.com/bayramkotan/VenvStudio/releases/latest/download/VenvStudio-x86_64.AppImage) |
| **macOS** | [VenvStudio-macOS](https://github.com/bayramkotan/VenvStudio/releases/latest/download/VenvStudio-macOS) |

### Kaynak Koddan Kurulum (Linux Debian/Ubuntu)

```bash
# Qt sistem bağımlılıkları
sudo apt install python3 python3-pip python3-venv \
  libxcb-cursor0 libxcb-xinerama0 libxcb-icccm4 \
  libxkbcommon-x11-0 libxcb-keysyms1 libxcb-image0 \
  libxcb-render-util0 libegl1

# Klonla ve çalıştır
git clone https://github.com/bayramkotan/VenvStudio.git
cd VenvStudio
pip install PySide6 --break-system-packages
python3 main.py
```

### Özellikler

- Sanal ortam oluşturma, silme, klonlama, yeniden adlandırma
- 70+ paket kataloğu, 14 kategori
- Hazır paket setleri (Veri Bilimi, Web, ML, NLP)
- Uygulama başlatıcı (JupyterLab, Spyder, Streamlit)
- 11 dil desteği (Türkçe dahil)
- Koyu ve açık tema
- Ayarları dışa/içe aktarma
- CLI aracı (`vs` komutu)
- Windows, macOS, Linux desteği

---

<p align="center">
  <strong>VenvStudio</strong> — Python ortam yönetimi basit olmalı. 🐍
</p>
