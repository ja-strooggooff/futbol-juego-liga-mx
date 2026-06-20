import sqlite3

conexion = sqlite3.connect("futtrivia.db")
filas = conexion.execute("""
    SELECT torneo, COUNT(*) FROM partidos
    WHERE torneo LIKE '%mx.1%' OR torneo LIKE '%ar.1%'
    GROUP BY torneo
    ORDER BY torneo
""").fetchall()

for torneo, cantidad in filas:
    print(f"{torneo}: {cantidad} partidos")

conexion.close()