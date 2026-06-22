import sqlite3

conexion = sqlite3.connect("futtrivia.db")
cursor = conexion.cursor()

# Buscar todos los partidos entre Tigres y Guadalajara en 2023
resultado = cursor.execute("""
    SELECT torneo, fecha, equipo1, goles1, goles2, equipo2
    FROM partidos
    WHERE (
        (equipo1 LIKE '%Tigres%' AND equipo2 LIKE '%Guadalajara%')
        OR
        (equipo1 LIKE '%Guadalajara%' AND equipo2 LIKE '%Tigres%')
    )
    AND fecha LIKE '2023%'
    ORDER BY fecha
""").fetchall()

for fila in resultado:
    torneo, fecha, eq1, g1, g2, eq2 = fila
    print(f"{fecha}: {eq1} {g1}-{g2} {eq2}")

conexion.close()