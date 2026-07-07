"""
Precalcula la dificultad (Fácil/Media/Difícil/Legendaria) de TODOS los
jugadores de jugadores_reales usando sistema_dificultad.py, y la guarda
en la tabla dificultad_jugadores.

¿Por qué un script aparte? Calcular el puntaje necesita agregar la tabla
appearances (1.8M filas) y cruzar apariciones_mundial: hacerlo al vuelo
en app.py tardaría ~30 segundos en cada arranque. Aquí se hace UNA vez
en lote (dos consultas grandes + cruces en memoria) y app.py solo lee
la tabla con un JOIN barato.

Correr de nuevo cuando cambien los datos (reimportaciones).
"""

import sqlite3
import time

from sistema_dificultad import asignar_dificultad, puntaje_fama_jugador


def crear_tabla(conexion):
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS dificultad_jugadores (
            player_id INTEGER PRIMARY KEY,
            puntaje REAL,
            dificultad TEXT
        )
    """)
    conexion.commit()


def cargar_stats_clubes(cursor):
    """Apariciones y goles de carrera por jugador, en UNA sola pasada."""
    print("Agregando appearances (1.8M filas, tarda un poco)...")
    inicio = time.time()
    stats = {
        player_id: (apariciones, goles)
        for player_id, apariciones, goles in cursor.execute(
            "SELECT player_id, COUNT(*), COALESCE(SUM(goles), 0) FROM appearances GROUP BY player_id"
        )
    }
    print(f"  {len(stats)} jugadores con stats en {time.time() - inicio:.1f}s")
    return stats


def cargar_apariciones_mundial(cursor):
    """Conteo de apariciones en Mundiales por nombre completo normalizado
    (la misma regla que apariciones_seleccion_jugador, pero en memoria)."""
    from sistema_dificultad import RUTA_BD  # noqa: F401  (misma BD)
    import unicodedata

    def normalizar(texto):
        texto = unicodedata.normalize("NFD", (texto or "").lower())
        return "".join(c for c in texto if unicodedata.category(c) != "Mn")

    conteos = {}
    for nombre, apellido, total in cursor.execute("""
        SELECT nombre, apellido, COUNT(*) FROM apariciones_mundial
        GROUP BY nombre, apellido
    """):
        completo = apellido if nombre == "not applicable" else f"{nombre} {apellido}"
        clave = normalizar(completo)
        conteos[clave] = conteos.get(clave, 0) + total
    print(f"  {len(conteos)} nombres con apariciones en Mundiales")
    return conteos, normalizar


def main():
    conexion = sqlite3.connect("futtrivia.db")
    cursor = conexion.cursor()
    crear_tabla(conexion)

    stats = cargar_stats_clubes(cursor)
    mundial, normalizar = cargar_apariciones_mundial(cursor)

    jugadores = cursor.execute(
        "SELECT player_id, nombre, valor_mercado FROM jugadores_reales WHERE nombre IS NOT NULL"
    ).fetchall()
    print(f"Calculando dificultad de {len(jugadores)} jugadores...")

    filas = []
    for player_id, nombre, valor in jugadores:
        apariciones, goles = stats.get(player_id, (0, 0))
        seleccion = mundial.get(normalizar(nombre), 0)
        puntaje = puntaje_fama_jugador(
            valor or 0, apariciones, goles,
            apariciones_seleccion=seleccion,
        )
        filas.append((player_id, puntaje, asignar_dificultad(puntaje)))

    cursor.executemany(
        "INSERT OR REPLACE INTO dificultad_jugadores (player_id, puntaje, dificultad) VALUES (?, ?, ?)",
        filas,
    )
    conexion.commit()

    print("\n¡Listo! Distribución:")
    for dificultad, total in cursor.execute(
        "SELECT dificultad, COUNT(*) FROM dificultad_jugadores GROUP BY dificultad ORDER BY 2 DESC"
    ):
        print(f"  {dificultad}: {total}")
    conexion.close()


if __name__ == "__main__":
    main()
