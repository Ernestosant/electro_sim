# Desarrollo y mantenimiento

## Objetivo

Este documento resume cómo trabajar en el proyecto sin romper la separación entre
UI, orquestación y motor físico. Está pensado para cambios de código, revisión de
regresiones y mantenimiento cotidiano.

## Entorno local

Requisitos:

- Python 3.11 o superior
- Entorno virtual recomendado
- Dependencias de desarrollo instaladas desde `.[dev]`

Instalación sugerida en Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".[dev]"
```

Ejecución de la aplicación:

```powershell
python -m electro_sim
```

También están disponibles:

```powershell
python run.py
electro-sim
```

## Estructura de trabajo

### Motor físico

- Vive en `src/electro_sim/physics_engine/`.
- Debe seguir siendo puro NumPy, sin Qt ni I/O.
- Es el lugar correcto para fórmulas, geometría, dispersión y barridos.

### Orquestación

- Vive en `src/electro_sim/services/`.
- Decide cuándo recalcular, cuándo usar cache y qué barrido ejecutar.

### Estado de aplicación

- Vive en `src/electro_sim/viewmodels/`.
- Centraliza el `SimulationRequest` y las referencias a modelos dispersivos.

### UI

- Vive en `src/electro_sim/ui/`.
- Debe limitarse a interacción, composición visual y render del resultado.

## Estrategia de pruebas

El proyecto mezcla pruebas físicas, regresión numérica y smoke tests de UI.

### Suites principales

- `tests/test_physics.py`: invariantes físicas y casos conocidos del motor.
- `tests/test_wavevector.py`: geometría interna basada en `k_x`, `k_z` y fase.
- `tests/test_vectorization_regression.py`: equivalencia entre rutas vectorizadas y comportamiento esperado.
- `tests/test_cross_regression.py`: regresión cruzada entre implementaciones o configuraciones.
- `tests/test_ui_smoke.py`: verificación mínima de arranque de UI.

Ejecución completa:

```powershell
pytest
```

Ejecución focalizada del motor:

```powershell
pytest tests/test_physics.py tests/test_wavevector.py tests/test_vectorization_regression.py tests/test_cross_regression.py
```

Cobertura:

```powershell
pytest --cov=electro_sim --cov-report=html
```

## Qué validar según el tipo de cambio

### Si solo cambias documentación o comentarios

- Revisar que no hayas roto sintaxis por indentación o comillas.
- Ejecutar al menos las suites del motor si tocaste docstrings o comentarios en archivos Python.

### Si cambias `physics_engine/`

- Ejecutar siempre `test_physics.py` y `test_wavevector.py`.
- Si tocaste vectorización o TMM, añadir `test_vectorization_regression.py` y `test_cross_regression.py`.
- Confirmar que no se introdujeron imports Qt ni dependencias de UI.

### Si cambias `services/` o `viewmodels/`

- Verificar manualmente el flujo de request y respuesta.
- Revisar el impacto en cache, debounce y señales.

### Si cambias `ui/`

- Correr `test_ui_smoke.py`.
- Abrir la app y comprobar que la vista Angular, la barra de estado y la exportación siguen funcionando.

## Convenciones para comentarios y docstrings

El proyecto tiene dos necesidades simultáneas:

- mantener código claro para desarrollo;
- usar `physics_engine/` como apoyo docente para clases.

Por eso, en el motor físico se prefieren comentarios que expliquen:

- qué magnitud física se calcula;
- por qué esa transformación es válida;
- qué convención numérica se está usando;
- cómo se relaciona el paso con Fresnel, Snell o TMM.

Evitar:

- comentarios que solo repiten la línea de código;
- docstrings genéricos sin contexto físico;
- mover explicaciones físicas importantes a la UI.

El estándar interno a imitar es el de:

- `src/electro_sim/physics_engine/fresnel.py`
- `src/electro_sim/physics_engine/tmm.py`

## Guía breve para extender el motor

### Nuevo modelo de dispersión

1. Implementarlo en `physics_engine/dispersion.py`.
2. Mantener la API `epsilon(wavelength_nm)`.
3. Inyectarlo desde la UI por el ViewModel.
4. Añadir pruebas para el nuevo modelo o preset.

### Nuevo barrido

1. Añadir o extender el dataclass de resultado en `physics_engine/types.py`.
2. Implementar la función en `physics_engine/sweeps.py`.
3. Conectar el modo desde `SimulationService`.
4. Exponer el resultado en UI solo después de validar el backend.

### Nueva estructura multicapa

1. Crear el builder en `physics_engine/structures.py`.
2. Documentar la condición física que usa la estructura.
3. Añadir pruebas o ejemplos que verifiquen el comportamiento esperado.

## Notas de mantenimiento

- No mezclar absorbancia óptica (`-log10(T)`) con absorptancia (`1 - R - T`).
- Mantener consistente el uso de `k_x` y `k_z` como formulación interna del motor.
- Si un cambio vuelve lento el hot path angular, revisar primero vectorización y cache antes de migrar a threads.
- La documentación técnica de referencia está en:
  - `docs/architecture.md`
  - `docs/physics_engine.md`
  - `src/electro_sim/resources/docs/fundamentals.md`