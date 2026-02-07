"""
VenvStudio - Constants and Popular Package Catalog
"""

APP_NAME = "VenvStudio"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Lightweight Python Virtual Environment Manager"
APP_AUTHOR = "VenvStudio Team"

# Popular packages organized by category
PACKAGE_CATALOG = {
    "🔬 Data Science": {
        "icon": "🔬",
        "packages": [
            {"name": "numpy", "desc": "Fundamental package for numerical computing"},
            {"name": "pandas", "desc": "Data analysis and manipulation library"},
            {"name": "scipy", "desc": "Scientific computing and technical computing"},
            {"name": "matplotlib", "desc": "2D plotting and visualization"},
            {"name": "seaborn", "desc": "Statistical data visualization"},
            {"name": "plotly", "desc": "Interactive graphing library"},
            {"name": "scikit-learn", "desc": "Machine learning algorithms"},
            {"name": "statsmodels", "desc": "Statistical modeling and econometrics"},
            {"name": "sympy", "desc": "Symbolic mathematics"},
        ],
    },
    "🤖 Machine Learning & AI": {
        "icon": "🤖",
        "packages": [
            {"name": "tensorflow", "desc": "Google's ML framework"},
            {"name": "torch", "desc": "PyTorch - Facebook's ML framework"},
            {"name": "keras", "desc": "High-level neural networks API"},
            {"name": "xgboost", "desc": "Gradient boosting framework"},
            {"name": "lightgbm", "desc": "Light gradient boosting machine"},
            {"name": "transformers", "desc": "Hugging Face transformer models"},
            {"name": "opencv-python", "desc": "Computer vision library"},
            {"name": "nltk", "desc": "Natural language toolkit"},
            {"name": "spacy", "desc": "Industrial-strength NLP"},
        ],
    },
    "🌐 Web Development": {
        "icon": "🌐",
        "packages": [
            {"name": "flask", "desc": "Lightweight WSGI web framework"},
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
            {"name": "jupyter", "desc": "Jupyter notebook"},
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
            {"name": "ansible-core", "desc": "IT automation platform"},
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
            {"name": "toml", "desc": "TOML file parser"},
        ],
    },
    "🔒 Security & Networking": {
        "icon": "🔒",
        "packages": [
            {"name": "cryptography", "desc": "Cryptographic recipes and primitives"},
            {"name": "pyjwt", "desc": "JSON Web Token implementation"},
            {"name": "bcrypt", "desc": "Password hashing"},
            {"name": "scapy", "desc": "Packet manipulation library"},
            {"name": "paramiko", "desc": "SSH protocol implementation"},
            {"name": "python-nmap", "desc": "Nmap port scanner interface"},
        ],
    },
}

# Quick-install presets
PRESETS = {
    "📊 Data Science Starter": ["numpy", "pandas", "matplotlib", "scikit-learn", "jupyter"],
    "🌐 Web API (FastAPI)": ["fastapi", "uvicorn", "sqlalchemy", "pydantic", "python-dotenv"],
    "🌐 Web App (Django)": ["django", "psycopg2-binary", "django-rest-framework", "celery"],
    "🌐 Web App (Flask)": ["flask", "sqlalchemy", "flask-cors", "gunicorn"],
    "🤖 ML Starter": ["numpy", "pandas", "scikit-learn", "matplotlib", "jupyter", "xgboost"],
    "🧪 Testing Suite": ["pytest", "pytest-cov", "pytest-asyncio", "factory-boy", "faker"],
    "🛠️ Dev Essentials": ["black", "flake8", "mypy", "isort", "pre-commit", "pytest"],
    "🔬 NLP Toolkit": ["transformers", "nltk", "spacy", "pandas", "numpy"],
}
