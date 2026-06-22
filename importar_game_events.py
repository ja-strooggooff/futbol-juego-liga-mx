import requests
import gzip
import csv
import io
import sqlite3

URL = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/game_events.csv.gz"


def crear_tabla_game_events(conexion):
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS game_events (
            game_event_id TEXT PRIMARY KEY,
            game_id INTEGER,
            fecha TEXT,
            minuto INTEGER,
            tipo TEXT,
            club_id INTEGER,
            club_nombre TEXT,
            player_id INTEGER,
            descripcion TEXT,
            player_in_id INTEGER,
            player_assist_id INTEGER
        )
    """)
    conexion.execute("CREATE INDEX IF NOT EXISTS idx_game_events_game ON game_events(game_id)")
    conexion.execute("CREATE INDEX IF NOT EXISTS idx_game_events_player ON game_events(player_id)")
    conexion.execute("CREATE INDEX IF NOT EXISTS idx_game_events_tipo ON game_events(tipo)")
    conexion.commit()


def limpiar_entero(valor_raw):
    if not valor_raw:
        return None
    try:
        return int(float(valor_raw))
    except ValueError:
        return None


def descargar_game_events():
    print("Descargando game_events (archivo grande, ten paciencia)...")
    respuesta = requests.get(URL)
    print(f"Status: {respuesta.status_code} | Tamaño: {len(respuesta.content) / 1024 / 1024:.2f} MB")
    contenido = gzip.decompress(respuesta.content).decode("utf-8")
    return csv.DictReader(io.StringIO(contenido))


def guardar_game_events(conexion, lector):
    cursor = conexion.cursor()
    nuevos = 0
    contador = 0

    for fila in lector:
        game_event_id = fila.get("game_event_id")
        if not game_event_id:
            continue

        cursor.execute("""
            INSERT OR IGNORE INTO game_events
            (game_event_id, game_id, fecha, minuto, tipo, club_id, club_nombre,
             player_id, descripcion, player_in_id, player_assist_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            game_event_id,
            limpiar_entero(fila.get("game_id")),
            fila.get("date"),
            limpiar_entero(fila.get("minute")),
            fila.get("type"),
            limpiar_entero(fila.get("club_id")),
            fila.get("club_name"),
            limpiar_entero(fila.get("player_id")),
            fila.get("description"),
            limpiar_entero(fila.get("player_in_id")),
            limpiar_entero(fila.get("player_assist_id")),
        ))

        if cursor.rowcount > 0:
            nuevos += 1

        contador += 1
        if contador % 100000 == 0:
            conexion.commit()
            print(f"  Procesados {contador} eventos...")

    conexion.commit()
    return nuevos, contador


def main():
    conexion = sqlite3.connect("futtrivia.db")
    crear_tabla_game_events(conexion)

    lector = descargar_game_events()
    nuevos, total = guardar_game_events(conexion, lector)
    conexion.close()

    print(f"\n¡Listo!")
    print(f"Total eventos procesados: {total}")
    print(f"Eventos nuevos guardados: {nuevos}")


if __name__ == "__main__":
    main()