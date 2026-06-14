"""
VenvStudio - Constants and Popular Package Catalog
"""

APP_NAME = "VenvStudio"
APP_VERSION = "1.5.2"

# ─── Shared Package Cache ─────────────────────────────────────────────────────
# Default path for pip/uv shared download cache.
# pip  → --cache-dir <path>
# uv   → UV_CACHE_DIR env var
import os as _os
DEFAULT_SHARED_CACHE_DIR = str(_os.path.join(_os.path.expanduser("~"), ".venvstudio", "pkg-cache"))
APP_DESCRIPTION = "Lightweight Python Virtual Environment Manager"
APP_AUTHOR = "VenvStudio Team"

# ─── Educational: Preset Descriptions ────────────────────────────────────────
# Shown on preset cards to explain what each preset is for and who should use it.

PRESET_DESCRIPTIONS = {
    "📊 Data Science Starter": (
        "Essential tools for data analysis and visualization. "
        "Includes NumPy for numerical computing, Pandas for data manipulation, "
        "Matplotlib for plotting, Scikit-learn for ML, and Jupyter for interactive notebooks. "
        "Perfect for beginners starting their data science journey."
    ),
    "🌐 Web API (FastAPI)": (
        "Build modern, high-performance REST APIs. "
        "FastAPI provides automatic API documentation (Swagger UI), "
        "Pydantic handles data validation, SQLAlchemy manages databases, "
        "and Uvicorn serves your application. Great for backend development."
    ),
    "🌐 Web App (Django)": (
        "Full-featured web application framework with batteries included. "
        "Django provides ORM, admin panel, authentication, and templating out of the box. "
        "Includes PostgreSQL support and Celery for background tasks."
    ),
    "🌐 Web App (Flask)": (
        "Lightweight and flexible web framework. "
        "Flask gives you the basics and lets you choose your own tools. "
        "Includes SQLAlchemy for database, CORS support, and Gunicorn for production serving."
    ),
    "🤖 ML Starter": (
        "Machine learning essentials for building and evaluating models. "
        "Scikit-learn provides classification, regression, and clustering algorithms. "
        "XGBoost adds powerful gradient boosting. Jupyter enables interactive experimentation."
    ),
    "👁️ Computer Vision": (
        "Tools for image processing and object detection. "
        "OpenCV handles image/video operations, Pillow for image manipulation, "
        "YOLOv8 (Ultralytics) for real-time object detection, "
        "and PyTorch + TorchVision for deep learning models."
    ),
    "🧪 Testing Suite": (
        "Professional testing tools for Python projects. "
        "Pytest is the standard testing framework, pytest-cov measures code coverage, "
        "Factory Boy creates test fixtures, and Faker generates realistic test data."
    ),
    "🛠️ Dev Essentials": (
        "Code quality tools every Python developer should use. "
        "Black auto-formats your code, Flake8 checks for style issues, "
        "MyPy catches type errors before runtime, isort organizes imports, "
        "and pre-commit runs checks automatically on every git commit."
    ),
    "🔬 NLP Toolkit": (
        "Natural Language Processing tools for text analysis. "
        "Transformers provides pre-trained models (BERT, GPT, etc.), "
        "NLTK for tokenization and linguistic analysis, "
        "spaCy for production-ready NLP pipelines. "
        "⚠️ spaCy requires Python 3.10+ on Windows."
    ),
    "🖥️ GUI Development": (
        "Build desktop applications with Python. "
        "PySide6 is the official Qt for Python binding — create professional cross-platform GUIs. "
        "PyInstaller packages your app into a standalone .exe or .app file."
    ),
    "📊 Visualization Suite": (
        "Advanced data visualization libraries. "
        "Matplotlib for static plots, Seaborn for statistical graphics, "
        "Plotly for interactive charts, Bokeh for web-based dashboards, "
        "and Altair for declarative visualizations."
    ),
    "🧪 JupyterLab Full": (
        "Complete JupyterLab setup with interactive widgets. "
        "JupyterLab is the next-generation notebook interface. "
        "ipywidgets adds interactive controls (sliders, buttons, dropdowns) to your notebooks."
    ),
    "📈 Time Series (Classic)": (
        "Statistical time series analysis and forecasting. "
        "Statsmodels for ARIMA/SARIMAX, pmdarima for auto-ARIMA, "
        "Prophet for trend/seasonality decomposition, "
        "sktime for unified ML, tsfresh for automatic feature extraction."
    ),
    "📈 Time Series (Deep Learning)": (
        "Neural network-based time series forecasting. "
        "PyTorch Forecasting for temporal fusion transformers, "
        "Darts for easy-to-use forecasting models, "
        "NeuralForecast for state-of-the-art neural models, "
        "GluonTS for probabilistic forecasting."
    ),
    "💰 Financial Analysis": (
        "Quantitative finance and algorithmic trading tools. "
        "yfinance downloads market data, QuantLib for derivatives pricing, "
        "Zipline for backtesting trading strategies, "
        "PyFolio for portfolio performance analysis."
    ),
    "💰 Financial LLM": (
        "Fine-tune large language models for financial applications. "
        "Transformers + PEFT for parameter-efficient fine-tuning, "
        "bitsandbytes for quantization (reduce memory usage), "
        "Accelerate for distributed training."
    ),
}

# ─── Educational: Launcher Tooltips ──────────────────────────────────────────
# Detailed tooltips for launcher cards — shown on hover.
# Format: {package_name: "tooltip text"}

LAUNCHER_TOOLTIPS = {
    "jupyterlab": (
        "🔬 JupyterLab — Interactive Computing Environment\n\n"
        "JupyterLab is a web-based IDE for notebooks, code, and data.\n"
        "You can write Python code in cells, see results instantly,\n"
        "mix code with visualizations and Markdown text.\n\n"
        "💡 Perfect for: data exploration, prototyping, teaching\n"
        "🌐 Opens in your browser at http://localhost:8888"
    ),
    "notebook": (
        "📓 Jupyter Notebook — Classic Notebook Interface\n\n"
        "The original Jupyter Notebook — simple, document-centric.\n"
        "Each notebook is a .ipynb file with code cells and outputs.\n\n"
        "💡 Perfect for: quick experiments, sharing analysis\n"
        "🌐 Opens in your browser at http://localhost:8888"
    ),
    "orange3": (
        "🍊 Orange Data Mining — Visual Programming\n\n"
        "Build data analysis workflows by connecting visual blocks.\n"
        "No coding required! Drag-and-drop widgets for classification,\n"
        "clustering, visualization, and more.\n\n"
        "💡 Perfect for: learning ML concepts, quick prototyping\n"
        "⚠️ Requires PyQt5 (installed automatically)"
    ),
    "spyder": (
        "🕷️ Spyder IDE — Scientific Python IDE\n\n"
        "A MATLAB-like development environment for Python.\n"
        "Features variable explorer, integrated plots, debugger,\n"
        "and IPython console.\n\n"
        "💡 Perfect for: scientific computing, data analysis"
    ),
    "ipython": (
        "🐍 IPython — Enhanced Python Shell\n\n"
        "A powerful interactive Python shell with:\n"
        "• Tab completion and syntax highlighting\n"
        "• Magic commands (%timeit, %run, %matplotlib)\n"
        "• Rich history and auto-indentation\n\n"
        "💡 Perfect for: quick testing, learning Python interactively"
    ),
    "streamlit": (
        "🎈 Streamlit — Data Apps in Minutes\n\n"
        "Turn Python scripts into interactive web apps.\n"
        "Just use st.write(), st.slider(), st.plot() etc.\n"
        "No HTML/CSS/JS knowledge needed!\n\n"
        "💡 Perfect for: dashboards, data demos, ML model showcases\n"
        "🌐 Opens at http://localhost:8501"
    ),
    "gradio": (
        "🤗 Gradio — ML Demo Builder\n\n"
        "Create web interfaces for ML models in 3 lines of code.\n"
        "Supports text, image, audio, video inputs/outputs.\n"
        "Share your demo with a public link instantly.\n\n"
        "💡 Perfect for: ML model demos, AI prototypes\n"
        "🌐 Opens at http://localhost:7860"
    ),
    "dash": (
        "📊 Dash by Plotly — Analytical Dashboards\n\n"
        "Build interactive analytical web apps with Python.\n"
        "Combines Plotly charts with HTML components.\n"
        "Reactive callbacks update charts automatically.\n\n"
        "💡 Perfect for: business dashboards, data reporting\n"
        "🌐 Opens at http://localhost:8050"
    ),
    "panel": (
        "🔲 Panel — HoloViz Dashboard Toolkit\n\n"
        "Create dashboards and data apps from notebooks or scripts.\n"
        "Works with Matplotlib, Plotly, Bokeh, and more.\n\n"
        "💡 Perfect for: scientific dashboards, interactive reports"
    ),
    "voila": (
        "📓 Voilà — Notebooks as Web Apps\n\n"
        "Turns Jupyter notebooks into standalone web applications.\n"
        "Hides all code cells — only shows outputs and widgets.\n\n"
        "💡 Perfect for: sharing analysis with non-technical users"
    ),
    "mlflow": (
        "🧪 MLflow — ML Experiment Tracking\n\n"
        "Track experiments, compare model metrics, manage models.\n"
        "Log parameters, metrics, and artifacts for every run.\n"
        "Built-in model registry for versioning.\n\n"
        "💡 Perfect for: ML experimentation, model management\n"
        "🌐 Opens at http://localhost:5000"
    ),
    "tensorboard": (
        "📈 TensorBoard — Training Visualization\n\n"
        "Visualize training metrics, model graphs, embeddings.\n"
        "Works with TensorFlow, PyTorch, and other frameworks.\n"
        "Select a log directory to see training progress.\n\n"
        "💡 Perfect for: monitoring deep learning training\n"
        "🌐 Opens at http://localhost:6006"
    ),
    "fastapi": (
        "⚡ FastAPI — Modern Web API Framework\n\n"
        "Build APIs with automatic documentation (Swagger UI).\n"
        "Type hints → automatic validation and serialization.\n"
        "Async support for high-performance applications.\n\n"
        "💡 Perfect for: REST APIs, microservices, backends\n"
        "🌐 API docs at http://localhost:8000/docs"
    ),
    "datasette": (
        "🗄️ Datasette — Explore SQLite Databases\n\n"
        "Instantly publish and explore SQLite databases as a web app.\n"
        "Browse tables, run SQL queries, export data as JSON/CSV.\n\n"
        "💡 Perfect for: data exploration, publishing open data\n"
        "🌐 Opens at http://localhost:8001"
    ),
    "marimo": (
        "🌊 Marimo — Reactive Notebook\n\n"
        "A next-generation Python notebook where every cell is reactive.\n"
        "Change a variable and all dependent cells update automatically.\n"
        "Notebooks run as scripts, apps, or slides too.\n\n"
        "💡 Perfect for: interactive data exploration, reproducible analysis\n"
        "🌐 Opens at http://localhost:2718"
    ),
    "r_console": (
        "📐 R Console — Statistical Computing\n\n"
        "R is the leading language for statistical analysis and data science.\n"
        "Thousands of packages via CRAN for statistics, ML, and visualization.\n\n"
        "💡 Perfect for: statistics, bioinformatics, academic research\n"
        "⚠️ Requires R to be installed: https://cran.r-project.org"
    ),
    "rstudio": (
        "🎯 RStudio — R Development Environment\n\n"
        "The most popular IDE for R with integrated console, plots,\n"
        "environment inspector, package manager, and R Markdown support.\n\n"
        "💡 Perfect for: data analysis, statistical modeling, reporting\n"
        "⚠️ Requires RStudio: https://posit.co/download/rstudio-desktop"
    ),
    "ollama": (
        "🦙 Ollama — Local LLM Runner\n\n"
        "Run large language models locally on your own hardware.\n"
        "Supports Llama 3, Mistral, Gemma, Phi, Qwen, and many more.\n"
        "Starts an OpenAI-compatible API at http://localhost:11434\n\n"
        "💡 Perfect for: private AI, offline LLMs, API integration\n"
        "⚠️ Requires Ollama: https://ollama.com"
    ),
    "dbeaver": (
        "🦫 DBeaver — Universal Database Manager\n\n"
        "Connect to PostgreSQL, MySQL, SQLite, MongoDB, and 80+ databases.\n"
        "Visual query builder, ER diagrams, data export/import.\n\n"
        "💡 Perfect for: database exploration, SQL development\n"
        "⚠️ Requires DBeaver: https://dbeaver.io"
    ),
    "quarto": (
        "📝 Quarto — Scientific Publishing System\n\n"
        "Create documents, slides, websites, and books from notebooks.\n"
        "Supports Python, R, Julia, and Observable JS in one document.\n"
        "Output to HTML, PDF, Word, Reveal.js, and more.\n\n"
        "💡 Perfect for: research reports, technical documentation\n"
        "⚠️ Requires Quarto: https://quarto.org"
    ),
    "jamovi": (
        "🧩 jamovi — Point-and-Click Statistics\n\n"
        "A free, open SPSS alternative with a clean modern interface.\n"
        "Runs on R under the hood — no coding needed.\n"
        "Descriptives, t-tests, ANOVA, regression, factor analysis and more.\n\n"
        "💡 Perfect for: students, researchers, SPSS/SPSS migrants\n"
        "⚠️ System install — VenvStudio will auto-install if not found"
    ),
    "jasp": (
        "📊 JASP — Bayesian & Frequentist Statistics\n\n"
        "Beautiful free statistics software with Bayesian analysis.\n"
        "Point-and-click interface with publication-ready output.\n"
        "Covers t-tests, ANOVA, regression, SEM, meta-analysis and more.\n\n"
        "💡 Perfect for: academic research, Bayesian inference\n"
        "⚠️ System install — VenvStudio will auto-install if not found"
    ),
}

# ─── Educational: UI Tooltips ────────────────────────────────────────────────
# Tooltips for buttons, labels, and UI elements throughout the app.

UI_TOOLTIPS = {
    # Main Window — Sidebar
    "sidebar_packages": "📦 Manage packages in your virtual environments.\nInstall, uninstall, and update Python packages.",
    "sidebar_environments": "📁 View and manage your virtual environments.\nCreate, delete, clone, rename, and export envs.",
    "sidebar_settings": "⚙️ Configure VenvStudio.\nTheme, language, Python versions, terminal, CLI tools.",

    # Environments Page
    "btn_new_env": "➕ Create a new virtual environment.\n\n💡 A virtual environment (venv) is an isolated Python installation.\nPackages installed in one venv don't affect others.",
    "btn_refresh": "🔄 Refresh the environment list.\nRe-scans the base directory for new or changed envs.",
    "btn_manage_pkgs": "📦 Open the package manager for this environment.\nInstall, uninstall, and update packages.",
    "btn_terminal": "🖥️ Open a terminal with this environment activated.\n\n💡 The terminal will automatically run the activation command\nso you can use Python and pip directly.",
    "btn_clone": "📋 Create a copy of this environment.\nA new env is created with the same packages installed.",
    "btn_rename": "✏️ Rename this environment.\nCreates a new env with the same packages and removes the old one.",
    "btn_export": "📤 Export this environment's packages.\nChoose from: requirements.txt, Dockerfile, docker-compose.yml,\npyproject.toml, environment.yml, or clipboard.",
    "btn_delete": "🗑️ Delete this environment permanently.\n⚠️ This cannot be undone!",
    "btn_make_default": "⭐ Set as default environment.\nThis env will be opened automatically when VenvStudio starts.",

    # Package Panel
    "env_selector": "🔄 Select which virtual environment to manage.\nPackages shown below belong to the selected env.",
    "btn_open_terminal": "🖥️ Open a terminal with this env activated.\n\n💡 Equivalent command:\n  source venv/bin/activate  (Linux/Mac)\n  .\\Scripts\\Activate.ps1    (Windows)",
    "tab_launch": "🚀 Launch installed applications.\nStart Jupyter, Streamlit, Gradio, and other tools\ndirectly from VenvStudio.",
    "tab_installed": "📦 View all installed packages.\nSelect packages to uninstall or check for updates.",
    "tab_catalog": "📚 Browse popular Python packages by category.\nClick to install packages you need.",
    "tab_presets": "⚡ Install pre-configured package sets.\nOne click to install a complete development stack.",
    "tab_manual": "✏️ Manually install packages by name.\nType package names separated by spaces or newlines.\n\n💡 You can paste from pip install commands — VenvStudio\nwill automatically extract the package names.",

    # Quick Launch
    "ql_section": "⚡ Quick Launch\nLaunch installed apps directly from the sidebar.\nSelect an environment from the dropdown below.",
}

# ─── Educational: Concept Explanations ───────────────────────────────────────
# Short explanations for concepts that appear in the UI.

EDUCATIONAL_HINTS = {
    "what_is_venv": (
        "💡 What is a Virtual Environment?\n\n"
        "A virtual environment (venv) is an isolated Python installation.\n"
        "Each venv has its own packages — installing NumPy in one venv\n"
        "doesn't affect other venvs or your system Python.\n\n"
        "This prevents version conflicts between projects.\n"
        "For example, Project A needs Django 4.2 and Project B needs Django 5.0\n"
        "— each can have its own venv with the right version."
    ),
    "what_is_pip": (
        "💡 What is pip?\n\n"
        "pip is Python's package installer. It downloads and installs\n"
        "packages from PyPI (Python Package Index) — a repository\n"
        "of over 500,000 Python packages.\n\n"
        "Common commands:\n"
        "  pip install numpy      — install a package\n"
        "  pip uninstall numpy    — remove a package\n"
        "  pip list               — show installed packages\n"
        "  pip freeze             — export package versions"
    ),
    "what_is_pypi": (
        "💡 What is PyPI?\n\n"
        "PyPI (Python Package Index) is the official repository\n"
        "for Python packages. When you run 'pip install numpy',\n"
        "pip downloads it from pypi.org.\n\n"
        "🌐 Browse packages: https://pypi.org"
    ),
    "what_is_requirements": (
        "💡 What is requirements.txt?\n\n"
        "A text file listing all packages and their versions.\n"
        "Used to recreate the same environment on another machine.\n\n"
        "  pip freeze > requirements.txt   — export\n"
        "  pip install -r requirements.txt — import\n\n"
        "This is how teams share their project dependencies."
    ),
}

PACKAGE_CATALOG = {
    "🔬 Data Exploration & Transformation": {
        "icon": "🔬",
        "packages": [
            {"name": "numpy", "desc": "Fundamental package for numerical computing"},
            {"name": "pandas", "desc": "Data analysis and manipulation library"},
            {"name": "scipy", "desc": "Scientific computing and technical computing"},
            {"name": "jupyter", "desc": "Interactive notebooks for data exploration"},
            {"name": "intake", "desc": "Data catalog and loading library"},
            {"name": "dask", "desc": "Parallel computing with task scheduling"},
            {"name": "polars", "desc": "Fast DataFrame library written in Rust"},
            {"name": "statsmodels", "desc": "Statistical modeling and econometrics"},
            {"name": "sympy", "desc": "Symbolic mathematics"},
        ],
    },
    "📊 Visualization": {
        "icon": "📊",
        "packages": [
            {"name": "matplotlib", "desc": "2D plotting and visualization"},
            {"name": "seaborn", "desc": "Statistical data visualization"},
            {"name": "plotly", "desc": "Interactive graphing library"},
            {"name": "bokeh", "desc": "Interactive visualization for modern browsers"},
            {"name": "holoviews", "desc": "Declarative data visualization"},
            {"name": "altair", "desc": "Declarative statistical visualization"},
            {"name": "dash", "desc": "Web-based analytical dashboards"},
        ],
    },
    "🤖 AI & Machine Learning": {
        "icon": "🤖",
        "packages": [
            {"name": "scikit-learn", "desc": "Machine learning algorithms"},
            {"name": "tensorflow", "desc": "Google's ML framework"},
            {"name": "keras", "desc": "High-level neural networks API"},
            {"name": "torch", "desc": "PyTorch - Facebook's ML framework"},
            {"name": "xgboost", "desc": "Gradient boosting framework"},
            {"name": "lightgbm", "desc": "Light gradient boosting machine"},
            {"name": "opencv-python", "desc": "Computer vision library"},
            {"name": "onnx", "desc": "Open Neural Network Exchange format"},
        ],
    },
    "📝 Natural Language Processing": {
        "icon": "📝",
        "packages": [
            {"name": "nltk", "desc": "Natural language toolkit"},
            {"name": "gensim", "desc": "Topic modeling and document similarity"},
            {"name": "transformers", "desc": "Hugging Face transformer models"},
            {"name": "spacy", "desc": "Industrial-strength NLP"},
            {"name": "textblob", "desc": "Simple NLP tasks"},
            {"name": "sentence-transformers", "desc": "Sentence embeddings"},
        ],
    },
    "🖥️ GUI & Frontend": {
        "icon": "🖥️",
        "packages": [
            {"name": "flask", "desc": "Lightweight WSGI web framework"},
            {"name": "cherrypy", "desc": "Minimalist Python web framework"},
            {"name": "streamlit", "desc": "Create data apps in minutes"},
            {"name": "panel", "desc": "High-level app and dashboarding solution"},
            {"name": "gradio", "desc": "Build ML demos quickly"},
            {"name": "PySide6", "desc": "Qt for Python - GUI toolkit"},
        ],
    },
    "🌐 Web Development": {
        "icon": "🌐",
        "packages": [
            {"name": "django", "desc": "High-level Python web framework"},
            {"name": "fastapi", "desc": "Modern, fast web framework for APIs"},
            {"name": "uvicorn", "desc": "ASGI web server implementation"},
            {"name": "requests", "desc": "HTTP library for humans"},
            {"name": "httpx", "desc": "Async-capable HTTP client"},
            {"name": "beautifulsoup4", "desc": "Web scraping library"},
            {"name": "selenium", "desc": "Browser automation"},
            {"name": "aiohttp", "desc": "Async HTTP client/server"},
        ],
    },
    "🗄️ Database": {
        "icon": "🗄️",
        "packages": [
            {"name": "sqlalchemy", "desc": "SQL toolkit and ORM"},
            {"name": "psycopg2-binary", "desc": "PostgreSQL adapter"},
            {"name": "pymongo", "desc": "MongoDB driver"},
            {"name": "redis", "desc": "Redis Python client"},
            {"name": "sqlite-utils", "desc": "SQLite utilities"},
            {"name": "peewee", "desc": "Simple and small ORM"},
            {"name": "alembic", "desc": "Database migration tool"},
        ],
    },
    "🛠️ Development Tools": {
        "icon": "🛠️",
        "packages": [
            {"name": "pytest", "desc": "Testing framework"},
            {"name": "black", "desc": "Code formatter"},
            {"name": "flake8", "desc": "Linting tool"},
            {"name": "mypy", "desc": "Static type checker"},
            {"name": "pylint", "desc": "Code analysis tool"},
            {"name": "isort", "desc": "Import sorter"},
            {"name": "pre-commit", "desc": "Git pre-commit hooks"},
            {"name": "tox", "desc": "Test automation"},
            {"name": "ipython", "desc": "Enhanced interactive Python"},
        ],
    },
    "☁️ Cloud & DevOps": {
        "icon": "☁️",
        "packages": [
            {"name": "boto3", "desc": "AWS SDK for Python"},
            {"name": "azure-storage-blob", "desc": "Azure Blob Storage client"},
            {"name": "google-cloud-storage", "desc": "Google Cloud Storage client"},
            {"name": "docker", "desc": "Docker SDK for Python"},
            {"name": "fabric", "desc": "Remote execution and deployment"},
            {"name": "paramiko", "desc": "SSH2 protocol library"},
        ],
    },
    "📦 Utilities": {
        "icon": "📦",
        "packages": [
            {"name": "click", "desc": "CLI creation toolkit"},
            {"name": "typer", "desc": "CLI apps with type hints"},
            {"name": "rich", "desc": "Rich text and formatting in terminal"},
            {"name": "pydantic", "desc": "Data validation using type hints"},
            {"name": "python-dotenv", "desc": "Read .env files"},
            {"name": "loguru", "desc": "Simplified logging"},
            {"name": "tqdm", "desc": "Progress bar library"},
            {"name": "pillow", "desc": "Image processing library"},
            {"name": "pyyaml", "desc": "YAML parser and emitter"},
        ],
    },
    "🔒 Security & Networking": {
        "icon": "🔒",
        "packages": [
            {"name": "cryptography", "desc": "Cryptographic recipes and primitives"},
            {"name": "pyjwt", "desc": "JSON Web Token implementation"},
            {"name": "bcrypt", "desc": "Password hashing"},
            {"name": "scapy", "desc": "Packet manipulation library"},
            {"name": "python-nmap", "desc": "Nmap port scanner interface"},
        ],
    },
    "📈 Time Series & Forecasting": {
        "icon": "📈",
        "packages": [
            {"name": "statsmodels", "desc": "Statistical modeling and econometrics"},
            {"name": "pmdarima", "desc": "Auto-ARIMA time series modeling"},
            {"name": "prophet", "desc": "Facebook's forecasting tool"},
            {"name": "sktime", "desc": "Unified time series ML framework"},
            {"name": "tsfresh", "desc": "Automatic time series feature extraction"},
            {"name": "darts", "desc": "Easy manipulation and forecasting of time series"},
            {"name": "neuralforecast", "desc": "Neural forecasting models"},
            {"name": "gluonts", "desc": "Probabilistic time series modeling"},
            {"name": "pytorch-forecasting", "desc": "Time series forecasting with PyTorch"},
            {"name": "tslearn", "desc": "Time series machine learning toolkit"},
        ],
    },
    "💰 Finance & Quantitative": {
        "icon": "💰",
        "packages": [
            {"name": "yfinance", "desc": "Yahoo Finance market data downloader"},
            {"name": "pandas-ta", "desc": "Technical analysis indicators for pandas"},
            {"name": "zipline-reloaded", "desc": "Algorithmic trading backtester"},
            {"name": "pyfolio", "desc": "Portfolio and risk analytics"},
            {"name": "quantlib", "desc": "Quantitative finance library"},
            {"name": "alpaca-py", "desc": "Alpaca Markets trading API"},
            {"name": "ccxt", "desc": "Cryptocurrency exchange trading library"},
            {"name": "finbert-embedding", "desc": "Financial domain BERT embeddings"},
            {"name": "datasets", "desc": "Hugging Face datasets for ML"},
            {"name": "peft", "desc": "Parameter-efficient fine-tuning"},
        ],
    },
    "🖼️ Image & Computer Vision": {
        "icon": "🖼️",
        "packages": [
            {"name": "pillow", "desc": "Image processing library"},
            {"name": "opencv-python", "desc": "Computer vision library"},
            {"name": "scikit-image", "desc": "Image processing in Python"},
            {"name": "torchvision", "desc": "PyTorch computer vision models"},
            {"name": "ultralytics", "desc": "YOLOv8 object detection"},
            {"name": "albumentations", "desc": "Image augmentation library"},
        ],
    },
    "🤖 Automation & Scripting": {
        "icon": "🤖",
        "packages": [
            {"name": "pyautogui", "desc": "GUI automation"},
            {"name": "schedule", "desc": "Job scheduling for humans"},
            {"name": "watchdog", "desc": "Filesystem event monitoring"},
            {"name": "openpyxl", "desc": "Excel file read/write"},
            {"name": "python-pptx", "desc": "PowerPoint file manipulation"},
            {"name": "python-docx", "desc": "Word document creation"},
            {"name": "reportlab", "desc": "PDF generation"},
        ],
    },
    "🧪 IDE & Tools": {
        "icon": "🧪",
        "packages": [
            {"name": "spyder-kernels", "desc": "Spyder IDE kernel support"},
            {"name": "jupyterlab", "desc": "JupyterLab - next-gen notebook interface"},
            {"name": "notebook", "desc": "Jupyter Notebook classic"},
            {"name": "orange3", "desc": "Orange - visual programming for data mining"},
            {"name": "voila", "desc": "Turn notebooks into standalone web apps"},
            {"name": "ipywidgets", "desc": "Interactive widgets for Jupyter"},
        ],
    },
}

PRESETS = {
    "📊 Data Science Starter": ["numpy", "pandas", "matplotlib", "scikit-learn", "jupyter"],
    "🌐 Web API (FastAPI)": ["fastapi", "uvicorn", "sqlalchemy", "pydantic", "python-dotenv"],
    "🌐 Web App (Django)": ["django", "psycopg2-binary", "django-rest-framework", "celery"],
    "🌐 Web App (Flask)": ["flask", "sqlalchemy", "flask-cors", "gunicorn"],
    "🤖 ML Starter": ["numpy", "pandas", "scikit-learn", "matplotlib", "jupyter", "xgboost"],
    "👁️ Computer Vision": ["opencv-python", "pillow", "scikit-image", "ultralytics", "torch", "torchvision"],
    "🧪 Testing Suite": ["pytest", "pytest-cov", "pytest-asyncio", "factory-boy", "faker"],
    "🛠️ Dev Essentials": ["black", "flake8", "mypy", "isort", "pre-commit", "pytest"],
    "🔬 NLP Toolkit": ["transformers", "nltk", "spacy", "pandas", "numpy"],
    "🖥️ GUI Development": ["PySide6", "pyinstaller"],
    "📊 Visualization Suite": ["matplotlib", "seaborn", "plotly", "bokeh", "altair"],
    "🧪 JupyterLab Full": ["jupyterlab", "ipywidgets", "numpy", "pandas", "matplotlib"],
    "📈 Time Series (Classic)": ["statsmodels", "pmdarima", "prophet", "sktime", "tsfresh", "pandas", "numpy"],
    "📈 Time Series (Deep Learning)": ["pytorch-forecasting", "darts", "neuralforecast", "gluonts", "transformers", "torch"],
    "💰 Financial Analysis": ["yfinance", "quantlib", "zipline-reloaded", "pyfolio", "ta-lib", "pandas", "numpy"],
    "💰 Financial LLM": ["transformers", "datasets", "peft", "bitsandbytes", "accelerate", "sentencepiece", "pandas"],
}

COMMAND_HINTS = {
    "install": "pip install {packages}",
    "uninstall": "pip uninstall -y {packages}",
    "list": "pip list --format=json",
    "freeze": "pip freeze > requirements.txt",
    "import_req": "pip install -r requirements.txt",
    "create_venv": "python -m venv {name}",
    "activate_win": r"{path}\Scripts\Activate.ps1",
    "activate_unix": "source {path}/bin/activate",
    "clone": "pip freeze > req.txt && python -m venv {target} && pip install -r req.txt",
}
