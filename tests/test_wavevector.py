from __future__ import annotations

import numpy as np
from numpy.lib.scimath import sqrt as csqrt
from numpy.testing import assert_allclose

from electro_sim.physics_engine.fresnel import FresnelEngine
from electro_sim.physics_engine.tmm import solve_tmm_vectorized
from electro_sim.physics_engine.wavevector import (
    kx_from_angle,
    kz_from_kx,
    phase_from_kz,
    sin_theta_from_kx,
)


def test_kz_helpers_match_interface_geometry() -> None:
    engine = FresnelEngine(1.0, 1.0, 2.25, 1.0)
    theta = np.radians(np.array([0.0, 25.0, 45.0, 70.0]))

    kx = kx_from_angle(theta, engine.medium1)
    sin_theta_t = (engine.n1 / engine.n2) * np.sin(theta).astype(complex)
    expected_k1z = engine.n1 * np.cos(theta).astype(complex)
    expected_k2z = engine.n2 * csqrt(1 - sin_theta_t ** 2)

    assert_allclose(kx, engine.n1 * np.sin(theta).astype(complex))
    assert_allclose(sin_theta_from_kx(engine.medium2, kx), sin_theta_t)
    assert_allclose(kz_from_kx(engine.medium1, kx), expected_k1z)
    assert_allclose(kz_from_kx(engine.medium2, kx), expected_k2z)


def test_phase_from_kz_matches_thin_film_beta_formula() -> None:
    film = {"eps": complex(1.9, 0.2), "mu": 1.0, "thickness": 120.0}
    engine = FresnelEngine(1.0, 1.0, complex(2.25, 0.5), 1.0, film=film, wavelength=550.0)
    theta = np.radians(np.array([10.0, 40.0, 65.0]))

    kx = kx_from_angle(theta, engine.medium1)
    sin_theta_film = (engine.n1 / engine.film["n"]) * np.sin(theta).astype(complex)
    expected_kfz = engine.film["n"] * csqrt(1 - sin_theta_film ** 2)
    expected_beta = (2 * np.pi * engine.film["thickness"] / engine.wavelength) * expected_kfz

    assert_allclose(kz_from_kx(engine.film, kx), expected_kfz)
    assert_allclose(
        phase_from_kz(kz_from_kx(engine.film, kx), engine.film["thickness"], engine.wavelength),
        expected_beta,
    )


def test_kz_from_kx_uses_evanescent_branch_above_critical_angle() -> None:
    engine = FresnelEngine(2.25, 1.0, 1.0, 1.0)
    theta = np.radians(np.array([60.0]))

    kx = kx_from_angle(theta, engine.medium1)
    k2z = kz_from_kx(engine.medium2, kx)

    assert abs(np.real(k2z[0])) < 1e-12
    assert np.imag(k2z[0]) > 0


def test_tmm_direct_kx_path_matches_public_multilayer_api() -> None:
    layers = [
        {"eps": 2.0, "mu": 1.0, "thickness": 80.0},
        {"eps": 1.5, "mu": 1.0, "thickness": 120.0},
        {"eps": 2.3, "mu": 1.0, "thickness": 60.0},
    ]
    engine = FresnelEngine(1.0, 1.0, 2.25, 1.0, layers=layers, wavelength=550.0)
    angles_deg = np.array([0.0, 20.0, 40.0, 70.0])
    theta = np.radians(angles_deg)
    kx = kx_from_angle(theta, engine.medium1)
    result = engine.calculate_coefficients(angles_deg)

    for polarization in ("TE", "TM"):
        r, t, q_inc, q_sub = solve_tmm_vectorized(
            kx=kx,
            layers=engine.layers,
            medium1=engine.medium1,
            medium2=engine.medium2,
            wavelength_nm=engine.wavelength,
            polarization=polarization,
        )

        assert_allclose(r, result[polarization]["r"])
        assert_allclose(t, result[polarization]["t"])
        assert_allclose(q_inc, kz_from_kx(engine.medium1, kx) / engine.medium1["mu"] if polarization == "TE" else kz_from_kx(engine.medium1, kx) / engine.medium1["eps"])
        assert_allclose(q_sub, kz_from_kx(engine.medium2, kx) / engine.medium2["mu"] if polarization == "TE" else kz_from_kx(engine.medium2, kx) / engine.medium2["eps"])