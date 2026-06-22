import requests
import gzip
import csv
import io
import sqlite3

URL = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/appearances.csv.gz"


def crear_tabla_appearances(conexion):
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS appearances (
            appearance_id TEXT PRIMARY KEY,
            game_id TEXT,
            player_id INTEGER,
            player_name TEXT,
            competition_id TEXT,
            fecha TEXT,
            goles INTEGER,
            asistencias INTEGER,
            minutos_jugados INTEGER,
            tarjetas_amarillas INTEGER,
            tarjetas_rojas INTEGER
        )
    """)
    # Un indice en player_id hace MUCHO mas rapidas las consultas
    # tipo "todas las apariciones de este jugador"
    conexion.execute("CREATE INDEX IF NOT EXISTS idx_appearances_player ON appearances(player_id)")
    conexion.commit()


def limpiar_entero(valor_raw):
    if not valor_raw:
        return None
    try:
        return int(valor_raw)
    except ValueError:
        return None


def descargar_appearances():
    print("Descargando appearances (archivo grande, ten paciencia)...")
    respuesta = requests.get(URL)
    print(f"Status: {respuesta.status_code} | Tamaño: {len(respuesta.content) / 1024 / 1024:.2f} MB")

    contenido = gzip.decompress(respuesta.content).decode("utf-8")
    lector = csv.DictReader(io.StringIO(contenido))
    return lector  # Nota: NO usamos list() aqui, lo procesamos fila por fila para no usar tanta memoria


def guardar_appearances(conexion, lector):
    cursor = conexion.cursor()
    nuevos = 0
    contador = 0

    for fila in lector:
        appearance_id = fila.get("appearance_id")
        if not appearance_id:
            continue

        cursor.execute("""
            INSERT OR IGNORE INTO appearances
            (appearance_id, game_id, player_id, player_name, competition_id,
             fecha, goles, asistencias, minutos_jugados, tarjetas_amarillas, tarjetas_rojas)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            appearance_id,
            fila.get("game_id"),
            limpiar_entero(fila.get("player_id")),
            fila.get("player_name"),
            fila.get("competition_id"),
            fila.get("date"),
            limpiar_entero(fila.get("goals")),
            limpiar_entero(fila.get("assists")),
            limpiar_entero(fila.get("minutes_played")),
            limpiar_entero(fila.get("yellow_cards")),
            limpiar_entero(fila.get("red_cards")),
        ))

        if cursor.rowcount > 0:
            nuevos += 1

        contador += 1
        if contador % 100000 == 0:
            conexion.commit()  # guardamos en bloques para no perder todo si algo falla
            print(f"  Procesadas {contador} filas...")

    conexion.commit()
    return nuevos, contador


def main():
    conexion = sqlite3.connect("futtrivia.db")
    crear_tabla_appearances(conexion)

    lector = descargar_appearances()
    nuevos, total = guardar_appearances(conexion, lector)
    conexion.close()

    print(f"\n¡Listo!")
    print(f"Total de filas procesadas: {total}")
    print(f"Apariciones nuevas guardadas: {nuevos}")


if __name__ == "__main__":
    main()