import sys
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
from src.core.config_manager import ConfigManager
from src.gui.package_panel import PackagePanel
p = PackagePanel(config=ConfigManager())
g = p.launcher_grid
w = p.launcher_grid_widget
print("izgaradaki kart:", g.count())
print("izgara widget yuksekligi   :", w.sizeHint().height())
print("izgara layout yukseklik ipucu:", g.sizeHint().height())
print("ilk kartin yuksekligi        :", list(p.launcher_cards.values())[0].sizeHint().height())
print()
print("beklenen: 9 satir x ~200px = ~1800+, gercek yukarida")
