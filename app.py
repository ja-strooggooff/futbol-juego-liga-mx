# ================================================================
#  app.py — El servidor de FutTrivia
#
#  Persona 2 (Backend): aquí vive toda la lógica del juego.
#  El navegador NUNCA sabe quién es el jugador secreto hasta
#  que el juego termina. Eso lo decide y lo guarda Python.
# ================================================================
import sqlite3
import random
import datetime
from flask import Flask, render_template, jsonify, request, session
from flask_session import Session

app = Flask(__name__)

# secret_key es necesario para que Flask pueda usar "session".
# La sesión es una cookie segura donde cada usuario guarda SU
# propia partida, sin que se mezcle con la de otros usuarios.
# En producción esto debe venir de una variable de entorno,
# por ahora lo dejamos fijo para desarrollo.
app.secret_key = "cambia-esto-luego-con-env-var"

from cachelib.file import FileSystemCache
app.config["SESSION_TYPE"] = "cachelib"
app.config["SESSION_CACHELIB"] = FileSystemCache("./flask_sessions")
app.config["SESSION_PERMANENT"] = False
Session(app)

# ================================================================
#  HISTORIAL DE PARTIDAS
#
#  Como todavía no tenemos base de datos, el historial vive en
#  la sesión del navegador (la misma cookie de siempre). Se guardan
#  solo las últimas 20 partidas para no saturar la cookie.
# ================================================================

MAX_HISTORIAL = 20


def registrar_resultado(juego, modo, resultado, detalle=None):
    """
    Guarda una partida terminada en el historial.
    juego: "wordle", "escudo", "trivia", "grid", "conexiones"
    resultado: "ganado", "perdido", "completado"
    detalle: diccionario opcional con datos extra (intentos, aciertos, etc.)
    """
    if "historial" not in session:
        session["historial"] = []

    entrada = {
        "juego": juego,
        "modo": modo,
        "fecha": datetime.date.today().isoformat(),
        "resultado": resultado,
        "detalle": detalle or {},
    }

    historial = session["historial"]
    historial.append(entrada)
    session["historial"] = historial[-MAX_HISTORIAL:]
    session.modified = True


@app.route("/api/historial")
def historial():
    """Devuelve el historial del usuario, más reciente primero."""
    return jsonify({"historial": list(reversed(session.get("historial", [])))})


# ================================================================
#  BASE DE DATOS TEMPORAL DE JUGADORES
#  (la migraremos a SQLite más adelante)
# ================================================================
def calcular_edad(fecha_nac_str):
    """Calcula la edad actual a partir de la fecha de nacimiento."""
    if not fecha_nac_str:
        return None
    try:
        nacimiento = datetime.date.fromisoformat(fecha_nac_str.split(" ")[0])
        hoy = datetime.date.today()
        return hoy.year - nacimiento.year - (
            (hoy.month, hoy.day) < (nacimiento.month, nacimiento.day)
        )
    except Exception:
        return None


def cargar_jugadores_desde_db(limite=50000):
    """
    Carga jugadores reales de la base de datos, filtrando solo los que
    tienen datos completos y un valor de mercado conocido.
    El parámetro 'limite' controla cuántos jugadores se cargan al iniciar
    el servidor — 300 es un buen balance entre variedad y rendimiento.
    Si la base de datos no existe (alguien clonó el repo y no corrió
    los scripts de importación), cae de vuelta a la lista de 8 hardcodeados.
    """
    try:
        conexion = sqlite3.connect("futtrivia.db")
        cursor = conexion.cursor()

        filas = cursor.execute("""
            SELECT
                j.nombre,
                j.posicion_especifica,
                j.pais,
                j.club,
                COALESCE(c.nombre, j.liga_codigo) AS liga,
                j.fecha_nacimiento,
                j.valor_mercado
            FROM jugadores_reales j
            LEFT JOIN competitions c ON j.liga_codigo = c.competition_id
            WHERE j.nombre IS NOT NULL AND j.nombre != ''
            AND j.posicion IS NOT NULL AND j.posicion != ''
            AND j.pais IS NOT NULL AND j.pais != ''
            AND j.club IS NOT NULL AND j.club != ''
            AND j.valor_mercado IS NOT NULL AND j.valor_mercado > 100000
            ORDER BY j.valor_mercado DESC
            LIMIT ?
        """, (limite,)).fetchall()

        conexion.close()

        jugadores = []
        for fila in filas:
            nombre, posicion, pais, club, liga, fecha_nac, valor = fila
            edad = calcular_edad(fecha_nac)
            if edad is None:
                continue  # sin edad no podemos hacer la comparacion numerica

            jugadores.append({
                "nombre": nombre,
                "posicion": posicion or "Desconocida",
                "liga": liga or "Desconocida",
                "equipo": club,
                "pais": pais,
                "edad": edad,
                "valor_mercado": int(valor),
            })

        if jugadores:
            print(f"[DB] {len(jugadores)} jugadores cargados desde futtrivia.db")
            return jugadores
        else:
            raise Exception("No se encontraron jugadores con datos completos")

    except Exception as e:
        print(f"[AVISO] No se pudo cargar jugadores desde DB: {e}")
        print("[AVISO] Usando lista de jugadores de respaldo")
        return JUGADORES_RESPALDO


# Lista de respaldo por si futtrivia.db no existe (ej. Juan o Daniel
# clonaron el repo pero no corrieron los scripts de importación todavía)
JUGADORES_RESPALDO = [
    {"nombre": "Lionel Messi", "posicion": "Right Winger", "liga": "MLS", "equipo": "Inter Miami", "pais": "Argentina", "edad": 37, "valor_mercado": 20000000},
    {"nombre": "Cristiano Ronaldo", "posicion": "Centre-Forward", "liga": "Saudi Pro League", "equipo": "Al Nassr", "pais": "Portugal", "edad": 39, "valor_mercado": 15000000},
    {"nombre": "Kylian Mbappé", "posicion": "Centre-Forward", "liga": "La Liga", "equipo": "Real Madrid", "pais": "Francia", "edad": 25, "valor_mercado": 180000000},
    {"nombre": "Erling Haaland", "posicion": "Centre-Forward", "liga": "Premier League", "equipo": "Manchester City", "pais": "Noruega", "edad": 23, "valor_mercado": 200000000},
    {"nombre": "Vinícius Jr.", "posicion": "Left Winger", "liga": "La Liga", "equipo": "Real Madrid", "pais": "Brasil", "edad": 23, "valor_mercado": 180000000},
    {"nombre": "Pedri", "posicion": "Central Midfield", "liga": "La Liga", "equipo": "Barcelona", "pais": "España", "edad": 22, "valor_mercado": 90000000},
    {"nombre": "Lamine Yamal", "posicion": "Right Winger", "liga": "La Liga", "equipo": "Barcelona", "pais": "España", "edad": 17, "valor_mercado": 150000000},
    {"nombre": "Jude Bellingham", "posicion": "Central Midfield", "liga": "La Liga", "equipo": "Real Madrid", "pais": "Inglaterra", "edad": 21, "valor_mercado": 180000000},
]

# Cargamos los jugadores al arrancar el servidor (una sola vez)
JUGADORES = cargar_jugadores_desde_db(limite=50000)

ATRIBUTOS_PISTA = ["posicion", "liga", "equipo", "pais", "edad", "valor_mercado"]


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

    """
    Elige un jugador secreto al azar y resetea el contador de intentos.
    Por ahora es al azar; cuando hagamos el "reto diario" esta función
    cambiará para elegir siempre el mismo jugador en el mismo día.
    """
def obtener_jugador_del_dia():
    hoy = datetime.date.today().isoformat()
    generador = random.Random(hoy)
    return generador.choice(JUGADORES)


def iniciar_partida_wordle(modo):
    if modo == "diario":
        jugador_secreto = obtener_jugador_del_dia()
    else:
        jugador_secreto = random.choice(JUGADORES)

    session[f"wordle_{modo}_secreto"] = jugador_secreto["nombre"]
    session[f"wordle_{modo}_intentos"] = 0
    session[f"wordle_{modo}_terminado"] = False
    session[f"wordle_{modo}_pistas_usadas"] = []

    if modo == "diario":
        session["wordle_diario_fecha"] = datetime.date.today().isoformat()


def necesita_partida_nueva(modo):
    clave_secreto = f"wordle_{modo}_secreto"
    if clave_secreto not in session:
        return True
    if modo == "diario":
        fecha_guardada = session.get("wordle_diario_fecha")
        if fecha_guardada != datetime.date.today().isoformat():
            return True
    return False


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



    # Si el usuario no tiene partida activa, le iniciamos una.
    # "secreto" not in session significa "este usuario nunca ha jugado
    # o ya terminó su última partida sin reiniciar".

@app.route("/wordle")
def wordle():
    modo = request.args.get("modo", "practica")
    if modo not in ("diario", "practica"):
        modo = "practica"
    if necesita_partida_nueva(modo):
        iniciar_partida_wordle(modo)
    return render_template("wordle.html")


# ================================================================
#  RUTAS DE API (JSON) — Las usa JavaScript
# ================================================================

@app.route("/api/jugadores")
def lista_jugadores():
    """Devuelve solo los nombres, para el autocomplete del input."""
    nombres = [j["nombre"] for j in JUGADORES]
    return jsonify(nombres)



    """
    Esta es la ruta más importante del juego.
    Recibe el nombre que el usuario intentó adivinar, lo compara
    contra el secreto guardado en SU sesión, y devuelve el
    resultado atributo por atributo (correcto / incorrecto / pista).

    El jugador secreto JAMÁS se manda al frontend hasta que
    el juego termina (ganó o se acabaron los intentos).
    """
@app.route("/api/intentar", methods=["POST"])
def intentar():
    data = obtener_json_seguro()
    modo = data.get("modo", "practica")
    if modo not in ("diario", "practica"):
        modo = "practica"

    clave_secreto = f"wordle_{modo}_secreto"
    clave_intentos = f"wordle_{modo}_intentos"
    clave_terminado = f"wordle_{modo}_terminado"

    if clave_secreto not in session:
        return jsonify({"error": "No hay partida activa. Recarga la página."}), 400

    if session.get(clave_terminado):
        return jsonify({"error": "El juego ya terminó."}), 400

    nombre_intento = limpiar_texto(data.get("nombre", "")).lower()
    if not nombre_intento:
        return jsonify({"error": "Nombre de jugador requerido"}), 400

    jugador = next((j for j in JUGADORES if j["nombre"].lower() == nombre_intento), None)
    if jugador is None:
        return jsonify({"error": "Jugador no encontrado"}), 404

    secreto = next(j for j in JUGADORES if j["nombre"] == session[clave_secreto])

    resultado = {}
    for attr in ["posicion", "liga", "equipo", "pais"]:
        valor = jugador[attr]
        resultado[attr] = {"valor": valor, "estado": "correcto" if valor == secreto[attr] else "incorrecto"}

    for attr in ["edad", "valor_mercado"]:
        valor = jugador[attr]
        if valor == secreto[attr]:
            resultado[attr] = {"valor": valor, "estado": "correcto"}
        else:
            resultado[attr] = {"valor": valor, "estado": "incorrecto", "pista": "subir" if valor < secreto[attr] else "bajar"}

    session[clave_intentos] += 1
    gano = jugador["nombre"] == secreto["nombre"]

    if gano or session[clave_intentos] >= 8:
        session[clave_terminado] = True
        registrar_resultado("wordle", modo, "ganado" if gano else "perdido", {
            "intentos": session[clave_intentos],
            "jugador": secreto["nombre"],
        })

    return jsonify({
        "modo": modo,
        "nombre": jugador["nombre"],
        "atributos": resultado,
        "gano": gano,
        "intentos": session[clave_intentos],
        "terminado": session[clave_terminado],
        "secreto": secreto["nombre"] if session[clave_terminado] else None,
    })

@app.route("/api/wordle/pista", methods=["POST"])
def wordle_pista():
    """
    El usuario puede pedir una pista opcional. Cuesta 1 intento
    real (de los 8 totales) y revela un atributo al azar del
    jugador secreto que aún no se le había mostrado.
    """
    data = obtener_json_seguro()
    modo = data.get("modo", "practica")
    if modo not in ("diario", "practica"):
        modo = "practica"

    clave_secreto = f"wordle_{modo}_secreto"
    clave_intentos = f"wordle_{modo}_intentos"
    clave_terminado = f"wordle_{modo}_terminado"
    clave_pistas = f"wordle_{modo}_pistas_usadas"

    if clave_secreto not in session:
        return jsonify({"error": "No hay partida activa"}), 400
    if session.get(clave_terminado):
        return jsonify({"error": "El juego ya terminó"}), 400
    if session[clave_intentos] >= 7:
        return jsonify({"error": "Te quedan muy pocos intentos para pedir más pistas"}), 400

    secreto = next(j for j in JUGADORES if j["nombre"] == session[clave_secreto])
    disponibles = [a for a in ATRIBUTOS_PISTA if a not in session[clave_pistas]]

    if not disponibles:
        return jsonify({"error": "Ya usaste todas las pistas disponibles"}), 400

    atributo_elegido = random.choice(disponibles)
    session[clave_pistas] = session[clave_pistas] + [atributo_elegido]
    session[clave_intentos] += 1

    return jsonify({
        "modo": modo,
        "atributo": atributo_elegido,
        "valor": secreto[atributo_elegido],
        "intentos_usados": session[clave_intentos],
    })





    """
    Empieza una partida nueva manualmente.
    Esto es temporal para que puedan probar — cuando hagamos el
    reto diario, el jugador secreto cambiará solo a la medianoche
    y esta ruta ya no hará falta.
    """
@app.route("/api/wordle/reiniciar", methods=["POST"])
def wordle_reiniciar():
    data = obtener_json_seguro()
    modo = data.get("modo", "practica")

    if modo == "diario":
        return jsonify({"error": "El reto diario no se puede reiniciar. Vuelve mañana."}), 400

    iniciar_partida_wordle("practica")
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

def obtener_generador(modo, prefijo):
    """
    Si es modo diario, regresa un generador con semilla fija basada
    en la fecha de hoy (mismo resultado para todos hoy).
    Si es práctica, regresa un generador nuevo y aleatorio cada vez.
    """
    if modo == "diario":
        hoy = datetime.date.today().isoformat()
        return random.Random(f"{prefijo}-{hoy}")
    return random.Random()



def generar_grid(generador, max_intentos=500):
    categorias_dict = construir_categorias()
    categorias_utiles = [c for c in categorias_dict.items() if len(c[1]) >= 2]
    if len(categorias_utiles) < 6:
        return None

    for _ in range(max_intentos):
        generador.shuffle(categorias_utiles)
        filas = categorias_utiles[:3]
        columnas = categorias_utiles[3:6]
        valido = all(set(jf) & set(jc) for (_, jf) in filas for (_, jc) in columnas)
        if valido:
            return {
                "filas": [{"tipo": k[0], "valor": k[1]} for k, _ in filas],
                "columnas": [{"tipo": k[0], "valor": k[1]} for k, _ in columnas],
            }
    return None


def jugador_cumple(jugador, tipo, valor):
    """Revisa si un jugador cumple con una categoría específica."""
    return jugador[tipo] == valor


def iniciar_nuevo_grid(modo):
    generador = obtener_generador(modo, "grid")
    grid = generar_grid(generador)

    session[f"grid_{modo}"] = grid
    session[f"grid_{modo}_usados"] = []
    session[f"grid_{modo}_resueltas"] = {}

    if modo == "diario":
        session["grid_diario_fecha"] = datetime.date.today().isoformat()


def necesita_grid_nuevo(modo):
    clave = f"grid_{modo}"
    if clave not in session or session[clave] is None:
        return True
    if modo == "diario":
        if session.get("grid_diario_fecha") != datetime.date.today().isoformat():
            return True
    return False

@app.route("/grid")
def grid_page():
    modo = request.args.get("modo", "practica")
    if modo not in ("diario", "practica"):
        modo = "practica"
    if necesita_grid_nuevo(modo):
        iniciar_nuevo_grid(modo)
    return render_template("grid.html")


@app.route("/api/grid")
def grid_info():
    modo = request.args.get("modo", "practica")
    if modo not in ("diario", "practica"):
        modo = "practica"

    clave = f"grid_{modo}"
    if clave not in session or session[clave] is None:
        return jsonify({"error": "No hay grid activo"}), 400

    return jsonify({
    "modo": modo,
    "filas": session[clave]["filas"],
    "columnas": session[clave]["columnas"],
    "resueltas": session[f"grid_{modo}_resueltas"],
})


@app.route("/api/grid/intentar", methods=["POST"])
def grid_intentar():
    data = obtener_json_seguro()
    modo = data.get("modo", "practica")
    if modo not in ("diario", "practica"):
        modo = "practica"

    clave = f"grid_{modo}"
    if clave not in session or session[clave] is None:
        return jsonify({"error": "No hay grid activo"}), 400

    fila = data.get("fila")
    columna = data.get("columna")
    nombre_intento = limpiar_texto(data.get("nombre", "")).lower()

    if not es_entero_en_rango(fila, 0, 2) or not es_entero_en_rango(columna, 0, 2):
        return jsonify({"error": "Fila y columna deben ser números entre 0 y 2"}), 400
    if not nombre_intento:
        return jsonify({"error": "Nombre de jugador requerido"}), 400

    celda_key = f"{fila}-{columna}"
    clave_resueltas = f"grid_{modo}_resueltas"
    clave_usados = f"grid_{modo}_usados"

    if session[clave_resueltas].get(celda_key):
        return jsonify({"error": "Esta celda ya está resuelta"}), 400
    if nombre_intento in [n.lower() for n in session[clave_usados]]:
        return jsonify({"error": "Ese jugador ya fue usado en este tablero"}), 400

    jugador = next((j for j in JUGADORES if j["nombre"].lower() == nombre_intento), None)
    if jugador is None:
        return jsonify({"error": "Jugador no encontrado"}), 404

    cat_fila = session[clave]["filas"][fila]
    cat_col = session[clave]["columnas"][columna]
    correcto = (
        jugador_cumple(jugador, cat_fila["tipo"], cat_fila["valor"])
        and jugador_cumple(jugador, cat_col["tipo"], cat_col["valor"])
    )

    if correcto:
        session[clave_resueltas][celda_key] = jugador["nombre"]
        session[clave_usados] = session[clave_usados] + [jugador["nombre"]]
        session.modified = True

    total = len(session[clave_resueltas])

    if total == 9:
        registrar_resultado("grid", modo, "completado", {"resueltas": total})

    return jsonify({
        "modo": modo,
        "correcto": correcto,
        "nombre": jugador["nombre"],
        "resueltas": total,
        "completo": total == 9,
    })

@app.route("/api/grid/reiniciar", methods=["POST"])
def grid_reiniciar():
    data = obtener_json_seguro()
    modo = data.get("modo", "practica")

    if modo == "diario":
        return jsonify({"error": "El grid diario no se puede reiniciar. Vuelve mañana."}), 400

    iniciar_nuevo_grid("practica")
    return jsonify({"ok": True})

@app.route("/api/grid/pista", methods=["POST"])
def grid_pista():
    data = obtener_json_seguro()
    modo = data.get("modo", "practica")
    if modo not in ("diario", "practica"):
        modo = "practica"

    clave = f"grid_{modo}"
    if clave not in session or session[clave] is None:
        return jsonify({"error": "No hay grid activo"}), 400

    fila = data.get("fila")
    columna = data.get("columna")
    if not es_entero_en_rango(fila, 0, 2) or not es_entero_en_rango(columna, 0, 2):
        return jsonify({"error": "Fila y columna deben ser números entre 0 y 2"}), 400

    celda_key = f"{fila}-{columna}"
    if session[f"grid_{modo}_resueltas"].get(celda_key):
        return jsonify({"error": "Esta celda ya está resuelta"}), 400

    cat_fila = session[clave]["filas"][fila]
    cat_col = session[clave]["columnas"][columna]
    usados = [n.lower() for n in session[f"grid_{modo}_usados"]]

    candidatos = [
        j["nombre"] for j in JUGADORES
        if jugador_cumple(j, cat_fila["tipo"], cat_fila["valor"])
        and jugador_cumple(j, cat_col["tipo"], cat_col["valor"])
        and j["nombre"].lower() not in usados
    ]

    if not candidatos:
        return jsonify({"error": "No hay jugadores disponibles para esta pista"}), 400

    return jsonify({"modo": modo, "jugador_sugerido": random.choice(candidatos)})
# ================================================================
#  JUEGO: CONEXIONES
#
#  Se muestran 8 jugadores mezclados. El usuario tiene que
#  encontrar grupos de jugadores que comparten algo (posición,
#  equipo, país, etc). Tiene 4 errores máximo antes de perder.
# ================================================================

MAX_ERRORES_CONEXIONES = 4

"""
Elige un atributo (posición, liga, equipo o país) y agrupa
a los jugadores según ese atributo. Solo es válido si hay
al menos 2 grupos con 2+ jugadores cada uno.
"""
def generar_conexiones(generador):
    tipos = ["posicion", "liga", "equipo", "pais"]
    generador.shuffle(tipos)
    for tipo in tipos:
        grupos = {}
        for jugador in JUGADORES:
            valor = jugador[tipo]
            grupos.setdefault(valor, []).append(jugador["nombre"])
        grupos_validos = {k: v for k, v in grupos.items() if len(v) >= 2}
        if len(grupos_validos) >= 2:
            return {"tipo": tipo, "grupos": grupos_validos}
    return None

def iniciar_nuevas_conexiones(modo):
    generador = obtener_generador(modo, "conexiones")
    resultado = generar_conexiones(generador)

    if resultado is None:
        session[f"conexiones_{modo}"] = None
        return

    grupos = resultado["grupos"]
    tablero = []
    for nombres in grupos.values():
        tablero.extend(nombres)
    generador.shuffle(tablero)

    session[f"conexiones_{modo}"] = {"tipo": resultado["tipo"], "grupos": grupos, "tablero": tablero}
    session[f"conexiones_{modo}_resueltos"] = []
    session[f"conexiones_{modo}_errores"] = 0

    if modo == "diario":
        session["conexiones_diario_fecha"] = datetime.date.today().isoformat()


def necesita_conexiones_nuevas(modo):
    clave = f"conexiones_{modo}"
    if clave not in session or session[clave] is None:
        return True
    if modo == "diario":
        if session.get("conexiones_diario_fecha") != datetime.date.today().isoformat():
            return True
    return False

@app.route("/conexiones")
def conexiones_page():
    modo = request.args.get("modo", "practica")
    if modo not in ("diario", "practica"):
        modo = "practica"
    if necesita_conexiones_nuevas(modo):
        iniciar_nuevas_conexiones(modo)
    return render_template("conexiones.html")


@app.route("/api/conexiones")
def conexiones_info():
    modo = request.args.get("modo", "practica")
    if modo not in ("diario", "practica"):
        modo = "practica"

    clave = f"conexiones_{modo}"
    if clave not in session or session[clave] is None:
        return jsonify({"error": "No hay partida activa"}), 400

    juego = session[clave]
    resueltos = session[f"conexiones_{modo}_resueltos"]

    jugadores_resueltos = set()
    grupos_resueltos_info = []
    for valor in resueltos:
        nombres = juego["grupos"][valor]
        jugadores_resueltos.update(nombres)
        grupos_resueltos_info.append({"valor": valor, "jugadores": nombres})

    tablero_pendiente = [n for n in juego["tablero"] if n not in jugadores_resueltos]

    return jsonify({
        "modo": modo,
        "tablero": tablero_pendiente,
        "grupos_resueltos": grupos_resueltos_info,
        "errores": session[f"conexiones_{modo}_errores"],
        "errores_max": MAX_ERRORES_CONEXIONES,
        "terminado": (
            len(resueltos) == len(juego["grupos"])
            or session[f"conexiones_{modo}_errores"] >= MAX_ERRORES_CONEXIONES
        ),
    })

@app.route("/api/conexiones/intentar", methods=["POST"])
def conexiones_intentar():
    data = obtener_json_seguro()
    modo = data.get("modo", "practica")
    if modo not in ("diario", "practica"):
        modo = "practica"

    clave = f"conexiones_{modo}"
    if clave not in session or session[clave] is None:
        return jsonify({"error": "No hay partida activa"}), 400

    juego = session[clave]
    clave_resueltos = f"conexiones_{modo}_resueltos"
    clave_errores = f"conexiones_{modo}_errores"
    resueltos = session[clave_resueltos]

    if session[clave_errores] >= MAX_ERRORES_CONEXIONES or len(resueltos) == len(juego["grupos"]):
        return jsonify({"error": "El juego ya terminó"}), 400

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
        session[clave_resueltos] = resueltos + [grupo_encontrado]
        session.modified = True
        correcto = True
    else:
        session[clave_errores] += 1
        correcto = False

    terminado = (
        len(session[clave_resueltos]) == len(juego["grupos"])
        or session[clave_errores] >= MAX_ERRORES_CONEXIONES
    )

    if terminado:
        gano_todo = len(session[clave_resueltos]) == len(juego["grupos"])
        registrar_resultado("conexiones", modo, "ganado" if gano_todo else "perdido", {
            "errores": session[clave_errores],
        })

    return jsonify({
        "modo": modo,
        "correcto": correcto,
        "categoria_encontrada": grupo_encontrado,
        "errores": session[clave_errores],
        "terminado": terminado,
    })


@app.route("/api/conexiones/reiniciar", methods=["POST"])
def conexiones_reiniciar():
    data = obtener_json_seguro()
    modo = data.get("modo", "practica")

    if modo == "diario":
        return jsonify({"error": "Las conexiones de hoy no se pueden reiniciar. Vuelve mañana."}), 400

    iniciar_nuevas_conexiones("practica")
    return jsonify({"ok": True})


@app.route("/api/conexiones/pista", methods=["POST"])
def conexiones_pista():
    data = obtener_json_seguro()
    modo = data.get("modo", "practica")
    if modo not in ("diario", "practica"):
        modo = "practica"

    clave = f"conexiones_{modo}"
    if clave not in session or session[clave] is None:
        return jsonify({"error": "No hay partida activa"}), 400

    juego = session[clave]
    resueltos = session[f"conexiones_{modo}_resueltos"]

    grupos_pendientes = [v for v in juego["grupos"] if v not in resueltos]
    if not grupos_pendientes:
        return jsonify({"error": "Ya no hay grupos pendientes"}), 400

    grupo_elegido = random.choice(grupos_pendientes)
    jugador_pista = random.choice(juego["grupos"][grupo_elegido])

    session[f"conexiones_{modo}_errores"] += 1

    return jsonify({
        "modo": modo,
        "jugador_pista": jugador_pista,
        "errores": session[f"conexiones_{modo}_errores"],
    })

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


def cargar_ids_partidos():
    """
    Carga UNA SOLA VEZ (al arrancar el servidor) la lista de IDs de
    partidos históricos disponibles. Así no consultamos la base de
    datos completa cada vez que alguien empieza una partida de trivia.
    Si el archivo futtrivia.db no existe (alguien clonó el repo y no
    corrió el script de descarga todavía), el juego sigue funcionando
    con las preguntas fijas, sin tronar.
    """
    try:
        conexion = sqlite3.connect("futtrivia.db")
        cursor = conexion.cursor()
        cursor.execute("SELECT id FROM partidos")
        ids = [fila[0] for fila in cursor.fetchall()]
        conexion.close()
        return ids
    except Exception:
        return []


IDS_PARTIDOS = cargar_ids_partidos()


def generar_pregunta_desde_partido(cursor, partido_id):
    """Convierte un partido real de la base de datos en una pregunta de opción múltiple."""
    cursor.execute(
        "SELECT equipo1, equipo2, goles1, goles2 FROM partidos WHERE id = ?",
        (partido_id,)
    )
    fila = cursor.fetchone()
    if fila is None:
        return None

    equipo1, equipo2, goles1, goles2 = fila

    if goles1 > goles2:
        ganador = equipo1
    elif goles2 > goles1:
        ganador = equipo2
    else:
        ganador = "Empate"

    opciones = [equipo1, equipo2, "Empate"]
    return {
        "pregunta": f"¿Quién ganó el partido {equipo1} vs {equipo2}?",
        "opciones": opciones,
        "correcta": opciones.index(ganador),
    }


def generar_pool_preguntas(generador, cantidad=10):
    """
    Arma un conjunto mixto de preguntas: las generales (tu banco fijo
    de 7) más varias generadas al azar desde los 90,000+ partidos reales.
    """
    pool = [
        {"pregunta": p["pregunta"], "opciones": p["opciones"], "correcta": p["correcta"]}
        for p in PREGUNTAS_TRIVIA
    ]

    if IDS_PARTIDOS:
        conexion = sqlite3.connect("futtrivia.db")
        cursor = conexion.cursor()
        elegidos = generador.sample(IDS_PARTIDOS, min(cantidad, len(IDS_PARTIDOS)))
        for partido_id in elegidos:
            pregunta = generar_pregunta_desde_partido(cursor, partido_id)
            if pregunta:
                pool.append(pregunta)
        conexion.close()

    return pool


def iniciar_nueva_trivia(modo):
    """
    Ahora arma un pool mixto (preguntas fijas + preguntas reales de
    partidos históricos), lo mezcla, y elige las primeras 5.
    Importante: guardamos las preguntas COMPLETAS en la sesión (con
    todo y la respuesta correcta) porque ya no usamos índices de una
    lista fija — las generamos al vuelo. La respuesta correcta nunca
    se manda al navegador hasta que el usuario contesta.
    """
    generador = obtener_generador(modo, "trivia")
    pool = generar_pool_preguntas(generador, cantidad=10)
    generador.shuffle(pool)

    session[f"trivia_{modo}_preguntas"] = pool[:PREGUNTAS_POR_PARTIDA]
    session[f"trivia_{modo}_actual"] = 0
    session[f"trivia_{modo}_aciertos"] = 0

    if modo == "diario":
        session["trivia_diario_fecha"] = datetime.date.today().isoformat()


def necesita_trivia_nueva(modo):
    clave = f"trivia_{modo}_preguntas"
    if clave not in session:
        return True
    if modo == "diario":
        if session.get("trivia_diario_fecha") != datetime.date.today().isoformat():
            return True
    return False


def pregunta_publica(pregunta_completa):
    """Quita el campo 'correcta' antes de mandarla al navegador."""
    return {"pregunta": pregunta_completa["pregunta"], "opciones": pregunta_completa["opciones"]}


@app.route("/trivia")
def trivia_page():
    modo = request.args.get("modo", "practica")
    if modo not in ("diario", "practica"):
        modo = "practica"
    if necesita_trivia_nueva(modo):
        iniciar_nueva_trivia(modo)
    return render_template("trivia.html")


@app.route("/api/trivia")
def trivia_info():
    modo = request.args.get("modo", "practica")
    if modo not in ("diario", "practica"):
        modo = "practica"

    clave_preguntas = f"trivia_{modo}_preguntas"
    if clave_preguntas not in session:
        return jsonify({"error": "No hay partida activa"}), 400

    actual = session[f"trivia_{modo}_actual"]
    preguntas = session[clave_preguntas]
    total = len(preguntas)

    if actual >= total:
        return jsonify({
            "modo": modo, "terminado": True,
            "aciertos": session[f"trivia_{modo}_aciertos"], "total": total,
        })

    pregunta_actual = preguntas[actual]
    return jsonify({
        "modo": modo, "terminado": False, "numero_pregunta": actual + 1,
        "total_preguntas": total, "aciertos": session[f"trivia_{modo}_aciertos"],
        **pregunta_publica(pregunta_actual),
    })


@app.route("/api/trivia/responder", methods=["POST"])
def trivia_responder():
    data = obtener_json_seguro()
    modo = data.get("modo", "practica")
    if modo not in ("diario", "practica"):
        modo = "practica"

    clave_preguntas = f"trivia_{modo}_preguntas"
    if clave_preguntas not in session:
        return jsonify({"error": "No hay partida activa"}), 400

    clave_actual = f"trivia_{modo}_actual"
    clave_aciertos = f"trivia_{modo}_aciertos"
    preguntas = session[clave_preguntas]
    actual = session[clave_actual]
    total = len(preguntas)

    if actual >= total:
        return jsonify({"error": "El juego ya terminó"}), 400

    opcion_elegida = data.get("opcion")
    if not es_entero_en_rango(opcion_elegida, 0, 3):
        return jsonify({"error": "La opción debe ser un número entre 0 y 3"}), 400

    pregunta = preguntas[actual]
    correcto = opcion_elegida == pregunta["correcta"]

    if correcto:
        session[clave_aciertos] += 1
    session[clave_actual] += 1
    terminado = session[clave_actual] >= total

    if terminado:
        registrar_resultado("trivia", modo, "completado", {"aciertos": session[clave_aciertos], "total": total})

    return jsonify({
        "modo": modo, "correcto": correcto, "respuesta_correcta": pregunta["correcta"],
        "aciertos": session[clave_aciertos], "terminado": terminado,
    })



@app.route("/api/trivia/reiniciar", methods=["POST"])
def trivia_reiniciar():
    data = obtener_json_seguro()
    modo = data.get("modo", "practica")

    if modo == "diario":
        return jsonify({"error": "La trivia de hoy no se puede reiniciar. Vuelve mañana."}), 400

    iniciar_nueva_trivia("practica")
    return jsonify({"ok": True})

@app.route("/api/trivia/pista", methods=["POST"])
def trivia_pista():
    """
    Elimina 2 opciones incorrectas de la pregunta actual.
    No se puede usar más de una vez por pregunta.
    """
    data = obtener_json_seguro()
    modo = data.get("modo", "practica")
    if modo not in ("diario", "practica"):
        modo = "practica"

    clave_preguntas = f"trivia_{modo}_preguntas"
    if clave_preguntas not in session:
        return jsonify({"error": "No hay partida activa"}), 400

    actual = session[f"trivia_{modo}_actual"]
    total = len(session[clave_preguntas])
    if actual >= total:
        return jsonify({"error": "El juego ya terminó"}), 400

    pregunta = session[clave_preguntas][actual]
    correcta = pregunta["correcta"]

    # Elegimos 2 opciones incorrectas al azar para "tachar"
    incorrectas = [i for i in range(4) if i != correcta]
    random.shuffle(incorrectas)
    eliminar = incorrectas[:2]

    return jsonify({"modo": modo, "opciones_eliminadas": eliminar})

# ================================================================
#  JUEGO: ADIVINA EL ESCUDO
#
#  El backend elige un equipo secreto. El usuario tiene 5 intentos.
#  Cada fallo revela una pista nueva (país, liga, inicial, emoji).
#  NOTA: usamos emojis como placeholder temporal de los escudos
#  reales, hasta que Daniel/Juan consigan las imágenes.
# ================================================================

ESCUDOS = {
    "Inter Miami": {"emoji": "🌴", "pais": "Estados Unidos", "liga": "MLS"},
    "Al Nassr": {"emoji": "🌙", "pais": "Arabia Saudita", "liga": "Saudi Pro League"},
    "Real Madrid": {"emoji": "👑", "pais": "España", "liga": "La Liga"},
    "Manchester City": {"emoji": "🩵", "pais": "Inglaterra", "liga": "Premier League"},
    "Barcelona": {"emoji": "🔵", "pais": "España", "liga": "La Liga"},
}

MAX_INTENTOS_ESCUDO = 5


def iniciar_partida_escudo(modo):
    generador = obtener_generador(modo, "escudo")
    equipo_secreto = generador.choice(list(ESCUDOS.keys()))

    session[f"escudo_{modo}_secreto"] = equipo_secreto
    session[f"escudo_{modo}_intentos"] = 0
    session[f"escudo_{modo}_terminado"] = False

    if modo == "diario":
        session["escudo_diario_fecha"] = datetime.date.today().isoformat()


def necesita_escudo_nuevo(modo):
    clave = f"escudo_{modo}_secreto"
    if clave not in session:
        return True
    if modo == "diario":
        if session.get("escudo_diario_fecha") != datetime.date.today().isoformat():
            return True
    return False


def obtener_pista(equipo_secreto, intentos_usados):
    """
    Va revelando pistas progresivamente según cuántos intentos
    fallidos lleva el usuario. Con 0 intentos, no hay pistas.
    """
    info = ESCUDOS[equipo_secreto]
    pistas = {"nivel_revelado": intentos_usados}

    if intentos_usados >= 1:
        pistas["pais"] = info["pais"]
    if intentos_usados >= 2:
        pistas["liga"] = info["liga"]
    if intentos_usados >= 3:
        pistas["inicial"] = equipo_secreto[0]
    if intentos_usados >= 4:
        pistas["emoji"] = info["emoji"]

    return pistas


@app.route("/escudo")
def escudo_page():
    modo = request.args.get("modo", "practica")
    if modo not in ("diario", "practica"):
        modo = "practica"
    if necesita_escudo_nuevo(modo):
        iniciar_partida_escudo(modo)
    return render_template("escudo.html")


@app.route("/api/escudo")
def escudo_info():
    modo = request.args.get("modo", "practica")
    if modo not in ("diario", "practica"):
        modo = "practica"

    clave_secreto = f"escudo_{modo}_secreto"
    if clave_secreto not in session:
        return jsonify({"error": "No hay partida activa"}), 400

    intentos = session[f"escudo_{modo}_intentos"]
    terminado = session[f"escudo_{modo}_terminado"]

    return jsonify({
        "modo": modo,
        "intentos": intentos,
        "intentos_max": MAX_INTENTOS_ESCUDO,
        "terminado": terminado,
        **obtener_pista(session[clave_secreto], intentos),
    })


@app.route("/api/escudo/intentar", methods=["POST"])
def escudo_intentar():
    data = obtener_json_seguro()
    modo = data.get("modo", "practica")
    if modo not in ("diario", "practica"):
        modo = "practica"

    clave_secreto = f"escudo_{modo}_secreto"
    clave_intentos = f"escudo_{modo}_intentos"
    clave_terminado = f"escudo_{modo}_terminado"

    if clave_secreto not in session:
        return jsonify({"error": "No hay partida activa"}), 400
    if session[clave_terminado]:
        return jsonify({"error": "El juego ya terminó"}), 400

    equipo_intento = limpiar_texto(data.get("equipo", ""))
    if not equipo_intento:
        return jsonify({"error": "Equipo requerido"}), 400

    secreto = session[clave_secreto]
    gano = equipo_intento.lower() == secreto.lower()

    session[clave_intentos] += 1
    if gano or session[clave_intentos] >= MAX_INTENTOS_ESCUDO:
        session[clave_terminado] = True
        registrar_resultado("escudo", modo, "ganado" if gano else "perdido", {
            "intentos": session[clave_intentos],
            "equipo": secreto,
        })

    return jsonify({
        "modo": modo,
        "gano": gano,
        "intentos": session[clave_intentos],
        "terminado": session[clave_terminado],
        "equipo_secreto": secreto if session[clave_terminado] else None,
        **obtener_pista(secreto, session[clave_intentos]),
    })


@app.route("/api/escudo/reiniciar", methods=["POST"])
def escudo_reiniciar():
    data = obtener_json_seguro()
    modo = data.get("modo", "practica")

    if modo == "diario":
        return jsonify({"error": "El escudo de hoy no se puede reiniciar. Vuelve mañana."}), 400

    iniciar_partida_escudo("practica")
    return jsonify({"ok": True})

@app.route("/api/escudo/pista", methods=["POST"])
def escudo_pista():
    """
    Pedir una pista cuesta 1 intento (igual que fallar un guess),
    pero no necesitas escribir un equipo incorrecto para conseguirla.
    """
    data = obtener_json_seguro()
    modo = data.get("modo", "practica")
    if modo not in ("diario", "practica"):
        modo = "practica"

    clave_secreto = f"escudo_{modo}_secreto"
    clave_intentos = f"escudo_{modo}_intentos"
    clave_terminado = f"escudo_{modo}_terminado"

    if clave_secreto not in session:
        return jsonify({"error": "No hay partida activa"}), 400
    if session[clave_terminado]:
        return jsonify({"error": "El juego ya terminó"}), 400
    if session[clave_intentos] >= MAX_INTENTOS_ESCUDO - 1:
        return jsonify({"error": "Te quedan muy pocos intentos para pedir más pistas"}), 400

    session[clave_intentos] += 1
    if session[clave_intentos] >= MAX_INTENTOS_ESCUDO:
        session[clave_terminado] = True

    return jsonify({
        "modo": modo,
        "intentos": session[clave_intentos],
        "terminado": session[clave_terminado],
        **obtener_pista(session[clave_secreto], session[clave_intentos]),
    })




# ================================================================
#  PUNTO DE ENTRADA
# ================================================================
if __name__ == "__main__":
    app.run(debug=True)