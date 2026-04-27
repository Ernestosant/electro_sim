"""Transfer Matrix Method vectorizado sobre el eje angular.

La matriz M = Π Mⱼ tiene shape `(2, 2, N_theta)` y la multiplicación se hace
con `np.einsum('ijn,jkn->ikn', ...)`. Con 30 capas y 500 ángulos el coste es
~0.5 ms en hardware moderno (vs ~200 ms del loop escalar del motor origen).
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from electro_sim.physics_engine.wavevector import kz_from_kx, phase_from_kz


def _polarization_admittance(
    medium: dict[str, complex], kz: NDArray[np.complex128], polarization: str
) -> NDArray[np.complex128]:
    """Calcula la admitancia óptica (q) para un medio dado, dependiendo de la polarización.

    La admitancia óptica q relaciona el campo magnético transversal con el campo eléctrico
    transversal. Para ondas TE (s) depende de la permeabilidad magnética μ, y para ondas 
    TM (p) depende de la permitividad eléctrica ε.

    Args:
        medium: Diccionario con las propiedades del medio ('eps' y 'mu').
        kz: Vector de onda perpendicular a la interfaz.
        polarization: "TE" o "TM".

    Returns:
        q: Admitancia óptica para la onda incidente.
    """
    if polarization == "TE":
        # Admitancia para polarización Transversal Eléctrica (onda s)
        # q = k_z / mu
        return kz / medium["mu"]
    
    # Admitancia para polarización Transversal Magnética (onda p)
    # q = k_z / eps
    return kz / medium["eps"]


def solve_tmm_vectorized(
    kx: NDArray[np.complex128],
    layers: list[dict],
    medium1: dict[str, complex],
    medium2: dict[str, complex],
    wavelength_nm: float,
    polarization: str,
) -> tuple[
    NDArray[np.complex128],
    NDArray[np.complex128],
    NDArray[np.complex128],
    NDArray[np.complex128],
]:
    """Resuelve el TMM para una lista de capas.

    Parameters
    ----------
    kx
        Componente tangencial conservada del vector de onda (array 1D).
    layers
        Lista de capas: cada una con keys 'n', 'eps', 'mu', 'thickness'.
    medium1, medium2
        Medios incidente y sustrato.
    wavelength_nm
        Longitud de onda de vacío.
    polarization
        "TE" o "TM".

    Returns
    -------
    r, t, q_inc, q_sub : ndarrays complejos, shape = kx.shape
    """
    # 1. Componentes longitudinales exteriores derivadas desde la magnitud conservada k_x.
    k1z = kz_from_kx(medium1, kx)
    k2z = kz_from_kx(medium2, kx)

    # 2. Admitancias del medio incidente (q_inc) y del sustrato (q_sub)
    q_inc = _polarization_admittance(medium1, k1z, polarization)
    q_sub = _polarization_admittance(medium2, k2z, polarization)

    # 3. Inicializamos la Matriz de Transferencia Total (M) como la matriz Identidad.
    # Dado que calculamos para N ángulos simultáneamente, el tensor tiene dimensiones (2, 2, N)
    N = kx.shape[0]
    M = np.zeros((2, 2, N), dtype=complex)
    M[0, 0] = 1.0
    M[1, 1] = 1.0

    # 4. Iteramos capa por capa multiplicando sus matrices de fase-interfaz.
    for layer in layers:
        # Cada capa toma su k_z a partir del mismo k_x conservado.
        kz_l = kz_from_kx(layer, kx)
        q_l = _polarization_admittance(layer, kz_l, polarization)

        # δ = (2π / λ) * d * k_z.
        delta = phase_from_kz(kz_l, layer["thickness"], wavelength_nm)

        cos_d = np.cos(delta)
        sin_d = np.sin(delta)

        # Construcción de la matriz de transferencia de la capa aislada (M_layer).
        # Con la convención temporal exp(i(k·r - wt)), los términos fuera de la
        # diagonal llevan signo negativo; este es el convenio que mantiene la
        # equivalencia con la ruta analítica de película delgada en medios lossless
        # y absorbentes.
        # |  cos(δ)         -i*sin(δ)/q  |
        # | -i*q*sin(δ)      cos(δ)      |
        M_layer = np.empty((2, 2, N), dtype=complex)
        M_layer[0, 0] = cos_d
        M_layer[0, 1] = -1j * sin_d / q_l
        M_layer[1, 0] = -1j * q_l * sin_d
        M_layer[1, 1] = cos_d

        # Multiplicación matricial (producto punto secuencial): M_total = M_total · M_layer
        # Usamos np.einsum para hacer la multiplicación (2x2) * (2x2) paralelizada sobre el eje N (los ángulos)
        M = np.einsum("ijn,jkn->ikn", M, M_layer)

    # 5. Extraemos la reflectancia (r) y transmitancia (t) del sistema completo desde la matriz total resultante
    # a partir del álgebra de los 4 elementos de M (M_11, M_12, M_21, M_22) acoplados con las admitancias exteriores.
    denom = q_inc * M[0, 0] + q_inc * q_sub * M[0, 1] + M[1, 0] + q_sub * M[1, 1]
    r = (q_inc * M[0, 0] + q_inc * q_sub * M[0, 1] - M[1, 0] - q_sub * M[1, 1]) / denom
    t = 2 * q_inc / denom

    return r, t, q_inc, q_sub
