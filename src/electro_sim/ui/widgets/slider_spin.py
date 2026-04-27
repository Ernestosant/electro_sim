from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class SliderSpin(QWidget):
    """Slider + SpinBox sincronizados con debouncer interno.

    Emite `value_changed(float)` inmediatamente en cada tick (para el label)
    y `value_changed_debounced(float)` tras `debounce_ms` de inactividad.
    Los plots conectan al debounced; labels pueden conectar al inmediato.
    """

    value_changed = pyqtSignal(float)
    value_changed_debounced = pyqtSignal(float)

    def __init__(
        self,
        label: str,
        minimum: float,
        maximum: float,
        value: float,
        step: float = 0.1,
        unit: str = "",
        debounce_ms: int = 80,
        decimals: int = 2,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._min = minimum
        self._max = maximum
        self._step = step
        self._scale = 1.0 / step

        self._label_title = QLabel(f"{label}:")
        self._label_value = QLabel(f"{value:.{decimals}f} {unit}".strip())
        self._label_value.setMinimumWidth(70)
        self._label_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(int(minimum * self._scale), int(maximum * self._scale))
        self._slider.setValue(int(value * self._scale))
        self._slider.setTracking(True)

        self._spin = QDoubleSpinBox()
        self._spin.setRange(minimum, maximum)
        self._spin.setSingleStep(step)
        self._spin.setValue(value)
        self._spin.setDecimals(decimals)
        self._spin.setSuffix(f" {unit}" if unit else "")
        self._spin.setMinimumWidth(95)

        self._unit = unit
        self._decimals = decimals

        header = QHBoxLayout()
        header.addWidget(self._label_title)
        header.addStretch()
        header.addWidget(self._label_value)

        row = QHBoxLayout()
        row.addWidget(self._slider, stretch=1)
        row.addWidget(self._spin)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(2)
        outer.addLayout(header)
        outer.addLayout(row)

        self._debouncer = QTimer(self)
        self._debouncer.setSingleShot(True)
        self._debouncer.setInterval(debounce_ms)
        self._debouncer.timeout.connect(self._emit_debounced)

        self._syncing = False
        self._slider.valueChanged.connect(self._on_slider)
        self._spin.valueChanged.connect(self._on_spin)

    def _on_slider(self, int_value: int) -> None:
        if self._syncing:
            return
        value = int_value / self._scale
        self._syncing = True
        self._spin.setValue(value)
        self._syncing = False
        self._update_label(value)
        self.value_changed.emit(value)
        self._debouncer.start()

    def _on_spin(self, value: float) -> None:
        if self._syncing:
            return
        self._syncing = True
        self._slider.setValue(int(value * self._scale))
        self._syncing = False
        self._update_label(value)
        self.value_changed.emit(value)
        self._debouncer.start()

    def _update_label(self, value: float) -> None:
        text = f"{value:.{self._decimals}f}"
        if self._unit:
            text = f"{text} {self._unit}"
        self._label_value.setText(text)

    def _emit_debounced(self) -> None:
        self.value_changed_debounced.emit(self._spin.value())

    def value(self) -> float:
        return self._spin.value()

    def set_value(self, value: float) -> None:
        self._spin.setValue(value)
