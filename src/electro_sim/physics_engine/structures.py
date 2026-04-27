"""Builders de estructuras multicapa estándar (DBR, AR λ/4, Fabry-Pérot).

Portado desde la lógica embebida en `C:\\Mis_proyectos\\Proyecto\\optic_simulator\\gui_app.py:181-244`.
"""

from __future__ import annotations


def build_dbr(
    n_high: float,
    n_low: float,
    n_pairs: int,
    wavelength_design_nm: float,
    mu: complex = 1.0 + 0j,
) -> list[dict]:
    """Construye un Espejo de Bragg Distribuido (DBR) con pares de capas λ/4.
    
    Un DBR es una estructura multicapa periódica que alterna índices de refracción
    altos y bajos. Si el grosor óptico de cada capa es exactamente un cuarto de la 
    longitud de onda de diseño, las reflexiones de cada interfaz interfieren
    constructivamente, creando un "espejo perfecto" en esa longitud de onda.
    
    Args:
        n_high: Índice de refracción del material denso.
        n_low: Índice de refracción del material menos denso.
        n_pairs: Número de pares (cada par contiene una capa n_high y una n_low).
        wavelength_design_nm: Longitud de onda objetivo en nanómetros (λ₀).
        mu: Permeabilidad magnética (por defecto 1.0, materiales no magnéticos).
        
    Returns:
        Lista de diccionarios de capas compatibles con el motor de física.
    """
    if n_pairs < 1:
        raise ValueError("n_pairs debe ser ≥ 1")

    # 1. Condición de cuarto de onda (Quarter-wave condition):
    # El grosor físico (d) multiplicado por el índice de refracción (n) debe ser λ/4.
    # Por lo tanto, d = λ / (4 * n)
    d_high = wavelength_design_nm / (4.0 * n_high)
    d_low = wavelength_design_nm / (4.0 * n_low)

    layers: list[dict] = []
    # 2. Ensamblaje periódico de los pares de capas
    for _ in range(int(n_pairs)):
        # Añadimos la capa de alto índice de refracción (eps = n^2)
        layers.append({"eps": complex(n_high ** 2, 0), "mu": mu, "thickness": d_high})
        # Añadimos la capa de bajo índice de refracción (eps = n^2)
        layers.append({"eps": complex(n_low ** 2, 0), "mu": mu, "thickness": d_low})
    return layers


def build_antireflection_quarter(
    n_ar: float,
    wavelength_design_nm: float,
    mu: complex = 1.0 + 0j,
) -> list[dict]:
    """Construye una capa única antirreflectante (AR) óptima.
    
    Para que una capa AR suprima completamente la reflexión en una longitud 
    de onda específica, su grosor óptico debe ser de un cuarto de onda (λ/4).
    Físicamente, el índice ideal se calcula como n_ar = sqrt(n_incidente * n_sustrato).
    
    Args:
        n_ar: Índice de refracción del material antirreflectante.
        wavelength_design_nm: Longitud de onda objetivo en nanómetros (λ₀).
        mu: Permeabilidad magnética.
        
    Returns:
        Lista con una única capa formateada para el motor.
    """
    # En un recubrimiento AR de cuarto de onda buscamos que los dos haces reflejados
    # principales salgan en oposición de fase y se cancelen.
    # La condición mínima para ello es fijar el grosor óptico en lambda/4.
    d = wavelength_design_nm / (4.0 * n_ar)

    # No imponemos aquí el valor "óptimo" de n_ar = sqrt(n1*n2); eso queda en manos
    # del llamador para permitir estudiar recubrimientos desintonizados o no ideales.
    return [{"eps": complex(n_ar ** 2, 0), "mu": mu, "thickness": d}]


def build_fabry_perot(
    n_mirror: float,
    n_cavity: float,
    n_pairs_per_mirror: int,
    cavity_thickness_nm: float,
    wavelength_design_nm: float,
    n_low: float = 1.0,
    mu: complex = 1.0 + 0j,
) -> list[dict]:
    """Construye una cavidad óptica de Fabry-Pérot.
    
    La cavidad se forma emparedando un material resonante (cavidad) entre dos 
    Espejos de Bragg (DBRs). La cavidad suele tener un grosor múltiplo de λ/2 
    para mantener resonancia. Este filtro permite pasar picos de transmisión
    extremadamente estrechos.
    
    Args:
        n_mirror: Índice alto para los DBRs reflectores.
        n_cavity: Índice de refracción del medio de la cavidad.
        n_pairs_per_mirror: Número de pares λ/4 en cada espejo DBR lateral.
        cavity_thickness_nm: Grosor físico de la cavidad central en nanómetros.
        wavelength_design_nm: Longitud de onda de sintonía de los espejos (λ₀).
        n_low: Índice bajo alternante para los espejos DBR (por defecto 1.0).
        mu: Permeabilidad magnética.
        
    Returns:
        Estructura completa: DBR Inferior -> Cavidad -> DBR Superior
    """
    # 1. Calculamos los grosores físicos para cumplir la condición λ/4 en los espejos
    d_mirror = wavelength_design_nm / (4.0 * n_mirror)
    d_low = wavelength_design_nm / (4.0 * n_low)

    def mirror() -> list[dict]:
        """Ensamblador de un espejo DBR individual.

        Cada espejo queda formado por una secuencia periódica alto-bajo índice.
        El orden importa porque fija la primera interfaz que verá la onda al entrar
        al espejo desde la cavidad o desde el medio exterior.
        """
        out: list[dict] = []
        for _ in range(int(n_pairs_per_mirror)):
            # Capa de alto índice: incrementa el contraste óptico del par.
            out.append({"eps": complex(n_mirror ** 2, 0), "mu": mu, "thickness": d_mirror})
            # Capa de bajo índice: completa el par lambda/4 y prepara la siguiente reflexión parcial.
            out.append({"eps": complex(n_low ** 2, 0), "mu": mu, "thickness": d_low})
        return out

    # 2. Ensamblaje del resonador
    layers: list[dict] = []
    # Espejo de entrada: refleja gran parte del campo hacia la cavidad.
    layers.extend(mirror())
    # Capa central: la cavidad donde la onda acumula fase y puede cumplir condición de resonancia.
    # A menudo se diseña con grosor óptico cercano a lambda/2 o múltiplos enteros, pero no se impone aquí.
    layers.append(
        {"eps": complex(n_cavity ** 2, 0), "mu": mu, "thickness": cavity_thickness_nm}
    )
    # Espejo de salida: cierra la cavidad y determina, junto con el espejo de entrada,
    # la fineza y el ancho del pico resonante.
    layers.extend(mirror())
    return layers


STRUCTURE_PRESETS: dict[str, str] = {
    "DBR (Distributed Bragg Reflector)": "dbr",
    "Antirreflectante λ/4": "ar_quarter",
    "Cavidad Fabry-Pérot": "fabry_perot",
    "Multicapa personalizada": "custom",
}
