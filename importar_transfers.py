import requests
import gzip
import csv
import io
import sqlite3

URL = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/transfers.csv.gz"


def crear_tabla_transfers(conexion):
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER,
            player_name TEXT,
            fecha_transferencia TEXT,
            temporada TEXT,
            club_origen_id INTEGER,
            club_destino_id INTEGER,
            club_origen_nombre TEXT,
            club_destino_nombre TEXT,
            monto_transferencia REAL,
            valor_mercado REAL
        )
    """)
    conexion.execute("CREATE INDEX IF NOT EXISTS idx_transfers_player ON transfers(player_id)")
    conexion.execute("CREATE INDEX IF NOT EXISTS idx_transfers_fecha ON transfers(fecha_transferencia)")
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


def descargar_transfers():
    print("Descargando transfers...")
    respuesta = requests.get(URL)
    print(f"Status: {respuesta.status_code} | Tamaño: {len(respuesta.content) / 1024 / 1024:.2f} MB")
    contenido = gzip.decompress(respuesta.content).decode("utf-8")
    lector = csv.DictReader(io.StringIO(contenido))
    return list(lector)


def guardar_transfers(conexion, filas):
    cursor = conexion.cursor()
    nuevos = 0

    for fila in filas:
        player_id = limpiar_entero(fila.get("player_id"))
        if not player_id:
            continue

        cursor.execute("""
            INSERT INTO transfers
            (player_id, player_name, fecha_transferencia, temporada,
             club_origen_id, club_destino_id, club_origen_nombre, club_destino_nombre,
             monto_transferencia, valor_mercado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            player_id,
            fila.get("player_name"),
            fila.get("transfer_date"),
            fila.get("transfer_season"),
            limpiar_entero(fila.get("from_club_id")),
            limpiar_entero(fila.get("to_club_id")),
            fila.get("from_club_name"),
            fila.get("to_club_name"),
            limpiar_decimal(fila.get("transfer_fee")),
            limpiar_decimal(fila.get("market_value_in_eur")),
        ))
        nuevos += 1

    conexion.commit()
    return nuevos


def main():
    conexion = sqlite3.connect("futtrivia.db")
    crear_tabla_transfers(conexion)

    filas = descargar_transfers()
    print(f"Total de transferencias en el archivo: {len(filas)}")

    nuevos = guardar_transfers(conexion, filas)
    conexion.close()

    print(f"\n¡Listo!")
    print(f"Transferencias guardadas: {nuevos}")


if __name__ == "__main__":
    main()