from __future__ import annotations

import time
from collections import deque

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QLabel


class FPSCounter(QLabel):
    """Contador de FPS con ventana móvil de 1 segundo."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._times: deque[float] = deque(maxlen=120)
        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._refresh)
        self._timer.start()
        self._refresh()

    def tick(self) -> None:
        self._times.append(time.perf_counter())

    def _refresh(self) -> None:
        now = time.perf_counter()
        while self._times and now - self._times[0] > 1.0:
            self._times.popleft()
        fps = len(self._times)
        self.setText(f"FPS: {fps}")
