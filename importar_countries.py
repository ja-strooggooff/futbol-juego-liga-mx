import requests
import gzip
import csv
import io
import sqlite3

URL = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/countries.csv.gz"


def crear_tabla_countries(conexion):
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS countries (
            country_id INTEGER PRIMARY KEY,
            nombre TEXT,
            codigo TEXT,
            confederacion TEXT,
            total_clubes INTEGER,
            total_jugadores INTEGER,
            edad_promedio REAL
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
    print("Descargando countries...")
    respuesta = requests.get(URL)
    print(f"Status: {respuesta.status_code} | Tamaño: {len(respuesta.content) / 1024:.2f} KB")

    contenido = gzip.decompress(respuesta.content).decode("utf-8")
    filas = list(csv.DictReader(io.StringIO(contenido)))
    print(f"Total países: {len(filas)}")

    conexion = sqlite3.connect("futtrivia.db")
    crear_tabla_countries(conexion)
    cursor = conexion.cursor()
    nuevos = 0

    for fila in filas:
        country_id = limpiar_entero(fila.get("country_id"))
        if not country_id:
            continue
        cursor.execute("""
            INSERT OR IGNORE INTO countries
            (country_id, nombre, codigo, confederacion, total_clubes, total_jugadores, edad_promedio)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            country_id,
            fila.get("country_name"),
            fila.get("country_code"),
            fila.get("confederation"),
            limpiar_entero(fila.get("total_clubs")),
            limpiar_entero(fila.get("total_players")),
            limpiar_decimal(fila.get("average_age")),
        ))
        if cursor.rowcount > 0:
            nuevos += 1

    conexion.commit()
    conexion.close()
    print(f"Países guardados: {nuevos}")


if __name__ == "__main__":
    main()