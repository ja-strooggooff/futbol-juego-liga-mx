import sqlite3
from sistema_dificultad import (
    apariciones_seleccion_jugador,
    calcular_dificultad_jugador,
    calcular_dificultad_partido,
)

conexion = sqlite3.connect("futtrivia.db")
cursor = conexion.cursor()

print("=== DIFICULTAD DE JUGADORES FAMOSOS (v3 con apariciones_mundial) ===")
jugadores = cursor.execute("""
    SELECT j.player_id, j.nombre, j.valor_mercado,
           (SELECT COUNT(*) FROM appearances a WHERE a.player_id = j.player_id) as apariciones,
           (SELECT SUM(goles) FROM appearances a WHERE a.player_id = j.player_id) as goles
    FROM jugadores_reales j
    WHERE j.nombre IN ('Lionel Messi', 'Cristiano Ronaldo', 'Kylian Mbappé', 'Rafa Márquez', 'Guillermo Ochoa')
""").fetchall()

for player_id, nombre, valor, apariciones, goles in jugadores:
    apariciones_sel = apariciones_seleccion_jugador(nombre, conexion)
    dificultad, puntaje = calcular_dificultad_jugador(valor, apariciones or 0, goles or 0, nombre, conexion)
    print(f"  {nombre}: {dificultad} (puntaje: {puntaje}, apariciones en Mundiales: {apariciones_sel})")

print()
print("=== JUGADORES AL AZAR (para ver variedad) ===")
aleatorios = cursor.execute("""
    SELECT j.player_id, j.nombre, j.valor_mercado,
           (SELECT COUNT(*) FROM appearances a WHERE a.player_id = j.player_id) as apariciones,
           (SELECT SUM(goles) FROM appearances a WHERE a.player_id = j.player_id) as goles
    FROM jugadores_reales j
    ORDER BY RANDOM()
    LIMIT 10
""").fetchall()

for player_id, nombre, valor, apariciones, goles in aleatorios:
    dificultad, puntaje = calcular_dificultad_jugador(valor, apariciones or 0, goles or 0, nombre, conexion)
    print(f"  {nombre}: {dificultad} (puntaje: {puntaje})")

print()
print("=== DIFICULTAD DE TORNEOS ===")
torneos = [
    ("World Cup", 2022, 5000),
    ("Liga MX", 2024, 3000),
    ("World Cup", 1930, 500),
    ("Bulgarian League", 1974, 50),
]
for nombre, anio, registros in torneos:
    dificultad, puntaje = calcular_dificultad_partido(nombre, anio, registros)
    print(f"  {nombre} {anio}: {dificultad} (puntaje: {puntaje})")

conexion.close()