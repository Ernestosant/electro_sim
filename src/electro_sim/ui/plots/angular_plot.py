"""Plot angular: R, T, A vs θ; |r|, |t| vs θ; φ_r, φ_t vs θ."""

from __future__ import annotations

from typing import Optional

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from electro_sim.physics_engine.types import AngularResult
from electro_sim.ui.plots.base_plot import ThemedPlotWidget
from electro_sim.ui.theme import PLOT_COLORS


_PLOT_CARD_COLORS = {
    "dark": {"background": "#181825", "border": "#313244"},
    "light": {"background": "#e6e9ef", "border": "#ccd0da"},
}
_PLOT_X_PADDING = 0.02


class AngularPlot(QWidget):
    """Matriz 2x2: R/T, absorbancia, amplitud y fase vs θ."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = "dark"
        self._last_result: Optional[AngularResult] = None
        self._plot_cards: list[QFrame] = []

        # --- Panel de información (Ángulos) ---
        self._info_layout = QHBoxLayout()
        self._info_layout.setContentsMargins(2, 0, 10, 0)
        self._info_layout.setSpacing(18)
        self._lbl_brewster = QLabel("Ángulo de Brewster: --")
        self._lbl_critical = QLabel("Ángulo Crítico: --")
        
        font = self._lbl_brewster.font()
        font.setBold(True)
        font.setPointSize(10)
        self._lbl_brewster.setFont(font)
        self._lbl_critical.setFont(font)
        
        self._info_layout.addWidget(self._lbl_brewster)
        self._info_layout.addWidget(self._lbl_critical)
        self._info_layout.addStretch()

        # --- 1. Reflectancia y transmitancia ---
        self._plot_rt = ThemedPlotWidget(title="Reflectancia y Transmitancia")
        self._plot_rt.setLabel("left", "Fracción de potencia")
        self._plot_rt.getAxis("left").enableAutoSIPrefix(False)
        self._plot_rt.setYRange(0, 1.05, padding=0)
        self._plot_rt.getViewBox().setMouseEnabled(y=False)
        self._plot_rt.getViewBox().disableAutoRange(axis=pg.ViewBox.YAxis)
        self._plot_rt.addLegend(offset=(6, 6))
        self._plot_rt.setLabel("bottom", "θᵢ (°)")

        # --- 2. Absorptancia angular ---
        self._plot_absorbance = ThemedPlotWidget(title="Absorbancia")
        self._plot_absorbance.setLabel("left", "Absorptancia")
        self._plot_absorbance.getAxis("left").enableAutoSIPrefix(False)
        self._plot_absorbance.setYRange(0, 1.05, padding=0)
        self._plot_absorbance.getViewBox().setMouseEnabled(y=False)
        self._plot_absorbance.getViewBox().disableAutoRange(axis=pg.ViewBox.YAxis)
        self._plot_absorbance.addLegend(offset=(6, 6))
        self._plot_absorbance.setLabel("bottom", "θᵢ (°)")

        # --- 3. Coeficientes de amplitud ---
        self._plot_amp = ThemedPlotWidget(title="Magnitud de Coeficientes (|r|, |t|)")
        self._plot_amp.setLabel("left", "Magnitud")
        self._plot_amp.setLabel("bottom", "θᵢ (°)")
        self._plot_amp.addLegend(offset=(6, 6))

        # --- 4. Fase (φ_r, φ_t) ---
        self._plot_phase = ThemedPlotWidget(title="Fase de Coeficientes (φ_r, φ_t)")
        self._plot_phase.setLabel("left", "Fase (°)")
        self._plot_phase.setLabel("bottom", "θᵢ (°)")
        self._plot_phase.setYRange(-185, 185, padding=0)
        self._plot_phase.addLegend(offset=(6, 6))

        pen_w = 2
        self._pen_w = pen_w

        # --- Curvas de Potencia ---
        self._curve_R_TE = self._plot_rt.plot([], [], name="R TE")
        self._curve_R_TM = self._plot_rt.plot([], [], name="R TM")
        self._curve_R_unpol = self._plot_rt.plot([], [], name="R Unpol")
        self._curve_T_TE = self._plot_rt.plot([], [], name="T TE")
        self._curve_T_TM = self._plot_rt.plot([], [], name="T TM")
        self._curve_T_unpol = self._plot_rt.plot([], [], name="T Unpol")
        # --- Curvas de Absorptancia ---
        self._curve_A_TE = self._plot_absorbance.plot([], [], name="A TE")
        self._curve_A_TM = self._plot_absorbance.plot([], [], name="A TM")
        self._curve_A_unpol = self._plot_absorbance.plot([], [], name="A Unpol")

        # --- Curvas de Amplitud ---
        self._curve_r_TE = self._plot_amp.plot([], [], name="|r| TE")
        self._curve_r_TM = self._plot_amp.plot([], [], name="|r| TM")
        self._curve_t_TE = self._plot_amp.plot([], [], name="|t| TE")
        self._curve_t_TM = self._plot_amp.plot([], [], name="|t| TM")

        # --- Curvas de Fase ---
        self._curve_phi_r_TE = self._plot_phase.plot([], [], name="φ_r TE")
        self._curve_phi_r_TM = self._plot_phase.plot([], [], name="φ_r TM")
        self._curve_phi_t_TE = self._plot_phase.plot([], [], name="φ_t TE")
        self._curve_phi_t_TM = self._plot_phase.plot([], [], name="φ_t TM")

        # --- Líneas de ángulo actual ---
        self._current_line_rt = pg.InfiniteLine(pos=45.0, angle=90, movable=False)
        self._current_line_absorbance = pg.InfiniteLine(pos=45.0, angle=90, movable=False)
        self._current_line_amp = pg.InfiniteLine(pos=45.0, angle=90, movable=False)
        self._current_line_phase = pg.InfiniteLine(pos=45.0, angle=90, movable=False)
        self._plot_rt.addItem(self._current_line_rt)
        self._plot_absorbance.addItem(self._current_line_absorbance)
        self._plot_amp.addItem(self._current_line_amp)
        self._plot_phase.addItem(self._current_line_phase)

        # Referencias
        self._brewster_lines: list[pg.InfiniteLine] = []
        self._critical_lines: list[pg.InfiniteLine] = []

        self._plot_absorbance.getViewBox().setXLink(self._plot_rt)
        self._plot_amp.getViewBox().setXLink(self._plot_rt)
        self._plot_phase.getViewBox().setXLink(self._plot_rt)

        self._plot_rt_card = self._wrap_plot(self._plot_rt)
        self._plot_absorbance_card = self._wrap_plot(self._plot_absorbance)
        self._plot_amp_card = self._wrap_plot(self._plot_amp)
        self._plot_phase_card = self._wrap_plot(self._plot_phase)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(14)
        top_row.addWidget(self._plot_rt_card, stretch=1)
        top_row.addWidget(self._plot_absorbance_card, stretch=1)

        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        bottom_row.setSpacing(14)
        bottom_row.addWidget(self._plot_amp_card, stretch=1)
        bottom_row.addWidget(self._plot_phase_card, stretch=1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 16, 10)
        layout.setSpacing(16)
        layout.addLayout(self._info_layout)
        layout.addLayout(top_row, stretch=1)
        layout.addLayout(bottom_row, stretch=1)

        # Configurar menús de visibilidad
        self._setup_visibility_menus()

        self.apply_theme("dark")

    def _wrap_plot(self, plot: ThemedPlotWidget) -> QFrame:
        card = QFrame(self)
        card.setObjectName("angularPlotCard")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        plot.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        inner = QVBoxLayout(card)
        inner.setContentsMargins(10, 10, 12, 10)
        inner.setSpacing(0)
        inner.addWidget(plot)

        self._plot_cards.append(card)
        return card

    def _apply_plot_card_theme(self, theme: str) -> None:
        colors = _PLOT_CARD_COLORS[theme]
        style = (
            "QFrame#angularPlotCard {"
            f"background-color: {colors['background']};"
            f"border: 1px solid {colors['border']};"
            "border-radius: 10px;"
            "}"
        )
        for card in self._plot_cards:
            card.setStyleSheet(style)

    def _setup_visibility_menus(self) -> None:
        """Agrega acciones checkeables al menú contextual de cada plot."""
        def add_toggles(plot_widget: pg.PlotWidget, curves_dict: dict[str, pg.PlotDataItem]) -> None:
            menu = plot_widget.plotItem.vb.menu
            # Creamos un submenú para las curvas
            visibility_menu = menu.addMenu("Mostrar/Ocultar Curvas")
            for name, curve in curves_dict.items():
                action = QAction(name, visibility_menu)
                action.setCheckable(True)
                action.setChecked(True)
                # Al cambiar, actualizamos la visibilidad
                action.toggled.connect(curve.setVisible)
                visibility_menu.addAction(action)

        # Diccionarios de curvas
        curves_rt = {
            "Reflectancia TE": self._curve_R_TE,
            "Reflectancia TM": self._curve_R_TM,
            "Reflectancia Unpol": self._curve_R_unpol,
            "Transmitancia TE": self._curve_T_TE,
            "Transmitancia TM": self._curve_T_TM,
            "Transmitancia Unpol": self._curve_T_unpol,
        }
        curves_absorbance = {
            "Absorptancia TE": self._curve_A_TE,
            "Absorptancia TM": self._curve_A_TM,
            "Absorptancia Unpol": self._curve_A_unpol,
        }
        curves_amp = {
            "|r| TE": self._curve_r_TE,
            "|r| TM": self._curve_r_TM,
            "|t| TE": self._curve_t_TE,
            "|t| TM": self._curve_t_TM,
        }
        curves_phase = {
            "φ_r TE": self._curve_phi_r_TE,
            "φ_r TM": self._curve_phi_r_TM,
            "φ_t TE": self._curve_phi_t_TE,
            "φ_t TM": self._curve_phi_t_TM,
        }

        add_toggles(self._plot_rt, curves_rt)
        add_toggles(self._plot_absorbance, curves_absorbance)
        add_toggles(self._plot_amp, curves_amp)
        add_toggles(self._plot_phase, curves_phase)

    # ---- themed rendering ----

    def apply_theme(self, theme: str) -> None:
        self._theme = theme
        self._plot_rt.apply_theme(theme)
        self._plot_absorbance.apply_theme(theme)
        self._plot_amp.apply_theme(theme)
        self._plot_phase.apply_theme(theme)
        colors = PLOT_COLORS[theme]
        w = self._pen_w

        self._lbl_brewster.setStyleSheet(f"color: {colors['brewster']};")
        self._lbl_critical.setStyleSheet(f"color: {colors['critical']};")
        self._apply_plot_card_theme(theme)

        # Potencia
        self._curve_R_TE.setPen(pg.mkPen(colors["TE"], width=w))
        self._curve_R_TM.setPen(pg.mkPen(colors["TM"], width=w))
        self._curve_R_unpol.setPen(pg.mkPen(colors["unpol"], width=w, style=Qt.PenStyle.SolidLine))
        self._curve_T_TE.setPen(pg.mkPen(colors["TE"], width=w, style=Qt.PenStyle.DashLine))
        self._curve_T_TM.setPen(pg.mkPen(colors["TM"], width=w, style=Qt.PenStyle.DashLine))
        self._curve_T_unpol.setPen(pg.mkPen(colors["unpol"], width=w, style=Qt.PenStyle.DashLine))
        self._curve_A_TE.setPen(pg.mkPen(colors["TE"], width=w))
        self._curve_A_TM.setPen(pg.mkPen(colors["TM"], width=w))
        self._curve_A_unpol.setPen(pg.mkPen(colors["unpol"], width=w, style=Qt.PenStyle.DashLine))

        # Amplitud
        self._curve_r_TE.setPen(pg.mkPen(colors["TE"], width=w))
        self._curve_r_TM.setPen(pg.mkPen(colors["TM"], width=w))
        self._curve_t_TE.setPen(pg.mkPen(colors["TE"], width=w, style=Qt.PenStyle.DashLine))
        self._curve_t_TM.setPen(pg.mkPen(colors["TM"], width=w, style=Qt.PenStyle.DashLine))

        # Fase
        self._curve_phi_r_TE.setPen(pg.mkPen(colors["TE"], width=w))
        self._curve_phi_r_TM.setPen(pg.mkPen(colors["TM"], width=w))
        self._curve_phi_t_TE.setPen(pg.mkPen(colors["TE"], width=w, style=Qt.PenStyle.DashLine))
        self._curve_phi_t_TM.setPen(pg.mkPen(colors["TM"], width=w, style=Qt.PenStyle.DashLine))

        current_pen = pg.mkPen(colors["current"], width=1.5, style=Qt.PenStyle.DotLine)
        self._current_line_rt.setPen(current_pen)
        self._current_line_absorbance.setPen(current_pen)
        self._current_line_amp.setPen(current_pen)
        self._current_line_phase.setPen(current_pen)

        if self._last_result is not None:
            self._redraw_reference_lines(self._last_result)

    # ---- data ----

    def update_data(self, result: AngularResult) -> None:
        self._last_result = result
        a = result.angles_deg
        
        if result.brewster_deg is not None:
            self._lbl_brewster.setText(f"Ángulo de Brewster: {result.brewster_deg:.2f}°")
        else:
            self._lbl_brewster.setText("Ángulo de Brewster: N/A")
            
        if result.critical_deg is not None:
            self._lbl_critical.setText(f"Ángulo Crítico: {result.critical_deg:.2f}°")
        else:
            self._lbl_critical.setText("Ángulo Crítico: N/A")
        
        # Potencia
        self._curve_R_TE.setData(a, result.R_TE)
        self._curve_R_TM.setData(a, result.R_TM)
        self._curve_R_unpol.setData(a, result.R_unpol)
        self._curve_T_TE.setData(a, result.T_TE)
        self._curve_T_TM.setData(a, result.T_TM)
        self._curve_T_unpol.setData(a, result.T_unpol)

        # Absorptancia
        self._curve_A_TE.setData(a, result.A_TE)
        self._curve_A_TM.setData(a, result.A_TM)
        self._curve_A_unpol.setData(a, result.A_unpol)

        # Amplitud
        self._curve_r_TE.setData(a, np.abs(result.r_TE))
        self._curve_r_TM.setData(a, np.abs(result.r_TM))
        self._curve_t_TE.setData(a, np.abs(result.t_TE))
        self._curve_t_TM.setData(a, np.abs(result.t_TM))

        # Fase
        self._curve_phi_r_TE.setData(a, result.phi_r_TE)
        self._curve_phi_r_TM.setData(a, result.phi_r_TM)
        self._curve_phi_t_TE.setData(a, result.phi_t_TE)
        self._curve_phi_t_TM.setData(a, result.phi_t_TM)

        if a.size:
            self._plot_rt.setXRange(float(a[0]), float(a[-1]), padding=_PLOT_X_PADDING)

        self._redraw_reference_lines(result)

    def _redraw_reference_lines(self, result: AngularResult) -> None:
        colors = PLOT_COLORS[self._theme]
        
        # Limpiar anteriores
        for p in [self._plot_rt, self._plot_absorbance, self._plot_amp, self._plot_phase]:
            p.clear_reference_lines()
        
        self._brewster_lines.clear()
        self._critical_lines.clear()

        plots = [self._plot_rt, self._plot_absorbance, self._plot_amp, self._plot_phase]

        if result.brewster_deg is not None:
            for p in plots:
                line = p.add_reference_line(
                    x=result.brewster_deg,
                    label=None,
                    color=colors["brewster"],
                )
                self._brewster_lines.append(line)
                
        if result.critical_deg is not None:
            for p in plots:
                line = p.add_reference_line(
                    x=result.critical_deg,
                    label=None,
                    color=colors["critical"],
                )
                self._critical_lines.append(line)

    def set_current_angle(self, angle_deg: float) -> None:
        self._current_line_rt.setValue(angle_deg)
        self._current_line_absorbance.setValue(angle_deg)
        self._current_line_amp.setValue(angle_deg)
        self._current_line_phase.setValue(angle_deg)
