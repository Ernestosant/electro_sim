from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout, QWidget

from electro_sim.physics_engine.types import AngularResult
from electro_sim.ui.plots.angular_plot import AngularPlot


class AngularTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._plot_curves = AngularPlot(self)

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(4, 4, 4, 4)
        main_lay.addWidget(self._plot_curves)

    def on_angular_ready(self, result: AngularResult) -> None:
        self._plot_curves.update_data(result)

    def on_angle_changed(self, angle_deg: float) -> None:
        self._plot_curves.set_current_angle(angle_deg)

    def apply_theme(self, theme: str) -> None:
        self._plot_curves.apply_theme(theme)
