import sqlite3

conexion = sqlite3.connect("futtrivia.db")
cursor = conexion.cursor()

print("=== TODAS LAS TEMPORADAS DE MÉXICO (JSON + TXT) ===")
filas = cursor.execute("""
    SELECT torneo, COUNT(*), MIN(fecha), MAX(fecha)
    FROM partidos
    WHERE torneo LIKE '%mx%'
    GROUP BY torneo
    ORDER BY torneo
""").fetchall()

for torneo, cantidad, fecha_min, fecha_max in filas:
    print(f"{torneo}")
    print(f"  Partidos: {cantidad} | Desde: {fecha_min} | Hasta: {fecha_max}")

print()
print("=== TODAS LAS TEMPORADAS DE ARGENTINA (JSON + TXT) ===")
filas2 = cursor.execute("""
    SELECT torneo, COUNT(*), MIN(fecha), MAX(fecha)
    FROM partidos
    WHERE torneo LIKE '%ar%' AND torneo LIKE '%argentina%' OR torneo LIKE '%ar1%'
    GROUP BY torneo
    ORDER BY torneo
""").fetchall()

for torneo, cantidad, fecha_min, fecha_max in filas2:
    print(f"{torneo}")
    print(f"  Partidos: {cantidad} | Desde: {fecha_min} | Hasta: {fecha_max}")

print()
total = cursor.execute("SELECT COUNT(*) FROM partidos").fetchone()[0]
print(f"TOTAL GENERAL DE PARTIDOS EN LA BASE DE DATOS: {total}")

conexion.close()