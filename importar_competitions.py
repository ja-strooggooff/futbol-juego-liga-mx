import requests
import gzip
import csv
import io
import sqlite3

URL = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/competitions.csv.gz"


def crear_tabla_competitions(conexion):
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS competitions (
            competition_id TEXT PRIMARY KEY,
            nombre TEXT,
            tipo TEXT,
            sub_tipo TEXT,
            pais TEXT,
            confederacion TEXT,
            total_clubes INTEGER
        )
    """)
    conexion.commit()


def descargar_competitions():
    print("Descargando competitions...")
    respuesta = requests.get(URL)
    print(f"Status: {respuesta.status_code} | Tamaño: {len(respuesta.content) / 1024:.2f} KB")

    contenido = gzip.decompress(respuesta.content).decode("utf-8")
    lector = csv.DictReader(io.StringIO(contenido))
    return list(lector)


def limpiar_entero(valor_raw):
    if not valor_raw:
        return None
    try:
        return int(valor_raw)
    except ValueError:
        return None


def guardar_competitions(conexion, filas):
    cursor = conexion.cursor()
    nuevos = 0
    ya_existian = 0

    for fila in filas:
        competition_id = fila.get("competition_id")
        if not competition_id:
            continue

        cursor.execute("""
            INSERT OR IGNORE INTO competitions
            (competition_id, nombre, tipo, sub_tipo, pais, confederacion, total_clubes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            competition_id,
            fila.get("name"),
            fila.get("type"),
            fila.get("sub_type"),
            fila.get("country_name"),
            fila.get("confederation"),
            limpiar_entero(fila.get("total_clubs")),
        ))

        if cursor.rowcount == 0:
            ya_existian += 1
        else:
            nuevos += 1

    conexion.commit()
    return nuevos, ya_existian


def main():
    conexion = sqlite3.connect("futtrivia.db")
    crear_tabla_competitions(conexion)

    filas = descargar_competitions()
    print(f"Total de competiciones en el archivo: {len(filas)}")

    nuevos, ya_existian = guardar_competitions(conexion, filas)
    conexion.close()

    print(f"\n¡Listo!")
    print(f"Competiciones nuevas: {nuevos}")
    print(f"Ya existían: {ya_existian}")


if __name__ == "__main__":
    main()