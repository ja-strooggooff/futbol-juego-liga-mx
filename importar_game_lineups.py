import requests
import gzip
import csv
import io
import sqlite3

URL = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/game_lineups.csv.gz"


def crear_tabla_game_lineups(conexion):
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS game_lineups (
            game_lineups_id TEXT PRIMARY KEY,
            game_id INTEGER,
            fecha TEXT,
            player_id INTEGER,
            club_id INTEGER,
            player_name TEXT,
            tipo TEXT,
            posicion TEXT,
            numero INTEGER,
            capitan INTEGER
        )
    """)
    conexion.execute("CREATE INDEX IF NOT EXISTS idx_lineups_game ON game_lineups(game_id)")
    conexion.execute("CREATE INDEX IF NOT EXISTS idx_lineups_player ON game_lineups(player_id)")
    conexion.execute("CREATE INDEX IF NOT EXISTS idx_lineups_club ON game_lineups(club_id)")
    conexion.commit()


def limpiar_entero(valor_raw):
    if not valor_raw:
        return None
    try:
        return int(float(valor_raw))
    except ValueError:
        return None


def descargar_game_lineups():
    print("Descargando game_lineups (archivo muy grande, ten paciencia)...")
    respuesta = requests.get(URL)
    print(f"Status: {respuesta.status_code} | Tamaño comprimido: {len(respuesta.content) / 1024 / 1024:.2f} MB")
    contenido = gzip.decompress(respuesta.content)
    print(f"Tamaño descomprimido: {len(contenido) / 1024 / 1024:.2f} MB")
    return csv.DictReader(io.StringIO(contenido.decode("utf-8")))


def guardar_game_lineups(conexion, lector):
    cursor = conexion.cursor()
    nuevos = 0
    contador = 0

    for fila in lector:
        game_lineups_id = fila.get("game_lineups_id")
        if not game_lineups_id:
            continue

        cursor.execute("""
            INSERT OR IGNORE INTO game_lineups
            (game_lineups_id, game_id, fecha, player_id, club_id,
             player_name, tipo, posicion, numero, capitan)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            game_lineups_id,
            limpiar_entero(fila.get("game_id")),
            fila.get("date"),
            limpiar_entero(fila.get("player_id")),
            limpiar_entero(fila.get("club_id")),
            fila.get("player_name"),
            fila.get("type"),
            fila.get("position"),
            limpiar_entero(fila.get("number")),
            limpiar_entero(fila.get("team_captain")),
        ))

        if cursor.rowcount > 0:
            nuevos += 1

        contador += 1
        if contador % 100000 == 0:
            conexion.commit()
            print(f"  Procesadas {contador} filas...")

    conexion.commit()
    return nuevos, contador


def main():
    conexion = sqlite3.connect("futtrivia.db")
    crear_tabla_game_lineups(conexion)

    lector = descargar_game_lineups()
    nuevos, total = guardar_game_lineups(conexion, lector)
    conexion.close()

    print(f"\n¡Listo!")
    print(f"Total filas procesadas: {total}")
    print(f"Registros nuevos guardados: {nuevos}")


if __name__ == "__main__":
    main()