import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
app = QApplication(sys.argv)
from src.gui.main_window import MainWindow
w = MainWindow()
w.show()

def rapor():
    p = w.package_panel
    g = p.launcher_grid
    gorunur = [n for n, c in p.launcher_cards.items() if c.isVisible()]
    print("izgaradaki oge :", g.count())
    print("gorunur kart   :", len(gorunur))
    print("ilk 6          :", gorunur[:6])
    print("son 6          :", gorunur[-6:])
    print("izgara widget  : gorunur =", p.launcher_grid_widget.isVisible(),
          "| yukseklik =", p.launcher_grid_widget.height())
    app.quit()

QTimer.singleShot(9000, rapor)
sys.exit(app.exec())
