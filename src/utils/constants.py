"""
VenvStudio - Constants and Popular Package Catalog
"""

APP_NAME = "VenvStudio"
APP_VERSION = "1.3.3"
APP_DESCRIPTION = "Lightweight Python Virtual Environment Manager"
APP_AUTHOR = "VenvStudio Team"

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
