"""
learn_page.py — VenvStudio Learn Panel
Sidebar Learn section: categories, snippets, links, Install & Try
"""
from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTextEdit, QApplication, QSizePolicy,
    QToolButton, QStackedWidget,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QColor, QFontDatabase

# ── Learn Content ──────────────────────────────────────────────────────────────

LEARN_CATEGORIES = [
    {
        "id": "quickstart",
        "icon": "⚡",
        "title": "Quick Start",
        "desc": "Get up and running with VenvStudio in minutes",
        "color": "#f9e2af",
        "topics": [
            {
                "title": "What is a Virtual Environment?",
                "body": (
                    "A virtual environment is an isolated Python installation. "
                    "Each project gets its own packages — no conflicts, no mess.\n\n"
                    "Think of it like a separate room for each project:\n"
                    "• Room A has numpy 1.x for a legacy project\n"
                    "• Room B has numpy 2.x for a new project\n"
                    "Both coexist peacefully."
                ),
                "snippet": "# Create a new environment\npython -m venv myproject\n\n# Activate it (Linux/macOS)\nsource myproject/bin/activate\n\n# Activate it (Windows)\nmyproject\\Scripts\\activate\n\n# Install a package\npip install numpy\n\n# Deactivate\ndeactivate",
                "links": [
                    ("📖 Python Docs", "https://docs.python.org/3/library/venv.html"),
                    ("▶ YouTube", "https://www.youtube.com/results?search_query=python+virtual+environment"),
                ],
            },
            {
                "title": "pip & PyPI Basics",
                "body": (
                    "pip is Python's package manager. PyPI (Python Package Index) "
                    "hosts 500,000+ packages you can install instantly."
                ),
                "snippet": "# Install a package\npip install requests\n\n# Install specific version\npip install requests==2.31.0\n\n# Install from requirements.txt\npip install -r requirements.txt\n\n# List installed packages\npip list\n\n# Show package info\npip show requests\n\n# Uninstall\npip uninstall requests\n\n# Search PyPI\n# https://pypi.org",
                "links": [
                    ("🌐 PyPI", "https://pypi.org"),
                    ("📖 pip Docs", "https://pip.pypa.io/en/stable/"),
                ],
            },
            {
                "title": "requirements.txt",
                "body": (
                    "A requirements.txt file lists all packages your project needs. "
                    "Share it with teammates so everyone has the same setup."
                ),
                "snippet": "# Generate requirements.txt from current env\npip freeze > requirements.txt\n\n# Install from requirements.txt\npip install -r requirements.txt\n\n# Example requirements.txt:\nnumpy==1.26.0\npandas>=2.0.0\nrequests~=2.31.0\nflask",
                "links": [
                    ("📖 pip freeze", "https://pip.pypa.io/en/stable/cli/pip_freeze/"),
                ],
            },
        ],
    },
    {
        "id": "ml",
        "icon": "🤖",
        "title": "ML / Deep Learning",
        "desc": "Machine learning, neural networks, and AI tools",
        "color": "#cba6f7",
        "topics": [
            {
                "title": "Getting Started with scikit-learn",
                "body": (
                    "scikit-learn is the go-to library for classical machine learning. "
                    "Classification, regression, clustering, and more — all with a consistent API."
                ),
                "snippet": "from sklearn.datasets import load_iris\nfrom sklearn.model_selection import train_test_split\nfrom sklearn.ensemble import RandomForestClassifier\nfrom sklearn.metrics import accuracy_score\n\n# Load data\nX, y = load_iris(return_X_y=True)\nX_train, X_test, y_train, y_test = train_test_split(\n    X, y, test_size=0.2, random_state=42\n)\n\n# Train\nmodel = RandomForestClassifier(n_estimators=100)\nmodel.fit(X_train, y_train)\n\n# Evaluate\npreds = model.predict(X_test)\nprint(f\"Accuracy: {accuracy_score(y_test, preds):.2%}\")",
                "packages": ["scikit-learn", "numpy", "pandas"],
                "links": [
                    ("🌐 scikit-learn.org", "https://scikit-learn.org"),
                    ("📖 User Guide", "https://scikit-learn.org/stable/user_guide.html"),
                    ("▶ YouTube", "https://www.youtube.com/results?search_query=scikit-learn+tutorial"),
                ],
            },
            {
                "title": "PyTorch Neural Networks",
                "body": (
                    "PyTorch is the most popular deep learning framework for research and production. "
                    "Dynamic computation graphs make debugging intuitive."
                ),
                "snippet": "import torch\nimport torch.nn as nn\n\n# Simple neural network\nclass Net(nn.Module):\n    def __init__(self):\n        super().__init__()\n        self.layers = nn.Sequential(\n            nn.Linear(784, 256),\n            nn.ReLU(),\n            nn.Dropout(0.2),\n            nn.Linear(256, 10),\n        )\n\n    def forward(self, x):\n        return self.layers(x)\n\nmodel = Net()\nprint(model)\nprint(f\"Parameters: {sum(p.numel() for p in model.parameters()):,}\")",
                "packages": ["torch", "torchvision"],
                "links": [
                    ("🌐 pytorch.org", "https://pytorch.org"),
                    ("📖 Tutorials", "https://pytorch.org/tutorials/"),
                    ("▶ YouTube", "https://www.youtube.com/results?search_query=pytorch+tutorial+beginners"),
                ],
            },
            {
                "title": "HuggingFace Transformers",
                "body": (
                    "HuggingFace Transformers gives you instant access to thousands of "
                    "pre-trained models — BERT, GPT, LLaMA, Whisper, and more."
                ),
                "snippet": "from transformers import pipeline\n\n# Sentiment analysis (no training needed!)\nclassifier = pipeline(\"sentiment-analysis\")\nresult = classifier(\"VenvStudio makes Python development a joy!\")\nprint(result)\n# [{'label': 'POSITIVE', 'score': 0.9998}]\n\n# Text generation\ngenerator = pipeline(\"text-generation\", model=\"gpt2\")\noutput = generator(\"Python is\", max_length=30)\nprint(output[0][\"generated_text\"])",
                "packages": ["transformers", "torch"],
                "links": [
                    ("🌐 huggingface.co", "https://huggingface.co"),
                    ("📖 Docs", "https://huggingface.co/docs/transformers"),
                    ("🤗 Model Hub", "https://huggingface.co/models"),
                ],
            },
        ],
    },
    {
        "id": "datascience",
        "icon": "📊",
        "title": "Data Science",
        "desc": "Data analysis, visualization, and exploration",
        "color": "#89dceb",
        "topics": [
            {
                "title": "Pandas Data Analysis",
                "body": (
                    "Pandas is the foundation of data science in Python. "
                    "DataFrames let you load, clean, transform, and analyze tabular data."
                ),
                "snippet": "import pandas as pd\n\n# Load data\ndf = pd.read_csv(\"data.csv\")\n\n# Explore\nprint(df.head())\nprint(df.describe())\nprint(df.info())\n\n# Filter\nhigh_value = df[df[\"price\"] > 100]\n\n# Group & aggregate\nsummary = df.groupby(\"category\")[\"sales\"].agg([\"sum\", \"mean\", \"count\"])\n\n# Handle missing values\ndf.fillna(0, inplace=True)\ndf.dropna(subset=[\"name\"], inplace=True)\n\n# Save\ndf.to_csv(\"output.csv\", index=False)",
                "packages": ["pandas", "numpy"],
                "links": [
                    ("🌐 pandas.pydata.org", "https://pandas.pydata.org"),
                    ("📖 10 Minutes to pandas", "https://pandas.pydata.org/docs/user_guide/10min.html"),
                ],
            },
            {
                "title": "Matplotlib & Seaborn",
                "body": (
                    "Visualize your data with Matplotlib (full control) "
                    "or Seaborn (beautiful statistical charts with less code)."
                ),
                "snippet": "import matplotlib.pyplot as plt\nimport seaborn as sns\nimport pandas as pd\nimport numpy as np\n\n# Sample data\ndf = pd.DataFrame({\n    \"x\": np.random.randn(200),\n    \"y\": np.random.randn(200),\n    \"category\": np.random.choice([\"A\", \"B\", \"C\"], 200),\n})\n\n# Seaborn scatter\nfig, axes = plt.subplots(1, 2, figsize=(12, 5))\nsns.scatterplot(data=df, x=\"x\", y=\"y\", hue=\"category\", ax=axes[0])\nsns.boxplot(data=df, x=\"category\", y=\"y\", ax=axes[1])\n\nplt.tight_layout()\nplt.savefig(\"chart.png\", dpi=150)\nplt.show()",
                "packages": ["matplotlib", "seaborn", "pandas", "numpy"],
                "links": [
                    ("🌐 matplotlib.org", "https://matplotlib.org"),
                    ("🌐 seaborn.pydata.org", "https://seaborn.pydata.org"),
                ],
            },
            {
                "title": "Jupyter Notebooks",
                "body": (
                    "Jupyter Notebooks blend code, output, and markdown in one document. "
                    "Perfect for exploration, sharing, and teaching."
                ),
                "snippet": "# Install and launch Jupyter\n# In VenvStudio: Catalog > Data > Install jupyter\n\n# Then launch from terminal:\njupyter notebook\n# or\njupyter lab\n\n# Useful magic commands:\n%matplotlib inline   # show plots inline\n%timeit sum(range(1000))  # benchmark\n%who                 # list variables\n\n# Export notebook\njupyter nbconvert --to html notebook.ipynb",
                "packages": ["jupyter", "jupyterlab"],
                "links": [
                    ("🌐 jupyter.org", "https://jupyter.org"),
                    ("▶ YouTube", "https://www.youtube.com/results?search_query=jupyter+notebook+tutorial"),
                ],
            },
        ],
    },
    {
        "id": "web",
        "icon": "🌐",
        "title": "Web Development",
        "desc": "APIs, web apps, and backend services",
        "color": "#a6e3a1",
        "topics": [
            {
                "title": "FastAPI REST API",
                "body": (
                    "FastAPI is the fastest way to build Python APIs. "
                    "Auto-generated docs, type validation, and async support out of the box."
                ),
                "snippet": "from fastapi import FastAPI\nfrom pydantic import BaseModel\n\napp = FastAPI(title=\"My API\", version=\"1.0\")\n\nclass Item(BaseModel):\n    name: str\n    price: float\n    in_stock: bool = True\n\nitems_db = {}\n\n@app.get(\"/\")\ndef root():\n    return {\"message\": \"Hello from FastAPI!\"}\n\n@app.post(\"/items/{item_id}\")\ndef create_item(item_id: int, item: Item):\n    items_db[item_id] = item\n    return {\"id\": item_id, **item.dict()}\n\n@app.get(\"/items/{item_id}\")\ndef get_item(item_id: int):\n    return items_db.get(item_id, {\"error\": \"Not found\"})\n\n# Run: uvicorn main:app --reload\n# Docs: http://localhost:8000/docs",
                "packages": ["fastapi", "uvicorn"],
                "links": [
                    ("🌐 fastapi.tiangolo.com", "https://fastapi.tiangolo.com"),
                    ("📖 Tutorial", "https://fastapi.tiangolo.com/tutorial/"),
                ],
            },
            {
                "title": "Flask Web App",
                "body": (
                    "Flask is a lightweight micro-framework. "
                    "Great for small apps, prototypes, and learning web development."
                ),
                "snippet": "from flask import Flask, render_template, jsonify, request\n\napp = Flask(__name__)\n\n# Simple route\n@app.route(\"/\")\ndef home():\n    return \"<h1>Hello Flask!</h1>\"\n\n# JSON API endpoint\n@app.route(\"/api/data\", methods=[\"GET\", \"POST\"])\ndef api_data():\n    if request.method == \"POST\":\n        data = request.get_json()\n        return jsonify({\"received\": data, \"status\": \"ok\"})\n    return jsonify({\"data\": [1, 2, 3]})\n\nif __name__ == \"__main__\":\n    app.run(debug=True, port=5000)\n# Visit: http://localhost:5000",
                "packages": ["flask"],
                "links": [
                    ("🌐 flask.palletsprojects.com", "https://flask.palletsprojects.com"),
                    ("▶ YouTube", "https://www.youtube.com/results?search_query=flask+python+tutorial"),
                ],
            },
            {
                "title": "Requests HTTP Client",
                "body": (
                    "The requests library makes HTTP calls simple and readable. "
                    "Consume any REST API in seconds."
                ),
                "snippet": "import requests\n\n# GET request\nresponse = requests.get(\"https://api.github.com/users/python\")\ndata = response.json()\nprint(data[\"name\"], data[\"public_repos\"])\n\n# POST with JSON\npayload = {\"title\": \"Test\", \"body\": \"Hello\", \"userId\": 1}\nr = requests.post(\n    \"https://jsonplaceholder.typicode.com/posts\",\n    json=payload,\n    headers={\"Content-Type\": \"application/json\"},\n)\nprint(r.status_code, r.json())\n\n# Session (reuse connection, cookies)\nwith requests.Session() as s:\n    s.headers.update({\"Authorization\": \"Bearer TOKEN\"})\n    r = s.get(\"https://api.example.com/protected\")",
                "packages": ["requests"],
                "links": [
                    ("🌐 requests.readthedocs.io", "https://requests.readthedocs.io"),
                ],
            },
        ],
    },
    {
        "id": "automation",
        "icon": "🤖",
        "title": "Automation",
        "desc": "Scripts, scraping, file handling, and task automation",
        "color": "#fab387",
        "topics": [
            {
                "title": "Web Scraping with BeautifulSoup",
                "body": (
                    "BeautifulSoup parses HTML so you can extract data from web pages. "
                    "Combine with requests for a powerful scraper."
                ),
                "snippet": "import requests\nfrom bs4 import BeautifulSoup\n\nurl = \"https://news.ycombinator.com\"\nresponse = requests.get(url)\nsoup = BeautifulSoup(response.text, \"html.parser\")\n\n# Find all story titles\nstories = soup.find_all(\"span\", class_=\"titleline\")\nfor i, story in enumerate(stories[:10], 1):\n    link = story.find(\"a\")\n    print(f\"{i}. {link.text}\")\n    print(f\"   {link.get('href', '')}\")\n    print()",
                "packages": ["beautifulsoup4", "requests", "lxml"],
                "links": [
                    ("📖 BS4 Docs", "https://www.crummy.com/software/BeautifulSoup/bs4/doc/"),
                ],
            },
            {
                "title": "File & Path Operations",
                "body": (
                    "Python's pathlib makes file operations readable and cross-platform. "
                    "No more os.path.join() headaches."
                ),
                "snippet": "from pathlib import Path\nimport shutil\n\n# Navigate paths\nhome = Path.home()\nproject = home / \"projects\" / \"myapp\"\nproject.mkdir(parents=True, exist_ok=True)\n\n# Read / write files\n(project / \"config.txt\").write_text(\"debug=true\")\ncontent = (project / \"config.txt\").read_text()\n\n# Find files\nfor py_file in project.rglob(\"*.py\"):\n    print(py_file.relative_to(project))\n\n# Copy, move, delete\nshutil.copy(\"source.txt\", \"dest.txt\")\nshutil.move(\"old/\", \"new/\")\nPath(\"temp.txt\").unlink(missing_ok=True)",
                "packages": [],
                "links": [
                    ("📖 pathlib Docs", "https://docs.python.org/3/library/pathlib.html"),
                ],
            },
            {
                "title": "Schedule Tasks",
                "body": (
                    "Run Python functions on a schedule — no cron needed. "
                    "The schedule library is dead simple."
                ),
                "snippet": "import schedule\nimport time\nfrom datetime import datetime\n\ndef backup_data():\n    print(f\"[{datetime.now():%H:%M:%S}] Running backup...\")\n    # your backup logic here\n\ndef send_report():\n    print(\"Sending daily report...\")\n\n# Schedule jobs\nschedule.every(10).minutes.do(backup_data)\nschedule.every().day.at(\"09:00\").do(send_report)\nschedule.every().monday.do(send_report)\n\nprint(\"Scheduler running... Ctrl+C to stop\")\nwhile True:\n    schedule.run_pending()\n    time.sleep(1)",
                "packages": ["schedule"],
                "links": [
                    ("🌐 schedule docs", "https://schedule.readthedocs.io"),
                ],
            },
        ],
    },
    {
        "id": "tools",
        "icon": "🔧",
        "title": "Dev Tools",
        "desc": "Testing, linting, formatting, and code quality",
        "color": "#f38ba8",
        "topics": [
            {
                "title": "pytest — Testing",
                "body": (
                    "pytest makes writing and running tests easy. "
                    "Write simple functions, get powerful output."
                ),
                "snippet": "# test_math.py\nimport pytest\n\ndef add(a, b): return a + b\ndef divide(a, b):\n    if b == 0: raise ValueError(\"Division by zero\")\n    return a / b\n\ndef test_add():\n    assert add(2, 3) == 5\n    assert add(-1, 1) == 0\n\ndef test_divide():\n    assert divide(10, 2) == 5.0\n\ndef test_divide_by_zero():\n    with pytest.raises(ValueError):\n        divide(10, 0)\n\n@pytest.mark.parametrize(\"a,b,expected\", [\n    (1, 2, 3), (0, 0, 0), (-1, 1, 0)\n])\ndef test_add_param(a, b, expected):\n    assert add(a, b) == expected\n\n# Run: pytest -v",
                "packages": ["pytest"],
                "links": [
                    ("🌐 pytest.org", "https://pytest.org"),
                    ("📖 Docs", "https://docs.pytest.org"),
                ],
            },
            {
                "title": "Black & Ruff — Formatting",
                "body": (
                    "Black formats your code automatically. "
                    "Ruff is a lightning-fast linter. Both eliminate style debates."
                ),
                "snippet": "# Install\n# pip install black ruff\n\n# Format all Python files\nblack .\n\n# Check without changing\nblack --check .\n\n# Ruff lint\nruff check .\n\n# Ruff fix automatically\nruff check --fix .\n\n# pyproject.toml config:\n# [tool.black]\n# line-length = 88\n# target-version = ['py311']\n\n# [tool.ruff]\n# line-length = 88\n# select = [\"E\", \"F\", \"I\"]  # pycodestyle, pyflakes, isort",
                "packages": ["black", "ruff"],
                "links": [
                    ("🌐 black.readthedocs.io", "https://black.readthedocs.io"),
                    ("🌐 docs.astral.sh/ruff", "https://docs.astral.sh/ruff"),
                ],
            },
        ],
    },
]


# ── Widgets ────────────────────────────────────────────────────────────────────

class TopicCard(QFrame):
    """Expandable topic card with snippet + links."""

    install_requested = Signal(list)  # list of package names

    def __init__(self, topic: dict, colors: dict, parent=None):
        super().__init__(parent)
        self._topic = topic
        self._c = colors
        self._expanded = False
        self._setup()

    def _setup(self):
        c = self._c
        self.setObjectName("topicCard")
        self.setStyleSheet(f"""
            QFrame#topicCard {{
                background: {c['card']};
                border: 1px solid {c['border']};
                border-radius: 8px;
            }}
        """)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setStyleSheet("background: transparent; border: none;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(14, 10, 14, 10)

        title_lbl = QLabel(self._topic["title"])
        title_lbl.setStyleSheet(f"color: {c['fg']}; font-size: 14px; font-weight: bold; border: none; letter-spacing: 0.3px;")
        hl.addWidget(title_lbl)
        hl.addStretch()

        self._arrow = QLabel("›")
        self._arrow.setStyleSheet(f"color: {c['fg_muted']}; font-size: 20px; border: none;")
        hl.addWidget(self._arrow)
        layout.addWidget(header)

        # Body (hidden by default)
        self._body_widget = QWidget()
        self._body_widget.setVisible(False)
        bl = QVBoxLayout(self._body_widget)
        bl.setContentsMargins(14, 4, 14, 14)
        bl.setSpacing(10)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background: {c['border']}; max-height: 1px; border: none;")
        bl.addWidget(sep)

        # Description
        if self._topic.get("body"):
            body_lbl = QLabel(self._topic["body"])
            body_lbl.setWordWrap(True)
            body_lbl.setStyleSheet("color: #a6adc8; font-size: 13px; border: none; line-height: 1.6;")
            bl.addWidget(body_lbl)

        # Code snippet
        if self._topic.get("snippet"):
            snippet_frame = QFrame()
            snippet_frame.setStyleSheet(f"""
                QFrame {{
                    background: {c.get('input_bg', '#1e1e2e')};
                    border: 1px solid {c['border']};
                    border-radius: 6px;
                }}
            """)
            sf_layout = QVBoxLayout(snippet_frame)
            sf_layout.setContentsMargins(0, 0, 0, 0)
            sf_layout.setSpacing(0)

            # Snippet header
            snippet_header = QFrame()
            snippet_header.setStyleSheet("background: transparent; border: none; border-bottom: 1px solid " + c['border'] + ";")
            sh_layout = QHBoxLayout(snippet_header)
            sh_layout.setContentsMargins(10, 6, 6, 6)

            lang_lbl = QLabel("python")
            lang_lbl.setStyleSheet(f"color: {c['fg_muted']}; font-size: 11px; border: none;")
            sh_layout.addWidget(lang_lbl)
            sh_layout.addStretch()

            copy_btn = QPushButton("⧉ Copy")
            copy_btn.setFixedHeight(22)
            copy_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {c['fg_muted']};
                    border: 1px solid {c['border']};
                    border-radius: 4px;
                    font-size: 11px;
                    padding: 0 8px;
                }}
                QPushButton:hover {{ color: {c['fg']}; border-color: {c['accent']}; }}
            """)
            copy_btn.clicked.connect(self._copy_snippet)
            sh_layout.addWidget(copy_btn)
            sf_layout.addWidget(snippet_header)

            # Snippet text
            snippet_edit = QTextEdit()
            snippet_edit.setPlainText(self._topic["snippet"])
            snippet_edit.setReadOnly(True)
            snippet_edit.setFont(QFont("Consolas", 12))
            snippet_edit.setStyleSheet(f"""
                QTextEdit {{
                    background: transparent;
                    color: {c['fg']};
                    border: none;
                    padding: 8px 10px;
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 12px;
                }}
            """)
            lines = self._topic["snippet"].count("\n") + 1
            snippet_edit.setFixedHeight(min(max(lines * 20, 80), 320))
            sf_layout.addWidget(snippet_edit)
            self._snippet_edit = snippet_edit
            bl.addWidget(snippet_frame)

        # Bottom row: links + install button
        bottom = QHBoxLayout()
        bottom.setSpacing(6)

        # Links
        for link_text, link_url in self._topic.get("links", []):
            link_btn = QPushButton(link_text)
            link_btn.setFixedHeight(26)
            link_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {c['accent']};
                    border: 1px solid {c['accent']};
                    border-radius: 4px;
                    font-size: 11px;
                    padding: 0 10px;
                }}
                QPushButton:hover {{ background: {c['accent']}22; }}
            """)
            url = link_url
            link_btn.clicked.connect(lambda _, u=url: self._open_url(u))
            bottom.addWidget(link_btn)

        bottom.addStretch()

        # Install & Try button
        pkgs = self._topic.get("packages", [])
        if pkgs:
            install_btn = QPushButton(f"⬇ Install {', '.join(pkgs[:2])}{'...' if len(pkgs) > 2 else ''}")
            install_btn.setFixedHeight(26)
            install_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {c['accent']};
                    color: {c.get('accent_fg', '#fff')};
                    border: none;
                    border-radius: 4px;
                    font-size: 11px;
                    padding: 0 12px;
                    font-weight: bold;
                }}
                QPushButton:hover {{ background: {c['accent']}dd; }}
            """)
            install_btn.clicked.connect(lambda _, p=pkgs: self.install_requested.emit(p))
            bottom.addWidget(install_btn)

        bl.addLayout(bottom)
        layout.addWidget(self._body_widget)

    def _copy_snippet(self):
        if hasattr(self, "_snippet_edit"):
            QApplication.clipboard().setText(self._snippet_edit.toPlainText())

    def _open_url(self, url: str):
        import webbrowser
        webbrowser.open(url)

    def mousePressEvent(self, event):
        self._toggle()
        super().mousePressEvent(event)

    def _toggle(self):
        self._expanded = not self._expanded
        self._body_widget.setVisible(self._expanded)
        self._arrow.setText("∨" if self._expanded else "›")


class CategoryPanel(QWidget):
    """Panel showing all topics for a category."""

    install_requested = Signal(list)

    def __init__(self, category: dict, colors: dict, parent=None):
        super().__init__(parent)
        self._cat = category
        self._c = colors
        self._setup()

    def _setup(self):
        c = self._c
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Category header
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background: {c['card']};
                border-radius: 10px;
                border: 1px solid {c['border']};
            }}
        """)
        hl = QVBoxLayout(header)
        hl.setContentsMargins(16, 14, 16, 14)
        hl.setSpacing(4)

        title_row = QHBoxLayout()
        icon_lbl = QLabel(self._cat["icon"])
        icon_lbl.setStyleSheet("font-size: 28px; border: none;")
        title_row.addWidget(icon_lbl)

        title_lbl = QLabel(self._cat["title"])
        title_lbl.setStyleSheet(
            f"color: {self._cat['color']}; font-size: 22px; font-weight: bold; border: none; letter-spacing: 0.5px;"
        )
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        hl.addLayout(title_row)

        desc_lbl = QLabel(self._cat["desc"])
        desc_lbl.setStyleSheet("color: #a6adc8; font-size: 13px; border: none;")
        hl.addWidget(desc_lbl)
        layout.addWidget(header)

        # Topics
        for topic in self._cat.get("topics", []):
            card = TopicCard(topic, c)
            card.install_requested.connect(self.install_requested)
            layout.addWidget(card)

        layout.addStretch()


class LearnPage(QWidget):
    """Main Learn page — sidebar categories + content area."""

    install_packages_requested = Signal(list)

    def __init__(self, colors_fn, parent=None):
        super().__init__(parent)
        self._colors_fn = colors_fn
        self._setup()

    def _c(self) -> dict:
        return self._colors_fn()

    def _setup(self):
        c = self._c()
        main = QHBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # ── Left nav ──────────────────────────────────────────────────────
        nav_frame = QFrame()
        nav_frame.setFixedWidth(180)
        nav_frame.setStyleSheet(f"""
            QFrame {{
                background: {c['card']};
                border-right: 1px solid {c['border']};
            }}
        """)
        nav_layout = QVBoxLayout(nav_frame)
        nav_layout.setContentsMargins(8, 16, 8, 16)
        nav_layout.setSpacing(4)

        nav_title = QLabel("  📚 Learn")
        nav_title.setStyleSheet(
            f"color: {c['fg']}; font-size: 16px; font-weight: bold; padding: 4px 0 14px 0;"
        )
        nav_layout.addWidget(nav_title)

        self._nav_btns = []
        self._stack = QStackedWidget()

        for i, cat in enumerate(LEARN_CATEGORIES):
            btn = QPushButton(f"  {cat['icon']}  {cat['title']}")
            btn.setCheckable(True)
            btn.setFixedHeight(34)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {c['fg_muted']};
                    border: none;
                    border-radius: 6px;
                    text-align: left;
                    font-size: 13px;
                    padding: 0 8px;
                }}
                QPushButton:hover {{ background: {c['accent']}22; color: {c['fg']}; }}
                QPushButton:checked {{
                    background: {c['accent']}33;
                    color: {cat['color']};
                    font-weight: bold;
                }}
            """)
            btn.clicked.connect(lambda _, idx=i: self._switch_cat(idx))
            nav_layout.addWidget(btn)
            self._nav_btns.append(btn)

            # Create category panel
            panel = QScrollArea()
            panel.setWidgetResizable(True)
            panel.setStyleSheet("QScrollArea { border: none; background: transparent; }")
            content = CategoryPanel(cat, c)
            content.install_requested.connect(self.install_packages_requested)
            inner = QWidget()
            il = QVBoxLayout(inner)
            il.setContentsMargins(16, 16, 16, 16)
            il.addWidget(content)
            panel.setWidget(inner)
            self._stack.addWidget(panel)

        nav_layout.addStretch()
        main.addWidget(nav_frame)
        main.addWidget(self._stack, 1)

        self._switch_cat(0)

    def _switch_cat(self, idx: int):
        self._stack.setCurrentIndex(idx)
        for i, btn in enumerate(self._nav_btns):
            btn.setChecked(i == idx)

    def refresh_theme(self):
        """Re-apply theme colors."""
        pass  # full rebuild would require re-init; colors come from parent theme
