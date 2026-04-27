# electro_sim

Simulador interactivo de óptica ondulatoria con interfaz PyQt6 centrado en la vista Angular. Preserva el motor físico vectorizado y concentra la UX actual en el barrido angular con actualización en tiempo real.

## Features

Motor Fresnel vectorizado con NumPy:

- Reflexión/refracción para polarizaciones TE, TM y luz no polarizada
- ε, μ complejos (medios con pérdidas y magnéticos)
- Ángulo de Brewster y ángulo crítico (TIR)
- Película delgada (interferencia multi-onda)
- Multicapas por Transfer Matrix Method (hasta 30 capas)
- Presets: DBR, antirreflectante λ/4, Fabry-Pérot, custom

Modelos de dispersión:

- Sellmeier, Cauchy, Drude, Drude-Lorentz
- 10 materiales preset (BK7, Fused Silica, Sapphire, Silicon, Gold, Silver, Aluminum, Copper, Water, Air)

Análisis y visualización:

- **Angular**: R(θ), T(θ), A(θ) = 1 - R - T (absorptancia), |r|(θ), φ_r(θ) con marcadores Brewster, crítico y ángulo actual
- **Panel de Control persistente**: Materiales, Capas y Fuente viven en el dock izquierdo y alimentan la vista Angular en tiempo real
- **Exportación angular**: PNG de la vista activa y CSV del último resultado angular

Entrada de materiales con **3 modos**:

- **n** (Re + Im) — asume μ = 1, ε = n²
- **ε, μ** complejos directos — Fresnel generalizada (valida medios magnéticos)
- **Preset disperso** — ε(λ) recalculado cada cambio de λ₀

UX:

- Transiciones continuas a >30 fps moviendo θᵢ (cache LRU + debouncer 80 ms)
- Panel de Control persistente para Materiales, Capas y Fuente, recuperable desde Vista si se oculta
- Tema claro / oscuro con propagación a plots (Ctrl+D)
- Export PNG (Ctrl+E) y CSV (Ctrl+Shift+E) del resultado angular actual

## Requisitos

- Python ≥ 3.11
- Windows, Linux o macOS

## Instalación

```powershell
cd "C:\Mis_proyectos\maestria de instrumentacion\2do semestre\electrodinamica de sensores 2\electro simulations\electro_sim"
python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".[dev]"
```

## Ejecución

```powershell
python -m electro_sim
# o
python run.py
# o (tras instalar)
electro-sim
```

## Tests

```powershell
pytest
pytest --cov=electro_sim --cov-report=html
```

## Arquitectura

Hexagonal + MVVM. **Motor físico aislado en `physics_engine/`** para auditoría sin dependencias de UI:

```
ui/              widgets PyQt6 y plots PyQtGraph
  ↑
viewmodels/      QObjects con señales y estado compartido
  ↑
services/        orquestación (cache LRU, debouncer, export)
  ↑
physics_engine/  física pura NumPy — 0 Qt, 0 I/O — testeable sin QApplication
```

Archivos clave del motor:

```
physics_engine/
├── fresnel.py        FresnelEngine vectorizado (acepta scalar o array de θ)
├── tmm.py            Transfer Matrix Method con np.einsum (2,2,N_theta)
├── dispersion.py     Sellmeier, Cauchy, Drude, Drude-Lorentz + 10 presets
├── ellipsometry.py   Utilidades elipsométricas preservadas en el motor
├── structures.py     Builders DBR, AR λ/4, Fabry-Pérot
├── sweeps.py         sweep_angular + barridos auxiliares conservados en backend
├── constants.py      HC_EV_NM, umbrales, paleta
└── types.py          Dataclasses frozen Medium, Layer, SimulationRequest, *Result
```

Para el flujo real de señales, estado y cómputo, consulta `docs/architecture.md`.

## Documentación

- `docs/user_manual.md` — manual de la UI Angular-only, paneles, experimentos guiados, atajos, export y solución de problemas.
- `docs/architecture.md` — arquitectura real de la aplicación, responsabilidades por capa y flujo UI -> VM -> service -> motor.
- `docs/development.md` — entorno local, estrategia de pruebas y reglas de mantenimiento.
- `docs/physics_engine.md` — mapa docente del motor físico para clases y auditoría del código.
- `src/electro_sim/resources/docs/fundamentals.md` — teoría de referencia (Maxwell → Fresnel → TMM → dispersión → elipsometría) conservada en el repositorio.

## Licencia

GPL-3.0-or-later (herencia de PyQt6).
