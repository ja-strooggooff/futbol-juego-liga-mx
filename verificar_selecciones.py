import sqlite3
conexion = sqlite3.connect("futtrivia.db")
resultado = conexion.execute("""
    SELECT competition_id, nombre, tipo FROM competitions WHERE tipo = 'national_team_competition'
""").fetchall()
for r in resultado:
    print(r)

print()
print("=== Todos los tipos distintos que existen ===")
tipos = conexion.execute("SELECT DISTINCT tipo FROM competitions").fetchall()
for t in tipos:
    print(t)
conexion.close()