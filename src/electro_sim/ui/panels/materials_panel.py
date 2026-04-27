from __future__ import annotations

import numpy as np
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from electro_sim.physics_engine.dispersion import MATERIAL_PRESETS, DispersionModel
from electro_sim.physics_engine.types import Medium
from electro_sim.ui.widgets.collapsible_card import CollapsibleCard
from electro_sim.ui.widgets.complex_input import ComplexInput


def _n_to_eps(n_real: float, n_imag: float, mu: complex = 1.0 + 0j) -> complex:
    """ε = (n/√μ)² asumiendo μ ≈ 1 se reduce a ε = n²."""
    n = complex(n_real, n_imag)
    return (n * n) / mu


def _eps_to_n(eps: complex, mu: complex = 1.0 + 0j) -> complex:
    return np.sqrt(eps * mu)


class _MediumBlock(QWidget):
    """Bloque por medio con 3 modos: índice n | ε,μ | preset disperso."""

    changed = pyqtSignal(object, object)  # Medium, Optional[DispersionModel]

    def __init__(
        self,
        title: str,
        default_n: complex = 1.0 + 0j,
        default_preset: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._title = QLabel(title)
        self._title.setProperty("role", "heading")

        # Mode selector (radio horizontal)
        self._mode_group = QButtonGroup(self)
        self._rb_n = QRadioButton("n")
        self._rb_em = QRadioButton("ε, μ")
        self._rb_preset = QRadioButton("Preset")
        self._rb_n.setChecked(True)
        for i, rb in enumerate((self._rb_n, self._rb_em, self._rb_preset)):
            self._mode_group.addButton(rb, i)
            rb.toggled.connect(self._on_mode_toggled)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Modo:"))
        mode_row.addWidget(self._rb_n)
        mode_row.addWidget(self._rb_em)
        mode_row.addWidget(self._rb_preset)
        mode_row.addStretch()

        # --- Stack con 3 páginas ---
        self._stack = QStackedWidget()

        # Página 0: n (Re + Im)
        page_n = QWidget()
        form_n = QFormLayout(page_n)
        self._n_re = self._spin(0.01, 10.0, default_n.real, "", 4, 0.01)
        self._n_im = self._spin(0.0, 20.0, default_n.imag, "", 4, 0.01)
        form_n.addRow("Re(n):", self._n_re)
        form_n.addRow("Im(n) (k):", self._n_im)
        self._n_re.valueChanged.connect(self._emit)
        self._n_im.valueChanged.connect(self._emit)

        # Página 1: ε + μ (complejos)
        page_em = QWidget()
        v_em = QVBoxLayout(page_em)
        v_em.setContentsMargins(0, 0, 0, 0)
        self._eps_input = ComplexInput("ε", complex(default_n.real ** 2, 0))
        self._mu_input = ComplexInput("μ", 1.0 + 0j)
        v_em.addWidget(self._eps_input)
        v_em.addWidget(self._mu_input)
        self._eps_input.value_changed.connect(self._emit)
        self._mu_input.value_changed.connect(self._emit)

        # Página 2: preset disperso
        page_preset = QWidget()
        form_p = QFormLayout(page_preset)
        self._preset = QComboBox()
        for name in MATERIAL_PRESETS:
            self._preset.addItem(name, name)
        if default_preset:
            idx = self._preset.findData(default_preset)
            if idx >= 0:
                self._preset.setCurrentIndex(idx)
        self._preset_info = QLabel()
        self._preset_info.setProperty("role", "muted")
        self._preset_info.setWordWrap(True)
        form_p.addRow("Material:", self._preset)
        form_p.addRow(self._preset_info)
        self._preset.currentIndexChanged.connect(self._emit)

        self._stack.addWidget(page_n)
        self._stack.addWidget(page_em)
        self._stack.addWidget(page_preset)

        # Summary label (derived values)
        self._summary = QLabel()
        self._summary.setProperty("role", "muted")
        self._summary.setWordWrap(True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 8)
        outer.setSpacing(4)
        outer.addWidget(self._title)
        outer.addLayout(mode_row)
        outer.addWidget(self._stack)
        outer.addWidget(self._summary)

    @staticmethod
    def _spin(minimum, maximum, value, suffix, decimals, step) -> QDoubleSpinBox:
        s = QDoubleSpinBox()
        s.setRange(minimum, maximum)
        s.setValue(value)
        s.setSuffix(suffix)
        s.setDecimals(decimals)
        s.setSingleStep(step)
        return s

    # ---- signals / logic ----

    def _on_mode_toggled(self, checked: bool) -> None:
        if not checked:
            return
        idx = self._mode_group.checkedId()
        self._stack.setCurrentIndex(idx)
        # Sync input across modes (so values stay coherent when user swaps)
        if idx == 0:
            n = _eps_to_n(self._eps_input.value(), self._mu_input.value())
            self._n_re.blockSignals(True)
            self._n_im.blockSignals(True)
            self._n_re.setValue(float(n.real))
            self._n_im.setValue(float(abs(n.imag)))
            self._n_re.blockSignals(False)
            self._n_im.blockSignals(False)
        elif idx == 1:
            n = complex(self._n_re.value(), self._n_im.value())
            self._eps_input.blockSignals(True)
            self._mu_input.blockSignals(True)
            self._eps_input.set_value(_n_to_eps(n.real, n.imag))
            self._mu_input.set_value(1.0 + 0j)
            self._eps_input.blockSignals(False)
            self._mu_input.blockSignals(False)
        self._emit()

    def _emit(self) -> None:
        mode = self._mode_group.checkedId()
        dispersive: DispersionModel | None = None
        name = ""

        if mode == 0:  # n
            n = complex(self._n_re.value(), self._n_im.value())
            mu = 1.0 + 0j
            eps = _n_to_eps(n.real, n.imag)
            name = f"n = {n.real:.3f}" + (f" + {n.imag:.3f}i" if n.imag else "")
        elif mode == 1:  # ε, μ
            eps = self._eps_input.value()
            mu = self._mu_input.value()
            name = f"ε={eps.real:.3f}{eps.imag:+.3f}i"
        else:  # preset
            preset_name = self._preset.currentData()
            dispersive = MATERIAL_PRESETS.get(preset_name)
            assert dispersive is not None
            eps = complex(dispersive.epsilon(550.0))
            mu = 1.0 + 0j
            name = preset_name or ""
            n = _eps_to_n(eps, mu)
            self._preset_info.setText(
                f"ε(550 nm) = {eps.real:.3f}{eps.imag:+.3f}i   "
                f"n(550 nm) = {n.real:.3f}{abs(n.imag):+.3f}i"
            )

        self._summary.setText(
            f"n = {_eps_to_n(eps, mu).real:.3f}{_eps_to_n(eps, mu).imag:+.3f}i   "
            f"ε = {eps.real:.3f}{eps.imag:+.3f}i   "
            f"μ = {mu.real:.3f}{mu.imag:+.3f}i"
        )
        self.changed.emit(Medium(eps=eps, mu=mu, name=name), dispersive)


class MaterialsPanel(QWidget):
    medium1_changed = pyqtSignal(object, object)
    medium2_changed = pyqtSignal(object, object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        card = CollapsibleCard("Materiales")

        self._m1 = _MediumBlock(
            title="Medio 1 (incidente)",
            default_n=1.0 + 0j,
            default_preset="Air",
        )
        self._m2 = _MediumBlock(
            title="Medio 2 (transmitido)",
            default_n=1.5 + 0j,
            default_preset="BK7",
        )

        self._m1.changed.connect(self.medium1_changed.emit)
        self._m2.changed.connect(self.medium2_changed.emit)

        card.addWidget(self._m1)
        card.addWidget(self._m2)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(card)
