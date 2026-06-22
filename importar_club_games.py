import requests
import gzip
import csv
import io
import sqlite3

URL = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/club_games.csv.gz"


def crear_tabla_club_games(conexion):
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS club_games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER,
            club_id INTEGER,
            goles_propios INTEGER,
            posicion_propia INTEGER,
            manager_propio TEXT,
            oponente_id INTEGER,
            goles_oponente INTEGER,
            posicion_oponente INTEGER,
            manager_oponente TEXT,
            local_visitante TEXT,
            gano INTEGER
        )
    """)
    conexion.execute("CREATE INDEX IF NOT EXISTS idx_club_games_game ON club_games(game_id)")
    conexion.execute("CREATE INDEX IF NOT EXISTS idx_club_games_club ON club_games(club_id)")
    conexion.commit()


def limpiar_entero(valor_raw):
    if not valor_raw:
        return None
    try:
        return int(float(valor_raw))
    except ValueError:
        return None


def descargar_club_games():
    print("Descargando club_games...")
    respuesta = requests.get(URL)
    print(f"Status: {respuesta.status_code} | Tamaño: {len(respuesta.content) / 1024 / 1024:.2f} MB")
    contenido = gzip.decompress(respuesta.content).decode("utf-8")
    lector = csv.DictReader(io.StringIO(contenido))
    return list(lector)


def guardar_club_games(conexion, filas):
    cursor = conexion.cursor()
    nuevos = 0

    for fila in filas:
        game_id = limpiar_entero(fila.get("game_id"))
        club_id = limpiar_entero(fila.get("club_id"))
        if not game_id or not club_id:
            continue

        cursor.execute("""
            INSERT INTO club_games
            (game_id, club_id, goles_propios, posicion_propia, manager_propio,
             oponente_id, goles_oponente, posicion_oponente, manager_oponente,
             local_visitante, gano)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            game_id,
            club_id,
            limpiar_entero(fila.get("own_goals")),
            limpiar_entero(fila.get("own_position")),
            fila.get("own_manager_name"),
            limpiar_entero(fila.get("opponent_id")),
            limpiar_entero(fila.get("opponent_goals")),
            limpiar_entero(fila.get("opponent_position")),
            fila.get("opponent_manager_name"),
            fila.get("hosting"),
            limpiar_entero(fila.get("is_win")),
        ))
        nuevos += 1

    conexion.commit()
    return nuevos


def main():
    conexion = sqlite3.connect("futtrivia.db")
    crear_tabla_club_games(conexion)

    filas = descargar_club_games()
    print(f"Total de filas en el archivo: {len(filas)}")

    nuevos = guardar_club_games(conexion, filas)
    conexion.close()

    print(f"\n¡Listo!")
    print(f"Registros guardados: {nuevos}")


if __name__ == "__main__":
    main()