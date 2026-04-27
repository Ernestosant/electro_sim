import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from electro_sim.app import MainWindow

app = QApplication(sys.argv)
window = MainWindow()
window.show()

def take_screenshot():
    # Force process events
    app.processEvents()
    # Grab window
    pixmap = window.grab()
    pixmap.save("debug_screenshot.png")
    # Close
    window.close()
    app.quit()

QTimer.singleShot(2000, take_screenshot)
sys.exit(app.exec())
