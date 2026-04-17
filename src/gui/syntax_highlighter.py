"""
syntax_highlighter.py — Python code syntax highlighter for QTextEdit.
Simple regex-based highlighter with Catppuccin-ish palette.
"""
from __future__ import annotations
import re
from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QColor, QFont,
)


class PythonHighlighter(QSyntaxHighlighter):
    """Regex-based Python syntax highlighter.

    Covers keywords, builtins, numbers, strings (single + triple-quoted),
    comments, decorators, function names, and class names. Good enough
    for learning material (not a full parser).
    """

    # Catppuccin Mocha palette
    COLORS = {
        "keyword":   "#cba6f7",  # mauve — if, def, class, return
        "builtin":   "#89b4fa",  # blue — print, len, range
        "string":    "#a6e3a1",  # green
        "number":    "#fab387",  # peach
        "comment":   "#6c7086",  # overlay0 — dim gray
        "decorator": "#f9e2af",  # yellow — @staticmethod
        "func_def":  "#89b4fa",  # blue — def NAME
        "class_def": "#f38ba8",  # pink — class NAME
        "operator":  "#94e2d5",  # teal — +, -, =, ==
        "self":      "#f5c2e7",  # pink-ish — self, cls
    }

    KEYWORDS = [
        "and", "as", "assert", "async", "await", "break", "class",
        "continue", "def", "del", "elif", "else", "except", "finally",
        "for", "from", "global", "if", "import", "in", "is", "lambda",
        "nonlocal", "not", "or", "pass", "raise", "return", "try",
        "while", "with", "yield", "True", "False", "None", "match", "case",
    ]

    BUILTINS = [
        "abs", "all", "any", "ascii", "bin", "bool", "bytearray", "bytes",
        "callable", "chr", "classmethod", "compile", "complex", "delattr",
        "dict", "dir", "divmod", "enumerate", "eval", "exec", "filter",
        "float", "format", "frozenset", "getattr", "globals", "hasattr",
        "hash", "help", "hex", "id", "input", "int", "isinstance",
        "issubclass", "iter", "len", "list", "locals", "map", "max",
        "memoryview", "min", "next", "object", "oct", "open", "ord",
        "pow", "print", "property", "range", "repr", "reversed", "round",
        "set", "setattr", "slice", "sorted", "staticmethod", "str", "sum",
        "super", "tuple", "type", "vars", "zip", "__import__",
    ]

    def __init__(self, document):
        super().__init__(document)
        self._rules: list = []
        self._build_rules()

    def _fmt(self, color_key: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(self.COLORS[color_key]))
        if bold:
            fmt.setFontWeight(QFont.Bold)
        if italic:
            fmt.setFontItalic(True)
        return fmt

    def _build_rules(self):
        # Keywords (bold)
        kw_fmt = self._fmt("keyword", bold=True)
        kw_pattern = r"\b(" + "|".join(self.KEYWORDS) + r")\b"
        self._rules.append((re.compile(kw_pattern), kw_fmt))

        # Builtins
        bi_fmt = self._fmt("builtin")
        bi_pattern = r"\b(" + "|".join(self.BUILTINS) + r")\b"
        self._rules.append((re.compile(bi_pattern), bi_fmt))

        # self / cls
        self._rules.append((re.compile(r"\b(self|cls)\b"), self._fmt("self", italic=True)))

        # Function definitions: def NAME
        self._rules.append(
            (re.compile(r"\bdef\s+([A-Za-z_]\w*)"), self._fmt("func_def", bold=True), 1)
        )
        # Class definitions: class NAME
        self._rules.append(
            (re.compile(r"\bclass\s+([A-Za-z_]\w*)"), self._fmt("class_def", bold=True), 1)
        )

        # Decorators: @name
        self._rules.append((re.compile(r"@[A-Za-z_]\w*"), self._fmt("decorator")))

        # Numbers: 42, 3.14, 1e10, 0x1F, 0b10
        self._rules.append((
            re.compile(r"\b(0x[0-9a-fA-F]+|0b[01]+|\d+\.?\d*([eE][+-]?\d+)?)\b"),
            self._fmt("number"),
        ))

        # Strings (single-line, both quote styles, handles escapes)
        self._rules.append((re.compile(r'"(?:\\.|[^"\\])*"'), self._fmt("string")))
        self._rules.append((re.compile(r"'(?:\\.|[^'\\])*'"), self._fmt("string")))

        # Comments (# ...) — must be after strings so # inside string isn't matched
        self._rules.append((re.compile(r"#[^\n]*"), self._fmt("comment", italic=True)))

    def highlightBlock(self, text: str):
        for rule in self._rules:
            if len(rule) == 2:
                pattern, fmt = rule
                for m in pattern.finditer(text):
                    self.setFormat(m.start(), m.end() - m.start(), fmt)
            else:
                pattern, fmt, group = rule
                for m in pattern.finditer(text):
                    start = m.start(group)
                    length = m.end(group) - start
                    self.setFormat(start, length, fmt)

        # Multi-line triple-quoted strings are tricky — we handle them with
        # block state tracking.
        self._handle_triple_strings(text)

    def _handle_triple_strings(self, text: str):
        """Support triple-quoted strings that span multiple lines."""
        string_fmt = self._fmt("string")
        self.setCurrentBlockState(0)

        # Handle """
        in_triple_d = self.previousBlockState() == 1
        start = 0
        while start < len(text):
            if in_triple_d:
                end = text.find('"""', start)
                if end == -1:
                    self.setFormat(start, len(text) - start, string_fmt)
                    self.setCurrentBlockState(1)
                    return
                self.setFormat(start, end - start + 3, string_fmt)
                start = end + 3
                in_triple_d = False
            else:
                pos = text.find('"""', start)
                if pos == -1:
                    break
                self.setFormat(pos, 3, string_fmt)
                start = pos + 3
                in_triple_d = True
        if in_triple_d:
            self.setCurrentBlockState(1)
