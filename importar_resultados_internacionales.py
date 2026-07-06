"""
Importa a futtrivia.db los resultados de selecciones nacionales desde 1872
del dataset martj42/international_results (results.csv en GitHub).

Los partidos van a la tabla nueva `resultados_internacionales`; NO se mezclan
con `partidos` (que conserva su fuente openfootball). El traslape entre
fuentes está documentado en docs/diagnostico-fuentes-selecciones.md.
"""

import csv
import os
import sqlite3

import requests

URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
RUTA_CSV = "downloads/international_results.csv"


def crear_tabla(conexion):
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS resultados_internacionales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            equipo_local TEXT,
            equipo_visitante TEXT,
            goles_local INTEGER,
            goles_visitante INTEGER,
            torneo TEXT,
            ciudad TEXT,
            pais TEXT,
            cancha_neutral INTEGER,
            UNIQUE(fecha, equipo_local, equipo_visitante)
        )
    """)
    conexion.execute(
        "CREATE INDEX IF NOT EXISTS idx_resint_fecha ON resultados_internacionales(fecha)"
    )
    conexion.execute(
        "CREATE INDEX IF NOT EXISTS idx_resint_torneo ON resultados_internacionales(torneo)"
    )
    conexion.commit()


def limpiar_entero(valor_raw):
    if not valor_raw or valor_raw == "NA":
        return None
    try:
        return int(float(valor_raw))
    except ValueError:
        return None


def descargar_resultados():
    if not os.path.exists(RUTA_CSV):
        print("Descargando results.csv de martj42/international_results...")
        respuesta = requests.get(URL, timeout=120)
        respuesta.raise_for_status()
        os.makedirs(os.path.dirname(RUTA_CSV), exist_ok=True)
        with open(RUTA_CSV, "wb") as archivo:
            archivo.write(respuesta.content)
        print(f"Tamaño: {len(respuesta.content) / 1024 / 1024:.2f} MB")
    with open(RUTA_CSV, encoding="utf-8") as archivo:
        return list(csv.DictReader(archivo))


def guardar_resultados(conexion, filas):
    cursor = conexion.cursor()
    nuevos = 0
    ya_existian = 0

    for fila in filas:
        cursor.execute("""
            INSERT OR IGNORE INTO resultados_internacionales
            (fecha, equipo_local, equipo_visitante, goles_local, goles_visitante,
             torneo, ciudad, pais, cancha_neutral)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fila.get("date"),
            fila.get("home_team"),
            fila.get("away_team"),
            limpiar_entero(fila.get("home_score")),
            limpiar_entero(fila.get("away_score")),
            fila.get("tournament"),
            fila.get("city"),
            fila.get("country"),
            1 if fila.get("neutral") == "TRUE" else 0,
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

    filas = descargar_resultados()
    print(f"Total de partidos en el archivo: {len(filas)}")

    nuevos, ya_existian = guardar_resultados(conexion, filas)
    conexion.close()

    print("\n¡Listo!")
    print(f"Partidos nuevos: {nuevos}")
    print(f"Ya existían: {ya_existian}")


if __name__ == "__main__":
    main()
