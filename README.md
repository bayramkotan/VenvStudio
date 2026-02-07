# 🐍 VenvStudio

**Lightweight Python Virtual Environment Manager**

A modern, cross-platform application for managing Python virtual environments. Built with PySide6 (Qt for Python) under LGPL-3.0 license.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)
![License](https://img.shields.io/badge/License-LGPL--3.0-green)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

---

## ✨ Features

- **Create & Manage** virtual environments with a modern GUI
- **Cross-Platform** — works on Windows, macOS, and Linux
- **Package Catalog** — browse 70+ popular packages organized by category
- **Quick Presets** — one-click installation of curated package bundles (Data Science, Web Dev, ML, etc.)
- **Package Management** — install, uninstall, search, and update packages
- **Requirements.txt** — import/export support
- **Clone Environments** — duplicate existing environments
- **Open Terminal** — launch a terminal with the environment activated
- **Dark & Light Themes** — Catppuccin-inspired modern design
- **Lightweight** — only dependency is PySide6

## 📦 Installation

### Prerequisites

- Python 3.8 or higher
- pip

### Install

```bash
# Clone the repository
git clone https://github.com/yourusername/venvstudio.git
cd venvstudio

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

## 🖥️ Default Environment Locations

| Platform | Default Path |
|----------|-------------|
| Windows  | `C:\venvstudio_envs` |
| macOS    | `~/venvstudio_envs` |
| Linux    | `~/venvstudio_envs` |

You can change this in **File → Settings** or when creating a new environment.

## 🏗️ Project Structure

```
venvstudio/
├── main.py                      # Entry point
├── requirements.txt             # Dependencies (PySide6)
├── LICENSE                      # LGPL-3.0
├── README.md
├── src/
│   ├── gui/
│   │   ├── main_window.py      # Main application window
│   │   ├── env_dialog.py       # Environment creation dialog
│   │   ├── package_panel.py    # Package management panel
│   │   └── styles.py           # Dark/Light theme stylesheets
│   ├── core/
│   │   ├── venv_manager.py     # Virtual environment operations
│   │   ├── pip_manager.py      # Package (pip) operations
│   │   └── config_manager.py   # Settings persistence (JSON)
│   └── utils/
│       ├── platform_utils.py   # Cross-platform utilities
│       └── constants.py        # Package catalog & presets
└── config/
    └── settings.json           # User settings (auto-generated)
```

## 🎨 Screenshots

The application features a modern sidebar-based design with:
- **Environments Page** — list, create, delete, clone environments
- **Packages Page** — browse catalog, manage installed packages, quick presets
- **Dark & Light Themes** — toggle from View menu

## 📋 Package Catalog Categories

- 🔬 Data Science (numpy, pandas, scipy, matplotlib, etc.)
- 🤖 Machine Learning & AI (tensorflow, pytorch, transformers, etc.)
- 🌐 Web Development (flask, django, fastapi, etc.)
- 🗄️ Database (sqlalchemy, psycopg2, pymongo, etc.)
- 🛠️ Development Tools (pytest, black, flake8, jupyter, etc.)
- ☁️ Cloud & DevOps (boto3, azure, docker, etc.)
- 📦 Utilities (click, pydantic, rich, pillow, etc.)
- 🔒 Security & Networking (cryptography, scapy, etc.)

## ⚡ Quick Install Presets

- 📊 Data Science Starter
- 🌐 Web API (FastAPI)
- 🌐 Web App (Django / Flask)
- 🤖 ML Starter
- 🧪 Testing Suite
- 🛠️ Dev Essentials
- 🔬 NLP Toolkit

## 🔧 Configuration

Settings are stored in platform-appropriate locations:

| Platform | Config Path |
|----------|------------|
| Windows  | `%APPDATA%\VenvStudio\settings.json` |
| macOS    | `~/Library/Application Support/VenvStudio/settings.json` |
| Linux    | `~/.config/VenvStudio/settings.json` |

## 📄 License

This project is licensed under the **LGPL-3.0 License** — you are free to use, modify, and distribute it.

PySide6 is used under the LGPL license (Qt for Python, official Qt binding).

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

**VenvStudio** — Because managing Python environments should be simple. 🐍
