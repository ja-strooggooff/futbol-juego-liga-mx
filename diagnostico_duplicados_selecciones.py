"""
Diagnóstico de duplicados ANTES de importar las 2 fuentes nuevas:

1. martj42/international_results (results.csv): resultados de selecciones desde 1872
2. jfjelstul/worldcup (player_appearances.csv): apariciones de jugadores en Mundiales

Compara cada partido nuevo contra las tablas existentes `games` y `partidos`
usando la llave fecha + pareja de equipos (sin importar el orden local/visitante,
con nombres normalizados a minúsculas).

Los CSV se leen de downloads/ (correr antes los importadores con --solo-descargar
o este mismo script, que los descarga si faltan).
"""

import csv
import os
import sqlite3

import requests

RUTA_RESULTADOS = "downloads/international_results.csv"
RUTA_APARICIONES = "downloads/wc_player_appearances.csv"

URL_RESULTADOS = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
URL_APARICIONES = "https://raw.githubusercontent.com/jfjelstul/worldcup/master/data-csv/player_appearances.csv"


def descargar_si_falta(ruta, url):
    if os.path.exists(ruta):
        return
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    print(f"Descargando {url} ...")
    respuesta = requests.get(url, timeout=120)
    respuesta.raise_for_status()
    with open(ruta, "wb") as archivo:
        archivo.write(respuesta.content)
    print(f"  Guardado en {ruta} ({len(respuesta.content) / 1024 / 1024:.2f} MB)")


def normalizar_equipo(nombre):
    if not nombre:
        return ""
    return nombre.strip().lower()


def llave_partido(fecha, equipo_a, equipo_b):
    """Llave única de un partido: fecha + equipos ordenados alfabéticamente,
    para que 'A vs B' y 'B vs A' cuenten como el mismo partido."""
    par = sorted([normalizar_equipo(equipo_a), normalizar_equipo(equipo_b)])
    return (fecha, par[0], par[1])


def llaves_existentes(conexion):
    """Regresa las llaves de todos los partidos ya guardados en games y partidos."""
    cursor = conexion.cursor()

    llaves_games = set()
    for fecha, local, visitante in cursor.execute(
        "SELECT fecha, club_local_nombre, club_visitante_nombre FROM games"
    ):
        llaves_games.add(llave_partido(fecha, local, visitante))

    llaves_partidos = set()
    for fecha, equipo1, equipo2 in cursor.execute(
        "SELECT fecha, equipo1, equipo2 FROM partidos"
    ):
        llaves_partidos.add(llave_partido(fecha, equipo1, equipo2))

    return llaves_games, llaves_partidos


def partidos_de_resultados_internacionales():
    """Un partido por fila del CSV de martj42."""
    with open(RUTA_RESULTADOS, encoding="utf-8") as archivo:
        for fila in csv.DictReader(archivo):
            yield llave_partido(fila["date"], fila["home_team"], fila["away_team"])


def partidos_de_apariciones_mundial():
    """El CSV de jfjelstul tiene una fila POR JUGADOR; aquí sacamos los
    partidos distintos (match_name viene como 'Equipo A vs Equipo B')."""
    partidos = set()
    with open(RUTA_APARICIONES, encoding="utf-8") as archivo:
        for fila in csv.DictReader(archivo):
            nombre = fila["match_name"]
            if " vs " not in nombre:
                continue
            equipo_a, equipo_b = nombre.split(" vs ", 1)
            partidos.add(llave_partido(fila["match_date"], equipo_a, equipo_b))
    return partidos


def diagnosticar(nombre_fuente, llaves_fuente, llaves_games, llaves_partidos):
    llaves_fuente = set(llaves_fuente)
    en_games = llaves_fuente & llaves_games
    en_partidos = llaves_fuente & llaves_partidos
    en_alguna = en_games | en_partidos
    nuevos = llaves_fuente - en_alguna

    print(f"\n=== {nombre_fuente} ===")
    print(f"Partidos distintos en la fuente: {len(llaves_fuente)}")
    print(f"Duplicados contra games:         {len(en_games)}")
    print(f"Duplicados contra partidos:      {len(en_partidos)}")
    print(f"Duplicados contra alguna tabla:  {len(en_alguna)}")
    print(f"Partidos NUEVOS:                 {len(nuevos)}")
    return len(llaves_fuente), len(en_games), len(en_partidos), len(en_alguna), len(nuevos)


def main():
    descargar_si_falta(RUTA_RESULTADOS, URL_RESULTADOS)
    descargar_si_falta(RUTA_APARICIONES, URL_APARICIONES)

    conexion = sqlite3.connect("futtrivia.db")
    llaves_games, llaves_partidos = llaves_existentes(conexion)
    conexion.close()
    print(f"Partidos ya en games:    {len(llaves_games)}")
    print(f"Partidos ya en partidos: {len(llaves_partidos)}")

    diagnosticar(
        "martj42/international_results (results.csv)",
        partidos_de_resultados_internacionales(),
        llaves_games,
        llaves_partidos,
    )
    diagnosticar(
        "jfjelstul/worldcup (player_appearances.csv, partidos distintos)",
        partidos_de_apariciones_mundial(),
        llaves_games,
        llaves_partidos,
    )

    print("\nNota: la comparación es por nombre exacto normalizado; si dos fuentes")
    print("escriben distinto al mismo equipo (p. ej. 'USA' vs 'United States'),")
    print("ese partido cuenta como nuevo aunque sea el mismo.")


if __name__ == "__main__":
    main()
