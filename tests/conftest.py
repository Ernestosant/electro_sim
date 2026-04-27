"""Fixtures compartidos por la suite de tests."""

from __future__ import annotations

import pytest
from PyQt6.QtCore import QCoreApplication, QSettings

from electro_sim.physics_engine.fresnel import FresnelEngine


@pytest.fixture
def air_glass_engine() -> FresnelEngine:
    return FresnelEngine(1.0, 1.0, 2.25, 1.0)


@pytest.fixture
def glass_air_engine() -> FresnelEngine:
    return FresnelEngine(2.25, 1.0, 1.0, 1.0)


@pytest.fixture
def magnetic_engine() -> FresnelEngine:
    return FresnelEngine(4.0, 1.0, 1.0, 4.0)


@pytest.fixture(autouse=True)
def isolated_qsettings(tmp_path, qapp) -> None:
    settings_dir = tmp_path / "settings"
    settings_dir.mkdir()

    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(settings_dir),
    )
    QCoreApplication.setOrganizationName("electro_sim_tests")
    QCoreApplication.setApplicationName("electro_sim_tests")

    settings = QSettings()
    settings.clear()
    yield
    settings.clear()
