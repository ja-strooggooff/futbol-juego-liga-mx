import sqlite3

conexion = sqlite3.connect("futtrivia.db")
cursor = conexion.cursor()

print("Creando vistas unificadas...")

# Vista que combina partidos de openfootball y transfermarkt
cursor.execute("DROP VIEW IF EXISTS todos_los_partidos")
cursor.execute("""
    CREATE VIEW todos_los_partidos AS
        SELECT
            'openfootball' AS fuente,
            torneo,
            fecha,
            equipo1,
            goles1,
            goles2,
            equipo2,
            NULL AS estadio
        FROM partidos
        UNION ALL
        SELECT
            'transfermarkt' AS fuente,
            competition_id AS torneo,
            fecha,
            club_local_nombre AS equipo1,
            goles_local AS goles1,
            goles_visitante AS goles2,
            club_visitante_nombre AS equipo2,
            estadio
        FROM games
        WHERE goles_local IS NOT NULL
        AND goles_visitante IS NOT NULL
""")
print("✓ Vista 'todos_los_partidos' creada")

# Vista de jugadores con nombre de liga legible
cursor.execute("DROP VIEW IF EXISTS jugadores_con_liga")
cursor.execute("""
    CREATE VIEW jugadores_con_liga AS
        SELECT
            j.player_id,
            j.nombre,
            j.posicion,
            j.posicion_especifica,
            j.pais,
            j.club,
            COALESCE(c.nombre, j.liga_codigo) AS liga,
            j.liga_codigo,
            j.fecha_nacimiento,
            j.valor_mercado
        FROM jugadores_reales j
        LEFT JOIN competitions c ON j.liga_codigo = c.competition_id
""")
print("✓ Vista 'jugadores_con_liga' creada (nombres de liga legibles)")

# Vista de apariciones con nombre del jugador y liga
cursor.execute("DROP VIEW IF EXISTS apariciones_detalle")
cursor.execute("""
    CREATE VIEW apariciones_detalle AS
        SELECT
            a.appearance_id,
            a.fecha,
            a.player_name AS jugador,
            a.goles,
            a.asistencias,
            a.minutos_jugados,
            a.tarjetas_amarillas,
            a.tarjetas_rojas,
            COALESCE(c.nombre, a.competition_id) AS competicion,
            a.competition_id
        FROM appearances a
        LEFT JOIN competitions c ON a.competition_id = c.competition_id
""")
print("✓ Vista 'apariciones_detalle' creada")

conexion.commit()

# Verificar que funcionan
print("\nVerificando vistas...")

total_partidos = cursor.execute("SELECT COUNT(*) FROM todos_los_partidos").fetchone()[0]
print(f"  todos_los_partidos: {total_partidos} partidos totales")

ejemplo = cursor.execute("""
    SELECT fuente, fecha, equipo1, goles1, goles2, equipo2
    FROM todos_los_partidos
    WHERE equipo1 LIKE '%Tigres%' OR equipo2 LIKE '%Tigres%'
    AND fecha LIKE '2023-05%'
    ORDER BY fecha
    LIMIT 5
""").fetchall()

print(f"\n  Ejemplo — Tigres en mayo 2023:")
for fila in ejemplo:
    fuente, fecha, eq1, g1, g2, eq2 = fila
    print(f"    [{fuente}] {fecha}: {eq1} {g1}-{g2} {eq2}")

jugadores = cursor.execute("""
    SELECT nombre, posicion, pais, club, liga
    FROM jugadores_con_liga
    WHERE pais = 'Mexico'
    LIMIT 5
""").fetchall()

print(f"\n  Ejemplo — Jugadores mexicanos:")
for j in jugadores:
    print(f"    {j[0]} | {j[1]} | {j[3]} | {j[4]}")

conexion.close()
print("\n¡Vistas creadas correctamente!")