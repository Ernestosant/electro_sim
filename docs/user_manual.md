# electro_sim — Manual de Usuario

> Simulador interactivo de óptica ondulatoria (Fresnel, TMM, elipsometría) con PyQt6 + PyQtGraph.

## Tabla de contenidos

1. [Introducción](#1-introducción)
2. [Instalación y primer arranque](#2-instalación-y-primer-arranque)
3. [Layout general de la aplicación](#3-layout-general-de-la-aplicación)
4. [Panel de control](#4-panel-de-control)
   1. [Materiales](#41-materiales)
   2. [Capas / Película](#42-capas--película)
   3. [Fuente (λ, θ, polarización)](#43-fuente-λ-θ-polarización)
5. [Vista Angular](#5-vista-angular)
   1. [Angular (R, T, A vs θ)](#51-angular-r-t-a-vs-θ)
6. [Experimentos paso a paso](#6-experimentos-paso-a-paso)
   1. [Reflexión Air → Glass](#61-reflexión-air--glass)
   2. [Ángulo de Brewster](#62-ángulo-de-brewster)
   3. [Reflexión interna total (TIR)](#63-reflexión-interna-total-tir)
   4. [Dispersión: oro en visible](#64-dispersión-oro-en-visible)
   5. [Antirreflectante λ/4](#65-antirreflectante-λ4)
   6. [DBR (espejo Bragg)](#66-dbr-espejo-bragg)
   7. [Material magnético](#67-material-magnético)
   8. [Exportar gráfico y CSV](#68-exportar-gráfico-y-csv)
7. [Atajos de teclado](#7-atajos-de-teclado)
8. [Tema claro / oscuro](#8-tema-claro--oscuro)
9. [Estructura del código y auditoría física](#9-estructura-del-código-y-auditoría-física)
10. [Solución de problemas](#10-solución-de-problemas)

---

## 1. Introducción

`electro_sim` resuelve las ecuaciones de Fresnel generalizadas para:

- Coeficientes de reflexión y transmisión (amplitud y fase) para polarizaciones TE y TM.
- Medios con ε y μ complejos (dieléctricos, metales, magnéticos, absorbentes).
- Películas delgadas con interferencia multi-onda.
- Multicapas por Transfer Matrix Method (hasta 30 capas).
- Modelos de dispersión cromática (Sellmeier, Cauchy, Drude, Drude-Lorentz) para 10 materiales preset.

La UI es nativa en PyQt6 y los plots usan PyQtGraph para actualización en tiempo real (objetivo ≥ 30 fps, cache LRU para re-visitar parámetros).

Si además de usar la app necesitás entender cómo está construida, consulta la documentación técnica complementaria:

- `architecture.md` — flujo de señales, estado y cómputo.
- `development.md` — entorno local, pruebas y mantenimiento.
- `physics_engine.md` — mapa docente del motor físico.
- `../src/electro_sim/resources/docs/fundamentals.md` — teoría de respaldo.

## 2. Instalación y primer arranque

```powershell
cd "C:\Mis_proyectos\maestria de instrumentacion\2do semestre\electrodinamica de sensores 2\electro simulations\electro_sim"
python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".[dev]"
python -m electro_sim
```

La primera ventana abre en ~1 s con la vista **Angular** activa y parámetros por defecto: Aire → BK7, λ₀ = 550 nm, θᵢ = 45°, polarización ambas (TE + TM).

## 3. Layout general de la aplicación

```
┌──────────────────────────────────────────────────────────────┐
│ Archivo  Vista  Ayuda                           menú          │
├──────────────┬───────────────────────────────────────────────┤
│ Panel de     │ QTabWidget central                             │
│ Control      │ ┌────────────────────────────────────────────┐│
│              │ │                  Angular                   ││
│ - Materiales │ ├────────────────────────────────────────────┤│
│ - Capas      │ │       (contenido según pestaña)             ││
│ - Fuente     │ │                                              ││
│              │ └──────────────────────────────────────────────┘│
├──────────────┴───────────────────────────────────────────────┤
│ θᵢ:45°  compute:1.5ms  cache:73%  R+T+A=1.0000✓  FPS:58       │
└──────────────────────────────────────────────────────────────┘
```

El **dock izquierdo** es re-posicionable (arrastre la barra) y colapsable. Si alguna vez lo cerrás, podés recuperarlo desde **Vista → Panel de Control**.

## 4. Panel de control

### 4.1 Materiales

Dos bloques (Medio 1 — incidente, Medio 2 — transmitido) con **3 modos de entrada**:

| Modo | Qué ingresás | Fórmula que aplica |
|---|---|---|
| **n** | Re(n), Im(n) = k | ε = n², μ = 1 (asume medio no magnético) |
| **ε, μ** | ε complejo + μ complejo | Directo; n = √(ε·μ) |
| **Preset** | Material del catálogo | ε(λ) se recalcula cada cambio de λ₀ |

Presets dispersos disponibles:

| Tipo | Materiales |
|---|---|
| Dieléctricos (Sellmeier) | Air, BK7, Fused Silica, Water, Sapphire, Silicon |
| Metales (Drude-Lorentz, Rakic 1998) | Gold, Silver, Aluminum, Copper |

Debajo de cada bloque verás un resumen `n = … , ε = … , μ = …` en tiempo real.

### 4.2 Capas / Película

Dropdown con 5 modos:

- **Ninguna** — interfaz única (sin capas intermedias).
- **Película delgada** — una capa con espesor d y n; usa fórmula cerrada con β = 2π n d cos θ / λ.
- **DBR** — N pares de capas λ/4 alternadas entre n_H y n_L (espejo Bragg).
- **Antirreflectante λ/4** — capa única con n óptimo = √(n₁·n₂) para R→0 en λ de diseño.
- **Fabry-Pérot** — DBR + cavidad + DBR; produce pico de transmitancia estrecho.

Cada modo expone sus parámetros específicos (espesor, n, λ de diseño, número de pares).

### 4.3 Fuente (λ, θ, polarización)

- **λ₀**: slider + spin (200–2000 nm). Debouncer 80 ms.
- **θᵢ**: slider + spin (0–89.9°). Actualización **continua** (no debounced) — el marcador y plot siguen el cursor.
- **Polarización**: `Ambas` (TE + TM juntas, default), `TE`, `TM`, `Unpol` (promedio incoherente).

## 5. Vista Angular

### 5.1 Angular (R, T, A vs θ)

**Panel superior izquierdo:** R_TE, R_TM (sólidas); T_TE, T_TM (discontinuas).  
**Panel superior derecho:** A_TE, A_TM y A_unpol. Aquí `A` significa **absorptancia**: `A = 1 - R - T`. No es la absorbancia óptica `-log10(T)`.  
**Panel inferior:** |r| TE/TM en eje Y izquierdo; φ_r TE/TM en eje Y derecho (-180° a 180°).  
**Marcadores verticales:** θ_B (amarillo, Brewster), θ_c (rojo, crítico), θᵢ actual (gris).

Cada tarjeta de gráfica incluye un checkbox **Leyenda** en la esquina superior derecha. Si una leyenda tapa curvas, marcadores o zonas de interés, desactívala solo en ese panel; las demás gráficas no se ven afectadas.

La aplicación expone una sola vista de resultados. Toda la interacción ocurre desde el **Panel de Control** y la respuesta se visualiza aquí de inmediato. El flujo actual es: editar parámetros a la izquierda, inspeccionar curvas angulares en el centro y exportar si hace falta.

En estructuras lossless (interfaz simple, película o multicapa sin pérdidas), la absorptancia debe permanecer en 0 para todos los ángulos. En cambio, una capa absorbente finita debe producir una curva `A(θ)` no nula y dependiente del ángulo.

**Cómo testearlo:**

1. Con config por defecto mové el slider θᵢ → el marcador gris se desliza.
2. En interfaz Aire→Vidrio verás: θ_B ≈ 56.3°, R_TM = 0 allí.
3. Invierte con Medio 1 = BK7 y Medio 2 = Air → aparece θ_c ≈ 41.8°.
4. Si una leyenda tapa la zona de Brewster o crítico, quitá el checkbox **Leyenda** en esa gráfica para despejar la vista.

## 6. Experimentos paso a paso

### 6.1 Reflexión Air → Glass

1. **Materiales → Medio 1**: modo `n`, Re(n) = 1.0.
2. **Medio 2**: modo `n`, Re(n) = 1.5.
3. **Fuente → θᵢ** deslizá de 0 a 89°.
4. **Esperado**: en θᵢ=0, R = 4 % (ambas pol). En θᵢ→90°, R → 100 %.

### 6.2 Ángulo de Brewster

1. Config del experimento anterior.
2. **Pestaña Angular** — aparece línea vertical amarilla `θ_B = 56.31°`.
3. Movés θᵢ a 56.31°: R_TM ≈ 0, R_TE ≈ 15 %. `R+T+A = 1.0000 ✓` en status bar.
4. Polarización TM sola: R colapsa a 0 exactamente en θ_B.

### 6.3 Reflexión interna total (TIR)

1. **Medio 1 = BK7**, **Medio 2 = Air**.
2. **Pestaña Angular** — línea vertical roja en `θ_c ≈ 41.8°`.
3. Arrastra θᵢ superando 41.8°: R_TE y R_TM saltan a 1, T cae a 0.
4. Fase φ_r varía rápidamente cerca de θ_c — mirá el panel inferior.

### 6.4 Dispersión: oro en visible

1. **Medio 1 = Air** (preset).
2. **Medio 2**: modo `Preset` → `Gold`. Ves `ε(550 nm) = -5.xxx + i.xxx`.
3. **Fuente → λ₀**: barrer de 400 a 800 nm. R cambia porque ε(λ) cambia.
4. **Esperado**: en 700–800 nm, R_unpol > 90 % (alta reflectancia IR de oro).

### 6.5 Antirreflectante λ/4

1. **Medio 1 = Air**, **Medio 2 = BK7** (o n=1.5).
2. **Capas** → `Antirreflectante λ/4`. n AR = √1.5 ≈ 1.225. λ diseño = 550 nm.
3. **Fuente → θᵢ = 0°**, λ₀ = 550 nm.
4. **Esperado**: R ≈ 0 exactamente (el recubrimiento anula la reflexión normal).
5. Variá λ₀ lejos de 550 nm → R re-aparece.

### 6.6 DBR (espejo Bragg)

1. **Medio 1 = Air**, **Medio 2 = BK7**.
2. **Capas** → `DBR`. n_H = 2.3, n_L = 1.45, Pares = 5, λ diseño = 550 nm.
3. **Fuente → λ₀ = 550 nm**.
4. **Esperado**: R > 0.97 en banda de stop central.
5. Movés λ₀ lejos → R cae.

### 6.7 Material magnético

1. **Medio 1**: modo `ε, μ`. ε = 4 + 0i, μ = 1 + 0i (→ n₁ = 2).
2. **Medio 2**: modo `ε, μ`. ε = 1 + 0i, μ = 4 + 0i (→ n₂ = 2 pero η distinto).
3. **Fuente → θᵢ = 0°**.
4. **Esperado**: **R = 0.36** (aunque n₁ = n₂, las impedancias difieren).

Este caso valida que el motor NO asume μ = 1 — es Fresnel generalizada con admitancia.

### 6.8 Exportar gráfico y CSV

1. Terminá cualquier experimento anterior (ej. Brewster con preset `Gold`).
2. **Ctrl+E** → guardá PNG de la vista Angular activa.
3. **Ctrl+Shift+E** → guardá CSV del resultado numérico. Abrilo en Excel/Python y verificá que las columnas coincidan con la tabla en la [sección 7.1](#71-exportación).

## 7. Atajos de teclado

| Acción | Atajo |
|---|---|
| Salir | Ctrl+Q |
| Alternar tema claro/oscuro | Ctrl+D |
| Ir a Angular | Ctrl+1 |
| Forzar recálculo (invalida cache) | F5 |
| Exportar imagen de la vista (PNG) | Ctrl+E |
| Exportar datos numéricos (CSV) | Ctrl+Shift+E |

### 7.1 Exportación

**Menú Exportar → Imagen de la pestaña (PNG)** o `Ctrl+E`:
Captura la vista Angular activa como PNG (usa `QWidget.grab()`). Abre diálogo de guardar con nombre sugerido `electro_sim_angular.png`.

**Menú Exportar → Datos numéricos (CSV)** o `Ctrl+Shift+E`:
Serializa el último resultado angular disponible:

| Vista | Columnas CSV |
|---|---|
| Angular | `angle_deg, R_TE, R_TM, R_unpol, T_TE, T_TM, T_unpol, Absorptance_TE, Absorptance_TM, Absorptance_unpol, abs_r_TE, abs_r_TM, phi_r_TE_deg, phi_r_TM_deg` |

Si todavía no hay un cálculo angular disponible, aparece el mensaje "No hay datos disponibles en esta pestaña".

## 8. Tema claro / oscuro

Menú **Vista → Alternar tema claro/oscuro** (o `Ctrl+D`). El color se propaga a:

- QSS global (fondo, textos, botones, sliders).
- Plots PyQtGraph (ejes, curvas, marcadores, líneas de referencia).
- Tema persiste en `QSettings` y se restaura al reabrir la app.

## 9. Estructura del código y auditoría física

Para auditar el motor físico sin mirar la UI:

```
src/electro_sim/
├── physics_engine/          ← FÍSICA PURA (sin Qt)
│   ├── fresnel.py           FresnelEngine vectorizado
│   ├── tmm.py               Transfer Matrix Method
│   ├── dispersion.py        Sellmeier, Cauchy, Drude, Drude-Lorentz + 10 presets
│   ├── ellipsometry.py      utilidades elipsométricas preservadas en el motor
│   ├── structures.py        Builders DBR, AR λ/4, Fabry-Pérot
│   ├── sweeps.py            Barridos del motor; la UI actual expone Angular
│   ├── constants.py         HC_EV_NM, umbrales, paleta de colores
│   └── types.py             Dataclasses Medium, Layer, SimulationRequest, *Result
│
├── services/                ← Orquestación (cache LRU + debouncer)
│   ├── simulation_service.py
│   └── cache.py
│
├── viewmodels/              ← Puente VM (Qt signals) entre UI y services
│   └── simulation_vm.py
│
└── ui/                      ← Todo Qt (widgets, plots, panels, tabs)
    ├── main_window.py
    ├── theme.py
    ├── panels/, plots/, widgets/, tabs/, dialogs/
    └── ...
```

**Regla**: `ui/` importa `viewmodels/`, `viewmodels/` importa `services/`, `services/` importa `physics_engine/`. **`physics_engine/` jamás importa Qt** → testeable sin QApplication.

Tests unitarios del motor:
```powershell
.\.venv\Scripts\activate
pytest tests/                           # suite completa
pytest tests/test_physics.py -v         # solo física
pytest tests/test_cross_regression.py   # regresión vs motor origen
pytest --cov=electro_sim --cov-report=html
```

## 10. Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| Ventana no abre, `ImportError: PyQt6` | venv no activo | `.\.venv\Scripts\activate` antes de `python -m electro_sim` |
| Plots quedan congelados al mover slider | Cache corrupta | **F5** para invalidar y recalcular |
| Advertencia "longitud de onda fuera del rango válido" | Preset Sellmeier fuera de banda | El modelo clampea al rango válido; cambiá a un preset más amplio o modo `n` manual |
| `R+T+A` diverge de 1 en status bar | Medio con pérdidas altas (ε imaginario grande) + multicapa | Esperado ~1e-3; si es mayor, reportalo |
| Cold start lento la primera vez | Compilación de bytecode | Las corridas siguientes son <1 s |
