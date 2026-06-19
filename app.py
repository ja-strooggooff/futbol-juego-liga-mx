# ================================================================
#  app.py — El servidor de FutTrivia
#
#  Persona 2 (Backend): aquí vive toda la lógica del juego.
#  El navegador NUNCA sabe quién es el jugador secreto hasta
#  que el juego termina. Eso lo decide y lo guarda Python.
# ================================================================

import random
from flask import Flask, render_template, jsonify, request, session

app = Flask(__name__)

# secret_key es necesario para que Flask pueda usar "session".
# La sesión es una cookie segura donde cada usuario guarda SU
# propia partida, sin que se mezcle con la de otros usuarios.
# En producción esto debe venir de una variable de entorno,
# por ahora lo dejamos fijo para desarrollo.
app.secret_key = "cambia-esto-luego-con-env-var"


# ================================================================
#  BASE DE DATOS TEMPORAL DE JUGADORES
#  (la migraremos a SQLite más adelante)
# ================================================================
JUGADORES = [
    {"nombre": "Lionel Messi", "posicion": "Delantero", "liga": "MLS", "equipo": "Inter Miami", "pais": "Argentina", "edad": 37, "dorsal": 10},
    {"nombre": "Cristiano Ronaldo", "posicion": "Delantero", "liga": "Saudi Pro League", "equipo": "Al Nassr", "pais": "Portugal", "edad": 39, "dorsal": 7},
    {"nombre": "Kylian Mbappé", "posicion": "Delantero", "liga": "La Liga", "equipo": "Real Madrid", "pais": "Francia", "edad": 25, "dorsal": 9},
    {"nombre": "Erling Haaland", "posicion": "Delantero", "liga": "Premier League", "equipo": "Manchester City", "pais": "Noruega", "edad": 23, "dorsal": 9},
    {"nombre": "Vinícius Jr.", "posicion": "Extremo", "liga": "La Liga", "equipo": "Real Madrid", "pais": "Brasil", "edad": 23, "dorsal": 7},
    {"nombre": "Pedri", "posicion": "Mediocampista", "liga": "La Liga", "equipo": "Barcelona", "pais": "España", "edad": 22, "dorsal": 8},
    {"nombre": "Lamine Yamal", "posicion": "Extremo", "liga": "La Liga", "equipo": "Barcelona", "pais": "España", "edad": 17, "dorsal": 19},
    {"nombre": "Jude Bellingham", "posicion": "Mediocampista", "liga": "La Liga", "equipo": "Real Madrid", "pais": "Inglaterra", "edad": 21, "dorsal": 5},
]


# ================================================================
#  LÓGICA DEL JUEGO
# ================================================================

def iniciar_nueva_partida():
    """
    Elige un jugador secreto al azar y resetea el contador de intentos.
    Por ahora es al azar; cuando hagamos el "reto diario" esta función
    cambiará para elegir siempre el mismo jugador en el mismo día.
    """
    jugador_secreto = random.choice(JUGADORES)
    session["secreto"] = jugador_secreto["nombre"]
    session["intentos"] = 0
    session["terminado"] = False


# ================================================================
#  RUTAS DE PÁGINAS (HTML)
# ================================================================

@app.route("/")
def index():
    juegos = [
        {"id": "wordle", "nombre": "Adivina el Jugador", "descripcion": "Tienes 8 intentos para adivinar el futbolista del día.", "icono": "⚽", "dificultad": "Fácil", "disponible": True},
        {"id": "escudo", "nombre": "Adivina el Escudo", "descripcion": "El escudo aparece pixelado. ¿Lo reconoces?", "icono": "🛡️", "dificultad": "Medio", "disponible": False},
        {"id": "trivia", "nombre": "Trivia Rápida", "descripcion": "10 preguntas de goles, campeones y récords.", "icono": "🏆", "dificultad": "Fácil", "disponible": False},
        {"id": "conexiones", "nombre": "Conexiones", "descripcion": "Agrupa los jugadores según lo que tienen en común.", "icono": "🔗", "dificultad": "Difícil", "disponible": False},
    ]
    return render_template("index.html", juegos=juegos)


@app.route("/wordle")
def wordle():
    # Si el usuario no tiene partida activa, le iniciamos una.
    # "secreto" not in session significa "este usuario nunca ha jugado
    # o ya terminó su última partida sin reiniciar".
    if "secreto" not in session:
        iniciar_nueva_partida()
    return render_template("wordle.html")


# ================================================================
#  RUTAS DE API (JSON) — Las usa JavaScript
# ================================================================

@app.route("/api/jugadores")
def lista_jugadores():
    """Devuelve solo los nombres, para el autocomplete del input."""
    nombres = [j["nombre"] for j in JUGADORES]
    return jsonify(nombres)


@app.route("/api/intentar", methods=["POST"])
def intentar():
    """
    Esta es la ruta más importante del juego.
    Recibe el nombre que el usuario intentó adivinar, lo compara
    contra el secreto guardado en SU sesión, y devuelve el
    resultado atributo por atributo (correcto / incorrecto / pista).

    El jugador secreto JAMÁS se manda al frontend hasta que
    el juego termina (ganó o se acabaron los intentos).
    """
    if "secreto" not in session:
        return jsonify({"error": "No hay partida activa. Recarga la página."}), 400

    if session.get("terminado"):
        return jsonify({"error": "El juego ya terminó."}), 400

    # request.get_json() lee el JSON que mandó JavaScript con fetch()
    data = request.get_json()
    nombre_intento = (data.get("nombre") or "").strip().lower()

    # Buscar el jugador que el usuario escribió
    jugador = next(
        (j for j in JUGADORES if j["nombre"].lower() == nombre_intento),
        None
    )
    if jugador is None:
        return jsonify({"error": "Jugador no encontrado"}), 404

    # Buscar el jugador secreto usando el nombre guardado en sesión
    secreto = next(j for j in JUGADORES if j["nombre"] == session["secreto"])

    # Comparar atributos de texto (posición, liga, equipo, país)
    resultado = {}
    for attr in ["posicion", "liga", "equipo", "pais"]:
        valor = jugador[attr]
        resultado[attr] = {
            "valor": valor,
            "estado": "correcto" if valor == secreto[attr] else "incorrecto",
        }

    # Comparar atributos numéricos (edad, dorsal) — estos llevan pista de dirección
    for attr in ["edad", "dorsal"]:
        valor = jugador[attr]
        if valor == secreto[attr]:
            resultado[attr] = {"valor": valor, "estado": "correcto"}
        else:
            resultado[attr] = {
                "valor": valor,
                "estado": "incorrecto",
                "pista": "subir" if valor < secreto[attr] else "bajar",
            }

    # Actualizar el estado de la partida en la sesión
    session["intentos"] += 1
    gano = jugador["nombre"] == secreto["nombre"]

    if gano or session["intentos"] >= 8:
        session["terminado"] = True

    return jsonify({
        "nombre": jugador["nombre"],
        "atributos": resultado,
        "gano": gano,
        "intentos": session["intentos"],
        "intentos_restantes": 8 - session["intentos"],
        "terminado": session["terminado"],
        # Solo revelamos el nombre del secreto cuando el juego termina
        "secreto": secreto["nombre"] if session["terminado"] else None,
    })


@app.route("/api/reiniciar", methods=["POST"])
def reiniciar():
    """
    Empieza una partida nueva manualmente.
    Esto es temporal para que puedan probar — cuando hagamos el
    reto diario, el jugador secreto cambiará solo a la medianoche
    y esta ruta ya no hará falta.
    """
    iniciar_nueva_partida()
    return jsonify({"ok": True})

# ================================================================
#  JUEGO: GRID DE EQUIPOS
#
#  Es un tablero de 3x3. Cada fila y columna representa una
#  categoría (ej. "juega en La Liga", "es de España"). El usuario
#  tiene que escribir un jugador que cumpla AMBAS condiciones
#  de la celda donde está parado. Un jugador solo se puede usar
#  una vez en todo el tablero.
# ================================================================

def construir_categorias():
    """
    Recorre todos los jugadores y agrupa sus atributos en categorías.
    Por ejemplo, la categoría ("pais", "España") va a tener la lista
    de nombres de todos los jugadores españoles.
    """
    categorias = {}
    for jugador in JUGADORES:
        for tipo in ["posicion", "liga", "equipo", "pais"]:
            valor = jugador[tipo]
            clave = (tipo, valor)
            categorias.setdefault(clave, []).append(jugador["nombre"])
    return categorias


def generar_grid(max_intentos=500):
    """
    Elige 3 categorías para las filas y 3 para las columnas,
    asegurándose de que CADA una de las 9 celdas tenga al menos
    un jugador real que la pueda resolver.
    """
    categorias_dict = construir_categorias()

    # Solo usamos categorías con 2+ jugadores; con 1 solo jugador
    # casi nunca cruza bien con otra categoría.
    categorias_utiles = [c for c in categorias_dict.items() if len(c[1]) >= 2]

    if len(categorias_utiles) < 6:
        return None  # Necesitamos más jugadores en la base de datos

    for _ in range(max_intentos):
        random.shuffle(categorias_utiles)
        filas = categorias_utiles[:3]
        columnas = categorias_utiles[3:6]

        # Verificar que TODAS las combinaciones fila x columna tengan
        # al menos un jugador en común
        valido = all(
            set(jf) & set(jc)
            for (_, jf) in filas
            for (_, jc) in columnas
        )
        if valido:
            return {
                "filas": [{"tipo": k[0], "valor": k[1]} for k, _ in filas],
                "columnas": [{"tipo": k[0], "valor": k[1]} for k, _ in columnas],
            }

    return None


def jugador_cumple(jugador, tipo, valor):
    """Revisa si un jugador cumple con una categoría específica."""
    return jugador[tipo] == valor


def iniciar_nuevo_grid():
    """Genera un grid nuevo y resetea el progreso del usuario."""
    grid = generar_grid()
    session["grid"] = grid
    session["grid_usados"] = []      # nombres de jugadores ya usados
    session["grid_resueltas"] = {}   # celdas ya resueltas: {"0-0": "Messi", ...}


@app.route("/grid")
def grid_page():
    if "grid" not in session or session["grid"] is None:
        iniciar_nuevo_grid()
    return render_template("grid.html")


@app.route("/api/grid")
def grid_info():
    """Devuelve las categorías de las filas y columnas para dibujar el tablero."""
    if "grid" not in session or session["grid"] is None:
        return jsonify({"error": "No hay grid activo"}), 400

    return jsonify({
        "filas": session["grid"]["filas"],
        "columnas": session["grid"]["columnas"],
        "resueltas": session["grid_resueltas"],
    })


@app.route("/api/grid/intentar", methods=["POST"])
def grid_intentar():
    """
    Recibe en qué celda (fila, columna) está jugando el usuario
    y qué jugador escribió. Revisa si ese jugador cumple AMBAS
    categorías de esa celda y que no se haya usado antes.
    """
    if "grid" not in session or session["grid"] is None:
        return jsonify({"error": "No hay grid activo"}), 400

    data = request.get_json()
    fila = data.get("fila")
    columna = data.get("columna")
    nombre_intento = (data.get("nombre") or "").strip().lower()

    if fila is None or columna is None:
        return jsonify({"error": "Faltan fila/columna"}), 400

    celda_key = f"{fila}-{columna}"

    if session["grid_resueltas"].get(celda_key):
        return jsonify({"error": "Esta celda ya está resuelta"}), 400

    if nombre_intento in [n.lower() for n in session["grid_usados"]]:
        return jsonify({"error": "Ese jugador ya fue usado en este tablero"}), 400

    jugador = next((j for j in JUGADORES if j["nombre"].lower() == nombre_intento), None)
    if jugador is None:
        return jsonify({"error": "Jugador no encontrado"}), 404

    cat_fila = session["grid"]["filas"][fila]
    cat_col = session["grid"]["columnas"][columna]

    correcto = (
        jugador_cumple(jugador, cat_fila["tipo"], cat_fila["valor"])
        and jugador_cumple(jugador, cat_col["tipo"], cat_col["valor"])
    )

    if correcto:
        session["grid_resueltas"][celda_key] = jugador["nombre"]
        session["grid_usados"] = session["grid_usados"] + [jugador["nombre"]]
        # session.modified = True le avisa a Flask que cambiamos algo
        # dentro de la sesión (listas/diccionarios anidados no se detectan solos)
        session.modified = True

    total_resueltas = len(session["grid_resueltas"])

    return jsonify({
        "correcto": correcto,
        "nombre": jugador["nombre"],
        "resueltas": total_resueltas,
        "completo": total_resueltas == 9,
    })


@app.route("/api/grid/reiniciar", methods=["POST"])
def grid_reiniciar():
    iniciar_nuevo_grid()
    return jsonify({"ok": True})



# ================================================================
#  PUNTO DE ENTRADA
# ================================================================
if __name__ == "__main__":
    app.run(debug=True)