import sqlite3

conexion = sqlite3.connect("futtrivia.db")
cursor = conexion.cursor()

total = cursor.execute("SELECT COUNT(*) FROM jugadores_reales").fetchone()[0]
print(f"Total en jugadores_reales: {total}")

sin_nombre = cursor.execute("SELECT COUNT(*) FROM jugadores_reales WHERE nombre IS NULL OR nombre = ''").fetchone()[0]
print(f"Sin nombre: {sin_nombre}")

sin_posicion = cursor.execute("SELECT COUNT(*) FROM jugadores_reales WHERE posicion IS NULL OR posicion = ''").fetchone()[0]
print(f"Sin posición: {sin_posicion}")

sin_pais = cursor.execute("SELECT COUNT(*) FROM jugadores_reales WHERE pais IS NULL OR pais = ''").fetchone()[0]
print(f"Sin país: {sin_pais}")

sin_club = cursor.execute("SELECT COUNT(*) FROM jugadores_reales WHERE club IS NULL OR club = ''").fetchone()[0]
print(f"Sin club: {sin_club}")

sin_valor = cursor.execute("SELECT COUNT(*) FROM jugadores_reales WHERE valor_mercado IS NULL OR valor_mercado <= 0").fetchone()[0]
print(f"Sin valor de mercado: {sin_valor}")

sin_fecha = cursor.execute("SELECT COUNT(*) FROM jugadores_reales WHERE fecha_nacimiento IS NULL OR fecha_nacimiento = ''").fetchone()[0]
print(f"Sin fecha de nacimiento: {sin_fecha}")

print()
print("=== Ejemplos de jugadores sin valor de mercado ===")
ejemplos = cursor.execute("""
    SELECT nombre, pais, club, fecha_nacimiento
    FROM jugadores_reales
    WHERE valor_mercado IS NULL OR valor_mercado <= 0
    LIMIT 10
""").fetchall()
for e in ejemplos:
    print(e)

print()
print("=== ¿Tienen valuaciones en player_valuations? ===")
resultado = cursor.execute("""
    SELECT j.nombre, COUNT(pv.id) as num_valuaciones
    FROM jugadores_reales j
    LEFT JOIN player_valuations pv ON j.player_id = pv.player_id
    WHERE j.valor_mercado IS NULL OR j.valor_mercado <= 0
    GROUP BY j.player_id
    LIMIT 10
""").fetchall()
for r in resultado:
    print(r)


conexion.close()