"""
test_trivia.py
Pruebas automatizadas del juego "Trivia Rápida".
"""


def test_iniciar_trivia_practica(client):
    """Cargar /trivia en modo práctica debe responder 200."""
    respuesta = client.get("/trivia?modo=practica")
    assert respuesta.status_code == 200


def test_pregunta_no_revela_respuesta_correcta(client):
    """La respuesta correcta nunca debe aparecer en el JSON antes de responder."""
    client.get("/trivia?modo=practica")
    respuesta = client.get("/api/trivia?modo=practica")
    datos = respuesta.get_json()
    assert "correcta" not in datos
    assert "respuesta_correcta" not in datos


def test_pregunta_tiene_opciones_validas(client):
    """
    Cada pregunta debe traer 3 opciones (preguntas de resultado real,
    tipo 'quién ganó') o 4 opciones (preguntas generales fijas).
    """
    client.get("/trivia?modo=practica")
    respuesta = client.get("/api/trivia?modo=practica")
    datos = respuesta.get_json()
    assert len(datos["opciones"]) in (3, 4)


def test_responder_con_opcion_fuera_de_rango_falla(client):
    """Mandar una opción como 99 debe rechazarse, no crashear."""
    client.get("/trivia?modo=practica")
    respuesta = client.post("/api/trivia/responder", json={"opcion": 99, "modo": "practica"})
    assert respuesta.status_code == 400


def test_responder_con_opcion_como_texto_falla(client):
    """Mandar la opción como string en vez de número debe rechazarse."""
    client.get("/trivia?modo=practica")
    respuesta = client.post("/api/trivia/responder", json={"opcion": "2", "modo": "practica"})
    assert respuesta.status_code == 400


def test_partida_completa_tiene_5_preguntas(client):
    """Una partida de trivia debe constar de exactamente 5 preguntas."""
    client.get("/trivia?modo=practica")
    preguntas_respondidas = 0
    for _ in range(10):
        respuesta = client.get("/api/trivia?modo=practica")
        datos = respuesta.get_json()
        if datos.get("terminado"):
            break
        client.post("/api/trivia/responder", json={"opcion": 0, "modo": "practica"})
        preguntas_respondidas += 1

    assert preguntas_respondidas == 5


def test_trivia_diaria_es_consistente(client):
    """La trivia diaria debe elegir las mismas 5 preguntas sin importar cuántas veces se genere hoy."""
    from app import obtener_generador, PREGUNTAS_TRIVIA, PREGUNTAS_POR_PARTIDA

    def elegir(generador):
        indices = list(range(len(PREGUNTAS_TRIVIA)))
        generador.shuffle(indices)
        return indices[:PREGUNTAS_POR_PARTIDA]

    seleccion_1 = elegir(obtener_generador("diario", "trivia"))
    seleccion_2 = elegir(obtener_generador("diario", "trivia"))

    assert seleccion_1 == seleccion_2