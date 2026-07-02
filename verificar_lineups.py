import sqlite3

conexion = sqlite3.connect("futtrivia.db")
cursor = conexion.cursor()

print("=== Equipos mexicanos en game_lineups ===")
resultado = cursor.execute("""
    SELECT DISTINCT gl.player_name, gl.posicion, gl.fecha, c.nombre
    FROM game_lineups gl
    JOIN games g ON gl.game_id = g.game_id
    JOIN competitions c ON g.competition_id = c.competition_id
    WHERE c.competition_id LIKE '%MEX%' OR c.competition_id LIKE '%MX%'
    LIMIT 20
""").fetchall()

for r in resultado:
    print(r)

print()
print("=== Clubes mexicanos en clubs ===")
clubes = cursor.execute("""
    SELECT club_id, nombre, liga_codigo FROM clubs
    WHERE liga_codigo LIKE '%MEX%' OR liga_codigo LIKE '%MX%'
    OR nombre LIKE '%Tigres%'
""").fetchall()

for c in clubes:
    print(c)

conexion.close()