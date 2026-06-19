"""
test_conexiones.py
Pruebas automatizadas del juego "Conexiones".
"""


def test_iniciar_conexiones_practica(client):
    """Cargar /conexiones en modo práctica debe responder 200."""
    respuesta = client.get("/conexiones?modo=practica")
    assert respuesta.status_code == 200


def test_tablero_no_esta_vacio(client):
    """El tablero inicial debe tener al menos 4 jugadores para agrupar."""
    client.get("/conexiones?modo=practica")
    respuesta = client.get("/api/conexiones?modo=practica")
    datos = respuesta.get_json()
    assert len(datos["tablero"]) >= 4


def test_conexiones_diario_es_consistente(client):
    """Las conexiones del día deben ser idénticas sin importar cuántas veces se generen hoy."""
    from app import generar_conexiones, obtener_generador

    resultado_1 = generar_conexiones(obtener_generador("diario", "conexiones"))
    resultado_2 = generar_conexiones(obtener_generador("diario", "conexiones"))

    assert resultado_1 == resultado_2


def test_seleccion_incorrecta_cuenta_como_error(client):
    """Mandar una selección de jugadores que no forma un grupo válido debe sumar un error."""
    client.get("/conexiones?modo=practica")
    info = client.get("/api/conexiones?modo=practica").get_json()
    tablero = info["tablero"]

    seleccion_invalida = tablero[:2] if len(tablero) >= 2 else tablero
    respuesta = client.post("/api/conexiones/intentar", json={"jugadores": seleccion_invalida, "modo": "practica"})
    datos = respuesta.get_json()

    if not datos["correcto"]:
        assert datos["errores"] == 1


def test_seleccion_no_es_lista_no_truena(client):
    """Mandar 'jugadores' como texto en vez de lista no debe crashear el servidor."""
    client.get("/conexiones?modo=practica")
    respuesta = client.post("/api/conexiones/intentar", json={"jugadores": "esto no es una lista", "modo": "practica"})
    assert respuesta.status_code != 500


def test_no_se_puede_jugar_conexiones_diarias_dos_veces(client):
    """Las conexiones diarias no deben poder reiniciarse."""
    client.get("/conexiones?modo=diario")
    respuesta = client.post("/api/conexiones/reiniciar", json={"modo": "diario"})
    assert respuesta.status_code == 400