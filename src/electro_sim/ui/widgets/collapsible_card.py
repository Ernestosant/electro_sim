from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class CollapsibleCard(QWidget):
    """QGroupBox-like colapsable. Reemplaza `st.expander`."""

    toggled = pyqtSignal(bool)

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._header_button = QPushButton(f"▼  {title}")
        self._header_button.setCheckable(True)
        self._header_button.setChecked(True)
        self._header_button.setFlat(True)
        self._header_button.setProperty("variant", "collapsible-header")
        self._header_button.toggled.connect(self._on_toggled)

        self._content = QFrame()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(8, 6, 8, 8)
        self._content_layout.setSpacing(6)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._header_button)
        outer.addWidget(self._content)

        self._title = title

    def addWidget(self, widget: QWidget) -> None:  # noqa: N802
        self._content_layout.addWidget(widget)

    def addLayout(self, layout) -> None:  # noqa: N802
        self._content_layout.addLayout(layout)

    def _on_toggled(self, checked: bool) -> None:
        self._content.setVisible(checked)
        arrow = "▼" if checked else "▶"
        self._header_button.setText(f"{arrow}  {self._title}")
        self.toggled.emit(checked)
