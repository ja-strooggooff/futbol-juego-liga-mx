import sqlite3

conexion = sqlite3.connect("futtrivia.db")
cursor = conexion.cursor()

cursor.execute("DELETE FROM partidos WHERE torneo LIKE 'mexico-txt/%' OR torneo LIKE 'argentina-txt/%'")
borrados = cursor.rowcount
conexion.commit()
conexion.close()

print(f"Se borraron {borrados} partidos con formato de fecha viejo. Listos para volver a descargar bien.")