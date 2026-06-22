import sqlite3
import unicodedata

DB_PATH = "futtrivia.db"


def normalizar(texto):
    """
    Quita acentos y convierte a minúsculas.
    Así 'Atletico' encuentra 'Atlético', 'Munchen' encuentra 'München', etc.
    """
    if not texto:
        return ""
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return texto


def conectar():
    conexion = sqlite3.connect(DB_PATH)
    # Registramos la función de normalización para poder usarla en SQL
    conexion.create_function("norm", 1, normalizar)
    return conexion


def buscar_jugador(cursor, termino):
    return cursor.execute("""
        SELECT nombre, posicion, posicion_especifica, pais, club, liga_codigo
        FROM jugadores_reales
        WHERE norm(nombre) LIKE norm(?)
        LIMIT 10
    """, (f"%{termino}%",)).fetchall()


def buscar_partido(cursor, termino):
    return cursor.execute("""
        SELECT fuente, fecha, equipo1, goles1, goles2, equipo2
        FROM todos_los_partidos
        WHERE norm(equipo1) LIKE norm(?) OR norm(equipo2) LIKE norm(?)
        ORDER BY fecha DESC
        LIMIT 15
    """, (f"%{termino}%", f"%{termino}%")).fetchall()


def buscar_club(cursor, termino):
    return cursor.execute("""
        SELECT nombre, liga_codigo, estadio, capacidad_estadio, ultima_temporada
        FROM clubs
        WHERE norm(nombre) LIKE norm(?)
        LIMIT 10
    """, (f"%{termino}%",)).fetchall()


def buscar_alineacion(cursor, termino_equipo, temporada):
    return cursor.execute("""
        SELECT gl.fecha, gl.player_name, gl.posicion, gl.tipo, gl.capitan
        FROM game_lineups gl
        JOIN games g ON gl.game_id = g.game_id
        WHERE (norm(g.club_local_nombre) LIKE norm(?)
            OR norm(g.club_visitante_nombre) LIKE norm(?))
        AND g.temporada = ?
        AND gl.tipo = 'starting_lineup'
        ORDER BY gl.fecha DESC
        LIMIT 30
    """, (f"%{termino_equipo}%", f"%{termino_equipo}%", int(temporada))).fetchall()


def buscar_goles_jugador(cursor, termino):
    return cursor.execute("""
        SELECT player_name, COUNT(*) as total_goles,
               MIN(fecha) as primer_gol, MAX(fecha) as ultimo_gol
        FROM appearances
        WHERE norm(player_name) LIKE norm(?) AND goles > 0
        GROUP BY player_name
        ORDER BY total_goles DESC
        LIMIT 10
    """, (f"%{termino}%",)).fetchall()


def mostrar_menu():
    print("\n" + "="*50)
    print("   🔍 BUSCADOR UNIVERSAL - FutTrivia DB")
    print("="*50)
    print("1. Buscar jugador")
    print("2. Buscar partidos de un equipo")
    print("3. Buscar club")
    print("4. Ver alineación de un equipo (por temporada)")
    print("5. Goles históricos de un jugador")
    print("0. Salir")
    print("="*50)
    print("💡 No necesitas acentos: 'Atletico' encuentra 'Atlético'")


def main():
    conexion = conectar()
    cursor = conexion.cursor()

    while True:
        mostrar_menu()
        opcion = input("Elige una opción: ").strip()

        if opcion == "0":
            print("Cerrando buscador.")
            break

        elif opcion == "1":
            termino = input("Nombre del jugador: ").strip()
            resultados = buscar_jugador(cursor, termino)
            if not resultados:
                print(f"  ❌ No se encontró ningún jugador con '{termino}'")
            else:
                print(f"\n  ✅ {len(resultados)} resultado(s):")
                for r in resultados:
                    nombre, pos, pos_esp, pais, club, liga = r
                    print(f"  → {nombre} | {pos_esp or pos} | {pais} | {club} | {liga}")

        elif opcion == "2":
            termino = input("Nombre del equipo: ").strip()
            resultados = buscar_partido(cursor, termino)
            if not resultados:
                print(f"  ❌ No se encontraron partidos de '{termino}'")
            else:
                print(f"\n  ✅ Últimos {len(resultados)} partidos:")
                for r in resultados:
                    fuente, fecha, eq1, g1, g2, eq2 = r
                    print(f"  [{fuente}] {fecha}: {eq1} {g1}-{g2} {eq2}")

        elif opcion == "3":
            termino = input("Nombre del club: ").strip()
            resultados = buscar_club(cursor, termino)
            if not resultados:
                print(f"  ❌ No se encontró ningún club con '{termino}'")
            else:
                print(f"\n  ✅ {len(resultados)} resultado(s):")
                for r in resultados:
                    nombre, liga, estadio, capacidad, temporada = r
                    print(f"  → {nombre} | {liga} | {estadio} ({capacidad} asientos) | Última temp: {temporada}")

        elif opcion == "4":
            equipo = input("Nombre del equipo: ").strip()
            temporada = input("Temporada (año, ej: 2023): ").strip()
            resultados = buscar_alineacion(cursor, equipo, temporada)
            if not resultados:
                print(f"  ❌ No se encontró alineación de '{equipo}' en {temporada}")
                print(f"  💡 Recuerda que alineaciones vienen de transfermarkt — puede que el equipo no esté cubierto")
            else:
                print(f"\n  ✅ Titulares encontrados:")
                vistos = set()
                for r in resultados:
                    fecha, nombre, posicion, tipo, capitan = r
                    if nombre not in vistos:
                        cap = " (C)" if capitan else ""
                        print(f"  → {nombre} | {posicion}{cap} | {fecha}")
                        vistos.add(nombre)

        elif opcion == "5":
            termino = input("Nombre del jugador: ").strip()
            resultados = buscar_goles_jugador(cursor, termino)
            if not resultados:
                print(f"  ❌ No se encontraron goles de '{termino}'")
            else:
                print(f"\n  ✅ {len(resultados)} resultado(s):")
                for r in resultados:
                    nombre, goles, primero, ultimo = r
                    print(f"  → {nombre}: {goles} goles | {primero} → {ultimo}")

        else:
            print("  Opción no válida, elige entre 0 y 5.")

    conexion.close()


if __name__ == "__main__":
    main()