import sys
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
from src.core.config_manager import ConfigManager
from src.gui.package_panel import PackagePanel
p = PackagePanel(config=ConfigManager())

env_type = "conda"
match = {"venv", "conda"}
visible = [a for a in p.app_definitions
           if match & set(a.get("env_types",
               ["venv"] if not a.get("system_app") else ["conda", "system_tools"]))]
print("visible_apps:", len(visible))
print([a["name"] for a in visible])
print()
eksik = [a["name"] for a in visible if a["name"] not in p.launcher_cards]
print("karti olmayan:", eksik)
