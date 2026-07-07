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

v3: la señal de selección nacional ya no es un parámetro que llegaba
vacío — puntaje_fama_jugador() consulta las apariciones reales en
Mundiales de la tabla apariciones_mundial (jfjelstul/worldcup),
cruzando por nombre del jugador.
"""

import math
import datetime
import sqlite3


RUTA_BD = "futtrivia.db"

TORNEOS_TOP = ["world cup", "copa mundial", "champions league", "copa libertadores", "euro", "eurocopa"]
TORNEOS_MEDIOS = ["liga mx", "premier league", "la liga", "laliga", "serie a", "bundesliga", "ligue 1", "copa america", "mls"]


def apariciones_seleccion_jugador(nombre_jugador, conexion=None):
    """
    Cuenta las apariciones REALES del jugador con su selección en Mundiales,
    usando la tabla apariciones_mundial (fuente jfjelstul/worldcup).

    El cruce es por nombre porque los player_id de esa tabla ('P-14758') no
    son los de jugadores_reales (transfermarkt):
    1. Empate exacto de nombre completo ('Lionel Messi' = nombre + apellido;
       cuando la fuente marca el nombre como 'not applicable', el nombre
       completo es solo el apellido, p. ej. el Ronaldo brasileño).
    2. Si no hay empate, apellido exacto + prefijo del nombre, para apodos
       tipo 'Rafa Márquez' -> 'Rafael Márquez'.
    """
    if not nombre_jugador or not nombre_jugador.strip():
        return 0

    cerrar_al_final = conexion is None
    if conexion is None:
        conexion = sqlite3.connect(RUTA_BD)
    cursor = conexion.cursor()

    try:
        completo = nombre_jugador.strip().lower()
        total = cursor.execute("""
            SELECT COUNT(*) FROM apariciones_mundial
            WHERE lower(CASE WHEN nombre = 'not applicable'
                             THEN apellido
                             ELSE nombre || ' ' || apellido END) = ?
        """, (completo,)).fetchone()[0]
        if total:
            return total

        partes = completo.rsplit(" ", 1)
        if len(partes) == 2 and len(partes[0]) >= 3:
            nombre_pila, apellido = partes
            total = cursor.execute("""
                SELECT COUNT(*) FROM apariciones_mundial
                WHERE lower(apellido) = ?
                  AND (lower(nombre) LIKE ? || '%' OR ? LIKE lower(nombre) || '%')
            """, (apellido, nombre_pila, nombre_pila)).fetchone()[0]
        return total
    finally:
        if cerrar_al_final:
            conexion.close()


def puntaje_fama_jugador(valor_mercado, total_apariciones, total_goles, nombre_jugador=None, conexion=None,
                         apariciones_seleccion=None):
    """
    Calcula un puntaje 0-100 de qué tan 'reconocible' es un jugador.

    Pesos (v3):
    - valor_mercado actual: máx 20 (bajado, penaliza injustamente a retirados)
    - apariciones de carrera: máx 35 (trayectoria larga = reconocible)
    - goles: máx 10 (bajado, no penaliza a defensas/porteros)
    - apariciones con selección en Mundiales: máx 35. En v2 esto era un
      parámetro que casi siempre llegaba vacío; ahora se consulta de verdad
      en la tabla apariciones_mundial a partir de nombre_jugador. La escala
      es /20 porque el récord de partidos jugados en Mundiales anda en ~26
      (Messi), no en ~100 como los partidos totales de selección.

    Si apariciones_seleccion ya viene calculado (cálculos en lote sobre
    todo el pool), se usa directo y no se consulta la base por nombre.
    """
    puntaje = 0

    if valor_mercado and valor_mercado > 0:
        log_valor = math.log10(valor_mercado)
        puntaje += min(log_valor / 8.3 * 20, 20)

    if total_apariciones:
        puntaje += min(total_apariciones / 400 * 35, 35)

    if total_goles:
        puntaje += min(total_goles / 150 * 10, 10)

    if apariciones_seleccion is None and nombre_jugador:
        apariciones_seleccion = apariciones_seleccion_jugador(nombre_jugador, conexion)
    if apariciones_seleccion:
        puntaje += min(apariciones_seleccion / 20 * 35, 35)

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


def calcular_dificultad_jugador(valor_mercado, total_apariciones, total_goles, nombre_jugador=None, conexion=None):
    """Función de conveniencia: calcula todo de un jugador de una vez."""
    puntaje = puntaje_fama_jugador(valor_mercado, total_apariciones, total_goles, nombre_jugador, conexion)
    return asignar_dificultad(puntaje), puntaje


def calcular_dificultad_partido(nombre_competicion, anio, total_registros_competicion=0):
    """Función de conveniencia: calcula todo de un partido/torneo de una vez."""
    puntaje = puntaje_fama_torneo(nombre_competicion, anio, total_registros_competicion)
    return asignar_dificultad(puntaje), puntaje