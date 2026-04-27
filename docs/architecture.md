# Arquitectura de electro_sim

## Objetivo

Este documento explica la arquitectura real de la aplicación y el flujo que siguen
los datos desde un cambio en la interfaz hasta el cálculo físico y el render del
resultado. La idea es que el proyecto pueda mantenerse sin mezclar responsabilidades:
la UI controla interacción, el ViewModel controla estado, el servicio orquesta el
cómputo y el motor físico permanece puro y auditable.

## Capas

```text
ui/  -> viewmodels/ -> services/ -> physics_engine/
Qt      estado         orquestación   física pura NumPy
```

### 1. UI

Archivos principales:

- `src/electro_sim/ui/main_window.py`
- `src/electro_sim/ui/panels/`
- `src/electro_sim/ui/tabs/angular_tab.py`
- `src/electro_sim/ui/plots/`

Responsabilidad:

- Construir widgets, dock, tabs, menús y barra de estado.
- Recoger la interacción del usuario mediante señales Qt.
- Mostrar resultados ya calculados.
- Delegar el estado compartido al ViewModel.

La UI NO debe:

- Ejecutar fórmulas físicas.
- Tomar decisiones de cache, debounce o vectorización.
- Reescribir reglas de negocio que ya viven en `physics_engine/` o `services/`.

### 2. ViewModel

Archivo principal:

- `src/electro_sim/viewmodels/simulation_vm.py`

Responsabilidad:

- Mantener un `SimulationRequest` congelado como estado canónico.
- Recibir cambios desde los panels y convertirlos en una nueva versión del request.
- Emitir `request_simulation` cuando el estado cambia.
- Reenviar los resultados listos a la capa de UI con señales Qt.

Decisión importante:

- Los modelos dispersivos no viven dentro del `SimulationRequest`; se conservan en
  `self._dispersive_sources`. Esto mantiene serializable y estable el request y deja
  las referencias a modelos Python como un canal paralelo controlado por el ViewModel.

El ViewModel NO debe:

- Ejecutar directamente `sweep_angular`, `sweep_spectral` o similares.
- Tener código de widgets, estilos o render.
- Importar Qt gráfico fuera de las primitivas mínimas de señales.

### 3. Services

Archivo principal:

- `src/electro_sim/services/simulation_service.py`

Responsabilidad:

- Recibir requests desde el ViewModel.
- Aplicar debounce para evitar recalcular en cada evento intermedio.
- Consultar y actualizar la cache LRU.
- Elegir el barrido correcto según `req.mode`.
- Emitir el resultado ya resuelto (`AngularResult`, `SpectralResult`, etc.).

Puntos clave del diseño actual:

- El proyecto corre en main thread porque el hot path angular es suficientemente
  rápido con el motor vectorizado.
- El debounce desacopla la velocidad del input de la frecuencia de cómputo.
- La cache evita repetir cálculos cuando el usuario regresa a parámetros ya vistos.

El servicio NO debe:

- Conocer detalles de widgets concretos.
- Duplicar fórmulas del motor.
- Convertirse en un segundo ViewModel con estado de presentación.

### 4. physics_engine

Carpeta principal:

- `src/electro_sim/physics_engine/`

Responsabilidad:

- Resolver la física con NumPy puro.
- Mantener una API testeable sin depender de QApplication ni de señales Qt.
- Concentrar geometría de ondas, Fresnel, TMM, dispersión y barridos numéricos.

Submódulos relevantes:

- `wavevector.py`: formulación con `k_x` conservada y `k_z` por medio.
- `fresnel.py`: interfaz simple, película delgada y composición general.
- `tmm.py`: matrices de transferencia multicapa.
- `dispersion.py`: modelos espectrales y presets.
- `structures.py`: builders de estructuras estándar.
- `sweeps.py`: barridos angular, espectral, heatmap y espesor.

Regla estructural más importante del proyecto:

- `physics_engine/` jamás debe importar Qt.

## Flujo real de simulación

### Caso principal: vista Angular

1. El usuario cambia un valor en `MaterialsPanel`, `LayersPanel` o `SourcePanel`.
2. `MainWindow` conectó esas señales a setters del `SimulationVM`.
3. El setter reemplaza el `SimulationRequest` y emite `request_simulation`.
4. `MainWindow._on_request_simulation()` reenvía ese request al `SimulationService`.
5. `SimulationService.request()` guarda el request pendiente y activa el `QTimer`.
6. Cuando vence el debounce, `_flush()` busca primero en cache.
7. Si no hay cache hit, el servicio llama el barrido correspondiente en `physics_engine.sweeps`.
8. El barrido crea un `FresnelEngine`, resuelve el cálculo y devuelve un dataclass de resultado.
9. `SimulationService` emite la señal del resultado.
10. `SimulationVM` reenvía el resultado a la UI.
11. `AngularTab` actualiza curvas, marcadores y ejes.
12. `MainWindow` actualiza barra de estado, tiempo de cómputo, cache hit ratio y chequeo energético.

## Puntos de entrada importantes

### `MainWindow`

En `src/electro_sim/ui/main_window.py` ocurre el ensamblaje principal:

- Se construyen tabs, dock izquierdo, menús y barra de estado.
- Se conectan panels con setters del ViewModel.
- Se conectan señales del servicio con forwarders del ViewModel.
- Se dispara una simulación inicial con `request_now()`.

`MainWindow` actúa como composition root de la app Qt. Si en el futuro aparece una
segunda vista fuerte además de Angular, esta seguirá pasando por el mismo punto de
orquestación.

### `SimulationVM`

`src/electro_sim/viewmodels/simulation_vm.py` define el request base y los setters
atómicos (`set_medium1`, `set_medium2`, `set_layers`, `set_film`, `set_wavelength`,
`set_fixed_angle`, `set_mode`).

La decisión de usar `dataclasses.replace()` importa por dos razones:

- El estado es explícito y fácil de inspeccionar en pruebas.
- El request resultante se puede usar como clave de cache sin mutaciones ocultas.

### `SimulationService`

`src/electro_sim/services/simulation_service.py` separa dos caminos:

- `request()`: ruta normal con debounce.
- `request_now()`: ruta inmediata para acciones donde la UI necesita respuesta al instante.

Esto explica por qué mover el ángulo fijo puede refrescar el marcador con rapidez sin
esperar siempre al retardo completo del debounce.

## Modos de simulación

Aunque la UI actual expone sobre todo la vista Angular, el backend ya soporta varios
modos a través de `req.mode`:

- `angular`
- `spectral`
- `heatmap`
- `thickness`

La separación ya existe en `SimulationService._flush()` y en `physics_engine/sweeps.py`.
Si se reactivan o amplían vistas futuras, el punto natural de extensión es el servicio,
no el motor físico.

## Cómo extender sin romper la arquitectura

### Agregar un nuevo panel de entrada

- Crear el widget en `ui/panels/`.
- Emitir señales con tipos del dominio, no con referencias a widgets.
- Conectar esas señales en `MainWindow` hacia setters del `SimulationVM`.

### Agregar un nuevo resultado o barrido

- Definir el dataclass en `physics_engine/types.py`.
- Implementar el cálculo en `physics_engine/sweeps.py` o en el módulo físico que corresponda.
- Enseñar al servicio cómo despachar ese modo.
- Recién después conectar la nueva señal a una pestaña o plot.

### Agregar un nuevo modelo de dispersión

- Implementarlo en `physics_engine/dispersion.py`.
- Mantener la API compatible con `DispersionModel.epsilon(wavelength_nm)`.
- Inyectarlo desde la UI a través del ViewModel, no desde el motor.

## Riesgos de mantenimiento a vigilar

- Duplicar fórmulas entre UI y motor.
- Dejar que widgets construyan directamente objetos del motor sin pasar por el ViewModel.
- Meter lógica de cache o debounce dentro de los panels.
- Introducir imports Qt dentro de `physics_engine/`.
- Cambiar terminología física en la UI sin reflejarla en docs y tests.

## Lectura recomendada

- `README.md`: visión general y mapa documental.
- `docs/user_manual.md`: uso de la aplicación.
- `docs/development.md`: entorno local, pruebas y mantenimiento.
- `docs/physics_engine.md`: lectura docente del motor físico.
- `src/electro_sim/resources/docs/fundamentals.md`: teoría de respaldo.