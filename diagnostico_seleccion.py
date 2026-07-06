import sqlite3
conexion = sqlite3.connect("futtrivia.db")
cursor = conexion.cursor()

resultado = cursor.execute("""
    SELECT COUNT(*) FROM games
    WHERE tipo_competicion = 'national_team_competition'
""").fetchone()
print(f"Partidos de selección en tabla games: {resultado[0]}")

# Ver si hay lineups de esos partidos
resultado2 = cursor.execute("""
    SELECT COUNT(*) FROM game_lineups gl
    JOIN games g ON gl.game_id = g.game_id
    WHERE g.tipo_competicion = 'national_team_competition'
    AND gl.player_name = 'Lionel Messi'
""").fetchone()
print(f"Alineaciones de Messi en partidos de selección: {resultado2[0]}")

conexion.close()