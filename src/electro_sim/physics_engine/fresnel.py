"""Vectorized Fresnel engine.

Portado desde `C:\\Mis_proyectos\\Proyecto\\optic_simulator\\physics_engine.py`.
Conserva la API pública `FresnelEngine.calculate_coefficients(theta_i_deg)` que
acepta `float` (compatibilidad con tests existentes) **o** `ndarray` (ruta
rápida para barridos). Internamente todos los cálculos son vectorizados con
broadcast sobre el eje angular.

Fórmulas clave (de `physics_engine.py:56-253`):

- Impedancia/admitancia de polarización: q = kz/μ (TE), q = kz/ε (TM)
- Coeficientes de interfaz: r = (q₁-q₂)/(q₁+q₂); t = 2q₁/(q₁+q₂)
- Transmitancia de potencia: T = Re(q₂)/Re(q₁) · |t|²
- Película delgada: r_film = (r₀₁ + r₁₂·e^(2iβ))/(1 + r₀₁·r₁₂·e^(2iβ))
- Multicapa TMM: M = Π Mⱼ con Mⱼ = [[cos δ, i sin δ / qⱼ], [i qⱼ sin δ, cos δ]]
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.lib.scimath import sqrt as csqrt
from numpy.typing import ArrayLike, NDArray

from electro_sim.physics_engine.constants import FLUX_EPSILON, TRANSMITTANCE_LOG_EPSILON
from electro_sim.physics_engine.wavevector import (
    kx_from_angle,
    kz_from_kx,
    phase_from_kz,
    sin_theta_from_kx,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_medium(eps: complex | float, mu: complex | float) -> dict[str, complex]:
    """Construye un diccionario con las propiedades ópticas de un medio.
    
    A partir de la permitividad relativa (eps) y la permeabilidad magnética (mu),
    calcula el índice de refracción complejo (n) y la impedancia característica (eta).
    
    Args:
        eps: Permitividad dieléctrica relativa (ε).
        mu: Permeabilidad magnética relativa (μ).
        
    Returns:
        Diccionario con claves 'eps', 'mu', 'n' y 'eta'.
    """
    eps_c = complex(eps)
    mu_c = complex(mu)
    return {
        "eps": eps_c,
        "mu": mu_c,
        "n": csqrt(eps_c * mu_c),
        "eta": csqrt(mu_c / eps_c),
    }


def _polarization_admittance(
    medium: dict[str, complex], kz: NDArray[np.complex128], polarization: str
) -> NDArray[np.complex128]:
    """Calcula la admitancia óptica (q) para una polarización dada.
    
    La admitancia q relaciona los campos eléctrico y magnético tangenciales.
    - Para polarización TE (s): q = k_z / μ
    - Para polarización TM (p): q = k_z / ε
    
    Args:
        medium: Diccionario con propiedades del medio ('eps', 'mu').
        kz: Componente z del vector de onda.
        polarization: "TE" o "TM".
        
    Returns:
        Arreglo con las admitancias calculadas.
    """
    if polarization == "TE":
        return kz / medium["mu"]
    return kz / medium["eps"]


def _interface_coefficients(
    q_left: NDArray[np.complex128], q_right: NDArray[np.complex128]
) -> tuple[NDArray[np.complex128], NDArray[np.complex128]]:
    """Calcula los coeficientes de amplitud de Fresnel (r, t) en una interfaz simple.
    
    A partir de las admitancias de ambos lados de la interfaz:
    - Reflexión en amplitud: r = (q_incidente - q_transmitido) / (q_incidente + q_transmitido)
    - Transmisión en amplitud: t = 2 * q_incidente / (q_incidente + q_transmitido)
    """
    denominator = q_left + q_right
    r = (q_left - q_right) / denominator
    t = (2 * q_left) / denominator
    return r, t


def _power_transmittance(
    q_incident: NDArray[np.complex128],
    q_transmitted: NDArray[np.complex128],
    t_value: NDArray[np.complex128],
) -> NDArray[np.float64]:
    """Calcula la transmitancia de potencia (T) a partir de la amplitud (t).
    
    Fórmula física:
        T = [Re(q_transmitido) / Re(q_incidente)] * |t|^2
        
    Esta fórmula asegura la conservación de energía considerando la diferencia de 
    impedancias entre el medio incidente y el de salida.
    """
    incident_flux = np.real(q_incident)
    transmitted_flux = np.real(q_transmitted)
    safe_incident = np.where(np.abs(incident_flux) < FLUX_EPSILON, 1.0, incident_flux)
    T = np.where(
        np.abs(incident_flux) < FLUX_EPSILON,
        0.0,
        (transmitted_flux / safe_incident) * np.abs(t_value) ** 2
    )
    return np.maximum(0.0, np.real(T))


def _absorbance(T: NDArray[np.float64]) -> NDArray[np.float64]:
    """Calcula la absorbancia óptica (-log10(T)) a partir de la transmitancia.
    
    Aplica una cota de seguridad (TRANSMITTANCE_LOG_EPSILON) para evitar
    logaritmos de cero matemático en zonas de opacidad total.
    """
    safe_T = np.where(T > TRANSMITTANCE_LOG_EPSILON, T, 1.0)
    value = -np.log10(safe_T)
    return np.where(T > TRANSMITTANCE_LOG_EPSILON, value, np.inf)


def _visual_angle_array(sin_theta: NDArray[np.complex128]) -> NDArray[np.float64]:
    """Recupera el ángulo físico real (en grados) a partir del seno de fase complejo.
    
    Para ángulos post-críticos (TIR), el seno complejo excede 1.0. Esta función
    enmascara esos casos (retornando NaN) y calcula el ángulo real válido.
    """
    real_part = sin_theta.real
    imag_part = sin_theta.imag
    valid = (np.abs(imag_part) < 1e-9) & (np.abs(real_part) <= 1.0)
    safe = np.where(valid, np.clip(real_part, -1.0, 1.0), 0.0)
    angle = np.degrees(np.arcsin(safe))
    return np.where(valid, angle, np.nan)


def _build_channel(
    r: NDArray[np.complex128],
    t: NDArray[np.complex128],
    q_inc: NDArray[np.complex128],
    q_trans: NDArray[np.complex128],
) -> dict[str, NDArray[Any]]:
    """Empaqueta y calcula los coeficientes de potencia finales (R, T, A).
    
    - Reflectancia de potencia: R = |r|^2
    - Transmitancia de potencia: T = (calculada arriba)
    - Absorptancia: A = 1 - R - T  (fracción absorbida dentro de la estructura)
    - Absorbancia óptica: -log10(T)
    """
    R = np.abs(r) ** 2
    T = _power_transmittance(q_inc, q_trans, t)
    A = np.maximum(0.0, 1.0 - R - T)
    return {
        "r": r,
        "t": t,
        "R": R,
        "T": T,
        "A": A,
        "Absorbance": _absorbance(T),
        "phi_r": np.angle(r, deg=True),
        "phi_t": np.angle(t, deg=True),
    }


def _scalarize(value: Any) -> Any:
    """Reduce arrays de shape (1,) a escalares Python, recursivamente.

    Preserva el contrato del motor original cuando se invoca con `theta_i_deg`
    escalar (tests existentes asumen floats/complex puros, no arrays).
    """
    if isinstance(value, dict):
        return {k: _scalarize(v) for k, v in value.items()}
    if isinstance(value, np.ndarray):
        if value.ndim == 0:
            out = value.item()
        elif value.size == 1:
            out = value.ravel()[0].item()
        else:
            return value
        if isinstance(out, complex):
            return out
        if isinstance(out, float) and np.isnan(out):
            return None
        return float(out) if not isinstance(out, complex) else out
    if isinstance(value, np.floating):
        v = float(value)
        return None if np.isnan(v) else v
    if isinstance(value, np.complexfloating):
        return complex(value)
    return value


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class FresnelEngine:
    """Motor Fresnel generalizado (ε, μ complejos) con soporte vectorizado.

    Acepta un ángulo escalar (retorna dict con valores escalares, idéntico al
    motor origen) o un array de ángulos en grados (retorna dict con arrays).
    """

    def __init__(
        self,
        eps1: complex | float,
        mu1: complex | float,
        eps2: complex | float,
        mu2: complex | float,
        film: dict | None = None,
        wavelength: float = 550.0,
        layers: list[dict] | None = None,
    ) -> None:
        self.medium1 = _build_medium(eps1, mu1)
        self.medium2 = _build_medium(eps2, mu2)

        self.eps1 = self.medium1["eps"]
        self.mu1 = self.medium1["mu"]
        self.eps2 = self.medium2["eps"]
        self.mu2 = self.medium2["mu"]
        self.n1 = self.medium1["n"]
        self.n2 = self.medium2["n"]
        self.eta1 = self.medium1["eta"]
        self.eta2 = self.medium2["eta"]

        self.wavelength = float(wavelength)
        if self.wavelength <= 0:
            raise ValueError("wavelength must be positive")

        self.film: dict | None = None
        if film:
            thickness = float(film.get("thickness", 0.0))
            if thickness > 0:
                self.film = _build_medium(film.get("eps", 1.0), film.get("mu", 1.0))
                self.film["thickness"] = thickness

        self.layers: list[dict] = []
        if layers:
            for layer_spec in layers:
                thickness = float(layer_spec.get("thickness", 0.0))
                if thickness > 0:
                    lm = _build_medium(layer_spec.get("eps", 1.0), layer_spec.get("mu", 1.0))
                    lm["thickness"] = thickness
                    self.layers.append(lm)

    # -- Single interface -------------------------------------------------

    def _calculate_single_interface_vec(self, theta_i: NDArray[np.float64]) -> dict:
        # Formulación k_x-first: la componente tangencial se conserva en toda la interfaz.
        kx = kx_from_angle(theta_i, self.medium1)
        sin_theta_t = sin_theta_from_kx(self.medium2, kx)
        k1z = kz_from_kx(self.medium1, kx)
        k2z = kz_from_kx(self.medium2, kx)

        result: dict[str, Any] = {}
        for polarization in ("TE", "TM"):
            # 5. Calculamos la admitancia óptica (q) para la polarización actual en cada medio
            # TE: q = kz / mu  |  TM: q = kz / eps
            q1 = _polarization_admittance(self.medium1, k1z, polarization)
            q2 = _polarization_admittance(self.medium2, k2z, polarization)
            
            # 6. Obtenemos los coeficientes de amplitud de Fresnel (r, t) en la interfaz
            r, t = _interface_coefficients(q1, q2)
            
            # 7. Convertimos amplitudes en coeficientes de potencia (Reflectancia, Transmitancia)
            result[polarization] = _build_channel(r, t, q1, q2)

        result["unpolarized"] = {
            "R": (result["TE"]["R"] + result["TM"]["R"]) / 2,
            "T": (result["TE"]["T"] + result["TM"]["T"]) / 2,
            "A": (result["TE"]["A"] + result["TM"]["A"]) / 2,
        }
        result["angles"] = {
            "theta_i": np.degrees(theta_i),
            "theta_film": np.full_like(theta_i, np.nan),
            "theta_t": _visual_angle_array(sin_theta_t),
        }
        result["thin_film"] = None
        return result

    # -- Thin film --------------------------------------------------------

    def _calculate_thin_film_vec(self, theta_i: NDArray[np.float64]) -> dict:
        film = self.film
        assert film is not None
        
        # La estructura plana conserva k_x en todos los medios paralelos.
        kx = kx_from_angle(theta_i, self.medium1)
        sin_theta_film = sin_theta_from_kx(film, kx)
        sin_theta_t = sin_theta_from_kx(self.medium2, kx)
        k1z = kz_from_kx(self.medium1, kx)
        kfz = kz_from_kx(film, kx)
        k2z = kz_from_kx(self.medium2, kx)

        # beta = (2 * pi / lambda) * n_film * d * cos(theta_film) = (2 * pi * d / lambda) * kfz
        beta = phase_from_kz(kfz, film["thickness"], self.wavelength)
        
        # 7. Factor de fase de ida y vuelta (round-trip) dentro de la cavidad de la película: exp(i * 2 * beta)
        round_trip_phase = np.exp(2j * beta)

        result: dict[str, Any] = {}
        for polarization in ("TE", "TM"):
            # 8. Admitancias de los tres medios para la polarización dada
            q1 = _polarization_admittance(self.medium1, k1z, polarization)
            qf = _polarization_admittance(film, kfz, polarization)
            q2 = _polarization_admittance(self.medium2, k2z, polarization)

            # 9. Coeficientes de amplitud de Fresnel para las dos interfaces individuales
            # Interfaz 1: Medio incidente -> Película
            r01, t01 = _interface_coefficients(q1, qf)
            # Interfaz 2: Película -> Sustrato
            r12, t12 = _interface_coefficients(qf, q2)
            
            # 10. Coeficientes efectivos totales usando la fórmula de Airy (sumatoria infinita de reflexiones internas)
            # Denominador común de la interferencia múltiple de Airy
            denominator = 1 + r01 * r12 * round_trip_phase
            
            # Reflexión total de la película (suma coherente de ecos reflejados)
            r = (r01 + r12 * round_trip_phase) / denominator
            
            # Transmisión total de la película (incluye el desfase de un viaje 'beta' al cruzarla)
            t = (t01 * t12 * np.exp(1j * beta)) / denominator
            
            # 11. Conversión a flujo de potencias (R, T)
            result[polarization] = _build_channel(r, t, q1, q2)

        result["unpolarized"] = {
            "R": (result["TE"]["R"] + result["TM"]["R"]) / 2,
            "T": (result["TE"]["T"] + result["TM"]["T"]) / 2,
            "A": (result["TE"]["A"] + result["TM"]["A"]) / 2,
        }
        result["angles"] = {
            "theta_i": np.degrees(theta_i),
            "theta_film": _visual_angle_array(sin_theta_film),
            "theta_t": _visual_angle_array(sin_theta_t),
        }
        result["thin_film"] = {
            "thickness": film["thickness"],
            "wavelength": self.wavelength,
            "phase_shift_deg": np.degrees(beta.real),
        }
        return result

    # -- Multilayer TMM ---------------------------------------------------

    def _calculate_multilayer_vec(self, theta_i: NDArray[np.float64]) -> dict:
        from electro_sim.physics_engine.tmm import solve_tmm_vectorized

        # En multicapa la magnitud conservada es k_x; cada capa deriva su propio k_z.
        kx = kx_from_angle(theta_i, self.medium1)
        sin_theta_t = sin_theta_from_kx(self.medium2, kx)

        result: dict[str, Any] = {}
        for polarization in ("TE", "TM"):
            # 4. Invocación al solucionador de Matriz de Transferencia (TMM)
            # El algoritmo completo está en `tmm.py`, el cual maneja la sumatoria matricial
            r, t, q_inc, q_sub = solve_tmm_vectorized(
                kx=kx,
                layers=self.layers,
                medium1=self.medium1,
                medium2=self.medium2,
                wavelength_nm=self.wavelength,
                polarization=polarization,
            )
            # 5. Calculamos Potencias
            result[polarization] = _build_channel(r, t, q_inc, q_sub)

        result["unpolarized"] = {
            "R": (result["TE"]["R"] + result["TM"]["R"]) / 2,
            "T": (result["TE"]["T"] + result["TM"]["T"]) / 2,
            "A": (result["TE"]["A"] + result["TM"]["A"]) / 2,
        }

        first_layer = self.layers[0] if self.layers else None
        if first_layer is not None:
            sin_theta_first = sin_theta_from_kx(first_layer, kx)
            k_first = kz_from_kx(first_layer, kx)
            beta_first = phase_from_kz(k_first, first_layer["thickness"], self.wavelength)
            result["angles"] = {
                "theta_i": np.degrees(theta_i),
                "theta_film": _visual_angle_array(sin_theta_first),
                "theta_t": _visual_angle_array(sin_theta_t),
            }
            result["thin_film"] = {
                "thickness": first_layer["thickness"],
                "wavelength": self.wavelength,
                "phase_shift_deg": np.degrees(beta_first.real),
            }
        else:
            result["angles"] = {
                "theta_i": np.degrees(theta_i),
                "theta_film": np.full_like(theta_i, np.nan),
                "theta_t": _visual_angle_array(sin_theta_t),
            }
            result["thin_film"] = None

        result["multilayer"] = {
            "num_layers": len(self.layers),
            "total_thickness": sum(l["thickness"] for l in self.layers),
        }
        return result

    # -- Public API -------------------------------------------------------

    def calculate_coefficients(self, theta_i_deg: ArrayLike) -> dict:
        """Fresnel coefficients at one or many angles.

        - `theta_i_deg` escalar → retorno escalar (compat con tests).
        - `theta_i_deg` array  → retorno con arrays del mismo shape.
        """
        arr = np.asarray(theta_i_deg, dtype=float)
        was_scalar = arr.ndim == 0
        theta_arr = np.atleast_1d(arr)
        theta_rad = np.radians(theta_arr)

        if self.layers:
            result = self._calculate_multilayer_vec(theta_rad)
        elif self.film:
            result = self._calculate_thin_film_vec(theta_rad)
        else:
            result = self._calculate_single_interface_vec(theta_rad)

        if was_scalar:
            return _scalarize(result)
        return result

    # -- Special angles ---------------------------------------------------

    def get_critical_angle(self) -> float | None:
        """Calcula el ángulo crítico de reflexión total interna (TIR).
        
        El ángulo crítico solo existe cuando la luz viaja de un medio más denso 
        a uno menos denso (n1 > n2). Más allá de este ángulo, toda la luz se 
        refleja y no hay haz transmitido.
        
        Returns:
            El ángulo crítico en grados si existe, o None si no se cumple n1 > n2.
        """
        n1_real = self.n1.real
        n2_real = self.n2.real
        if n1_real > n2_real:
            return float(np.degrees(np.arcsin(n2_real / n1_real)))
        return None

    def get_brewster_angle(self) -> float:
        """Brewster TM angle (numérico si hay film; analítico si no)."""
        if self.film:
            angles = np.linspace(0, 89.9, 600)
            result = self.calculate_coefficients(angles)
            return float(angles[int(np.argmin(result["TM"]["R"]))])

        if self.mu1 == 1 and self.mu2 == 1:
            return float(np.degrees(np.arctan(self.n2.real / self.n1.real)))

        return float(np.degrees(np.arctan(np.real(self.n2 / self.n1))))

    # -- Spectral sweep (vectorized) --------------------------------------

    @staticmethod
    def calculate_spectral(
        model1: Any,
        mu1: complex | float,
        model2: Any,
        mu2: complex | float,
        theta_i_deg: float,
        wavelengths_nm: ArrayLike,
        layers_spec: list[dict] | None = None,
    ) -> dict[str, NDArray[Any]]:
        """Barrido espectral. Preserva la firma del motor origen.

        Elimina el loop de `physics_engine.py:356-372` usando arrays de ε(λ).
        Para multicapa usa loop interno sobre λ (cada λ cambia todas las ε),
        pero la evaluación por-λ es ya vectorizada sobre el ángulo único.
        """
        from electro_sim.physics_engine.dispersion import DispersionModel

        wls = np.asarray(wavelengths_nm, dtype=float)
        n_wl = len(wls)

        def _eps_array(model_or_eps: Any) -> NDArray[np.complex128]:
            if isinstance(model_or_eps, DispersionModel):
                return np.asarray(model_or_eps.epsilon(wls), dtype=complex)
            return np.full(n_wl, complex(model_or_eps))

        eps1_arr = _eps_array(model1)
        eps2_arr = _eps_array(model2)
        mu1_c = complex(mu1)
        mu2_c = complex(mu2)

        R_TE = np.empty(n_wl)
        R_TM = np.empty(n_wl)
        T_TE = np.empty(n_wl)
        T_TM = np.empty(n_wl)
        A_TE = np.empty(n_wl)
        A_TM = np.empty(n_wl)

        layer_eps_arrays: list[NDArray[np.complex128]] = []
        if layers_spec:
            for ls in layers_spec:
                model = ls.get("model", ls.get("eps", 1.0))
                layer_eps_arrays.append(_eps_array(model))

        for i, wl in enumerate(wls):
            layers = None
            if layers_spec:
                layers = []
                for j, ls in enumerate(layers_spec):
                    layers.append(
                        {
                            "eps": complex(layer_eps_arrays[j][i]),
                            "mu": ls.get("mu", 1.0),
                            "thickness": ls["thickness"],
                        }
                    )

            engine = FresnelEngine(
                complex(eps1_arr[i]),
                mu1_c,
                complex(eps2_arr[i]),
                mu2_c,
                wavelength=float(wl),
                layers=layers,
            )
            res = engine.calculate_coefficients(theta_i_deg)
            R_TE[i] = res["TE"]["R"]
            R_TM[i] = res["TM"]["R"]
            T_TE[i] = res["TE"]["T"]
            T_TM[i] = res["TM"]["T"]
            A_TE[i] = res["TE"]["A"]
            A_TM[i] = res["TM"]["A"]

        return {
            "wavelengths": wls,
            "R_TE": R_TE,
            "R_TM": R_TM,
            "T_TE": T_TE,
            "T_TM": T_TM,
            "A_TE": A_TE,
            "A_TM": A_TM,
            "R_unpol": (R_TE + R_TM) / 2,
            "T_unpol": (T_TE + T_TM) / 2,
            "A_unpol": (A_TE + A_TM) / 2,
        }
