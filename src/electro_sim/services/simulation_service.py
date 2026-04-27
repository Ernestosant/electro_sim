"""Servicio de simulación: debouncer + cache + cómputo.

MVP en main thread: el motor vectorizado tarda <15 ms para 500 ángulos con
TMM 30 capas, lo que no justifica todavía un QThread para barridos angulares.
El debouncer (80 ms) limita a ~12 Hz sostenidos.

Si en el futuro se añade heatmap 2D 500×200 (≈500 ms) como cómputo en hot-path,
migrar a QThread aquí sin tocar el resto del proyecto.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from electro_sim.physics_engine.sweeps import sweep_angular, sweep_heatmap, sweep_spectral, sweep_thickness
from electro_sim.physics_engine.types import (
    AngularResult,
    HeatmapResult,
    SimulationRequest,
    SpectralResult,
    ThicknessResult,
)
from electro_sim.services.cache import LRUCache


class SimulationService(QObject):
    simulation_ready = pyqtSignal(object)       # AngularResult
    spectral_ready = pyqtSignal(object)
    heatmap_ready = pyqtSignal(object)
    thickness_ready = pyqtSignal(object)
    compute_started = pyqtSignal()
    cache_hit_ratio_changed = pyqtSignal(float)

    def __init__(self, parent: QObject | None = None, debounce_ms: int = 80) -> None:
        super().__init__(parent)
        self._cache = LRUCache(maxsize=256)
        self._pending_request: SimulationRequest | None = None
        self._dispersive: dict[str, Any] = {}

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(debounce_ms)
        self._timer.timeout.connect(self._flush)

    def request(
        self,
        request: SimulationRequest,
        dispersive_sources: dict[str, Any] | None = None,
    ) -> None:
        self._pending_request = request
        if dispersive_sources is not None:
            self._dispersive = dispersive_sources
        self._timer.start()

    def request_now(
        self,
        request: SimulationRequest,
        dispersive_sources: dict[str, Any] | None = None,
    ) -> None:
        self._pending_request = request
        if dispersive_sources is not None:
            self._dispersive = dispersive_sources
        self._flush()

    def invalidate_cache(self) -> None:
        self._cache.clear()
        self.cache_hit_ratio_changed.emit(0.0)

    # ---- internal ----

    def _flush(self) -> None:
        req = self._pending_request
        if req is None:
            return
        self.compute_started.emit()

        key = (req, req.mode)
        cached = self._cache.get(key)
        if cached is not None:
            self._emit(req.mode, cached)
            self.cache_hit_ratio_changed.emit(self._cache.hit_ratio)
            return

        if req.mode == "angular":
            result = sweep_angular(req)
        elif req.mode == "spectral":
            result = sweep_spectral(
                req,
                model1=self._dispersive.get("medium1"),
                model2=self._dispersive.get("medium2"),
                layer_models=self._dispersive.get("layers"),
            )
        elif req.mode == "heatmap":
            result = sweep_heatmap(
                req,
                model1=self._dispersive.get("medium1"),
                model2=self._dispersive.get("medium2"),
                layer_models=self._dispersive.get("layers"),
            )
        elif req.mode == "thickness":
            result = sweep_thickness(req)
        else:
            return

        self._cache.put(key, result)
        self._emit(req.mode, result)
        self.cache_hit_ratio_changed.emit(self._cache.hit_ratio)

    def _emit(self, mode: str, result: Any) -> None:
        if isinstance(result, AngularResult):
            self.simulation_ready.emit(result)
        elif isinstance(result, SpectralResult):
            self.spectral_ready.emit(result)
        elif isinstance(result, HeatmapResult):
            self.heatmap_ready.emit(result)
        elif isinstance(result, ThicknessResult):
            self.thickness_ready.emit(result)
