# Fundamentos matemáticos

> Resumen de las ecuaciones que resuelve el motor `electro_sim.physics_engine`. Para derivaciones completas ver notas de clase y Born–Wolf (*Principles of Optics*), Macleod (*Thin-Film Optical Filters*), Rakic et al. *Applied Optics* 37, 5271 (1998).

## 1. Ecuaciones de Maxwell y condiciones de contorno

En un medio lineal, isótropo, homogéneo, sin fuentes:

    ∇·(εE) = 0            ∇·(μH) = 0
    ∇×E = −∂(μH)/∂t       ∇×H = ∂(εE)/∂t

Continuidad en una interfaz plana (vector normal ẑ):

- Componentes tangenciales de E y H: continuas.
- Componentes normales de εE y μH: continuas.

Esto conduce, por separación de variables, a las ondas planas:

    E(r, t) = E₀ exp(i(k·r − ωt))

con k²/μ ε = ω², es decir n = √(ε·μ), impedancia η = √(μ/ε).

## 2. Ecuaciones de Fresnel generalizadas (ε, μ complejos)

Descomposición en polarización TE (E⊥plano de incidencia) y TM (H⊥plano).

Sea kᵢz = nᵢ cos θᵢ la componente normal del vector de onda, y

    q_i^{TE} = k_iz / μ_i         (admitancia TE)
    q_i^{TM} = k_iz / ε_i         (admitancia TM)

Entonces los coeficientes de amplitud en una interfaz:

    r = (q₁ − q₂) / (q₁ + q₂)
    t = 2 q₁ / (q₁ + q₂)

Transmitancia de potencia (flujo de Poynting normal):

    T = Re(q₂) / Re(q₁) · |t|²
    R = |r|²
    A = 1 − R − T      (absorptancia o fracción absorbida, ≥ 0 en medios pasivos)

La absorbancia óptica es una magnitud distinta:

    Absorbance = −log10(T)

La vista Angular de la app grafica `A = 1 − R − T`, no la absorbancia óptica.

El motor usa estas ecuaciones vectorizadas sobre el eje angular con `numpy.lib.scimath.sqrt` (csqrt) para preservar signo correcto en medios absorbentes.

**Archivos:** `physics_engine/fresnel.py`, funciones `_interface_coefficients`, `_power_transmittance`, `_build_channel`.

## 3. Casos especiales

### 3.1 Ángulo de Brewster (polarización TM)

Para μ₁ = μ₂ = 1:

    tan θ_B = n₂ / n₁      →    R_TM(θ_B) = 0

Para medios con μ arbitrario el motor busca el mínimo numérico de R_TM.

### 3.2 Ángulo crítico (TIR)

Si n₁ > n₂:

    sin θ_c = n₂ / n₁      →    R(θ > θ_c) = 1,   T = 0

Por encima de θ_c, la onda transmitida es evanescente (k₂z imaginario puro).

### 3.3 Medios magnéticos no triviales

Si n₁ = n₂ pero η₁ ≠ η₂, existe reflexión a incidencia normal:

    R₀ = ((η₂ − η₁) / (η₂ + η₁))²

Esto valida que el motor usa admitancias (no sólo n) — test `test_magnetic_material`.

## 4. Película delgada (interferencia multi-onda)

Para una capa de espesor d e índice n_f entre medios 1 y 2:

    β = (2π / λ₀) · n_f · d · cos θ_f
    r = (r₀₁ + r₁₂ · e^{2iβ}) / (1 + r₀₁ · r₁₂ · e^{2iβ})
    t = (t₀₁ · t₁₂ · e^{iβ}) / (1 + r₀₁ · r₁₂ · e^{2iβ})

Interferencia constructiva: 2β = 2mπ. Destructiva: 2β = (2m+1)π.

Aplicación clásica — recubrimiento antirreflectante λ/4 con n_f = √(n₁·n₂) y d = λ₀/(4 n_f) anula R a incidencia normal en la λ de diseño.

**Archivo:** `physics_engine/fresnel.py::_calculate_thin_film_vec`.

## 5. Multicapa — Transfer Matrix Method (TMM)

Para cada capa j con espesor dⱼ:

    δⱼ = (2π / λ₀) · nⱼ · dⱼ · cos θⱼ
    Mⱼ = | cos δⱼ         −i sin δⱼ / qⱼ |
         | −i qⱼ sin δⱼ     cos δⱼ      |

La matriz total M = Π Mⱼ da:

    denom = q_inc M₀₀ + q_inc q_sub M₀₁ + M₁₀ + q_sub M₁₁
    r     = (q_inc M₀₀ + q_inc q_sub M₀₁ − M₁₀ − q_sub M₁₁) / denom
    t     = 2 q_inc / denom

**Vectorización:** el motor construye M con shape (2, 2, N_θ) y multiplica con `numpy.einsum('ijn,jkn->ikn', ...)`. Esto da ~90× speedup vs el loop escalar original.

**Archivo:** `physics_engine/tmm.py::solve_tmm_vectorized`.

## 6. Modelos de dispersión ε(λ)

### 6.1 Sellmeier (dieléctricos transparentes)

    n²(λ) = 1 + Σᵢ Bᵢ λ² / (λ² − Cᵢ)      (λ en μm, Cᵢ en μm²)

Presets: BK7, Fused Silica, Water, Sapphire, Silicon.

### 6.2 Cauchy

    n(λ) = A + B/λ² + C/λ⁴      (válida en rangos sin resonancias)

### 6.3 Drude (electrones libres)

    ε(ω) = ε∞ − ωp² / (ω² + iγω)

Re(ε) < 0 por debajo de la frecuencia de plasma → reflexión metálica.

### 6.4 Drude–Lorentz (metales con bandas interbanda)

    ε(ω) = ε∞ − f₀ ωp² / (ω(ω + iΓ₀)) + Σⱼ fⱼ ωp² / (ωⱼ² − ω² − i γⱼ ω)

Presets (Rakic 1998): Gold, Silver, Aluminum, Copper — 5 osciladores cada uno.

**Archivo:** `physics_engine/dispersion.py`.

## 7. Elipsometría

    ρ = r_TM / r_TE = tan ψ · exp(iΔ)
    ψ = arctan(|r_TM| / |r_TE|)
    Δ = arg(r_TM) − arg(r_TE)

- En θ_B (medio no absorbente): ψ = 0, porque r_TM = 0.
- En incidencia normal: ψ = 45°, porque r_TE = r_TM.

### Elipse de polarización (Jones)

Luz incidente linealmente polarizada a 45°; tras reflexión, (ψ, Δ) definen una elipse en el plano transversal:

    Ex(t) = cos ψ · cos(ωt)
    Ey(t) = sin ψ · cos(ωt + Δ)

- Δ = 0: elipse colapsa a una recta (polarización lineal rotada).
- Δ = ±90°, ψ = 45°: polarización circular.
- Otros (ψ, Δ): elipse inclinada — sentido horario o antihorario según sgn(sin Δ).

**Archivo:** `physics_engine/ellipsometry.py`.

## 8. Barridos disponibles en la app

| Modo | Función | Salida |
|---|---|---|
| Angular | `sweep_angular(req)` | R(θ), T(θ), A(θ) como absorptancia, |r|(θ), φ(θ) |
| Espectral | `sweep_spectral(req)` | R(λ), T(λ) — con ε(λ) disperso |
| Heatmap | `sweep_heatmap(req)` | R(θ, λ) 2D — para DBR/Fabry-Pérot |
| Espesor | `sweep_thickness(req)` | R(d) — diseño de AR |

**Archivo:** `physics_engine/sweeps.py`.

## 9. Conservación de energía (validación)

En cada cómputo la app muestra `R + T + A` en la status bar. Debe ser 1 a tolerancia numérica; discrepancias > 1e-3 indican un problema numérico o una implementación inconsistente. Para capas absorbentes finitas, además, `A` debe volverse positiva en alguna parte del barrido angular.

Tests unitarios fuerzan esta invariante sobre:
- `test_energy_conservation_te_air_glass`, `*_tm_*`, `*_magnetic`
- `test_energy_conservation_lossy_te/tm/complex_mu`
- `test_energy_conservation_multilayer_lossless/lossy`

Ejecutá `pytest tests/` para correr los 125 tests.
