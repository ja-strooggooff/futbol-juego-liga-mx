"""
test_dificultad.py
Pruebas del sistema de puntuación de fama/dificultad
(sistema_dificultad.py), incluida la consulta de apariciones
reales en Mundiales desde la tabla apariciones_mundial.
"""

import datetime
import sqlite3

import pytest

from sistema_dificultad import (
    apariciones_seleccion_jugador,
    asignar_dificultad,
    calcular_dificultad_jugador,
    combinar_puntajes,
    puntaje_fama_jugador,
    puntaje_fama_torneo,
)


def hay_tabla_apariciones():
    """Los tests de apariciones reales solo corren si la base tiene datos."""
    try:
        conexion = sqlite3.connect("futtrivia.db")
        total = conexion.execute("SELECT COUNT(*) FROM apariciones_mundial").fetchone()[0]
        conexion.close()
        return total > 0
    except sqlite3.Error:
        return False


requiere_apariciones = pytest.mark.skipif(
    not hay_tabla_apariciones(),
    reason="futtrivia.db no tiene la tabla apariciones_mundial poblada",
)


# ----------------------------------------------------------------
#  asignar_dificultad y combinar_puntajes (funciones puras)
# ----------------------------------------------------------------

def test_asignar_dificultad_umbrales():
    """75+ Fácil, 45+ Media, 20+ Difícil, abajo Legendaria (bordes incluidos)."""
    assert asignar_dificultad(100) == "Fácil"
    assert asignar_dificultad(75) == "Fácil"
    assert asignar_dificultad(74.9) == "Media"
    assert asignar_dificultad(45) == "Media"
    assert asignar_dificultad(44.9) == "Difícil"
    assert asignar_dificultad(20) == "Difícil"
    assert asignar_dificultad(19.9) == "Legendaria"
    assert asignar_dificultad(0) == "Legendaria"


def test_combinar_puntajes_promedia_y_tolera_faltantes():
    assert combinar_puntajes(80, 40) == 60
    assert combinar_puntajes(80, None) == 80
    assert combinar_puntajes(None, 40) == 40
    assert combinar_puntajes(None, None) == 0


# ----------------------------------------------------------------
#  puntaje_fama_torneo
# ----------------------------------------------------------------

def test_torneo_top_reciente_llega_a_facil():
    """Un Mundial reciente con muchos registros debe quedar en el rango Fácil."""
    anio_actual = datetime.date.today().year
    puntaje = puntaje_fama_torneo("World Cup", anio_actual, total_registros_competicion=5000)
    assert puntaje >= 75
    assert asignar_dificultad(puntaje) == "Fácil"


def test_torneo_desconocido_y_viejo_es_dificil_o_peor():
    puntaje = puntaje_fama_torneo("Bulgarian League", 1974, total_registros_competicion=50)
    assert puntaje < 45


def test_torneo_puntaje_dentro_de_rango():
    for nombre, anio, registros in [
        ("World Cup", 2022, 10**9),
        (None, None, 0),
        ("Liga MX", 2024, 3000),
    ]:
        puntaje = puntaje_fama_torneo(nombre, anio, registros)
        assert 0 <= puntaje <= 100


# ----------------------------------------------------------------
#  puntaje_fama_jugador (parte numérica, sin base de datos)
# ----------------------------------------------------------------

def test_jugador_sin_datos_da_cero():
    assert puntaje_fama_jugador(None, 0, 0) == 0
    assert puntaje_fama_jugador(0, None, None) == 0


def test_jugador_mas_goles_no_baja_el_puntaje():
    base = puntaje_fama_jugador(1000000, 100, 10)
    con_mas_goles = puntaje_fama_jugador(1000000, 100, 100)
    assert con_mas_goles >= base


def test_jugador_puntaje_maximo_sin_seleccion_es_65():
    """Sin señal de selección, los pesos suman 20+35+10 = 65 como techo."""
    puntaje = puntaje_fama_jugador(10**9, 10**5, 10**5)
    assert puntaje == 65
    assert 0 <= puntaje <= 100


# ----------------------------------------------------------------
#  apariciones_seleccion_jugador (consulta real a apariciones_mundial)
# ----------------------------------------------------------------

@requiere_apariciones
def test_apariciones_messi_por_nombre_exacto():
    assert apariciones_seleccion_jugador("Lionel Messi") == 26


@requiere_apariciones
def test_apariciones_apodo_usa_fallback_de_apellido():
    """'Rafa Márquez' debe encontrar a 'Rafael Márquez' (19 apariciones)."""
    assert apariciones_seleccion_jugador("Rafa Márquez") == 19


@requiere_apariciones
def test_apariciones_cristiano_no_choca_con_ronaldo_brasileno():
    assert apariciones_seleccion_jugador("Cristiano Ronaldo") == 22


@requiere_apariciones
def test_apariciones_desconocido_o_vacio_da_cero():
    assert apariciones_seleccion_jugador("Jugador Inventado Xyz") == 0
    assert apariciones_seleccion_jugador("") == 0
    assert apariciones_seleccion_jugador(None) == 0


@requiere_apariciones
def test_la_senal_de_seleccion_sube_el_puntaje():
    sin_nombre = puntaje_fama_jugador(35000000, 526, 452)
    con_nombre = puntaje_fama_jugador(35000000, 526, 452, "Lionel Messi")
    assert con_nombre > sin_nombre
    assert con_nombre <= 100


@requiere_apariciones
def test_calcular_dificultad_jugador_es_coherente():
    """La etiqueta que regresa debe corresponder al puntaje que regresa."""
    etiqueta, puntaje = calcular_dificultad_jugador(35000000, 526, 452, "Lionel Messi")
    assert etiqueta == asignar_dificultad(puntaje)
    assert etiqueta == "Fácil"  # Messi debe ser la pregunta más fácil posible
