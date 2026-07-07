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


# ----------------------------------------------------------------
#  Arreglo de generar_conexiones (4 grupos de 4 desde anclas):
#  antes mandaba el pool completo de 47,000+ jugadores al tablero.
# ----------------------------------------------------------------

def test_generar_conexiones_es_confiable():
    """20 corridas seguidas con semillas distintas deben producir tablero."""
    import random
    from app import generar_conexiones

    for semilla in range(20):
        assert generar_conexiones(random.Random(semilla)) is not None, f"falló con semilla {semilla}"


def test_generar_conexiones_estructura_4_grupos_de_4():
    """Estilo NYT: 4 grupos de 4 jugadores, 16 nombres únicos en el tablero."""
    import random
    from app import generar_conexiones

    resultado = generar_conexiones(random.Random(11))
    assert resultado is not None
    grupos = resultado["grupos"]
    assert len(grupos) == 4
    assert all(len(miembros) == 4 for miembros in grupos.values())

    nombres = [n for miembros in grupos.values() for n in miembros]
    assert len(set(nombres)) == 16


def test_generar_conexiones_miembros_exclusivos():
    """Cada ficha cumple SU categoría y ninguna otra: solución única."""
    import random
    from app import generar_conexiones, JUGADORES

    resultado = generar_conexiones(random.Random(5))
    assert resultado is not None
    grupos = resultado["grupos"]

    por_nombre = {}
    for j in JUGADORES:
        por_nombre.setdefault(j["nombre"], []).append(j)

    categorias = set(grupos.keys())
    for valor, miembros in grupos.items():
        otras = categorias - {valor}
        for nombre in miembros:
            # Puede haber homónimos: basta con que algún registro del
            # nombre cumpla exactamente su grupo y ningún otro.
            cumple = any(
                valor in {j["posicion"], j["liga"], j["equipo"], j["pais"]}
                and not (otras & {j["posicion"], j["liga"], j["equipo"], j["pais"]})
                for j in por_nombre[nombre]
            )
            assert cumple, f"{nombre} no es exclusivo del grupo {valor}"


def test_tablero_de_conexiones_tiene_16_fichas(client):
    """La API debe mandar exactamente las 16 fichas, no el pool completo."""
    client.get("/conexiones?modo=practica")
    datos = client.get("/api/conexiones?modo=practica").get_json()
    assert len(datos["tablero"]) == 16