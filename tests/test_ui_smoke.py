from __future__ import annotations

import numpy as np
import pytest
from PyQt6.QtWidgets import QFrame, QScrollArea

from electro_sim.physics_engine.sweeps import sweep_angular
from electro_sim.physics_engine.types import AngularResult, Layer, Medium, SimulationRequest
from electro_sim.services.export_service import export_angular_csv
from electro_sim.ui.main_window import MainWindow
from electro_sim.ui.plots.base_plot import ThemedPlotWidget
from electro_sim.ui.tabs.angular_tab import AngularTab


@pytest.fixture
def main_window(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    return window


def _make_absorbing_request() -> SimulationRequest:
    return SimulationRequest(
        medium1=Medium(eps=1.0 + 0j, mu=1.0 + 0j, name="Air"),
        medium2=Medium(eps=2.25 + 0j, mu=1.0 + 0j, name="Glass"),
        layers=(Layer(eps=(2.0 + 0.1j) ** 2, mu=1.0 + 0j, thickness_nm=100.0),),
        wavelength_nm=550.0,
        angle_range_deg=(0.0, 80.0, 81),
        fixed_angle_deg=45.0,
        mode="angular",
    )


def test_main_window_exposes_only_angular_and_seeds_initial_result(main_window, qtbot) -> None:
    qtbot.waitUntil(lambda: main_window._last_angular is not None, timeout=1000)

    assert main_window._tabs.count() == 1
    assert main_window._tabs.tabText(0) == "Angular"
    assert main_window._tabs.currentWidget() is main_window._angular_tab
    assert main_window._last_angular is not None
    assert main_window._angular_tab._plot_curves._current_line_rt.value() == pytest.approx(
        main_window._vm.request.fixed_angle_deg
    )


def test_control_dock_can_be_toggled_from_view_action(main_window, qtbot) -> None:
    dock = main_window._control_dock

    assert dock is not None
    assert dock.toggleViewAction().text() == "Panel de Control"
    assert dock.isVisible()

    dock.toggleViewAction().trigger()
    qtbot.waitUntil(lambda: not dock.isVisible(), timeout=1000)

    dock.toggleViewAction().trigger()
    qtbot.waitUntil(lambda: dock.isVisible(), timeout=1000)


def test_main_window_thin_film_supports_complex_index(main_window, qtbot) -> None:
    qtbot.waitUntil(lambda: main_window._last_angular is not None, timeout=1000)

    expected_n = 2.0 + 0.1j
    expected_eps = expected_n ** 2
    film_index = main_window._layers._mode.findData("film")

    main_window._layers._mode.setCurrentIndex(film_index)
    main_window._layers._film_d.setValue(100.0)
    main_window._layers._film_n.set_value(expected_n)

    qtbot.waitUntil(
        lambda: abs(main_window._vm.request.film_eps - expected_eps) < 1e-9
        and main_window._last_angular is not None
        and np.max(main_window._last_angular.A_unpol) > 1e-6,
        timeout=2000,
    )

    assert main_window._vm.request.film_thickness_nm == pytest.approx(100.0)
    assert main_window._vm.request.film_eps == pytest.approx(expected_eps)
    assert main_window._vm.request.layers == ()
    assert np.max(main_window._last_angular.A_TE) > 1e-6
    assert np.max(main_window._last_angular.A_TM) > 1e-6


def test_angular_tab_uses_four_plot_layout_without_scroll(qtbot) -> None:
    tab = AngularTab()
    qtbot.addWidget(tab)
    tab.show()

    result = AngularResult(
        angles_deg=np.array([5.0, 30.0, 55.0]),
        R_TE=np.array([0.1, 0.2, 0.35]),
        R_TM=np.array([0.08, 0.16, 0.28]),
        R_unpol=np.array([0.09, 0.18, 0.315]),
        T_TE=np.array([0.85, 0.75, 0.55]),
        T_TM=np.array([0.88, 0.78, 0.6]),
        T_unpol=np.array([0.865, 0.765, 0.575]),
        A_TE=np.array([0.05, 0.05, 0.1]),
        A_TM=np.array([0.04, 0.06, 0.12]),
        A_unpol=np.array([0.045, 0.055, 0.11]),
        r_TE=np.array([0.3 + 0.0j, 0.45 + 0.1j, 0.6 + 0.15j]),
        r_TM=np.array([0.25 + 0.0j, 0.38 + 0.12j, 0.5 + 0.18j]),
        t_TE=np.array([0.8 + 0.0j, 0.72 + 0.05j, 0.58 + 0.1j]),
        t_TM=np.array([0.82 + 0.0j, 0.75 + 0.04j, 0.63 + 0.08j]),
        phi_r_TE=np.array([10.0, 20.0, 35.0]),
        phi_r_TM=np.array([8.0, 18.0, 28.0]),
        phi_t_TE=np.array([-5.0, -12.0, -20.0]),
        phi_t_TM=np.array([-4.0, -10.0, -18.0]),
        brewster_deg=56.3,
        critical_deg=41.8,
        compute_ms=1.2,
    )

    tab.on_angular_ready(result)
    tab.on_angle_changed(30.0)

    assert tab.findChildren(QScrollArea) == []
    assert len(tab.findChildren(ThemedPlotWidget)) == 4
    plot_cards = tab.findChildren(QFrame, "angularPlotCard")
    assert len(plot_cards) == 4
    assert all(card.layout().contentsMargins().right() >= 12 for card in plot_cards)

    rt_x, rt_y = tab._plot_curves._curve_R_TE.getData()
    abs_x, abs_y = tab._plot_curves._curve_A_unpol.getData()
    x_range, _ = tab._plot_curves._plot_rt.viewRange()

    assert np.allclose(rt_x, result.angles_deg)
    assert np.allclose(rt_y, result.R_TE)
    assert np.allclose(abs_x, result.angles_deg)
    assert np.allclose(abs_y, result.A_unpol)
    assert x_range[1] > result.angles_deg[-1]
    assert tab._plot_curves._current_line_rt.value() == pytest.approx(30.0)
    assert tab._plot_curves._current_line_absorbance.value() == pytest.approx(30.0)


def test_angular_tab_renders_positive_absorptance_from_real_sweep(qtbot) -> None:
    tab = AngularTab()
    qtbot.addWidget(tab)
    tab.show()

    result = sweep_angular(_make_absorbing_request())
    tab.on_angular_ready(result)

    abs_x, abs_y = tab._plot_curves._curve_A_unpol.getData()

    assert np.max(result.A_TE) > 1e-6
    assert np.max(result.A_TM) > 1e-6
    assert np.max(result.A_unpol) > 1e-6
    assert np.allclose(abs_x, result.angles_deg)
    assert np.allclose(abs_y, result.A_unpol)
    assert np.max(abs_y) > 1e-6


def test_export_angular_csv_uses_absorptance_headers(tmp_path) -> None:
    result = sweep_angular(_make_absorbing_request())
    path = tmp_path / "angular.csv"

    export_angular_csv(result, str(path))

    header = path.read_text(encoding="utf-8").splitlines()[0]
    assert "Absorptance_TE" in header
    assert "Absorptance_TM" in header
    assert "Absorptance_unpol" in header