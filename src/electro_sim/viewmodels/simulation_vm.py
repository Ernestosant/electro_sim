"""ViewModel central: agrega estado de los panels y emite SimulationRequest.

Escucha cambios de los panels (materiales, capas, fuente) vía señales, arma el
`SimulationRequest` frozen y lo emite. El servicio decide si recalcular.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal

from electro_sim.physics_engine.dispersion import DispersionModel
from electro_sim.physics_engine.types import (
    Layer,
    Medium,
    SimulationMode,
    SimulationRequest,
)


class SimulationVM(QObject):
    request_simulation = pyqtSignal(object)  # SimulationRequest
    angular_ready = pyqtSignal(object)       # AngularResult
    spectral_ready = pyqtSignal(object)
    heatmap_ready = pyqtSignal(object)
    thickness_ready = pyqtSignal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._request = SimulationRequest(
            medium1=Medium(eps=1.0 + 0j, mu=1.0 + 0j, name="Air"),
            medium2=Medium(eps=2.25 + 0j, mu=1.0 + 0j, name="Glass (n=1.5)"),
            layers=(),
            film_thickness_nm=0.0,
            wavelength_nm=550.0,
            angle_range_deg=(0.0, 89.9, 500),
            fixed_angle_deg=45.0,
            polarization="unpolarized",
            mode="angular",
        )
        self._dispersive_sources: dict[str, DispersionModel | None] = {
            "medium1": None,
            "medium2": None,
        }

    # ---- getters ----
    @property
    def request(self) -> SimulationRequest:
        return self._request

    @property
    def dispersive_sources(self) -> dict[str, Any]:
        return dict(self._dispersive_sources)

    # ---- setters emit request_simulation ----
    def set_medium1(self, medium: Medium, dispersive: DispersionModel | None = None) -> None:
        self._dispersive_sources["medium1"] = dispersive
        self._request = replace(self._request, medium1=medium)
        self.request_simulation.emit(self._request)

    def set_medium2(self, medium: Medium, dispersive: DispersionModel | None = None) -> None:
        self._dispersive_sources["medium2"] = dispersive
        self._request = replace(self._request, medium2=medium)
        self.request_simulation.emit(self._request)

    def set_layers(self, layers: list[Layer]) -> None:
        self._request = replace(self._request, layers=tuple(layers))
        self.request_simulation.emit(self._request)

    def set_film(self, thickness_nm: float, eps: complex, mu: complex) -> None:
        self._request = replace(
            self._request,
            film_thickness_nm=float(thickness_nm),
            film_eps=eps,
            film_mu=mu,
        )
        self.request_simulation.emit(self._request)

    def set_wavelength(self, wavelength_nm: float) -> None:
        self._request = replace(self._request, wavelength_nm=float(wavelength_nm))
        self.request_simulation.emit(self._request)

    def set_fixed_angle(self, angle_deg: float) -> None:
        # Ángulo marcador — no invalida curva angular, solo actualiza marcador.
        self._request = replace(self._request, fixed_angle_deg=float(angle_deg))
        self.request_simulation.emit(self._request)

    def set_polarization(self, polarization: str) -> None:
        self._request = replace(self._request, polarization=polarization)

    def set_mode(self, mode: SimulationMode) -> None:
        self._request = replace(self._request, mode=mode)
        self.request_simulation.emit(self._request)

    # ---- forwarders used by service ----
    def on_angular_result(self, result) -> None:
        self.angular_ready.emit(result)

    def on_spectral_result(self, result) -> None:
        self.spectral_ready.emit(result)

    def on_heatmap_result(self, result) -> None:
        self.heatmap_ready.emit(result)

    def on_thickness_result(self, result) -> None:
        self.thickness_ready.emit(result)
