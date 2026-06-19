# crear_base_datos.py
import sqlite3

def crear_base_datos():
    conexion = sqlite3.connect("futtrivia.db")
    cursor = conexion.cursor()

    # UNIQUE evita que el mismo partido se guarde dos veces si corremos
    # el script otra vez en el futuro.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS partidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            torneo TEXT,
            fecha TEXT,
            equipo1 TEXT,
            equipo2 TEXT,
            goles1 INTEGER,
            goles2 INTEGER,
            estadio TEXT,
            grupo TEXT,
            UNIQUE(torneo, fecha, equipo1, equipo2)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS goles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            partido_id INTEGER,
            jugador TEXT,
            minuto TEXT,
            FOREIGN KEY (partido_id) REFERENCES partidos(id),
            UNIQUE(partido_id, jugador, minuto)
        )
    """)

    # Tabla nueva: guarda CUÁNDO fue la última vez que actualizamos
    # los datos, para saber si vale la pena volver a correr el script.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metadatos (
            clave TEXT PRIMARY KEY,
            valor TEXT
        )
    """)

    conexion.commit()
    conexion.close()
    print("Base de datos creada: futtrivia.db")

if __name__ == "__main__":
    crear_base_datos()