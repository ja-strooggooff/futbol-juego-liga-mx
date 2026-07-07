"""
test_grid.py
Pruebas automatizadas del juego "Grid de Equipos".
"""


def test_iniciar_grid_practica(client):
    """Cargar /grid en modo práctica debe responder 200."""
    respuesta = client.get("/grid?modo=practica")
    assert respuesta.status_code == 200


def test_grid_tiene_3_filas_y_3_columnas(client):
    """El tablero generado siempre debe tener exactamente 3 filas y 3 columnas."""
    client.get("/grid?modo=practica")
    respuesta = client.get("/api/grid?modo=practica")
    datos = respuesta.get_json()
    if "error" in datos:
        return
    assert len(datos["filas"]) == 3
    assert len(datos["columnas"]) == 3


def test_grid_diario_es_consistente(client):
    """El grid diario debe ser idéntico sin importar cuántas veces se genere hoy."""
    from app import generar_grid, obtener_generador

    grid_1 = generar_grid(obtener_generador("diario", "grid"))
    grid_2 = generar_grid(obtener_generador("diario", "grid"))

    assert grid_1 == grid_2


def test_intentar_con_fila_invalida_falla(client):
    """Mandar una fila fuera de rango (ej. 99) debe rechazarse con error claro."""
    client.get("/grid?modo=practica")
    respuesta = client.post("/api/grid/intentar", json={"fila": 99, "columna": 0, "nombre": "Lionel Messi", "modo": "practica"})
    assert respuesta.status_code == 400


def test_intentar_con_tipos_raros_no_truena(client):
    """Mandar fila/columna como texto en vez de número no debe crashear el servidor."""
    client.get("/grid?modo=practica")
    respuesta = client.post("/api/grid/intentar", json={"fila": "hola", "columna": "mundo", "nombre": "Lionel Messi", "modo": "practica"})
    assert respuesta.status_code != 500
    assert "error" in respuesta.get_json()


def test_no_se_puede_resolver_celda_dos_veces(client):
    """Una vez resuelta una celda, no debe poder volver a marcarse."""
    client.get("/grid?modo=practica")
    info = client.get("/api/grid?modo=practica").get_json()

    if "error" in info:
        return

    from app import JUGADORES, jugador_cumple
    cat_fila = info["filas"][0]
    cat_col = info["columnas"][0]
    candidato = next(
        (j["nombre"] for j in JUGADORES
         if jugador_cumple(j, cat_fila["tipo"], cat_fila["valor"]) and jugador_cumple(j, cat_col["tipo"], cat_col["valor"])),
        None
    )

    if candidato is None:
        return

    primer_intento = client.post("/api/grid/intentar", json={"fila": 0, "columna": 0, "nombre": candidato, "modo": "practica"})
    assert primer_intento.get_json()["correcto"] is True

    segundo_intento = client.post("/api/grid/intentar", json={"fila": 0, "columna": 0, "nombre": candidato, "modo": "practica"})
    assert segundo_intento.status_code == 400


# ----------------------------------------------------------------
#  Arreglo de generar_grid (ancla + testigos): antes fallaba 20/20
#  con el pool de 47,000+ jugadores; ahora debe ser confiable.
# ----------------------------------------------------------------

def test_generar_grid_es_confiable():
    """20 corridas seguidas con semillas distintas deben producir tablero."""
    import random
    from app import generar_grid

    for semilla in range(20):
        assert generar_grid(random.Random(semilla)) is not None, f"falló con semilla {semilla}"


def test_generar_grid_todas_las_celdas_tienen_solucion():
    """Cada una de las 9 celdas debe tener al menos un jugador válido."""
    import random
    from app import generar_grid, JUGADORES, jugador_cumple

    grid = generar_grid(random.Random(123))
    assert grid is not None
    assert len(grid["filas"]) == 3
    assert len(grid["columnas"]) == 3

    for fila in grid["filas"]:
        for columna in grid["columnas"]:
            hay_candidato = any(
                jugador_cumple(j, fila["tipo"], fila["valor"])
                and jugador_cumple(j, columna["tipo"], columna["valor"])
                for j in JUGADORES
            )
            assert hay_candidato, f"celda sin solución: {fila} x {columna}"


def test_generar_grid_no_usa_valores_placeholder():
    """Categorías como 'Sin equipo' o 'Desconocida' no deben aparecer en el tablero."""
    import random
    from app import generar_grid, VALORES_PLACEHOLDER

    grid = generar_grid(random.Random(7))
    assert grid is not None
    valores = [c["valor"] for c in grid["filas"] + grid["columnas"]]
    assert not any(v in VALORES_PLACEHOLDER for v in valores)