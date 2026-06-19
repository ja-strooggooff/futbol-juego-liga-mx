"""
test_escudo.py
Pruebas automatizadas del juego "Adivina el Escudo".
"""


def test_iniciar_escudo_practica(client):
    """Cargar /escudo en modo práctica debe responder 200."""
    respuesta = client.get("/escudo?modo=practica")
    assert respuesta.status_code == 200


def test_sin_intentos_no_hay_pistas(client):
    """Al inicio (0 intentos), no debe revelarse ninguna pista todavía."""
    client.get("/escudo?modo=practica")
    respuesta = client.get("/api/escudo?modo=practica")
    datos = respuesta.get_json()
    assert datos["nivel_revelado"] == 0
    assert "pais" not in datos
    assert "emoji" not in datos


def test_pistas_se_revelan_progresivamente(client):
    """Cada intento fallido debe revelar una pista nueva, en orden."""
    client.get("/escudo?modo=practica")

    r1 = client.post("/api/escudo/intentar", json={"equipo": "Equipo Falso", "modo": "practica"})
    datos_1 = r1.get_json()
    assert "pais" in datos_1
    assert "liga" not in datos_1

    r2 = client.post("/api/escudo/intentar", json={"equipo": "Equipo Falso", "modo": "practica"})
    datos_2 = r2.get_json()
    assert "liga" in datos_2


def test_equipo_secreto_oculto_hasta_terminar(client):
    """El campo equipo_secreto debe ser None mientras el juego no termine."""
    client.get("/escudo?modo=practica")
    respuesta = client.post("/api/escudo/intentar", json={"equipo": "Equipo Falso", "modo": "practica"})
    datos = respuesta.get_json()
    assert datos["equipo_secreto"] is None


def test_equipo_vacio_falla(client):
    """Mandar un equipo vacío debe rechazarse con error, no crashear."""
    client.get("/escudo?modo=practica")
    respuesta = client.post("/api/escudo/intentar", json={"equipo": "", "modo": "practica"})
    assert respuesta.status_code == 400


def test_escudo_diario_es_consistente(client):
    """El equipo secreto del día debe ser el mismo sin importar cuántas veces se elija."""
    from app import obtener_generador, ESCUDOS

    secreto_1 = obtener_generador("diario", "escudo").choice(list(ESCUDOS.keys()))
    secreto_2 = obtener_generador("diario", "escudo").choice(list(ESCUDOS.keys()))

    assert secreto_1 == secreto_2
    