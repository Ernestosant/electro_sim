from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QDoubleSpinBox, QHBoxLayout, QLabel, QWidget


class ComplexInput(QWidget):
    """Par Re + Im para un valor complejo (ε, μ)."""

    value_changed = pyqtSignal(complex)

    def __init__(
        self,
        label: str,
        value: complex = 1.0 + 0j,
        re_range: tuple[float, float] = (0.01, 50.0),
        im_range: tuple[float, float] = (-10.0, 10.0),
        step: float = 0.05,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._label = QLabel(f"{label}:")
        self._re = QDoubleSpinBox()
        self._re.setRange(*re_range)
        self._re.setSingleStep(step)
        self._re.setDecimals(4)
        self._re.setValue(value.real)
        self._re.setPrefix("Re=")

        self._im = QDoubleSpinBox()
        self._im.setRange(*im_range)
        self._im.setSingleStep(step)
        self._im.setDecimals(4)
        self._im.setValue(value.imag)
        self._im.setPrefix("Im=")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self._label)
        layout.addWidget(self._re, stretch=1)
        layout.addWidget(self._im, stretch=1)

        self._re.valueChanged.connect(self._emit)
        self._im.valueChanged.connect(self._emit)

    def _emit(self) -> None:
        self.value_changed.emit(complex(self._re.value(), self._im.value()))

    def value(self) -> complex:
        return complex(self._re.value(), self._im.value())

    def set_value(self, value: complex) -> None:
        self._re.setValue(value.real)
        self._im.setValue(value.imag)
