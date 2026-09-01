"""
VenvStudio - Constants and Popular Package Catalog
"""

APP_NAME = "VenvStudio"
APP_VERSION = "1.6.69"

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
    "🕸️ Web Scraping": (
        "Crawl and extract data from websites. Scrapy for large crawls, Playwright for JavaScript-heavy pages, BeautifulSoup and lxml for parsing."
    ),
    "⚡ Async Backend": (
        "High-throughput async API stack. FastAPI with async PostgreSQL (asyncpg), SQLAlchemy, HTTPX, and Celery for background tasks."
    ),
    "🗣️ LLM App Starter": (
        "Build applications on top of large language models. OpenAI and Anthropic clients, LangChain orchestration, and ChromaDB for embeddings."
    ),
    "🧠 Deep Learning (PyTorch)": (
        "Train neural networks with PyTorch. Lightning for structured training loops, timm for image models, TensorBoard for monitoring."
    ),
    "🧠 Deep Learning (JAX)": (
        "High-performance deep learning with JAX. Flax for neural networks and Optax for optimizers — great for research and TPUs."
    ),
    "🎨 Audio Processing": (
        "Analyze and manipulate audio. Librosa for music/audio analysis, SoundFile and PyDub for I/O and editing."
    ),
    "🎬 Video Processing": (
        "Edit and process video. MoviePy for editing, ImageIO and OpenCV for frame-level work."
    ),
    "🗺️ Geospatial Analysis": (
        "Work with geographic data. GeoPandas and Shapely for geometry, Folium for maps, Rasterio for raster data."
    ),
    "🧬 Bioinformatics": (
        "Analyze biological data. Biopython for sequences, Scanpy and AnnData for single-cell analysis."
    ),
    "🎮 Game Dev (Pygame)": (
        "Build 2D games with Pygame — a mature, beginner-friendly cross-platform game library."
    ),
    "🎮 Game Dev (Arcade)": (
        "Modern 2D game development with Arcade — a cleaner, Pythonic alternative to Pygame."
    ),
    "📄 PDF & Documents": (
        "Generate and parse documents. pypdf and pdfplumber for PDFs, python-docx and openpyxl for Office files, WeasyPrint for HTML-to-PDF."
    ),
    "📚 Documentation Site": (
        "Build project documentation. MkDocs with the Material theme for Markdown docs, Sphinx for API references."
    ),
    "📊 Data Engineering": (
        "Build data pipelines. PyArrow and DuckDB for fast columnar data, Polars for DataFrames, Prefect for orchestration."
    ),
    "🔬 Data Science Full": (
        "A complete data science toolkit — NumPy, Pandas, SciPy, visualization, Scikit-learn, JupyterLab, and Polars."
    ),
    "🛠️ Modern Dev (Ruff)": (
        "Fast modern Python tooling. Ruff for linting/formatting, mypy for types, pytest for tests, pre-commit hooks."
    ),
    "🧪 Testing Full": (
        "Comprehensive testing stack. pytest with coverage, mocking, parallel runs, async support, Hypothesis, and Faker."
    ),
    "🌐 Full-Stack (Reflex)": (
        "Build full web apps in pure Python with Reflex — no JavaScript required — plus SQLModel for the database."
    ),
    "📈 Interactive Dashboard": (
        "Create data dashboards fast. Streamlit for the UI, Plotly and Altair for interactive charts."
    ),
    "🔌 Messaging (Kafka)": (
        "Event streaming with Apache Kafka. kafka-python client plus Pydantic for message schemas."
    ),
    "💬 Bot Development": (
        "Build chat bots. python-telegram-bot and discord.py for Telegram and Discord, with async HTTP support."
    ),
    "🔐 Security Toolkit": (
        "Security and cryptography tools. cryptography and bcrypt for encryption, PyJWT for tokens, nmap and scapy for networking."
    ),
    "☁️ AWS Cloud": (
        "Interact with AWS services. boto3 and botocore SDKs plus the AWS CLI."
    ),
    "🐳 DevOps Toolkit": (
        "Automate infrastructure. Docker SDK, Fabric and Paramiko for SSH, YAML config, Rich output."
    ),
    "🤖 Computer Vision (Full)": (
        "Complete computer vision stack. OpenCV, Pillow, scikit-image, Albumentations augmentation, and PyTorch with Ultralytics YOLO."
    ),
    "📝 NLP (Transformers)": (
        "Modern NLP with Hugging Face Transformers, Datasets, and Tokenizers, plus spaCy and NLTK."
    ),
    "🔭 Astronomy & Astrophysics": (
        "Python tools for astronomy and astrophysics. "
        "Astropy as the core framework, AstroQuery for catalog access, "
        "Astroplan for observation planning, Reproject for WCS reprojection, "
        "and Matplotlib for sky maps and spectra."
    ),
    "⚛️ Physics Simulation": (
        "Simulate physical systems in Python. "
        "SciPy for ODEs and linear algebra, SymPy for symbolic math, "
        "Pint for unit handling, Matplotlib for visualizations, "
        "and QuTiP for quantum mechanics simulations."
    ),
    "🧪 Computational Chemistry": (
        "Molecular modeling and computational chemistry. "
        "RDKit for cheminformatics and molecular manipulation, "
        "MDAnalysis for molecular dynamics trajectories, "
        "Mendeleev for element data, and ASE (Atomic Simulation Environment) "
        "for atomistic simulations."
    ),
    "🌍 Climate & Earth Science": (
        "Analyze climate and Earth science data. "
        "Xarray for labeled N-D arrays (NetCDF/HDF5), Cartopy for map projections, "
        "cfgrib for GRIB files, MetPy for meteorological calculations, "
        "and Pandas for time series."
    ),
    "🔬 Scientific Computing (SciPy Stack)": (
        "The full scientific Python stack. "
        "NumPy for arrays, SciPy for algorithms (optimization, FFT, signal processing), "
        "SymPy for symbolic math, Matplotlib for plotting, "
        "Pandas for data, and Numba for JIT-compiled fast loops."
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
    "shiny": (
        "✨ Shiny — Reactive Web Apps in Pure Python\n\nPosit's Shiny for Python builds interactive web apps with\nreactive outputs — no HTML/JS required.\n\n💡 Perfect for: dashboards, data apps, interactive reports\n🌐 Opens in your browser at http://localhost:8000"
    ),
    "nicegui": (
        "🎯 NiceGUI — Web UI with Python\n\nCreate buttons, charts, tables, 3D scenes and more with a\nfriendly Python API. Runs in the browser.\n\n💡 Perfect for: dashboards, control panels, quick UIs\n🌐 Opens in your browser at http://localhost:8080"
    ),
    "bokeh": (
        "🌈 Bokeh — Interactive Visualization Server\n\nServe interactive plots and data apps that update in the\nbrowser. Great for streaming and large datasets.\n\n💡 Perfect for: interactive charts, live dashboards\n🌐 Opens in your browser at http://localhost:5006"
    ),
    "chainlit": (
        "💬 Chainlit — Conversational AI UIs\n\nBuild chat interfaces for LLM apps quickly, with streaming,\nmessage history and rich elements.\n\n💡 Perfect for: chatbots, LLM demos, RAG frontends\n🌐 Opens in your browser at http://localhost:8000"
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
    "⚡ Async & Concurrency": {
        "icon": "⚡",
        "packages": [
            {"name": "anyio", "desc": "Async compatibility layer over asyncio/trio"},
            {"name": "trio", "desc": "Friendly async concurrency library"},
            {"name": "asyncpg", "desc": "Fast async PostgreSQL driver"},
            {"name": "aiomysql", "desc": "Async MySQL driver"},
            {"name": "aiofiles", "desc": "Async file operations"},
            {"name": "uvloop", "desc": "Ultra-fast asyncio event loop"},
            {"name": "gevent", "desc": "Coroutine-based concurrency"},
            {"name": "celery", "desc": "Distributed task queue"},
        ],
    },
    "🧰 CLI & Terminal": {
        "icon": "🧰",
        "packages": [
            {"name": "textual", "desc": "Modern TUI framework for the terminal"},
            {"name": "prompt-toolkit", "desc": "Interactive command-line applications"},
            {"name": "questionary", "desc": "Interactive user prompts"},
            {"name": "colorama", "desc": "Cross-platform colored terminal text"},
            {"name": "tabulate", "desc": "Pretty-print tabular data"},
            {"name": "argcomplete", "desc": "Bash tab completion for argparse"},
            {"name": "fire", "desc": "Auto-generate CLIs from any object"},
            {"name": "halo", "desc": "Terminal spinners"},
        ],
    },
    "🌐 HTTP & Scraping": {
        "icon": "🌐",
        "packages": [
            {"name": "scrapy", "desc": "Fast high-level web crawling framework"},
            {"name": "playwright", "desc": "Browser automation for testing/scraping"},
            {"name": "lxml", "desc": "Fast XML/HTML processing"},
            {"name": "parsel", "desc": "Extract data from HTML/XML with selectors"},
            {"name": "html5lib", "desc": "Standards-compliant HTML parser"},
            {"name": "urllib3", "desc": "HTTP client with connection pooling"},
            {"name": "websockets", "desc": "WebSocket client/server library"},
            {"name": "requests-html", "desc": "HTML parsing with JavaScript support"},
        ],
    },
    "🔢 Scientific Computing": {
        "icon": "🔢",
        "packages": [
            {"name": "numba", "desc": "JIT compiler for numerical Python"},
            {"name": "cython", "desc": "C-extensions for Python"},
            {"name": "networkx", "desc": "Graph and network analysis"},
            {"name": "xarray", "desc": "N-dimensional labeled arrays"},
            {"name": "h5py", "desc": "HDF5 binary data format"},
            {"name": "pint", "desc": "Physical quantities and units"},
            {"name": "uncertainties", "desc": "Calculations with uncertainties"},
            {"name": "mpmath", "desc": "Arbitrary-precision arithmetic"},
        ],
    },
    "🧠 Deep Learning": {
        "icon": "🧠",
        "packages": [
            {"name": "jax", "desc": "Composable transformations of NumPy programs"},
            {"name": "flax", "desc": "Neural network library for JAX"},
            {"name": "lightning", "desc": "PyTorch Lightning - high-level training"},
            {"name": "timm", "desc": "PyTorch image models"},
            {"name": "diffusers", "desc": "Diffusion models for generation"},
            {"name": "accelerate", "desc": "Distributed training made simple"},
            {"name": "safetensors", "desc": "Safe tensor serialization"},
            {"name": "onnxruntime", "desc": "Cross-platform ML inference"},
        ],
    },
    "🗣️ LLM & GenAI": {
        "icon": "🗣️",
        "packages": [
            {"name": "openai", "desc": "OpenAI API client"},
            {"name": "anthropic", "desc": "Anthropic Claude API client"},
            {"name": "langchain", "desc": "Framework for LLM applications"},
            {"name": "llama-index", "desc": "Data framework for LLM apps"},
            {"name": "tiktoken", "desc": "Fast BPE tokenizer for OpenAI models"},
            {"name": "chromadb", "desc": "Embeddings/vector database"},
            {"name": "faiss-cpu", "desc": "Efficient similarity search"},
            {"name": "sentencepiece", "desc": "Unsupervised text tokenizer"},
            {"name": "chainlit", "desc": "Build conversational LLM/chat UIs"},
        ],
    },
    "🎨 Audio & Media": {
        "icon": "🎨",
        "packages": [
            {"name": "librosa", "desc": "Audio and music analysis"},
            {"name": "soundfile", "desc": "Read/write sound files"},
            {"name": "pydub", "desc": "Manipulate audio with a simple API"},
            {"name": "moviepy", "desc": "Video editing with Python"},
            {"name": "imageio", "desc": "Read/write image, video, volumetric data"},
            {"name": "av", "desc": "Pythonic bindings for FFmpeg"},
            {"name": "mutagen", "desc": "Audio metadata handling"},
        ],
    },
    "🗺️ Geospatial": {
        "icon": "🗺️",
        "packages": [
            {"name": "geopandas", "desc": "Geographic pandas extensions"},
            {"name": "shapely", "desc": "Manipulation of geometric objects"},
            {"name": "folium", "desc": "Interactive leaflet maps"},
            {"name": "rasterio", "desc": "Read/write geospatial raster data"},
            {"name": "pyproj", "desc": "Cartographic projections and transforms"},
            {"name": "geopy", "desc": "Geocoding library"},
            {"name": "osmnx", "desc": "Street networks from OpenStreetMap"},
        ],
    },
    "🧬 Bioinformatics": {
        "icon": "🧬",
        "packages": [
            {"name": "biopython", "desc": "Tools for biological computation"},
            {"name": "scikit-bio", "desc": "Bioinformatics data structures/algorithms"},
            {"name": "pysam", "desc": "Read/write SAM/BAM/VCF files"},
            {"name": "anndata", "desc": "Annotated data matrices"},
            {"name": "scanpy", "desc": "Single-cell analysis in Python"},
        ],
    },
    "🎮 Game & Graphics": {
        "icon": "🎮",
        "packages": [
            {"name": "pygame", "desc": "Cross-platform game development"},
            {"name": "arcade", "desc": "Modern 2D game framework"},
            {"name": "moderngl", "desc": "Modern OpenGL bindings"},
            {"name": "pyglet", "desc": "Windowing and multimedia library"},
            {"name": "panda3d", "desc": "3D game engine"},
            {"name": "noise", "desc": "Perlin noise generation"},
        ],
    },
    "📄 Docs & Parsing": {
        "icon": "📄",
        "packages": [
            {"name": "pypdf", "desc": "Pure-Python PDF library"},
            {"name": "pdfplumber", "desc": "Extract text/tables from PDFs"},
            {"name": "markdown", "desc": "Markdown to HTML converter"},
            {"name": "mkdocs", "desc": "Project documentation with Markdown"},
            {"name": "sphinx", "desc": "Documentation generator"},
            {"name": "jinja2", "desc": "Templating engine"},
            {"name": "tabula-py", "desc": "Extract tables from PDFs"},
            {"name": "python-frontmatter", "desc": "Parse YAML frontmatter"},
        ],
    },
    "✅ Validation & Config": {
        "icon": "✅",
        "packages": [
            {"name": "pydantic-settings", "desc": "Settings management with pydantic"},
            {"name": "marshmallow", "desc": "Object serialization/validation"},
            {"name": "cerberus", "desc": "Lightweight data validation"},
            {"name": "dynaconf", "desc": "Layered configuration management"},
            {"name": "environs", "desc": "Parse environment variables"},
            {"name": "attrs", "desc": "Classes without boilerplate"},
            {"name": "cattrs", "desc": "Composable un/structuring of data"},
        ],
    },
    "📊 Data Engineering": {
        "icon": "📊",
        "packages": [
            {"name": "pyarrow", "desc": "Apache Arrow columnar format"},
            {"name": "duckdb", "desc": "In-process analytical database"},
            {"name": "sqlmodel", "desc": "SQL databases with Python types"},
            {"name": "great-expectations", "desc": "Data validation and profiling"},
            {"name": "prefect", "desc": "Modern workflow orchestration"},
            {"name": "apache-airflow", "desc": "Programmatic workflow authoring"},
            {"name": "dbt-core", "desc": "Data transformation tool"},
            {"name": "fastparquet", "desc": "Parquet format for Python"},
        ],
    },
    "🧪 Testing & Quality": {
        "icon": "🧪",
        "packages": [
            {"name": "hypothesis", "desc": "Property-based testing"},
            {"name": "pytest-mock", "desc": "Thin mock wrapper for pytest"},
            {"name": "pytest-xdist", "desc": "Distributed/parallel test runs"},
            {"name": "coverage", "desc": "Code coverage measurement"},
            {"name": "ruff", "desc": "Extremely fast Python linter"},
            {"name": "bandit", "desc": "Security linter for Python"},
            {"name": "nox", "desc": "Flexible test automation"},
            {"name": "responses", "desc": "Mock the requests library"},
        ],
    },
    "📈 Dashboards & Reporting": {
        "icon": "📈",
        "packages": [
            {"name": "panel", "desc": "High-level app and dashboard framework"},
            {"name": "shiny", "desc": "Reactive web apps in pure Python"},
            {"name": "reflex", "desc": "Build web apps in pure Python"},
            {"name": "nicegui", "desc": "Web-based UI with Python"},
            {"name": "great-tables", "desc": "Beautiful publication-quality tables"},
            {"name": "weasyprint", "desc": "HTML/CSS to PDF"},
        ],
    },
    "🔌 Messaging & Queues": {
        "icon": "🔌",
        "packages": [
            {"name": "kafka-python", "desc": "Apache Kafka client"},
            {"name": "pika", "desc": "RabbitMQ (AMQP) client"},
            {"name": "kombu", "desc": "Messaging library for Python"},
            {"name": "paho-mqtt", "desc": "MQTT client"},
            {"name": "nats-py", "desc": "NATS messaging client"},
            {"name": "dramatiq", "desc": "Distributed task processing"},
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
    "🕸️ Web Scraping": ["scrapy", "playwright", "beautifulsoup4", "lxml", "requests", "pandas"],
    "⚡ Async Backend": ["fastapi", "uvicorn", "asyncpg", "sqlalchemy", "pydantic", "httpx", "celery"],
    "🗣️ LLM App Starter": ["openai", "anthropic", "langchain", "tiktoken", "chromadb", "python-dotenv"],
    "🧠 Deep Learning (PyTorch)": ["torch", "torchvision", "lightning", "timm", "numpy", "matplotlib", "tensorboard"],
    "🧠 Deep Learning (JAX)": ["jax", "flax", "optax", "numpy", "matplotlib"],
    "🎨 Audio Processing": ["librosa", "soundfile", "pydub", "numpy", "scipy", "matplotlib"],
    "🎬 Video Processing": ["moviepy", "imageio", "opencv-python", "pillow", "numpy"],
    "🗺️ Geospatial Analysis": ["geopandas", "shapely", "folium", "rasterio", "pyproj", "pandas"],
    "🧬 Bioinformatics": ["biopython", "scanpy", "anndata", "numpy", "pandas", "matplotlib"],
    "🎮 Game Dev (Pygame)": ["pygame", "numpy", "pillow"],
    "🎮 Game Dev (Arcade)": ["arcade", "pillow", "numpy"],
    "📄 PDF & Documents": ["pypdf", "pdfplumber", "python-docx", "openpyxl", "reportlab", "weasyprint"],
    "📚 Documentation Site": ["mkdocs", "mkdocs-material", "sphinx", "jinja2"],
    "📊 Data Engineering": ["pyarrow", "duckdb", "polars", "sqlalchemy", "prefect", "pandas"],
    "🔬 Data Science Full": ["numpy", "pandas", "scipy", "matplotlib", "seaborn", "scikit-learn", "jupyterlab", "statsmodels", "polars"],
    "🛠️ Modern Dev (Ruff)": ["ruff", "mypy", "pytest", "pytest-cov", "pre-commit", "black"],
    "🧪 Testing Full": ["pytest", "pytest-cov", "pytest-mock", "pytest-xdist", "pytest-asyncio", "hypothesis", "faker", "responses"],
    "🌐 Full-Stack (Reflex)": ["reflex", "sqlmodel", "httpx", "python-dotenv"],
    "📈 Interactive Dashboard": ["streamlit", "plotly", "pandas", "numpy", "altair"],
    "🔌 Messaging (Kafka)": ["kafka-python", "pydantic", "python-dotenv"],
    "💬 Bot Development": ["python-telegram-bot", "discord.py", "aiohttp", "python-dotenv"],
    "🔐 Security Toolkit": ["cryptography", "bcrypt", "pyjwt", "python-nmap", "scapy"],
    "☁️ AWS Cloud": ["boto3", "botocore", "awscli", "python-dotenv"],
    "🐳 DevOps Toolkit": ["docker", "fabric", "paramiko", "pyyaml", "rich"],
    "🤖 Computer Vision (Full)": ["opencv-python", "pillow", "scikit-image", "albumentations", "torch", "torchvision", "ultralytics"],
    "📝 NLP (Transformers)": ["transformers", "datasets", "tokenizers", "sentencepiece", "torch", "spacy", "nltk"],
    "🔭 Astronomy & Astrophysics": ["astropy", "astroquery", "astroplan", "reproject", "matplotlib", "numpy", "scipy"],
    "⚛️ Physics Simulation": ["scipy", "sympy", "numpy", "pint", "matplotlib", "qutip"],
    "🧪 Computational Chemistry": ["rdkit", "mdanalysis", "mendeleev", "ase", "numpy", "matplotlib"],
    "🌍 Climate & Earth Science": ["xarray", "cartopy", "cfgrib", "metpy", "pandas", "numpy", "matplotlib"],
    "🔬 Scientific Computing (SciPy Stack)": ["numpy", "scipy", "sympy", "matplotlib", "pandas", "numba"],
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

# ─── Conflict Rules ───────────────────────────────────────────────────────────
# Known package incompatibilities with Python versions and env types.
# Used by the pre-flight installer check and the Conflict Manager dialog.
#
# Each entry:
#   "package_name" (lowercase, normalized): {
#       "max_python":   "X.Y"   — last known working Python minor version (None = no limit)
#       "min_python":   "X.Y"   — minimum Python version required (None = no limit)
#       "blocked_envs": [...]   — env types where this package cannot be installed
#       "note":         str     — human-readable explanation shown in the UI
#       "severity":     "error"|"warning"  — error = will fail, warning = may fail
#   }
#
# Sources: PyPI classifiers, GitHub issues, personal testing (2026-08).

CONFLICT_RULES = {
    # ── PyQt5 ─────────────────────────────────────────────────────────────────
    "pyqt5": {
        "category": 'GUI toolkits',
        "alternative": "PySide6",
        "max_python": "3.12",
        "min_python": None,
        "blocked_envs": ['pipx'],
        "note": "PyQt5 wheels are not available for Python 3.13+. Use PySide6 instead.",
        "severity": "error",
    },
    "pyqtwebengine": {
        "category": 'GUI toolkits',
        "alternative": "PySide6",
        "max_python": "3.12",
        "min_python": None,
        "blocked_envs": ['pipx'],
        "note": "PyQtWebEngine wheels are not available for Python 3.13+.",
        "severity": "error",
    },

    # ── TensorFlow ────────────────────────────────────────────────────────────
    "tensorflow": {
        "category": 'GPU / ML frameworks',
        "alternative": "torch",
        "max_python": "3.12",
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "TensorFlow does not yet provide wheels for Python 3.13+. Use PyTorch as an alternative.",
        "severity": "error",
    },
    "tensorflow-cpu": {
        "category": 'GPU / ML frameworks',
        "alternative": "torch",
        "max_python": "3.12",
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "TensorFlow-CPU does not yet provide wheels for Python 3.13+.",
        "severity": "error",
    },
    "tensorflow-gpu": {
        "category": 'GPU / ML frameworks',
        "alternative": "torch",
        "max_python": "3.12",
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "TensorFlow-GPU does not yet provide wheels for Python 3.13+.",
        "severity": "error",
    },
    "keras": {
        "category": 'GPU / ML frameworks',
        "alternative": "torch",
        "max_python": "3.12",
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "Keras (standalone) requires TensorFlow which does not support Python 3.13+ yet.",
        "severity": "warning",
    },

    # ── Orange3 ───────────────────────────────────────────────────────────────
    "orange3": {
        "category": 'GUI toolkits',
        "max_python": "3.12",
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "Orange3 requires PyQt5 which is not available for Python 3.13+.",
        "severity": "error",
    },

    # ── Torch / PyTorch ───────────────────────────────────────────────────────
    "torch": {
        "category": 'GPU / ML frameworks',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "PyTorch requires Python 3.9+. GPU support requires CUDA-compatible hardware.",
        "severity": "warning",
    },
    "torchvision": {
        "category": 'GPU / ML frameworks',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "torchvision must match the installed PyTorch version exactly.",
        "severity": "warning",
    },
    "torchaudio": {
        "category": 'GPU / ML frameworks',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "torchaudio must match the installed PyTorch version exactly.",
        "severity": "warning",
    },

    # ── Spyder ────────────────────────────────────────────────────────────────
    "spyder": {
        "category": 'GUI toolkits',
        "max_python": "3.12",
        "min_python": "3.8",
        "blocked_envs": ["pipx"],
        "note": "Spyder 6+ supports Python 3.13 but PyQt5 dependency may fail. pipx is not supported.",
        "severity": "warning",
    },

    # ── bitsandbytes ─────────────────────────────────────────────────────────
    "bitsandbytes": {
        "category": 'GPU / ML frameworks',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx', 'conda', 'pixi'],
        "note": "bitsandbytes requires CUDA on Linux/Windows. CPU-only support is limited.",
        "severity": "warning",
    },

    # ── ta-lib ────────────────────────────────────────────────────────────────
    "ta-lib": {
        "category": 'Compiled/native needing a C compiler',
        "max_python": None,
        "min_python": None,
        "blocked_envs": ['pipx'],
        "note": "ta-lib requires the TA-Lib C library to be installed on the system first (not a pure Python package).",
        "severity": "warning",
    },

    # ── Zipline ───────────────────────────────────────────────────────────────
    "zipline-reloaded": {
        "category": 'Finance / quantitative',
        "max_python": "3.11",
        "min_python": None,
        "blocked_envs": ['pipx'],
        "note": "zipline-reloaded has limited support for Python 3.12+.",
        "severity": "warning",
    },

    # ── apache-airflow ────────────────────────────────────────────────────────
    "apache-airflow": {
        "category": 'Data engineering / big data',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ["pipx", "pixi"],
        "note": "Apache Airflow requires a dedicated environment and is not suited for pipx or pixi.",
        "severity": "warning",
    },

    # ── scapy ─────────────────────────────────────────────────────────────────
    "scapy": {
        "category": 'Security / networking tools',
        "max_python": None,
        "min_python": None,
        "blocked_envs": ['pipx'],
        "note": "Scapy requires root/admin privileges for raw packet operations.",
        "severity": "warning",
    },

    # ── rdkit ─────────────────────────────────────────────────────────────────
    "rdkit": {
        "category": 'Scientific / conda-preferred',
        "max_python": None,
        "min_python": None,
        "blocked_envs": ['pipx'],
        "note": "RDKit is best installed via conda-forge (conda env). PyPI wheel may be incomplete.",
        "severity": "warning",
    },

    # ── cartopy ───────────────────────────────────────────────────────────────
    "cartopy": {
        "category": 'Scientific / conda-preferred',
        "max_python": None,
        "min_python": None,
        "blocked_envs": ['pipx'],
        "note": "Cartopy requires GEOS and PROJ C libraries. Best installed via conda-forge.",
        "severity": "warning",
    },

    # ── panda3d ───────────────────────────────────────────────────────────────
    "panda3d": {
        "category": 'Games / 3D graphics',
        "max_python": "3.12",
        "min_python": None,
        "blocked_envs": ['pipx'],
        "note": "Panda3D does not yet provide wheels for Python 3.13+.",
        "severity": "error",
    },

    # ── pywin32 ───────────────────────────────────────────────────────────────
    "pywin32": {
        "category": 'Windows-only',
        "max_python": None,
        "min_python": None,
        "blocked_envs": ['pipx'],
        "note": "pywin32 is Windows-only and will fail on Linux/macOS.",
        "severity": "error",
    },
    "winreg": {
        "category": 'Windows-only',
        "max_python": None,
        "min_python": None,
        "blocked_envs": ['pipx'],
        "note": "winreg is a Windows built-in module — not installable via pip.",
        "severity": "error",
    },

    # ── asyncpg ───────────────────────────────────────────────────────────────
    "asyncpg": {
        "category": 'Database drivers needing system libs',
        "max_python": None,
        "min_python": "3.8",
        "blocked_envs": ['pipx'],
        "note": "asyncpg requires PostgreSQL to be running and accessible.",
        "severity": "warning",
    },

    # ── qutip ─────────────────────────────────────────────────────────────────
    "qutip": {
        "category": 'Scientific / conda-preferred',
        "max_python": "3.12",
        "min_python": None,
        "blocked_envs": ['pipx'],
        "note": "QuTiP may not have binary wheels for Python 3.13+. Compilation from source may be needed.",
        "severity": "warning",
    },

    # ── pygame ────────────────────────────
    "pygame": {
        "category": 'Games / 3D graphics',
        "alternative": "pygame-ce",
        "max_python": "3.13",
        "min_python": None,
        "blocked_envs": ['pipx'],
        "note": "pygame 2.6.1 ships wheels through Python 3.13 only. On 3.14+ "
                "pip/uv falls back to building from source, which fails because "
                "pygame's legacy build script needs distutils.msvccompiler -- "
                "removed from the standard library in Python 3.12+. Use Python "
                "3.13 or earlier, or try pygame-ce (community fork).",
        "severity": "error",
    },

    # ── GUI toolkits ─────────────────────────────────────────────────────────────
    "pyqt5": {
        "category": 'GUI toolkits',
        "alternative": "PySide6",
        "max_python": "3.12",
        "min_python": "3.8",
        "blocked_envs": ['pipx'],
        "note": "PyQt5 wheels are not available for Python 3.13+. Use PySide6 instead.",
        "severity": "error",
    },
    "pyqt6": {
        "category": 'GUI toolkits',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "PyQt6 is GPL/commercial-licensed (unlike PySide6's LGPL) -- check licensing before using it in a distributed app.",
        "severity": "warning",
    },
    "pyside2": {
        "category": 'GUI toolkits',
        "alternative": "PySide6",
        "max_python": "3.10",
        "min_python": None,
        "blocked_envs": ['pipx'],
        "note": "PySide2 is Qt5-based and no longer maintained; officially superseded by PySide6. Wheels stop at Python 3.10.",
        "severity": "error",
    },
    "wxpython": {
        "category": 'GUI toolkits',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "wxPython has no prebuilt wheel for many Linux distros -- pip falls back to a from-source build that needs GTK dev headers and can take 20+ minutes.",
        "severity": "warning",
    },
    "kivy": {
        "category": 'GUI toolkits',
        "max_python": None,
        "min_python": "3.8",
        "blocked_envs": ['pipx'],
        "note": "Kivy needs SDL2/GStreamer system libraries for multimedia features; the pip wheel alone may not include them on Linux.",
        "severity": "warning",
    },
    "kivymd": {
        "category": 'GUI toolkits',
        "max_python": None,
        "min_python": "3.7",
        "blocked_envs": ['pipx'],
        "note": "KivyMD requires Kivy itself to be installed and working first -- install Kivy before this.",
        "severity": "warning",
    },

    # ── GPU / ML frameworks ─────────────────────────────────────────────────────────────
    "jax": {
        "category": 'GPU / ML frameworks',
        "max_python": None,
        "min_python": "3.12",
        "blocked_envs": ['pipx'],
        "note": "jax's CPU-only wheel is what pip installs by default; GPU support needs a separate jax[cuda12] install matching your installed CUDA version exactly.",
        "severity": "warning",
    },
    "jaxlib": {
        "category": 'GPU / ML frameworks',
        "max_python": None,
        "min_python": "3.12",
        "blocked_envs": ['pipx'],
        "note": "jaxlib version must match jax's version exactly, and the GPU build requires a matching CUDA toolkit already installed on the system.",
        "severity": "warning",
    },
    "cupy": {
        "category": 'GPU / ML frameworks',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "cupy requires a specific cupy-cudaXXX package matching your installed CUDA version -- plain 'cupy' from PyPI is usually a source distribution that needs the CUDA toolkit to build.",
        "severity": "warning",
    },
    "onnxruntime-gpu": {
        "category": 'GPU / ML frameworks',
        "max_python": None,
        "min_python": "3.11",
        "blocked_envs": ['pipx'],
        "note": "Requires a matching CUDA/cuDNN version already installed; conflicts with the plain 'onnxruntime' (CPU) package if both are installed.",
        "severity": "warning",
    },
    "catboost": {
        "category": 'GPU / ML frameworks',
        "max_python": None,
        "min_python": None,
        "blocked_envs": ['pipx'],
        "note": "Large wheel (100+ MB) with bundled GPU support; CPU-only environments still download the full package.",
        "severity": "warning",
    },
    "detectron2": {
        "category": 'GPU / ML frameworks',
        "max_python": None,
        "min_python": None,
        "blocked_envs": ['pipx', 'conda', 'pixi'],
        "note": "Not published on PyPI -- must be installed from Facebook Research's GitHub repo with a matching PyTorch + CUDA version. 'pip install detectron2' will fail with a package-not-found error.",
        "severity": "error",
    },
    "mmcv": {
        "category": 'GPU / ML frameworks',
        "max_python": None,
        "min_python": "3.7",
        "blocked_envs": ['pipx', 'conda', 'pixi'],
        "note": "mmcv's full version (with CUDA ops) must be installed via OpenMMLab's own index URL matching your PyTorch/CUDA versions -- the plain PyPI wheel is the lightweight 'mmcv-lite' equivalent.",
        "severity": "warning",
    },
    "deepspeed": {
        "category": 'GPU / ML frameworks',
        "max_python": None,
        "min_python": None,
        "blocked_envs": ['pipx', 'conda', 'pixi'],
        "note": "Requires a CUDA-capable GPU, a matching PyTorch install, and (on Windows) is largely unsupported -- Linux is strongly recommended.",
        "severity": "warning",
    },
    "flash-attn": {
        "category": 'GPU / ML frameworks',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx', 'conda', 'pixi'],
        "note": "Needs an NVIDIA GPU with compute capability 7.5+, a matching CUDA toolkit, and compiles native extensions on install -- often takes 10+ minutes and fails without a CUDA dev environment.",
        "severity": "warning",
    },
    "horovod": {
        "category": 'GPU / ML frameworks',
        "max_python": None,
        "min_python": "3.6",
        "blocked_envs": ['pipx', 'conda', 'pixi'],
        "note": "Requires MPI (OpenMPI/MPICH) already installed on the system, plus the deep learning framework(s) it's built against (TensorFlow/PyTorch) installed first.",
        "severity": "warning",
    },
    "nvidia-cudnn-cu12": {
        "category": 'GPU / ML frameworks',
        "max_python": None,
        "min_python": None,
        "blocked_envs": ['pipx', 'conda', 'pixi'],
        "note": "This is a redistributed CUDA library, not a Python package in the usual sense -- only useful alongside a matching PyTorch/TensorFlow CUDA build.",
        "severity": "warning",
    },
    "nvidia-cublas-cu12": {
        "category": 'GPU / ML frameworks',
        "max_python": None,
        "min_python": None,
        "blocked_envs": ['pipx', 'conda', 'pixi'],
        "note": "Redistributed CUDA library, same caveat as nvidia-cudnn-cu12 -- only meaningful paired with a matching GPU framework install.",
        "severity": "warning",
    },

    # ── Geospatial (conda-forge preferred) ─────────────────────────────────────────────────────────────
    "gdal": {
        "category": 'Geospatial (conda-forge preferred)',
        "max_python": None,
        "min_python": "3.8",
        "blocked_envs": ['pipx'],
        "note": "The GDAL Python bindings version must match the system GDAL C library version EXACTLY, or imports fail with a version-mismatch error. conda-forge handles this automatically; pip does not.",
        "severity": "error",
    },
    "fiona": {
        "category": 'Geospatial (conda-forge preferred)',
        "max_python": None,
        "min_python": "3.8",
        "blocked_envs": ['pipx'],
        "note": "Depends on GDAL being installed and version-matched on the system first -- same caveat as the gdal package itself.",
        "severity": "error",
    },
    "rasterio": {
        "category": 'Geospatial (conda-forge preferred)',
        "max_python": None,
        "min_python": "3.12",
        "blocked_envs": ['pipx'],
        "note": "Depends on GDAL being installed and version-matched on the system first -- same caveat as the gdal package itself.",
        "severity": "error",
    },
    "geopandas": {
        "category": 'Geospatial (conda-forge preferred)',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Depends on GDAL/GEOS/PROJ C libraries via fiona/shapely/pyproj -- conda-forge is the recommended install path to get matching versions.",
        "severity": "warning",
    },
    "pyproj": {
        "category": 'Geospatial (conda-forge preferred)',
        "max_python": None,
        "min_python": "3.11",
        "blocked_envs": ['pipx'],
        "note": "Depends on the system PROJ C library; mismatched versions between the Python binding and the system PROJ install cause silent coordinate-transform errors.",
        "severity": "warning",
    },
    "shapely": {
        "category": 'Geospatial (conda-forge preferred)',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Depends on the system GEOS C library; conda-forge bundles a matching GEOS automatically, pip wheels usually do too but can conflict with a separately-installed GEOS.",
        "severity": "warning",
    },

    # ── Scientific / conda-preferred ─────────────────────────────────────────────────────────────
    "openbabel": {
        "category": 'Scientific / conda-preferred',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "The PyPI wheel is community-maintained and less reliable than the conda-forge build; conda-forge is the officially recommended install path.",
        "severity": "warning",
    },
    "mdanalysis": {
        "category": 'Scientific / conda-preferred',
        "max_python": None,
        "min_python": "3.11",
        "blocked_envs": ['pipx'],
        "note": "Some optional analysis modules need additional C libraries (e.g. for trajectory formats) that conda-forge bundles but pip does not.",
        "severity": "warning",
    },
    "ase": {
        "category": 'Scientific / conda-preferred',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Calculator backends (VASP, Gaussian, etc.) are separate external programs ASE calls out to -- installing the Python package alone doesn't include them.",
        "severity": "warning",
    },
    "pymatgen": {
        "category": 'Scientific / conda-preferred',
        "max_python": None,
        "min_python": "3.11",
        "blocked_envs": ['pipx'],
        "note": "Some features need external codes (e.g. BoltzTraP2, Zeo++) that are not pip-installable and must be compiled/installed separately.",
        "severity": "warning",
    },

    # ── Database drivers needing system libs ─────────────────────────────────────────────────────────────
    "psycopg2": {
        "category": 'Database drivers needing system libs',
        "alternative": "psycopg2-binary",
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "Needs PostgreSQL's libpq dev headers to build from source (pg_config not found errors are common). Use psycopg2-binary for a self-contained wheel instead, especially for development.",
        "severity": "warning",
    },
    "mysqlclient": {
        "category": 'Database drivers needing system libs',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Needs MySQL/MariaDB client dev headers (mysql_config) to build; frequently fails on systems without a MySQL dev package installed.",
        "severity": "error",
    },
    "pyodbc": {
        "category": 'Database drivers needing system libs',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "Needs unixODBC (Linux/macOS) or the Microsoft ODBC Driver (Windows) installed on the system, plus a configured DSN/driver for the actual database.",
        "severity": "warning",
    },
    "cx-oracle": {
        "category": 'Database drivers needing system libs',
        "max_python": None,
        "min_python": None,
        "blocked_envs": ['pipx'],
        "note": "Requires Oracle Instant Client libraries installed and on the system library path -- pip install alone does not provide them.",
        "severity": "error",
    },
    "ibm-db": {
        "category": 'Database drivers needing system libs',
        "max_python": None,
        "min_python": None,
        "blocked_envs": ['pipx'],
        "note": "Bundles or requires the IBM Db2 client libraries; build can fail without a matching Db2 driver already present.",
        "severity": "warning",
    },

    # ── Audio/video needing system tools ─────────────────────────────────────────────────────────────
    "pyaudio": {
        "category": 'Audio/video needing system tools',
        "alternative": "sounddevice",
        "max_python": None,
        "min_python": None,
        "blocked_envs": ['pipx'],
        "note": "Needs PortAudio's dev headers to build (portaudio.h not found is a common error on Linux). Consider sounddevice as a pure-wheel alternative.",
        "severity": "warning",
    },
    "moviepy": {
        "category": 'Audio/video needing system tools',
        "max_python": None,
        "min_python": None,
        "blocked_envs": ['pipx'],
        "note": "Requires ffmpeg to be installed and on PATH at runtime -- moviepy itself is pure Python, but does nothing useful without the ffmpeg binary.",
        "severity": "warning",
    },

    # ── Windows-only ─────────────────────────────────────────────────────────────
    "winshell": {
        "category": 'Windows-only',
        "max_python": None,
        "min_python": None,
        "blocked_envs": ['pipx', 'conda', 'pixi'],
        "note": "Windows-only (uses the Windows shell API via pywin32) -- will fail to import on Linux/macOS.",
        "severity": "error",
    },
    "comtypes": {
        "category": 'Windows-only',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "Windows-only (COM automation) -- will fail to import on Linux/macOS.",
        "severity": "error",
    },
    "pywin32-ctypes": {
        "category": 'Windows-only',
        "max_python": None,
        "min_python": "3.6",
        "blocked_envs": ['pipx', 'conda', 'pixi'],
        "note": "Windows-only helper package -- will fail to import on Linux/macOS.",
        "severity": "error",
    },

    # ── Compiled/native needing a C compiler ─────────────────────────────────────────────────────────────
    "pycairo": {
        "category": 'Compiled/native needing a C compiler',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Needs Cairo's dev headers (libcairo2-dev on Debian/Ubuntu) to build from source when no prebuilt wheel matches your platform.",
        "severity": "warning",
    },
    "pygobject": {
        "category": 'Compiled/native needing a C compiler',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Needs GObject-Introspection and GTK dev headers on the system -- notoriously difficult to install on Windows outside of conda-forge or MSYS2.",
        "severity": "warning",
    },
    "pyzmq": {
        "category": 'Compiled/native needing a C compiler',
        "max_python": None,
        "min_python": "3.8",
        "blocked_envs": ['pipx'],
        "note": "Bundles its own libzmq by default, but can conflict with a separately-installed system libzmq if ZMQ_PREFIX is set.",
        "severity": "warning",
    },
    "python-levenshtein": {
        "category": 'Compiled/native needing a C compiler',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Compiles a C extension on install; needs a working C compiler if no prebuilt wheel matches your platform/Python version.",
        "severity": "warning",
    },

    # ── Big data needing a Java runtime ─────────────────────────────────────────────────────────────
    "pyspark": {
        "category": 'Data engineering / big data',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": [],
        "note": "Requires a Java Runtime Environment (JRE 8/11/17 depending on version) installed and on PATH -- pip install alone does not include Java.",
        "severity": "error",
    },

    # ── dlib-based (CMake + C++ compiler) ─────────────────────────────────────────────────────────────
    "dlib": {
        "category": 'dlib-based (CMake + C++ compiler)',
        "max_python": None,
        "min_python": None,
        "blocked_envs": ['pipx'],
        "note": "Compiles from source via CMake and a C++ compiler -- no prebuilt wheels for most platforms. Needs Visual Studio Build Tools on Windows or build-essential on Linux; can take 10+ minutes.",
        "severity": "error",
    },
    "face-recognition": {
        "category": 'dlib-based (CMake + C++ compiler)',
        "max_python": None,
        "min_python": None,
        "blocked_envs": ['pipx'],
        "note": "Depends on dlib, which compiles from source (CMake + C++ compiler required) -- see the dlib entry for the same install caveats.",
        "severity": "error",
    },

    # ── Legacy/deprecated crypto ─────────────────────────────────────────────────────────────
    "pycrypto": {
        "category": 'Legacy/deprecated crypto',
        "alternative": "pycryptodome",
        "max_python": None,
        "min_python": None,
        "blocked_envs": ['pipx'],
        "note": "Deprecated and unmaintained since 2013, with known security issues. Use pycryptodome instead -- it's a drop-in replacement with the same import name.",
        "severity": "error",
    },
    "m2crypto": {
        "category": 'Legacy/deprecated crypto',
        "max_python": None,
        "min_python": "3.6",
        "blocked_envs": ['pipx'],
        "note": "Needs OpenSSL dev headers (libssl-dev) to build from source when no matching prebuilt wheel exists.",
        "severity": "warning",
    },

    # ── Unix-only servers ─────────────────────────────────────────────────────────────
    "uwsgi": {
        "category": 'Unix-only servers',
        "alternative": "waitress",
        "max_python": None,
        "min_python": None,
        "blocked_envs": [],
        "note": "Unix-only (uses fork() and other POSIX APIs) -- will not build or run on Windows. Use waitress on Windows instead.",
        "severity": "error",
    },
    "gunicorn": {
        "category": 'Unix-only servers',
        "alternative": "waitress",
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": [],
        "note": "Unix-only (uses fork() via the os module) -- will not run on Windows. Use waitress on Windows instead.",
        "severity": "error",
    },

    # ── NLP with heavy native dependencies ─────────────────────────────────────────────────────────────
    "fasttext": {
        "category": 'NLP with heavy native dependencies',
        "max_python": None,
        "min_python": None,
        "blocked_envs": ['pipx'],
        "note": "Compiles a C++ extension on install; needs a working C++ compiler if no prebuilt wheel matches your platform.",
        "severity": "warning",
    },
    "sentencepiece": {
        "category": 'NLP with heavy native dependencies',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "Compiles a C++ extension on install when no prebuilt wheel matches; rarely an issue on common platforms but can fail on less common architectures.",
        "severity": "warning",
    },

    # ── Popular packages — baseline Python version floor (PyPI-declared,
    # not a known conflict, just avoids a live PyPI round-trip for very
    # common packages) ────────────────────────────────────────────────────
    "accelerate": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "aiohttp": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "alembic": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "anthropic": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx', 'conda', 'pixi'],
        "note": "Requires Python 3.9+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "apscheduler": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.8",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.8+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "arrow": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.8",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.8+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "attrs": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.9+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "authlib": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "azure-storage-blob": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.9+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "bcrypt": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.8",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.8+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "beautifulsoup4": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.7",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.7+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "black": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": [],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "bokeh": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "boto3": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "botocore": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "celery": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.9+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "certifi": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.7",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.7+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "cffi": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "chardet": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "charset-normalizer": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.7",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.7+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "chromadb": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx', 'conda', 'pixi'],
        "note": "Requires Python 3.9+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "click": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "coverage": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": [],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "cryptography": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.9+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "dash": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.9+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "dask": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "dataclasses-json": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.7",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.7+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "datasets": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "django": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.12",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.12+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "docutils": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.9+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "duckdb": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "dynaconf": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "environs": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "factory-boy": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.8",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.8+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "faker": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "fastapi": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "flake8": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": [],
        "note": "Requires Python 3.9+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "flask": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.9+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "flask-sqlalchemy": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.8",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.8+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "freezegun": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.8",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.8+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "google-cloud-storage": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "gradio": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "grpcio": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "httpx": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.8",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.8+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "hypercorn": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": [],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "hyperopt": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "hypothesis": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "imageio": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "invoke": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": [],
        "note": "Requires Python 3.9+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "isort": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": [],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "jinja2": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.7",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.7+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "jsonschema": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "kombu": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.9+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "langchain": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "lightgbm": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "llama-index": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx', 'conda', 'pixi'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "loguru": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.5",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.5+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "lxml": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.8",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.8+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "markupsafe": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.9+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "marshmallow": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "matplotlib": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.11",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.11+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "mkdocs": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.8",
        "blocked_envs": [],
        "note": "Requires Python 3.8+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "msgpack": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "mypy": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": [],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "networkx": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.11",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.11+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "nox": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": [],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "numpy": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.12",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.12+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "openai": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "opencv-python": {
        "category": 'Popular packages',
        "alternative": "opencv-python-headless",
        "max_python": None,
        "min_python": "3.6",
        "blocked_envs": ['pipx', 'conda', 'pixi'],
        "note": "Requires Python 3.6+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "openpyxl": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.8",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.8+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "optuna": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.9+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "pandas": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.11",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.11+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "panel": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "paramiko": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.9+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "pendulum": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.9+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "pillow": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "pip": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "playwright": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": [],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "plotly": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.8",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.8+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "polars": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "pre-commit": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": [],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "protobuf": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "psutil": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.6",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.6+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "pyarrow": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "pycparser": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "pydantic": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.9+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "pygments": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.9+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "pyjwt": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.9+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "pylint": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": [],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "pymongo": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.9+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "pytest": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "pytest-asyncio": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "pytest-cov": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.9+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "python-docx": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.9+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "python-dotenv": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "python-pptx": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.8",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.8+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "python-socketio": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.8",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.8+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "pyyaml": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.8",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.8+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "redis": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "regex": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "requests": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "rich": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.9+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "ruff": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.7",
        "blocked_envs": [],
        "note": "Requires Python 3.7+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "schedule": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.7",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.7+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "scikit-image": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.11",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.11+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "scikit-learn": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.11",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.11+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "scipy": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.12",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.12+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "scrapy": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": [],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "seaborn": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.8",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.8+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "selenium": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "sentence-transformers": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "sentry-sdk": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.6",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.6+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "setuptools": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "sh": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "shap": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.12",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.12+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "sphinx": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.12",
        "blocked_envs": [],
        "note": "Requires Python 3.12+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "sqlalchemy": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.7",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.7+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "sqlmodel": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "starlette": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "statsmodels": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.9+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "streamlit": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": [],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "structlog": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "sympy": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.9+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "tox": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": [],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "tqdm": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.8",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.8+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "transformers": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "typer": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "urllib3": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "uvicorn": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.10",
        "blocked_envs": [],
        "note": "Requires Python 3.10+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "waitress": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": [],
        "note": "Requires Python 3.9+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "watchdog": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.9+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "websockets": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.11",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.11+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "wheel": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.9+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "xgboost": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.12",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.12+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },
    "xlsxwriter": {
        "category": 'Popular packages',
        "max_python": None,
        "min_python": "3.8",
        "blocked_envs": ['pipx'],
        "note": "Requires Python 3.8+ (PyPI-declared minimum, checked 2026-08-13).",
        "severity": "warning",
    },

    # ── Computer Vision / Image Processing ──────────────────────────
    "opencv-python": {
        "category": "Computer Vision / Image Processing",
        "alternative": "opencv-python-headless",
        "max_python": None,
        "min_python": "3.6",
        "blocked_envs": ['pipx', 'conda', 'pixi'],
        "note": "The three OpenCV PyPI packages (opencv-python, opencv-python-headless, opencv-contrib-python) install into the SAME 'cv2' module namespace -- having more than one installed in the same environment causes unpredictable import behavior. Pick exactly one. This one needs system GUI libraries (libGL) present; use opencv-python-headless on servers/Docker without a display.",
        "severity": "warning",
    },
    "opencv-contrib-python": {
        "category": "Computer Vision / Image Processing",
        "alternative": "opencv-python-headless",
        "max_python": None,
        "min_python": "3.6",
        "blocked_envs": ['pipx', 'conda', 'pixi'],
        "note": "Includes extra/experimental modules beyond opencv-python, but shares the same 'cv2' import namespace -- installing this alongside plain opencv-python or opencv-python-headless in the same environment causes unpredictable behavior. Pick exactly one OpenCV variant.",
        "severity": "warning",
    },
    "opencv-python-headless": {
        "category": "Computer Vision / Image Processing",
        "max_python": None,
        "min_python": "3.6",
        "blocked_envs": ['pipx', 'conda', 'pixi'],
        "note": "Built without GUI/display dependencies (no libGL needed) -- the right choice for servers, Docker, and CI. Shares the 'cv2' import namespace with opencv-python/opencv-contrib-python; installing more than one OpenCV variant in the same environment causes unpredictable behavior.",
        "severity": "warning",
    },
    "av": {
        "category": "Computer Vision / Image Processing",
        "max_python": None,
        "min_python": "3.11",
        "blocked_envs": ['pipx'],
        "note": "PyAV wheels bundle their own FFmpeg build, but building from source (when no matching wheel exists) requires FFmpeg's dev headers and libraries already installed on the system.",
        "severity": "warning",
    },
    "pytesseract": {
        "category": "Computer Vision / Image Processing",
        "max_python": None,
        "min_python": "3.8",
        "blocked_envs": ['pipx'],
        "note": "This is only a thin Python wrapper -- it calls the Tesseract OCR binary, which is NOT installed by pip and must be installed separately (e.g. via apt/brew/the official Windows installer) and be on PATH, or pytesseract raises TesseractNotFoundError at runtime.",
        "severity": "error",
    },
    "mediapipe": {
        "category": "Computer Vision / Image Processing",
        "max_python": None,
        "min_python": None,
        "blocked_envs": ['pipx', 'conda', 'pixi'],
        "note": "Wheel availability lags behind current Python releases and is inconsistent across platforms/architectures (notably Apple Silicon and ARM Linux) -- check PyPI for your exact platform before relying on it in a new environment.",
        "severity": "warning",
    },
    "pyzbar": {
        "category": "Computer Vision / Image Processing",
        "max_python": None,
        "min_python": None,
        "blocked_envs": ['pipx'],
        "note": "Needs the system ZBar library (libzbar) installed and on the library path -- the Python package alone does not bundle it, so barcode/QR decoding fails at import or at runtime without it.",
        "severity": "error",
    },
    "kornia": {
        "category": "Computer Vision / Image Processing",
        "max_python": None,
        "min_python": "3.11",
        "blocked_envs": ['pipx'],
        "note": "Requires PyTorch to already be installed (not a bundled dependency in all cases) -- GPU acceleration additionally depends on that PyTorch build having matching CUDA support.",
        "severity": "warning",
    },
    "pillow-simd": {
        "category": "Computer Vision / Image Processing",
        "alternative": "pillow",
        "max_python": None,
        "min_python": "3.7",
        "blocked_envs": ['pipx', 'conda', 'pixi'],
        "note": "A drop-in performance replacement for Pillow that installs into the SAME 'PIL' import namespace -- having both pillow and pillow-simd installed in the same environment causes one to silently shadow the other depending on install order. Uninstall pillow first.",
        "severity": "warning",
    },
    "albumentations": {
        "category": "Computer Vision / Image Processing",
        "max_python": None,
        "min_python": "3.9",
        "blocked_envs": ['pipx'],
        "note": "Depends on OpenCV for many transforms -- inherits the multi-package 'cv2' namespace conflict risk (see the opencv-python entry) if more than one OpenCV variant ends up installed alongside it.",
        "severity": "warning",
    },
}

# Normalized aliases — map common alternate names to the canonical key above.
CONFLICT_RULES_ALIASES = {
    "torch":              "torch",
    "pytorch":            "torch",
    "tensorflow-cpu":     "tensorflow-cpu",
    "tensorflow_cpu":     "tensorflow-cpu",
    "tensorflow-gpu":     "tensorflow-gpu",
    "tensorflow_gpu":     "tensorflow-gpu",
    "tf":                 "tensorflow",
    "keras":              "keras",
    "pyqt5":              "pyqt5",
    "PyQt5":              "pyqt5",
    "pyqtwebengine":      "pyqtwebengine",
    "PyQtWebEngine":      "pyqtwebengine",
    "orange3":            "orange3",
    "Orange3":            "orange3",
    "ta_lib":             "ta-lib",
    "talib":              "ta-lib",
    "zipline":            "zipline-reloaded",
    "rdkit-pypi":         "rdkit",
    "rdkit_pypi":         "rdkit",
}
