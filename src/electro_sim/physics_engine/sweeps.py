"""Barridos vectorizados: angular, espectral, heatmap 2D y espesor.

Funciones puras que aceptan un `SimulationRequest` y devuelven el dataclass de
resultado correspondiente con `compute_ms` medido.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
from numpy.typing import NDArray

from electro_sim.physics_engine.dispersion import DispersionModel
from electro_sim.physics_engine.fresnel import FresnelEngine
from electro_sim.physics_engine.types import (
    AngularResult,
    HeatmapResult,
    SimulationRequest,
    SpectralResult,
    ThicknessResult,
)


def _layers_from_request(req: SimulationRequest) -> list[dict]:
    """Convierte la especificación de capas del request en diccionarios para el motor."""
    return [
        {"eps": complex(l.eps), "mu": complex(l.mu), "thickness": float(l.thickness_nm)}
        for l in req.layers
    ]


def _film_from_request(req: SimulationRequest) -> dict | None:
    """Convierte la especificación de la película delgada de la UI al formato del motor."""
    if req.film_thickness_nm > 0:
        return {
            "eps": complex(req.film_eps),
            "mu": complex(req.film_mu),
            "thickness": float(req.film_thickness_nm),
        }
    return None


def sweep_angular(req: SimulationRequest) -> AngularResult:
    """Ejecuta una simulación de barrido angular.
    
    Esta función fija la longitud de onda de la luz incidente y varía el ángulo de 
    incidencia (theta_i) desde un valor mínimo hasta un valor máximo. Retorna los 
    coeficientes de reflexión, transmisión y absorptancia para cada ángulo.
    
    Args:
        req: Objeto `SimulationRequest` que contiene todos los parámetros físicos (medios, capas).
        
    Returns:
        Un objeto `AngularResult` con arrays paralelos para los ángulos evaluados y los coeficientes.
    """
    t0 = time.perf_counter()

    # Extraemos el rango angular del request y generamos un array de puntos equiespaciados
    a_min, a_max, a_n = req.angle_range_deg
    angles = np.linspace(a_min, a_max, a_n)

    # Instanciamos el motor de Fresnel base. 
    # El motor interno está vectorizado, por lo que puede procesar todo el array 'angles' de una vez
    # sin necesidad de bucles iterativos en Python, lo que aumenta dramáticamente el rendimiento.
    engine = FresnelEngine(
        eps1=complex(req.medium1.eps),
        mu1=complex(req.medium1.mu),
        eps2=complex(req.medium2.eps),
        mu2=complex(req.medium2.mu),
        film=_film_from_request(req),
        wavelength=float(req.wavelength_nm),
        layers=_layers_from_request(req) or None,
    )

    # Calculamos todos los coeficientes en una sola llamada vectorizada
    res = engine.calculate_coefficients(angles)

    compute_ms = (time.perf_counter() - t0) * 1000.0
    return AngularResult(
        angles_deg=angles,
        R_TE=res["TE"]["R"],
        R_TM=res["TM"]["R"],
        R_unpol=res["unpolarized"]["R"],
        T_TE=res["TE"]["T"],
        T_TM=res["TM"]["T"],
        T_unpol=res["unpolarized"]["T"],
        A_TE=res["TE"]["A"],
        A_TM=res["TM"]["A"],
        A_unpol=res["unpolarized"]["A"],
        r_TE=res["TE"]["r"],
        r_TM=res["TM"]["r"],
        t_TE=res["TE"]["t"],
        t_TM=res["TM"]["t"],
        phi_r_TE=res["TE"]["phi_r"],
        phi_r_TM=res["TM"]["phi_r"],
        phi_t_TE=res["TE"]["phi_t"],
        phi_t_TM=res["TM"]["phi_t"],
        brewster_deg=engine.get_brewster_angle(),
        critical_deg=engine.get_critical_angle(),
        compute_ms=compute_ms,
    )


def _resolve_eps_array(
    source: Any, wavelengths_nm: NDArray[np.float64]
) -> NDArray[np.complex128]:
    """Evalúa la permitividad dieléctrica a través de un rango de longitudes de onda.
    
    Acepta tanto modelos de dispersión (Drude, Sellmeier) como constantes complejas.
    La salida siempre es un arreglo complejo de la misma longitud que el barrido.
    """
    # Si el origen es un modelo dispersivo, evaluamos epsilon(lambda) en cada punto.
    if isinstance(source, DispersionModel):
        return np.asarray(source.epsilon(wavelengths_nm), dtype=complex)

    # Si el material no dispersa, replicamos el mismo epsilon para todo el barrido.
    return np.full(len(wavelengths_nm), complex(source))


def sweep_spectral(
    req: SimulationRequest,
    model1: Any | None = None,
    model2: Any | None = None,
    layer_models: list[Any] | None = None,
) -> SpectralResult:
    """Ejecuta una simulación de barrido espectral.
    
    Esta función fija el ángulo de incidencia y varía la longitud de onda de la luz 
    incidente. Si se proporcionan modelos de dispersión (ej. Lorentz-Drude), la 
    permitividad (ε) de los materiales se recalcula en cada paso de longitud de onda.
    
    Args:
        req: Objeto `SimulationRequest` con los parámetros del entorno.
        model1: Modelo de dispersión opcional para el medio de incidencia.
        model2: Modelo de dispersión opcional para el medio de transmisión/sustrato.
        layer_models: Modelos de dispersión opcionales para las capas intermedias.
        
    Returns:
        Un objeto `SpectralResult` que contiene la respuesta óptica en función de λ.
    """
    t0 = time.perf_counter()

    # Generamos el rango de longitudes de onda
    wl_min, wl_max, wl_n = req.wavelength_range_nm
    wls = np.linspace(wl_min, wl_max, wl_n)

    # 1. Resolvemos epsilon(lambda) para los medios exterior e interior.
    #    Si un medio usa preset dispersivo, este paso recalcula su respuesta en todo el espectro.
    #    Si el medio es constante, el arreglo resultante solo repite el mismo valor complejo.
    eps1_arr = (
        _resolve_eps_array(model1 if model1 is not None else req.medium1.eps, wls)
    )
    eps2_arr = (
        _resolve_eps_array(model2 if model2 is not None else req.medium2.eps, wls)
    )
    mu1 = complex(req.medium1.mu)
    mu2 = complex(req.medium2.mu)

    # 2. Repetimos la misma lógica para cada capa intermedia.
    #    Aquí se arma una lista de arreglos: un arreglo epsilon(lambda) por capa.
    layer_eps_arrays: list[NDArray[np.complex128]] = []
    if layer_models is not None:
        for m in layer_models:
            layer_eps_arrays.append(_resolve_eps_array(m, wls))
    elif req.layers:
        # Si no hay modelo dispersivo explícito, asumimos permitividad constante en todo el barrido.
        for l in req.layers:
            layer_eps_arrays.append(np.full(wl_n, complex(l.eps)))

    R_TE = np.empty(wl_n)
    R_TM = np.empty(wl_n)
    T_TE = np.empty(wl_n)
    T_TM = np.empty(wl_n)
    A_TE = np.empty(wl_n)
    A_TM = np.empty(wl_n)

    # 3. Recorremos lambda de manera explícita.
    #    A diferencia del barrido angular, aquí cada paso cambia epsilon de medios y capas.
    #    Vectorizar simultáneamente todas las lambdas implicaría tensorizar también la
    #    estructura multicapa completa; por ahora se privilegia claridad y costo razonable.
    for i, wl in enumerate(wls):
        layers = None
        if req.layers:
            # Construimos la pila de capas evaluada exactamente en lambda_i.
            layers = [
                {
                    "eps": complex(layer_eps_arrays[j][i]),
                    "mu": complex(l.mu),
                    "thickness": float(l.thickness_nm),
                }
                for j, l in enumerate(req.layers)
            ]

        # 4. Reinstanciamos el motor con las propiedades ópticas correspondientes a esta lambda.
        #    Cada iteración representa un problema físico distinto porque cambian los materiales.
        engine = FresnelEngine(
            eps1=complex(eps1_arr[i]),
            mu1=mu1,
            eps2=complex(eps2_arr[i]),
            mu2=mu2,
            film=_film_from_request(req),
            wavelength=float(wl),
            layers=layers,
        )
        # 5. Para cada lambda resolvemos el sistema en el ángulo fijo del request.
        res = engine.calculate_coefficients(req.fixed_angle_deg)
        R_TE[i] = res["TE"]["R"]
        R_TM[i] = res["TM"]["R"]
        T_TE[i] = res["TE"]["T"]
        T_TM[i] = res["TM"]["T"]
        A_TE[i] = res["TE"]["A"]
        A_TM[i] = res["TM"]["A"]

    compute_ms = (time.perf_counter() - t0) * 1000.0
    return SpectralResult(
        wavelengths_nm=wls,
        R_TE=R_TE,
        R_TM=R_TM,
        R_unpol=(R_TE + R_TM) / 2,
        T_TE=T_TE,
        T_TM=T_TM,
        T_unpol=(T_TE + T_TM) / 2,
        A_TE=A_TE,
        A_TM=A_TM,
        compute_ms=compute_ms,
    )


def sweep_heatmap(
    req: SimulationRequest,
    model1: Any | None = None,
    model2: Any | None = None,
    layer_models: list[Any] | None = None,
) -> HeatmapResult:
    """Simulación combinada espectro-angular (Mapa de Calor 2D).
    
    Genera matrices bidimensionales (R y T en función de θ y λ). Esta función aprovecha
    la vectorización angular interna de `FresnelEngine` e itera externamente sobre el 
    espectro de longitudes de onda.
    
    Args:
        req: Objeto `SimulationRequest` con los parámetros y rangos a explorar.
        model1: Modelo dispersivo del medio 1 (opcional).
        model2: Modelo dispersivo del sustrato (opcional).
        layer_models: Modelos dispersivos de las capas (opcional).
        
    Returns:
        Objeto `HeatmapResult` conteniendo matrices (shape [N_lambda, N_theta]) 
        con la reflectancia y transmitancia evaluadas.
    """
    t0 = time.perf_counter()

    # El heatmap combina dos ejes independientes:
    # - angulo incidente a lo largo de las columnas;
    # - longitud de onda a lo largo de las filas.
    a_min, a_max, a_n = req.angle_range_deg
    angles = np.linspace(a_min, a_max, a_n)
    wl_min, wl_max, wl_n = req.wavelength_range_nm
    wls = np.linspace(wl_min, wl_max, wl_n)

    # Igual que en el barrido espectral, resolvemos epsilon(lambda) para cada medio.
    eps1_arr = (
        _resolve_eps_array(model1 if model1 is not None else req.medium1.eps, wls)
    )
    eps2_arr = (
        _resolve_eps_array(model2 if model2 is not None else req.medium2.eps, wls)
    )
    mu1 = complex(req.medium1.mu)
    mu2 = complex(req.medium2.mu)

    layer_eps_arrays: list[NDArray[np.complex128]] = []
    if layer_models is not None:
        for m in layer_models:
            layer_eps_arrays.append(_resolve_eps_array(m, wls))
    elif req.layers:
        # Si no hay dispersión explícita en capas, cada fila del heatmap reutiliza la misma epsilon.
        for l in req.layers:
            layer_eps_arrays.append(np.full(wl_n, complex(l.eps)))

    R_TE = np.empty((wl_n, a_n))
    R_TM = np.empty((wl_n, a_n))
    T_TE = np.empty((wl_n, a_n))
    T_TM = np.empty((wl_n, a_n))

    # Recorremos lambda en el eje externo y resolvemos todos los angulos de esa fila de una sola vez.
    for i, wl in enumerate(wls):
        layers = None
        if req.layers:
            # Armamos la estructura evaluada en esta lambda para producir la fila i del mapa.
            layers = [
                {
                    "eps": complex(layer_eps_arrays[j][i]),
                    "mu": complex(l.mu),
                    "thickness": float(l.thickness_nm),
                }
                for j, l in enumerate(req.layers)
            ]

        # Cada fila del heatmap corresponde a un problema óptico distinto en longitud de onda.
        engine = FresnelEngine(
            eps1=complex(eps1_arr[i]),
            mu1=mu1,
            eps2=complex(eps2_arr[i]),
            mu2=mu2,
            film=_film_from_request(req),
            wavelength=float(wl),
            layers=layers,
        )
        
        # El motor interno ya está vectorizado en ángulo, así que la fila completa sale en una llamada.
        res = engine.calculate_coefficients(angles)
        
        # Guardamos la fila i en matrices con shape (N_lambda, N_theta).
        # Esta convención facilita leer el eje vertical como lambda y el horizontal como ángulo.
        R_TE[i] = res["TE"]["R"]
        R_TM[i] = res["TM"]["R"]
        T_TE[i] = res["TE"]["T"]
        T_TM[i] = res["TM"]["T"]

    compute_ms = (time.perf_counter() - t0) * 1000.0
    return HeatmapResult(
        angles_deg=angles,
        wavelengths_nm=wls,
        R_TE=R_TE,
        R_TM=R_TM,
        R_unpol=(R_TE + R_TM) / 2,
        T_TE=T_TE,
        T_TM=T_TM,
        T_unpol=(T_TE + T_TM) / 2,
        compute_ms=compute_ms,
    )


def sweep_thickness(
    req: SimulationRequest,
    layer_index: int = 0,
) -> ThicknessResult:
    """Barrido iterativo del espesor físico de una película delgada.
    
    Esta simulación fija tanto el ángulo de incidencia como la longitud de onda, 
    y varía exclusivamente el espesor (grosor) de una de las capas. Si se provee 
    una estructura multicapa, se varíará la capa indicada en `layer_index`.
    
    Este tipo de simulación es especialmente útil para observar cómo se comportan 
    interferómetros o capas antirreflejo a medida que cambia el camino óptico en 
    la estructura.
    
    Args:
        req: Objeto `SimulationRequest` con parámetros de entorno y materiales.
        layer_index: Índice (0-based) de la capa multicapa cuyo espesor se variará.
        
    Returns:
        Objeto `ThicknessResult` con los coeficientes ópticos en función del espesor evaluado.
    """
    t0 = time.perf_counter()

    d_min, d_max, d_n = req.thickness_range_nm
    thicknesses = np.linspace(d_min, d_max, d_n)

    R_TE = np.empty(d_n)
    R_TM = np.empty(d_n)
    T_TE = np.empty(d_n)
    T_TM = np.empty(d_n)

    base_layers = _layers_from_request(req)

    # Aquí el parámetro barrido es el espesor físico, así que resolvemos un problema por cada d_i.
    for i, d in enumerate(thicknesses):
        layers = None
        film = None
        if base_layers:
            layers = [dict(l) for l in base_layers]
            # Si existe una pila multicapa, modificamos solo la capa indicada y dejamos las demás fijas.
            if 0 <= layer_index < len(layers):
                layers[layer_index]["thickness"] = float(d)
        else:
            # Si no hay pila de capas, interpretamos el barrido como una película simple entre medios externos.
            film = {
                "eps": complex(req.film_eps),
                "mu": complex(req.film_mu),
                "thickness": float(d),
            }

        engine = FresnelEngine(
            eps1=complex(req.medium1.eps),
            mu1=complex(req.medium1.mu),
            eps2=complex(req.medium2.eps),
            mu2=complex(req.medium2.mu),
            film=film if (layers is None and d > 0) else None,
            wavelength=float(req.wavelength_nm),
            layers=layers,
        )
        res = engine.calculate_coefficients(req.fixed_angle_deg)
        R_TE[i] = res["TE"]["R"]
        R_TM[i] = res["TM"]["R"]
        T_TE[i] = res["TE"]["T"]
        T_TM[i] = res["TM"]["T"]

    compute_ms = (time.perf_counter() - t0) * 1000.0
    return ThicknessResult(
        thicknesses_nm=thicknesses,
        R_TE=R_TE,
        R_TM=R_TM,
        R_unpol=(R_TE + R_TM) / 2,
        T_TE=T_TE,
        T_TM=T_TM,
        T_unpol=(T_TE + T_TM) / 2,
        compute_ms=compute_ms,
    )
