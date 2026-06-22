import sqlite3
c = sqlite3.connect("futtrivia.db")
r = c.execute("""
    SELECT fuente, fecha, equipo1, goles1, goles2, equipo2
    FROM todos_los_partidos
    WHERE (equipo1 LIKE '%Tigres%' OR equipo2 LIKE '%Tigres%')
    AND fecha LIKE '2023-05%'
    ORDER BY fecha
""").fetchall()
for f in r: print(f)
c.close()