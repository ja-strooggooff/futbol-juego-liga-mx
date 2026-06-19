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
#  VALIDACIÓN DE ENTRADAS (INPUTS)
#
#  Nunca hay que confiar en lo que manda el navegador. Alguien
#  puede mandar datos vacíos, del tipo equivocado, fuera de rango,
#  o directamente basura (a propósito o por error). Estas funciones
#  limpian y validan todo antes de usarlo.
# ================================================================

def obtener_json_seguro():
    """
    Lee el JSON del request de forma segura.
    Si no hay JSON, está mal formado, o no es un objeto {},
    devuelve un diccionario vacío en vez de tronar el servidor.
    """
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def limpiar_texto(valor, max_largo=80):
    """
    Limpia un texto que viene del usuario:
    - Si no es texto, devuelve vacío
    - Quita espacios al inicio/final
    - Lo recorta si es absurdamente largo
    """
    if not isinstance(valor, str):
        return ""
    return valor.strip()[:max_largo]


def es_entero_en_rango(valor, minimo, maximo):
    """
    Revisa que 'valor' sea un número entero dentro de un rango.
    Ojo: en Python, True/False cuentan como 1/0 — por eso
    descartamos explícitamente los booleanos.
    """
    return isinstance(valor, int) and not isinstance(valor, bool) and minimo <= valor <= maximo


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
    data = obtener_json_seguro()
    nombre_intento = limpiar_texto(data.get("nombre", "")).lower()

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

    data = obtener_json_seguro()
    fila = data.get("fila")
    columna = data.get("columna")
    nombre_intento = limpiar_texto(data.get("nombre", "")).lower()

    if not es_entero_en_rango(fila, 0, 2) or not es_entero_en_rango(columna, 0, 2):
        return jsonify({"error": "Fila y columna deben ser números entre 0 y 2"}), 400

    if not nombre_intento:
        return jsonify({"error": "Nombre de jugador requerido"}), 400

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
#  JUEGO: CONEXIONES
#
#  Se muestran 8 jugadores mezclados. El usuario tiene que
#  encontrar grupos de jugadores que comparten algo (posición,
#  equipo, país, etc). Tiene 4 errores máximo antes de perder.
# ================================================================

MAX_ERRORES_CONEXIONES = 4


def generar_conexiones():
    """
    Elige un atributo (posición, liga, equipo o país) y agrupa
    a los jugadores según ese atributo. Solo es válido si hay
    al menos 2 grupos con 2+ jugadores cada uno.
    """
    tipos = ["posicion", "liga", "equipo", "pais"]
    random.shuffle(tipos)

    for tipo in tipos:
        grupos = {}
        for jugador in JUGADORES:
            valor = jugador[tipo]
            grupos.setdefault(valor, []).append(jugador["nombre"])

        # Descartamos grupos de un solo jugador (no sirven para "conectar")
        grupos_validos = {k: v for k, v in grupos.items() if len(v) >= 2}

        if len(grupos_validos) >= 2:
            return {"tipo": tipo, "grupos": grupos_validos}

    return None


def iniciar_nuevas_conexiones():
    """Genera una partida nueva: arma el tablero y resetea el progreso."""
    resultado = generar_conexiones()
    if resultado is None:
        session["conexiones"] = None
        return

    grupos = resultado["grupos"]
    tablero = []
    for nombres in grupos.values():
        tablero.extend(nombres)
    random.shuffle(tablero)  # Mezclamos para que no se note el orden de los grupos

    session["conexiones"] = {
        "tipo": resultado["tipo"],
        "grupos": grupos,
        "tablero": tablero,
    }
    session["conexiones_resueltos"] = []  # categorías ya encontradas
    session["conexiones_errores"] = 0


@app.route("/conexiones")
def conexiones_page():
    if "conexiones" not in session or session["conexiones"] is None:
        iniciar_nuevas_conexiones()
    return render_template("conexiones.html")


@app.route("/api/conexiones")
def conexiones_info():
    """
    Devuelve el tablero actual (solo los jugadores que faltan por
    agrupar) y los grupos que ya se resolvieron.
    """
    if "conexiones" not in session or session["conexiones"] is None:
        return jsonify({"error": "No hay partida activa"}), 400

    juego = session["conexiones"]
    resueltos = session["conexiones_resueltos"]

    jugadores_resueltos = set()
    grupos_resueltos_info = []
    for valor in resueltos:
        nombres = juego["grupos"][valor]
        jugadores_resueltos.update(nombres)
        grupos_resueltos_info.append({"valor": valor, "jugadores": nombres})

    tablero_pendiente = [n for n in juego["tablero"] if n not in jugadores_resueltos]

    return jsonify({
        "tablero": tablero_pendiente,
        "grupos_resueltos": grupos_resueltos_info,
        "errores": session["conexiones_errores"],
        "errores_max": MAX_ERRORES_CONEXIONES,
        "terminado": (
            len(resueltos) == len(juego["grupos"])
            or session["conexiones_errores"] >= MAX_ERRORES_CONEXIONES
        ),
    })


@app.route("/api/conexiones/intentar", methods=["POST"])
def conexiones_intentar():
    """
    Recibe una lista de nombres que el usuario seleccionó.
    Si coinciden EXACTAMENTE con un grupo sin resolver, acierta.
    Si no, cuenta como error.
    """
    if "conexiones" not in session or session["conexiones"] is None:
        return jsonify({"error": "No hay partida activa"}), 400

    juego = session["conexiones"]
    resueltos = session["conexiones_resueltos"]

    if session["conexiones_errores"] >= MAX_ERRORES_CONEXIONES or len(resueltos) == len(juego["grupos"]):
        return jsonify({"error": "El juego ya terminó"}), 400

    data = obtener_json_seguro()
    seleccion = data.get("jugadores", [])
    if not isinstance(seleccion, list):
        seleccion = []
    seleccion_normalizada = set(limpiar_texto(n).lower() for n in seleccion if isinstance(n, str))

    grupo_encontrado = None
    for valor, nombres in juego["grupos"].items():
        if valor in resueltos:
            continue
        if seleccion_normalizada == set(n.lower() for n in nombres):
            grupo_encontrado = valor
            break

    if grupo_encontrado:
        session["conexiones_resueltos"] = resueltos + [grupo_encontrado]
        session.modified = True
        correcto = True
    else:
        session["conexiones_errores"] += 1
        correcto = False

    terminado = (
        len(session["conexiones_resueltos"]) == len(juego["grupos"])
        or session["conexiones_errores"] >= MAX_ERRORES_CONEXIONES
    )

    return jsonify({
        "correcto": correcto,
        "categoria_encontrada": grupo_encontrado,
        "errores": session["conexiones_errores"],
        "terminado": terminado,
    })


@app.route("/api/conexiones/reiniciar", methods=["POST"])
def conexiones_reiniciar():
    iniciar_nuevas_conexiones()
    return jsonify({"ok": True})

# ================================================================
#  JUEGO: TRIVIA RÁPIDA
#
#  5 preguntas de opción múltiple por partida, elegidas al azar
#  de un banco de preguntas. El usuario nunca ve la respuesta
#  correcta hasta que contesta.
# ================================================================

PREGUNTAS_TRIVIA = [
    {
        "pregunta": "¿Qué selección ganó el Mundial de 2022 en Qatar?",
        "opciones": ["Francia", "Argentina", "Brasil", "Croacia"],
        "correcta": 1,
    },
    {
        "pregunta": "¿Quién es el máximo goleador histórico de la Champions League?",
        "opciones": ["Lionel Messi", "Cristiano Ronaldo", "Robert Lewandowski", "Karim Benzema"],
        "correcta": 1,
    },
    {
        "pregunta": "¿Cuántos goles necesita un jugador para anotar un 'hat-trick'?",
        "opciones": ["2", "3", "4", "5"],
        "correcta": 1,
    },
    {
        "pregunta": "¿Qué equipo tiene más títulos de Liga MX?",
        "opciones": ["Chivas", "América", "Cruz Azul", "Toluca"],
        "correcta": 1,
    },
    {
        "pregunta": "¿En qué país se jugó el Mundial de 1978, ganado por la selección local?",
        "opciones": ["Brasil", "Uruguay", "Argentina", "México"],
        "correcta": 2,
    },
    {
        "pregunta": "¿Cuál es el club con más títulos de Copa Libertadores?",
        "opciones": ["Boca Juniors", "River Plate", "Independiente", "Peñarol"],
        "correcta": 2,
    },
    {
        "pregunta": "¿Cuántos jugadores de campo (sin contar al portero) tiene un equipo en la cancha?",
        "opciones": ["9", "10", "11", "12"],
        "correcta": 1,
    },
]

PREGUNTAS_POR_PARTIDA = 5


def iniciar_nueva_trivia():
    """Elige 5 preguntas al azar del banco completo, sin repetir."""
    indices = list(range(len(PREGUNTAS_TRIVIA)))
    random.shuffle(indices)
    session["trivia_preguntas"] = indices[:PREGUNTAS_POR_PARTIDA]
    session["trivia_actual"] = 0
    session["trivia_aciertos"] = 0


def pregunta_publica(indice_pregunta):
    """
    Devuelve la pregunta y sus opciones SIN el campo "correcta".
    Así el navegador nunca puede ver la respuesta antes de contestar.
    """
    p = PREGUNTAS_TRIVIA[indice_pregunta]
    return {"pregunta": p["pregunta"], "opciones": p["opciones"]}


@app.route("/trivia")
def trivia_page():
    if "trivia_preguntas" not in session:
        iniciar_nueva_trivia()
    return render_template("trivia.html")


@app.route("/api/trivia")
def trivia_info():
    """Devuelve la pregunta actual del usuario, o el resultado final si ya terminó."""
    if "trivia_preguntas" not in session:
        return jsonify({"error": "No hay partida activa"}), 400

    actual = session["trivia_actual"]
    total = len(session["trivia_preguntas"])

    if actual >= total:
        return jsonify({
            "terminado": True,
            "aciertos": session["trivia_aciertos"],
            "total": total,
        })

    indice_real = session["trivia_preguntas"][actual]
    return jsonify({
        "terminado": False,
        "numero_pregunta": actual + 1,
        "total_preguntas": total,
        "aciertos": session["trivia_aciertos"],
        **pregunta_publica(indice_real),
    })


@app.route("/api/trivia/responder", methods=["POST"])
def trivia_responder():
    """
    Recibe el índice de la opción que eligió el usuario (0, 1, 2 o 3),
    la compara contra la respuesta correcta, y avanza a la siguiente pregunta.
    """
    if "trivia_preguntas" not in session:
        return jsonify({"error": "No hay partida activa"}), 400

    actual = session["trivia_actual"]
    total = len(session["trivia_preguntas"])

    if actual >= total:
        return jsonify({"error": "El juego ya terminó"}), 400

    data = obtener_json_seguro()
    opcion_elegida = data.get("opcion")

    if not es_entero_en_rango(opcion_elegida, 0, 3):
        return jsonify({"error": "La opción debe ser un número entre 0 y 3"}), 400

    indice_real = session["trivia_preguntas"][actual]
    pregunta = PREGUNTAS_TRIVIA[indice_real]
    correcto = (opcion_elegida == pregunta["correcta"])

    if correcto:
        session["trivia_aciertos"] += 1

    session["trivia_actual"] += 1
    terminado = session["trivia_actual"] >= total

    return jsonify({
        "correcto": correcto,
        "respuesta_correcta": pregunta["correcta"],
        "aciertos": session["trivia_aciertos"],
        "terminado": terminado,
    })


@app.route("/api/trivia/reiniciar", methods=["POST"])
def trivia_reiniciar():
    iniciar_nueva_trivia()
    return jsonify({"ok": True})


# ================================================================
#  PUNTO DE ENTRADA
# ================================================================
if __name__ == "__main__":
    app.run(debug=True)