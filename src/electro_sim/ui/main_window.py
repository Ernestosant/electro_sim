from __future__ import annotations

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QDockWidget,
    QLabel,
    QMainWindow,
    QScrollArea,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from electro_sim.physics_engine.types import AngularResult
from electro_sim.services import export_service
from electro_sim.services.simulation_service import SimulationService
from electro_sim.ui.panels.layers_panel import LayersPanel
from electro_sim.ui.panels.materials_panel import MaterialsPanel
from electro_sim.ui.panels.source_panel import SourcePanel
from electro_sim.ui.tabs.angular_tab import AngularTab
from electro_sim.ui.theme import apply_theme
from electro_sim.ui.widgets.fps_counter import FPSCounter
from electro_sim.viewmodels.simulation_vm import SimulationVM

TAB_TITLES = ["Angular"]


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("electro_sim — Simulador Óptico")
        self.resize(1500, 950)

        self._settings = QSettings()
        self._theme = self._settings.value("theme", "dark", type=str)

        self._vm = SimulationVM()
        self._service = SimulationService()

        self._last_angular: AngularResult | None = None
        self._control_dock: QDockWidget | None = None

        self._vm.request_simulation.connect(self._on_request_simulation)
        self._service.simulation_ready.connect(self._vm.on_angular_result)
        self._service.cache_hit_ratio_changed.connect(self._on_cache_hit_ratio)
        self._service.compute_started.connect(self._on_compute_started)

        self._build_tabs()
        self._build_left_dock()
        self._build_menus()
        self._build_status_bar()

        app = QApplication.instance()
        if app is not None:
            apply_theme(app, self._theme)  # type: ignore[arg-type]
        self._apply_theme_to_plots()

        self._restore_geometry()

        self._vm.angular_ready.connect(self._on_angular_result)
        self._sync_request_dependent_ui()

        # Disparar simulación inicial
        self._service.request_now(self._vm.request, self._vm.dispersive_sources)

    # ---- builders ----

    def _build_tabs(self) -> None:
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self._tabs.setMovable(True)

        self._angular_tab = AngularTab()
        self._vm.angular_ready.connect(self._angular_tab.on_angular_ready)
        self._tabs.addTab(self._angular_tab, TAB_TITLES[0])

        self._tabs.setCurrentIndex(0)
        self.setCentralWidget(self._tabs)

    def _build_left_dock(self) -> None:
        dock = QDockWidget("Panel de Control", self)
        dock.setObjectName("ControlDock")
        dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )

        content = QWidget()
        col = QVBoxLayout(content)
        col.setContentsMargins(6, 6, 6, 6)
        col.setSpacing(8)

        self._materials = MaterialsPanel()
        self._layers = LayersPanel()
        self._source = SourcePanel()

        col.addWidget(self._materials)
        col.addWidget(self._layers)
        col.addWidget(self._source)
        col.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        scroll.setMinimumWidth(200)

        dock.setWidget(scroll)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        self._control_dock = dock

        self._materials.medium1_changed.connect(self._vm.set_medium1)
        self._materials.medium2_changed.connect(self._vm.set_medium2)
        self._layers.layers_changed.connect(self._vm.set_layers)
        self._layers.film_changed.connect(self._vm.set_film)
        self._source.wavelength_changed.connect(self._on_wavelength_changed)
        self._source.angle_changed.connect(self._on_angle_changed)
        self._source.polarization_changed.connect(self._vm.set_polarization)

    def _build_menus(self) -> None:
        menu_file = self.menuBar().addMenu("&Archivo")
        act_quit = QAction("&Salir", self)
        act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        act_quit.triggered.connect(self.close)
        menu_file.addAction(act_quit)

        menu_view = self.menuBar().addMenu("&Vista")
        if self._control_dock is not None:
            act_control_dock = self._control_dock.toggleViewAction()
            act_control_dock.setText("Panel de Control")
            menu_view.addAction(act_control_dock)
            menu_view.addSeparator()
        act_theme = QAction("Alternar tema claro/oscuro", self)
        act_theme.setShortcut("Ctrl+D")
        act_theme.triggered.connect(self._toggle_theme)
        menu_view.addAction(act_theme)
        menu_view.addSeparator()
        for i, title in enumerate(TAB_TITLES, start=1):
            act = QAction(title, self)
            act.setShortcut(QKeySequence(f"Ctrl+{i}"))
            act.triggered.connect(lambda _=False, idx=i - 1: self._tabs.setCurrentIndex(idx))
            menu_view.addAction(act)

        menu_sim = self.menuBar().addMenu("&Simulación")
        act_recalc = QAction("Forzar recálculo", self)
        act_recalc.setShortcut("F5")
        act_recalc.triggered.connect(self._force_recalc)
        menu_sim.addAction(act_recalc)

        menu_export = self.menuBar().addMenu("&Exportar")
        act_png = QAction("Imagen de la pestaña (PNG)", self)
        act_png.setShortcut("Ctrl+E")
        act_png.triggered.connect(self._export_png)
        menu_export.addAction(act_png)
        act_csv = QAction("Datos numéricos (CSV)", self)
        act_csv.setShortcut("Ctrl+Shift+E")
        act_csv.triggered.connect(self._export_csv)
        menu_export.addAction(act_csv)

        menu_help = self.menuBar().addMenu("A&yuda")
        act_about = QAction("&Acerca de", self)
        act_about.triggered.connect(self._show_about)
        menu_help.addAction(act_about)

    def _build_status_bar(self) -> None:
        sb = QStatusBar()
        self._fps = FPSCounter()
        self._lbl_compute = QLabel("compute: —")
        self._lbl_cache = QLabel("cache: 0%")
        self._lbl_energy = QLabel("R+T+A ≈ 1")
        self._lbl_angle = QLabel("θᵢ: 45.00°")
        self._lbl_lambda = QLabel("λ₀: 550 nm")
        for w in (
            self._lbl_angle, self._lbl_lambda, self._lbl_compute,
            self._lbl_cache, self._lbl_energy, self._fps,
        ):
            sb.addPermanentWidget(w)
        self.setStatusBar(sb)

    # ---- handlers ----

    def _on_request_simulation(self, request) -> None:
        # Request base siempre angular — otras pestañas disparan su propio mode
        self._service.request(request, self._vm.dispersive_sources)

    def _on_compute_started(self) -> None:
        pass

    def _on_cache_hit_ratio(self, ratio: float) -> None:
        self._lbl_cache.setText(f"cache: {ratio * 100:.0f}%")

    def _on_angle_changed(self, angle_deg: float) -> None:
        self._vm.set_fixed_angle(angle_deg)
        self._angular_tab.on_angle_changed(angle_deg)
        self._lbl_angle.setText(f"θᵢ: {angle_deg:.2f}°")
        # Refresca render del ángulo actual usando último resultado cacheado
        self._service.request_now(self._vm.request, self._vm.dispersive_sources)

    def _on_wavelength_changed(self, wl_nm: float) -> None:
        self._vm.set_wavelength(wl_nm)
        self._lbl_lambda.setText(f"λ₀: {wl_nm:.1f} nm")

    def _on_angular_result(self, result: AngularResult) -> None:
        self._last_angular = result
        self._lbl_compute.setText(f"compute: {result.compute_ms:.1f} ms")
        total = float(result.R_unpol[0] + result.T_unpol[0] + result.A_unpol[0])
        ok = abs(total - 1.0) < 1e-3
        self._lbl_energy.setText(
            f"R+T+A = {total:.4f} {'✓' if ok else '⚠'}"
        )
        self._fps.tick()

    def _export_png(self) -> None:
        tab = self._tabs.currentWidget()
        name = self._tabs.tabText(self._tabs.currentIndex()).replace(" ", "_").lower()
        path = export_service.ask_save_path(
            self, f"electro_sim_{name}.png", "PNG (*.png)"
        )
        if path is None:
            return
        pixmap = tab.grab()
        pixmap.save(path)

    def _export_csv(self) -> None:
        idx = self._tabs.currentIndex()
        title = self._tabs.tabText(idx)
        result = self._last_angular if title == "Angular" else None
        writer = export_service.export_angular_csv if title == "Angular" else None
        if result is None or writer is None:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Exportar CSV", "No hay datos disponibles en esta pestaña.")
            return
        name = title.replace(" ", "_").lower()
        path = export_service.ask_save_path(self, f"electro_sim_{name}.csv", "CSV (*.csv)")
        if path is None:
            return
        writer(result, path)

    def _toggle_theme(self) -> None:
        self._theme = "light" if self._theme == "dark" else "dark"
        self._settings.setValue("theme", self._theme)
        app = QApplication.instance()
        if app is not None:
            apply_theme(app, self._theme)  # type: ignore[arg-type]
        self._apply_theme_to_plots()

    def _apply_theme_to_plots(self) -> None:
        for tab in (getattr(self, "_angular_tab", None),):
            if tab is not None and hasattr(tab, "apply_theme"):
                tab.apply_theme(self._theme)

    def _force_recalc(self) -> None:
        self._service.invalidate_cache()
        self._service.request_now(self._vm.request, self._vm.dispersive_sources)

    def _show_about(self) -> None:
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.about(
            self,
            "Acerca de electro_sim",
            "electro_sim 0.1.0\n\n"
            "Simulador interactivo de óptica ondulatoria\n"
            "PyQt6 + PyQtGraph + NumPy\n\n"
            "Motor auditable en src/electro_sim/physics_engine/\n"
            "Manual en docs/user_manual.md",
        )

    # ---- persistence ----

    def _restore_geometry(self) -> None:
        settings = self._settings
        if geom := settings.value("window_geometry"):
            self.restoreGeometry(geom)
        if state := settings.value("window_state"):
            self.restoreState(state)
            
        # Forzar que el panel de control siempre sea visible al iniciar
        if self._control_dock and not self._control_dock.isVisible():
            self._control_dock.setVisible(True)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._settings.setValue("window/geometry", self.saveGeometry())
        self._settings.setValue("window/state", self.saveState())
        super().closeEvent(event)

    def _sync_request_dependent_ui(self) -> None:
        request = self._vm.request
        self._angular_tab.on_angle_changed(request.fixed_angle_deg)
