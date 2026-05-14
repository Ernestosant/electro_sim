"""CSV import for multilayer stack definitions."""

from __future__ import annotations

import csv
import math
from collections.abc import Mapping
from pathlib import Path

from electro_sim.physics_engine.types import Layer

INDEX_COLUMNS = frozenset({"n_re", "n_im", "thickness_nm"})
EPS_MU_COLUMNS = frozenset({"eps_re", "eps_im", "mu_re", "mu_im", "thickness_nm"})


class LayerCsvError(ValueError):
    """Raised when a multilayer CSV cannot be converted to physical layers."""


def _field_mapping(fieldnames: list[str] | None) -> dict[str, str]:
    if not fieldnames:
        raise LayerCsvError("El CSV esta vacio o no tiene encabezados.")

    mapping: dict[str, str] = {}
    for original in fieldnames:
        key = original.strip().lower()
        if not key:
            continue
        if key in mapping:
            raise LayerCsvError(f"Columna duplicada: '{key}'.")
        mapping[key] = original
    return mapping


def _detect_format(mapping: Mapping[str, str]) -> str:
    keys = set(mapping)
    if keys >= INDEX_COLUMNS:
        return "index"
    if keys >= EPS_MU_COLUMNS:
        return "eps_mu"

    if keys & INDEX_COLUMNS:
        missing = sorted(INDEX_COLUMNS - keys)
        raise LayerCsvError(
            "Faltan columnas para el formato por indice: " + ", ".join(missing)
        )
    if keys & EPS_MU_COLUMNS:
        missing = sorted(EPS_MU_COLUMNS - keys)
        raise LayerCsvError(
            "Faltan columnas para el formato eps/mu: " + ", ".join(missing)
        )
    raise LayerCsvError(
        "El CSV debe contener name,n_re,n_im,thickness_nm "
        "o eps_re,eps_im,mu_re,mu_im,thickness_nm."
    )


def _is_blank_row(row: Mapping[str | None, object]) -> bool:
    return all(str(value or "").strip() == "" for value in row.values())


def _cell(row: Mapping[str | None, object], mapping: Mapping[str, str], key: str) -> str:
    return str(row.get(mapping[key], "") or "").strip()


def _float_cell(
    row: Mapping[str | None, object],
    mapping: Mapping[str, str],
    row_number: int,
    key: str,
) -> float:
    raw = _cell(row, mapping, key)
    if raw == "":
        raise LayerCsvError(f"Fila {row_number}, columna '{key}': valor requerido.")
    try:
        value = float(raw)
    except ValueError as exc:
        raise LayerCsvError(
            f"Fila {row_number}, columna '{key}': '{raw}' no es un numero valido."
        ) from exc
    if not math.isfinite(value):
        raise LayerCsvError(
            f"Fila {row_number}, columna '{key}': el valor debe ser finito."
        )
    return value


def _validate_positive_thickness(thickness_nm: float, row_number: int) -> None:
    if thickness_nm <= 0.0:
        raise LayerCsvError(
            f"Fila {row_number}, columna 'thickness_nm': el espesor debe ser > 0."
        )


def _layer_from_index_format(
    row: Mapping[str | None, object],
    mapping: Mapping[str, str],
    row_number: int,
) -> Layer:
    n_re = _float_cell(row, mapping, row_number, "n_re")
    n_im = _float_cell(row, mapping, row_number, "n_im")
    thickness_nm = _float_cell(row, mapping, row_number, "thickness_nm")

    if n_re <= 0.0:
        raise LayerCsvError(f"Fila {row_number}, columna 'n_re': n_re debe ser > 0.")
    if n_im < 0.0:
        raise LayerCsvError(f"Fila {row_number}, columna 'n_im': n_im debe ser >= 0.")
    _validate_positive_thickness(thickness_nm, row_number)

    n = complex(n_re, n_im)
    return Layer(eps=complex(n * n), mu=1.0 + 0j, thickness_nm=thickness_nm)


def _layer_from_eps_mu_format(
    row: Mapping[str | None, object],
    mapping: Mapping[str, str],
    row_number: int,
) -> Layer:
    eps = complex(
        _float_cell(row, mapping, row_number, "eps_re"),
        _float_cell(row, mapping, row_number, "eps_im"),
    )
    mu = complex(
        _float_cell(row, mapping, row_number, "mu_re"),
        _float_cell(row, mapping, row_number, "mu_im"),
    )
    thickness_nm = _float_cell(row, mapping, row_number, "thickness_nm")

    if abs(eps) == 0.0:
        raise LayerCsvError(f"Fila {row_number}, columnas eps_*: eps no puede ser 0.")
    if abs(mu) == 0.0:
        raise LayerCsvError(f"Fila {row_number}, columnas mu_*: mu no puede ser 0.")
    _validate_positive_thickness(thickness_nm, row_number)

    return Layer(eps=eps, mu=mu, thickness_nm=thickness_nm)


def load_layers_csv(path: str | Path) -> list[Layer]:
    """Load a multilayer stack from a CSV file.

    Supported headers:

    - ``name,n_re,n_im,thickness_nm`` (``name`` is optional)
    - ``eps_re,eps_im,mu_re,mu_im,thickness_nm``
    """
    csv_path = Path(path)
    try:
        with csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            mapping = _field_mapping(reader.fieldnames)
            csv_format = _detect_format(mapping)
            layers: list[Layer] = []

            for row_number, row in enumerate(reader, start=2):
                if None in row and any(str(value or "").strip() for value in row[None] or []):
                    raise LayerCsvError(f"Fila {row_number}: demasiadas columnas.")
                if _is_blank_row(row):
                    continue

                if csv_format == "index":
                    layers.append(_layer_from_index_format(row, mapping, row_number))
                else:
                    layers.append(_layer_from_eps_mu_format(row, mapping, row_number))
    except OSError as exc:
        raise LayerCsvError(f"No se pudo leer el CSV: {exc}") from exc

    if not layers:
        raise LayerCsvError("El CSV no contiene capas validas.")
    return layers

