# Guía docente del motor físico

## Objetivo

Este documento sirve como mapa de lectura para usar `physics_engine/` como apoyo de
clase. No reemplaza la teoría extensa de `src/electro_sim/resources/docs/fundamentals.md`,
pero sí explica cómo esa teoría se traduce en código ejecutable dentro del proyecto.

## Idea central del motor

La API pública todavía permite hablar en ángulos, pero internamente el motor trabaja
mejor con las componentes del vector de onda normalizadas por `k_0 = 2π / λ`:

- `k_x`: componente tangencial conservada en interfaces planas.
- `k_z`: componente normal a la interfaz, distinta en cada medio.

Esta formulación facilita:

- aplicar Snell en forma algebraica;
- elegir correctamente la rama evanescente sobre el ángulo crítico;
- reutilizar la misma geometría en Fresnel simple, película delgada y TMM.

## Ruta sugerida para una clase

### 1. Tipos y constantes

Archivos:

- `src/electro_sim/physics_engine/types.py`
- `src/electro_sim/physics_engine/constants.py`

Qué explicar aquí:

- qué representa un `Medium`;
- cómo se modela una `Layer`;
- qué guarda un `SimulationRequest`;
- qué magnitudes devuelve cada resultado.

Este paso fija el vocabulario antes de entrar en fórmulas.

### 2. Geometría de onda

Archivo:

- `src/electro_sim/physics_engine/wavevector.py`

Conceptos clave:

- conservación de la componente tangencial `k_x`;
- recuperación del seno propagante en otro medio;
- cálculo de `k_z` con rama compleja física;
- fase acumulada al recorrer una capa finita.

Si una clase necesita entender TIR, ondas evanescentes o la relación entre Snell y
propagación en capas, este archivo es el primer punto obligatorio.

### 3. Fresnel generalizado

Archivo:

- `src/electro_sim/physics_engine/fresnel.py`

Conceptos clave:

- admitancia óptica para TE y TM;
- coeficientes de amplitud `r` y `t`;
- conversión a reflectancia, transmitancia y absorptancia;
- extensión a película delgada;
- uso de materiales con `ε` y `μ` complejos.

Aquí ya se puede discutir por qué el motor no asume `μ = 1` y por qué la energía se
evalúa con flujo real en lugar de usar solo `|t|^2`.

### 4. Transfer Matrix Method

Archivo:

- `src/electro_sim/physics_engine/tmm.py`

Conceptos clave:

- matriz de cada capa;
- composición secuencial de capas;
- papel de `δ = (2π/λ) d k_z`;
- diferencia entre formulación analítica de película y formulación matricial general.

Este módulo es ideal para mostrar cómo una teoría aparentemente pesada se vuelve una
operación repetitiva sobre matrices 2x2.

### 5. Dispersión material

Archivo:

- `src/electro_sim/physics_engine/dispersion.py`

Conceptos clave:

- por qué `ε` depende de `λ`;
- diferencia entre modelos dieléctricos y metálicos;
- uso de presets para experiments rápidos sin reescribir parámetros.

### 6. Estructuras estándar

Archivo:

- `src/electro_sim/physics_engine/structures.py`

Conceptos clave:

- capas de cuarto de onda;
- espejos de Bragg (DBR);
- recubrimientos antirreflectantes;
- cavidades Fabry-Pérot.

Este módulo traduce reglas de diseño óptico en listas de capas concretas para el motor.

### 7. Barridos numéricos

Archivo:

- `src/electro_sim/physics_engine/sweeps.py`

Conceptos clave:

- barrido angular a longitud de onda fija;
- barrido espectral a ángulo fijo;
- heatmap espectro-angular;
- barrido de espesor.

Aquí se ve la diferencia entre lo que se vectoriza completamente y lo que todavía se
itera explícitamente por claridad y costo computacional.

## Flujo físico resumido

1. Se define el sistema: medios, capas, longitud de onda y tipo de barrido.
2. El motor convierte el ángulo incidente en `k_x`.
3. Cada medio o capa calcula su `k_z` usando ese mismo `k_x` conservado.
4. Con `k_z` se construyen admitancias y fases.
5. Fresnel simple o TMM producen `r` y `t`.
6. A partir de `r` y `t` se obtienen `R`, `T`, fases y magnitudes derivadas.
7. `sweeps.py` empaqueta todo en dataclasses listos para consumir desde la UI.

## Terminología que conviene fijar en clase

### Absorptancia

Fracción de potencia absorbida dentro de la estructura:

```text
A = 1 - R - T
```

### Absorbancia

Magnitud óptica de transmisión usada en espectroscopia:

```text
Absorbancia = -log10(T)
```

Ambas aparecen en el proyecto, pero NO significan lo mismo.

## Dónde apoyarse con pruebas

Para usar el motor como material de clase conviene enlazar explicación con pruebas:

- `tests/test_wavevector.py`: geometría de `k_x`, `k_z` y fase.
- `tests/test_physics.py`: invariantes físicas del motor.
- `tests/test_vectorization_regression.py`: consistencia de la ruta vectorizada.
- `tests/test_cross_regression.py`: comparación entre rutas o implementaciones.

## Reglas docentes para futuros cambios

- Toda función no trivial en `physics_engine/` debe tener docstring con contexto físico.
- Los comentarios inline deben explicar una magnitud, una convención o una decisión numérica.
- Si un bloque matemático es central para la clase, documentarlo paso a paso.
- Si una explicación teórica ya existe en `fundamentals.md`, enlazarla en docs y evitar duplicación extensa.

## Documentos relacionados

- `README.md`
- `docs/architecture.md`
- `docs/development.md`
- `docs/user_manual.md`
- `src/electro_sim/resources/docs/fundamentals.md`