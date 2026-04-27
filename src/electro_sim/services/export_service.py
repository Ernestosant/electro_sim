"""Export de plots pyqtgraph a PNG/SVG y de arrays a CSV."""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
import pyqtgraph.exporters  # noqa: F401 - registra exporters
from PyQt6.QtWidgets import QFileDialog, QWidget

from electro_sim.physics_engine.types import (
    AngularResult,
    HeatmapResult,
    SpectralResult,
    ThicknessResult,
)


def export_plot_png(plot_item: pg.PlotItem | pg.PlotWidget, path: str) -> None:
    if isinstance(plot_item, pg.PlotWidget):
        plot_item = plot_item.getPlotItem()
    exporter = pg.exporters.ImageExporter(plot_item)
    exporter.parameters()["width"] = 1600
    exporter.export(path)


def export_plot_svg(plot_item: pg.PlotItem | pg.PlotWidget, path: str) -> None:
    if isinstance(plot_item, pg.PlotWidget):
        plot_item = plot_item.getPlotItem()
    exporter = pg.exporters.SVGExporter(plot_item)
    exporter.export(path)


def export_angular_csv(result: AngularResult, path: str) -> None:
    header = (
        "angle_deg,R_TE,R_TM,R_unpol,T_TE,T_TM,T_unpol,"
        "Absorptance_TE,Absorptance_TM,Absorptance_unpol,abs_r_TE,abs_r_TM,phi_r_TE_deg,phi_r_TM_deg"
    )
    data = np.column_stack([
        result.angles_deg,
        result.R_TE, result.R_TM, result.R_unpol,
        result.T_TE, result.T_TM, result.T_unpol,
        result.A_TE, result.A_TM, result.A_unpol,
        np.abs(result.r_TE), np.abs(result.r_TM),
        result.phi_r_TE, result.phi_r_TM,
    ])
    np.savetxt(path, data, delimiter=",", header=header, comments="")


def export_spectral_csv(result: SpectralResult, path: str) -> None:
    header = "wavelength_nm,R_TE,R_TM,R_unpol,T_TE,T_TM,T_unpol,Absorptance_TE,Absorptance_TM"
    data = np.column_stack([
        result.wavelengths_nm,
        result.R_TE, result.R_TM, result.R_unpol,
        result.T_TE, result.T_TM, result.T_unpol,
        result.A_TE, result.A_TM,
    ])
    np.savetxt(path, data, delimiter=",", header=header, comments="")


def export_heatmap_csv(result: HeatmapResult, path: str, channel: str = "R_unpol") -> None:
    data = getattr(result, channel)
    # Formato: primera fila = θ, primera columna = λ, resto = data
    header = ["wavelength_nm"] + [f"{a:.3f}" for a in result.angles_deg]
    with open(path, "w", encoding="utf-8") as f:
        f.write(",".join(header) + "\n")
        for i, wl in enumerate(result.wavelengths_nm):
            row = [f"{wl:.3f}"] + [f"{v:.6f}" for v in data[i]]
            f.write(",".join(row) + "\n")


def export_thickness_csv(result: ThicknessResult, path: str) -> None:
    header = "thickness_nm,R_TE,R_TM,R_unpol,T_TE,T_TM,T_unpol"
    data = np.column_stack([
        result.thicknesses_nm,
        result.R_TE, result.R_TM, result.R_unpol,
        result.T_TE, result.T_TM, result.T_unpol,
    ])
    np.savetxt(path, data, delimiter=",", header=header, comments="")


def ask_save_path(
    parent: QWidget,
    default_name: str,
    filters: str = "PNG (*.png);;SVG (*.svg);;CSV (*.csv)",
) -> str | None:
    path, _ = QFileDialog.getSaveFileName(parent, "Exportar", default_name, filters)
    return path or None
