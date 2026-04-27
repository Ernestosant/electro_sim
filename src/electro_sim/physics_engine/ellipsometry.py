"""Elipsometría: ψ, Δ, matriz de Jones y elipse de polarización.

Relaciones estándar:

    ρ = r_TM / r_TE = tan(ψ)·exp(iΔ)
    ψ = arctan(|r_TM|/|r_TE|)
    Δ = arg(r_TM) - arg(r_TE)

La elipse de Jones para luz linealmente polarizada a 45° incidente, reflejada,
se parametriza por (ψ, Δ) y define una trayectoria en el plano transversal.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def ellipsometric_params(
    r_te: NDArray[np.complex128], r_tm: NDArray[np.complex128]
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Retorna (ψ_deg, Δ_deg). Acepta escalares o arrays."""
    # 1. Aseguramos formato complejo para extraer amplitud y fase
    r_te = np.asarray(r_te, dtype=complex)
    r_tm = np.asarray(r_tm, dtype=complex)

    # 2. Magnitudes de reflexión para calcular el cociente de amplitudes
    abs_te = np.abs(r_te)
    
    # 3. Protección numérica contra división por cero (si abs_te es cero, el valor de tangente será infinito)
    safe = np.where(abs_te < 1e-15, 1.0, abs_te)
    
    # 4. Cálculo del ángulo de amplitud Psi (ψ)
    # ρ = r_TM / r_TE = |r_TM|/|r_TE| * exp(iΔ) => tan(ψ) = |r_TM|/|r_TE| => ψ = arctan(|r_TM|/|r_TE|)
    psi = np.degrees(np.arctan(np.abs(r_tm) / safe))
    
    # Casos límite: si la reflexión TE es nula, la polarización es puramente TM (Psi = 90 grados)
    psi = np.where(abs_te < 1e-15, 90.0, psi)

    # 5. Cálculo del desfase Delta (Δ): Diferencia de fases entre el campo TM y el campo TE
    # Δ = arg(r_TM) - arg(r_TE)
    delta = np.degrees(np.angle(r_tm) - np.angle(r_te))
    
    # 6. Normalización de fase: Acotamos Delta al rango principal de la rama trigonométrica [-180, 180)
    delta = np.mod(delta + 180.0, 360.0) - 180.0
    return psi, delta


def jones_ellipse(
    psi_deg: float, delta_deg: float, n_points: int = 200
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Traza la elipse de polarización para los (ψ, Δ) dados.

    Asume luz incidente linealmente polarizada a 45°. Retorna arrays (Ex, Ey)
    correspondientes a un ciclo de fase ωt ∈ [0, 2π].
    """
    # 1. Conversión de las constantes elipsométricas a radianes para su evaluación trigonométrica continua
    psi = np.radians(psi_deg)
    delta = np.radians(delta_deg)
    
    # 2. Vector temporal equivalente (fase = ωt) variando a lo largo de un ciclo espacial completo (0 a 2π)
    t = np.linspace(0, 2 * np.pi, n_points)

    # 3. Proyecciones cartesianas (Ex, Ey) de la ecuación paramétrica de la elipse de Jones
    # El eje X representa el vector polarizado TE, asumiendo su fase como la referencia cero: E_x(t) = cos(ψ) * cos(ωt)
    Ex = np.cos(psi) * np.cos(t)
    # El eje Y representa el vector polarizado TM, desfasado por Δ respecto a TE, con amplitud modulada por sin(ψ)
    Ey = np.sin(psi) * np.cos(t + delta)
    return Ex, Ey


def ellipse_params(
    psi_deg: float, delta_deg: float
) -> tuple[float, float, float, str]:
    """Parámetros geométricos de la elipse: semiejes (a, b), inclinación, handedness.

    - a, b: semiejes mayor y menor
    - tilt_deg: ángulo de inclinación del semieje mayor respecto al eje x
    - handedness: "right" | "left" | "linear"
    """
    # 1. Transformamos ψ y Δ a radianes para los cálculos geométricos
    psi = np.radians(psi_deg)
    delta = np.radians(delta_deg)

    # 2. Precomputamos términos trigonométricos comunes que aparecen en el vector de Stokes
    sin2psi = np.sin(2 * psi)
    cos_delta = np.cos(delta)

    # 3. Ángulo de inclinación de la elipse (tilt o azimut θ)
    # tg(2θ) = tg(2ψ) * cos(Δ). Despejando θ vía arctan2 para considerar cuadrantes correctamente
    tilt = 0.5 * np.arctan2(sin2psi * cos_delta, np.cos(2 * psi))

    # 4. Ángulo de elipticidad (χ o chi)
    # sin(2χ) = sin(2ψ) * sin(Δ). Cuantifica qué tan "abierta" es la elipse (0 = lineal, 45 = circular)
    sin2chi = sin2psi * np.sin(delta)
    chi = 0.5 * np.arcsin(sin2chi)
    
    # 5. Longitud normalizada de los semiejes de la elipse de polarización
    # a: semieje mayor, b: semieje menor
    a = np.sqrt((1 + np.cos(2 * chi)) / 2)
    b = np.sqrt((1 - np.cos(2 * chi)) / 2) * np.sign(np.sin(2 * chi) + 1e-30)
    b_abs = abs(b)

    # 6. Clasificación de la quiralidad ("handedness") según el signo de sin(Δ)
    if abs(np.sin(delta)) < 1e-6:
        # Δ ≈ 0 o 180° -> elipse colapsada a línea
        handedness = "linear"
    elif np.sin(delta) > 0:
        # Δ > 0 -> retraso de fase genera rotación a la derecha (sentido antihorario óptico)
        handedness = "right"
    else:
        # Δ < 0 -> rotación a la izquierda
        handedness = "left"

    return float(a), float(b_abs), float(np.degrees(tilt)), handedness
