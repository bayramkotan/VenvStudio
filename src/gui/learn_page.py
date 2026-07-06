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

from src.gui.learn_content import LEARN_CATEGORIES


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
        # B183: bg colours were hardcoded for the dark Catppuccin Mocha
        # theme (deep greens/blues/oranges) which look out of place on a
        # light background. Pick a translucent tint of the border colour
        # instead — works for both light and dark themes because the
        # alpha channel keeps it subtle either way.
        for kind, icon, border_color, title_text in (
            ("tip",     "💡", c.get("success", "#a6e3a1"), "Tip"),
            ("note",    "ℹ",  c.get("info",    c.get("accent", "#89b4fa")), "Note"),
            ("warning", "⚠",  c.get("warning", "#fab387"), "Warning"),
        ):
            text_val = self._topic.get(kind)
            if not text_val:
                continue
            # 22 alpha hex ≈ ~13% opacity — a soft tinted background
            # that reads as "tip green / note blue / warning orange"
            # on top of any theme.
            bg_color = f"{border_color}22"
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
            # B183: previously hardcoded Catppuccin Mocha colours (#11111b
            # and #181825) regardless of theme. Now picks the deepest
            # background ('input_bg') and a slightly lighter shade
            # ('card' or 'secondary') from the active palette so light
            # themes get a light code block.
            code_bg   = c.get("input_bg", "#11111b")
            header_bg = c.get("card", c.get("secondary", "#181825"))
            snippet_frame = QFrame()
            snippet_frame.setStyleSheet(f"""
                QFrame {{
                    background: {code_bg};
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
                f"background: {header_bg}; border: none; "
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
            # B183: snippet text colour was hardcoded #cdd6f4 (Catppuccin
            # Mocha foreground), invisible on light themes. Use palette
            # 'fg' so it matches whatever theme is active.
            snippet_edit.setStyleSheet(f"""
                QTextEdit {{
                    background: transparent;
                    color: {c['fg']};
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
        # B183: snapshot current palette so the next apply_theme call knows
        # which colours to swap out of inline stylesheets across the entire
        # Learn page (sidebar, topic cards, category panels, code blocks).
        try:
            self._last_palette = {k: v for k, v in colors_fn().items()
                                  if isinstance(v, str) and v.startswith("#")}
        except Exception:
            self._last_palette = None
        self._setup()

    def apply_theme(self, theme: str = None):
        """Re-apply theme across the Learn page.

        Strategy: generic palette sweep (B183). Walk every child widget,
        and for any inline stylesheet that contains a colour string from
        the *previous* palette, replace it with the matching colour from
        the *new* palette. No hardcoded widget list — this picks up new
        cards, panels and labels automatically.
        """
        try:
            from PySide6.QtWidgets import QWidget
            new_palette = self._colors_fn() if callable(self._colors_fn) else {}
            old_palette = getattr(self, "_last_palette", None) or {}
            replacements = []
            for k, v_old in old_palette.items():
                if not (isinstance(v_old, str) and v_old.startswith("#")):
                    continue
                v_new = new_palette.get(k)
                if isinstance(v_new, str) and v_new and v_new != v_old:
                    replacements.append((v_old.lower(), v_new))
                    replacements.append((v_old.upper(), v_new))
            if replacements:
                for w in self.findChildren(QWidget):
                    try:
                        ss = w.styleSheet()
                        if not ss:
                            continue
                        new_ss = ss
                        changed = False
                        for v_old, v_new in replacements:
                            if v_old in new_ss:
                                new_ss = new_ss.replace(v_old, v_new)
                                changed = True
                        if changed:
                            w.setStyleSheet(new_ss)
                    except RuntimeError:
                        pass
            # Also refresh the Learn page itself
            try:
                ss = self.styleSheet()
                if ss:
                    new_ss = ss
                    for v_old, v_new in replacements:
                        new_ss = new_ss.replace(v_old, v_new)
                    if new_ss != ss:
                        self.setStyleSheet(new_ss)
            except Exception:
                pass
            # Update the snapshot for the next switch
            self._last_palette = {k: v for k, v in new_palette.items()
                                  if isinstance(v, str) and v.startswith("#")}
        except Exception:
            pass

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
