from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from numpy.testing import assert_allclose

from electro_sim.physics_engine.fresnel import FresnelEngine
from electro_sim.physics_engine.structures import build_dbr
from electro_sim.physics_engine.sweeps import trace_tmm
from electro_sim.physics_engine.tmm import solve_tmm_trace_vectorized, solve_tmm_vectorized
from electro_sim.physics_engine.types import Layer, Medium, SimulationRequest
from electro_sim.physics_engine.wavevector import kx_from_angle
from electro_sim.services.export_service import export_tmm_trace_csv


def _request(
    layers: tuple[Layer, ...] = (),
    angle_range: tuple[float, float, int] = (0.0, 70.0, 4),
) -> SimulationRequest:
    return SimulationRequest(
        medium1=Medium(eps=1.0 + 0j, mu=1.0 + 0j, name="Air"),
        medium2=Medium(eps=2.25 + 0j, mu=1.0 + 0j, name="Glass"),
        layers=layers,
        wavelength_nm=550.0,
        angle_range_deg=angle_range,
        mode="angular",
    )


def _layer_dicts(layers: tuple[Layer, ...]) -> list[dict]:
    return [
        {"eps": layer.eps, "mu": layer.mu, "thickness": layer.thickness_nm}
        for layer in layers
    ]


def test_tmm_trace_global_matches_existing_solver_for_te_and_tm() -> None:
    layers = (
        Layer(eps=2.0 + 0j, mu=1.0 + 0j, thickness_nm=80.0),
        Layer(eps=1.5 + 0j, mu=1.0 + 0j, thickness_nm=120.0),
        Layer(eps=2.3 + 0j, mu=1.0 + 0j, thickness_nm=60.0),
    )
    trace = trace_tmm(_request(layers))
    engine = FresnelEngine(1.0, 1.0, 2.25, 1.0, layers=_layer_dicts(layers), wavelength=550.0)
    kx = kx_from_angle(np.radians(trace.angles_deg), engine.medium1)

    for polarization, pol_trace in (("TE", trace.TE), ("TM", trace.TM)):
        r, t, _, _ = solve_tmm_vectorized(
            kx=kx,
            layers=engine.layers,
            medium1=engine.medium1,
            medium2=engine.medium2,
            wavelength_nm=engine.wavelength,
            polarization=polarization,
        )
        assert_allclose(pol_trace.r, r, atol=1e-12)
        assert_allclose(pol_trace.t, t, atol=1e-12)

    n_angles = trace.angles_deg.size
    assert trace.TE.kz.shape == (len(layers) + 2, n_angles)
    assert trace.TE.interface_r.shape == (len(layers) + 1, n_angles)
    assert trace.TE.matrices.shape == (len(layers) + 1, 2, 2, n_angles)
    assert trace.TE.cumulative_matrices.shape == trace.TE.matrices.shape


def test_tmm_trace_simple_interface_matches_fresnel_local_coefficients() -> None:
    trace = trace_tmm(_request(angle_range=(0.0, 60.0, 4)))
    engine = FresnelEngine(1.0, 1.0, 2.25, 1.0, wavelength=550.0)
    result = engine.calculate_coefficients(trace.angles_deg)

    assert_allclose(trace.TE.interface_r[0], trace.TE.r, atol=1e-12)
    assert_allclose(trace.TE.interface_t[0], trace.TE.t, atol=1e-12)
    assert_allclose(trace.TE.r, result["TE"]["r"], atol=1e-12)
    assert_allclose(trace.TM.r, result["TM"]["r"], atol=1e-12)
    assert trace.TE.matrices.shape[0] == 1


def test_tmm_trace_single_layer_matches_thin_film_formula() -> None:
    film = Layer(eps=1.9 + 0j, mu=1.0 + 0j, thickness_nm=100.0)
    trace = trace_tmm(_request(layers=(film,), angle_range=(0.0, 70.0, 5)))
    film_engine = FresnelEngine(
        1.0,
        1.0,
        2.25,
        1.0,
        film={"eps": film.eps, "mu": film.mu, "thickness": film.thickness_nm},
        wavelength=550.0,
    )
    result = film_engine.calculate_coefficients(trace.angles_deg)

    assert_allclose(trace.TE.R, result["TE"]["R"], atol=1e-10)
    assert_allclose(trace.TM.R, result["TM"]["R"], atol=1e-10)
    assert_allclose(trace.TE.T, result["TE"]["T"], atol=1e-10)
    assert_allclose(trace.TM.T, result["TM"]["T"], atol=1e-10)


def test_tmm_trace_filters_zero_thickness_layers_before_labeling() -> None:
    layers = (
        Layer(eps=1.8 + 0j, mu=1.0 + 0j, thickness_nm=0.0),
        Layer(eps=2.0 + 0j, mu=1.0 + 0j, thickness_nm=80.0),
        Layer(eps=1.4 + 0j, mu=1.0 + 0j, thickness_nm=0.0),
    )
    trace = trace_tmm(_request(layers, angle_range=(0.0, 10.0, 3)))

    assert trace.medium_labels == ("Air", "L1", "Glass")
    assert trace.layer_thicknesses_nm.tolist() == [80.0]
    assert trace.TE.interface_r.shape[0] == len(trace.medium_labels) - 1
    assert trace.TE.matrices.shape[0] == len(trace.medium_labels) - 1


def test_tmm_trace_rejects_invalid_polarization() -> None:
    engine = FresnelEngine(1.0, 1.0, 2.25, 1.0, wavelength=550.0)
    angles = np.array([0.0, 20.0])
    kx = kx_from_angle(np.radians(angles), engine.medium1)

    with pytest.raises(ValueError, match="polarization"):
        solve_tmm_trace_vectorized(
            kx=kx,
            layers=engine.layers,
            medium1=engine.medium1,
            medium2=engine.medium2,
            wavelength_nm=engine.wavelength,
            polarization="unpolarized",  # type: ignore[arg-type]
        )


def test_tmm_trace_energy_for_lossless_dbr_and_lossy_layer() -> None:
    dbr_layers = tuple(
        Layer(eps=complex(layer["eps"]), mu=complex(layer["mu"]), thickness_nm=layer["thickness"])
        for layer in build_dbr(2.3, 1.45, 4, 550.0)
    )
    dbr_trace = trace_tmm(_request(dbr_layers, angle_range=(0.0, 70.0, 8)))

    assert_allclose(dbr_trace.TE.R + dbr_trace.TE.T, 1.0, atol=1e-8)
    assert_allclose(dbr_trace.TM.R + dbr_trace.TM.T, 1.0, atol=1e-8)

    lossy = Layer(eps=(2.0 + 0.1j) ** 2, mu=1.0 + 0j, thickness_nm=100.0)
    lossy_trace = trace_tmm(_request((lossy,), angle_range=(0.0, 70.0, 5)))

    assert_allclose(lossy_trace.TE.R + lossy_trace.TE.T + lossy_trace.TE.A, 1.0, atol=1e-10)
    assert_allclose(lossy_trace.TM.R + lossy_trace.TM.T + lossy_trace.TM.A, 1.0, atol=1e-10)
    assert np.max(lossy_trace.TE.A) > 1e-6
    assert np.max(lossy_trace.TM.A) > 1e-6


def test_tmm_trace_export_writes_three_csv_files_with_stable_headers(tmp_path: Path) -> None:
    layers = (Layer(eps=2.0 + 0j, mu=1.0 + 0j, thickness_nm=80.0),)
    trace = trace_tmm(_request(layers, angle_range=(0.0, 10.0, 3)))
    paths = export_tmm_trace_csv(trace, str(tmp_path / "trace.csv"))

    global_lines = Path(paths["global"]).read_text(encoding="utf-8").splitlines()
    interface_lines = Path(paths["interfaces"]).read_text(encoding="utf-8").splitlines()
    matrix_lines = Path(paths["matrices"]).read_text(encoding="utf-8").splitlines()

    assert global_lines[0].split(",") == [
        "angle_deg", "polarization", "wavelength_nm",
        "M11_re", "M11_im", "M12_re", "M12_im",
        "M21_re", "M21_im", "M22_re", "M22_im",
        "r_re", "r_im", "t_re", "t_im", "R", "T", "A",
    ]
    assert "r_local_re" in interface_lines[0]
    assert "local_M11_re" in matrix_lines[0]

    n_angles = trace.angles_deg.size
    n_interfaces = len(layers) + 1
    assert len(global_lines) == 1 + 2 * n_angles
    assert len(interface_lines) == 1 + 2 * n_angles * n_interfaces
    assert len(matrix_lines) == 1 + 2 * n_angles * n_interfaces
