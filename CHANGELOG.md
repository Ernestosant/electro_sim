# Changelog

## Unreleased

### UI (PyQt6 + PyQtGraph)
- La vista Angular agrega un checkbox `Leyenda` en cada gráfica para mostrar u ocultar la leyenda sin afectar las curvas de los demás paneles.

### Tests y documentación
- README y manual de usuario actualizados para explicar el nuevo control de visibilidad de leyendas por gráfica.

## 0.1.1 — Angular-only UI

### UI (PyQt6 + PyQtGraph)
- La ventana principal queda reducida a una sola vista Angular; se retiran Simulación, Espectro, Mapa 2D, Elipsometría, Fundamentos, Polar y Absorbancia.
- El Panel de Control se mantiene como única entrada de Materiales, Capas y Fuente para alimentar el barrido angular.
- Export PNG y CSV quedan acotados al resultado angular activo.

### Tests y documentación
- Smoke tests actualizados para validar la shell Angular-only y el sembrado inicial del resultado angular.
- README y manual de usuario alineados al nuevo alcance de una sola vista.

## 0.1.0 — MVP inicial

### Motor físico (`physics_engine/`)
- Portado desde `C:\Mis_proyectos\Proyecto\optic_simulator\physics_engine.py` preservando API (`FresnelEngine.calculate_coefficients(theta_i_deg)` acepta scalar o array).
- Vectorización con NumPy broadcasting:
  - Single interface / thin film / TMM multilayer usan operaciones vectorizadas sobre `N_theta`.
  - TMM usa `np.einsum('ijn,jkn->ikn', ...)` para la cadena de matrices 2×2.
- Speedup medido: **90–600×** vs loop escalar original (500 ángulos, TMM 10 capas: 2.2 ms vs ~200 ms).
- Carpeta renombrada `core/` → `physics_engine/` para auditoría física separada de la UI.

### UI (PyQt6 + PyQtGraph)
- MainWindow con 6 pestañas (Simulación, Angular, Espectro, Mapa 2D, Elipsometría, Fundamentos) + dock izquierdo con panels colapsables.
- Tema claro / oscuro (QSS Catppuccin) propagado a plots pyqtgraph al vuelo; persistido en `QSettings`.
- Materials panel con **3 modos de entrada** por medio: índice `n` (Re + Im), `ε, μ` complejos, o preset disperso. Valores se sincronizan entre modos al cambiar.
- Layers panel: interfaz única / película delgada / DBR / AR λ/4 / Fabry-Pérot con parámetros específicos.
- Source panel con slider de θᵢ continuo (no debouncer — plot sigue el cursor) y λ₀ con debouncer 80 ms.
- Plots live:
  - Angular: R/T/A + |r|/φ dual-eje.
  - Simulación: ray tracer 2D con ángulos Snell reales + elipse Jones + cards de métricas.
  - Espectro: R(λ) / T(λ) con marcador λ₀.
  - Mapa 2D: heatmap pg.ImageItem viridis + Surface 3D OpenGL + R(d) thickness + β(θ) fase.
  - Elipsometría: polar + Argand + elipse + ψ, Δ vs θ.
  - Fundamentos: QTextBrowser cargando `resources/docs/fundamentals.md` en Markdown.

### Pipeline de cómputo
- `SimulationService` con cache LRU 256 entradas y `QTimer` debouncer 80 ms; ejecuta en main thread (motor <15 ms hace QThread innecesario por ahora).
- `SimulationVM` como puente signal/slot entre panels y servicio.
- Modos de barrido independientes: `angular` (automático), `spectral` / `heatmap` / `thickness` (disparados por botón en cada pestaña).

### Export
- `Ctrl+E` → PNG de la pestaña activa (usa `QWidget.grab()`).
- `Ctrl+Shift+E` → CSV del último resultado numérico (angular / espectral / heatmap 2D / thickness).

### Tests
- 125 tests pytest pasando en ~0.4 s:
  - 57 portados 1:1 del proyecto origen (`test_physics.py`).
  - 60 de regresión escalar ↔ vectorizado (100 escenarios random).
  - 7 de regresión cruzada contra el motor origen usando `importlib.util.spec_from_file_location`.
- `conftest.py` con fixtures de motores Air-Glass, Glass-Air, magnético.

### Packaging
- `pyproject.toml` (Hatch + PEP 621) con deps pinneadas: PyQt6 ≥ 6.6, pyqtgraph ≥ 0.13.3, numpy ≥ 1.26, scipy ≥ 1.11, matplotlib ≥ 3.8, qtawesome ≥ 1.3, PyOpenGL ≥ 3.1.
- `requirements.txt` fallback para pip puro.
- Entry point `electro-sim` registrado.

### Documentación
- `README.md` con quickstart, features y arquitectura.
- `docs/user_manual.md` con TOC, layout, panels, descripción de las 6 pestañas, 11 experimentos paso a paso (incluye heatmap stop-band de DBR, barrido de espesor, export), atajos, tema, solución de problemas.
- `src/electro_sim/resources/docs/fundamentals.md` con 9 secciones teóricas (Maxwell → elipsometría), también renderizado dentro de la app.
