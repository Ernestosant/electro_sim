from __future__ import annotations

from importlib import resources
from typing import Literal

from PyQt6.QtWidgets import QApplication

Theme = Literal["dark", "light"]


def load_qss(theme: Theme) -> str:
    try:
        files = resources.files("electro_sim.resources.themes")
        content = (files / f"{theme}.qss").read_text(encoding="utf-8")
        return content
    except Exception:
        return ""


def apply_theme(app: QApplication, theme: Theme) -> None:
    qss = load_qss(theme)
    app.setStyleSheet(qss)


PLOT_COLORS = {
    "dark": {
        "background": "#1e1e2e",
        "foreground": "#cdd6f4",
        "grid": "#313244",
        "TE": "#f38ba8",
        "TM": "#89b4fa",
        "T": "#a6e3a1",
        "A": "#fab387",
        "unpol": "#cba6f7",
        "brewster": "#f9e2af",
        "critical": "#eba0ac",
        "current": "#a6adc8",
        "psi": "#f5c2e7",
        "delta": "#94e2d5",
    },
    "light": {
        "background": "#ffffff",
        "foreground": "#4c4f69",
        "grid": "#ccd0da",
        "TE": "#d20f39",
        "TM": "#1e66f5",
        "T": "#40a02b",
        "A": "#df8e1d",
        "unpol": "#8839ef",
        "brewster": "#df8e1d",
        "critical": "#d20f39",
        "current": "#6c6f85",
        "psi": "#ea76cb",
        "delta": "#179299",
    },
}
