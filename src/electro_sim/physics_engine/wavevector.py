"""Helpers para trabajar con el vector de onda conservado en estructuras planas.

El motor sigue aceptando angulos en la API publica, pero internamente conviene
formular la propagacion en terminos de la componente tangencial conservada k_x
y la componente longitudinal k_z en cada medio.

Todas las componentes se manejan normalizadas por k_0 = 2*pi/lambda. Es decir,
el modulo total de la onda en un medio queda representado por n, y no por
`(2*pi/lambda) * n`. Ese factor global vuelve a aparecer solo al calcular la
fase acumulada dentro de una capa finita.
"""

from __future__ import annotations

import numpy as np
from numpy.lib.scimath import sqrt as csqrt
from numpy.typing import NDArray


def kx_from_angle(
    theta_i: NDArray[np.float64], incident_medium: dict[str, complex]
) -> NDArray[np.complex128]:
    """Calcula la componente tangencial conservada del vector de onda.

    En una interfaz plana homogénea, la componente paralela a la superficie se
    conserva al pasar de un medio a otro. En la formulación normalizada del
    proyecto:

        k_x = n_incidente * sin(theta_i)

    Args:
        theta_i: Ángulo de incidencia en radianes.
        incident_medium: Diccionario del medio incidente. Debe contener `n`.

    Returns:
        Arreglo complejo con la componente tangencial conservada.
    """
    # 1. Tomamos el seno geométrico del ángulo incidente.
    sin_theta_i = np.sin(theta_i).astype(complex)

    # 2. Escalamos por el índice complejo del medio incidente.
    #    Esto incorpora tanto propagación como posible absorción del medio.
    return incident_medium["n"] * sin_theta_i


def sin_theta_from_kx(
    medium: dict[str, complex], kx: NDArray[np.complex128]
) -> NDArray[np.complex128]:
    """Recupera el seno de propagación en un medio a partir de k_x.

    Una vez fijada la componente tangencial conservada, la ley de Snell se puede
    escribir como:

        sin(theta_medio) = k_x / n_medio

    Esto evita recomputar ángulos interfaz por interfaz y deja toda la geometría
    expresada en términos de la misma magnitud conservada.

    Args:
        medium: Diccionario del medio de interés. Debe contener `n`.
        kx: Componente tangencial conservada ya calculada.

    Returns:
        Seno complejo del ángulo de propagación en ese medio.
    """
    # Dividir por el índice del medio equivale a invertir la relación usada para k_x.
    return kx / medium["n"]


def kz_from_kx(
    medium: dict[str, complex], kx: NDArray[np.complex128]
) -> NDArray[np.complex128]:
    """Calcula la componente longitudinal del vector de onda en un medio.

    A partir de la identidad geométrica del vector de onda normalizado:

        n^2 = k_x^2 + k_z^2

    despejamos:

        k_z = sqrt(n^2 - k_x^2)

    La raíz debe manejarse en el plano complejo porque, por encima del ángulo
    crítico o en medios absorbentes, `k_z` deja de ser puramente real.

    Args:
        medium: Diccionario del medio de interés. Debe contener `n`.
        kx: Componente tangencial conservada.

    Returns:
        Componente longitudinal compleja `k_z`.
    """
    # 1. Construimos el radicando usando la versión normalizada de la relación
    #    k_x^2 + k_z^2 = n^2.
    radicand = (medium["n"] ** 2) - (kx ** 2)

    # 2. Usamos la raíz compleja de NumPy para conservar la rama físicamente útil.
    #    En TIR esta elección produce un k_z con parte imaginaria positiva, que
    #    representa decaimiento evanescente al penetrar en el medio transmitido.
    return csqrt(radicand)


def phase_from_kz(
    kz: NDArray[np.complex128], thickness_nm: float, wavelength_nm: float
) -> NDArray[np.complex128]:
    """Calcula la fase compleja acumulada al cruzar una capa finita.

    La fase de propagación usada por película delgada y TMM es:

        beta = (2*pi/λ) * d * k_z

    Como `k_z` puede ser complejo, el resultado también lo es:

    - la parte real controla la oscilación de fase;
    - la parte imaginaria controla el decaimiento o crecimiento exponencial.

    Args:
        kz: Componente longitudinal en la capa.
        thickness_nm: Espesor físico de la capa en nanómetros.
        wavelength_nm: Longitud de onda en vacío en nanómetros.

    Returns:
        Fase compleja acumulada a través de la capa.
    """
    # El prefactor 2*pi*d/lambda reintroduce la escala física que habíamos
    # separado al trabajar con k_x y k_z en forma normalizada.
    propagation_factor = (2 * np.pi * thickness_nm / wavelength_nm)
    return propagation_factor * kz