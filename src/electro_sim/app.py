from __future__ import annotations

from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QApplication

from electro_sim import __version__
from electro_sim.ui.main_window import MainWindow


def create_app(argv: list[str]) -> tuple[QApplication, MainWindow]:
    QCoreApplication.setOrganizationName("electro_sim")
    QCoreApplication.setApplicationName("electro_sim")
    QCoreApplication.setApplicationVersion(__version__)

    app = QApplication(argv)
    window = MainWindow()
    return app, window
