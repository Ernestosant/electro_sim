"""Constantes físicas, numéricas y visuales para el motor de física.

Este módulo centraliza los valores fijos utilizados en los cálculos electromagnéticos,
tolerancias para evitar inestabilidades numéricas (como divisiones por cero) y la
configuración de colores para los gráficos de la interfaz.
"""

from __future__ import annotations

# Constante de Planck por la velocidad de la luz (hc) expresada en eV * nm.
# Se utiliza para la conversión fundamental entre longitud de onda (nm) y energía (eV): E = hc / λ.
HC_EV_NM: float = 1239.8419843320028

# Tolerancia de energía para comprobaciones de conservación (R + T + A = 1).
ENERGY_TOLERANCE: float = 1e-4

# Valores epsilon (muy pequeños) usados para evitar divisiones por cero en el cálculo 
# de transmitancia de potencia cuando el flujo incidente es casi nulo.
FLUX_EPSILON: float = 1e-12

# Límite mínimo de transmitancia para el cálculo del logaritmo en la absorbancia (-log10(T)).
TRANSMITTANCE_LOG_EPSILON: float = 1e-12

DEFAULT_N_ANGLES: int = 500
DEFAULT_N_WAVELENGTHS: int = 200
MAX_ABSORPTANCE_DISPLAY: float = 1.0

COLOR_TE = "#E45756"
COLOR_TM = "#4C78A8"
COLOR_TRANSMITTED = "#54A24B"
COLOR_BREWSTER = "#DAA520"
COLOR_CRITICAL = "#DC3545"
COLOR_CURRENT_ANGLE = "#888888"
COLOR_UNPOLARIZED = "#9467BD"
COLOR_PSI = "#E68A00"
COLOR_DELTA = "#2CA02C"
COLOR_ABSORBED = "#E69F00"
