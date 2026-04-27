"""Tipos de datos y estructuras para la comunicación con el motor de física.

Este módulo define las 'dataclasses' (clases de datos) que representan los parámetros
de entrada (medios, capas, condiciones de simulación) y los resultados estructurados
de las distintas simulaciones (angular, espectral, etc.). El uso de dataclasses 
facilita el manejo de los datos sin lógica compleja asociada.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

import numpy as np


Polarization = Literal["TE", "TM", "unpolarized"]
SimulationMode = Literal["angular", "spectral", "heatmap", "thickness"]


@dataclass(frozen=True)
class Medium:
    """Representa un medio óptico semi-infinito (ej. medio incidente o sustrato final).
    
    Attributes:
        eps: Permitividad dieléctrica relativa (ε). Puede ser compleja (la parte imaginaria representa pérdidas/absorción).
        mu: Permeabilidad magnética relativa (μ). Generalmente 1.0 + 0j para medios no magnéticos.
        name: Nombre identificativo del material (opcional).
    """
    eps: complex
    mu: complex = 1.0 + 0j
    name: str = ""


@dataclass(frozen=True)
class Layer:
    """Representa una capa delgada plana (thin film) dentro de una estructura multicapa.
    
    Attributes:
        eps: Permitividad dieléctrica relativa (ε) de la capa.
        mu: Permeabilidad magnética relativa (μ) de la capa.
        thickness_nm: Espesor físico (grosor) de la capa en nanómetros (d).
    """
    eps: complex
    mu: complex
    thickness_nm: float


@dataclass(frozen=True)
class SimulationRequest:
    """Encapsula todos los parámetros necesarios para ejecutar una simulación óptica.
    
    Esta estructura concentra las condiciones de contorno (medios 1 y 2), la física
    intermedia (capas) y los parámetros del haz incidente (longitud de onda, ángulo).
    Las funciones de 'sweep' (barridos) usan este objeto como fuente de verdad.
    """
    medium1: Medium
    medium2: Medium
    layers: tuple[Layer, ...] = ()
    film_thickness_nm: float = 0.0
    film_eps: complex = 1.0 + 0j
    film_mu: complex = 1.0 + 0j
    wavelength_nm: float = 550.0
    angle_range_deg: tuple[float, float, int] = (0.0, 89.9, 500)
    fixed_angle_deg: float = 45.0
    wavelength_range_nm: tuple[float, float, int] = (300.0, 800.0, 200)
    thickness_range_nm: tuple[float, float, int] = (0.0, 500.0, 300)
    polarization: Polarization = "unpolarized"
    mode: SimulationMode = "angular"


@dataclass
class AngularResult:
    """Resultados de un barrido angular (fijando la longitud de onda, variando el ángulo).
    
    Almacena los coeficientes de potencia (Reflectancia R, Transmitancia T, Absorptancia A) 
    y de amplitud complejos (r, t) para las polarizaciones TE (s) y TM (p), evaluados 
    para un arreglo de ángulos de incidencia.
    """
    angles_deg: np.ndarray
    R_TE: np.ndarray
    R_TM: np.ndarray
    R_unpol: np.ndarray
    T_TE: np.ndarray
    T_TM: np.ndarray
    T_unpol: np.ndarray
    A_TE: np.ndarray
    A_TM: np.ndarray
    A_unpol: np.ndarray
    r_TE: np.ndarray
    r_TM: np.ndarray
    t_TE: np.ndarray
    t_TM: np.ndarray
    phi_r_TE: np.ndarray
    phi_r_TM: np.ndarray
    phi_t_TE: np.ndarray
    phi_t_TM: np.ndarray
    brewster_deg: Optional[float] = None
    critical_deg: Optional[float] = None
    compute_ms: float = 0.0


@dataclass
class SpectralResult:
    """Resultados de un barrido espectral (fijando el ángulo, variando la longitud de onda).
    
    Almacena los coeficientes de potencia (R, T, A) evaluados a lo largo de un 
    espectro de longitudes de onda incidentes. Aquí A representa la absorptancia.
    """
    wavelengths_nm: np.ndarray
    R_TE: np.ndarray
    R_TM: np.ndarray
    R_unpol: np.ndarray
    T_TE: np.ndarray
    T_TM: np.ndarray
    T_unpol: np.ndarray
    A_TE: np.ndarray
    A_TM: np.ndarray
    compute_ms: float = 0.0


@dataclass
class HeatmapResult:
    """Resultados de un barrido 2D simultáneo (espectro-angular).
    
    Permite generar mapas de calor donde un eje es el ángulo y el otro la longitud de onda.
    Las matrices de resultados (ej. R_TE) tienen forma (N_wavelengths, N_angles).
    """
    angles_deg: np.ndarray
    wavelengths_nm: np.ndarray
    R_TE: np.ndarray  # shape (N_wl, N_theta)
    R_TM: np.ndarray
    R_unpol: np.ndarray
    T_TE: np.ndarray
    T_TM: np.ndarray
    T_unpol: np.ndarray
    compute_ms: float = 0.0


@dataclass
class ThicknessResult:
    """Resultados de un barrido de espesor (variando el grosor de una capa específica).
    
    Útil para observar interferencias constructivas o destructivas (oscilaciones de Fabry-Pérot)
    a medida que cambia el camino óptico dentro de la película delgada.
    """
    thicknesses_nm: np.ndarray
    R_TE: np.ndarray
    R_TM: np.ndarray
    R_unpol: np.ndarray
    T_TE: np.ndarray
    T_TM: np.ndarray
    T_unpol: np.ndarray
    compute_ms: float = 0.0
