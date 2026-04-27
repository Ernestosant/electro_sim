from __future__ import annotations

from typing import Any

import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget

from electro_sim.ui.theme import PLOT_COLORS


class ThemedPlotWidget(pg.PlotWidget):
    """PlotWidget de pyqtgraph con tema integrado y export helpers."""

    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = "dark"
        self._legend_visible = True
        self._title_text = title
        self._title_kwargs: dict[str, Any] = {"size": "10pt"}
        self._axis_labels: dict[str, dict[str, Any]] = {}
        self._reference_lines: list[pg.InfiniteLine] = []

        self.setBackground(PLOT_COLORS["dark"]["background"])
        self.showGrid(x=True, y=True, alpha=0.25)
        self.setTitle(title, size="10pt")

    def addLegend(self, *args: Any, **kwargs: Any) -> Any:  # noqa: N802
        legend = self.getPlotItem().addLegend(*args, **kwargs)
        legend.setVisible(self._legend_visible)
        return legend

    def setTitle(self, title: str | None = None, **kwargs) -> None:  # noqa: N802
        if title is not None:
            self._title_text = title
        stored_kwargs = {key: value for key, value in kwargs.items() if key != "color"}
        if stored_kwargs:
            self._title_kwargs.update(stored_kwargs)
        themed_kwargs = dict(self._title_kwargs)
        themed_kwargs.update(stored_kwargs)
        themed_kwargs["color"] = PLOT_COLORS[self._theme]["foreground"]
        self.getPlotItem().setTitle(self._title_text, **themed_kwargs)

    def setLabel(  # noqa: N802
        self,
        axis: str,
        text: str | None = None,
        units: str | None = None,
        unitPrefix: str | None = None,
        **kwargs,
    ) -> None:
        stored_kwargs = {key: value for key, value in kwargs.items() if key != "color"}
        self._axis_labels[axis] = {
            "text": text,
            "units": units,
            "unitPrefix": unitPrefix,
            "kwargs": stored_kwargs,
        }
        themed_kwargs = dict(stored_kwargs)
        themed_kwargs["color"] = PLOT_COLORS[self._theme]["foreground"]
        self.getPlotItem().setLabel(
            axis,
            text=text,
            units=units,
            unitPrefix=unitPrefix,
            **themed_kwargs,
        )

    def apply_theme(self, theme: str) -> None:
        self._theme = theme
        colors = PLOT_COLORS[theme]
        self.setBackground(colors["background"])
        axis_pen = pg.mkPen(colors["foreground"])
        for ax_name in ("left", "bottom", "top", "right"):
            ax = self.getAxis(ax_name)
            ax.setPen(axis_pen)
            ax.setTextPen(colors["foreground"])
        self.setTitle(self._title_text)
        for axis_name, spec in self._axis_labels.items():
            self.setLabel(
                axis_name,
                text=spec["text"],
                units=spec["units"],
                unitPrefix=spec["unitPrefix"],
                **spec["kwargs"],
            )
        legend = self.plotItem.legend
        if legend is not None:
            if hasattr(legend, "setBrush"):
                legend.setBrush(pg.mkBrush(colors["background"]))
            if hasattr(legend, "setPen"):
                legend.setPen(pg.mkPen(colors["grid"]))
            for _sample, label in legend.items:
                label.setAttr("color", colors["foreground"])
            legend.setVisible(self._legend_visible)
        self.showGrid(x=True, y=True, alpha=0.25)

    def set_legend_visible(self, visible: bool) -> None:
        self._legend_visible = visible
        legend = self.plotItem.legend
        if legend is not None:
            legend.setVisible(visible)

    def legend_visible(self) -> bool:
        return self._legend_visible

    def add_reference_line(
        self,
        x: float,
        label: str | None,
        color: str,
        style=pg.QtCore.Qt.PenStyle.DashLine,
    ) -> pg.InfiniteLine:
        line_kwargs: dict[str, Any] = {
            "pos": x,
            "angle": 90,
            "pen": pg.mkPen(color=color, style=style, width=1.5),
        }
        if label:
            line_kwargs["label"] = label
            line_kwargs["labelOpts"] = {
                "color": color,
                "position": 0.92,
                "movable": False,
            }
        line = pg.InfiniteLine(**line_kwargs)
        self.addItem(line)
        self._reference_lines.append(line)
        return line

    def clear_reference_lines(self) -> None:
        for line in self._reference_lines:
            self.removeItem(line)
        self._reference_lines.clear()
