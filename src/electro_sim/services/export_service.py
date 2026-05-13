"""Export de plots pyqtgraph a PNG/SVG y de arrays a CSV."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pyqtgraph as pg
import pyqtgraph.exporters  # noqa: F401 - registra exporters
from PyQt6.QtWidgets import QFileDialog, QWidget

from electro_sim.physics_engine.types import (
    AngularResult,
    HeatmapResult,
    SpectralResult,
    ThicknessResult,
    TMMTrace,
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


def _complex_header(prefix: str) -> list[str]:
    return [f"{prefix}_re", f"{prefix}_im"]


def _complex_values(value: complex) -> list[float]:
    return [float(np.real(value)), float(np.imag(value))]


def _tmm_output_paths(path: str) -> dict[str, str]:
    base = Path(path)
    suffix = base.suffix or ".csv"
    return {
        "global": str(base.with_name(f"{base.stem}_global{suffix}")),
        "interfaces": str(base.with_name(f"{base.stem}_interfaces{suffix}")),
        "matrices": str(base.with_name(f"{base.stem}_matrices{suffix}")),
    }


def export_tmm_trace_csv(trace: TMMTrace, path: str) -> dict[str, str]:
    """Exporta la traza TMM en tres CSV: global, interfaces y matrices."""
    paths = _tmm_output_paths(path)

    global_header = [
        "angle_deg", "polarization", "wavelength_nm",
        *_complex_header("M11"), *_complex_header("M12"),
        *_complex_header("M21"), *_complex_header("M22"),
        *_complex_header("r"), *_complex_header("t"),
        "R", "T", "A",
    ]
    with open(paths["global"], "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(global_header)
        for pol_trace in (trace.TE, trace.TM):
            for angle_idx, angle in enumerate(trace.angles_deg):
                total = pol_trace.total_matrix[:, :, angle_idx]
                writer.writerow([
                    float(angle),
                    pol_trace.polarization,
                    trace.wavelength_nm,
                    *_complex_values(total[0, 0]),
                    *_complex_values(total[0, 1]),
                    *_complex_values(total[1, 0]),
                    *_complex_values(total[1, 1]),
                    *_complex_values(pol_trace.r[angle_idx]),
                    *_complex_values(pol_trace.t[angle_idx]),
                    float(pol_trace.R[angle_idx]),
                    float(pol_trace.T[angle_idx]),
                    float(pol_trace.A[angle_idx]),
                ])

    interface_header = [
        "angle_deg", "polarization", "interface_index",
        "medium_left", "medium_right",
        *_complex_header("kz_left"), *_complex_header("kz_right"),
        *_complex_header("q_left"), *_complex_header("q_right"),
        *_complex_header("r_local"), *_complex_header("t_local"),
    ]
    with open(paths["interfaces"], "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(interface_header)
        for pol_trace in (trace.TE, trace.TM):
            for interface_idx in range(pol_trace.interface_r.shape[0]):
                for angle_idx, angle in enumerate(trace.angles_deg):
                    writer.writerow([
                        float(angle),
                        pol_trace.polarization,
                        interface_idx,
                        trace.medium_labels[interface_idx],
                        trace.medium_labels[interface_idx + 1],
                        *_complex_values(pol_trace.kz[interface_idx, angle_idx]),
                        *_complex_values(pol_trace.kz[interface_idx + 1, angle_idx]),
                        *_complex_values(pol_trace.admittance[interface_idx, angle_idx]),
                        *_complex_values(pol_trace.admittance[interface_idx + 1, angle_idx]),
                        *_complex_values(pol_trace.interface_r[interface_idx, angle_idx]),
                        *_complex_values(pol_trace.interface_t[interface_idx, angle_idx]),
                    ])

    matrix_header = [
        "angle_deg", "polarization", "matrix_index",
        "medium_left", "medium_right",
        *_complex_header("local_M11"), *_complex_header("local_M12"),
        *_complex_header("local_M21"), *_complex_header("local_M22"),
        *_complex_header("cumulative_M11"), *_complex_header("cumulative_M12"),
        *_complex_header("cumulative_M21"), *_complex_header("cumulative_M22"),
    ]
    with open(paths["matrices"], "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(matrix_header)
        for pol_trace in (trace.TE, trace.TM):
            for matrix_idx in range(pol_trace.matrices.shape[0]):
                for angle_idx, angle in enumerate(trace.angles_deg):
                    local = pol_trace.matrices[matrix_idx, :, :, angle_idx]
                    cumulative = pol_trace.cumulative_matrices[matrix_idx, :, :, angle_idx]
                    writer.writerow([
                        float(angle),
                        pol_trace.polarization,
                        matrix_idx,
                        trace.medium_labels[matrix_idx],
                        trace.medium_labels[matrix_idx + 1],
                        *_complex_values(local[0, 0]),
                        *_complex_values(local[0, 1]),
                        *_complex_values(local[1, 0]),
                        *_complex_values(local[1, 1]),
                        *_complex_values(cumulative[0, 0]),
                        *_complex_values(cumulative[0, 1]),
                        *_complex_values(cumulative[1, 0]),
                        *_complex_values(cumulative[1, 1]),
                    ])

    return paths


def ask_save_path(
    parent: QWidget,
    default_name: str,
    filters: str = "PNG (*.png);;SVG (*.svg);;CSV (*.csv)",
) -> str | None:
    path, _ = QFileDialog.getSaveFileName(parent, "Exportar", default_name, filters)
    return path or None
