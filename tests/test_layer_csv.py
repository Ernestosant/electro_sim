from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from electro_sim.physics_engine.sweeps import sweep_angular
from electro_sim.physics_engine.types import Medium, SimulationRequest
from electro_sim.services.layer_csv import LayerCsvError, load_layers_csv

EXAMPLE_CSV = Path(__file__).resolve().parents[1] / "examples" / "multilayer_100_layers.csv"


def _write_csv(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "layers.csv"
    path.write_text(text, encoding="utf-8")
    return path


def test_load_layers_csv_index_format(tmp_path: Path) -> None:
    path = _write_csv(
        tmp_path,
        "name,n_re,n_im,thickness_nm\nL1,1.5,0.01,100\nL2,2.0,0.02,80\n",
    )

    layers = load_layers_csv(path)

    assert len(layers) == 2
    assert layers[0].eps == pytest.approx((1.5 + 0.01j) ** 2)
    assert layers[0].mu == pytest.approx(1.0 + 0j)
    assert layers[0].thickness_nm == pytest.approx(100.0)


def test_load_layers_csv_eps_mu_format(tmp_path: Path) -> None:
    path = _write_csv(
        tmp_path,
        "eps_re,eps_im,mu_re,mu_im,thickness_nm\n2.25,0.1,1.0,0.02,120\n",
    )

    layers = load_layers_csv(path)

    assert len(layers) == 1
    assert layers[0].eps == pytest.approx(2.25 + 0.1j)
    assert layers[0].mu == pytest.approx(1.0 + 0.02j)
    assert layers[0].thickness_nm == pytest.approx(120.0)


@pytest.mark.parametrize(
    ("text", "match"),
    [
        ("n_re,n_im\n1.5,0.0\n", "Faltan columnas"),
        ("n_re,n_im,thickness_nm\nabc,0.0,100\n", "no es un numero valido"),
        ("n_re,n_im,thickness_nm\n1.5,0.0,0\n", "espesor debe ser > 0"),
        ("n_re,n_im,thickness_nm\n1.5,-0.01,100\n", "n_im debe ser >= 0"),
        ("", "vacio"),
    ],
)
def test_load_layers_csv_rejects_invalid_input(tmp_path: Path, text: str, match: str) -> None:
    path = _write_csv(tmp_path, text)

    with pytest.raises(LayerCsvError, match=match):
        load_layers_csv(path)


def test_example_100_layers_is_physically_consistent() -> None:
    layers = load_layers_csv(EXAMPLE_CSV)
    triples = {
        (
            round(np.sqrt(layer.eps).real, 9),
            round(np.sqrt(layer.eps).imag, 9),
            round(layer.thickness_nm, 9),
        )
        for layer in layers
    }

    request = SimulationRequest(
        medium1=Medium(eps=1.0 + 0j, mu=1.0 + 0j, name="Air"),
        medium2=Medium(eps=2.25 + 0j, mu=1.0 + 0j, name="Glass"),
        layers=tuple(layers),
        wavelength_nm=550.0,
        angle_range_deg=(0.0, 80.0, 161),
        mode="angular",
    )
    result = sweep_angular(request)

    assert len(layers) == 100
    assert len(triples) == 100
    for channel in (
        result.R_TE,
        result.R_TM,
        result.T_TE,
        result.T_TM,
        result.A_TE,
        result.A_TM,
    ):
        assert np.all(np.isfinite(channel))
        assert np.min(channel) >= -1e-12
        assert np.max(channel) <= 1.0 + 1e-12

    assert np.max(np.abs(result.R_TE + result.T_TE + result.A_TE - 1.0)) < 1e-9
    assert np.max(np.abs(result.R_TM + result.T_TM + result.A_TM - 1.0)) < 1e-9
    assert np.max(result.A_TE) > 1e-6
    assert np.max(result.A_TM) > 1e-6
