"""Panel de capas: película simple / multicapa / DBR / AR λ/4 / Fabry-Pérot."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from electro_sim.physics_engine.structures import (
    build_antireflection_quarter,
    build_dbr,
    build_fabry_perot,
)
from electro_sim.physics_engine.types import Layer
from electro_sim.ui.widgets.collapsible_card import CollapsibleCard
from electro_sim.ui.widgets.complex_input import ComplexInput


MAX_MANUAL_THICKNESS_NM = 1_000_000.0


class _LayerItemWidget(QWidget):
    """Fila para una capa personalizada: [n complex] [espesor] [eliminar]."""

    changed = pyqtSignal()
    removed = pyqtSignal()

    def __init__(
        self,
        index: int,
        n: complex = 1.5 + 0j,
        d_nm: float = 100.0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._lbl = QLabel(f"L{index}:")
        self._lbl.setFixedWidth(25)
        self._n_input = ComplexInput("", n, re_range=(0.01, 10.0), im_range=(0.0, 10.0), step=0.01)
        self._d_input = LayersPanel._thickness_spin(d_nm)
        self._d_input.setFixedWidth(120)

        self._btn_del = QPushButton("×")
        self._btn_del.setFixedWidth(25)
        self._btn_del.setToolTip("Eliminar capa")

        layout.addWidget(self._lbl)
        layout.addWidget(self._n_input, stretch=2)
        layout.addWidget(self._d_input, stretch=1)
        layout.addWidget(self._btn_del)

        self._n_input.value_changed.connect(self.changed.emit)
        self._d_input.valueChanged.connect(self.changed.emit)
        self._btn_del.clicked.connect(self.removed.emit)

    def layer(self) -> Layer:
        n = self._n_input.value()
        return Layer(eps=complex(n * n), mu=1.0 + 0j, thickness_nm=self._d_input.value())

    def set_index(self, index: int) -> None:
        self._lbl.setText(f"L{index}:")


class LayersPanel(QWidget):
    layers_changed = pyqtSignal(list)  # list[Layer]
    film_changed = pyqtSignal(float, complex, complex)  # thickness, eps, mu

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        card = CollapsibleCard("Capas / Película")

        self._mode = QComboBox()
        self._mode.addItem("Ninguna", "none")
        self._mode.addItem("Película delgada", "film")
        self._mode.addItem("Personalizado", "custom")
        self._mode.addItem("DBR", "dbr")
        self._mode.addItem("Antirreflectante λ/4", "ar")
        self._mode.addItem("Fabry-Pérot", "fp")
        self._mode.currentIndexChanged.connect(self._on_mode_changed)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_none())
        self._stack.addWidget(self._build_film())
        self._stack.addWidget(self._build_custom())
        self._stack.addWidget(self._build_dbr())
        self._stack.addWidget(self._build_ar())
        self._stack.addWidget(self._build_fp())

        card.addWidget(QLabel("Tipo:"))
        card.addWidget(self._mode)
        card.addWidget(self._stack)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(card)

    # ---- builders ----

    def _build_none(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.addWidget(QLabel("Sin capas — interfaz única."))
        return w

    def _build_film(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self._film_d = self._thickness_spin(120.0)
        self._film_n = ComplexInput(
            "Índice n",
            1.38 + 0j,
            re_range=(0.01, 10.0),
            im_range=(0.0, 10.0),
            step=0.01,
        )
        form.addRow("Espesor d:", self._film_d)
        form.addRow(self._film_n)
        self._film_d.valueChanged.connect(self._emit_film)
        self._film_n.value_changed.connect(self._emit_film)
        return w

    def _build_custom(self) -> QWidget:
        w = QWidget()
        vlay = QVBoxLayout(w)
        vlay.setContentsMargins(0, 4, 0, 4)

        self._layers_list_container = QWidget()
        self._layers_list_layout = QVBoxLayout(self._layers_list_container)
        self._layers_list_layout.setContentsMargins(0, 0, 0, 0)
        self._layers_list_layout.setSpacing(2)
        self._layers_list_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._layers_list_container)
        scroll.setMaximumHeight(200)

        self._btn_add = QPushButton("+ Añadir capa")
        self._btn_add.clicked.connect(self._add_custom_layer)

        vlay.addWidget(scroll)
        vlay.addWidget(self._btn_add)

        self._custom_items: list[_LayerItemWidget] = []
        return w

    def _build_dbr(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self._dbr_nh = self._spin(0.5, 5.0, 2.3, "", 3, 0.01)
        self._dbr_nl = self._spin(0.5, 5.0, 1.45, "", 3, 0.01)
        self._dbr_pairs = QSpinBox()
        self._dbr_pairs.setRange(1, 30)
        self._dbr_pairs.setValue(5)
        self._dbr_wl = self._spin(100.0, 3000.0, 550.0, " nm", 1, 1.0)
        form.addRow("n alto:", self._dbr_nh)
        form.addRow("n bajo:", self._dbr_nl)
        form.addRow("Pares:", self._dbr_pairs)
        form.addRow("λ diseño:", self._dbr_wl)
        for s in (self._dbr_nh, self._dbr_nl, self._dbr_wl):
            s.valueChanged.connect(self._emit_dbr)
        self._dbr_pairs.valueChanged.connect(self._emit_dbr)
        return w

    def _build_ar(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self._ar_n = self._spin(0.5, 5.0, 1.23, "", 3, 0.01)
        self._ar_wl = self._spin(100.0, 3000.0, 550.0, " nm", 1, 1.0)
        form.addRow("n AR:", self._ar_n)
        form.addRow("λ diseño:", self._ar_wl)
        for s in (self._ar_n, self._ar_wl):
            s.valueChanged.connect(self._emit_ar)
        return w

    def _build_fp(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self._fp_nm = self._spin(0.5, 5.0, 2.3, "", 3, 0.01)
        self._fp_nc = self._spin(0.5, 5.0, 1.5, "", 3, 0.01)
        self._fp_pairs = QSpinBox()
        self._fp_pairs.setRange(1, 10)
        self._fp_pairs.setValue(3)
        self._fp_dc = self._thickness_spin(183.0)
        self._fp_wl = self._spin(100.0, 3000.0, 550.0, " nm", 1, 1.0)
        form.addRow("n espejo:", self._fp_nm)
        form.addRow("n cavidad:", self._fp_nc)
        form.addRow("Pares por espejo:", self._fp_pairs)
        form.addRow("d cavidad:", self._fp_dc)
        form.addRow("λ diseño:", self._fp_wl)
        for s in (self._fp_nm, self._fp_nc, self._fp_dc, self._fp_wl):
            s.valueChanged.connect(self._emit_fp)
        self._fp_pairs.valueChanged.connect(self._emit_fp)
        return w

    @staticmethod
    def _spin(
        minimum: float, maximum: float, value: float, suffix: str, decimals: int, step: float
    ) -> QDoubleSpinBox:
        s = QDoubleSpinBox()
        s.setRange(minimum, maximum)
        s.setValue(value)
        s.setSuffix(suffix)
        s.setDecimals(decimals)
        s.setSingleStep(step)
        return s

    @staticmethod
    def _thickness_spin(value: float) -> QDoubleSpinBox:
        s = LayersPanel._spin(0.0, MAX_MANUAL_THICKNESS_NM, value, " nm", 1, 1.0)
        s.setKeyboardTracking(False)
        s.setAccelerated(True)
        s.setMinimumWidth(120)
        return s

    # ---- emitters ----

    def _on_mode_changed(self, idx: int) -> None:
        self._stack.setCurrentIndex(idx)
        self._emit_current()

    def _emit_current(self) -> None:
        mode = self._mode.currentData()
        if mode == "none":
            self.layers_changed.emit([])
            self.film_changed.emit(0.0, 1.0 + 0j, 1.0 + 0j)
        elif mode == "film":
            self._emit_film()
        elif mode == "custom":
            self._emit_custom()
        elif mode == "dbr":
            self._emit_dbr()
        elif mode == "ar":
            self._emit_ar()
        elif mode == "fp":
            self._emit_fp()

    def _add_custom_layer(self) -> None:
        idx = len(self._custom_items) + 1
        item = _LayerItemWidget(idx)
        item.changed.connect(self._emit_custom)
        item.removed.connect(lambda: self._on_custom_layer_removed(item))
        self._layers_list_layout.insertWidget(idx - 1, item)
        self._custom_items.append(item)
        self._emit_custom()

    def _on_custom_layer_removed(self, item: _LayerItemWidget) -> None:
        item.setParent(None)
        self._custom_items.remove(item)
        for i, widget in enumerate(self._custom_items, start=1):
            widget.set_index(i)
        self._emit_custom()

    def _emit_custom(self) -> None:
        layers = [item.layer() for item in self._custom_items]
        self.film_changed.emit(0.0, 1.0 + 0j, 1.0 + 0j)
        self.layers_changed.emit(layers)

    def _emit_film(self) -> None:
        d = self._film_d.value()
        n = self._film_n.value()
        self.layers_changed.emit([])
        self.film_changed.emit(d, complex(n * n), 1.0 + 0j)

    def _emit_dbr(self) -> None:
        layers = build_dbr(
            n_high=self._dbr_nh.value(),
            n_low=self._dbr_nl.value(),
            n_pairs=self._dbr_pairs.value(),
            wavelength_design_nm=self._dbr_wl.value(),
        )
        self.film_changed.emit(0.0, 1.0 + 0j, 1.0 + 0j)
        self.layers_changed.emit(
            [Layer(eps=complex(l["eps"]), mu=complex(l["mu"]), thickness_nm=l["thickness"])
             for l in layers]
        )

    def _emit_ar(self) -> None:
        layers = build_antireflection_quarter(
            n_ar=self._ar_n.value(),
            wavelength_design_nm=self._ar_wl.value(),
        )
        self.film_changed.emit(0.0, 1.0 + 0j, 1.0 + 0j)
        self.layers_changed.emit(
            [Layer(eps=complex(l["eps"]), mu=complex(l["mu"]), thickness_nm=l["thickness"])
             for l in layers]
        )

    def _emit_fp(self) -> None:
        layers = build_fabry_perot(
            n_mirror=self._fp_nm.value(),
            n_cavity=self._fp_nc.value(),
            n_pairs_per_mirror=self._fp_pairs.value(),
            cavity_thickness_nm=self._fp_dc.value(),
            wavelength_design_nm=self._fp_wl.value(),
        )
        self.film_changed.emit(0.0, 1.0 + 0j, 1.0 + 0j)
        self.layers_changed.emit(
            [Layer(eps=complex(l["eps"]), mu=complex(l["mu"]), thickness_nm=l["thickness"])
             for l in layers]
        )
