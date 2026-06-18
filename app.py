# ============================================================
#  app.py  —  El corazón del proyecto
#  Este archivo es el SERVIDOR. Cuando lo corres con Python,
#  levanta un sitio web al que puedes entrar desde tu navegador.
# ============================================================

# Flask es la librería que convierte Python en un servidor web.
# "render_template" sirve para mandar archivos HTML al navegador.
from flask import Flask, render_template

# Aquí creamos la "app". Es como encender el servidor.
# __name__ le dice a Flask en qué carpeta estamos trabajando.
app = Flask(__name__)


# ============================================================
#  RUTAS  —  Una ruta es una URL.
#  Cuando alguien va a "/" (la página principal), Flask ejecuta
#  la función que está justo abajo del @app.route(...)
# ============================================================

# Ruta principal: http://localhost:5000/
@app.route("/")
def index():
    # Esta lista tiene los juegos que vamos a mostrar en el home.
    # Cada juego es un "diccionario" (como un objeto con datos).
    juegos = [
        {
            "id": "wordle",
            "nombre": "Adivina el Jugador",
            "descripcion": "Tienes 8 intentos para adivinar el futbolista misterioso del día.",
            "icono": "⚽",
            "dificultad": "Fácil",
            "disponible": True,
        },
        {
            "id": "escudo",
            "nombre": "Adivina el Escudo",
            "descripcion": "El escudo aparece pixelado y se revela poco a poco. ¿Lo conoces?",
            "icono": "🛡️",
            "dificultad": "Medio",
            "disponible": False,  # Lo construiremos después
        },
        {
            "id": "trivia",
            "nombre": "Trivia Rápida",
            "descripcion": "10 preguntas sobre goles, campeones y récords del fútbol mundial.",
            "icono": "🏆",
            "dificultad": "Fácil",
            "disponible": False,
        },
        {
            "id": "conexiones",
            "nombre": "Conexiones",
            "descripcion": "Agrupa los 12 jugadores según lo que tienen en común.",
            "icono": "🔗",
            "dificultad": "Difícil",
            "disponible": False,
        },
    ]

    # render_template busca el archivo "index.html" en la carpeta /templates
    # y le manda la variable "juegos" para que HTML la pueda usar.
    return render_template("index.html", juegos=juegos)


# Ruta del juego Wordle: http://localhost:5000/wordle
@app.route("/wordle")
def wordle():
    return render_template("wordle.html")


# ============================================================
#  PUNTO DE ENTRADA
#  Este bloque solo corre cuando ejecutas: python app.py
#  debug=True significa que si cambias el código, el servidor
#  se reinicia solo. Muy útil mientras desarrollamos.
# ============================================================
if __name__ == "__main__":
    app.run(debug=True)
