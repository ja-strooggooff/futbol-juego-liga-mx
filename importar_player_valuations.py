import requests
import gzip
import csv
import io
import sqlite3

URL = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/player_valuations.csv.gz"


def crear_tabla_player_valuations(conexion):
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS player_valuations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER,
            fecha TEXT,
            valor_mercado REAL,
            club_nombre TEXT,
            club_id INTEGER,
            liga_codigo TEXT
        )
    """)
    conexion.execute("CREATE INDEX IF NOT EXISTS idx_valuations_player ON player_valuations(player_id)")
    conexion.execute("CREATE INDEX IF NOT EXISTS idx_valuations_fecha ON player_valuations(fecha)")
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


def descargar_player_valuations():
    print("Descargando player_valuations...")
    respuesta = requests.get(URL)
    print(f"Status: {respuesta.status_code} | Tamaño: {len(respuesta.content) / 1024 / 1024:.2f} MB")
    contenido = gzip.decompress(respuesta.content).decode("utf-8")
    return csv.DictReader(io.StringIO(contenido))


def guardar_player_valuations(conexion, lector):
    cursor = conexion.cursor()
    nuevos = 0
    contador = 0

    for fila in lector:
        player_id = limpiar_entero(fila.get("player_id"))
        if not player_id:
            continue

        cursor.execute("""
            INSERT INTO player_valuations
            (player_id, fecha, valor_mercado, club_nombre, club_id, liga_codigo)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            player_id,
            fila.get("date"),
            limpiar_decimal(fila.get("market_value_in_eur")),
            fila.get("current_club_name"),
            limpiar_entero(fila.get("current_club_id")),
            fila.get("player_club_domestic_competition_id"),
        ))
        nuevos += 1
        contador += 1

        if contador % 100000 == 0:
            conexion.commit()
            print(f"  Procesadas {contador} filas...")

    conexion.commit()
    return nuevos, contador


def main():
    conexion = sqlite3.connect("futtrivia.db")
    crear_tabla_player_valuations(conexion)

    lector = descargar_player_valuations()
    nuevos, total = guardar_player_valuations(conexion, lector)
    conexion.close()

    print(f"\n¡Listo!")
    print(f"Total filas procesadas: {total}")
    print(f"Valuaciones guardadas: {nuevos}")


if __name__ == "__main__":
    main()