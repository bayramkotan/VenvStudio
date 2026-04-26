"""
learn_page.py — VenvStudio Learn Panel
Sidebar Learn section: categories, snippets, links, Install & Try
"""
from __future__ import annotations
import re
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTextEdit, QApplication, QSizePolicy,
    QToolButton, QStackedWidget,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QColor, QFontDatabase

try:
    from src.gui.syntax_highlighter import PythonHighlighter
except Exception:
    PythonHighlighter = None  # fallback — no highlighting available


def _md_to_html(text: str, c: dict) -> str:
    """Lightweight Markdown-ish formatter for Learn body / info / table cells.

    Supported:
        `code`        → <code> (colored inline)
        **bold**      → <b>
        *italic*      → <i>
        Lines starting with "• ", "- ", "* "  → bullet (▸)
        Lines starting with "1. ", "2. " ...   → numbered (accent color)
        Blank lines → paragraph break
    """
    if not text:
        return ""

    # Escape HTML first, we add only safe tags back
    html = (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))

    # Inline code `xxx`
    code_bg = c.get("input_bg", "#1e1e2e")
    code_fg = c.get("accent", "#89b4fa")
    html = re.sub(
        r"`([^`\n]+)`",
        rf'<code style="background:{code_bg}; color:{code_fg}; '
        rf'padding:1px 5px; border-radius:3px; '
        rf'font-family:Consolas,Monaco,monospace; font-size:12px;">\1</code>',
        html,
    )
    # Bold **xxx**
    html = re.sub(r"\*\*([^\*\n]+)\*\*", r"<b>\1</b>", html)
    # Italic *xxx*
    html = re.sub(r"(?<!\*)\*([^\*\n]+)\*(?!\*)", r"<i>\1</i>", html)

    lines = html.split("\n")
    out: list = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith(("• ", "- ", "* ")):
            content = stripped[2:]
            out.append(
                f'<div style="margin-left:14px; text-indent:-10px;">▸ {content}</div>'
            )
        elif re.match(r"^\d+\. ", stripped):
            num, _, rest = stripped.partition(". ")
            out.append(
                f'<div style="margin-left:14px; text-indent:-14px;">'
                f'<b style="color:{c.get("accent","#89b4fa")};">{num}.</b> {rest}</div>'
            )
        elif stripped == "":
            out.append("<br/>")
        else:
            out.append(line)
    return "<br/>".join(out)


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
                    "A **virtual environment** is an isolated Python installation. "
                    "Each project gets its own packages — no conflicts, no mess.\n\n"
                    "Think of it like a *separate room* for each project:\n"
                    "• Room A has `numpy 1.x` for a legacy project\n"
                    "• Room B has `numpy 2.x` for a new project\n"
                    "Both coexist peacefully."
                ),
                "diagram": (
                    "  System Python (your OS)\n"
                    "  │\n"
                    "  ├── 📁 projectA/venv/   ← numpy 1.26, pandas 2.0\n"
                    "  │                         (isolated sandbox)\n"
                    "  │\n"
                    "  ├── 📁 projectB/venv/   ← numpy 2.1, polars 0.20\n"
                    "  │                         (independent sandbox)\n"
                    "  │\n"
                    "  └── 📁 projectC/venv/   ← tensorflow 2.15\n"
                    "                            (no conflicts with A or B)"
                ),
                "tip": (
                    "Use **one virtual environment per project**. Never install "
                    "packages globally with `sudo pip` — that can break system Python."
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
                    "**pip** is Python's package manager. "
                    "**PyPI** (Python Package Index) hosts **500,000+** packages you can install instantly.\n\n"
                    "Common workflow:\n"
                    "1. Find a package on PyPI (or Google it)\n"
                    "2. Run `pip install packagename`\n"
                    "3. `import packagename` in your Python code"
                ),
                "note": (
                    "pip comes **pre-installed** with Python 3.4+. "
                    "You don't need to install it separately."
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
                    "A `requirements.txt` file lists all packages your project needs. "
                    "**Share it with teammates** so everyone has the same setup.\n\n"
                    "**Version operators** let you control update flexibility:"
                ),
                "table": {
                    "headers": ["Operator", "Example", "Meaning"],
                    "rows": [
                        ["`==`",   "`numpy==1.26.0`",  "Exact version only — safest for prod"],
                        ["`>=`",   "`numpy>=1.26`",    "At least this version or newer"],
                        ["`~=`",   "`numpy~=1.26.0`",  "Compatible release (same major.minor)"],
                        ["`!=`",   "`numpy!=1.26.1`",  "Any version except this one"],
                        ["`<`",    "`numpy<2.0`",      "Strictly less than"],
                        ["(none)", "`numpy`",          "Latest — **not recommended** for prod"],
                    ],
                },
                "warning": (
                    "Never commit a `requirements.txt` from a **dirty env** (one with leftover "
                    "experimental packages). Use `pip-tools` or `uv pip compile` for clean lockfiles "
                    "with proper dependency resolution."
                ),
                "snippet": "# Generate requirements.txt from current env\npip freeze > requirements.txt\n\n# Install from requirements.txt\npip install -r requirements.txt\n\n# Example requirements.txt:\nnumpy==1.26.0\npandas>=2.0.0\nrequests~=2.31.0\nflask\n\n# Reproducible install with hashes (supply chain safety)\npip install --require-hashes -r requirements.txt",
                "links": [
                    ("📖 pip freeze", "https://pip.pypa.io/en/stable/cli/pip_freeze/"),
                    ("🔒 pip-tools", "https://github.com/jazzband/pip-tools"),
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
    # Python Temelleri
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "python_basics",
        "icon": "🐍",
        "title": "Python Basics",
        "desc": "Variables, types, control flow, functions, classes — the fundamentals",
        "color": "#a6e3a1",
        "topics": [
            {
                "title": "Variables & Data Types",
                "body": (
                    "Python has **dynamic typing**: the type of a variable is determined at runtime. "
                    "You don't declare types — just assign.\n\n"
                    "Every built-in type is either **mutable** (can change in place) or **immutable** "
                    "(creates a new object on change). This distinction matters for performance and correctness."
                ),
                "table": {
                    "headers": ["Type", "Category", "Example", "Mutable?"],
                    "rows": [
                        ["`int`",   "Number",     "`42`, `10**100`",             "— (immutable)"],
                        ["`float`", "Number",     "`3.14`, `1.5e-10`",           "— (immutable)"],
                        ["`str`",   "Text",       "`\"hello\"`, `f'{name}'`",     "— (immutable)"],
                        ["`bool`",  "Boolean",    "`True`, `False`",             "— (immutable)"],
                        ["`tuple`", "Sequence",   "`(1, 2, 3)`",                  "— (immutable)"],
                        ["`list`",  "Sequence",   "`[1, 2, 3]`",                  "✓ mutable"],
                        ["`dict`",  "Mapping",    "`{'a': 1}`",                   "✓ mutable"],
                        ["`set`",   "Collection", "`{1, 2, 3}`",                  "✓ mutable"],
                        ["`None`",  "Singleton",  "`None`",                       "— (immutable)"],
                    ],
                },
                "diagram": (
                    "  a = [1, 2, 3]        ← list at memory address 0x100\n"
                    "  b = a                ← b points to the SAME list\n"
                    "  a.append(4)          ← mutates the shared list\n"
                    "  print(b)             ← [1, 2, 3, 4]  ← both see the change!\n"
                    "\n"
                    "  x = 10               ← int at 0x200\n"
                    "  y = x                ← y points to 0x200 too\n"
                    "  x = x + 1            ← x points to a NEW int 0x204\n"
                    "  print(y)             ← 10  ← y unchanged (int is immutable)"
                ),
                "snippet": "# Numbers\nx = 42\npi = 3.14159\nbig = 10 ** 100  # unbounded ints\n\n# Strings\nname = \"Ada\"\nmsg = f\"Hello, {name}!\"    # f-string\nmulti = \"\"\"multi\nline\"\"\"\n\n# Collections\nfruits = [\"apple\", \"banana\"]       # list — mutable\ncoords = (3, 4)                     # tuple — immutable\nperson = {\"name\": \"Ada\", \"age\": 36} # dict\nunique = {1, 2, 3, 2}               # set → {1, 2, 3}\n\n# Type check\nprint(type(x))           # <class 'int'>\nprint(isinstance(x, int)) # True",
                "tip": (
                    "Use **f-strings** for all string formatting — they're faster and more readable "
                    "than `%` or `.format()`."
                ),
                "warning": (
                    "When you pass a mutable object (list, dict) to a function, the function can "
                    "**modify the original**. Pass a copy with `list(x)` or `dict(x)` if you don't want that."
                ),
                "links": [
                    ("📖 Python Docs", "https://docs.python.org/3/tutorial/introduction.html"),
                    ("📖 Data Types", "https://docs.python.org/3/library/stdtypes.html"),
                ],
            },
            {
                "title": "Control Flow: if / for / while",
                "body": (
                    "Python uses **indentation** (4 spaces by convention) instead of braces "
                    "to delimit blocks. No semicolons needed at line ends."
                ),
                "snippet": "# if / elif / else\nage = 18\nif age < 13:\n    tier = \"child\"\nelif age < 20:\n    tier = \"teen\"\nelse:\n    tier = \"adult\"\n\n# for with range\nfor i in range(5):       # 0, 1, 2, 3, 4\n    print(i)\n\n# for over a collection\nfor fruit in [\"apple\", \"banana\"]:\n    print(fruit)\n\n# enumerate — index + value\nfor idx, fruit in enumerate([\"a\", \"b\"]):\n    print(idx, fruit)\n\n# while\nn = 10\nwhile n > 0:\n    n -= 1\n\n# match (Python 3.10+)\nmatch status:\n    case 200: print(\"OK\")\n    case 404: print(\"Not Found\")\n    case _:   print(\"Unknown\")",
                "note": (
                    "Use `for item in iterable:` instead of C-style `for i in range(len(items))`. "
                    "It's idiomatic and avoids off-by-one errors."
                ),
                "table": {
                    "headers": ["Statement", "When to use", "Example"],
                    "rows": [
                        ["`if/elif/else`", "Branching on conditions",   "Role lookup, validation"],
                        ["`for x in ...`", "Iterate over known items",  "List, dict, file lines"],
                        ["`while`",        "Loop until condition false","Game loop, retry logic"],
                        ["`match/case`",   "Pattern match (3.10+)",     "Parsing, state machines"],
                        ["`break`",        "Exit loop early",           "Found target in search"],
                        ["`continue`",     "Skip to next iteration",    "Filter bad rows in loop"],
                        ["`else` on loop", "Runs if loop didn't break", "Flag 'not found' case"],
                    ],
                },
                "tip": (
                    "Python loops have an **unusual `else` clause** that runs when the loop "
                    "completes without `break`. Perfect for search patterns: "
                    "`for x in items: if match: break; else: print('not found')`."
                ),
                "links": [
                    ("📖 Control Flow", "https://docs.python.org/3/tutorial/controlflow.html"),
                    ("📖 match statement", "https://peps.python.org/pep-0636/"),
                ],
            },
            {
                "title": "Functions & Arguments",
                "body": (
                    "Functions are **first-class objects** — you can pass them around, return them, "
                    "store them in variables. Arguments support **defaults**, `*args`, `**kwargs`."
                ),
                "table": {
                    "headers": ["Argument kind", "Syntax", "Example call"],
                    "rows": [
                        ["Positional",       "`def f(a, b):`",            "`f(1, 2)`"],
                        ["Default",          "`def f(a, b=10):`",         "`f(1)` → b=10"],
                        ["Keyword-only",     "`def f(*, a, b):`",         "`f(a=1, b=2)`"],
                        ["Positional-only",  "`def f(a, b, /):`",         "`f(1, 2)` (can't use names)"],
                        ["Variadic args",    "`def f(*nums):`",           "`f(1, 2, 3)` → nums=(1,2,3)"],
                        ["Variadic kwargs",  "`def f(**opts):`",          "`f(a=1)` → opts={'a':1}"],
                        ["Type-hinted",      "`def f(x: int) -> str:`",   "Static check with mypy"],
                    ],
                },
                "snippet": "# Basic function\ndef greet(name: str) -> str:\n    return f\"Hello, {name}!\"\n\n# Default arguments\ndef greet(name: str = \"world\") -> str:\n    return f\"Hello, {name}!\"\n\n# Keyword args\nprint(greet(name=\"Ada\"))\n\n# Variable arguments\ndef sum_all(*numbers):\n    return sum(numbers)\nsum_all(1, 2, 3, 4)  # 10\n\n# Keyword variadic\ndef make_dict(**kwargs):\n    return kwargs\nmake_dict(a=1, b=2)  # {'a': 1, 'b': 2}\n\n# Lambda (anonymous)\nsquare = lambda x: x ** 2\n\n# Type hints (recommended)\ndef add(a: int, b: int) -> int:\n    return a + b",
                "warning": (
                    "**Never use mutable default arguments** like `def foo(items=[])`. "
                    "The default is created ONCE and reused across calls. Use `None` and `items = []` inside."
                ),
                "note": (
                    "Functions can be **nested** (closures capture outer variables) and returned "
                    "as values — the foundation for decorators, callbacks, and functional patterns."
                ),
                "links": [
                    ("📖 Functions", "https://docs.python.org/3/tutorial/controlflow.html#defining-functions"),
                    ("📖 PEP 570", "https://peps.python.org/pep-0570/"),
                ],
            },
            {
                "title": "Classes & Objects (OOP)",
                "body": (
                    "Python supports **object-oriented programming** with classes. `self` refers to "
                    "the instance; `cls` refers to the class. Constructor is `__init__`."
                ),
                "diagram": (
                    "       ┌────────────────┐\n"
                    "       │    Animal      │  ← base class\n"
                    "       │  kingdom       │    class variable (shared)\n"
                    "       │  __init__      │    constructor\n"
                    "       │  speak()       │    method\n"
                    "       └───────┬────────┘\n"
                    "               │ inherits from\n"
                    "       ┌───────┴────────┐\n"
                    "       │                │\n"
                    "  ┌─────┴────┐   ┌──────┴─────┐\n"
                    "  │   Dog    │   │   Cat      │   ← subclasses override speak()\n"
                    "  │ speak()  │   │  speak()   │\n"
                    "  └──────────┘   └────────────┘"
                ),
                "snippet": "class Animal:\n    \"\"\"Base class for animals.\"\"\"\n\n    # Class variable (shared)\n    kingdom = \"Animalia\"\n\n    def __init__(self, name: str, age: int):\n        # Instance variables\n        self.name = name\n        self.age = age\n\n    def speak(self) -> str:\n        return \"...\"\n\n    def __repr__(self) -> str:\n        return f\"{type(self).__name__}({self.name!r}, {self.age})\"\n\n\nclass Dog(Animal):\n    def speak(self) -> str:\n        return \"Woof!\"\n\n\nclass Cat(Animal):\n    def speak(self) -> str:\n        return \"Meow!\"\n\n\nrex = Dog(\"Rex\", 5)\nprint(rex)              # Dog('Rex', 5)\nprint(rex.speak())       # Woof!\nprint(isinstance(rex, Animal))  # True",
                "table": {
                    "headers": ["Dunder method", "Triggered by", "Purpose"],
                    "rows": [
                        ["`__init__`",  "`Obj(...)` construction", "Initialize instance"],
                        ["`__repr__`",  "`repr(obj)`, debug print", "Unambiguous dev repr"],
                        ["`__str__`",   "`str(obj)`, `print(obj)`", "User-friendly text"],
                        ["`__eq__`",    "`a == b`",                  "Equality comparison"],
                        ["`__hash__`",  "`hash(obj)`, set/dict keys", "Hashability"],
                        ["`__len__`",   "`len(obj)`",                "Length/count"],
                        ["`__iter__`",  "`for x in obj`",            "Iteration protocol"],
                        ["`__call__`",  "`obj()`",                   "Make instance callable"],
                        ["`__enter__` / `__exit__`", "`with obj:`",  "Context manager"],
                    ],
                },
                "tip": (
                    "Use `@dataclass` for data-heavy classes — auto-generates `__init__`, "
                    "`__repr__`, `__eq__` for you. See next topic."
                ),
                "links": [
                    ("📖 Classes", "https://docs.python.org/3/tutorial/classes.html"),
                    ("📖 Data model", "https://docs.python.org/3/reference/datamodel.html"),
                ],
            },
            {
                "title": "Dataclasses",
                "body": (
                    "`@dataclass` decorator auto-generates boilerplate for **data-carrier** classes. "
                    "Much cleaner than writing `__init__`, `__repr__`, `__eq__` manually.\n\n"
                    "Available since Python 3.7 (`dataclasses` module) — no external dependencies needed."
                ),
                "table": {
                    "headers": ["Decorator arg", "What it does", "When to use"],
                    "rows": [
                        ["`frozen=True`",       "Immutable — no attribute changes after init", "Dict keys, set members, value objects"],
                        ["`order=True`",        "Auto `<`, `<=`, `>`, `>=` from field order",  "Sortable records"],
                        ["`slots=True`",        "Use `__slots__` — faster, less memory (3.10+)", "Many instances"],
                        ["`kw_only=True`",      "All fields keyword-only (3.10+)",             "Avoid positional confusion"],
                        ["`eq=False`",          "Don't generate `__eq__`",                     "Use reference equality"],
                    ],
                },
                "snippet": "from dataclasses import dataclass, field\nfrom typing import List\n\n@dataclass\nclass Point:\n    x: float\n    y: float\n    label: str = \"origin\"\n\np = Point(1.0, 2.0)\nprint(p)  # Point(x=1.0, y=2.0, label='origin')\n\n# Mutable defaults need field(default_factory=...)\n@dataclass\nclass Config:\n    name: str\n    tags: List[str] = field(default_factory=list)\n\n# Frozen (immutable) dataclass\n@dataclass(frozen=True)\nclass Coord:\n    x: int\n    y: int\n\n# Can now use as dict key / in set\npoints = {Coord(0, 0), Coord(1, 1)}",
                "tip": (
                    "For **validation** + serialization, use **Pydantic** instead — stricter type checks, "
                    "JSON/dict conversion, and FastAPI integration. Dataclasses stay in stdlib for simple cases."
                ),
                "warning": (
                    "For mutable default values (`list`, `dict`, `set`), use `field(default_factory=list)` — "
                    "**not** `= []`. Direct mutable defaults raise ValueError in dataclasses."
                ),
                "packages": ["pydantic"],
                "links": [
                    ("📖 dataclasses", "https://docs.python.org/3/library/dataclasses.html"),
                    ("🔥 Pydantic", "https://docs.pydantic.dev/"),
                ],
            },
            {
                "title": "Exception Handling",
                "body": (
                    "Use `try`/`except`/`else`/`finally` to handle errors gracefully. "
                    "Python has a rich exception hierarchy — **catch specifically**, not broadly."
                ),
                "diagram": (
                    "  BaseException\n"
                    "  ├── SystemExit         ← sys.exit()\n"
                    "  ├── KeyboardInterrupt  ← Ctrl+C\n"
                    "  └── Exception          ← catch-all for regular errors\n"
                    "      ├── ArithmeticError\n"
                    "      │   ├── ZeroDivisionError\n"
                    "      │   └── OverflowError\n"
                    "      ├── LookupError\n"
                    "      │   ├── IndexError    ← list[99] out of range\n"
                    "      │   └── KeyError      ← dict['nope'] not found\n"
                    "      ├── OSError           ← file, socket, permission errors\n"
                    "      ├── TypeError         ← wrong type used\n"
                    "      ├── ValueError        ← right type, wrong value\n"
                    "      └── ...many more"
                ),
                "snippet": "# Basic try/except\ntry:\n    result = 10 / 0\nexcept ZeroDivisionError as e:\n    print(f\"Math error: {e}\")\n\n# Multiple exceptions\ntry:\n    data = json.loads(user_input)\nexcept (json.JSONDecodeError, TypeError) as e:\n    print(f\"Bad input: {e}\")\n\n# finally always runs\ntry:\n    f = open(\"data.txt\")\n    data = f.read()\nfinally:\n    f.close()\n\n# Better: context manager\nwith open(\"data.txt\") as f:\n    data = f.read()\n# auto-closed, even on exception\n\n# Custom exception\nclass ValidationError(Exception):\n    pass\n\nraise ValidationError(\"Invalid email format\")",
                "warning": (
                    "**Never use bare `except:`** — it catches `KeyboardInterrupt` and `SystemExit`, "
                    "hiding real bugs. Always specify the exception type, or use `except Exception:` "
                    "for a catch-all that still lets Ctrl+C work."
                ),
                "tip": (
                    "Use `except ... as e:` and `logging.exception(e)` to capture full tracebacks — "
                    "never silently swallow exceptions in production code."
                ),
                "links": [
                    ("📖 Errors", "https://docs.python.org/3/tutorial/errors.html"),
                    ("📖 Exception hierarchy", "https://docs.python.org/3/library/exceptions.html"),
                ],
            },
            {
                "title": "List / Dict / Set Comprehensions",
                "body": (
                    "Comprehensions are **concise, readable** ways to transform collections. "
                    "Much faster than equivalent `for` loops (runs at C speed internally)."
                ),
                "table": {
                    "headers": ["Type", "Syntax", "Returns"],
                    "rows": [
                        ["List",      "`[expr for x in iter]`",           "`list`"],
                        ["Dict",      "`{k: v for x in iter}`",            "`dict`"],
                        ["Set",       "`{expr for x in iter}`",            "`set`"],
                        ["Generator", "`(expr for x in iter)`",            "`generator` (lazy)"],
                        ["Filtered",  "`[expr for x in iter if cond]`",    "filtered collection"],
                        ["Nested",    "`[[expr for y in a] for x in b]`",  "2D list (etc.)"],
                    ],
                },
                "snippet": "# List comprehension\nsquares = [x ** 2 for x in range(10)]\n# [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]\n\n# With filter\nevens = [x for x in range(20) if x % 2 == 0]\n\n# Nested\nmatrix = [[i * j for j in range(5)] for i in range(5)]\n\n# Dict comprehension\nsquared = {x: x ** 2 for x in range(5)}\n# {0: 0, 1: 1, 2: 4, 3: 9, 4: 16}\n\n# Set comprehension\nunique_lens = {len(word) for word in [\"hi\", \"bye\", \"yo\"]}\n# {2, 3}\n\n# Generator expression (lazy, memory-efficient)\ntotal = sum(x ** 2 for x in range(1_000_000))",
                "tip": (
                    "Prefer **generator expressions** `(x for x in ...)` over list comprehensions "
                    "when you just iterate once — saves memory for large data."
                ),
                "warning": (
                    "**Don't nest more than 2 comprehensions** — readability drops fast. "
                    "Use a regular `for` loop with descriptive variable names instead."
                ),
                "links": [
                    ("📖 Comprehensions", "https://docs.python.org/3/tutorial/datastructures.html#list-comprehensions"),
                    ("📖 PEP 274 (Dict)", "https://peps.python.org/pep-0274/"),
                ],
            },
            {
                "title": "Decorators",
                "body": (
                    "Decorators **wrap a function** to add behavior without modifying its code. "
                    "Syntax sugar for `func = decorator(func)`.\n\n"
                    "Common uses: **logging, timing, caching, authentication, retry logic, rate limiting.**"
                ),
                "diagram": (
                    "  @timer                       ┌────────────────────┐\n"
                    "  def slow():       ═══>       │  wrapper(*args)    │\n"
                    "      time.sleep(1)             │   start = now()   │\n"
                    "                                │   result = slow()  │  ← original function\n"
                    "  # equivalent to:              │   log(now()-start) │\n"
                    "  slow = timer(slow)           │   return result   │\n"
                    "                                └────────────────────┘"
                ),
                "snippet": "import functools\nimport time\n\ndef timer(func):\n    @functools.wraps(func)\n    def wrapper(*args, **kwargs):\n        start = time.perf_counter()\n        result = func(*args, **kwargs)\n        elapsed = time.perf_counter() - start\n        print(f\"{func.__name__}: {elapsed:.3f}s\")\n        return result\n    return wrapper\n\n@timer\ndef slow():\n    time.sleep(1)\n    return 42\n\nslow()  # slow: 1.001s → 42\n\n# Built-in @functools.lru_cache — memoization\n@functools.lru_cache(maxsize=128)\ndef fib(n: int) -> int:\n    if n < 2: return n\n    return fib(n-1) + fib(n-2)\n\nfib(100)  # instant (would be slow without cache)",
                "table": {
                    "headers": ["Decorator", "From", "What it does"],
                    "rows": [
                        ["`@property`",            "builtin",              "Method as attribute"],
                        ["`@staticmethod`",        "builtin",              "Method without `self`/`cls`"],
                        ["`@classmethod`",         "builtin",              "Method receiving `cls`"],
                        ["`@functools.lru_cache`", "`functools`",          "Memoize (cache results)"],
                        ["`@functools.wraps`",     "`functools`",          "Preserve name/docstring in wrappers"],
                        ["`@dataclass`",           "`dataclasses`",        "Auto-gen class boilerplate"],
                        ["`@contextmanager`",      "`contextlib`",         "Convert generator to context manager"],
                        ["`@pytest.fixture`",      "`pytest`",             "Provide test setup/teardown"],
                    ],
                },
                "tip": (
                    "Always use `@functools.wraps(func)` inside your wrapper — it preserves the "
                    "original function's name, docstring, and signature (critical for debugging and IDEs)."
                ),
                "links": [
                    ("📖 Decorators", "https://peps.python.org/pep-0318/"),
                    ("📖 functools", "https://docs.python.org/3/library/functools.html"),
                ],
            },
            {
                "title": "Generators & Iterators",
                "body": (
                    "Generators produce values **lazily** using `yield`. Iterating over a "
                    "generator doesn't load all values into memory — perfect for **huge datasets, "
                    "infinite sequences, and streaming pipelines**."
                ),
                "snippet": "# Generator function\ndef count_up_to(n):\n    i = 0\n    while i < n:\n        yield i\n        i += 1\n\nfor x in count_up_to(5):\n    print(x)  # 0, 1, 2, 3, 4\n\n# Read a huge log file line-by-line (O(1) memory)\ndef read_log(path):\n    with open(path) as f:\n        for line in f:\n            if \"ERROR\" in line:\n                yield line\n\n# Consume\nerrors = list(read_log(\"app.log\"))\n\n# Infinite generator\ndef fibonacci():\n    a, b = 0, 1\n    while True:\n        yield a\n        a, b = b, a + b\n\nimport itertools\nfirst_10 = list(itertools.islice(fibonacci(), 10))",
                "table": {
                    "headers": ["itertools function", "What it does", "Example"],
                    "rows": [
                        ["`chain(*iterables)`",    "Link iterables end-to-end", "`chain([1,2], [3,4])` → 1,2,3,4"],
                        ["`islice(it, stop)`",     "Slice any iterable lazily", "First 10 of infinite seq"],
                        ["`groupby(it, key)`",     "Group consecutive items",   "`groupby(sorted_data, key)`"],
                        ["`product(*iters)`",      "Cartesian product",         "All combinations"],
                        ["`combinations(it, r)`",  "All r-length picks",        "lottery numbers"],
                        ["`permutations(it, r)`",  "All orderings",             "anagrams"],
                        ["`takewhile(pred, it)`",  "Take until predicate False", "until first negative"],
                        ["`accumulate(it)`",       "Running sum/product",       "cumulative sums"],
                    ],
                },
                "tip": (
                    "Chain generators for **data pipelines**: "
                    "`squared = (x*x for x in read_log())` — each step streams, no intermediate lists."
                ),
                "warning": (
                    "Generators are **single-use** — once exhausted, they're empty. "
                    "Call the generator function again to get a fresh iterator, or use `itertools.tee()`."
                ),
                "links": [
                    ("📖 Generators", "https://docs.python.org/3/howto/functional.html#generators"),
                    ("📖 itertools", "https://docs.python.org/3/library/itertools.html"),
                ],
            },
            {
                "title": "Type Hints & typing",
                "body": (
                    "Type hints make code **self-documenting** and enable static checkers like **mypy** "
                    "to catch bugs before runtime. Hints have **zero runtime cost** — they're just annotations."
                ),
                "table": {
                    "headers": ["Old (3.8-)", "Modern (3.9+/3.10+)", "Meaning"],
                    "rows": [
                        ["`List[int]`",           "`list[int]`",            "List of ints (3.9+)"],
                        ["`Dict[str, int]`",      "`dict[str, int]`",       "str→int mapping (3.9+)"],
                        ["`Tuple[int, str]`",     "`tuple[int, str]`",      "Fixed-shape tuple (3.9+)"],
                        ["`Optional[int]`",       "`int | None`",           "Int or None (3.10+)"],
                        ["`Union[int, str]`",     "`int \\| str`",          "Int or str (3.10+)"],
                        ["`Callable[[int], str]`","`Callable[[int], str]`", "Function taking int, returning str"],
                        ["`TypeVar('T')`",        "`def f[T](x: T) -> T`",  "Generic (3.12+)"],
                    ],
                },
                "snippet": "from typing import List, Dict, Optional, Union, Callable, Tuple\nfrom pathlib import Path\n\n# Basic hints\ndef greet(name: str, times: int = 1) -> str:\n    return f\"Hello {name}\\n\" * times\n\n# Collections\ndef parse(nums: List[int]) -> Dict[str, int]:\n    return {\"sum\": sum(nums), \"count\": len(nums)}\n\n# Optional = Union[X, None]\ndef find_user(uid: int) -> Optional[dict]:\n    ...\n\n# Modern syntax (Python 3.10+)\ndef find_user(uid: int) -> dict | None:\n    ...\n\n# Callable\ndef apply(fn: Callable[[int], int], x: int) -> int:\n    return fn(x)\n\n# Tuple with fixed types\ndef min_max(nums: List[int]) -> Tuple[int, int]:\n    return min(nums), max(nums)",
                "tip": (
                    "Add `from __future__ import annotations` at the top of older Python files — "
                    "lets you use modern `list[int]` / `int | None` syntax everywhere, regardless of Python version."
                ),
                "note": (
                    "`mypy`, `pyright`, and `ruff` all check type hints. Use **strict mode** for new code "
                    "and gradually tighten as you gain confidence. IDEs (VS Code, PyCharm) use these for autocomplete."
                ),
                "packages": ["mypy"],
                "links": [
                    ("📖 typing", "https://docs.python.org/3/library/typing.html"),
                    ("🔍 mypy", "https://mypy.readthedocs.io/"),
                    ("🧪 pyright", "https://github.com/microsoft/pyright"),
                ],
            },
            {
                "title": "Modules & Packages",
                "body": (
                    "A **module** is a `.py` file. A **package** is a directory with `__init__.py` "
                    "(or PEP 420 namespace). Imports let you reuse code across files."
                ),
                "diagram": (
                    "  my_package/\n"
                    "  ├── __init__.py        ← marks directory as package\n"
                    "  ├── main.py\n"
                    "  ├── utils.py\n"
                    "  └── submodule/\n"
                    "      ├── __init__.py\n"
                    "      └── helpers.py\n"
                    "\n"
                    "  # From main.py:\n"
                    "  from .utils import clean\n"
                    "  from .submodule.helpers import fetch"
                ),
                "snippet": "# Import a module\nimport math\nprint(math.pi)\n\n# Import specific name\nfrom math import pi, sqrt\n\n# Alias\nimport numpy as np\n\n# Relative import (inside a package)\nfrom .utils import clean\nfrom ..common import config\n\n# Guarded main block\nif __name__ == \"__main__\":\n    # Only runs when file is executed directly,\n    # NOT when imported\n    main()",
                "table": {
                    "headers": ["Import form", "Example", "When to use"],
                    "rows": [
                        ["Module",          "`import math`",                "Few calls — `math.sqrt(x)` is explicit"],
                        ["Specific name",   "`from math import sqrt`",      "Many calls to same few names"],
                        ["Alias",           "`import numpy as np`",         "Standard community conventions (np, pd, plt)"],
                        ["All names",       "`from math import *`",         "❌ Avoid — pollutes namespace"],
                        ["Relative",        "`from .utils import clean`",   "Inside a package"],
                        ["Deferred",        "inside function body",         "Break circular imports, reduce startup time"],
                    ],
                },
                "note": (
                    "The `if __name__ == \"__main__\":` idiom lets a file work both as a "
                    "**standalone script** AND as an **importable module**. Essential for library code."
                ),
                "warning": (
                    "**Never use `from x import *`** in production code — it pollutes your namespace, "
                    "breaks IDE autocomplete, and makes `grep`ing for usage impossible."
                ),
                "links": [
                    ("📖 Modules", "https://docs.python.org/3/tutorial/modules.html"),
                    ("📖 PEP 328 relative imports", "https://peps.python.org/pep-0328/"),
                ],
            },
            {
                "title": "async / await (asyncio)",
                "body": (
                    "`async`/`await` enables **concurrent I/O** without threads. Perfect for network "
                    "requests, web servers, database queries — **anything that waits a lot**.\n\n"
                    "Async is about **concurrency**, not parallelism: one event loop juggles many "
                    "coroutines, switching between them whenever one awaits."
                ),
                "table": {
                    "headers": ["Workload", "Use async?", "Why"],
                    "rows": [
                        ["HTTP requests to many URLs",  "✅ Yes",             "Waiting on network — async excels"],
                        ["Read 1000s of files",         "⚠ Sometimes",       "Depends on OS — `aiofiles` can help"],
                        ["Database queries",             "✅ Yes",             "asyncpg/SQLAlchemy async — huge wins"],
                        ["Web server handlers",          "✅ Yes",             "FastAPI/Starlette scale to thousands"],
                        ["CPU-intensive math",           "❌ No",              "Use `multiprocessing` or `threading`"],
                        ["Simple scripts",               "❌ No",              "Overhead not worth it — stay sync"],
                    ],
                },
                "snippet": "import asyncio\nimport aiohttp  # pip install aiohttp\n\nasync def fetch(session, url):\n    async with session.get(url) as resp:\n        return await resp.text()\n\nasync def main():\n    async with aiohttp.ClientSession() as session:\n        urls = [\n            \"https://python.org\",\n            \"https://pypi.org\",\n            \"https://github.com\",\n        ]\n        # Concurrent fetches\n        results = await asyncio.gather(\n            *(fetch(session, u) for u in urls)\n        )\n        for url, html in zip(urls, results):\n            print(f\"{url}: {len(html)} bytes\")\n\nasyncio.run(main())",
                "tip": (
                    "Use `asyncio.gather()` to run coroutines **concurrently**. "
                    "Awaiting one-by-one runs sequentially — defeats the point."
                ),
                "warning": (
                    "**Never mix blocking calls** (`requests.get`, `time.sleep`) inside async code — "
                    "they freeze the event loop. Use `aiohttp`/`httpx`, `asyncio.sleep` etc."
                ),
                "packages": ["aiohttp", "httpx"],
                "links": [
                    ("📖 asyncio", "https://docs.python.org/3/library/asyncio.html"),
                    ("🚀 httpx", "https://www.python-httpx.org/"),
                ],
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # İstatistik & Matematik (Data Science Foundations)
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "stats_math",
        "icon": "📐",
        "title": "Statistics & Math",
        "desc": "Probability, distributions, linear algebra, calculus — DS foundations",
        "color": "#fab387",
        "topics": [
            {
                "title": "Descriptive Statistics",
                "body": (
                    "Summarize data with **central tendency** (mean, median, mode) and "
                    "**dispersion** (variance, std deviation, IQR). These are the building "
                    "blocks of all data analysis."
                ),
                "snippet": "import numpy as np\nimport statistics\n\ndata = [23, 45, 67, 12, 89, 34, 56, 78, 90, 11]\n\n# Central tendency\nmean   = np.mean(data)      # 50.5\nmedian = np.median(data)    # 50.5\nmode   = statistics.mode([1,2,2,3,4])  # 2\n\n# Dispersion\nvariance = np.var(data, ddof=1)   # sample variance\nstd      = np.std(data, ddof=1)   # sample std\niqr      = np.percentile(data, 75) - np.percentile(data, 25)\n\n# Quartiles\nq1, q2, q3 = np.percentile(data, [25, 50, 75])\n\n# Full summary\nimport pandas as pd\npd.Series(data).describe()\n# count, mean, std, min, 25%, 50%, 75%, max",
                "table": {
                    "headers": ["Metric", "When to use", "Robust to outliers?"],
                    "rows": [
                        ["Mean",      "Symmetric data",             "❌ No"],
                        ["Median",    "Skewed data, outliers",       "✅ Yes"],
                        ["Mode",      "Categorical, most-frequent",  "✅ Yes"],
                        ["Std dev",   "Symmetric data",             "❌ No"],
                        ["IQR",       "Skewed data, outliers",       "✅ Yes"],
                    ],
                },
                "packages": ["numpy", "pandas"],
                "links": [
                    ("📖 NumPy stats", "https://numpy.org/doc/stable/reference/routines.statistics.html"),
                ],
            },
            {
                "title": "Probability Distributions",
                "body": (
                    "Distributions model how data is spread. **Normal** (Gaussian), **Poisson**, "
                    "**Binomial**, **Exponential** cover most real-world cases. Use `scipy.stats`."
                ),
                "snippet": "from scipy import stats\nimport numpy as np\nimport matplotlib.pyplot as plt\n\n# Normal distribution: N(μ=0, σ=1)\nx = np.linspace(-4, 4, 200)\npdf = stats.norm.pdf(x, loc=0, scale=1)\n\nplt.plot(x, pdf)\nplt.title(\"Standard Normal PDF\")\nplt.xlabel(\"z\")\nplt.ylabel(\"density\")\nplt.show()\n\n# Sample from distributions\nnormal_samples  = stats.norm.rvs(loc=10, scale=2, size=1000)\nuniform_samples = stats.uniform.rvs(0, 1, size=1000)\npoisson_samples = stats.poisson.rvs(mu=5, size=1000)\n\n# Probability (P(X <= x))\nstats.norm.cdf(1.96)    # 0.975 (two-tailed critical value)\n\n# Inverse CDF (quantile function)\nstats.norm.ppf(0.95)    # 1.645",
                "table": {
                    "headers": ["Distribution", "Models", "Parameters"],
                    "rows": [
                        ["Normal",      "Heights, IQ scores, measurement error", "μ (mean), σ (std)"],
                        ["Binomial",    "# successes in N trials",                "n, p"],
                        ["Poisson",     "Count of events per interval",           "λ (rate)"],
                        ["Exponential", "Time between events",                    "λ (rate)"],
                        ["Uniform",     "Equal probability in [a, b]",            "a, b"],
                        ["Beta",        "Probabilities, proportions",             "α, β"],
                    ],
                },
                "packages": ["scipy", "matplotlib"],
                "links": [
                    ("📖 scipy.stats", "https://docs.scipy.org/doc/scipy/reference/stats.html"),
                ],
            },
            {
                "title": "Hypothesis Testing",
                "body": (
                    "Hypothesis tests answer: **\"is this effect real or just chance?\"** "
                    "Standard flow:\n"
                    "1. Null hypothesis `H₀` (no effect)\n"
                    "2. Alternative `H₁` (effect exists)\n"
                    "3. Compute test statistic\n"
                    "4. Get p-value — if `p < α` (usually 0.05), reject `H₀`"
                ),
                "snippet": "from scipy import stats\nimport numpy as np\n\n# ── t-test: are two group means different? ──\ngroup_a = np.random.normal(100, 15, 50)  # IQ test group A\ngroup_b = np.random.normal(105, 15, 50)  # group B\n\nt_stat, p_value = stats.ttest_ind(group_a, group_b)\nprint(f\"t = {t_stat:.3f}, p = {p_value:.4f}\")\nif p_value < 0.05:\n    print(\"Groups are significantly different\")\n\n# ── Chi-squared: categorical independence ──\nobserved = [[50, 30], [20, 60]]  # e.g. gender × preference\nchi2, p, dof, expected = stats.chi2_contingency(observed)\n\n# ── ANOVA: compare 3+ group means ──\nf_stat, p = stats.f_oneway(group_a, group_b, group_c)\n\n# ── Shapiro-Wilk: is data normal? ──\nstat, p = stats.shapiro(group_a)  # p > 0.05 → normal",
                "warning": (
                    "`p < 0.05` does **not** mean a result is practically important. "
                    "With huge samples, trivial effects get tiny p-values. Always report "
                    "**effect size** (Cohen's d, η²) alongside p-values."
                ),
                "packages": ["scipy"],
                "links": [
                    ("📖 scipy.stats tests", "https://docs.scipy.org/doc/scipy/reference/stats.html#statistical-tests"),
                ],
            },
            {
                "title": "Linear Algebra with NumPy",
                "body": (
                    "ML, graphics, simulations — all built on matrices and vectors. "
                    "`numpy.linalg` gives you the essentials."
                ),
                "snippet": "import numpy as np\n\n# Vectors and matrices\nv = np.array([1, 2, 3])\nM = np.array([[1, 2], [3, 4]])\n\n# Basic ops\nM.T                  # transpose\nM @ M                # matrix multiply (Python 3.5+ @ operator)\nnp.linalg.inv(M)     # inverse\nnp.linalg.det(M)     # determinant → -2.0\nnp.trace(M)          # trace → 5\n\n# Dot product\nnp.dot(v, v)         # 14\nv @ v                # same — 14\n\n# Eigenvalues / eigenvectors\neigvals, eigvecs = np.linalg.eig(M)\n\n# Solve Ax = b\nA = np.array([[1, 2], [3, 4]])\nb = np.array([5, 11])\nx = np.linalg.solve(A, b)   # [-1. , 3.]\n\n# SVD — foundation of PCA, recommenders\nU, s, Vt = np.linalg.svd(M)\n\n# Norms\nnp.linalg.norm(v)        # L2 norm\nnp.linalg.norm(v, ord=1) # L1 norm",
                "tip": (
                    "NumPy broadcasts scalars and compatible shapes — no explicit loops needed. "
                    "**Avoid Python for-loops over NumPy arrays** — they're 100× slower."
                ),
                "packages": ["numpy"],
                "links": [
                    ("📖 numpy.linalg", "https://numpy.org/doc/stable/reference/routines.linalg.html"),
                ],
            },
            {
                "title": "Calculus with SymPy",
                "body": (
                    "**SymPy** does symbolic math — exact derivatives, integrals, limits. "
                    "Unlike NumPy (numeric), SymPy returns formulas."
                ),
                "snippet": "import sympy as sp\n\n# Symbols\nx, y = sp.symbols('x y')\n\n# Define a function\nf = x**3 - 2*x**2 + x - 1\n\n# Derivative\nf_prime = sp.diff(f, x)\n# 3x² - 4x + 1\n\n# Integral\nF = sp.integrate(f, x)\n# x⁴/4 - 2x³/3 + x²/2 - x\n\n# Definite integral\nsp.integrate(f, (x, 0, 2))    # -2/3\n\n# Limit\nsp.limit(sp.sin(x)/x, x, 0)   # 1\n\n# Solve equations\nsp.solve(f, x)                # roots of x³-2x²+x-1=0\nsp.solve([x + y - 5, x - y - 1], [x, y])  # {x: 3, y: 2}\n\n# Taylor series\nsp.series(sp.cos(x), x, 0, 6)\n# 1 - x²/2 + x⁴/24 + O(x⁶)\n\n# Pretty print\nsp.pprint(f_prime)",
                "packages": ["sympy"],
                "links": [
                    ("📖 SymPy", "https://docs.sympy.org/"),
                ],
            },
            {
                "title": "Bayes' Theorem & Bayesian Thinking",
                "body": (
                    "Bayes' theorem updates beliefs with evidence:\n\n"
                    "**P(A|B) = P(B|A) × P(A) / P(B)**\n\n"
                    "Read as: *posterior ∝ likelihood × prior*. Core to spam filters, "
                    "medical diagnosis, A/B testing, and Bayesian ML."
                ),
                "snippet": "# Example: disease test problem\n# Disease has 1% prevalence\n# Test: 95% sensitivity, 90% specificity\n# You test positive. What's the probability you have it?\n\nprior            = 0.01        # P(disease)\nsensitivity      = 0.95        # P(positive | disease)\nfalse_positive   = 0.10        # P(positive | no disease)\n\n# Total probability of positive test\np_positive = (\n    sensitivity * prior\n    + false_positive * (1 - prior)\n)\n\n# Bayes' theorem\nposterior = sensitivity * prior / p_positive\nprint(f\"P(disease | positive) = {posterior:.1%}\")\n# Result: ~8.8%, not 95% — counterintuitive!\n\n# Library: pymc for Bayesian modeling\n# pip install pymc\nimport pymc as pm\nwith pm.Model():\n    p = pm.Beta('p', alpha=1, beta=1)  # uniform prior\n    obs = pm.Binomial('obs', n=100, p=p, observed=60)\n    trace = pm.sample(1000)",
                "note": (
                    "The 'disease test paradox': even with a 95% accurate test, testing positive "
                    "for a rare disease often means you probably DON'T have it. Always consider the prior."
                ),
                "packages": ["pymc"],
                "links": [
                    ("📖 PyMC", "https://www.pymc.io/"),
                    ("📺 3Blue1Brown", "https://www.youtube.com/watch?v=HZGCoVF3YvM"),
                ],
            },
            {
                "title": "Linear Regression (OLS)",
                "body": (
                    "**Linear regression** fits `y = β₀ + β₁x + ε` to data. Foundation of "
                    "predictive modeling and econometrics. Three ways in Python:"
                ),
                "snippet": "import numpy as np\nimport pandas as pd\n\n# ── Option 1: NumPy from scratch ──\nx = np.array([1, 2, 3, 4, 5])\ny = np.array([2.1, 3.9, 6.1, 8.0, 10.2])\n\nslope, intercept = np.polyfit(x, y, deg=1)\nprint(f\"y = {slope:.2f}x + {intercept:.2f}\")\n\n# ── Option 2: scikit-learn ──\nfrom sklearn.linear_model import LinearRegression\nX = x.reshape(-1, 1)\nmodel = LinearRegression().fit(X, y)\nprint(f\"slope={model.coef_[0]:.3f}, intercept={model.intercept_:.3f}\")\nprint(f\"R² = {model.score(X, y):.4f}\")\n\n# ── Option 3: statsmodels (best for inference) ──\nimport statsmodels.api as sm\nX_sm = sm.add_constant(x)   # add intercept column\nresult = sm.OLS(y, X_sm).fit()\nprint(result.summary())     # full stats, p-values, CIs",
                "tip": (
                    "Use **statsmodels** when you need p-values, confidence intervals, and "
                    "diagnostics. Use **sklearn** when you need prediction in an ML pipeline."
                ),
                "packages": ["scikit-learn", "statsmodels"],
                "links": [
                    ("📖 statsmodels", "https://www.statsmodels.org/"),
                    ("📖 sklearn linear", "https://scikit-learn.org/stable/modules/linear_model.html"),
                ],
            },
            {
                "title": "PCA — Principal Component Analysis",
                "body": (
                    "PCA reduces high-dimensional data to a few components that capture the most "
                    "variance. Used for **visualization, compression, denoising**."
                ),
                "snippet": "import numpy as np\nfrom sklearn.decomposition import PCA\nfrom sklearn.datasets import load_iris\nimport matplotlib.pyplot as plt\n\n# Iris: 4D → 2D\niris = load_iris()\nX, y = iris.data, iris.target\n\npca = PCA(n_components=2)\nX_2d = pca.fit_transform(X)\n\nprint(f\"Explained variance: {pca.explained_variance_ratio_}\")\n# e.g. [0.729, 0.229] — first 2 components cover 95.8%\n\n# Plot\nfor cls in range(3):\n    mask = y == cls\n    plt.scatter(X_2d[mask, 0], X_2d[mask, 1],\n                label=iris.target_names[cls])\nplt.xlabel('PC1')\nplt.ylabel('PC2')\nplt.legend()\nplt.show()\n\n# Key: components are orthogonal, ordered by variance\nprint(pca.components_)   # 2×4 matrix of loadings",
                "warning": (
                    "**Always standardize** features before PCA if they have different units "
                    "(age in years vs. income in $). Use `StandardScaler` first."
                ),
                "packages": ["scikit-learn", "matplotlib"],
                "links": [
                    ("📖 sklearn PCA", "https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.PCA.html"),
                ],
            },
            {
                "title": "Monte Carlo Simulation",
                "body": (
                    "**Monte Carlo** estimates results via random sampling. Powerful for integrals, "
                    "risk analysis, physics simulations, option pricing, game AI."
                ),
                "snippet": "import numpy as np\n\n# ── Estimate π using random points in a unit square ──\nN = 1_000_000\nx = np.random.uniform(-1, 1, N)\ny = np.random.uniform(-1, 1, N)\n\ninside_circle = (x**2 + y**2) <= 1\npi_est = 4 * inside_circle.mean()\nprint(f\"π ≈ {pi_est:.5f}\")   # ~3.14159\n\n# ── Option pricing (Black-Scholes via MC) ──\nS0 = 100     # spot price\nK  = 105     # strike\nT  = 1       # years\nr  = 0.05    # risk-free rate\nsigma = 0.2  # volatility\n\nN = 100_000\nZ = np.random.standard_normal(N)\nST = S0 * np.exp((r - 0.5 * sigma**2) * T + sigma * np.sqrt(T) * Z)\npayoff = np.maximum(ST - K, 0)\ncall_price = np.exp(-r * T) * payoff.mean()\nprint(f\"Call option price ≈ ${call_price:.2f}\")\n\n# ── Confidence interval of the estimate ──\nstd_err = payoff.std() / np.sqrt(N)\nprint(f\"95% CI: ±{1.96 * std_err:.3f}\")",
                "tip": (
                    "Monte Carlo error decreases as `1/√N`. To halve the error, you need **4×** more samples. "
                    "Use **variance reduction** (antithetic variates, control variates) for faster convergence."
                ),
                "packages": ["numpy"],
                "links": [
                    ("📖 NumPy random", "https://numpy.org/doc/stable/reference/random/index.html"),
                ],
            },
            {
                "title": "Optimization (scipy.optimize)",
                "body": (
                    "Find minimum/maximum of a function — critical for ML (loss), "
                    "engineering (design), operations (cost)."
                ),
                "snippet": "from scipy import optimize\nimport numpy as np\n\n# ── Minimize a scalar function ──\ndef f(x):\n    return (x - 2)**2 + 3\n\nresult = optimize.minimize(f, x0=0)\nprint(result.x)    # [2.] — minimum at x=2\nprint(result.fun)  # 3.0 — min value\n\n# ── Multivariate: Rosenbrock banana function ──\ndef rosenbrock(x):\n    return sum(100 * (x[1:] - x[:-1]**2)**2 + (1 - x[:-1])**2)\n\nres = optimize.minimize(rosenbrock, x0=[0, 0, 0],\n                         method='Nelder-Mead')\nprint(res.x)     # [1., 1., 1.]\n\n# ── Find a root (where f(x)=0) ──\nroot = optimize.brentq(lambda x: x**2 - 2, 0, 2)\nprint(root)      # √2 ≈ 1.41421\n\n# ── Curve fitting ──\ndef model(x, a, b):\n    return a * np.exp(-b * x)\n\nxdata = np.linspace(0, 4, 50)\nydata = 2.5 * np.exp(-0.8 * xdata) + 0.2 * np.random.randn(50)\nparams, _ = optimize.curve_fit(model, xdata, ydata)\nprint(f\"Fitted: a={params[0]:.3f}, b={params[1]:.3f}\")",
                "packages": ["scipy"],
                "links": [
                    ("📖 scipy.optimize", "https://docs.scipy.org/doc/scipy/reference/optimize.html"),
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
            {
                "title": "Scikit-learn — Classical ML",
                "body": (
                    "scikit-learn is the go-to library for classical machine learning. "
                    "Consistent API: fit/predict/score for every model. "
                    "Decision trees, SVMs, random forests, k-means, and more."
                ),
                "snippet": "from sklearn.datasets import load_iris\nfrom sklearn.model_selection import train_test_split\nfrom sklearn.ensemble import RandomForestClassifier\nfrom sklearn.metrics import classification_report, confusion_matrix\nimport numpy as np\n\n# Load built-in dataset\niris = load_iris()\nX, y = iris.data, iris.target\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)\n\n# Train Random Forest\nrf = RandomForestClassifier(n_estimators=100, random_state=42)\nrf.fit(X_train, y_train)\n\n# Evaluate\ny_pred = rf.predict(X_test)\nprint(classification_report(y_test, y_pred, target_names=iris.target_names))\n\n# Feature importance\nfor name, imp in zip(iris.feature_names, rf.feature_importances_):\n    print(f'{name:25s}: {imp:.3f}')",
                "packages": ["scikit-learn"],
                "links": [("🌐 scikit-learn.org", "https://scikit-learn.org")],
            },
            {
                "title": "Neural Networks from Scratch",
                "body": (
                    "Build a 2-layer neural network with just NumPy. "
                    "Forward pass, backpropagation, gradient descent — "
                    "understanding these fundamentals makes framework docs click."
                ),
                "snippet": "import numpy as np\n\ndef sigmoid(z): return 1 / (1 + np.exp(-z))\ndef sigmoid_grad(a): return a * (1 - a)\n\nnp.random.seed(42)\n# XOR dataset\nX = np.array([[0,0],[0,1],[1,0],[1,1]], dtype=float)\ny = np.array([[0],[1],[1],[0]], dtype=float)\n\n# Weights\nW1 = np.random.randn(2, 4) * 0.5\nb1 = np.zeros((1, 4))\nW2 = np.random.randn(4, 1) * 0.5\nb2 = np.zeros((1, 1))\n\nlr = 0.5\nfor epoch in range(5000):\n    # Forward\n    z1 = X @ W1 + b1\n    a1 = sigmoid(z1)\n    z2 = a1 @ W2 + b2\n    a2 = sigmoid(z2)\n\n    # Loss (MSE)\n    loss = np.mean((a2 - y)**2)\n\n    # Backward\n    d2 = 2*(a2-y) * sigmoid_grad(a2)\n    d1 = (d2 @ W2.T) * sigmoid_grad(a1)\n    W2 -= lr * a1.T @ d2; b2 -= lr * d2.mean(0)\n    W1 -= lr * X.T  @ d1; b1 -= lr * d1.mean(0)\n\n    if epoch % 1000 == 0:\n        print(f'Epoch {epoch:5d}  loss={loss:.6f}')\n\nprint('\\nPredictions:', a2.round(2).T)",
                "packages": ["numpy"],
            },
            {
                "title": "PyTorch — Tensors & Autograd",
                "body": (
                    "PyTorch is the most popular deep learning framework in research. "
                    "Dynamic computation graphs, intuitive debugging, and a rich ecosystem. "
                    "Autograd computes gradients automatically."
                ),
                "snippet": "import torch\nimport torch.nn as nn\n\n# Tensors\nx = torch.tensor([[1., 2.], [3., 4.]], requires_grad=True)\ny = (x ** 2).sum()\ny.backward()              # compute gradients\nprint('Gradient:', x.grad) # dy/dx = 2x\n\n# Simple linear regression with autograd\ntorch.manual_seed(0)\nX = torch.randn(100, 1)\ny = 3 * X + 2 + 0.1 * torch.randn(100, 1)\n\nmodel = nn.Linear(1, 1)\noptimizer = torch.optim.SGD(model.parameters(), lr=0.1)\nloss_fn = nn.MSELoss()\n\nfor epoch in range(200):\n    pred = model(X)\n    loss = loss_fn(pred, y)\n    optimizer.zero_grad()\n    loss.backward()\n    optimizer.step()\n\nw, b = model.weight.item(), model.bias.item()\nprint(f'Learned: y = {w:.3f}x + {b:.3f}  (true: 3x + 2)')",
                "packages": ["torch"],
                "links": [("🌐 pytorch.org", "https://pytorch.org")],
            },
            {
                "title": "Data Preprocessing Pipeline",
                "body": (
                    "Raw data is messy. sklearn's Pipeline chains preprocessing steps "
                    "and a model into one object — preventing data leakage and simplifying "
                    "cross-validation."
                ),
                "snippet": "from sklearn.pipeline import Pipeline\nfrom sklearn.preprocessing import StandardScaler, OneHotEncoder\nfrom sklearn.compose import ColumnTransformer\nfrom sklearn.ensemble import GradientBoostingClassifier\nfrom sklearn.datasets import fetch_openml\nfrom sklearn.model_selection import cross_val_score\nimport numpy as np\n\n# Titanic dataset\n# data = fetch_openml('titanic', version=1, as_frame=True)\n# Simulate similar structure\nnp.random.seed(42)\nn = 500\nX_num = np.random.randn(n, 2)\nX_cat = np.random.choice(['A','B','C'], size=(n, 1))\nimport pandas as pd\nX = pd.DataFrame(np.hstack([X_num, X_cat]), columns=['age','fare','class'])\nX['age'] = X['age'].astype(float); X['fare'] = X['fare'].astype(float)\ny = (X['age'] + X['fare'] > 0).astype(int)\n\nnumeric = Pipeline([('scaler', StandardScaler())])\ncategorical = Pipeline([('ohe', OneHotEncoder(handle_unknown='ignore'))])\npreprocessor = ColumnTransformer([\n    ('num', numeric, ['age','fare']),\n    ('cat', categorical, ['class']),\n])\npipeline = Pipeline([('prep', preprocessor), ('clf', GradientBoostingClassifier())])\nscores = cross_val_score(pipeline, X, y, cv=5)\nprint(f'CV accuracy: {scores.mean():.3f} ± {scores.std():.3f}')",
                "packages": ["scikit-learn", "pandas"],
            },
            {
                "title": "Model Evaluation & Hyperparameter Tuning",
                "body": (
                    "Never trust a single train/test split. "
                    "k-Fold cross-validation and GridSearchCV/RandomizedSearchCV "
                    "find the best hyperparameters without overfitting to the test set."
                ),
                "snippet": "from sklearn.datasets import load_breast_cancer\nfrom sklearn.model_selection import GridSearchCV, StratifiedKFold\nfrom sklearn.svm import SVC\nfrom sklearn.preprocessing import StandardScaler\nfrom sklearn.pipeline import Pipeline\n\nX, y = load_breast_cancer(return_X_y=True)\n\npipe = Pipeline([\n    ('scaler', StandardScaler()),\n    ('svc', SVC(probability=True)),\n])\n\nparam_grid = {\n    'svc__C': [0.1, 1, 10],\n    'svc__gamma': ['scale', 'auto'],\n    'svc__kernel': ['rbf', 'linear'],\n}\n\ncv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)\ngrid = GridSearchCV(pipe, param_grid, cv=cv, scoring='roc_auc', n_jobs=-1, verbose=1)\ngrid.fit(X, y)\n\nprint(f'Best AUC: {grid.best_score_:.4f}')\nprint(f'Best params: {grid.best_params_}')",
                "packages": ["scikit-learn"],
            },
            {
                "title": "Model Serialization & Deployment",
                "body": (
                    "Trained models must be saved and served. "
                    "joblib for sklearn models, torch.save for PyTorch, "
                    "ONNX for cross-framework export. FastAPI makes a simple inference server."
                ),
                "snippet": "import joblib\nfrom sklearn.ensemble import RandomForestClassifier\nfrom sklearn.datasets import load_iris\nimport numpy as np\n\n# Train\nX, y = load_iris(return_X_y=True)\nmodel = RandomForestClassifier(n_estimators=50, random_state=42)\nmodel.fit(X, y)\n\n# Save\njoblib.dump(model, '/tmp/iris_rf.joblib')\nprint('Model saved.')\n\n# Load and predict\nloaded = joblib.load('/tmp/iris_rf.joblib')\nsample = np.array([[5.1, 3.5, 1.4, 0.2]])\nprob = loaded.predict_proba(sample)[0]\nnames = load_iris().target_names\nprint('Prediction probabilities:')\nfor name, p in zip(names, prob):\n    print(f'  {name}: {p:.3f}')\n\n# FastAPI serving example:\n# from fastapi import FastAPI\n# app = FastAPI()\n# @app.post('/predict')\n# def predict(features: list[float]):\n#     return {'class': names[loaded.predict([features])[0]]}'",
                "packages": ["scikit-learn", "joblib"],
                "links": [("🌐 fastapi.tiangolo.com", "https://fastapi.tiangolo.com")],
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
            {
                "title": "FITS Files — Astronomical Data Format",
                "body": (
                    "FITS (Flexible Image Transport System) is the standard file format "
                    "for astronomical data. astropy.io.fits reads images, spectra, "
                    "and tables from telescopes worldwide."
                ),
                "snippet": "from astropy.io import fits\nimport numpy as np\nimport matplotlib.pyplot as plt\n\n# Open a FITS file (e.g. Hubble image)\n# hdu = fits.open('hubble_image.fits')\n# hdu.info()  # list extensions\n\n# Create a synthetic FITS image\ndata = np.random.normal(1000, 50, (256, 256))\n# Add a fake star\nfor i in range(256):\n    for j in range(256):\n        r = np.sqrt((i-128)**2 + (j-128)**2)\n        data[i, j] += 50000 * np.exp(-r**2 / (2*5**2))\n\nhdu = fits.PrimaryHDU(data)\nhdu.header['TELESCOP'] = 'MySim'\nhdu.header['FILTER']   = 'V'\nhdu.writeto('/tmp/star.fits', overwrite=True)\n\n# Read it back\nwith fits.open('/tmp/star.fits') as hdul:\n    img = hdul[0].data\n    print(hdul[0].header['TELESCOP'])\n\nplt.imshow(img, cmap='inferno', origin='lower')\nplt.colorbar(label='Counts')\nplt.title('Simulated Star')\nplt.show()",
                "packages": ["astropy", "matplotlib"],
                "links": [
                    ("📖 FITS Standard", "https://fits.gsfc.nasa.gov/"),
                ],
            },
            {
                "title": "Spectroscopy — Analyzing Stellar Spectra",
                "body": (
                    "Spectrographs split starlight into wavelengths. "
                    "By analyzing absorption/emission lines we determine "
                    "temperature, chemical composition, and radial velocity."
                ),
                "snippet": "import numpy as np\nimport matplotlib.pyplot as plt\nfrom scipy.signal import find_peaks\n\n# Simulate a stellar spectrum (blackbody + absorption lines)\nwl = np.linspace(380, 750, 1000)  # nm\n\n# Planck function (T = 6000 K, like the Sun)\nh, c, k = 6.626e-34, 3e8, 1.38e-23\nT = 6000\nlambda_m = wl * 1e-9\nB = (2*h*c**2 / lambda_m**5) / (np.exp(h*c/(lambda_m*k*T)) - 1)\nB /= B.max()\n\n# Add Hydrogen Balmer absorption lines\nfor line_nm, depth in [(656.3, 0.3), (486.1, 0.2), (434.0, 0.15)]:\n    sigma = 2.0\n    B -= depth * np.exp(-0.5*((wl - line_nm)/sigma)**2)\n\nplt.plot(wl, B, 'b-', lw=0.8)\nplt.xlabel('Wavelength (nm)')\nplt.ylabel('Relative Flux')\nplt.title('Simulated Solar Spectrum (G2V)')\nplt.axvline(656.3, color='r', lw=0.5, label='Hα')\nplt.legend()\nplt.show()",
                "packages": ["numpy", "matplotlib", "scipy"],
            },
            {
                "title": "N-Body Gravity Simulation",
                "body": (
                    "Simulate gravitational interactions between N bodies — "
                    "planets, stars, or dark matter particles. "
                    "Uses Leapfrog integration for energy conservation."
                ),
                "snippet": "import numpy as np\nimport matplotlib.pyplot as plt\n\nG = 6.674e-11  # gravitational constant\n\ndef nbody_step(pos, vel, mass, dt):\n    n = len(mass)\n    acc = np.zeros_like(pos)\n    for i in range(n):\n        for j in range(n):\n            if i == j: continue\n            r = pos[j] - pos[i]\n            dist = np.linalg.norm(r) + 1e-10\n            acc[i] += G * mass[j] * r / dist**3\n    vel += acc * dt\n    pos += vel * dt\n    return pos, vel\n\n# Sun + Earth system (AU units, G=4π²)\nG = 4 * np.pi**2\nmass = np.array([1.0, 3e-6])           # solar masses\npos  = np.array([[0.,0.], [1.,0.]])    # AU\nvel  = np.array([[0.,0.], [0., 2*np.pi]])  # AU/yr\n\ntrajectory = [pos.copy()]\nfor _ in range(1000):\n    pos, vel = nbody_step(pos, vel, mass, dt=0.001)\n    trajectory.append(pos.copy())\n\ntraj = np.array(trajectory)\nplt.plot(traj[:,1,0], traj[:,1,1], 'b-', lw=0.5)\nplt.plot(0, 0, 'yo', ms=12, label='Sun')\nplt.axis('equal'); plt.legend(); plt.title('Earth Orbit (1 year)')\nplt.show()",
                "packages": ["numpy", "matplotlib"],
            },
            {
                "title": "Radio Astronomy — Signal Processing",
                "body": (
                    "Radio telescopes detect faint signals and require heavy DSP. "
                    "FFT-based spectral analysis, folding pulsar signals, and "
                    "removing radio-frequency interference (RFI)."
                ),
                "snippet": "import numpy as np\nimport matplotlib.pyplot as plt\n\n# Simulate a pulsar signal\nfs = 10000   # sample rate (Hz)\nduration = 1 # second\nt = np.linspace(0, duration, fs * duration)\n\n# Pulsar period = 33 ms (like Crab pulsar)\nperiod = 0.033\npulse = np.zeros_like(t)\nfor i, ti in enumerate(t):\n    phase = (ti % period) / period\n    if phase < 0.05:  # 5% duty cycle\n        pulse[i] = np.exp(-((phase - 0.025)/0.01)**2)\n\n# Add noise\nnoise = np.random.normal(0, 0.3, len(t))\nsignal = pulse + noise\n\n# FFT spectrum\nfreqs = np.fft.rfftfreq(len(t), 1/fs)\nspectrum = np.abs(np.fft.rfft(signal))\n\nplt.figure(figsize=(12,4))\nplt.subplot(1,2,1); plt.plot(t[:1000], signal[:1000]); plt.title('Signal')\nplt.subplot(1,2,2); plt.semilogy(freqs[:200], spectrum[:200]); plt.title('Spectrum')\nplt.tight_layout(); plt.show()",
                "packages": ["numpy", "matplotlib"],
            },
            {
                "title": "Exoplanet Transit Detection",
                "body": (
                    "When a planet crosses its star, brightness dips slightly. "
                    "This transit photometry method discovered thousands of exoplanets. "
                    "Simulate and detect transits using lightkurve."
                ),
                "snippet": "import numpy as np\nimport matplotlib.pyplot as plt\n\n# Simulate a transit light curve\nt = np.linspace(0, 10, 1000)  # days\n\n# Planet parameters\nperiod = 3.5      # days\nt0 = 1.5          # first transit\ndepth = 0.01      # 1% dip (Earth-like around Sun = 0.008%)\nduration = 0.1    # days\n\nflux = np.ones_like(t)\nfor center in np.arange(t0, 10, period):\n    in_transit = np.abs(t - center) < duration/2\n    # Trapezoidal shape\n    flux[in_transit] -= depth * (1 - (np.abs(t[in_transit] - center) / (duration/2))**2)\n\n# Add photon noise\nflux += np.random.normal(0, 0.002, len(t))\n\nplt.figure(figsize=(12,4))\nplt.plot(t, flux, 'k.', ms=2, alpha=0.7)\nplt.axhline(1-depth, color='r', ls='--', label=f'Transit depth {depth:.1%}')\nplt.xlabel('Time (days)'); plt.ylabel('Relative Flux')\nplt.title('Simulated Exoplanet Transit'); plt.legend()\nplt.show()",
                "packages": ["numpy", "matplotlib"],
                "links": [
                    ("🌐 lightkurve.org", "https://lightkurve.org"),
                ],
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
            {
                "title": "Collision Detection & Physics",
                "body": (
                    "Collision detection is the backbone of any game. "
                    "Pygame provides rect-based AABB collision. "
                    "For more realistic physics use pymunk (2D Chipmunk binding)."
                ),
                "snippet": "import pygame\nimport pymunk\nimport pymunk.pygame_util\n\npygame.init()\nscreen = pygame.display.set_mode((600, 400))\nclock = pygame.time.Clock()\n\nspace = pymunk.Space()\nspace.gravity = (0, -900)\n\n# Ground\nground = pymunk.Segment(space.static_body, (0, 50), (600, 50), 5)\nground.friction = 0.8\nspace.add(ground)\n\n# Falling ball\nbody = pymunk.Body(1, pymunk.moment_for_circle(1, 0, 20))\nbody.position = (300, 350)\nshape = pymunk.Circle(body, 20)\nshape.elasticity = 0.8\nspace.add(body, shape)\n\ndraw_options = pymunk.pygame_util.DrawOptions(screen)\n\nrunning = True\nwhile running:\n    for event in pygame.event.get():\n        if event.type == pygame.QUIT: running = False\n    screen.fill((20, 20, 30))\n    space.step(1/60)\n    space.debug_draw(draw_options)\n    pygame.display.flip()\n    clock.tick(60)\npygame.quit()",
                "packages": ["pygame", "pymunk"],
                "links": [("🌐 pymunk.org", "https://www.pymunk.org")],
            },
            {
                "title": "Sprite Sheets & Animation",
                "body": (
                    "Sprite sheets pack multiple animation frames into one image. "
                    "Load once, blit different regions each frame — faster than loading "
                    "individual files."
                ),
                "snippet": "import pygame\n\npygame.init()\nscreen = pygame.display.set_mode((400, 300))\nclock = pygame.time.Clock()\n\n# Load sprite sheet (each frame 64x64)\n# sheet = pygame.image.load('character.png').convert_alpha()\n# Simulate with colored rects\nCOLORS = [(255,0,0),(0,255,0),(0,0,255),(255,255,0)]\nFRAME_W, FRAME_H = 64, 64\nFPS = 8  # animation fps\n\nframe = 0\ntimer = 0\n\nrunning = True\nwhile running:\n    dt = clock.tick(60) / 1000\n    for event in pygame.event.get():\n        if event.type == pygame.QUIT: running = False\n\n    timer += dt\n    if timer >= 1/FPS:\n        frame = (frame + 1) % len(COLORS)\n        timer = 0\n\n    screen.fill((30, 30, 40))\n    # Draw current frame (colored rect as placeholder)\n    pygame.draw.rect(screen, COLORS[frame], (168, 118, FRAME_W, FRAME_H))\n    pygame.draw.rect(screen, (255,255,255), (168, 118, FRAME_W, FRAME_H), 2)\n    pygame.display.flip()\npygame.quit()",
                "packages": ["pygame"],
            },
            {
                "title": "Tilemap & Tiled Integration",
                "body": (
                    "Tilemaps build worlds from reusable tiles. "
                    "Design levels in Tiled editor (free), export as TMX, "
                    "and load with pytiled-parser or arcade's built-in loader."
                ),
                "snippet": "# With Arcade's built-in Tiled support:\nimport arcade\n\nclass TiledGame(arcade.Window):\n    def __init__(self):\n        super().__init__(800, 600, 'Tiled Map Demo')\n        self.tile_map = None\n        self.scene = None\n        self.camera = arcade.Camera(800, 600)\n\n    def setup(self):\n        # Load a .tmx file exported from Tiled editor\n        # self.tile_map = arcade.load_tilemap('map.tmx', scaling=2.0)\n        # self.scene = arcade.Scene.from_tilemap(self.tile_map)\n        pass\n\n    def on_draw(self):\n        self.clear()\n        self.camera.use()\n        # self.scene.draw()\n        arcade.draw_text('Load a .tmx tilemap!', 200, 300,\n                         arcade.color.WHITE, 24)\n\nTiledGame().setup()\nif __name__ == '__main__':\n    arcade.run()",
                "packages": ["arcade"],
                "links": [("🌐 mapeditor.org", "https://www.mapeditor.org/")],
            },
            {
                "title": "Sound & Music with Pygame",
                "body": (
                    "pygame.mixer handles sound effects and background music. "
                    "Load OGG/WAV files for sound effects, MP3/OGG for music. "
                    "Control volume, channels, and loop count."
                ),
                "snippet": "import pygame\nimport numpy as np\n\npygame.init()\npygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)\n\n# Generate a beep sound programmatically (440 Hz sine wave)\nfs = 44100\nduration = 0.3  # seconds\nt = np.linspace(0, duration, int(fs * duration), False)\nwave = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)\nstereo = np.column_stack([wave, wave])\n\nsound = pygame.sndarray.make_sound(stereo)\n\n# Play sound\nscreen = pygame.display.set_mode((300, 200))\npygame.display.set_caption('Press SPACE to beep')\nclock = pygame.time.Clock()\n\nrunning = True\nwhile running:\n    for event in pygame.event.get():\n        if event.type == pygame.QUIT: running = False\n        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:\n            sound.play()\n    clock.tick(60)\npygame.quit()",
                "packages": ["pygame", "numpy"],
            },
            {
                "title": "Game State Machine",
                "body": (
                    "A State Machine (FSM) cleanly separates Menu, Playing, Paused, "
                    "and GameOver states. Each state handles its own events, updates, "
                    "and rendering — no tangled if/else chains."
                ),
                "snippet": "import pygame\nfrom enum import Enum, auto\n\nclass State(Enum):\n    MENU = auto()\n    PLAYING = auto()\n    PAUSED = auto()\n    GAME_OVER = auto()\n\npygame.init()\nscreen = pygame.display.set_mode((400, 300))\nclock = pygame.time.Clock()\nfont = pygame.font.SysFont(None, 36)\n\nstate = State.MENU\nscore = 0\n\nrunning = True\nwhile running:\n    for event in pygame.event.get():\n        if event.type == pygame.QUIT: running = False\n        if event.type == pygame.KEYDOWN:\n            if state == State.MENU and event.key == pygame.K_RETURN:\n                state = State.PLAYING; score = 0\n            elif state == State.PLAYING and event.key == pygame.K_ESCAPE:\n                state = State.PAUSED\n            elif state == State.PAUSED and event.key == pygame.K_ESCAPE:\n                state = State.PLAYING\n            elif state == State.GAME_OVER and event.key == pygame.K_RETURN:\n                state = State.MENU\n\n    if state == State.PLAYING:\n        score += 1\n        if score > 300: state = State.GAME_OVER\n\n    screen.fill((20,20,30))\n    labels = {State.MENU: 'MENU — Press ENTER', State.PLAYING: f'PLAYING — score {score}',\n              State.PAUSED: 'PAUSED — ESC to resume', State.GAME_OVER: 'GAME OVER — ENTER'}\n    txt = font.render(labels[state], True, (200,200,200))\n    screen.blit(txt, (20, 130))\n    pygame.display.flip(); clock.tick(60)\npygame.quit()",
                "packages": ["pygame"],
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
            {
                "title": "Layouts & Responsive UI",
                "body": (
                    "PySide6 layouts automatically resize widgets when the window grows. "
                    "QHBoxLayout, QVBoxLayout, QGridLayout, and QFormLayout are the four pillars. "
                    "Combine them to build complex UIs."
                ),
                "snippet": "from PySide6.QtWidgets import (\n    QApplication, QWidget, QHBoxLayout, QVBoxLayout,\n    QGridLayout, QLabel, QPushButton, QLineEdit, QSizePolicy\n)\nimport sys\n\napp = QApplication(sys.argv)\nwindow = QWidget()\nwindow.setWindowTitle('Layout Demo')\nwindow.resize(400, 300)\n\nmain = QVBoxLayout(window)\n\n# Top bar\ntop = QHBoxLayout()\ntop.addWidget(QLabel('Search:'))\ntop.addWidget(QLineEdit())\ntop.addWidget(QPushButton('Go'))\nmain.addLayout(top)\n\n# Grid of buttons\ngrid = QGridLayout()\nfor r in range(3):\n    for c in range(3):\n        btn = QPushButton(f'({r},{c})')\n        grid.addWidget(btn, r, c)\nmain.addLayout(grid)\n\n# Stretch to push everything up\nmain.addStretch()\nwindow.show()\nsys.exit(app.exec())",
                "packages": ["PySide6"],
                "links": [("📖 Qt Layouts", "https://doc.qt.io/qt-6/layout.html")],
            },
            {
                "title": "Signals & Slots — Event System",
                "body": (
                    "Qt's signal/slot mechanism connects events to handlers without tight coupling. "
                    "Built-in signals (clicked, textChanged) or define custom signals "
                    "with Signal()."
                ),
                "snippet": "from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QSlider\nfrom PySide6.QtCore import Signal, QObject, Qt\nimport sys\n\nclass Counter(QObject):\n    value_changed = Signal(int)  # custom signal\n\n    def __init__(self):\n        super().__init__()\n        self._val = 0\n\n    def increment(self):\n        self._val += 1\n        self.value_changed.emit(self._val)  # emit signal\n\napp = QApplication(sys.argv)\nwindow = QWidget()\nlayout = QVBoxLayout(window)\n\nlabel = QLabel('Count: 0')\nbtn   = QPushButton('Click me')\ncounter = Counter()\n\n# Connect signal to slot (any callable)\ncounter.value_changed.connect(lambda v: label.setText(f'Count: {v}'))\nbtn.clicked.connect(counter.increment)\n\nlayout.addWidget(label)\nlayout.addWidget(btn)\nwindow.show()\nsys.exit(app.exec())",
                "packages": ["PySide6"],
            },
            {
                "title": "Threading — Keep UI Responsive",
                "body": (
                    "Never run long tasks on the main thread — it freezes the UI. "
                    "Use QThread or concurrent.futures. "
                    "Communicate results back via signals."
                ),
                "snippet": "from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QProgressBar\nfrom PySide6.QtCore import QThread, Signal\nimport time, sys\n\nclass Worker(QThread):\n    progress = Signal(int)\n    finished = Signal(str)\n\n    def run(self):\n        for i in range(1, 11):\n            time.sleep(0.3)          # simulate work\n            self.progress.emit(i * 10)\n        self.finished.emit('Done!')\n\napp = QApplication(sys.argv)\nwin = QWidget()\nlayout = QVBoxLayout(win)\n\nlabel = QLabel('Press Start')\nbar   = QProgressBar(); bar.setRange(0, 100)\nbtn   = QPushButton('Start')\n\nworker = Worker()\nworker.progress.connect(bar.setValue)\nworker.finished.connect(label.setText)\nbtn.clicked.connect(worker.start)\nbtn.clicked.connect(lambda: btn.setEnabled(False))\n\nlayout.addWidget(label); layout.addWidget(bar); layout.addWidget(btn)\nwin.show(); sys.exit(app.exec())",
                "packages": ["PySide6"],
            },
            {
                "title": "System Tray & Notifications",
                "body": (
                    "QSystemTrayIcon lets your app live in the system tray. "
                    "Show notifications, context menus, and hide/show the main window "
                    "on tray icon click."
                ),
                "snippet": "from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMainWindow\nfrom PySide6.QtGui import QIcon, QPixmap, QColor\nimport sys\n\napp = QApplication(sys.argv)\napp.setQuitOnLastWindowClosed(False)  # keep alive when window closed\n\n# Create a simple colored icon\npx = QPixmap(32, 32); px.fill(QColor('#89b4fa'))\nicon = QIcon(px)\n\ntray = QSystemTrayIcon(icon, app)\ntray.setToolTip('My Tray App')\n\nmenu = QMenu()\nshow_act  = menu.addAction('Show Window')\nquit_act  = menu.addAction('Quit')\ntray.setContextMenu(menu)\n\nwin = QMainWindow()\nwin.setWindowTitle('Tray Demo')\nwin.resize(300, 200)\n\nshow_act.triggered.connect(win.show)\nquit_act.triggered.connect(app.quit)\ntray.activated.connect(lambda r: win.show() if r == QSystemTrayIcon.Trigger else None)\n\ntray.show()\ntray.showMessage('Ready', 'App is running in tray!', QSystemTrayIcon.Information, 2000)\nwin.show()\nsys.exit(app.exec())",
                "packages": ["PySide6"],
            },
            {
                "title": "Tkinter — Built-in GUI",
                "body": (
                    "Tkinter ships with Python — no install needed. "
                    "Great for simple tools and scripts. "
                    "Supports ttk themed widgets for a modern look."
                ),
                "snippet": "import tkinter as tk\nfrom tkinter import ttk, messagebox\n\nroot = tk.Tk()\nroot.title('Tkinter Demo')\nroot.geometry('300x200')\n\n# ttk styled frame\nframe = ttk.Frame(root, padding=20)\nframe.pack(fill='both', expand=True)\n\nttk.Label(frame, text='Enter your name:').pack(anchor='w')\nentry = ttk.Entry(frame)\nentry.pack(fill='x', pady=4)\n\ndef greet():\n    name = entry.get().strip() or 'World'\n    messagebox.showinfo('Hello', f'Hello, {name}!')\n\nttk.Button(frame, text='Greet', command=greet).pack(pady=8)\n\n# Progress bar example\nbar = ttk.Progressbar(frame, mode='indeterminate')\nbar.pack(fill='x')\nbar.start(10)\n\nroot.mainloop()",
                "packages": [],
            },
            {
                "title": "File Dialogs & Settings Persistence",
                "body": (
                    "QFileDialog opens native file pickers. "
                    "QSettings stores user preferences in the OS-native location "
                    "(Registry on Windows, ~/.config on Linux, plist on macOS)."
                ),
                "snippet": "from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog\nfrom PySide6.QtCore import QSettings\nimport sys\n\napp = QApplication(sys.argv)\nwin = QWidget(); win.resize(400, 200)\nlayout = QVBoxLayout(win)\n\nsettings = QSettings('MyCompany', 'MyApp')\nlast_dir = settings.value('last_dir', '')\n\nlabel = QLabel('Last dir: ' + (last_dir or '(none)'))\nlayout.addWidget(label)\n\ndef open_file():\n    path, _ = QFileDialog.getOpenFileName(win, 'Open File', last_dir, '*.py')\n    if path:\n        import os; d = os.path.dirname(path)\n        settings.setValue('last_dir', d)\n        label.setText('Opened: ' + path)\n\nbtn = QPushButton('Open File'); btn.clicked.connect(open_file)\nlayout.addWidget(label); layout.addWidget(btn)\nwin.show(); sys.exit(app.exec())",
                "packages": ["PySide6"],
            }
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
            {
                "title": "Maturin — Build & Publish Rust Extensions",
                "body": (
                    "Maturin builds PyO3 projects and publishes them to PyPI. "
                    "One command creates wheels for Linux, macOS, and Windows. "
                    "The fastest path from Rust code to `pip install`."
                ),
                "snippet": "# Terminal workflow:\n# pip install maturin\n# maturin new mylib --bindings pyo3\n# cd mylib\n# maturin develop          # install locally in editable mode\n# maturin build --release  # build .whl\n# maturin publish          # upload to PyPI\n\n# src/lib.rs (auto-generated):\n# use pyo3::prelude::*;\n# #[pyfunction]\n# fn sum_as_string(a: usize, b: usize) -> PyResult<String> {\n#     Ok((a + b).to_string())\n# }\n# #[pymodule]\n# fn mylib(_py: Python, m: &PyModule) -> PyResult<()> {\n#     m.add_function(wrap_pyfunction!(sum_as_string, m)?)?;\n#     Ok(())\n# }\n\n# After maturin develop:\nimport mylib  # your compiled Rust code!\nprint(mylib.sum_as_string(3, 4))  # '7'",
                "packages": ["maturin"],
                "links": [("🌐 maturin.rs", "https://www.maturin.rs")],
            },
            {
                "title": "cffi & ctypes — Call C/C++ from Python",
                "body": (
                    "Not everything needs Rust. ctypes is in stdlib, "
                    "cffi is more ergonomic. Both let you call compiled C libraries "
                    "without writing a wrapper — great for legacy codebases."
                ),
                "snippet": "import ctypes\nimport ctypes.util\n\n# Load system math library\nlibm = ctypes.CDLL(ctypes.util.find_library('m') or 'libm.so.6')\n\n# Set argument and return types\nlibm.sin.argtypes = [ctypes.c_double]\nlibm.sin.restype  = ctypes.c_double\nlibm.sqrt.argtypes = [ctypes.c_double]\nlibm.sqrt.restype  = ctypes.c_double\n\nimport math\nprint(f'sin(π/6) = {libm.sin(math.pi/6):.6f}')   # 0.5\nprint(f'sqrt(2)  = {libm.sqrt(2.0):.6f}')         # 1.414...\n\n# Create a struct\nclass Point(ctypes.Structure):\n    _fields_ = [('x', ctypes.c_double), ('y', ctypes.c_double)]\n\np = Point(3.0, 4.0)\ndist = libm.sqrt(p.x**2 + p.y**2)\nprint(f'Distance from origin: {dist:.2f}')  # 5.0",
                "packages": [],
            },
            {
                "title": "Polars — Rust-Powered DataFrames",
                "body": (
                    "Polars is a DataFrame library written in Rust — typically 5–50× "
                    "faster than pandas for large datasets. "
                    "Lazy evaluation builds a query plan and optimizes it before executing."
                ),
                "snippet": "import polars as pl\nimport numpy as np\n\n# Create a DataFrame\nnp.random.seed(42)\nn = 1_000_000\ndf = pl.DataFrame({\n    'id':       np.arange(n),\n    'category': np.random.choice(['A','B','C','D'], n),\n    'value':    np.random.exponential(10, n),\n    'score':    np.random.normal(50, 15, n).clip(0, 100),\n})\n\n# Lazy query — optimized before execution\nresult = (\n    df.lazy()\n    .filter(pl.col('score') > 40)\n    .group_by('category')\n    .agg([\n        pl.col('value').mean().alias('avg_value'),\n        pl.col('score').median().alias('med_score'),\n        pl.len().alias('count'),\n    ])\n    .sort('avg_value', descending=True)\n    .collect()\n)\nprint(result)",
                "packages": ["polars"],
                "links": [("🌐 pola.rs", "https://pola.rs")],
            },
            {
                "title": "Ruff — Rust-Powered Python Linter",
                "body": (
                    "Ruff replaces flake8, isort, pyupgrade, and more — "
                    "10–100× faster because it's written in Rust. "
                    "Configured in pyproject.toml, CI-friendly, and editor-integrated."
                ),
                "snippet": "# Install\n# pip install ruff\n\n# Run on current directory\n# ruff check .\n# ruff check . --fix   # auto-fix safe issues\n# ruff format .        # format like Black\n\n# pyproject.toml configuration:\n# [tool.ruff]\n# line-length = 88\n# target-version = 'py311'\n# select = ['E', 'F', 'I', 'UP', 'N']  # rules to enable\n# ignore = ['E501']                    # rules to ignore\n\n# [tool.ruff.isort]\n# known-first-party = ['mypackage']\n\n# Example: run ruff programmatically\nimport subprocess, sys\nresult = subprocess.run(\n    [sys.executable, '-m', 'ruff', 'check', '--select=F', '.'],\n    capture_output=True, text=True\n)\nprint(result.stdout or 'No issues found!')",
                "packages": ["ruff"],
                "links": [("🌐 docs.astral.sh/ruff", "https://docs.astral.sh/ruff/")],
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

    # ═══════════════════════════════════════════════════════════════════════════
    # Core Libraries
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "core_libs",
        "icon": "📦",
        "title": "Core Libraries",
        "desc": "NumPy, Pandas, Matplotlib, Seaborn, Plotly, Requests, Pillow",
        "color": "#89b4fa",
        "topics": [
            {
                "title": "NumPy — Arrays & Vectorized Math",
                "body": (
                    "NumPy is the foundation of scientific Python. "
                    "ndarray gives you C-speed array operations in pure Python syntax. "
                    "Broadcasting lets you operate on arrays of different shapes without loops."
                ),
                "snippet": "import numpy as np\n\na = np.array([1, 2, 3, 4, 5])\nb = np.arange(0, 10, 2)          # [0 2 4 6 8]\nc = np.linspace(0, 1, 5)         # [0. .25 .5 .75 1.]\nz = np.zeros((3, 4))\nr = np.random.randn(100, 2)\n\n# Vectorized ops (no loops!)\nprint(a * 2)\nprint(np.sqrt(a))\nprint(a @ a)                     # dot product = 55\n\n# Broadcasting\nm = np.array([[1,2],[3,4],[5,6]])\nprint(m + np.array([10, 20]))    # add [10,20] to each row\n\n# Slicing\nprint(m[:, 0])                   # first column\nprint(m[m > 3])                  # boolean mask\n\n# Aggregations\nprint(m.mean(axis=0))\nprint(m.sum(), m.max(), m.std())",
                "packages": ["numpy"],
                "links": [("🌐 numpy.org", "https://numpy.org")],
            },
            {
                "title": "Pandas — DataFrames & Data Wrangling",
                "body": (
                    "Pandas is the Excel of Python — but programmable. "
                    "DataFrame is a table with labeled rows and columns. "
                    "Load, clean, transform, merge, and analyze tabular data in minutes."
                ),
                "snippet": "import pandas as pd\nimport numpy as np\n\ndf = pd.DataFrame({\n    'name':   ['Alice', 'Bob', 'Charlie', 'Diana'],\n    'age':    [25, 30, 35, 28],\n    'salary': [60000, 80000, 90000, 75000],\n    'dept':   ['Eng', 'Sales', 'Eng', 'HR'],\n})\n\nprint(df.head(2))\nprint(df.describe())\n\n# Filter\neng = df[df['dept'] == 'Eng']\nprint(df[['name', 'salary']])\n\n# GroupBy\nprint(df.groupby('dept')['salary'].mean())\n\n# New column\ndf['bonus'] = df['salary'] * 0.1\n\n# Handle missing\ndf2 = df.copy(); df2.loc[0, 'age'] = np.nan\ndf2['age'].fillna(df2['age'].median(), inplace=True)\n\n# Sort\nprint(df.sort_values('salary', ascending=False))",
                "packages": ["pandas"],
                "links": [("🌐 pandas.pydata.org", "https://pandas.pydata.org")],
            },
            {
                "title": "Matplotlib — Plotting Fundamentals",
                "body": (
                    "Matplotlib is the bedrock of Python visualization. "
                    "Full control over every pixel — axes, ticks, colors, annotations. "
                    "pyplot provides a MATLAB-like interface for quick plots."
                ),
                "snippet": "import matplotlib.pyplot as plt\nimport numpy as np\n\nx = np.linspace(0, 2*np.pi, 300)\n\nfig, axes = plt.subplots(2, 2, figsize=(10, 8))\nfig.suptitle('Matplotlib Gallery', fontsize=14, fontweight='bold')\n\naxes[0,0].plot(x, np.sin(x), 'b-', label='sin')\naxes[0,0].plot(x, np.cos(x), 'r--', label='cos')\naxes[0,0].legend(); axes[0,0].set_title('Trig Functions')\n\nnp.random.seed(42)\nxs, ys = np.random.randn(200), np.random.randn(200)\naxes[0,1].scatter(xs, ys, c=xs+ys, cmap='viridis', alpha=0.6)\naxes[0,1].set_title('Scatter')\n\ncats = ['A','B','C','D']\naxes[1,0].bar(cats, [23,45,12,67], color='steelblue')\naxes[1,0].set_title('Bar Chart')\n\naxes[1,1].hist(np.random.randn(1000), bins=30, color='salmon', edgecolor='white')\naxes[1,1].set_title('Histogram')\n\nplt.tight_layout()\nplt.show()",
                "packages": ["matplotlib"],
                "links": [("🌐 matplotlib.org", "https://matplotlib.org")],
            },
            {
                "title": "Seaborn — Statistical Visualization",
                "body": (
                    "Seaborn builds on Matplotlib with beautiful defaults and "
                    "high-level functions for statistical plots. "
                    "Heatmaps, violin plots, pair plots — one line each."
                ),
                "snippet": "import seaborn as sns\nimport matplotlib.pyplot as plt\n\nsns.set_theme(style='darkgrid', palette='muted')\ntips = sns.load_dataset('tips')\n\nfig, axes = plt.subplots(1, 3, figsize=(14, 4))\n\nsns.histplot(tips['total_bill'], kde=True, ax=axes[0])\naxes[0].set_title('Distribution')\n\nsns.boxplot(data=tips, x='day', y='total_bill', hue='sex', ax=axes[1])\naxes[1].set_title('Box Plot')\n\ncorr = tips[['total_bill','tip','size']].corr()\nsns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm', ax=axes[2])\naxes[2].set_title('Correlation')\n\nplt.tight_layout()\nplt.show()\n\n# One-liner pair plot:\n# sns.pairplot(tips, hue='sex'); plt.show()",
                "packages": ["seaborn"],
                "links": [("🌐 seaborn.pydata.org", "https://seaborn.pydata.org")],
            },
            {
                "title": "Plotly — Interactive Charts",
                "body": (
                    "Plotly creates interactive charts that zoom, pan, and hover. "
                    "plotly.express is the high-level API — one line for most chart types. "
                    "Works in Jupyter, browsers, and Dash apps."
                ),
                "snippet": "import plotly.express as px\nimport plotly.graph_objects as go\nimport numpy as np\n\n# Gapminder bubble chart\ndf = px.data.gapminder().query('year == 2007')\nfig = px.scatter(\n    df, x='gdpPercap', y='lifeExp',\n    size='pop', color='continent',\n    hover_name='country', log_x=True,\n    title='GDP vs Life Expectancy (2007)',\n)\nfig.show()\n\n# 3D surface\nx = np.linspace(-3, 3, 60)\ny = np.linspace(-3, 3, 60)\nX, Y = np.meshgrid(x, y)\nZ = np.sin(np.sqrt(X**2 + Y**2))\nfig2 = go.Figure(go.Surface(z=Z, x=X, y=Y, colorscale='Viridis'))\nfig2.update_layout(title='3D Surface: sinc function')\nfig2.show()",
                "packages": ["plotly"],
                "links": [("🌐 plotly.com/python", "https://plotly.com/python/")],
            },
            {
                "title": "Requests — HTTP for Humans",
                "body": (
                    "The most downloaded Python package. "
                    "GET, POST, auth, sessions, timeouts — all with a clean API. "
                    "For async HTTP use httpx."
                ),
                "snippet": "import requests\n\n# Simple GET\nr = requests.get('https://httpbin.org/get', params={'q': 'python'})\nprint(r.status_code)   # 200\nprint(r.json())\n\n# POST with JSON body\nr = requests.post('https://httpbin.org/post',\n    json={'name': 'Alice', 'score': 99},\n    headers={'Authorization': 'Bearer mytoken'},\n    timeout=10,\n)\nprint(r.json()['json'])\n\n# Session (reuses TCP connection + cookies)\nwith requests.Session() as s:\n    s.headers['User-Agent'] = 'MyBot/1.0'\n    r1 = s.get('https://httpbin.org/cookies/set?foo=bar')\n    r2 = s.get('https://httpbin.org/cookies')\n    print(r2.json())\n\n# Download a file\nwith requests.get('https://httpbin.org/image/png', stream=True) as r:\n    with open('/tmp/img.png', 'wb') as f:\n        for chunk in r.iter_content(8192):\n            f.write(chunk)",
                "packages": ["requests"],
                "links": [("🌐 docs.python-requests.org", "https://docs.python-requests.org")],
            },
            {
                "title": "Pillow — Image Processing",
                "body": (
                    "Pillow (PIL fork) opens, edits, and saves images. "
                    "Resize, crop, rotate, filter, draw text — all without ImageMagick."
                ),
                "snippet": "from PIL import Image, ImageDraw, ImageFilter\n\nimg = Image.new('RGB', (400, 300), color=(30, 30, 46))\ndraw = ImageDraw.Draw(img)\n\ndraw.ellipse([50, 50, 150, 150], fill=(137, 180, 250))\ndraw.rectangle([200, 80, 350, 200], outline=(166, 227, 161), width=3)\ndraw.line([0, 250, 400, 250], fill=(243, 139, 168), width=2)\ndraw.text((160, 260), 'Hello Pillow!', fill=(205, 214, 244))\n\nblurred = img.filter(ImageFilter.GaussianBlur(radius=2))\n\nimport numpy as np\narr = np.array(img)\nimg2 = Image.fromarray(arr)\n\nthumb = img.copy()\nthumb.thumbnail((200, 150))\nprint(thumb.size)\n\nimg.save('/tmp/demo.png')\nimg.show()",
                "packages": ["Pillow"],
                "links": [("🌐 pillow.readthedocs.io", "https://pillow.readthedocs.io")],
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # Data & Finance
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "finance",
        "icon": "📈",
        "title": "Data & Finance",
        "desc": "yfinance, pandas-ta, Prophet, ARIMA, portfolio analysis",
        "color": "#a6e3a1",
        "topics": [
            {
                "title": "yfinance — Stock & Market Data",
                "body": (
                    "yfinance downloads historical OHLCV data, dividends, splits, "
                    "and company info from Yahoo Finance. "
                    "Free, no API key required."
                ),
                "snippet": "import yfinance as yf\nimport matplotlib.pyplot as plt\n\naapl = yf.download('AAPL', start='2023-01-01', end='2024-01-01', progress=False)\nprint(aapl.tail())\n\n# Multiple tickers\ntickers = yf.download(['AAPL','MSFT','GOOGL'], start='2023-01-01', progress=False)\nclosing = tickers['Close']\n\nnorm = closing / closing.iloc[0] * 100\nnorm.plot(figsize=(10,5), title='Normalized Price (base=100)')\nplt.ylabel('Index'); plt.grid(alpha=0.3); plt.show()\n\n# Company info\ntic = yf.Ticker('AAPL')\ninfo = tic.info\nprint('Market Cap: $' + str(round(info.get('marketCap',0)/1e9, 1)) + 'B')\nprint('P/E Ratio:', info.get('trailingPE','N/A'))",
                "packages": ["yfinance", "matplotlib"],
                "links": [("🌐 github.com/ranaroussi/yfinance", "https://github.com/ranaroussi/yfinance")],
            },
            {
                "title": "Time Series — ARIMA & Forecasting",
                "body": (
                    "ARIMA (AutoRegressive Integrated Moving Average) is the classical "
                    "approach to time series forecasting. "
                    "statsmodels provides ARIMA, SARIMA, and SARIMAX."
                ),
                "snippet": "import pandas as pd\nimport numpy as np\nimport matplotlib.pyplot as plt\nfrom statsmodels.tsa.arima.model import ARIMA\n\nnp.random.seed(42)\ndates = pd.date_range('2020-01', periods=60, freq='ME')\ntrend = np.linspace(100, 200, 60)\nseason = 20 * np.sin(2 * np.pi * np.arange(60) / 12)\nnoise = np.random.normal(0, 5, 60)\nseries = pd.Series(trend + season + noise, index=dates)\n\nmodel = ARIMA(series, order=(1,1,1), seasonal_order=(1,1,1,12))\nresult = model.fit()\n\nforecast = result.get_forecast(steps=12)\nfc = forecast.predicted_mean\nci = forecast.conf_int()\n\nplt.figure(figsize=(12,4))\nplt.plot(series, label='Actual')\nplt.plot(fc, label='Forecast', color='red')\nplt.fill_between(ci.index, ci.iloc[:,0], ci.iloc[:,1], alpha=0.2, color='red')\nplt.title('SARIMA Forecast'); plt.legend(); plt.show()",
                "packages": ["statsmodels", "matplotlib"],
                "links": [("🌐 statsmodels.org", "https://www.statsmodels.org")],
            },
            {
                "title": "Prophet — Facebook's Forecasting Tool",
                "body": (
                    "Prophet handles holidays, seasonality, and missing data automatically. "
                    "Works great for business time series (sales, traffic, demand). "
                    "Requires a DataFrame with ds (date) and y (value) columns."
                ),
                "snippet": "from prophet import Prophet\nimport pandas as pd\nimport numpy as np\nimport matplotlib.pyplot as plt\n\nnp.random.seed(0)\ndates = pd.date_range('2021-01-01', periods=365*2, freq='D')\ntrend = np.linspace(100, 300, len(dates))\nseason_w = 15 * np.sin(2*np.pi*np.arange(len(dates))/7)\nseason_y = 40 * np.sin(2*np.pi*np.arange(len(dates))/365)\nnoise = np.random.normal(0, 8, len(dates))\n\ndf = pd.DataFrame({'ds': dates, 'y': trend + season_w + season_y + noise})\n\nmodel = Prophet(yearly_seasonality=True, weekly_seasonality=True,\n                changepoint_prior_scale=0.05)\nmodel.fit(df)\n\nfuture = model.make_future_dataframe(periods=90)\nforecast = model.predict(future)\n\nmodel.plot(forecast)\nplt.title('Prophet Forecast')\nplt.show()",
                "packages": ["prophet", "matplotlib"],
                "links": [("🌐 facebook.github.io/prophet", "https://facebook.github.io/prophet/")],
            },
            {
                "title": "Portfolio Analysis & Risk Metrics",
                "body": (
                    "Sharpe ratio, drawdown, VaR, correlation — the essential metrics "
                    "for evaluating a portfolio. Pure Python/pandas, no paid data needed."
                ),
                "snippet": "import numpy as np\nimport pandas as pd\nimport yfinance as yf\nimport matplotlib.pyplot as plt\n\ntickers = ['AAPL', 'MSFT', 'BND', 'GLD']\nprices = yf.download(tickers, start='2020-01-01', progress=False)['Close']\nreturns = prices.pct_change().dropna()\n\nweights = np.array([0.25, 0.25, 0.25, 0.25])\nport_ret = returns @ weights\n\nann_ret  = port_ret.mean() * 252\nann_vol  = port_ret.std() * np.sqrt(252)\nsharpe   = ann_ret / ann_vol\n\ncum = (1 + port_ret).cumprod()\nmax_dd = ((cum - cum.cummax()) / cum.cummax()).min()\nvar_95 = np.percentile(port_ret, 5)\n\nprint(f'Annual Return: {ann_ret:.1%}')\nprint(f'Annual Vol:    {ann_vol:.1%}')\nprint(f'Sharpe Ratio:  {sharpe:.2f}')\nprint(f'Max Drawdown:  {max_dd:.1%}')\nprint(f'VaR (95%):     {var_95:.2%} per day')\n\ncum.plot(title='Portfolio Cumulative Return')\nplt.show()",
                "packages": ["yfinance", "matplotlib"],
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # AI / LLM
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "llm",
        "icon": "🤖",
        "title": "AI / LLM",
        "desc": "OpenAI, Ollama, LangChain, HuggingFace, embeddings, RAG",
        "color": "#cba6f7",
        "topics": [
            {
                "title": "OpenAI API — Chat Completions",
                "body": (
                    "The OpenAI Python SDK lets you call GPT-4o, o1, and others. "
                    "Chat completions, streaming, function calling, vision — all in a clean API. "
                    "Set OPENAI_API_KEY in your environment."
                ),
                "snippet": "from openai import OpenAI\n\nclient = OpenAI()  # reads OPENAI_API_KEY from env\n\n# Simple chat\nresponse = client.chat.completions.create(\n    model='gpt-4o-mini',\n    messages=[\n        {'role': 'system', 'content': 'You are a helpful Python tutor.'},\n        {'role': 'user',   'content': 'Explain list comprehensions briefly.'},\n    ],\n    max_tokens=100,\n)\nprint(response.choices[0].message.content)\n\n# Streaming\nstream = client.chat.completions.create(\n    model='gpt-4o-mini',\n    messages=[{'role': 'user', 'content': 'Count to 5.'}],\n    stream=True,\n)\nfor chunk in stream:\n    if chunk.choices[0].delta.content:\n        print(chunk.choices[0].delta.content, end='', flush=True)\nprint()",
                "packages": ["openai"],
                "links": [("🌐 platform.openai.com/docs", "https://platform.openai.com/docs")],
            },
            {
                "title": "Ollama — Run LLMs Locally",
                "body": (
                    "Ollama runs open-source LLMs (Llama 3, Mistral, Phi-3, Gemma) "
                    "locally on your machine — no API key, no cloud, no cost. "
                    "Python SDK mirrors the OpenAI API for easy switching."
                ),
                "snippet": "# First: install Ollama from ollama.com and run:\n# ollama pull llama3.2\n\nimport ollama\n\nresponse = ollama.chat(\n    model='llama3.2',\n    messages=[{'role': 'user', 'content': 'What is a Python decorator?'}],\n)\nprint(response['message']['content'])\n\n# Streaming\nfor chunk in ollama.chat(\n    model='llama3.2',\n    messages=[{'role': 'user', 'content': 'Write a haiku about Python.'}],\n    stream=True,\n):\n    print(chunk['message']['content'], end='', flush=True)\nprint()\n\n# List available models\nmodels = ollama.list()\nfor m in models['models']:\n    size_gb = m.get('size', 0) / 1e9\n    print(m['name'] + ' -- ' + str(round(size_gb, 1)) + ' GB')",
                "packages": ["ollama"],
                "links": [("🌐 ollama.com", "https://ollama.com")],
            },
            {
                "title": "Embeddings & Semantic Search",
                "body": (
                    "Embeddings convert text into vectors. Similar meaning = similar vectors. "
                    "Use sentence-transformers for local embeddings, "
                    "then cosine similarity or a vector DB to find related documents."
                ),
                "snippet": "from sentence_transformers import SentenceTransformer\nimport numpy as np\n\nmodel = SentenceTransformer('all-MiniLM-L6-v2')  # 80MB, runs locally\n\ndocs = [\n    'Python is great for data science.',\n    'Machine learning requires lots of data.',\n    'The Eiffel Tower is in Paris.',\n    'Neural networks are a type of ML model.',\n]\n\nembeddings = model.encode(docs)\nprint('Embedding shape:', embeddings.shape)  # (4, 384)\n\nquery = 'What programming language is good for AI?'\nq_emb = model.encode([query])\n\ndef cosine_sim(a, b):\n    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))\n\nsimilarities = [cosine_sim(q_emb[0], d) for d in embeddings]\nranked = sorted(zip(similarities, docs), reverse=True)\n\nprint('Query:', query)\nfor score, doc in ranked[:3]:\n    print(f'  {score:.3f} -- {doc}')",
                "packages": ["sentence-transformers"],
                "links": [("🌐 sbert.net", "https://www.sbert.net")],
            },
            {
                "title": "RAG — Retrieval Augmented Generation",
                "body": (
                    "RAG grounds LLM answers in your own documents. "
                    "Chunk docs, embed, store in vector DB, retrieve relevant chunks, "
                    "then send to LLM with the question. Reduces hallucination dramatically."
                ),
                "snippet": "from sentence_transformers import SentenceTransformer\nimport numpy as np\n\ndocs = [\n    'Python was created by Guido van Rossum in 1991.',\n    'Python 3.0 was released in December 2008.',\n    'Python is named after Monty Python, not the snake.',\n    'The Zen of Python: Beautiful is better than ugly.',\n    'pip is the package installer for Python.',\n    'Virtual environments isolate project dependencies.',\n]\n\nmodel = SentenceTransformer('all-MiniLM-L6-v2')\ndoc_embs = model.encode(docs)\n\ndef retrieve(query, top_k=2):\n    q_emb = model.encode([query])[0]\n    scores = doc_embs @ q_emb / (\n        np.linalg.norm(doc_embs, axis=1) * np.linalg.norm(q_emb)\n    )\n    idx = np.argsort(scores)[::-1][:top_k]\n    return [docs[i] for i in idx]\n\nquery = 'When was Python created?'\ncontext = retrieve(query)\nprint('Retrieved context:')\nfor c in context:\n    print('  -', c)\n\nprompt = 'Context:\\n' + '\\n'.join(context) + '\\n\\nQuestion: ' + query + '\\nAnswer:'\nprint('\\nPrompt sent to LLM:\\n' + prompt)\n# response = llm.invoke(prompt)  # plug in OpenAI/Ollama here",
                "packages": ["sentence-transformers"],
                "links": [("🌐 huggingface.co/docs/hub/rag", "https://huggingface.co/docs/hub/rag")],
            },
            {
                "title": "HuggingFace Transformers — Local Models",
                "body": (
                    "HuggingFace hosts 500,000+ models. "
                    "transformers library lets you run them locally: "
                    "text generation, classification, NER, summarization, translation."
                ),
                "snippet": "from transformers import pipeline\n\n# Sentiment analysis\nsentiment = pipeline('sentiment-analysis',\n    model='distilbert-base-uncased-finetuned-sst-2-english')\nprint(sentiment('I love using Python for machine learning!'))\n# [{'label': 'POSITIVE', 'score': 0.9998}]\n\n# Text summarization\nsummarizer = pipeline('summarization', model='sshleifer/distilbart-cnn-12-6')\ntext = (\n    'Python is a high-level, general-purpose programming language. '\n    'Its design philosophy emphasizes code readability. '\n    'Python is dynamically typed and supports multiple paradigms.'\n)\nsummary = summarizer(text, max_length=60, min_length=20, do_sample=False)\nprint(summary[0]['summary_text'])\n\n# Named entity recognition\nner = pipeline('ner', grouped_entities=True)\nresult = ner('Guido van Rossum created Python at CWI in Amsterdam.')\nfor entity in result:\n    print(entity['entity_group'].ljust(10), entity['word'])",
                "packages": ["transformers", "torch"],
                "links": [("🌐 huggingface.co", "https://huggingface.co")],
            },
        ],
    },
        ],
    },
]


# ── UI Widgets ─────────────────────────────────────────────────────────────────

class TopicCard(QFrame):
    """Expandable topic card with snippet + links."""

    install_requested = Signal(list)  # list of package names
    bookmark_toggled = Signal(str, bool)  # (topic_title, is_bookmarked)

    def __init__(self, topic: dict, colors: dict, bookmarked: bool = False, parent=None):
        super().__init__(parent)
        self._topic = topic
        self._c = colors
        self._expanded = False
        self._bookmarked = bookmarked
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

        # Description with inline markdown (bold, italic, code, bullets, numbers)
        if self._topic.get("body"):
            body_lbl = QLabel(_md_to_html(self._topic["body"], c))
            body_lbl.setWordWrap(True)
            body_lbl.setTextFormat(Qt.RichText)
            body_lbl.setOpenExternalLinks(True)
            body_lbl.setStyleSheet(
                f"color: {c.get('fg', '#cdd6f4')}; font-size: 15px; "
                "border: none; line-height: 1.6; padding: 2px 0; background: transparent;"
            )
            bl.addWidget(body_lbl)

        # ── Optional: tip / note / warning info callouts ────────────────
        for kind, icon, bg_color, border_color, title_text in (
            ("tip",     "💡", "#1e2a1e", "#a6e3a1", "Tip"),
            ("note",    "ℹ",  "#1e2030", "#89b4fa", "Note"),
            ("warning", "⚠",  "#2a1f1a", "#fab387", "Warning"),
        ):
            text_val = self._topic.get(kind)
            if not text_val:
                continue
            info_frame = QFrame()
            info_frame.setStyleSheet(
                f"QFrame {{ background: {bg_color}; "
                f"border: 1px solid {border_color}; "
                f"border-left: 4px solid {border_color}; "
                f"border-radius: 6px; }}"
            )
            il = QVBoxLayout(info_frame)
            il.setContentsMargins(14, 10, 14, 10)
            il.setSpacing(4)
            title_lbl2 = QLabel(f"{icon}  <b style='color:{border_color};'>{title_text}</b>")
            title_lbl2.setTextFormat(Qt.RichText)
            title_lbl2.setStyleSheet("border: none; font-size: 13px; background: transparent;")
            il.addWidget(title_lbl2)
            text_lbl = QLabel(_md_to_html(text_val, c))
            text_lbl.setTextFormat(Qt.RichText)
            text_lbl.setWordWrap(True)
            text_lbl.setStyleSheet(
                f"color: {c['fg']}; font-size: 13px; border: none; "
                f"background: transparent; line-height: 1.5;"
            )
            il.addWidget(text_lbl)
            bl.addWidget(info_frame)

        # ── Optional: comparison table ──────────────────────────────────
        table_data = self._topic.get("table")
        if isinstance(table_data, dict):
            headers = table_data.get("headers", [])
            rows = table_data.get("rows", [])
            if headers and rows:
                table_frame = QFrame()
                table_frame.setStyleSheet(
                    f"QFrame {{ background: {c.get('input_bg', '#1e1e2e')}; "
                    f"border: 1px solid {c['border']}; border-radius: 6px; }}"
                )
                tl = QVBoxLayout(table_frame)
                tl.setContentsMargins(0, 0, 0, 0)
                tl.setSpacing(0)

                # Header row
                hdr = QFrame()
                hdr.setStyleSheet(
                    f"background: {c['border']}55; border: none; "
                    f"border-bottom: 1px solid {c['border']};"
                )
                hdrl = QHBoxLayout(hdr)
                hdrl.setContentsMargins(12, 7, 12, 7)
                for h in headers:
                    hlbl = QLabel(h)
                    hlbl.setStyleSheet(
                        f"color: {c['accent']}; font-size: 13px; "
                        f"font-weight: bold; border: none; background: transparent;"
                    )
                    hdrl.addWidget(hlbl, 1)
                tl.addWidget(hdr)

                # Data rows (zebra striping)
                for i, row in enumerate(rows):
                    row_frame = QFrame()
                    row_bg = "transparent" if i % 2 == 0 else f"{c['border']}22"
                    row_frame.setStyleSheet(f"background: {row_bg}; border: none;")
                    rl = QHBoxLayout(row_frame)
                    rl.setContentsMargins(12, 6, 12, 6)
                    for cell in row:
                        clbl = QLabel(_md_to_html(str(cell), c))
                        clbl.setTextFormat(Qt.RichText)
                        clbl.setWordWrap(True)
                        clbl.setStyleSheet(
                            f"color: {c['fg']}; font-size: 13px; border: none; "
                            f"background: transparent;"
                        )
                        rl.addWidget(clbl, 1)
                    tl.addWidget(row_frame)
                bl.addWidget(table_frame)

        # ── Optional: ASCII diagram (monospace, preserve whitespace) ─────
        diagram = self._topic.get("diagram")
        if diagram:
            diag_lbl = QLabel(diagram)
            diag_lbl.setFont(QFont("Consolas", 12))
            diag_lbl.setTextFormat(Qt.PlainText)
            diag_lbl.setStyleSheet(
                f"color: {c['fg_muted']}; "
                f"background: {c.get('input_bg', '#1e1e2e')}; "
                f"border: 1px solid {c['border']}; border-radius: 6px; "
                f"padding: 12px; font-family: Consolas, 'Courier New', monospace; "
                f"font-size: 12px;"
            )
            bl.addWidget(diag_lbl)

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
                    line-height: 1.5;
                }}
            """)
            # Apply Python syntax highlighting (only if language is python / unset)
            lang = (self._topic.get("language") or "python").lower()
            if lang == "python" and PythonHighlighter is not None:
                try:
                    self._highlighter = PythonHighlighter(snippet_edit.document())
                except Exception:
                    pass
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

        # Bookmark this button
        self._bm_btn = QPushButton("✅ Bookmarked" if self._bookmarked else "🔖 Bookmark this")
        self._bm_btn.setFixedHeight(28)
        self._bm_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {c['fg_muted']}; "
            f"border: 1px solid {c['border']}; border-radius: 6px; "
            f"font-size: {c['fs_tiny']}px; padding: 0 12px; }}"
            f"QPushButton:hover {{ border-color: {c['accent']}; color: {c['fg']}; }}"
        )
        self._bm_btn.setCursor(Qt.PointingHandCursor)
        self._bm_btn.clicked.connect(self._toggle_bookmark)
        bottom.addWidget(self._bm_btn)

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

    def _toggle_bookmark(self):
        self._bookmarked = not self._bookmarked
        if hasattr(self, '_bm_btn'):
            self._bm_btn.setText("✅ Bookmarked" if self._bookmarked else "🔖 Bookmark this")
        self.bookmark_toggled.emit(self._topic["title"], self._bookmarked)

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
    bookmark_toggled = Signal(str, bool)  # (topic_title, is_bookmarked)

    def __init__(self, category: dict, colors: dict, bookmarks: set = None, parent=None):
        super().__init__(parent)
        self._cat = category
        self._c = colors
        self._bookmarks = bookmarks or set()
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
            is_bm = topic["title"] in self._bookmarks
            card = TopicCard(topic, c, bookmarked=is_bm)
            card.install_requested.connect(self.install_requested)
            card.bookmark_toggled.connect(self.bookmark_toggled)
            layout.addWidget(card)

        layout.addStretch()


class LearnPage(QWidget):
    """Main Learn page — sidebar categories + content area."""

    install_packages_requested = Signal(list)
    bookmark_changed = Signal(list)  # emits full bookmarks list on any change

    def __init__(self, colors_fn, config=None, parent=None):
        super().__init__(parent)
        self._colors_fn = colors_fn
        self._config = config
        _raw = (config.get("bookmarked_topics", []) if config else []) or []
        self._bookmarks = set(_raw)
        self._setup()

    def _on_bookmark_toggled(self, title: str, is_bookmarked: bool):
        if is_bookmarked:
            self._bookmarks.add(title)
        else:
            self._bookmarks.discard(title)
        bm_list = list(self._bookmarks)
        if self._config:
            self._config.set("bookmarked_topics", bm_list)
        self.bookmark_changed.emit(bm_list)

    def _jump_to_topic(self, topic_title: str):
        """Switch to the category containing this topic and expand the card."""
        for i, cat in enumerate(LEARN_CATEGORIES):
            for topic in cat.get("topics", []):
                if topic["title"] == topic_title:
                    self._switch_cat(i)
                    # Find and expand the card after the panel renders
                    from PySide6.QtCore import QTimer
                    QTimer.singleShot(100, lambda t=topic_title: self._expand_topic_card(t))
                    return

    def _expand_topic_card(self, topic_title: str):
        """Find the TopicCard with the given title and expand it."""
        panel = self._stack.currentWidget()
        if not panel:
            return
        # Walk the widget tree to find TopicCard widgets
        for card in panel.findChildren(TopicCard):
            if card._topic.get("title") == topic_title:
                if not card._expanded:
                    card._toggle()
                # Scroll to the card
                scroll_area = panel
                from PySide6.QtCore import QTimer
                QTimer.singleShot(50, lambda c=card, s=scroll_area: self._scroll_to_card(c, s))
                return

    def _scroll_to_card(self, card, scroll_area):
        """Scroll the scroll area to make the card visible."""
        try:
            from PySide6.QtWidgets import QScrollArea
            # Find the QScrollArea parent
            w = scroll_area
            while w:
                if isinstance(w, QScrollArea):
                    pos = card.mapTo(w.widget(), card.rect().topLeft())
                    w.verticalScrollBar().setValue(pos.y() - 20)
                    break
                w = w.parent()
        except Exception:
            pass

    def remove_bookmark(self, title: str):
        """Remove a bookmark externally (called from main_window sidebar)."""
        self._bookmarks.discard(title)
        bm_list = list(self._bookmarks)
        if self._config:
            self._config.set("bookmarked_topics", bm_list)
        self.bookmark_changed.emit(bm_list)

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
            content = CategoryPanel(cat, c, bookmarks=self._bookmarks)
            content.install_requested.connect(self.install_packages_requested)
            content.bookmark_toggled.connect(self._on_bookmark_toggled)
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
