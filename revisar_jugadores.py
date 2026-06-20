import sqlite3

conexion = sqlite3.connect("futtrivia.db")
cursor = conexion.cursor()

total = cursor.execute("SELECT COUNT(*) FROM jugadores_reales").fetchone()[0]
print(f"Total de jugadores guardados: {total}")

print("\nEjemplos al azar:")
ejemplos = cursor.execute("SELECT nombre, posicion, pais, club FROM jugadores_reales ORDER BY RANDOM() LIMIT 5").fetchall()
for e in ejemplos:
    print(e)

conexion.close()