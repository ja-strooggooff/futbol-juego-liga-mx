import sqlite3
from sistema_dificultad import calcular_dificultad_jugador, calcular_dificultad_partido


def contar_apariciones_seleccion(cursor, player_id):
    """Cuenta cuántas veces un jugador jugó en torneos de selección nacional."""
    resultado = cursor.execute("""
        SELECT COUNT(*) FROM appearances a
        JOIN competitions c ON a.competition_id = c.competition_id
        WHERE a.player_id = ? AND c.tipo = 'national_team_competition'
    """, (player_id,)).fetchone()
    return resultado[0] if resultado else 0


conexion = sqlite3.connect("futtrivia.db")
cursor = conexion.cursor()

print("=== DIFICULTAD DE JUGADORES FAMOSOS (v2 con selección nacional) ===")
jugadores = cursor.execute("""
    SELECT j.player_id, j.nombre, j.valor_mercado,
           (SELECT COUNT(*) FROM appearances a WHERE a.player_id = j.player_id) as apariciones,
           (SELECT SUM(goles) FROM appearances a WHERE a.player_id = j.player_id) as goles
    FROM jugadores_reales j
    WHERE j.nombre IN ('Lionel Messi', 'Cristiano Ronaldo', 'Kylian Mbappé', 'Rafa Márquez', 'Guillermo Ochoa')
""").fetchall()

for player_id, nombre, valor, apariciones, goles in jugadores:
    apariciones_sel = contar_apariciones_seleccion(cursor, player_id)
    dificultad, puntaje = calcular_dificultad_jugador(valor, apariciones or 0, goles or 0, apariciones_sel)
    print(f"  {nombre}: {dificultad} (puntaje: {puntaje}, apariciones selección: {apariciones_sel})")

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
    apariciones_sel = contar_apariciones_seleccion(cursor, player_id)
    dificultad, puntaje = calcular_dificultad_jugador(valor, apariciones or 0, goles or 0, apariciones_sel)
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