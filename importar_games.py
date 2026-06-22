import requests
import gzip
import csv
import io
import sqlite3

URL = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/games.csv.gz"


def crear_tabla_games(conexion):
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS games (
            game_id INTEGER PRIMARY KEY,
            competition_id TEXT,
            temporada INTEGER,
            ronda TEXT,
            fecha TEXT,
            club_local_id INTEGER,
            club_visitante_id INTEGER,
            goles_local INTEGER,
            goles_visitante INTEGER,
            club_local_nombre TEXT,
            club_visitante_nombre TEXT,
            estadio TEXT,
            asistencia INTEGER,
            arbitro TEXT,
            formacion_local TEXT,
            formacion_visitante TEXT,
            tipo_competicion TEXT
        )
    """)
    conexion.execute("CREATE INDEX IF NOT EXISTS idx_games_competition ON games(competition_id)")
    conexion.execute("CREATE INDEX IF NOT EXISTS idx_games_fecha ON games(fecha)")
    conexion.commit()


def limpiar_entero(valor_raw):
    if not valor_raw:
        return None
    try:
        return int(float(valor_raw))
    except ValueError:
        return None


def descargar_games():
    print("Descargando games...")
    respuesta = requests.get(URL)
    print(f"Status: {respuesta.status_code} | Tamaño: {len(respuesta.content) / 1024 / 1024:.2f} MB")
    contenido = gzip.decompress(respuesta.content).decode("utf-8")
    lector = csv.DictReader(io.StringIO(contenido))
    return list(lector)


def guardar_games(conexion, filas):
    cursor = conexion.cursor()
    nuevos = 0
    ya_existian = 0

    for fila in filas:
        try:
            game_id = int(fila["game_id"])
        except (ValueError, KeyError):
            continue

        cursor.execute("""
            INSERT OR IGNORE INTO games
            (game_id, competition_id, temporada, ronda, fecha,
             club_local_id, club_visitante_id, goles_local, goles_visitante,
             club_local_nombre, club_visitante_nombre, estadio, asistencia,
             arbitro, formacion_local, formacion_visitante, tipo_competicion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            game_id,
            fila.get("competition_id"),
            limpiar_entero(fila.get("season")),
            fila.get("round"),
            fila.get("date"),
            limpiar_entero(fila.get("home_club_id")),
            limpiar_entero(fila.get("away_club_id")),
            limpiar_entero(fila.get("home_club_goals")),
            limpiar_entero(fila.get("away_club_goals")),
            fila.get("home_club_name"),
            fila.get("away_club_name"),
            fila.get("stadium"),
            limpiar_entero(fila.get("attendance")),
            fila.get("referee"),
            fila.get("home_club_formation"),
            fila.get("away_club_formation"),
            fila.get("competition_type"),
        ))

        if cursor.rowcount == 0:
            ya_existian += 1
        else:
            nuevos += 1

    conexion.commit()
    return nuevos, ya_existian


def main():
    conexion = sqlite3.connect("futtrivia.db")
    crear_tabla_games(conexion)

    filas = descargar_games()
    print(f"Total de partidos en el archivo: {len(filas)}")

    nuevos, ya_existian = guardar_games(conexion, filas)
    conexion.close()

    print(f"\n¡Listo!")
    print(f"Partidos nuevos: {nuevos}")
    print(f"Ya existían: {ya_existian}")


if __name__ == "__main__":
    main()
    