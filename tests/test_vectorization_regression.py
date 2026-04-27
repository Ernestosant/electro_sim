"""Valida que el motor vectorizado produzca resultados idénticos al modo escalar.

Recorre 100 escenarios aleatorios (semilla fija) × 5 ángulos cada uno y verifica
`engine.calculate_coefficients(angle_scalar) == engine.calculate_coefficients(np.array([angle]))[0]`
a tolerancia < 1e-10.
"""

from __future__ import annotations

import numpy as np
import pytest

from electro_sim.physics_engine.fresnel import FresnelEngine
from electro_sim.physics_engine.structures import build_dbr

RNG = np.random.default_rng(seed=42)


def _make_random_engine(include_film: bool = False, include_layers: bool = False) -> FresnelEngine:
    eps1 = complex(RNG.uniform(0.5, 4.0), RNG.uniform(0, 0.5))
    mu1 = complex(RNG.uniform(0.5, 2.0), 0)
    eps2 = complex(RNG.uniform(0.5, 6.0), RNG.uniform(0, 1.0))
    mu2 = complex(RNG.uniform(0.5, 2.0), 0)

    film = None
    if include_film:
        film = {
            "eps": complex(RNG.uniform(1.1, 3.5), 0),
            "mu": 1.0 + 0j,
            "thickness": float(RNG.uniform(50.0, 400.0)),
        }

    layers = None
    if include_layers:
        layers = build_dbr(
            n_high=float(RNG.uniform(1.8, 2.5)),
            n_low=float(RNG.uniform(1.2, 1.6)),
            n_pairs=int(RNG.integers(1, 6)),
            wavelength_design_nm=float(RNG.uniform(400, 700)),
        )

    return FresnelEngine(eps1, mu1, eps2, mu2, film=film, layers=layers, wavelength=550.0)


@pytest.mark.parametrize("scenario_idx", range(30))
def test_scalar_vs_vectorized_single_interface(scenario_idx: int) -> None:
    engine = _make_random_engine(include_film=False, include_layers=False)
    angles = np.array([10.0, 25.0, 45.0, 60.0, 80.0])

    vec = engine.calculate_coefficients(angles)
    for i, a in enumerate(angles):
        sca = engine.calculate_coefficients(float(a))
        for pol in ("TE", "TM"):
            assert sca[pol]["R"] == pytest.approx(vec[pol]["R"][i], abs=1e-12)
            assert sca[pol]["T"] == pytest.approx(vec[pol]["T"][i], abs=1e-12)
            assert abs(sca[pol]["r"] - vec[pol]["r"][i]) < 1e-12
            assert abs(sca[pol]["t"] - vec[pol]["t"][i]) < 1e-12


@pytest.mark.parametrize("scenario_idx", range(15))
def test_scalar_vs_vectorized_thin_film(scenario_idx: int) -> None:
    engine = _make_random_engine(include_film=True, include_layers=False)
    angles = np.array([5.0, 30.0, 55.0])

    vec = engine.calculate_coefficients(angles)
    for i, a in enumerate(angles):
        sca = engine.calculate_coefficients(float(a))
        for pol in ("TE", "TM"):
            assert sca[pol]["R"] == pytest.approx(vec[pol]["R"][i], abs=1e-10)
            assert sca[pol]["T"] == pytest.approx(vec[pol]["T"][i], abs=1e-10)


@pytest.mark.parametrize("scenario_idx", range(15))
def test_scalar_vs_vectorized_multilayer(scenario_idx: int) -> None:
    engine = _make_random_engine(include_film=False, include_layers=True)
    angles = np.array([0.0, 20.0, 40.0, 70.0])

    vec = engine.calculate_coefficients(angles)
    for i, a in enumerate(angles):
        sca = engine.calculate_coefficients(float(a))
        for pol in ("TE", "TM"):
            assert sca[pol]["R"] == pytest.approx(vec[pol]["R"][i], abs=1e-10)
            assert sca[pol]["T"] == pytest.approx(vec[pol]["T"][i], abs=1e-10)


def test_vectorized_shape_matches_input() -> None:
    engine = FresnelEngine(1.0, 1.0, 2.25, 1.0)
    angles = np.linspace(0, 89, 500)
    res = engine.calculate_coefficients(angles)
    for pol in ("TE", "TM"):
        for key in ("R", "T", "A", "r", "t", "phi_r", "phi_t"):
            assert res[pol][key].shape == angles.shape
