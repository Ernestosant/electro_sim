"""Motor de Física de Electro Sim.

Este paquete contiene la implementación del motor electromagnético para resolver
las ecuaciones de Fresnel y la Matriz de Transferencia (TMM) aplicadas a películas
delgadas (thin films) y estructuras multicapa.

Está diseñado de forma modular y puramente funcional/vectorizada para garantizar
una alta eficiencia (bajos milisegundos por simulación) en la capa de interfaz
de usuario gráfica.

Módulos principales:
- `fresnel`: El núcleo del motor. Resuelve interfaces simples y películas delgadas.
- `tmm`: Algoritmo de la Matriz de Transferencia para multicapas complejas.
- `dispersion`: Modelos de permitividad dieléctrica (Sellmeier, Drude, Lorentz).
- `ellipsometry`: Cálculo de la elipse de Jones y parámetros elipsométricos.
- `sweeps`: Orquestadores que barren variables (angular, espectral, espesor).
- `structures`: Constructores (builders) de filtros ópticos estándar (AR, DBR).
"""
