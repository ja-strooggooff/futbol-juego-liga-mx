"""
Importa a futtrivia.db las apariciones de jugadores en Mundiales (masculinos
y femeninos) del dataset jfjelstul/worldcup (player_appearances.csv en GitHub).

Van a la tabla nueva `apariciones_mundial`, separada de `appearances` (que
solo cubre partidos de clubes y tiene otro esquema). El traslape de partidos
con games/partidos está documentado en docs/diagnostico-fuentes-selecciones.md.
"""

import csv
import os
import sqlite3

import requests

URL = "https://raw.githubusercontent.com/jfjelstul/worldcup/master/data-csv/player_appearances.csv"
RUTA_CSV = "downloads/wc_player_appearances.csv"


def crear_tabla(conexion):
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS apariciones_mundial (
            key_id INTEGER PRIMARY KEY,
            torneo_id TEXT,
            torneo_nombre TEXT,
            match_id TEXT,
            partido_nombre TEXT,
            fecha TEXT,
            fase TEXT,
            grupo TEXT,
            equipo_id TEXT,
            equipo_nombre TEXT,
            equipo_codigo TEXT,
            es_local INTEGER,
            player_id TEXT,
            apellido TEXT,
            nombre TEXT,
            dorsal INTEGER,
            posicion TEXT,
            posicion_codigo TEXT,
            titular INTEGER,
            suplente INTEGER
        )
    """)
    conexion.execute(
        "CREATE INDEX IF NOT EXISTS idx_aparmun_torneo ON apariciones_mundial(torneo_id)"
    )
    conexion.execute(
        "CREATE INDEX IF NOT EXISTS idx_aparmun_match ON apariciones_mundial(match_id)"
    )
    conexion.execute(
        "CREATE INDEX IF NOT EXISTS idx_aparmun_player ON apariciones_mundial(player_id)"
    )
    conexion.commit()


def limpiar_entero(valor_raw):
    if not valor_raw or valor_raw == "NA":
        return None
    try:
        return int(float(valor_raw))
    except ValueError:
        return None


def descargar_apariciones():
    if not os.path.exists(RUTA_CSV):
        print("Descargando player_appearances.csv de jfjelstul/worldcup...")
        respuesta = requests.get(URL, timeout=120)
        respuesta.raise_for_status()
        os.makedirs(os.path.dirname(RUTA_CSV), exist_ok=True)
        with open(RUTA_CSV, "wb") as archivo:
            archivo.write(respuesta.content)
        print(f"Tamaño: {len(respuesta.content) / 1024 / 1024:.2f} MB")
    with open(RUTA_CSV, encoding="utf-8") as archivo:
        return list(csv.DictReader(archivo))


def guardar_apariciones(conexion, filas):
    cursor = conexion.cursor()
    nuevos = 0
    ya_existian = 0

    for fila in filas:
        key_id = limpiar_entero(fila.get("key_id"))
        if key_id is None:
            continue

        cursor.execute("""
            INSERT OR IGNORE INTO apariciones_mundial
            (key_id, torneo_id, torneo_nombre, match_id, partido_nombre, fecha,
             fase, grupo, equipo_id, equipo_nombre, equipo_codigo, es_local,
             player_id, apellido, nombre, dorsal, posicion, posicion_codigo,
             titular, suplente)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            key_id,
            fila.get("tournament_id"),
            fila.get("tournament_name"),
            fila.get("match_id"),
            fila.get("match_name"),
            fila.get("match_date"),
            fila.get("stage_name"),
            fila.get("group_name"),
            fila.get("team_id"),
            fila.get("team_name"),
            fila.get("team_code"),
            limpiar_entero(fila.get("home_team")),
            fila.get("player_id"),
            fila.get("family_name"),
            fila.get("given_name"),
            limpiar_entero(fila.get("shirt_number")),
            fila.get("position_name"),
            fila.get("position_code"),
            limpiar_entero(fila.get("starter")),
            limpiar_entero(fila.get("substitute")),
        ))

        if cursor.rowcount == 0:
            ya_existian += 1
        else:
            nuevos += 1

    conexion.commit()
    return nuevos, ya_existian


def main():
    conexion = sqlite3.connect("futtrivia.db")
    crear_tabla(conexion)

    filas = descargar_apariciones()
    print(f"Total de apariciones en el archivo: {len(filas)}")

    nuevos, ya_existian = guardar_apariciones(conexion, filas)
    conexion.close()

    print("\n¡Listo!")
    print(f"Apariciones nuevas: {nuevos}")
    print(f"Ya existían: {ya_existian}")


if __name__ == "__main__":
    main()
