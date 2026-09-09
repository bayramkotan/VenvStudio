import sys
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
from src.core.config_manager import ConfigManager
from src.gui.package_panel import PackagePanel
p = PackagePanel(config=ConfigManager())
print("app_definitions      :", len(p.app_definitions))
print("izgaraya giren       :", len(getattr(p, "launcher_grid_apps", [])))
print("uretilen kart        :", len(p.launcher_cards))
for a in ("Prefect", "Evidently", "Notebook (classic)"):
    print(f"  {a:20}", "kart VAR" if a in p.launcher_cards else "kart YOK")
