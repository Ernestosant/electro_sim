from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from electro_sim.ui.widgets.collapsible_card import CollapsibleCard
from electro_sim.ui.widgets.slider_spin import SliderSpin


class SourcePanel(QWidget):
    wavelength_changed = pyqtSignal(float)
    angle_changed = pyqtSignal(float)
    polarization_changed = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        card = CollapsibleCard("Fuente")

        self._lambda = SliderSpin(
            label="Longitud de onda λ₀",
            minimum=200.0,
            maximum=2000.0,
            value=550.0,
            step=1.0,
            unit="nm",
            debounce_ms=80,
            decimals=1,
        )
        self._lambda.value_changed_debounced.connect(self.wavelength_changed.emit)

        self._theta = SliderSpin(
            label="Ángulo de incidencia θᵢ",
            minimum=0.0,
            maximum=89.9,
            value=45.0,
            step=0.1,
            unit="°",
            debounce_ms=40,
            decimals=2,
        )
        self._theta.value_changed.connect(self.angle_changed.emit)

        pol_box = QWidget()
        pol_row = QHBoxLayout(pol_box)
        pol_row.setContentsMargins(0, 4, 0, 4)
        self._pol_group = QButtonGroup(self)
        for i, (label, value) in enumerate([
            ("Ambas", "both"),
            ("TE", "TE"),
            ("TM", "TM"),
            ("Unpol", "unpolarized"),
        ]):
            btn = QRadioButton(label)
            btn.setProperty("pol", value)
            if i == 0:
                btn.setChecked(True)
            self._pol_group.addButton(btn, i)
            pol_row.addWidget(btn)
            btn.toggled.connect(self._on_pol_changed)

        card.addWidget(self._lambda)
        card.addWidget(self._theta)
        card.addWidget(pol_box)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(card)

    def _on_pol_changed(self, checked: bool) -> None:
        if not checked:
            return
        btn = self._pol_group.checkedButton()
        if btn is None:
            return
        self.polarization_changed.emit(btn.property("pol"))

    def wavelength(self) -> float:
        return self._lambda.value()

    def angle(self) -> float:
        return self._theta.value()

    def polarization(self) -> str:
        btn = self._pol_group.checkedButton()
        return btn.property("pol") if btn else "both"
