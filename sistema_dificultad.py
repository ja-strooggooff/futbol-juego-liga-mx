"""
sistema_dificultad.py

Sistema de puntuación automática de "fama/dificultad" para jugadores
y torneos/partidos. No usa Machine Learning (no tenemos datos de
entrenamiento todavía) — usa reglas basadas en señales reales de la
base de datos.

v2: corrige el sesgo contra porteros (poco peso a goles) y contra
jugadores retirados (poco peso a valor de mercado actual, más peso
a trayectoria de carrera y presencia con selección nacional).
Ajustado para audiencia mixta/internacional: ligas domésticas
(incluida Liga MX) ya no llegan a "Fácil" solo por ser recientes.
"""

import math
import datetime


TORNEOS_TOP = ["world cup", "copa mundial", "champions league", "copa libertadores", "euro", "eurocopa"]
TORNEOS_MEDIOS = ["liga mx", "premier league", "la liga", "laliga", "serie a", "bundesliga", "ligue 1", "copa america", "mls"]


def puntaje_fama_jugador(valor_mercado, total_apariciones, total_goles, apariciones_seleccion=0):
    """
    Calcula un puntaje 0-100 de qué tan 'reconocible' es un jugador.

    Pesos (v2):
    - valor_mercado actual: máx 20 (bajado, penaliza injustamente a retirados)
    - apariciones de carrera: máx 35 (trayectoria larga = reconocible)
    - goles: máx 10 (bajado, no penaliza a defensas/porteros)
    - apariciones con selección nacional: máx 35 (nuevo, premia íconos
      históricos sin depender del valor de mercado actual)
    """
    puntaje = 0

    if valor_mercado and valor_mercado > 0:
        log_valor = math.log10(valor_mercado)
        puntaje += min(log_valor / 8.3 * 20, 20)

    if total_apariciones:
        puntaje += min(total_apariciones / 400 * 35, 35)

    if total_goles:
        puntaje += min(total_goles / 150 * 10, 10)

    if apariciones_seleccion:
        puntaje += min(apariciones_seleccion / 100 * 35, 35)

    return round(min(puntaje, 100), 1)


def puntaje_fama_torneo(nombre_competicion, anio, total_registros_competicion=0):
    """
    Calcula un puntaje 0-100 de qué tan 'famoso' es un torneo/competición.

    Ajustado para audiencia mixta/internacional: las ligas domésticas
    (incluida Liga MX) tienen un techo más bajo — solo los torneos
    verdaderamente globales (Mundial, Champions, Libertadores, Euro)
    pueden llegar al rango "Fácil".
    """
    puntaje = 0
    nombre_lower = (nombre_competicion or "").lower()

    if any(t in nombre_lower for t in TORNEOS_TOP):
        puntaje += 45
    elif any(t in nombre_lower for t in TORNEOS_MEDIOS):
        puntaje += 20
    else:
        puntaje += 8

    if anio:
        anio_actual = datetime.date.today().year
        antiguedad = anio_actual - int(anio)
        if antiguedad <= 5:
            puntaje += 25
        elif antiguedad <= 15:
            puntaje += 15
        elif antiguedad <= 30:
            puntaje += 8
        else:
            puntaje += 2

    if total_registros_competicion:
        puntaje += min(total_registros_competicion / 1000 * 20, 20)

    return round(min(puntaje, 100), 1)


def combinar_puntajes(puntaje_jugador=None, puntaje_torneo=None):
    """Combina puntaje de jugador y/o torneo. Si solo hay uno, se usa directo."""
    puntajes_validos = [p for p in [puntaje_jugador, puntaje_torneo] if p is not None]
    if not puntajes_validos:
        return 0
    return round(sum(puntajes_validos) / len(puntajes_validos), 1)


def asignar_dificultad(puntaje):
    """Convierte un puntaje 0-100 en una etiqueta de dificultad."""
    if puntaje >= 75:
        return "Fácil"
    elif puntaje >= 45:
        return "Media"
    elif puntaje >= 20:
        return "Difícil"
    else:
        return "Legendaria"


def calcular_dificultad_jugador(valor_mercado, total_apariciones, total_goles, apariciones_seleccion=0):
    """Función de conveniencia: calcula todo de un jugador de una vez."""
    puntaje = puntaje_fama_jugador(valor_mercado, total_apariciones, total_goles, apariciones_seleccion)
    return asignar_dificultad(puntaje), puntaje


def calcular_dificultad_partido(nombre_competicion, anio, total_registros_competicion=0):
    """Función de conveniencia: calcula todo de un partido/torneo de una vez."""
    puntaje = puntaje_fama_torneo(nombre_competicion, anio, total_registros_competicion)
    return asignar_dificultad(puntaje), puntaje