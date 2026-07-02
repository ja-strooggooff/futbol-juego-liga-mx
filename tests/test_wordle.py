"""
test_wordle.py
Pruebas automatizadas del juego "Adivina el Jugador".
Cada función que empieza con "test_" es una prueba independiente.
"""


def test_iniciar_partida_practica(client):
    """Cargar /wordle en modo práctica debe responder 200 (sin errores)."""
    respuesta = client.get("/wordle?modo=practica")
    assert respuesta.status_code == 200


def test_intentar_sin_partida_activa_falla(client):
    """Mandar un intento sin haber cargado /wordle primero debe fallar con claridad."""
    respuesta = client.post("/api/intentar", json={"nombre": "Lionel Messi", "modo": "practica"})
    assert respuesta.status_code == 400
    assert "error" in respuesta.get_json()


def test_intentar_jugador_inexistente(client):
    """Si el nombre no está en la base de datos, debe responder 404."""
    client.get("/wordle?modo=practica")
    respuesta = client.post("/api/intentar", json={"nombre": "Jugador Que No Existe", "modo": "practica"})
    assert respuesta.status_code == 404


def test_intentar_sin_nombre_falla(client):
    """Mandar un intento vacío debe rechazarse con un error, no tronar."""
    client.get("/wordle?modo=practica")
    respuesta = client.post("/api/intentar", json={"nombre": "", "modo": "practica"})
    assert respuesta.status_code == 400


def test_intentar_sin_body_no_truena(client):
    """Mandar un POST sin nada de JSON no debe causar un error 500."""
    client.get("/wordle?modo=practica")
    respuesta = client.post("/api/intentar")
    assert respuesta.status_code in (400, 404)


def test_jugador_correcto_revela_secreto(client):
    """Si adivinas al jugador secreto exacto, 'gano' debe ser True."""
    client.get("/wordle?modo=practica")

    from app import JUGADORES

    # Leemos el nombre del secreto directamente de la sesión activa,
    # sin necesidad de agotar intentos ni reiniciar.
    with client.session_transaction() as sess:
        nombre_secreto = sess.get("wordle_practica_secreto")

    assert nombre_secreto is not None, "No se encontró un secreto activo en la sesión"

    respuesta = client.post("/api/intentar", json={"nombre": nombre_secreto, "modo": "practica"})
    datos = respuesta.get_json()
    assert datos.get("gano") is True
    assert datos.get("terminado") is True




def test_no_se_puede_jugar_despues_de_terminar(client):
    """Una vez que el juego termina, no debe aceptar más intentos."""
    client.get("/wordle?modo=practica")
    client.post("/api/wordle/reiniciar", json={"modo": "practica"})
    from app import JUGADORES
    nombre_cualquiera = JUGADORES[0]["nombre"]
    for _ in range(8):
        respuesta = client.post("/api/intentar", json={"nombre": nombre_cualquiera, "modo": "practica"})
        if respuesta.get_json().get("terminado"):
            break
    respuesta_extra = client.post("/api/intentar", json={"nombre": nombre_cualquiera, "modo": "practica"})
    assert respuesta_extra.status_code == 400


def test_reto_diario_es_consistente(client):
    """El reto diario debe darle el MISMO jugador secreto a cualquiera que juegue hoy."""
    from app import obtener_generador, JUGADORES
    secreto_1 = obtener_generador("diario", "wordle").choice(JUGADORES)["nombre"]
    secreto_2 = obtener_generador("diario", "wordle").choice(JUGADORES)["nombre"]
    assert secreto_1 == secreto_2


def test_reto_diario_no_se_puede_reiniciar(client):
    """El modo diario debe rechazar la petición de reinicio."""
    client.get("/wordle?modo=diario")
    respuesta = client.post("/api/wordle/reiniciar", json={"modo": "diario"})
    assert respuesta.status_code == 400


def test_modo_practica_si_se_puede_reiniciar(client):
    """El modo práctica sí debe poder reiniciarse libremente."""
    client.get("/wordle?modo=practica")
    respuesta = client.post("/api/wordle/reiniciar", json={"modo": "practica"})
    assert respuesta.status_code == 200
    assert respuesta.get_json()["ok"] is True


def test_pista_revela_un_atributo_y_consume_intento(client):
    """Pedir una pista debe devolver un atributo y aumentar el contador de intentos."""
    client.get("/wordle?modo=practica")
    respuesta = client.post("/api/wordle/pista", json={"modo": "practica"})
    datos = respuesta.get_json()
    assert respuesta.status_code == 200
    assert "atributo" in datos
    assert "valor" in datos
    assert datos["intentos_usados"] == 1


def test_pistas_no_se_repiten(client):
    """Pedir varias pistas seguidas no debe repetir el mismo atributo dos veces."""
    client.get("/wordle?modo=practica")
    atributos_recibidos = []
    for _ in range(3):
        respuesta = client.post("/api/wordle/pista", json={"modo": "practica"})
        atributos_recibidos.append(respuesta.get_json()["atributo"])
    assert len(atributos_recibidos) == len(set(atributos_recibidos)), "Se repitió un atributo de pista"


def test_inputs_raros_no_tumban_el_servidor(client):
    """Mandar datos basura nunca debe causar un error 500 (crash del servidor)."""
    client.get("/wordle?modo=practica")
    casos_raros = [
        {"nombre": 12345, "modo": "practica"},
        {"nombre": ["a", "b"], "modo": "practica"},
        {"modo": "practica"},
        {},
    ]
    for caso in casos_raros:
        respuesta = client.post("/api/intentar", json=caso)
        assert respuesta.status_code != 500, f"El servidor crasheó con: {caso}"