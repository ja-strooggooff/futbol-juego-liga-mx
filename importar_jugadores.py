import requests
import gzip
import csv
import io
import sqlite3

URL = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/players.csv.gz"


def limpiar_fecha(fecha_raw):
    """Convierte '1978-06-09 00:00:00' en solo '1978-06-09'."""
    if not fecha_raw:
        return None
    return fecha_raw.split(" ")[0]


def limpiar_entero(valor_raw):
    """Convierte texto a número, o None si está vacío/raro."""
    if not valor_raw:
        return None
    try:
        return int(valor_raw)
    except ValueError:
        return None


def crear_tabla_jugadores(conexion):
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS jugadores_reales (
            player_id INTEGER PRIMARY KEY,
            nombre TEXT,
            posicion TEXT,
            posicion_especifica TEXT,
            pais TEXT,
            club TEXT,
            liga_codigo TEXT,
            fecha_nacimiento TEXT,
            valor_mercado INTEGER
        )
    """)
    conexion.commit()


def descargar_jugadores():
    print("Descargando jugadores de transfermarkt-datasets...")
    respuesta = requests.get(URL)
    print(f"Status: {respuesta.status_code} | Tamaño: {len(respuesta.content) / 1024 / 1024:.2f} MB")

    contenido = gzip.decompress(respuesta.content).decode("utf-8")
    lector = csv.DictReader(io.StringIO(contenido))
    return list(lector)


def guardar_jugadores(conexion, filas):
    cursor = conexion.cursor()
    nuevos = 0
    ya_existian = 0

    for fila in filas:
        try:
            player_id = int(fila["player_id"])
        except (ValueError, KeyError):
            continue  # fila sin ID válido, la saltamos

        cursor.execute("""
            INSERT OR IGNORE INTO jugadores_reales
            (player_id, nombre, posicion, posicion_especifica, pais, club, liga_codigo, fecha_nacimiento, valor_mercado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            player_id,
            fila.get("name"),
            fila.get("position"),
            fila.get("sub_position"),
            fila.get("country_of_citizenship"),
            fila.get("current_club_name"),
            fila.get("current_club_domestic_competition_id"),
            limpiar_fecha(fila.get("date_of_birth")),
            limpiar_entero(fila.get("market_value_in_eur")),
        ))

        if cursor.rowcount == 0:
            ya_existian += 1
        else:
            nuevos += 1

    conexion.commit()
    return nuevos, ya_existian


def main():
    conexion = sqlite3.connect("futtrivia.db")
    crear_tabla_jugadores(conexion)

    filas = descargar_jugadores()
    print(f"Total de jugadores en el archivo: {len(filas)}")

    nuevos, ya_existian = guardar_jugadores(conexion, filas)
    conexion.close()

    print(f"\n¡Listo!")
    print(f"Jugadores nuevos guardados: {nuevos}")
    print(f"Ya existían (no duplicados): {ya_existian}")


if __name__ == "__main__":
    main()