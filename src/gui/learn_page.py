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
    # ═══════════════════════════════════════════════════════════════════════════
    # Quick Start
    # ═══════════════════════════════════════════════════════════════════════════
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
                "snippet": "# Install a package\npip install requests\n\n# Install specific version\npip install requests==2.31.0\n\n# Install from requirements.txt\npip install -r requirements.txt\n\n# List installed packages\npip list\n\n# Show package info\npip show requests\n\n# Uninstall\npip uninstall requests\n\n# Search PyPI at https://pypi.org",
                "links": [
                    ("🌐 PyPI", "https://pypi.org"),
                    ("📖 pip Docs", "https://pip.pypa.io/en/stable/"),
                ],
            },
            {
                "title": "requirements.txt & Dependency Pinning",
                "body": (
                    "A requirements.txt file lists all packages your project needs. "
                    "Share it with teammates so everyone has the same setup.\n\n"
                    "Version operators:\n"
                    "• ==    exact version\n"
                    "• >=    minimum version\n"
                    "• ~=    compatible release (same major.minor)\n"
                    "• <     less than"
                ),
                "snippet": "# Generate requirements.txt from current env\npip freeze > requirements.txt\n\n# Install from requirements.txt\npip install -r requirements.txt\n\n# Example requirements.txt:\nnumpy==1.26.0\npandas>=2.0.0\nrequests~=2.31.0\nflask\n\n# Reproducible install with hashes (supply chain safety)\npip install --require-hashes -r requirements.txt",
                "links": [
                    ("📖 pip freeze", "https://pip.pypa.io/en/stable/cli/pip_freeze/"),
                ],
            },
            {
                "title": "Python Project Layout",
                "body": (
                    "A clean folder structure saves you headaches later. "
                    "This is the de-facto standard for modern Python packages."
                ),
                "snippet": "myproject/\n├── src/\n│   └── myproject/\n│       ├── __init__.py\n│       ├── core.py\n│       └── cli.py\n├── tests/\n│   └── test_core.py\n├── pyproject.toml      # project metadata + deps\n├── README.md\n├── LICENSE\n├── .gitignore\n└── requirements.txt    # or use pyproject deps\n\n# Install in editable mode for development\npip install -e .",
                "links": [
                    ("📖 packaging.python.org", "https://packaging.python.org/en/latest/tutorials/packaging-projects/"),
                ],
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # Scientific Computing
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "scientific",
        "icon": "🔬",
        "title": "Scientific Computing",
        "desc": "NumPy, SciPy, SymPy — the foundation of Python science",
        "color": "#89dceb",
        "topics": [
            {
                "title": "NumPy — Fast N-Dimensional Arrays",
                "body": (
                    "NumPy is the bedrock of scientific Python. Vectorized operations "
                    "run at C speed — no Python loops needed."
                ),
                "snippet": "import numpy as np\n\n# Create arrays\na = np.array([1, 2, 3, 4, 5])\nb = np.linspace(0, 2*np.pi, 100)\ngrid = np.meshgrid(np.arange(5), np.arange(5))\n\n# Vectorized ops (no loops!)\ny = np.sin(b) * np.exp(-b/5)\n\n# Linear algebra\nA = np.random.randn(3, 3)\neigvals, eigvecs = np.linalg.eig(A)\nprint(f\"Eigenvalues: {eigvals}\")\n\n# Broadcasting\nrow = np.array([1, 2, 3])\ncol = np.array([[10], [20], [30]])\nmatrix = row + col  # 3x3 matrix",
                "packages": ["numpy"],
                "links": [
                    ("🌐 numpy.org", "https://numpy.org"),
                    ("📖 NumPy Docs", "https://numpy.org/doc/stable/"),
                ],
            },
            {
                "title": "SciPy — Scientific Algorithms",
                "body": (
                    "SciPy builds on NumPy with optimization, integration, interpolation, "
                    "signal processing, sparse matrices, and much more."
                ),
                "snippet": "from scipy import integrate, optimize, signal\nimport numpy as np\n\n# Numerical integration\nresult, error = integrate.quad(lambda x: np.exp(-x**2), 0, np.inf)\nprint(f\"∫ e^(-x²) dx = {result:.6f}\")  # sqrt(pi)/2\n\n# Root finding\nroot = optimize.brentq(lambda x: x**3 - 2*x - 5, 1, 3)\nprint(f\"Root of x³-2x-5: {root:.6f}\")\n\n# ODE: simple harmonic oscillator\ndef oscillator(t, y, omega=1.0):\n    return [y[1], -omega**2 * y[0]]\n\nt = np.linspace(0, 10, 100)\nsol = integrate.solve_ivp(oscillator, [0, 10], [1, 0], t_eval=t)",
                "packages": ["scipy", "numpy"],
                "links": [
                    ("🌐 scipy.org", "https://scipy.org"),
                    ("📖 SciPy Docs", "https://docs.scipy.org/doc/scipy/"),
                ],
            },
            {
                "title": "SymPy — Symbolic Mathematics",
                "body": (
                    "Do algebra and calculus symbolically, like Mathematica. "
                    "Great for physics derivations, equation solving, and code generation."
                ),
                "snippet": "import sympy as sp\n\n# Define symbols\nx, y, t = sp.symbols('x y t')\n\n# Differentiate\nf = sp.sin(x) * sp.exp(-x**2)\nprint(sp.diff(f, x))\n\n# Integrate symbolically\nprint(sp.integrate(sp.cos(x)**2, x))\n\n# Solve equations\nsolutions = sp.solve(x**2 - 2*x - 3, x)\nprint(solutions)  # [-1, 3]\n\n# Taylor series\nseries = sp.series(sp.exp(x), x, 0, 6)\nprint(series)\n\n# LaTeX output (for papers/reports)\nprint(sp.latex(sp.integrate(sp.sin(x)/x, x)))",
                "packages": ["sympy"],
                "links": [
                    ("🌐 sympy.org", "https://sympy.org"),
                ],
            },
            {
                "title": "JAX — Autodiff + GPU/TPU",
                "body": (
                    "NumPy-compatible API with automatic differentiation and "
                    "JIT compilation to GPU/TPU. A favorite for modern ML research."
                ),
                "snippet": "import jax\nimport jax.numpy as jnp\nfrom jax import grad, jit, vmap\n\n# Automatic differentiation\ndef loss(w, x, y):\n    return jnp.mean((jnp.dot(x, w) - y) ** 2)\n\ngrad_loss = grad(loss)\n\n# JIT compile\n@jit\ndef update(w, x, y, lr=0.01):\n    return w - lr * grad_loss(w, x, y)\n\n# Vectorized mapping (no loops)\nbatched_fn = vmap(lambda x: jnp.sin(x) ** 2)\nresult = batched_fn(jnp.linspace(0, jnp.pi, 100))",
                "packages": ["jax", "jaxlib"],
                "links": [
                    ("🌐 jax.readthedocs.io", "https://jax.readthedocs.io"),
                ],
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # Physics & Simulations
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "physics",
        "icon": "🪐",
        "title": "Physics & Simulations",
        "desc": "N-body, oscillators, fluid dynamics, and more",
        "color": "#b4befe",
        "topics": [
            {
                "title": "Projectile Motion with Air Drag",
                "body": (
                    "Classical mechanics with a realistic twist. The drag force "
                    "makes the trajectory non-parabolic — solve numerically with SciPy."
                ),
                "snippet": "import numpy as np\nfrom scipy.integrate import solve_ivp\n\ndef projectile(t, state, k=0.05, g=9.81):\n    x, y, vx, vy = state\n    v = np.hypot(vx, vy)\n    # Quadratic drag: F = -k * v * velocity_vector\n    ax = -k * v * vx\n    ay = -k * v * vy - g\n    return [vx, vy, ax, ay]\n\n# Initial: 50 m/s at 45°\nv0 = 50.0\nangle = np.pi / 4\nstate0 = [0, 0, v0*np.cos(angle), v0*np.sin(angle)]\n\nsol = solve_ivp(\n    projectile, [0, 15], state0,\n    dense_output=True,\n    events=lambda t, s: s[1],  # stop when y=0\n    max_step=0.01,\n)\nprint(f\"Range: {sol.y[0, -1]:.1f} m, flight time: {sol.t[-1]:.2f} s\")",
                "packages": ["scipy", "numpy"],
                "links": [
                    ("📖 SciPy ODEs", "https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html"),
                ],
            },
            {
                "title": "N-Body Gravity Simulation",
                "body": (
                    "Newton's law of gravitation applied to multiple bodies. "
                    "Naive O(N²) algorithm — use Barnes-Hut for large N (DarkFlow-style)."
                ),
                "snippet": "import numpy as np\n\ndef nbody_step(positions, velocities, masses, dt, G=6.674e-11):\n    N = len(masses)\n    accelerations = np.zeros_like(positions)\n    for i in range(N):\n        for j in range(N):\n            if i == j:\n                continue\n            r = positions[j] - positions[i]\n            dist = np.linalg.norm(r) + 1e-10  # softening\n            accelerations[i] += G * masses[j] * r / dist**3\n    velocities += accelerations * dt\n    positions += velocities * dt\n    return positions, velocities\n\n# Earth–Moon system\nmasses = np.array([5.97e24, 7.35e22])\npos = np.array([[0, 0, 0], [3.84e8, 0, 0]], dtype=float)\nvel = np.array([[0, 0, 0], [0, 1022, 0]], dtype=float)  # Moon orbital v\n\nfor step in range(1000):\n    pos, vel = nbody_step(pos, vel, masses, dt=3600)  # 1 hour steps\nprint(f\"Moon position after ~42 days: {pos[1]} m\")",
                "packages": ["numpy"],
                "links": [
                    ("📖 Barnes-Hut", "https://en.wikipedia.org/wiki/Barnes%E2%80%93Hut_simulation"),
                ],
            },
            {
                "title": "Damped Harmonic Oscillator",
                "body": (
                    "The spring-mass-damper: d²x/dt² + 2ζω₀·dx/dt + ω₀²·x = 0\n\n"
                    "ζ < 1 → underdamped (oscillates)\n"
                    "ζ = 1 → critically damped (fastest return to equilibrium)\n"
                    "ζ > 1 → overdamped (slow approach, no oscillation)"
                ),
                "snippet": "import numpy as np\nfrom scipy.integrate import odeint\n\ndef oscillator(state, t, omega0=2*np.pi, zeta=0.1):\n    x, v = state\n    return [v, -2*zeta*omega0*v - omega0**2 * x]\n\nt = np.linspace(0, 10, 1000)\n\n# Compare three damping regimes\nfor zeta, label in [(0.1, 'Underdamped'), (1.0, 'Critical'), (2.0, 'Overdamped')]:\n    sol = odeint(oscillator, [1.0, 0.0], t, args=(2*np.pi, zeta))\n    print(f\"{label:15s} — x(t=5) = {sol[500, 0]:+.4f}\")",
                "packages": ["scipy", "numpy"],
            },
            {
                "title": "Diagonal Lattice Theorem",
                "body": (
                    "Number of unique cells crossed by a line from (0,0) to (m,n) "
                    "on an integer grid equals f(m,n) = m + n − gcd(m,n).\n\n"
                    "Beautiful bridge between geometry and number theory."
                ),
                "snippet": "from math import gcd\n\ndef cells_crossed(m: int, n: int) -> int:\n    \"\"\"Diagonal Lattice Theorem: f(m, n) = m + n - gcd(m, n)\"\"\"\n    return m + n - gcd(m, n)\n\nfor m, n in [(3, 2), (4, 4), (12, 8), (100, 37)]:\n    print(f\"f({m:3d}, {n:3d}) = {cells_crossed(m, n):4d}\")\n\n# Verify empirically: count unique unit squares\ndef verify(m, n):\n    crossed = set()\n    for i in range(1000):\n        t = i / 1000\n        x, y = t * m, t * n\n        crossed.add((int(x), int(y)))\n    return len(crossed)",
                "links": [
                    ("🌐 bayramkotan.com", "https://bayramkotan.com"),
                ],
            },
            {
                "title": "Monte Carlo Integration",
                "body": (
                    "Estimate integrals by random sampling. Converges as O(1/√N) "
                    "regardless of dimension — the curse of dimensionality is lifted."
                ),
                "snippet": "import numpy as np\n\n# Estimate π by sampling points in unit square\ndef estimate_pi(n_samples=1_000_000):\n    pts = np.random.rand(n_samples, 2)\n    inside = np.sum(np.sum(pts**2, axis=1) <= 1.0)\n    return 4 * inside / n_samples\n\nprint(f\"π ≈ {estimate_pi():.5f} (true: {np.pi:.5f})\")\n\n# Integrate f(x,y) = sin(x) * cos(y) over [0, π]²\ndef mc_integral(f, bounds, n=100_000):\n    d = len(bounds)\n    samples = np.random.rand(n, d)\n    for i, (lo, hi) in enumerate(bounds):\n        samples[:, i] = samples[:, i] * (hi - lo) + lo\n    volume = np.prod([hi - lo for lo, hi in bounds])\n    return volume * np.mean([f(*s) for s in samples])\n\nresult = mc_integral(\n    lambda x, y: np.sin(x) * np.cos(y),\n    [(0, np.pi), (0, np.pi)]\n)\nprint(f\"Integral ≈ {result:.4f} (true: 0)\")",
                "packages": ["numpy"],
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # ML / Deep Learning
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "ml",
        "icon": "🤖",
        "title": "ML / Deep Learning",
        "desc": "Machine learning, neural networks, and AI tools",
        "color": "#cba6f7",
        "topics": [
            {
                "title": "scikit-learn — Classical ML",
                "body": (
                    "Classification, regression, clustering, and more — all with a consistent API. "
                    "The default choice for tabular data."
                ),
                "snippet": "from sklearn.datasets import load_iris\nfrom sklearn.model_selection import train_test_split, cross_val_score\nfrom sklearn.ensemble import RandomForestClassifier\nfrom sklearn.metrics import classification_report\n\n# Load data\nX, y = load_iris(return_X_y=True)\nX_train, X_test, y_train, y_test = train_test_split(\n    X, y, test_size=0.2, random_state=42\n)\n\n# Train\nmodel = RandomForestClassifier(n_estimators=100, random_state=42)\nmodel.fit(X_train, y_train)\n\n# Cross-validation (more robust than single split)\ncv_scores = cross_val_score(model, X, y, cv=5)\nprint(f\"CV accuracy: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}\")\n\n# Full classification report\nprint(classification_report(y_test, model.predict(X_test)))",
                "packages": ["scikit-learn", "numpy", "pandas"],
                "links": [
                    ("🌐 scikit-learn.org", "https://scikit-learn.org"),
                    ("▶ YouTube", "https://www.youtube.com/results?search_query=scikit-learn+tutorial"),
                ],
            },
            {
                "title": "PyTorch — Deep Learning",
                "body": (
                    "The most popular deep learning framework. Dynamic graphs, "
                    "eager execution, GPU acceleration out of the box."
                ),
                "snippet": "import torch\nimport torch.nn as nn\nimport torch.nn.functional as F\n\n# Simple neural network\nclass Net(nn.Module):\n    def __init__(self):\n        super().__init__()\n        self.conv1 = nn.Conv2d(1, 32, 3)\n        self.conv2 = nn.Conv2d(32, 64, 3)\n        self.fc1 = nn.Linear(9216, 128)\n        self.fc2 = nn.Linear(128, 10)\n        self.dropout = nn.Dropout(0.25)\n\n    def forward(self, x):\n        x = F.relu(self.conv1(x))\n        x = F.max_pool2d(F.relu(self.conv2(x)), 2)\n        x = torch.flatten(x, 1)\n        x = F.relu(self.fc1(self.dropout(x)))\n        return self.fc2(x)\n\nmodel = Net()\nprint(model)\nprint(f\"Parameters: {sum(p.numel() for p in model.parameters()):,}\")\n\n# GPU if available\ndevice = torch.device('cuda' if torch.cuda.is_available() else 'cpu')\nmodel = model.to(device)\nprint(f\"Running on: {device}\")",
                "packages": ["torch", "torchvision"],
                "links": [
                    ("🌐 pytorch.org", "https://pytorch.org"),
                    ("📖 Tutorials", "https://pytorch.org/tutorials/"),
                ],
            },
            {
                "title": "Hugging Face Transformers",
                "body": (
                    "State-of-the-art NLP and beyond. Use pre-trained models for "
                    "sentiment analysis, translation, summarization, image classification — "
                    "all in 3 lines of code."
                ),
                "snippet": "from transformers import pipeline\n\n# Sentiment analysis\nclf = pipeline('sentiment-analysis')\nprint(clf('VenvStudio makes Python environments fun!'))\n\n# Text generation\ngen = pipeline('text-generation', model='gpt2')\nprint(gen('The future of Python is', max_length=30)[0]['generated_text'])\n\n# Translation\ntr = pipeline('translation_en_to_fr')\nprint(tr('Machine learning is amazing'))\n\n# Zero-shot classification (no training needed!)\nclf = pipeline('zero-shot-classification')\nresult = clf(\n    'I love physics simulations in Python',\n    candidate_labels=['science', 'cooking', 'sports']\n)\nprint(result['labels'][0])",
                "packages": ["transformers", "torch"],
                "links": [
                    ("🌐 huggingface.co", "https://huggingface.co"),
                ],
            },
            {
                "title": "LangChain + LLM Apps",
                "body": (
                    "Build apps powered by large language models. Chain prompts, "
                    "retrieve documents, query databases — all declaratively."
                ),
                "snippet": "# pip install langchain langchain-openai\n\nfrom langchain_openai import ChatOpenAI\nfrom langchain.prompts import ChatPromptTemplate\nfrom langchain.schema.output_parser import StrOutputParser\n\n# Simple chain\nprompt = ChatPromptTemplate.from_template(\n    'Explain {topic} like I am {age} years old.'\n)\nmodel = ChatOpenAI(model='gpt-4', temperature=0.7)\nparser = StrOutputParser()\n\nchain = prompt | model | parser\n\nresult = chain.invoke({'topic': 'quantum entanglement', 'age': 10})\nprint(result)",
                "packages": ["langchain", "langchain-openai"],
                "links": [
                    ("🌐 langchain.com", "https://www.langchain.com"),
                ],
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # Data Science
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "datascience",
        "icon": "📊",
        "title": "Data Science",
        "desc": "Pandas, plotting, Jupyter — explore data interactively",
        "color": "#a6e3a1",
        "topics": [
            {
                "title": "Pandas — DataFrames for Python",
                "body": (
                    "The Excel of Python. Load, clean, transform, and analyze tabular "
                    "data with an expressive, chainable API."
                ),
                "snippet": "import pandas as pd\nimport numpy as np\n\n# Create a DataFrame\ndf = pd.DataFrame({\n    'name': ['Alice', 'Bob', 'Charlie', 'Diana'],\n    'age': [25, 30, 35, 28],\n    'city': ['NYC', 'LA', 'NYC', 'Chicago'],\n    'score': [85, 92, 78, 95],\n})\n\n# Filter + sort\nresult = (df[df.age >= 28]\n    .sort_values('score', ascending=False)\n    .reset_index(drop=True))\nprint(result)\n\n# Group-by\nprint(df.groupby('city')['score'].agg(['mean', 'count']))\n\n# Apply custom function\ndf['category'] = df.score.apply(lambda s: 'A' if s >= 90 else 'B')\n\n# Read CSV / write Parquet\n# df = pd.read_csv('data.csv')\n# df.to_parquet('data.parquet')  # faster, smaller",
                "packages": ["pandas", "numpy"],
                "links": [
                    ("🌐 pandas.pydata.org", "https://pandas.pydata.org"),
                ],
            },
            {
                "title": "Matplotlib + Seaborn — Visualizations",
                "body": (
                    "Matplotlib for full control, Seaborn for beautiful statistical plots. "
                    "Together they cover 99% of plotting needs."
                ),
                "snippet": "import matplotlib.pyplot as plt\nimport seaborn as sns\nimport numpy as np\n\nsns.set_theme(style='whitegrid', palette='mako')\n\n# Generate data\nnp.random.seed(42)\nx = np.linspace(0, 10, 100)\ny = np.sin(x) + np.random.randn(100) * 0.1\n\nfig, axes = plt.subplots(1, 2, figsize=(12, 4))\n\n# Line plot with confidence band\naxes[0].plot(x, y, label='noisy sine')\naxes[0].fill_between(x, y-0.2, y+0.2, alpha=0.3)\naxes[0].set_title('Line with band')\naxes[0].legend()\n\n# Seaborn distribution plot\nsns.histplot(y, kde=True, ax=axes[1])\naxes[1].set_title('Distribution')\n\nplt.tight_layout()\nplt.savefig('plot.png', dpi=150)\nplt.show()",
                "packages": ["matplotlib", "seaborn", "numpy"],
                "links": [
                    ("🌐 matplotlib.org", "https://matplotlib.org"),
                    ("🌐 seaborn.pydata.org", "https://seaborn.pydata.org"),
                ],
            },
            {
                "title": "Plotly — Interactive Charts",
                "body": (
                    "Beautiful interactive plots that work in Jupyter, web apps, and "
                    "static HTML. Pan, zoom, hover tooltips — all out of the box."
                ),
                "snippet": "import plotly.express as px\nimport plotly.graph_objects as go\n\n# Quick interactive scatter\nfig = px.scatter(\n    x=[1, 2, 3, 4, 5], y=[2, 4, 1, 5, 3],\n    size=[10, 20, 30, 40, 50], color=[1, 2, 3, 4, 5],\n    hover_data={'label': ['A', 'B', 'C', 'D', 'E']},\n    title='Interactive Scatter'\n)\nfig.show()\n\n# 3D surface plot\nimport numpy as np\nx, y = np.meshgrid(np.linspace(-5, 5, 40), np.linspace(-5, 5, 40))\nz = np.sin(np.sqrt(x**2 + y**2))\n\nfig3d = go.Figure(data=[go.Surface(x=x, y=y, z=z, colorscale='Viridis')])\nfig3d.update_layout(title='sin(√(x²+y²))')\nfig3d.write_html('surface.html')",
                "packages": ["plotly", "numpy"],
                "links": [
                    ("🌐 plotly.com/python", "https://plotly.com/python/"),
                ],
            },
            {
                "title": "Jupyter Notebooks",
                "body": (
                    "The de-facto standard for data exploration and teaching. "
                    "Mix code, markdown, equations (LaTeX), and rich outputs in one document.\n\n"
                    "JupyterLab is the modern IDE; classic Notebook is still lovely and lightweight."
                ),
                "snippet": "# Install JupyterLab\npip install jupyterlab\n\n# Start the server\njupyter lab\n\n# Useful cell-level magics:\n# %time statement     — time a single statement\n# %%timeit            — time the whole cell\n# %%writefile f.py    — save cell content to a file\n# %load f.py          — load a file into a cell\n# %matplotlib inline  — plots render in cells\n# %pip install <pkg>  — install without leaving kernel\n\n# Jupyter-only interactive widgets\nfrom ipywidgets import interact\n\n@interact(frequency=(0.1, 5.0, 0.1))\ndef plot_sine(frequency=1.0):\n    import numpy as np, matplotlib.pyplot as plt\n    x = np.linspace(0, 2*np.pi, 200)\n    plt.plot(x, np.sin(frequency * x))\n    plt.show()",
                "packages": ["jupyterlab", "ipywidgets", "matplotlib"],
                "links": [
                    ("🌐 jupyter.org", "https://jupyter.org"),
                ],
            },
            {
                "title": "Polars — Blazing Fast DataFrames",
                "body": (
                    "Rust-powered DataFrame library. Often 5–30× faster than Pandas, "
                    "with a cleaner expression-based API. Great for larger-than-RAM data."
                ),
                "snippet": "import polars as pl\n\n# Read CSV lazily (doesn't load full file)\nlf = pl.scan_csv('huge.csv')\n\n# Build a query plan — executes at .collect()\nresult = (lf\n    .filter(pl.col('amount') > 100)\n    .group_by('category')\n    .agg([\n        pl.col('amount').sum().alias('total'),\n        pl.col('amount').mean().alias('avg'),\n        pl.col('id').count().alias('n'),\n    ])\n    .sort('total', descending=True)\n    .collect()\n)\nprint(result)\n\n# DataFrame basics\ndf = pl.DataFrame({'x': [1, 2, 3], 'y': [10, 20, 30]})\ndf = df.with_columns((pl.col('x') * pl.col('y')).alias('product'))",
                "packages": ["polars"],
                "links": [
                    ("🌐 pola.rs", "https://pola.rs"),
                ],
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # Astronomy
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "astronomy",
        "icon": "🌌",
        "title": "Astronomy",
        "desc": "astropy, skyfield, stellar physics",
        "color": "#f5c2e7",
        "topics": [
            {
                "title": "astropy — Units, Coordinates, Time",
                "body": (
                    "The standard library for astronomy. Handle units (km, parsec, Jy), "
                    "convert between coordinate frames (ICRS, Galactic), and work with "
                    "astronomical time scales."
                ),
                "snippet": "from astropy import units as u\nfrom astropy.coordinates import SkyCoord, EarthLocation, AltAz\nfrom astropy.time import Time\n\n# Unit arithmetic with dimensional analysis\nv = 300 * u.km / u.s\nd = 10 * u.Mpc\ntime_to_travel = (d / v).to(u.Gyr)\nprint(f\"Travel time: {time_to_travel:.3f}\")\n\n# Convert between coordinate systems\nm31 = SkyCoord.from_name('M31')  # Andromeda galaxy\nprint(f\"ICRS:     {m31}\")\nprint(f\"Galactic: {m31.galactic}\")\n\n# When is M31 visible from your location tonight?\nist = EarthLocation(lat=41.01*u.deg, lon=28.97*u.deg, height=40*u.m)\nnow = Time.now()\nm31_altaz = m31.transform_to(AltAz(obstime=now, location=ist))\nprint(f\"M31 altitude from Istanbul now: {m31_altaz.alt:.2f}\")",
                "packages": ["astropy"],
                "links": [
                    ("🌐 astropy.org", "https://astropy.org"),
                ],
            },
            {
                "title": "Skyfield — Planetary Positions",
                "body": (
                    "Precise positions of planets, moons, stars, and artificial satellites. "
                    "Uses JPL ephemerides for sub-arcsecond accuracy."
                ),
                "snippet": "from skyfield.api import load, wgs84\n\n# Load ephemeris (downloads first time, ~20 MB)\nplanets = load('de421.bsp')\nts = load.timescale()\nt = ts.now()\n\n# Position of Mars from Earth, right now\nearth, mars = planets['earth'], planets['mars']\napparent = earth.at(t).observe(mars).apparent()\nra, dec, distance = apparent.radec()\n\nprint(f\"Mars right ascension: {ra}\")\nprint(f\"Mars declination:     {dec}\")\nprint(f\"Distance from Earth:  {distance.au:.4f} AU\")\n\n# ISS position from TLE\nfrom skyfield.api import EarthSatellite\n# (fetch fresh TLE from https://celestrak.org/NORAD/elements/stations.txt)",
                "packages": ["skyfield"],
                "links": [
                    ("🌐 rhodesmill.org/skyfield", "https://rhodesmill.org/skyfield/"),
                ],
            },
            {
                "title": "Stellar Evolution — Main Sequence",
                "body": (
                    "Simple mass-luminosity and mass-radius relations. "
                    "Real stellar evolution uses MESA or Modules for Experiments in Stellar Astrophysics."
                ),
                "snippet": "import numpy as np\n\n# Solar units\nL_sun = 3.828e26  # W\nR_sun = 6.96e8    # m\nT_sun = 5778      # K\n\n# Main sequence mass-luminosity relation\ndef luminosity(M_solar):\n    \"\"\"L ~ M^3.5 for M > 0.43 M_sun.\"\"\"\n    return M_solar ** 3.5\n\n# Main sequence mass-radius relation\ndef radius(M_solar):\n    \"\"\"Rough fit for main sequence.\"\"\"\n    return M_solar ** 0.8\n\n# Main sequence lifetime (fuel / burn rate)\ndef lifetime_gyr(M_solar):\n    return 10 * (M_solar ** -2.5)\n\nprint(f\"{'M/M_sun':>8s} {'L/L_sun':>10s} {'R/R_sun':>10s} {'life (Gyr)':>12s}\")\nfor M in [0.5, 1.0, 2.0, 5.0, 20.0]:\n    print(f\"{M:8.2f} {luminosity(M):10.2f} {radius(M):10.2f} {lifetime_gyr(M):12.4f}\")",
                "packages": ["numpy"],
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # Game Development
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "gamedev",
        "icon": "🎮",
        "title": "Game Development",
        "desc": "Pygame, Pyglet, and 2D/3D game basics",
        "color": "#fab387",
        "topics": [
            {
                "title": "Pygame — Your First Game",
                "body": (
                    "A bouncing ball in 30 lines. Pygame is the easiest way to start "
                    "making 2D games in Python — ideal for learning game loops, events, "
                    "and rendering."
                ),
                "snippet": "import pygame\n\npygame.init()\nscreen = pygame.display.set_mode((640, 480))\npygame.display.set_caption('Bouncing Ball')\nclock = pygame.time.Clock()\n\nx, y = 100, 100\nvx, vy = 4, 3\nradius = 20\n\nrunning = True\nwhile running:\n    for event in pygame.event.get():\n        if event.type == pygame.QUIT:\n            running = False\n\n    # Update physics\n    x += vx\n    y += vy\n    if x - radius < 0 or x + radius > 640:\n        vx = -vx\n    if y - radius < 0 or y + radius > 480:\n        vy = -vy\n\n    # Render\n    screen.fill((20, 20, 30))\n    pygame.draw.circle(screen, (137, 180, 250), (x, y), radius)\n    pygame.display.flip()\n    clock.tick(60)\n\npygame.quit()",
                "packages": ["pygame"],
                "links": [
                    ("🌐 pygame.org", "https://www.pygame.org"),
                ],
            },
            {
                "title": "Pyglet — Modern OpenGL Games",
                "body": (
                    "Pyglet uses native OpenGL for hardware acceleration. "
                    "Cleaner API than Pygame, better for larger games, "
                    "supports 3D rendering and shaders."
                ),
                "snippet": "import pyglet\n\nwindow = pyglet.window.Window(640, 480, 'Pyglet Demo')\nlabel = pyglet.text.Label(\n    'Hello, Pyglet!',\n    font_name='Arial', font_size=32,\n    x=window.width//2, y=window.height//2,\n    anchor_x='center', anchor_y='center',\n)\n\nangle = 0.0\n\n@window.event\ndef on_draw():\n    window.clear()\n    label.draw()\n\ndef update(dt):\n    global angle\n    angle += dt * 50\n    label.rotation = angle\n\npyglet.clock.schedule_interval(update, 1/60)\npyglet.app.run()",
                "packages": ["pyglet"],
                "links": [
                    ("🌐 pyglet.org", "https://pyglet.org"),
                ],
            },
            {
                "title": "Arcade — Friendly Game Framework",
                "body": (
                    "Built on top of Pyglet, Arcade has a simpler and more pythonic API "
                    "than Pygame. Ships with physics, sprite systems, and tilemap loaders."
                ),
                "snippet": "import arcade\n\nWIDTH, HEIGHT = 800, 600\n\nclass Game(arcade.Window):\n    def __init__(self):\n        super().__init__(WIDTH, HEIGHT, 'Arcade Demo')\n        arcade.set_background_color(arcade.color.DARK_SLATE_BLUE)\n        self.x = WIDTH // 2\n        self.y = HEIGHT // 2\n\n    def on_draw(self):\n        self.clear()\n        arcade.draw_circle_filled(self.x, self.y, 30, arcade.color.AMBER)\n\n    def on_key_press(self, key, modifiers):\n        step = 20\n        if key == arcade.key.LEFT:  self.x -= step\n        if key == arcade.key.RIGHT: self.x += step\n        if key == arcade.key.UP:    self.y += step\n        if key == arcade.key.DOWN:  self.y -= step\n\nGame().run() if hasattr(Game(), 'run') else arcade.run()",
                "packages": ["arcade"],
                "links": [
                    ("🌐 api.arcade.academy", "https://api.arcade.academy/"),
                ],
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # GUI / Desktop Apps
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "gui",
        "icon": "🖥️",
        "title": "GUI / Desktop Apps",
        "desc": "PySide6, Tkinter, Textual — build native apps",
        "color": "#74c7ec",
        "topics": [
            {
                "title": "PySide6 — Professional Qt GUIs",
                "body": (
                    "The same framework VenvStudio uses! Industrial-strength widgets, "
                    "native look and feel on Linux/macOS/Windows, comprehensive event system."
                ),
                "snippet": "from PySide6.QtWidgets import (\n    QApplication, QMainWindow, QWidget, QVBoxLayout,\n    QPushButton, QLabel, QSlider,\n)\nfrom PySide6.QtCore import Qt\nimport sys\n\nclass Demo(QMainWindow):\n    def __init__(self):\n        super().__init__()\n        self.setWindowTitle('PySide6 Demo')\n        self.resize(400, 300)\n\n        central = QWidget()\n        layout = QVBoxLayout(central)\n\n        self.label = QLabel('Slide me!')\n        self.label.setAlignment(Qt.AlignCenter)\n        self.label.setStyleSheet('font-size: 24px;')\n\n        slider = QSlider(Qt.Horizontal)\n        slider.setRange(0, 100)\n        slider.valueChanged.connect(\n            lambda v: self.label.setText(f'Value: {v}')\n        )\n\n        btn = QPushButton('Click me')\n        btn.clicked.connect(lambda: self.label.setText('Clicked!'))\n\n        layout.addWidget(self.label)\n        layout.addWidget(slider)\n        layout.addWidget(btn)\n        self.setCentralWidget(central)\n\napp = QApplication(sys.argv)\nwin = Demo()\nwin.show()\nsys.exit(app.exec())",
                "packages": ["PySide6"],
                "links": [
                    ("🌐 doc.qt.io/qtforpython", "https://doc.qt.io/qtforpython-6/"),
                ],
            },
            {
                "title": "Tkinter — Built-in & Simple",
                "body": (
                    "Ships with every Python install. Ugly by default but unbeatable for "
                    "quick utilities and single-file scripts. Pair with ttk for modern styling."
                ),
                "snippet": "import tkinter as tk\nfrom tkinter import ttk, messagebox\n\nroot = tk.Tk()\nroot.title('Tkinter Demo')\nroot.geometry('340x200')\n\n# Use ttk for modern native-looking widgets\nframe = ttk.Frame(root, padding=20)\nframe.pack(fill='both', expand=True)\n\nttk.Label(frame, text='Your name:', font=('Arial', 12)).pack(pady=4)\nname_var = tk.StringVar()\nttk.Entry(frame, textvariable=name_var, width=30).pack(pady=4)\n\ndef greet():\n    name = name_var.get() or 'stranger'\n    messagebox.showinfo('Greeting', f'Hello, {name}!')\n\nttk.Button(frame, text='Greet', command=greet).pack(pady=8)\nroot.mainloop()",
                "links": [
                    ("📖 Tk docs", "https://docs.python.org/3/library/tkinter.html"),
                ],
            },
            {
                "title": "Textual — Terminal UIs That Look Like Apps",
                "body": (
                    "Build rich TUI applications with CSS-like styling. Reactive, "
                    "async, cross-platform. Your terminal finally looks good."
                ),
                "snippet": "from textual.app import App, ComposeResult\nfrom textual.widgets import Header, Footer, Button, Static\nfrom textual.containers import Container\n\nclass DemoApp(App):\n    CSS = '''\n    Screen { align: center middle; }\n    Button { margin: 1 2; }\n    #count { text-align: center; color: $accent; text-style: bold; }\n    '''\n\n    def compose(self) -> ComposeResult:\n        yield Header()\n        yield Container(\n            Static('Counter: 0', id='count'),\n            Button('+', variant='success', id='inc'),\n            Button('-', variant='error', id='dec'),\n        )\n        yield Footer()\n\n    def on_mount(self):\n        self.count = 0\n\n    def on_button_pressed(self, event):\n        self.count += 1 if event.button.id == 'inc' else -1\n        self.query_one('#count').update(f'Counter: {self.count}')\n\nDemoApp().run()",
                "packages": ["textual"],
                "links": [
                    ("🌐 textual.textualize.io", "https://textual.textualize.io"),
                ],
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # Web Development
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "web",
        "icon": "🌐",
        "title": "Web Development",
        "desc": "FastAPI, Flask, Django — build web APIs and apps",
        "color": "#89b4fa",
        "topics": [
            {
                "title": "FastAPI — Modern Async APIs",
                "body": (
                    "Automatic OpenAPI docs, type-hint validation, async/await out of the box. "
                    "The go-to choice for new Python web APIs in 2026."
                ),
                "snippet": "from fastapi import FastAPI, HTTPException\nfrom pydantic import BaseModel\nfrom typing import Optional\n\napp = FastAPI(title='My API', version='1.0')\n\nclass Item(BaseModel):\n    name: str\n    price: float\n    is_offer: Optional[bool] = None\n\nitems_db: dict[int, Item] = {}\n\n@app.get('/')\ndef root():\n    return {'status': 'ok', 'items': len(items_db)}\n\n@app.post('/items/', status_code=201)\ndef create_item(item: Item) -> dict:\n    item_id = len(items_db) + 1\n    items_db[item_id] = item\n    return {'item_id': item_id, 'item': item}\n\n@app.get('/items/{item_id}')\ndef read_item(item_id: int) -> Item:\n    if item_id not in items_db:\n        raise HTTPException(404, 'Item not found')\n    return items_db[item_id]\n\n# Run: uvicorn main:app --reload\n# Interactive docs at http://localhost:8000/docs",
                "packages": ["fastapi", "uvicorn[standard]"],
                "links": [
                    ("🌐 fastapi.tiangolo.com", "https://fastapi.tiangolo.com"),
                ],
            },
            {
                "title": "Flask — Minimalist & Classic",
                "body": (
                    "The classic microframework. Small core, huge ecosystem. "
                    "Perfect when you want total control over your stack."
                ),
                "snippet": "from flask import Flask, jsonify, request, render_template_string\n\napp = Flask(__name__)\n\n@app.route('/')\ndef index():\n    return render_template_string('''\n        <h1>Hello, Flask!</h1>\n        <p>Try <a href=\"/api/hello/World\">/api/hello/World</a></p>\n    ''')\n\n@app.route('/api/hello/<name>')\ndef hello(name):\n    return jsonify(message=f'Hello, {name}!', tool='flask')\n\n@app.route('/api/echo', methods=['POST'])\ndef echo():\n    return jsonify(received=request.get_json())\n\nif __name__ == '__main__':\n    app.run(debug=True, port=5000)",
                "packages": ["flask"],
                "links": [
                    ("🌐 flask.palletsprojects.com", "https://flask.palletsprojects.com"),
                ],
            },
            {
                "title": "Streamlit — Data Apps in Minutes",
                "body": (
                    "Turn a Python script into a web app with no HTML or JS. "
                    "Perfect for ML demos, dashboards, and internal tools."
                ),
                "snippet": "import streamlit as st\nimport pandas as pd\nimport numpy as np\n\nst.set_page_config(page_title='My Dashboard', layout='wide')\nst.title('📊 Interactive Dashboard')\n\n# Sidebar controls\nn = st.sidebar.slider('Number of points', 10, 1000, 100)\nnoise = st.sidebar.slider('Noise', 0.0, 1.0, 0.2)\n\n# Generate data\nx = np.linspace(0, 4*np.pi, n)\ny = np.sin(x) + np.random.randn(n) * noise\ndf = pd.DataFrame({'x': x, 'y': y})\n\n# Layout\ncol1, col2 = st.columns(2)\ncol1.line_chart(df.set_index('x'))\ncol2.dataframe(df.describe())\n\nif st.button('Regenerate'):\n    st.rerun()\n\n# Run: streamlit run app.py",
                "packages": ["streamlit", "pandas", "numpy"],
                "links": [
                    ("🌐 streamlit.io", "https://streamlit.io"),
                ],
            },
            {
                "title": "httpx — Modern HTTP Client",
                "body": (
                    "The successor to requests. Same friendly API, plus async support "
                    "and HTTP/2. Use it for scripts, scrapers, and API clients."
                ),
                "snippet": "import httpx\nimport asyncio\n\n# Synchronous (requests-compatible)\nr = httpx.get('https://api.github.com/users/octocat')\nr.raise_for_status()\nprint(r.json()['bio'])\n\n# Async: fire many requests in parallel\nasync def fetch_all():\n    urls = [f'https://httpbin.org/delay/{i}' for i in range(1, 4)]\n    async with httpx.AsyncClient(timeout=10.0) as client:\n        tasks = [client.get(url) for url in urls]\n        responses = await asyncio.gather(*tasks)\n        for r in responses:\n            print(r.status_code, r.url)\n\nasyncio.run(fetch_all())",
                "packages": ["httpx"],
                "links": [
                    ("🌐 httpx.org", "https://www.python-httpx.org"),
                ],
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # Testing & Quality
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "testing",
        "icon": "🧪",
        "title": "Testing & Code Quality",
        "desc": "pytest, mypy, ruff, pre-commit — ship with confidence",
        "color": "#94e2d5",
        "topics": [
            {
                "title": "pytest — The Testing Standard",
                "body": (
                    "Simpler than unittest, with powerful fixtures and plugins. "
                    "The expected testing tool in every Python project."
                ),
                "snippet": "# test_math.py\nimport pytest\n\ndef add(a, b):\n    return a + b\n\n# Basic test\ndef test_add_positive():\n    assert add(2, 3) == 5\n\n# Parametrize — one test, many cases\n@pytest.mark.parametrize('a,b,expected', [\n    (0, 0, 0),\n    (1, 2, 3),\n    (-1, 1, 0),\n    (1.5, 2.5, 4.0),\n])\ndef test_add(a, b, expected):\n    assert add(a, b) == expected\n\n# Fixture — reusable setup\n@pytest.fixture\ndef big_list():\n    return list(range(1000))\n\ndef test_len(big_list):\n    assert len(big_list) == 1000\n\n# Run: pytest -v\n# Run with coverage: pytest --cov=mypackage",
                "packages": ["pytest", "pytest-cov"],
                "links": [
                    ("🌐 docs.pytest.org", "https://docs.pytest.org"),
                ],
            },
            {
                "title": "ruff — Lightning-Fast Linter",
                "body": (
                    "Written in Rust, 10-100× faster than flake8/pylint. Also handles "
                    "formatting (drop-in Black replacement) and auto-fixes most issues."
                ),
                "snippet": "# Install\npip install ruff\n\n# Check your code\nruff check .\n\n# Auto-fix what's fixable\nruff check --fix .\n\n# Format (Black-compatible)\nruff format .\n\n# Configure in pyproject.toml:\n[tool.ruff]\nline-length = 100\ntarget-version = 'py311'\n\n[tool.ruff.lint]\nselect = ['E', 'F', 'W', 'I', 'N', 'UP', 'B']\nignore = ['E501']  # handled by formatter\n\n[tool.ruff.format]\nquote-style = 'double'",
                "packages": ["ruff"],
                "links": [
                    ("🌐 docs.astral.sh/ruff", "https://docs.astral.sh/ruff/"),
                ],
            },
            {
                "title": "mypy — Static Type Checking",
                "body": (
                    "Catches type errors before you run. Python's type hints get teeth — "
                    "find None-dereferences, wrong argument types, and more at compile time."
                ),
                "snippet": "# example.py\nfrom typing import Optional\n\ndef greet(name: str, times: int = 1) -> str:\n    return f'Hello, {name}! ' * times\n\ndef find_user(user_id: int) -> Optional[str]:\n    users = {1: 'alice', 2: 'bob'}\n    return users.get(user_id)\n\n# This will raise a type error:\nuser = find_user(3)\nprint(user.upper())  # mypy: error — user could be None!\n\n# Run type checker:\n# mypy example.py\n# mypy --strict example.py  # more paranoid mode\n\n# In pyproject.toml:\n[tool.mypy]\nstrict = true\npython_version = '3.11'",
                "packages": ["mypy"],
                "links": [
                    ("🌐 mypy-lang.org", "https://mypy-lang.org"),
                ],
            },
            {
                "title": "pre-commit — Automatic Git Hooks",
                "body": (
                    "Run ruff, mypy, and other checks automatically before every git commit. "
                    "Never accidentally push unformatted code again."
                ),
                "snippet": "# .pre-commit-config.yaml\nrepos:\n  - repo: https://github.com/astral-sh/ruff-pre-commit\n    rev: v0.6.0\n    hooks:\n      - id: ruff\n        args: [--fix]\n      - id: ruff-format\n\n  - repo: https://github.com/pre-commit/mirrors-mypy\n    rev: v1.11.0\n    hooks:\n      - id: mypy\n\n  - repo: https://github.com/pre-commit/pre-commit-hooks\n    rev: v4.6.0\n    hooks:\n      - id: trailing-whitespace\n      - id: end-of-file-fixer\n      - id: check-yaml\n      - id: check-added-large-files\n\n# Install the hooks\npip install pre-commit\npre-commit install\npre-commit run --all-files",
                "packages": ["pre-commit"],
                "links": [
                    ("🌐 pre-commit.com", "https://pre-commit.com"),
                ],
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # Automation & DevOps
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "automation",
        "icon": "⚙️",
        "title": "Automation & DevOps",
        "desc": "Scripts, tasks, scheduling, deployment",
        "color": "#fab387",
        "topics": [
            {
                "title": "pathlib — Modern File Paths",
                "body": (
                    "Forget os.path.join! pathlib is the modern, object-oriented "
                    "way to handle files and directories — cross-platform by default."
                ),
                "snippet": "from pathlib import Path\n\nhome = Path.home()\ndocs = home / 'Documents' / 'Python'\ndocs.mkdir(parents=True, exist_ok=True)\n\n# Write a file\n(docs / 'notes.txt').write_text('Hello, pathlib!')\n\n# Read it back\ncontent = (docs / 'notes.txt').read_text()\nprint(content)\n\n# Recursive search\nfor py_file in Path('.').rglob('*.py'):\n    size_kb = py_file.stat().st_size / 1024\n    print(f'{py_file}: {size_kb:.1f} KB')\n\n# Path operations\nfile = Path('/home/user/data.csv')\nprint(file.parent)     # /home/user\nprint(file.stem)       # data\nprint(file.suffix)     # .csv\nprint(file.with_suffix('.parquet'))  # /home/user/data.parquet",
                "links": [
                    ("📖 pathlib docs", "https://docs.python.org/3/library/pathlib.html"),
                ],
            },
            {
                "title": "Click — Beautiful CLIs",
                "body": (
                    "Build command-line tools with decorators. Automatic help screens, "
                    "argument parsing, nested commands — all while staying readable."
                ),
                "snippet": "import click\n\n@click.group()\ndef cli():\n    \"\"\"My awesome CLI tool.\"\"\"\n    pass\n\n@cli.command()\n@click.argument('name')\n@click.option('--count', '-c', default=1, help='Number of greetings')\n@click.option('--shout/--no-shout', default=False)\ndef greet(name, count, shout):\n    \"\"\"Greet someone.\"\"\"\n    message = f'Hello, {name}!'\n    if shout:\n        message = message.upper()\n    for _ in range(count):\n        click.echo(message)\n\n@cli.command()\n@click.argument('file', type=click.Path(exists=True))\ndef analyze(file):\n    \"\"\"Analyze a file.\"\"\"\n    size = click.format_filename(file)\n    click.secho(f'File: {size}', fg='green')\n\nif __name__ == '__main__':\n    cli()\n\n# Usage: python mycli.py greet Alice --count 3 --shout",
                "packages": ["click"],
                "links": [
                    ("🌐 click.palletsprojects.com", "https://click.palletsprojects.com"),
                ],
            },
            {
                "title": "Rich — Beautiful Terminal Output",
                "body": (
                    "Progress bars, tables, syntax-highlighted code, markdown, tracebacks — "
                    "all gorgeous in your terminal. Your scripts deserve to look this good."
                ),
                "snippet": "from rich import print\nfrom rich.console import Console\nfrom rich.table import Table\nfrom rich.progress import track\nimport time\n\nconsole = Console()\n\n# Colored output with markup\nprint('[bold red]Warning![/] Something [italic cyan]interesting[/] happened.')\n\n# Tables\ntable = Table(title='Planets')\ntable.add_column('Name', style='cyan')\ntable.add_column('Mass (Earth=1)', style='magenta', justify='right')\ntable.add_row('Mercury', '0.055')\ntable.add_row('Earth', '1.00')\ntable.add_row('Jupiter', '317.8')\nconsole.print(table)\n\n# Progress bar\nfor _ in track(range(30), description='Computing...'):\n    time.sleep(0.05)\n\n# Better tracebacks — install once:\n# from rich.traceback import install; install(show_locals=True)",
                "packages": ["rich"],
                "links": [
                    ("🌐 rich.readthedocs.io", "https://rich.readthedocs.io"),
                ],
            },
            {
                "title": "Selenium / Playwright — Browser Automation",
                "body": (
                    "Automate web browsers for scraping, testing, or bots. "
                    "Playwright is the modern choice — faster and more reliable than Selenium."
                ),
                "snippet": "# pip install playwright && playwright install\n\nfrom playwright.sync_api import sync_playwright\n\nwith sync_playwright() as p:\n    browser = p.chromium.launch(headless=False)\n    page = browser.new_page()\n\n    page.goto('https://pypi.org')\n    page.fill('input[name=q]', 'playwright')\n    page.press('input[name=q]', 'Enter')\n\n    # Wait for first result\n    page.wait_for_selector('a.package-snippet', timeout=5000)\n\n    # Grab the first package name\n    first = page.locator('a.package-snippet').first\n    print('First result:', first.text_content().strip())\n\n    page.screenshot(path='pypi-search.png')\n    browser.close()",
                "packages": ["playwright"],
                "links": [
                    ("🌐 playwright.dev/python", "https://playwright.dev/python/"),
                ],
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # Rust ↔ Python
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "rust",
        "icon": "🦀",
        "title": "Rust ↔ Python",
        "desc": "PyO3, maturin — accelerate Python with Rust",
        "color": "#f38ba8",
        "topics": [
            {
                "title": "PyO3 — Rust Extensions for Python",
                "body": (
                    "Write native Python extensions in Rust. 10-100× speedups, "
                    "no GIL restrictions, full Python API access. Used by polars, pydantic v2, "
                    "and ruff."
                ),
                "snippet": "// src/lib.rs\nuse pyo3::prelude::*;\n\n/// Sum numbers in parallel.\n#[pyfunction]\nfn fast_sum(numbers: Vec<f64>) -> f64 {\n    numbers.iter().sum()\n}\n\n/// Compute the nth Fibonacci number.\n#[pyfunction]\nfn fib(n: u64) -> u64 {\n    if n <= 1 { return n; }\n    let (mut a, mut b) = (0u64, 1u64);\n    for _ in 2..=n {\n        let c = a + b;\n        a = b;\n        b = c;\n    }\n    b\n}\n\n#[pymodule]\nfn myrust(m: &Bound<'_, PyModule>) -> PyResult<()> {\n    m.add_function(wrap_pyfunction!(fast_sum, m)?)?;\n    m.add_function(wrap_pyfunction!(fib, m)?)?;\n    Ok(())\n}",
                "packages": [],
                "links": [
                    ("🌐 pyo3.rs", "https://pyo3.rs"),
                ],
            },
            {
                "title": "maturin — Build & Publish Rust Wheels",
                "body": (
                    "The official tool for building PyO3 extensions. Creates manylinux, "
                    "macOS, and Windows wheels with one command. Handles PyPI publishing too."
                ),
                "snippet": "# Install maturin\npip install maturin\n\n# Create a new mixed Rust/Python project\nmaturin new --bindings pyo3 myrust\ncd myrust\n\n# Build + install for local testing\nmaturin develop\n\n# Now use it from Python!\npython -c \"import myrust; print(myrust.fib(50))\"\n\n# Build release wheels\nmaturin build --release\n\n# Publish to PyPI (after testing)\nmaturin publish\n\n# Cross-compile for multiple Python versions/platforms (CI):\n# maturin build --release --strip --compatibility manylinux2014",
                "packages": ["maturin"],
                "links": [
                    ("🌐 maturin.rs", "https://www.maturin.rs"),
                ],
            },
            {
                "title": "uv — Rust-Powered Package Manager",
                "body": (
                    "From Astral (ruff, PyOxidizer team). 10-100× faster than pip. "
                    "Drop-in replacement that resolves deps in milliseconds, not minutes."
                ),
                "snippet": "# Install uv (standalone, no Python needed)\ncurl -LsSf https://astral.sh/uv/install.sh | sh    # macOS/Linux\npowershell -c \"irm https://astral.sh/uv/install.ps1 | iex\"  # Windows\n\n# Create a venv (instant!)\nuv venv myenv\n\n# Install packages (cached, parallelized)\nuv pip install numpy pandas scikit-learn\n\n# Or use uv's project management (à la Poetry/Cargo)\nuv init myproject\ncd myproject\nuv add requests\nuv run python main.py\n\n# Lockfile-based reproducible installs\nuv sync\n\n# Python version management\nuv python install 3.12\nuv python list",
                "packages": [],
                "links": [
                    ("🌐 docs.astral.sh/uv", "https://docs.astral.sh/uv/"),
                ],
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # Dev Tools
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "tools",
        "icon": "🛠️",
        "title": "Dev Tools",
        "desc": "Formatters, linters, debuggers, profilers",
        "color": "#f5c2e7",
        "topics": [
            {
                "title": "black — The Uncompromising Formatter",
                "body": (
                    "Format your code with zero configuration. The Python community "
                    "standard — what ruff-format is compatible with."
                ),
                "snippet": "# Install\npip install black\n\n# Format a file\nblack myfile.py\n\n# Format entire project\nblack .\n\n# Check without writing (useful in CI)\nblack --check .\n\n# Show what would change\nblack --diff myfile.py\n\n# In pyproject.toml:\n[tool.black]\nline-length = 100\ntarget-version = ['py311']\nskip-string-normalization = false",
                "packages": ["black"],
                "links": [
                    ("🌐 black.readthedocs.io", "https://black.readthedocs.io"),
                ],
            },
            {
                "title": "icecream — Better than print()",
                "body": (
                    "Replace `print(f'x={x}')` with `ic(x)`. Auto-detects variable names, "
                    "adds colors, shows file+line info. Your debugging workflow will thank you."
                ),
                "snippet": "from icecream import ic\n\nx = 42\ny = [1, 2, 3]\nname = 'Alice'\n\n# Single variable\nic(x)       # ic| x: 42\n\n# Multiple variables\nic(x, y, name)  # ic| x: 42, y: [1, 2, 3], name: 'Alice'\n\n# Expressions\nic(x * 2)   # ic| x * 2: 84\n\n# As a decorator\n@ic\ndef add(a, b):\n    return a + b\n\nadd(3, 4)   # ic| add(3, 4): 7\n\n# Replace all print statements globally (optional)\n# from icecream import install; install()",
                "packages": ["icecream"],
                "links": [
                    ("🌐 github.com/gruns/icecream", "https://github.com/gruns/icecream"),
                ],
            },
            {
                "title": "py-spy — Profile Running Python",
                "body": (
                    "Sampling profiler that attaches to any Python process — no code changes needed. "
                    "Works on production, finds bottlenecks in seconds."
                ),
                "snippet": "# Install\npip install py-spy\n\n# Real-time top-like view of a Python process\npy-spy top --pid 12345\n\n# Record a flamegraph (SVG)\npy-spy record -o profile.svg --pid 12345\n\n# Or launch + profile a script\npy-spy record -o profile.svg -- python myapp.py\n\n# Dump the current stack trace (great for hung processes)\npy-spy dump --pid 12345\n\n# Subprocesses too\npy-spy record -s -o profile.svg -- python parent.py",
                "packages": ["py-spy"],
                "links": [
                    ("🌐 github.com/benfred/py-spy", "https://github.com/benfred/py-spy"),
                ],
            },
            {
                "title": "Poetry & uv — Modern Dependency Management",
                "body": (
                    "Beyond pip: these tools manage lockfiles, virtualenvs, and publishing in one. "
                    "Poetry is mature; uv is the fast newcomer."
                ),
                "snippet": "# ── Poetry ──────────────────────\npip install poetry\npoetry new myproject && cd myproject\npoetry add requests 'pandas>=2.0'\npoetry add --group dev pytest ruff\npoetry install    # install all deps from poetry.lock\npoetry run pytest\npoetry shell      # activate the env\npoetry publish --build   # to PyPI\n\n# ── uv (faster, Rust-based) ─────\ncurl -LsSf https://astral.sh/uv/install.sh | sh\nuv init myproject && cd myproject\nuv add requests pandas\nuv sync           # install all deps from uv.lock\nuv run python main.py\n\n# Both read/write pyproject.toml — industry standard.",
                "packages": [],
                "links": [
                    ("🌐 python-poetry.org", "https://python-poetry.org"),
                    ("🌐 docs.astral.sh/uv", "https://docs.astral.sh/uv/"),
                ],
            },
        ],
    },
]


# ── UI Widgets ─────────────────────────────────────────────────────────────────

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
                border-radius: 10px;
            }}
            QFrame#topicCard:hover {{
                border: 1px solid {c['accent']}77;
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
        hl.setContentsMargins(18, 14, 18, 14)

        title_lbl = QLabel(self._topic["title"])
        title_lbl.setStyleSheet(
            f"color: {c['fg']}; font-size: 17px; font-weight: bold; "
            "border: none; letter-spacing: 0.3px;"
        )
        title_lbl.setWordWrap(True)
        hl.addWidget(title_lbl, 1)

        self._arrow = QLabel("›")
        self._arrow.setStyleSheet(
            f"color: {c['fg_muted']}; font-size: 26px; border: none; "
            "padding-left: 10px;"
        )
        hl.addWidget(self._arrow)
        layout.addWidget(header)

        # Body (hidden by default)
        self._body_widget = QWidget()
        self._body_widget.setVisible(False)
        bl = QVBoxLayout(self._body_widget)
        bl.setContentsMargins(18, 4, 18, 18)
        bl.setSpacing(14)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background: {c['border']}; max-height: 1px; border: none;")
        bl.addWidget(sep)

        # Description
        if self._topic.get("body"):
            body_lbl = QLabel(self._topic["body"])
            body_lbl.setWordWrap(True)
            body_lbl.setStyleSheet(
                f"color: {c.get('fg_muted', '#a6adc8')}; font-size: 15px; "
                "border: none; line-height: 1.6; padding: 2px 0;"
            )
            bl.addWidget(body_lbl)

        # Code snippet
        if self._topic.get("snippet"):
            snippet_frame = QFrame()
            snippet_frame.setStyleSheet(f"""
                QFrame {{
                    background: #11111b;
                    border: 1px solid {c['border']};
                    border-radius: 8px;
                }}
            """)
            sf_layout = QVBoxLayout(snippet_frame)
            sf_layout.setContentsMargins(0, 0, 0, 0)
            sf_layout.setSpacing(0)

            # Snippet header
            snippet_header = QFrame()
            snippet_header.setStyleSheet(
                f"background: #181825; border: none; "
                f"border-top-left-radius: 8px; border-top-right-radius: 8px; "
                f"border-bottom: 1px solid {c['border']};"
            )
            sh_layout = QHBoxLayout(snippet_header)
            sh_layout.setContentsMargins(14, 8, 8, 8)

            lang_lbl = QLabel("🐍 python")
            lang_lbl.setStyleSheet(
                f"color: {c['fg_muted']}; font-size: 13px; border: none; font-weight: bold;"
            )
            sh_layout.addWidget(lang_lbl)
            sh_layout.addStretch()

            copy_btn = QPushButton("⧉ Copy")
            copy_btn.setFixedHeight(28)
            copy_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {c['fg_muted']};
                    border: 1px solid {c['border']};
                    border-radius: 5px;
                    font-size: 13px;
                    font-weight: bold;
                    padding: 0 12px;
                }}
                QPushButton:hover {{
                    color: {c['fg']};
                    border-color: {c['accent']};
                    background: {c['accent']}22;
                }}
            """)
            copy_btn.setCursor(Qt.PointingHandCursor)
            copy_btn.clicked.connect(self._copy_snippet)
            sh_layout.addWidget(copy_btn)
            sf_layout.addWidget(snippet_header)

            # Snippet text — bigger, more readable
            snippet_edit = QTextEdit()
            snippet_edit.setPlainText(self._topic["snippet"])
            snippet_edit.setReadOnly(True)
            snippet_edit.setFont(QFont("Consolas", 14))
            snippet_edit.setStyleSheet(f"""
                QTextEdit {{
                    background: transparent;
                    color: #cdd6f4;
                    border: none;
                    padding: 12px 14px;
                    font-family: 'Consolas', 'Fira Code', 'Courier New', monospace;
                    font-size: 15px;
                    font-weight: bold;
                    line-height: 1.5;
                }}
            """)
            lines = self._topic["snippet"].count("\n") + 1
            snippet_edit.setFixedHeight(min(max(lines * 24, 100), 520))
            sf_layout.addWidget(snippet_edit)
            self._snippet_edit = snippet_edit
            bl.addWidget(snippet_frame)

        # Bottom row: links + install button
        bottom = QHBoxLayout()
        bottom.setSpacing(8)

        # Links
        for link_text, link_url in self._topic.get("links", []):
            link_btn = QPushButton(link_text)
            link_btn.setFixedHeight(32)
            link_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {c['accent']};
                    border: 1px solid {c['accent']};
                    border-radius: 6px;
                    font-size: 13px;
                    font-weight: bold;
                    padding: 0 14px;
                }}
                QPushButton:hover {{
                    background: {c['accent']}33;
                }}
            """)
            link_btn.setCursor(Qt.PointingHandCursor)
            url = link_url
            link_btn.clicked.connect(lambda _, u=url: self._open_url(u))
            bottom.addWidget(link_btn)

        bottom.addStretch()

        # Install & Try button
        pkgs = self._topic.get("packages", [])
        if pkgs:
            pkg_preview = ', '.join(pkgs[:2]) + ('...' if len(pkgs) > 2 else '')
            install_btn = QPushButton(f"⬇ Install {pkg_preview}")
            install_btn.setFixedHeight(32)
            install_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {c['accent']};
                    color: {c.get('accent_fg', '#11111b')};
                    border: none;
                    border-radius: 6px;
                    font-size: 13px;
                    padding: 0 16px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: {c['accent']}dd;
                }}
            """)
            install_btn.setCursor(Qt.PointingHandCursor)
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
        layout.setSpacing(16)

        # Category header — bigger, more prominent
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background: {c['card']};
                border-radius: 12px;
                border: 1px solid {c['border']};
                border-left: 4px solid {self._cat['color']};
            }}
        """)
        hl = QVBoxLayout(header)
        hl.setContentsMargins(20, 18, 20, 18)
        hl.setSpacing(6)

        title_row = QHBoxLayout()
        icon_lbl = QLabel(self._cat["icon"])
        icon_lbl.setStyleSheet("font-size: 36px; border: none;")
        title_row.addWidget(icon_lbl)

        title_lbl = QLabel(self._cat["title"])
        title_lbl.setStyleSheet(
            f"color: {self._cat['color']}; font-size: 28px; font-weight: bold; "
            "border: none; letter-spacing: 0.5px; padding-left: 6px;"
        )
        title_row.addWidget(title_lbl)
        title_row.addStretch()

        count_lbl = QLabel(f"{len(self._cat.get('topics', []))} topics")
        count_lbl.setStyleSheet(
            f"color: {c['fg_muted']}; font-size: 14px; border: none; "
            f"background: {c['border']}; padding: 4px 12px; border-radius: 12px;"
        )
        title_row.addWidget(count_lbl)
        hl.addLayout(title_row)

        desc_lbl = QLabel(self._cat["desc"])
        desc_lbl.setStyleSheet(
            f"color: {c['fg_muted']}; font-size: 16px; border: none; "
            "padding-left: 4px; padding-top: 2px;"
        )
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

        # ── Left nav — wider and more prominent ───────────────────────────
        nav_frame = QFrame()
        nav_frame.setFixedWidth(230)
        nav_frame.setStyleSheet(f"""
            QFrame {{
                background: {c['card']};
                border-right: 1px solid {c['border']};
            }}
        """)
        nav_layout = QVBoxLayout(nav_frame)
        nav_layout.setContentsMargins(10, 20, 10, 20)
        nav_layout.setSpacing(4)

        nav_title = QLabel("  📚 Learn")
        nav_title.setStyleSheet(
            f"color: {c['fg']}; font-size: 20px; font-weight: bold; "
            "padding: 4px 0 6px 0;"
        )
        nav_layout.addWidget(nav_title)

        nav_subtitle = QLabel("  Explore Python")
        nav_subtitle.setStyleSheet(
            f"color: {c['fg_muted']}; font-size: 12px; padding: 0 0 16px 0;"
        )
        nav_layout.addWidget(nav_subtitle)

        self._nav_btns = []
        self._stack = QStackedWidget()

        for i, cat in enumerate(LEARN_CATEGORIES):
            btn = QPushButton(f"  {cat['icon']}   {cat['title']}")
            btn.setCheckable(True)
            btn.setFixedHeight(42)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {c['fg_muted']};
                    border: none;
                    border-radius: 8px;
                    text-align: left;
                    font-size: 15px;
                    font-weight: bold;
                    padding: 0 10px;
                }}
                QPushButton:hover {{
                    background: {c['accent']}22;
                    color: {c['fg']};
                }}
                QPushButton:checked {{
                    background: {c['accent']}33;
                    color: {cat['color']};
                    border-left: 3px solid {cat['color']};
                    padding-left: 7px;
                }}
            """)
            btn.setCursor(Qt.PointingHandCursor)
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
            il.setContentsMargins(24, 24, 24, 24)
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
