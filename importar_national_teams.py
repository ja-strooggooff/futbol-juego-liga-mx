import requests
import gzip
import csv
import io
import sqlite3

URL = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/national_teams.csv.gz"


def crear_tabla_national_teams(conexion):
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS national_teams (
            national_team_id INTEGER PRIMARY KEY,
            nombre TEXT,
            country_id INTEGER,
            pais TEXT,
            confederacion TEXT,
            imagen_url TEXT,
            tamano_plantilla INTEGER,
            edad_promedio REAL,
            valor_mercado REAL,
            entrenador TEXT,
            ranking_fifa INTEGER,
            ultima_temporada INTEGER
        )
    """)
    conexion.commit()


def limpiar_entero(valor_raw):
    if not valor_raw:
        return None
    try:
        return int(float(valor_raw))
    except ValueError:
        return None


def limpiar_decimal(valor_raw):
    if not valor_raw:
        return None
    try:
        return float(valor_raw)
    except ValueError:
        return None


def main():
    print("Descargando national_teams...")
    respuesta = requests.get(URL)
    print(f"Status: {respuesta.status_code} | Tamaño: {len(respuesta.content) / 1024:.2f} KB")

    contenido = gzip.decompress(respuesta.content).decode("utf-8")
    filas = list(csv.DictReader(io.StringIO(contenido)))
    print(f"Total selecciones: {len(filas)}")

    conexion = sqlite3.connect("futtrivia.db")
    crear_tabla_national_teams(conexion)
    cursor = conexion.cursor()
    nuevos = 0

    for fila in filas:
        team_id = limpiar_entero(fila.get("national_team_id"))
        if not team_id:
            continue
        cursor.execute("""
            INSERT OR IGNORE INTO national_teams
            (national_team_id, nombre, country_id, pais, confederacion, imagen_url,
             tamano_plantilla, edad_promedio, valor_mercado, entrenador, ranking_fifa, ultima_temporada)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            team_id,
            fila.get("name"),
            limpiar_entero(fila.get("country_id")),
            fila.get("country_name"),
            fila.get("confederation"),
            fila.get("team_image_url"),
            limpiar_entero(fila.get("squad_size")),
            limpiar_decimal(fila.get("average_age")),
            limpiar_decimal(fila.get("total_market_value")),
            fila.get("coach_name"),
            limpiar_entero(fila.get("fifa_ranking")),
            limpiar_entero(fila.get("last_season")),
        ))
        if cursor.rowcount > 0:
            nuevos += 1

    conexion.commit()
    conexion.close()
    print(f"Selecciones guardadas: {nuevos}")


if __name__ == "__main__":
    main()