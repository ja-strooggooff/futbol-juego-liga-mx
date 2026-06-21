import requests
import gzip
import csv
import io
import sqlite3

URL = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/clubs.csv.gz"


def crear_tabla_clubs(conexion):
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS clubs (
            club_id INTEGER PRIMARY KEY,
            nombre TEXT,
            liga_codigo TEXT,
            tamano_plantilla INTEGER,
            edad_promedio REAL,
            jugadores_extranjeros INTEGER,
            jugadores_seleccion_nacional INTEGER,
            estadio TEXT,
            capacidad_estadio INTEGER,
            balance_transferencias TEXT,
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


def descargar_clubs():
    print("Descargando clubs...")
    respuesta = requests.get(URL)
    print(f"Status: {respuesta.status_code} | Tamaño: {len(respuesta.content) / 1024:.2f} KB")

    contenido = gzip.decompress(respuesta.content).decode("utf-8")
    lector = csv.DictReader(io.StringIO(contenido))
    return list(lector)


def guardar_clubs(conexion, filas):
    cursor = conexion.cursor()
    nuevos = 0
    ya_existian = 0

    for fila in filas:
        try:
            club_id = int(fila["club_id"])
        except (ValueError, KeyError):
            continue

        cursor.execute("""
            INSERT OR IGNORE INTO clubs
            (club_id, nombre, liga_codigo, tamano_plantilla, edad_promedio,
             jugadores_extranjeros, jugadores_seleccion_nacional, estadio,
             capacidad_estadio, balance_transferencias, ultima_temporada)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            club_id,
            fila.get("name"),
            fila.get("domestic_competition_id"),
            limpiar_entero(fila.get("squad_size")),
            limpiar_decimal(fila.get("average_age")),
            limpiar_entero(fila.get("foreigners_number")),
            limpiar_entero(fila.get("national_team_players")),
            fila.get("stadium_name"),
            limpiar_entero(fila.get("stadium_seats")),
            fila.get("net_transfer_record"),
            limpiar_entero(fila.get("last_season")),
        ))

        if cursor.rowcount == 0:
            ya_existian += 1
        else:
            nuevos += 1

    conexion.commit()
    return nuevos, ya_existian


def main():
    conexion = sqlite3.connect("futtrivia.db")
    crear_tabla_clubs(conexion)

    filas = descargar_clubs()
    print(f"Total de clubes en el archivo: {len(filas)}")

    nuevos, ya_existian = guardar_clubs(conexion, filas)
    conexion.close()

    print(f"\n¡Listo!")
    print(f"Clubes nuevos: {nuevos}")
    print(f"Ya existían: {ya_existian}")


if __name__ == "__main__":
    main()