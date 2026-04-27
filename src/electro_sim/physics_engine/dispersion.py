"""Optical dispersion models for wavelength-dependent complex permittivity ε(λ).

Sellmeier, Cauchy, Drude, Drude-Lorentz + presets de 10 materiales.

Portado desde `C:\\Mis_proyectos\\Proyecto\\optic_simulator\\dispersion_models.py`
preservando parámetros literales (Rakic 1998 para metales, Sellmeier para
dieléctricos, etc.).
"""

from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from typing import Any

import numpy as np
import numpy.typing as npt
from numpy.lib.scimath import sqrt as csqrt

from electro_sim.physics_engine.constants import HC_EV_NM


class DispersionModel(ABC):
    """Clase base abstracta para modelos de dispersión óptica.
    
    Un modelo de dispersión describe cómo la permitividad relativa (ε) de un material
    cambia en función de la longitud de onda de la luz incidente. Esto modela fenómenos
    físicos como la absorción resonante y el retraso de fase en distintos materiales.
    """
    name: str = ""

    @abstractmethod
    def epsilon(self, wavelength_nm: npt.ArrayLike) -> complex | npt.NDArray[Any]:
        """Calcula la permitividad compleja ε(λ) para una o varias longitudes de onda.
        
        Args:
            wavelength_nm: Longitud de onda en nanómetros (escalar o arreglo de numpy).
            
        Returns:
            Permitividad dieléctrica compleja evaluada en las longitudes de onda dadas.
        """
        ...

    def n_complex(self, wavelength_nm: npt.ArrayLike) -> complex | npt.NDArray[Any]:
        """Calcula el índice de refracción complejo n(λ) a partir de la permitividad.
        
        Utiliza la relación fundamental n = sqrt(ε * μ), asumiendo que μ = 1 (medios no magnéticos),
        por lo que n = sqrt(ε).
        
        Args:
            wavelength_nm: Longitud de onda en nanómetros.
            
        Returns:
            Índice de refracción complejo.
        """
        return csqrt(self.epsilon(wavelength_nm))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"


class ConstantModel(DispersionModel):
    """Modelo de material sin dispersión (permitividad constante en todas las frecuencias).
    
    Ideal para modelar vacío, aire, o como aproximación de primer orden para 
    materiales dieléctricos transparentes muy lejos de sus resonancias de absorción.
    """
    def __init__(self, eps: complex | float, name: str = "") -> None:
        self.eps = complex(eps)
        self.name = name

    def epsilon(self, wavelength_nm: npt.ArrayLike) -> complex | npt.NDArray[Any]:
        wl = np.asarray(wavelength_nm, dtype=float)
        return np.full_like(wl, self.eps, dtype=complex) if wl.ndim else self.eps


class SellmeierModel(DispersionModel):
    r"""n²(λ) = 1 + Σ Bᵢ λ²/(λ² - Cᵢ). Cᵢ in μm²."""

    def __init__(
        self,
        coefficients: npt.ArrayLike,
        valid_range: tuple[float, float] | None = None,
        name: str = "",
    ) -> None:
        self.coefficients = np.asarray(coefficients, dtype=float)
        self.valid_range = valid_range
        self.name = name

    def epsilon(self, wavelength_nm: npt.ArrayLike) -> complex | npt.NDArray[Any]:
        wl_nm = np.asarray(wavelength_nm, dtype=float)
        
        # 1. La ecuación original de Sellmeier utiliza sistemáticamente la longitud de onda en micrómetros
        wl_um = wl_nm / 1000.0

        if self.valid_range is not None:
            lo, hi = self.valid_range
            out = (wl_um < lo) | (wl_um > hi)
            if np.any(out):
                warnings.warn(
                    f"{self.name or 'SellmeierModel'}: longitud de onda fuera "
                    f"del rango válido [{lo}–{hi}] μm; se clampea.",
                    stacklevel=2,
                )
                wl_um = np.clip(wl_um, lo, hi)

        # 2. Precomputamos el cuadrado de la longitud de onda
        lam2 = wl_um ** 2
        
        # 3. Separamos los coeficientes B_i y C_i de la matriz de parámetros
        B = self.coefficients[:, 0]
        C = self.coefficients[:, 1]
        
        # 4. Evaluamos la sumatoria de la ecuación de Sellmeier de forma vectorizada.
        # Fórmula: n^2(λ) = 1 + Sum_i [ B_i * λ^2 / (λ^2 - C_i) ]
        n2 = 1.0 + np.sum(B * lam2[..., np.newaxis] / (lam2[..., np.newaxis] - C), axis=-1)
        
        # Retornamos epsilon = n^2
        return n2.astype(complex)


class CauchyModel(DispersionModel):
    r"""n(λ) = A + B/λ² + C/λ⁴, con λ en μm."""

    def __init__(self, A: float, B: float, C: float = 0.0, name: str = "") -> None:
        self.A = A
        self.B = B
        self.C = C
        self.name = name

    def epsilon(self, wavelength_nm: npt.ArrayLike) -> complex | npt.NDArray[Any]:
        # 1. Transformación de unidades de nm a micrómetros
        wl_um = np.asarray(wavelength_nm, dtype=float) / 1000.0
        
        # 2. Ecuación polinómica de Cauchy para dieléctricos puros:
        # n(λ) = A + B / λ^2 + C / λ^4
        n = self.A + self.B / wl_um ** 2 + self.C / wl_um ** 4
        
        # 3. Permitividad relativa (ε) es el cuadrado del índice de refracción
        return (n ** 2).astype(complex)


class DrudeModel(DispersionModel):
    r"""ε(ω) = ε∞ − ωp² / (ω² + iγω)."""

    def __init__(
        self, eps_inf: float, omega_p_eV: float, gamma_eV: float, name: str = ""
    ) -> None:
        self.eps_inf = eps_inf
        self.omega_p_eV = omega_p_eV
        self.gamma_eV = gamma_eV
        self.name = name

    def epsilon(self, wavelength_nm: npt.ArrayLike) -> complex | npt.NDArray[Any]:
        wl = np.asarray(wavelength_nm, dtype=float)
        
        # 1. Convertimos la longitud de onda a energía/frecuencia (en electronvoltios) usando E = hc / λ
        omega = HC_EV_NM / wl
        
        # 2. Precomputamos el cuadrado de la frecuencia del plasma (ω_p^2)
        wp2 = self.omega_p_eV ** 2
        
        # 3. Aplicamos el modelo clásico de Drude para un gas de electrones libres:
        # ε(ω) = ε_inf - ω_p^2 / (ω * (ω + i * γ))
        # Donde γ (gamma) es el término de amortiguamiento o colisiones
        return self.eps_inf - wp2 / (omega * (omega + 1j * self.gamma_eV))


class DrudeLorentzModel(DispersionModel):
    r"""Rakic 1998: Drude + Σ Lorentz oscillators."""

    def __init__(
        self,
        eps_inf: float,
        omega_p_eV: float,
        f0: float,
        gamma0_eV: float,
        oscillators: npt.ArrayLike,
        name: str = "",
    ) -> None:
        self.eps_inf = eps_inf
        self.omega_p_eV = omega_p_eV
        self.f0 = f0
        self.gamma0_eV = gamma0_eV
        self.oscillators = np.asarray(oscillators, dtype=float)
        self.name = name

    def epsilon(self, wavelength_nm: npt.ArrayLike) -> complex | npt.NDArray[Any]:
        wl = np.asarray(wavelength_nm, dtype=float)
        
        # 1. Frecuencia incidente (omega) en eV
        omega = HC_EV_NM / wl
        
        # 2. Cuadrado de la frecuencia del plasma del material
        wp2 = self.omega_p_eV ** 2

        # 3. Base intraband (Modelo de Drude para electrones libres de conducción)
        # Atenuado por su fuerza de oscilador principal f0
        eps = self.eps_inf - self.f0 * wp2 / (omega * (omega + 1j * self.gamma0_eV))

        # 4. Transiciones interband (Osciladores de Lorentz ligados)
        if self.oscillators.size:
            # Extraemos los 3 parámetros para cada oscilador (f_j: fuerza, w_j: frecuencia resonante, g_j: ancho de banda)
            f_j = self.oscillators[:, 0]
            w_j = self.oscillators[:, 1]
            g_j = self.oscillators[:, 2]
            
            # 5. Broadcast de la frecuencia incidente para operar algebraicamente contra todos los osciladores a la vez
            om = omega[..., np.newaxis] if np.ndim(omega) else omega
            
            # 6. Sumamos la contribución polarizacional de cada oscilador de Lorentz:
            # ε = ε_drude + Sumatoria [ f_j * ω_p^2 / (ω_j^2 - ω^2 - i * g_j * ω) ]
            eps = eps + np.sum(f_j * wp2 / (w_j ** 2 - om ** 2 - 1j * g_j * om), axis=-1)

        return eps


MATERIAL_PRESETS: dict[str, DispersionModel] = {
    "Air": ConstantModel(1.0, name="Air"),
    "BK7": SellmeierModel(
        coefficients=[
            (1.03961212, 0.00600069867),
            (0.231792344, 0.0200179144),
            (1.01046945, 103.560653),
        ],
        valid_range=(0.3, 2.5),
        name="BK7",
    ),
    "Fused Silica": SellmeierModel(
        coefficients=[
            (0.6961663, 0.0046791),
            (0.4079426, 0.0135121),
            (0.8974794, 97.934003),
        ],
        valid_range=(0.21, 6.7),
        name="Fused Silica",
    ),
    "Water": SellmeierModel(
        coefficients=[
            (5.684027565e-1, 5.101829712e-3),
            (1.726177391e-1, 1.821153936e-2),
            (2.086189578e-2, 2.620722293e-2),
            (1.130748688e-1, 1.069792721e1),
        ],
        valid_range=(0.2, 1.1),
        name="Water",
    ),
    "Sapphire": SellmeierModel(
        coefficients=[
            (1.4313493, 0.0052799261),
            (0.65054713, 0.0142382647),
            (5.3414021, 325.01783),
        ],
        valid_range=(0.2, 5.5),
        name="Sapphire",
    ),
    "Gold": DrudeLorentzModel(
        eps_inf=1.0,
        omega_p_eV=9.03,
        f0=0.760,
        gamma0_eV=0.053,
        oscillators=[
            (0.024, 0.415, 0.241),
            (0.010, 0.830, 0.345),
            (0.071, 2.969, 0.870),
            (0.601, 4.304, 2.494),
            (4.384, 13.32, 2.214),
        ],
        name="Gold",
    ),
    "Silver": DrudeLorentzModel(
        eps_inf=1.0,
        omega_p_eV=9.01,
        f0=0.845,
        gamma0_eV=0.048,
        oscillators=[
            (0.065, 0.816, 3.886),
            (0.124, 4.481, 0.452),
            (0.011, 8.185, 0.065),
            (0.840, 9.083, 0.916),
            (5.646, 20.29, 2.419),
        ],
        name="Silver",
    ),
    "Aluminum": DrudeLorentzModel(
        eps_inf=1.0,
        omega_p_eV=14.98,
        f0=0.523,
        gamma0_eV=0.047,
        oscillators=[
            (0.227, 0.162, 0.333),
            (0.050, 1.544, 0.312),
            (0.166, 1.808, 1.351),
            (0.030, 3.473, 3.382),
            (4.305, 11.34, 4.860),
        ],
        name="Aluminum",
    ),
    "Copper": DrudeLorentzModel(
        eps_inf=1.0,
        omega_p_eV=10.83,
        f0=0.575,
        gamma0_eV=0.030,
        oscillators=[
            (0.061, 0.291, 0.378),
            (0.104, 2.957, 1.056),
            (0.723, 5.300, 3.213),
            (0.638, 11.18, 4.305),
        ],
        name="Copper",
    ),
    "Silicon": SellmeierModel(
        coefficients=[
            (10.6684293, 0.301516485 ** 2),
            (0.0030434748, 1.13475115 ** 2),
            (1.54133408, 1104.0 ** 2),
        ],
        valid_range=(1.1, 5.0),
        name="Silicon",
    ),
}


def get_preset(name: str) -> DispersionModel:
    """Obtiene un modelo de dispersión preconfigurado por su nombre.
    
    Args:
        name: Clave del material en el diccionario `MATERIAL_PRESETS` (ej. "Gold", "BK7").
        
    Returns:
        Instancia de un `DispersionModel` pre-parametrizado con los datos de literatura.
        
    Raises:
        KeyError: Si el nombre del material no existe en los presets disponibles.
    """
    if name not in MATERIAL_PRESETS:
        raise KeyError(
            f"Preset desconocido: {name!r}. Disponibles: {list(MATERIAL_PRESETS.keys())}"
        )
    return MATERIAL_PRESETS[name]
