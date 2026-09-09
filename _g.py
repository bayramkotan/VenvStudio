import sys
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
from src.core.config_manager import ConfigManager
from src.gui.package_panel import PackagePanel
p = PackagePanel(config=ConfigManager())

g = p.launcher_grid
print("ILK KURULUM sonrasi:")
print("  izgaradaki oge:", g.count(), "| satir:", g.rowCount(), "| sutun:", g.columnCount())

# env degisimini taklit et
import inspect
fn = getattr(p, "_on_env_selector_changed", None)
print("  _on_env_selector_changed var mi:", bool(fn))

print()
print("izgara hucreleri:")
for r in range(g.rowCount()):
    satir = []
    for c in range(g.columnCount()):
        it = g.itemAtPosition(r, c)
        w = it.widget() if it else None
        satir.append("--" if w is None else ("gizli" if not w.isVisible() else "VAR"))
    print(f"  {r}: {satir}")
