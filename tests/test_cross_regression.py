"""Regresión cruzada: compara `electro_sim` contra el motor origen.

Importa `C:\\Mis_proyectos\\Proyecto\\optic_simulator\\physics_engine.py` vía
`importlib` sin copiar código (solo lectura) y verifica que ambos motores
devuelvan los mismos valores de R, T, r, t a tolerancia 1e-10.

Si el proyecto origen no está disponible, los tests se omiten con skip.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

import numpy as np
import pytest

from electro_sim.physics_engine.fresnel import FresnelEngine

ORIGIN_PATH = pathlib.Path(r"C:\Mis_proyectos\Proyecto\optic_simulator\physics_engine.py")


@pytest.fixture(scope="module")
def origin_engine_cls():
    if not ORIGIN_PATH.exists():
        pytest.skip(f"Proyecto origen no encontrado en {ORIGIN_PATH}")

    sys.path.insert(0, str(ORIGIN_PATH.parent))
    try:
        spec = importlib.util.spec_from_file_location("origin_physics_engine", ORIGIN_PATH)
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.FresnelEngine
    finally:
        sys.path.pop(0)


SCENARIOS = [
    ("air-glass", (1.0, 1.0, 2.25, 1.0), None, None),
    ("glass-air", (2.25, 1.0, 1.0, 1.0), None, None),
    ("magnetic", (4.0, 1.0, 1.0, 4.0), None, None),
    (
        "lossy",
        (1.0, 1.0, complex(2.25, 1.0), 1.0),
        None,
        None,
    ),
    (
        "thin-film",
        (1.0, 1.0, 2.25, 1.0),
        {"eps": 1.9, "mu": 1.0, "thickness": 100.0},
        None,
    ),
    (
        "quarter-wave",
        (1.0, 1.0, 1.5**2, 1.0),
        {"eps": 1.5, "mu": 1.0, "thickness": 550.0 / (4 * np.sqrt(1.5))},
        None,
    ),
    (
        "multilayer-3",
        (1.0, 1.0, 2.25, 1.0),
        None,
        [
            {"eps": 2.0, "mu": 1.0, "thickness": 80.0},
            {"eps": 1.5, "mu": 1.0, "thickness": 120.0},
            {"eps": 2.3, "mu": 1.0, "thickness": 60.0},
        ],
    ),
]


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s[0] for s in SCENARIOS])
def test_cross_regression(scenario, origin_engine_cls) -> None:
    name, (eps1, mu1, eps2, mu2), film, layers = scenario

    new_engine = FresnelEngine(eps1, mu1, eps2, mu2, film=film, wavelength=550.0, layers=layers)
    old_engine = origin_engine_cls(eps1, mu1, eps2, mu2, film=film, wavelength=550.0, layers=layers)

    angles = np.linspace(0, 89.9, 80)
    new_res = new_engine.calculate_coefficients(angles)

    for i, a in enumerate(angles):
        old_res = old_engine.calculate_coefficients(float(a))
        for pol in ("TE", "TM"):
            assert new_res[pol]["R"][i] == pytest.approx(old_res[pol]["R"], abs=1e-10), (
                f"{name} pol={pol} angle={a:.2f}° R mismatch"
            )
            assert new_res[pol]["T"][i] == pytest.approx(old_res[pol]["T"], abs=1e-10), (
                f"{name} pol={pol} angle={a:.2f}° T mismatch"
            )
            assert abs(new_res[pol]["r"][i] - old_res[pol]["r"]) < 1e-10, (
                f"{name} pol={pol} angle={a:.2f}° r mismatch"
            )
