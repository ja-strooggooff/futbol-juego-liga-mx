import pytest
from app import app as flask_app


@pytest.fixture
def client():
    """
    Esta es la pieza central de los tests: un 'cliente' que simula
    un navegador haciendo peticiones a tu servidor Flask, pero sin
    necesidad de abrir un navegador real ni correr python app.py.

    pytest detecta automáticamente esta función como un "fixture"
    (algo reutilizable). Cualquier test que reciba un parámetro
    llamado "client" la usa automáticamente.
    """
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as test_client:
        yield test_client