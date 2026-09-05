"""VenvStudio - Code Map: what is in a codebase and what talks to what.

B30. Reads a tree of Python files with `ast` and answers the questions that
kept costing this project whole sessions:

    which folders hold which files, and what is each file for
    what does each file define, and what is each definition for
    who imports whom, and who calls whom
    which names are defined MORE THAN ONCE, and have the copies drifted
    which definitions nothing appears to reach
    which class methods shadow a mixin's method of the same name
    which constants hold the same data under two names

Those last four are not decoration. Every one of them is a bug this codebase
actually shipped:

    duplicate + drifted   src/gui/platform_utils.py held ten copies of
                          src/utils/platform_utils.py's functions and five had
                          drifted; a fix written to one never reached the other
    unreached             nine of those eleven functions were imported by
                          nobody at all
    shadowed mixin        settings_editors.py had never run: the class defined
                          the same six methods, and a class's own method beats
                          a mixin's, so a whole feature silently did not exist
    twin constants        _SYNC_CMD and _ENV_CREATE held the same five entries;
                          the Sync button read one and the right-click menu the
                          other

WHAT THIS CANNOT SEE, and why it never says "delete this". Static analysis
misses `getattr(obj, name)()`, Qt signal connections, anything dispatched
through a string, and plugin-style dynamic imports. A Qt slot connected in a
.ui file has no visible caller and is not dead. So the report says "no static
caller found" and leaves the judgement to a person. A confident wrong deletion
would cost more than the duplication it removed.

Qt-free on purpose: this is one of the three starting points B34 names for a
test suite, and it has to run in CI and from a terminal, not only inside a
running application.
"""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

__all__ = ["Definition", "FileInfo", "CodeMap", "scan", "to_markdown"]

# Directories that are never source: they are environments, caches or build
# output, and walking them turns a two-second scan into a two-minute one.
SKIP_DIRS = {
    ".git", ".venv", "venv", "__pycache__", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", ".tox", ".nox", "__pypackages__", ".pixi", "node_modules",
    "build", "dist", ".eggs", "site-packages", ".idea", ".vscode",
}


def _first_line(node) -> str:
    """The first sentence of a docstring, or "" -- this is the 'what for'."""
    doc = ast.get_docstring(node)
    if not doc:
        return ""
    line = doc.strip().splitlines()[0].strip()
    return line


@dataclass
class Definition:
    """One function, method or class."""
    name: str
    kind: str                    # "function" | "method" | "class"
    lineno: int
    end_lineno: int
    doc: str = ""
    owner: str = ""              # class name, for methods
    calls: Set[str] = field(default_factory=set)
    body_hash: str = ""          # normalised source, for drift comparison
    is_private: bool = False
    is_accessor: bool = False    # @property / @x.setter / @overload etc.

    @property
    def lines(self) -> int:
        return self.end_lineno - self.lineno + 1

    @property
    def qualname(self) -> str:
        return f"{self.owner}.{self.name}" if self.owner else self.name


@dataclass
class FileInfo:
    """One Python file."""
    path: str                    # relative, forward slashes
    doc: str = ""
    loc: int = 0
    defs: List[Definition] = field(default_factory=list)
    imports: Set[str] = field(default_factory=set)      # module paths
    imported_names: Set[str] = field(default_factory=set)
    classes: Dict[str, List[str]] = field(default_factory=dict)  # name -> bases
    constants: Dict[str, str] = field(default_factory=dict)      # name -> value

    @property
    def folder(self) -> str:
        return str(Path(self.path).parent).replace("\\", "/")


@dataclass
class CodeMap:
    """The whole reading of one tree."""
    root: str
    files: List[FileInfo] = field(default_factory=list)
    duplicates: List[dict] = field(default_factory=list)
    unreached: List[Tuple[str, str]] = field(default_factory=list)
    shadowed: List[dict] = field(default_factory=list)
    twin_constants: List[dict] = field(default_factory=list)
    errors: List[Tuple[str, str]] = field(default_factory=list)

    @property
    def total_loc(self) -> int:
        return sum(f.loc for f in self.files)

    def by_folder(self) -> Dict[str, List[FileInfo]]:
        out: Dict[str, List[FileInfo]] = {}
        for f in sorted(self.files, key=lambda x: x.path):
            out.setdefault(f.folder, []).append(f)
        return out


class _Reader(ast.NodeVisitor):
    """Walks one module and fills a FileInfo."""

    def __init__(self, info: FileInfo):
        self.info = info
        self._class_stack: List[str] = []

    # -- imports ---------------------------------------------------------
    def visit_Import(self, node: ast.Import):
        for a in node.names:
            self.info.imports.add(a.name)
            self.info.imported_names.add((a.asname or a.name).split(".")[0])

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod = node.module or ""
        if mod:
            self.info.imports.add(mod)
        for a in node.names:
            self.info.imported_names.add(a.asname or a.name)

    # -- definitions -----------------------------------------------------
    def _add_def(self, node, kind: str):
        d = Definition(
            name=node.name,
            kind=kind,
            lineno=node.lineno,
            end_lineno=getattr(node, "end_lineno", node.lineno),
            doc=_first_line(node),
            owner=self._class_stack[-1] if self._class_stack else "",
            is_private=node.name.startswith("_"),
        )
        # A property and its setter are two defs of one name, on purpose.
        # Reporting `PipManager.backend` as "defined twice, and the copies
        # differ" is the report crying wolf about correct code.
        for dec in getattr(node, "decorator_list", []):
            try:
                txt = ast.unparse(dec)
            except Exception:
                continue
            if (txt in ("property", "staticmethod", "classmethod",
                        "cached_property", "functools.cached_property")
                    or txt.endswith((".setter", ".getter", ".deleter",
                                     ".register", ".overload"))
                    or txt in ("overload", "typing.overload",
                               "singledispatch")):
                d.is_accessor = True
        for n in ast.walk(node):
            if isinstance(n, ast.Call):
                f = n.func
                if isinstance(f, ast.Name):
                    d.calls.add(f.id)
                elif isinstance(f, ast.Attribute):
                    # self._foo() and module.foo() both matter; keep the tail
                    d.calls.add(f.attr)
            # A name can be REACHED without being called. `connect(self._foo)`
            # hands the method to Qt, which calls it later; `sorted(key=_k)`
            # and `{"x": _handler}` do the same. Counting only ast.Call
            # reported every slot in the application as unreached -- 47 of
            # them on the first run, which would have made the whole report
            # something to scroll past. References count too.
            elif isinstance(n, ast.Attribute):
                d.calls.add(n.attr)
            elif isinstance(n, ast.Name):
                d.calls.add(n.id)
        try:
            # Normalised source: comments and formatting removed, so two
            # copies that differ only in layout are not reported as drifted.
            d.body_hash = ast.unparse(node)
        except Exception:
            d.body_hash = ""
        self.info.defs.append(d)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._add_def(node, "method" if self._class_stack else "function")
        # Nested definitions are part of their parent, not separate entries.

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef):
        self._add_def(node, "class")
        bases = []
        for b in node.bases:
            try:
                bases.append(ast.unparse(b))
            except Exception:
                pass
        self.info.classes[node.name] = bases
        self._class_stack.append(node.name)
        for child in node.body:
            self.visit(child)
        self._class_stack.pop()

    # -- constants -------------------------------------------------------
    def visit_Assign(self, node: ast.Assign):
        """Record dict/list/tuple constants so twins can be spotted."""
        if not isinstance(node.value, (ast.Dict, ast.List, ast.Tuple, ast.Set)):
            return
        for t in node.targets:
            if isinstance(t, ast.Name):
                try:
                    val = ast.unparse(node.value)
                except Exception:
                    continue
                # Only sizeable literals are interesting; two empty lists
                # being equal says nothing.
                if len(val) >= 40:
                    key = t.id
                    if self._class_stack:
                        key = f"{self._class_stack[-1]}.{t.id}"
                    self.info.constants[key] = val


def _read_file(path: Path, root: Path) -> Optional[FileInfo]:
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    rel = str(path.relative_to(root)).replace("\\", "/")
    info = FileInfo(path=rel, loc=src.count("\n") + 1)
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        info.doc = f"(could not be parsed: line {e.lineno})"
        return info
    info.doc = _first_line(tree)
    _Reader(info).visit(tree)
    return info


def _find_duplicates(cmap: CodeMap):
    """Names defined in more than one file, and whether the copies agree.

    Methods are keyed by class as well as name -- two unrelated classes each
    having a `refresh` is normal and not worth reporting.
    """
    seen: Dict[str, List[Tuple[str, Definition]]] = {}
    for f in cmap.files:
        for d in f.defs:
            if d.is_accessor:
                continue
            if d.name.startswith("__") and d.name.endswith("__"):
                # Two classes of the same name both having __init__ is
                # inevitable, not a finding. Measured on hatch/poetry/pdm,
                # dunders were most of the noise.
                continue
            if d.kind == "method":
                key = f"{d.owner}.{d.name}"
            else:
                key = d.name
            seen.setdefault(key, []).append((f.path, d))
    for key, places in sorted(seen.items()):
        if len(places) < 2:
            continue
        hashes = {d.body_hash for _, d in places}
        cmap.duplicates.append({
            "name": key,
            "kind": places[0][1].kind,
            "places": [(p, d.lineno, d.lines) for p, d in places],
            "identical": len(hashes) == 1,
        })


def _find_unreached(cmap: CodeMap):
    """Definitions nothing in the tree imports or calls by name.

    Deliberately conservative: a name is considered reached if it appears in
    ANY other file's imports, in any call anywhere, or in any constant. Dunder
    methods, `main`, and test functions are never reported.
    """
    imported: Set[str] = set()
    refs: Dict[str, Set[str]] = {}       # name -> the definitions that use it
    literals: List[str] = []
    for f in cmap.files:
        imported |= f.imported_names
        for d in f.defs:
            for c in d.calls:
                refs.setdefault(c, set()).add(f"{f.path}::{d.qualname}")
        literals.extend(f.constants.values())
    blob = " ".join(literals)
    for f in cmap.files:
        for d in f.defs:
            n = d.name
            if n.startswith("__") and n.endswith("__"):
                continue
            if n in ("main", "setup") or n.startswith("test_"):
                continue
            if n in imported:
                continue
            # Its own body does not count: a recursive helper, or a method
            # that mentions its own name, is not thereby reached from outside.
            users = refs.get(n, set()) - {f"{f.path}::{d.qualname}"}
            if users:
                continue
            if n in blob:          # appears inside a string or literal
                continue
            cmap.unreached.append((f.path, d.qualname))


def _calls_super(cmap: CodeMap, cls: str, method: str) -> bool:
    """Does cls.method delegate with super()? Then the override is deliberate."""
    for f in cmap.files:
        for d in f.defs:
            if d.kind == "method" and d.owner == cls and d.name == method:
                return "super" in d.calls
    return False


def _find_shadowed(cmap: CodeMap):
    """A class method that hides a base class's method of the same name.

    This is the settings_editors.py failure: the mixin was listed, the method
    existed in it, and the class's own copy won every time -- so editing the
    mixin changed nothing and no error was ever raised.
    """
    # Where each class's methods live.
    methods: Dict[str, Dict[str, str]] = {}   # class -> {method: file}
    bases_of: Dict[str, List[str]] = {}
    file_of_class: Dict[str, str] = {}
    for f in cmap.files:
        for d in f.defs:
            if d.kind == "method" and d.owner:
                methods.setdefault(d.owner, {})[d.name] = f.path
        for cls, bases in f.classes.items():
            bases_of[cls] = bases
            file_of_class[cls] = f.path

    for cls, bases in bases_of.items():
        own = methods.get(cls, {})
        for base in bases:
            base = base.split("[")[0].split(".")[-1]
            if base not in methods:
                continue
            # Only MIXIN-style composition, and only when super() is not
            # called. An ordinary subclass overriding its parent is normal
            # OOP -- flagging it produced 45/260/120 findings on hatch,
            # poetry and pdm, which is a report nobody reads. The real bug
            # (settings_editors.py) had both marks: the base was a mixin
            # listed alongside others, and the override never delegated, so
            # the mixin's code could not run at all.
            multi = len(bases) > 1
            if not (base.endswith("Mixin") or multi):
                continue
            for m, where in methods[base].items():
                if m in own and not (m.startswith("__") and m.endswith("__")):
                    if _calls_super(cmap, cls, m):
                        continue
                    cmap.shadowed.append({
                        "class": cls,
                        "base": base,
                        "method": m,
                        "class_file": file_of_class.get(cls, ""),
                        "base_file": where,
                    })


def _find_twin_constants(cmap: CodeMap):
    """Two names holding the identical literal -- one of them is redundant."""
    by_value: Dict[str, List[Tuple[str, str]]] = {}
    for f in cmap.files:
        for name, val in f.constants.items():
            by_value.setdefault(val, []).append((f.path, name))
    for val, places in by_value.items():
        if len(places) < 2:
            continue
        names = {n for _, n in places}
        cmap.twin_constants.append({
            "names": sorted(names),
            "places": places,
            "preview": val[:70] + ("..." if len(val) > 70 else ""),
        })


def default_source_dir(version: str = "") -> Path:
    """Where a downloaded copy of the source should go.

    B72. Somewhere the person can actually find and open, so Documents rather
    than a config directory -- the point of downloading it is to read it.
    The version is in the folder name so two downloads never overwrite each
    other and it is obvious which release you are looking at.

    ⚠️ The New Project dialog already resolves Documents (the shell on
    Windows, XDG on Linux, both localised) and this is a SECOND resolver.
    They should be merged into one; this one is deliberately small and in one
    place so the merge is easy when that function is located.
    """
    home = Path.home()
    docs = home / "Documents"
    if os.name == "nt":
        try:
            import ctypes.wintypes as _w
            import ctypes
            buf = ctypes.create_unicode_buffer(_w.MAX_PATH)
            # 0x05 = CSIDL_PERSONAL (Documents), redirected under OneDrive
            if ctypes.windll.shell32.SHGetFolderPathW(
                    None, 5, None, 0, buf) == 0 and buf.value:
                docs = Path(buf.value)
        except Exception:
            pass
    else:
        try:
            import subprocess
            out = subprocess.run(["xdg-user-dir", "DOCUMENTS"],
                                 capture_output=True, text=True, timeout=5)
            if out.returncode == 0 and out.stdout.strip():
                docs = Path(out.stdout.strip())
        except Exception:
            pass
    if not docs.is_dir():
        docs = home
    name = f"venvstudio-v{version}" if version else "venvstudio-source"
    return docs / "vs_source" / name


def fetch_source(version: str = "", dest=None,
                 repo: str = "bayramkotan/VenvStudio",
                 progress=None, force: bool = False) -> Path:
    """Download the project's source and return the folder it landed in.

    B72 (Bayram, 2026-09-05). Someone who installed with `pip install
    venvstudio` has the source on disk -- pip ships .py files -- but it is
    buried in site-packages, read-only, and possibly incomplete, since
    packaging rules need not include everything in the repository. Telling
    that person "clone it from GitHub" assumes they know what cloning is and
    that git is installed, which on a Mac it need not be.

    So this fetches it. A ZIP over https from codeload.github.com rather than
    `git clone`: no git required, one request, and it works the same on all
    three platforms. Tested against the real repository -- a release is about
    26 MB.

    The tag matching the running version is tried FIRST, because a map of
    main would describe code the person is not running. `main` is the
    fallback, and which one was used is reported.

    `progress(done_bytes, total_bytes, message)` is called as it goes; total
    is 0 when the server sends no length.
    """
    import io
    import shutil
    import urllib.error
    import urllib.request
    import zipfile

    dest = Path(dest) if dest else default_source_dir(version)
    if dest.exists() and any(dest.iterdir()) and not force:
        if progress:
            progress(0, 0, f"Already downloaded: {dest}")
        return dest

    refs = []
    if version:
        refs.append((f"tags/v{version}", f"v{version}"))
    refs.append(("heads/main", "main"))

    last = ""
    for ref, label in refs:
        url = f"https://codeload.github.com/{repo}/zip/refs/{ref}"
        try:
            if progress:
                progress(0, 0, f"Downloading {label}…")
            req = urllib.request.Request(
                url, headers={"User-Agent": "VenvStudio"})
            with urllib.request.urlopen(req, timeout=60) as r:
                total = int(r.headers.get("Content-Length") or 0)
                buf = io.BytesIO()
                got = 0
                while True:
                    chunk = r.read(65536)
                    if not chunk:
                        break
                    buf.write(chunk)
                    got += len(chunk)
                    if progress:
                        progress(got, total, f"Downloading {label}…")
        except urllib.error.HTTPError as e:
            last = f"{e.code} for {label}"
            continue                      # tag missing -> try main
        except Exception as e:
            raise RuntimeError(f"Could not download the source: {e}") from e

        if progress:
            progress(got, got, "Unpacking…")
        tmp = dest.parent / (dest.name + ".part")
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(buf) as z:
                z.extractall(tmp)
            # GitHub wraps everything in one folder (VenvStudio-main/);
            # lift its contents up so the path is predictable.
            entries = list(tmp.iterdir())
            root_dir = entries[0] if len(entries) == 1 and entries[0].is_dir() \
                else tmp
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(root_dir), str(dest))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        if progress:
            progress(got, got, f"Source ({label}) is in {dest}")
        return dest

    raise RuntimeError(
        f"Could not download the source ({last or 'no release found'})")


def scan(root, skip_dirs: Optional[Set[str]] = None) -> CodeMap:
    """Read every .py file under `root` and work out what connects to what."""
    root = Path(root).resolve()
    skip = SKIP_DIRS if skip_dirs is None else set(skip_dirs)
    cmap = CodeMap(root=str(root))
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for fn in sorted(filenames):
            if not fn.endswith(".py"):
                continue
            p = Path(dirpath) / fn
            try:
                info = _read_file(p, root)
            except Exception as e:                       # pragma: no cover
                cmap.errors.append((str(p), str(e)))
                continue
            if info:
                cmap.files.append(info)
    _find_duplicates(cmap)
    _find_unreached(cmap)
    _find_shadowed(cmap)
    _find_twin_constants(cmap)
    return cmap


# ── Report ───────────────────────────────────────────────────────────────

def to_markdown(cmap: CodeMap, max_defs: int = 0) -> str:
    """The map as Markdown. `max_defs`: 0 means list every definition."""
    L: List[str] = []
    A = L.append
    A(f"# Code Map — {Path(cmap.root).name}")
    A("")
    A(f"{len(cmap.files)} files · {cmap.total_loc:,} lines · "
      f"{sum(len(f.defs) for f in cmap.files)} definitions")
    A("")

    warn = (len(cmap.duplicates) + len(cmap.unreached)
            + len(cmap.shadowed) + len(cmap.twin_constants))
    if warn:
        A("## What to look at")
        A("")
        A("Nothing here is an error on its own. Static analysis cannot see "
          "`getattr` calls, Qt signal connections or anything dispatched "
          "through a string, so judge each one.")
        A("")

    drifted = [d for d in cmap.duplicates if not d["identical"]]
    same = [d for d in cmap.duplicates if d["identical"]]
    if drifted:
        A(f"### ⚠️ Defined more than once, and the copies DIFFER "
          f"({len(drifted)})")
        A("")
        A("A fix written to one of these does not reach the other.")
        A("")
        for d in drifted:
            where = " · ".join(f"`{p}`:{ln}" for p, ln, _ in d["places"])
            A(f"- **{d['name']}** ({d['kind']}) — {where}")
        A("")
    if same:
        A(f"### Defined more than once, copies identical ({len(same)})")
        A("")
        for d in same:
            where = " · ".join(f"`{p}`:{ln}" for p, ln, _ in d["places"])
            A(f"- **{d['name']}** ({d['kind']}) — {where}")
        A("")

    if cmap.shadowed:
        A(f"### ⚠️ Class method hides a base's method ({len(cmap.shadowed)})")
        A("")
        A("The class's own copy wins. Editing the base changes nothing, and "
          "nothing warns you.")
        A("")
        for s in cmap.shadowed:
            A(f"- `{s['class']}.{s['method']}` in `{s['class_file']}` hides "
              f"`{s['base']}.{s['method']}` in `{s['base_file']}`")
        A("")

    if cmap.twin_constants:
        A(f"### ⚠️ Same data under two names ({len(cmap.twin_constants)})")
        A("")
        for t in cmap.twin_constants:
            where = " · ".join(f"`{p}`:{n}" for p, n in t["places"])
            A(f"- {where}")
            A(f"  - `{t['preview']}`")
        A("")

    if cmap.unreached:
        A(f"### No static caller found ({len(cmap.unreached)})")
        A("")
        A("Possibly dead — or reached by a signal, a `getattr`, or a name "
          "built at runtime. Check before removing anything.")
        A("")
        for path, name in cmap.unreached:
            A(f"- `{path}` — {name}")
        A("")

    A("## The tree")
    A("")
    for folder, files in cmap.by_folder().items():
        A(f"### `{folder}/`")
        A("")
        for f in files:
            A(f"#### `{Path(f.path).name}` — {f.loc:,} lines")
            if f.doc:
                A(f"> {f.doc}")
            A("")
            classes = [d for d in f.defs if d.kind == "class"]
            funcs = [d for d in f.defs if d.kind == "function"]
            for c in classes:
                A(f"- **class {c.name}** — {c.doc or '(no docstring)'}")
                ms = [d for d in f.defs
                      if d.kind == "method" and d.owner == c.name]
                shown = ms if max_defs == 0 else ms[:max_defs]
                for m in shown:
                    A(f"  - `{m.name}()` — {m.doc or '(no docstring)'}")
                if len(ms) > len(shown):
                    A(f"  - … {len(ms) - len(shown)} more")
            for fn in funcs:
                A(f"- `{fn.name}()` — {fn.doc or '(no docstring)'}")
            A("")
    return "\n".join(L)


def _main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(
        prog="code_map",
        description="Map a Python tree: what is where, what calls what, "
                    "and what is defined twice.")
    ap.add_argument("root", nargs="?", default=".",
                    help="folder to scan (default: current directory)")
    ap.add_argument("-o", "--output", default="",
                    help="write Markdown here instead of standard output")
    ap.add_argument("--warnings-only", action="store_true",
                    help="skip the file tree, print only the findings")
    args = ap.parse_args(argv)

    cmap = scan(args.root)
    text = to_markdown(cmap)
    if args.warnings_only and "## The tree" in text:
        text = text.split("## The tree")[0].rstrip() + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"{len(cmap.files)} files, {cmap.total_loc:,} lines "
              f"-> {args.output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
