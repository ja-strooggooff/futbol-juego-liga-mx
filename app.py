# ================================================================
#  app.py — El servidor de FutTrivia
#
#  Persona 2 (Backend): aquí vive toda la lógica del juego.
#  El navegador NUNCA sabe quién es el jugador secreto hasta
#  que el juego termina. Eso lo decide y lo guarda Python.
# ================================================================
import os
import sqlite3
import random
import datetime
import time
import unicodedata
from flask import Flask, render_template, jsonify, request, session
from flask_session import Session
from sistema_dificultad import calcular_dificultad_jugador, calcular_dificultad_partido

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
                j.valor_mercado,
                j.player_id,
                d.dificultad
            FROM jugadores_reales j
            LEFT JOIN competitions c ON j.liga_codigo = c.competition_id
            LEFT JOIN dificultad_jugadores d ON d.player_id = j.player_id
            WHERE j.nombre IS NOT NULL AND j.nombre != ''
            AND j.posicion IS NOT NULL AND j.posicion != ''
            ORDER BY j.valor_mercado DESC
            LIMIT ?
        """, (limite,)).fetchall()

        conexion.close()

        jugadores = []
        for fila in filas:
            nombre, posicion, pais, club, liga, fecha_nac, valor, player_id, dificultad = fila
            edad = calcular_edad(fecha_nac)
            if edad is None:
                continue  # sin edad no podemos comparar en Wordle, este si es necesario

            jugadores.append({
                "nombre": nombre,
                "posicion": posicion or "Desconocida",
                "liga": liga or "Desconocida",
                "equipo": club or "Sin equipo",
                "pais": pais or "Desconocido",
                "edad": edad,
                "valor_mercado": int(valor) if valor else 0,
                "player_id": player_id,
                # etiqueta precalculada por calcular_dificultad_jugadores.py;
                # si el script no ha corrido, queda None y el filtro de
                # dificultad simplemente no aplica
                "dificultad": dificultad,
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
JUGADORES = cargar_jugadores_desde_db(limite=100000)

ATRIBUTOS_PISTA = ["posicion", "liga", "equipo", "pais", "edad", "valor_mercado"]


def normalizar_nombre(texto):
    """
    Minúsculas y sin acentos (misma idea que buscar.py): así
    'gonzalez' encuentra 'González' y 'MESSI' encuentra 'Messi'.
    """
    if not texto:
        return ""
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


# Índice precalculado (nombre normalizado + sus palabras → jugador)
# para no normalizar 47,000+ nombres en cada intento del usuario.
INDICE_NOMBRES = [
    (normalizar_nombre(j["nombre"]), frozenset(normalizar_nombre(j["nombre"]).split()), j)
    for j in JUGADORES
]


# ================================================================
#  LIGAS JUGABLES
#
#  El usuario puede jugar con todo el pool ("todas") o filtrar por
#  liga. Los valores de "ligas_jugadores" son los nombres que trae
#  el campo liga de JUGADORES (vienen de la tabla competitions).
# ================================================================

LIGAS_JUGABLES = {
    "mx": {"nombre": "Liga MX", "ligas_jugadores": {"liga-mx-clausura"}},
    "argentina": {"nombre": "Liga Argentina", "ligas_jugadores": {"torneo-apertura"}},
}


def liga_valida(valor):
    """'mx' y 'argentina' son ligas reales; cualquier otra cosa es 'todas'."""
    return valor if valor in LIGAS_JUGABLES else "todas"


JUGADORES_POR_LIGA = {"todas": JUGADORES}
INDICE_POR_LIGA = {"todas": INDICE_NOMBRES}
for _clave_liga, _info_liga in LIGAS_JUGABLES.items():
    JUGADORES_POR_LIGA[_clave_liga] = [
        j for j in JUGADORES if j["liga"] in _info_liga["ligas_jugadores"]
    ]
    INDICE_POR_LIGA[_clave_liga] = [
        entrada for entrada in INDICE_NOMBRES
        if entrada[2]["liga"] in _info_liga["ligas_jugadores"]
    ]


# ================================================================
#  DIFICULTAD JUGABLE
#
#  Las etiquetas vienen precalculadas por calcular_dificultad_jugadores.py
#  (tabla dificultad_jugadores, con sistema_dificultad.py). El selector
#  es independiente del de liga: cualquier combinación vale. Si un combo
#  no alcanza para armar un juego (ej. Liga MX + Fácil está vacío), el
#  juego relaja SOLO la dificultad y conserva la liga.
# ================================================================

DIFICULTADES_JUGABLES = {
    "facil": "Fácil",
    "media": "Media",
    "dificil": "Difícil",
    "legendaria": "Legendaria",
}


def dificultad_valida(valor):
    return valor if valor in DIFICULTADES_JUGABLES else "todas"


_POOLS_COMBINADOS = {}


def pool_jugadores(liga, dificultad="todas"):
    """Jugadores de esa liga con esa dificultad (cacheado por combo)."""
    liga = liga_valida(liga)
    dificultad = dificultad_valida(dificultad)
    if dificultad == "todas":
        return JUGADORES_POR_LIGA[liga]
    clave = (liga, dificultad)
    if clave not in _POOLS_COMBINADOS:
        etiqueta = DIFICULTADES_JUGABLES[dificultad]
        _POOLS_COMBINADOS[clave] = [
            j for j in JUGADORES_POR_LIGA[liga] if j["dificultad"] == etiqueta
        ]
    return _POOLS_COMBINADOS[clave]


# player_id → etiqueta, para filtrar las preguntas de trivia
DIFICULTAD_POR_PLAYER_ID = {
    j["player_id"]: j["dificultad"] for j in JUGADORES if j.get("player_id")
}


# ================================================================
#  LÍMITE DE TIEMPO
#
#  Cada partida guarda su fecha límite en la sesión: la validación
#  es del lado del SERVIDOR (un cronómetro solo en el navegador se
#  burla con recargar la página). El frontend muestra la cuenta
#  regresiva y, al llegar a cero, consulta el estado para confirmar.
#  Trivia corre por pregunta; los demás, por partida completa.
# ================================================================

# El tiempo es el TERCER selector del usuario (combinable con liga y
# dificultad). En trivia el tiempo elegido aplica al QUIZ COMPLETO
# (las 5 preguntas comparten un solo reloj), no por pregunta.
TIEMPOS_JUGABLES = {"30": 30, "60": 60, "90": 90, "120": 120}
TIEMPO_DEFECTO = "120"


def tiempo_valido(valor):
    return valor if valor in TIEMPOS_JUGABLES else TIEMPO_DEFECTO


# Para probar la derrota por tiempo sin esperar:
# FUTTRIVIA_TIEMPO_PRUEBA=5 fuerza todos los relojes a 5 segundos.
_SEGUNDOS_PRUEBA = None
if os.environ.get("FUTTRIVIA_TIEMPO_PRUEBA"):
    _SEGUNDOS_PRUEBA = int(os.environ["FUTTRIVIA_TIEMPO_PRUEBA"])


def iniciar_limite(juego, modo, tiempo=TIEMPO_DEFECTO):
    segundos = _SEGUNDOS_PRUEBA or TIEMPOS_JUGABLES[tiempo_valido(tiempo)]
    session[f"{juego}_{modo}_limite"] = time.time() + segundos


def tiempo_restante(juego, modo):
    """Segundos que le quedan a la partida/pregunta (None si no hay reloj:
    partidas viejas en sesión de antes de esta función)."""
    limite = session.get(f"{juego}_{modo}_limite")
    if limite is None:
        return None
    return max(0, int(limite - time.time()))


def tiempo_agotado(juego, modo):
    restante = tiempo_restante(juego, modo)
    return restante is not None and restante <= 0


def _unico_o_error(candidatos, nombre_buscado):
    if len(candidatos) == 1:
        return candidatos[0], None

    # Desempate por fama: los candidatos vienen ordenados por valor de
    # mercado (JUGADORES se carga así). Si el primero es MUY superior
    # al segundo (10x) y realmente conocido, es el que el usuario
    # quiso decir: 'messi' → Lionel Messi, no Rayane Messi.
    primero, segundo = candidatos[0], candidatos[1]
    if primero["valor_mercado"] >= 5000000 and primero["valor_mercado"] >= 10 * max(segundo["valor_mercado"], 1):
        return primero, None

    ejemplos = ", ".join(j["nombre"] for j in candidatos[:3])
    return None, f"Hay {len(candidatos)} jugadores que coinciden con '{nombre_buscado}' (ej: {ejemplos}). Escribe más letras."


def buscar_jugador_flexible(nombre_buscado, liga="todas"):
    """
    Búsqueda tolerante para los intentos de Wordle y Grid, en 3 niveles
    (siempre sin acentos ni mayúsculas, como buscar.py):
    1. Nombre completo exacto: 'lionel messi' → Lionel Messi.
    2. Palabras completas: 'messi' → Lionel Messi (no confunde con
       Junior Messias, porque 'messi' no es una palabra de ese nombre).
    3. Subcadena: 'lewand' → Robert Lewandowski.
    En los niveles 2 y 3 solo se acepta un ganador ÚNICO; con varios
    ('gonzalez') se pide precisar, sin gastarle intentos al usuario.
    Si se juega con liga filtrada, solo busca en jugadores de esa liga.

    Regresa (jugador, None) si hay ganador único, o (None, mensaje).
    """
    consulta = normalizar_nombre(nombre_buscado)
    if not consulta:
        return None, "Nombre de jugador requerido"
    palabras_consulta = set(consulta.split())

    por_palabra = []
    por_subcadena = []
    nombres_vistos = set()
    for nombre_norm, palabras, jugador in INDICE_POR_LIGA[liga_valida(liga)]:
        if nombre_norm == consulta:
            return jugador, None
        if jugador["nombre"] in nombres_vistos:
            continue
        if palabras_consulta <= palabras:
            nombres_vistos.add(jugador["nombre"])
            por_palabra.append(jugador)
        elif consulta in nombre_norm:
            nombres_vistos.add(jugador["nombre"])
            por_subcadena.append(jugador)

    if por_palabra:
        return _unico_o_error(por_palabra, nombre_buscado)
    if por_subcadena:
        return _unico_o_error(por_subcadena, nombre_buscado)
    donde = f" en {LIGAS_JUGABLES[liga]['nombre']}" if liga in LIGAS_JUGABLES else ""
    return None, f"No se encontró ningún jugador con '{nombre_buscado}'{donde}"


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
def pool_wordle(liga, dificultad):
    """El pool del secreto de Wordle; si el combo está vacío (ej. Liga MX
    + Fácil), se relaja la dificultad y se conserva la liga."""
    pool = pool_jugadores(liga, dificultad)
    return pool if pool else JUGADORES_POR_LIGA[liga_valida(liga)]


def obtener_jugador_del_dia(liga="todas", dificultad="todas", tiempo=TIEMPO_DEFECTO):
    hoy = datetime.date.today().isoformat()
    # Con todo en default la semilla es solo la fecha (compatibilidad con
    # el reto diario que ya estaba corriendo); cada combo tiene el suyo
    # (incluido el tiempo: si no, cambiar de reloj regalaría tiempo
    # fresco para el mismo secreto del día).
    todo_default = liga == "todas" and dificultad == "todas" and tiempo == TIEMPO_DEFECTO
    semilla = hoy if todo_default else f"{hoy}-{liga}-{dificultad}-{tiempo}"
    generador = random.Random(semilla)
    return generador.choice(pool_wordle(liga, dificultad))


def iniciar_partida_wordle(modo, liga="todas", dificultad="todas", tiempo=TIEMPO_DEFECTO):
    liga = liga_valida(liga)
    dificultad = dificultad_valida(dificultad)
    tiempo = tiempo_valido(tiempo)
    if modo == "diario":
        jugador_secreto = obtener_jugador_del_dia(liga, dificultad, tiempo)
    else:
        jugador_secreto = random.choice(pool_wordle(liga, dificultad))

    session[f"wordle_{modo}_secreto"] = jugador_secreto["nombre"]
    session[f"wordle_{modo}_intentos"] = 0
    session[f"wordle_{modo}_terminado"] = False
    session[f"wordle_{modo}_pistas_usadas"] = []
    session[f"wordle_{modo}_liga"] = liga
    session[f"wordle_{modo}_dificultad"] = dificultad
    session[f"wordle_{modo}_tiempo"] = tiempo
    session[f"wordle_{modo}_por_tiempo"] = False
    iniciar_limite("wordle", modo, tiempo)

    if modo == "diario":
        session["wordle_diario_fecha"] = datetime.date.today().isoformat()


def necesita_partida_nueva(modo, liga="todas", dificultad="todas", tiempo=TIEMPO_DEFECTO):
    clave_secreto = f"wordle_{modo}_secreto"
    if clave_secreto not in session:
        return True
    if session.get(f"wordle_{modo}_liga", "todas") != liga_valida(liga):
        return True
    if session.get(f"wordle_{modo}_dificultad", "todas") != dificultad_valida(dificultad):
        return True
    if session.get(f"wordle_{modo}_tiempo", TIEMPO_DEFECTO) != tiempo_valido(tiempo):
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
    liga = liga_valida(request.args.get("liga", "todas"))
    dificultad = dificultad_valida(request.args.get("dificultad", "todas"))
    tiempo = tiempo_valido(request.args.get("tiempo", TIEMPO_DEFECTO))
    if necesita_partida_nueva(modo, liga, dificultad, tiempo):
        iniciar_partida_wordle(modo, liga, dificultad, tiempo)
    return render_template("wordle.html")


# ================================================================
#  RUTAS DE API (JSON) — Las usa JavaScript
# ================================================================

def finalizar_wordle_por_tiempo(modo):
    """Si el reloj llegó a cero con la partida viva, se pierde. Regresa
    True si la partida acaba de terminar por tiempo."""
    clave_terminado = f"wordle_{modo}_terminado"
    if not session.get(clave_terminado) and tiempo_agotado("wordle", modo):
        session[clave_terminado] = True
        session[f"wordle_{modo}_por_tiempo"] = True
        registrar_resultado("wordle", modo, "perdido", {
            "por_tiempo": True,
            "jugador": session[f"wordle_{modo}_secreto"],
        })
        return True
    return False


@app.route("/api/wordle")
def wordle_info():
    """Estado de la partida: el frontend lo usa para sincronizar el
    cronómetro y para confirmar la derrota cuando llega a cero."""
    modo = request.args.get("modo", "practica")
    if modo not in ("diario", "practica"):
        modo = "practica"

    clave_secreto = f"wordle_{modo}_secreto"
    if clave_secreto not in session:
        return jsonify({"error": "No hay partida activa"}), 400

    finalizar_wordle_por_tiempo(modo)
    terminado = session[f"wordle_{modo}_terminado"]

    return jsonify({
        "modo": modo,
        "intentos": session[f"wordle_{modo}_intentos"],
        "terminado": terminado,
        "por_tiempo": session.get(f"wordle_{modo}_por_tiempo", False),
        "tiempo_restante": tiempo_restante("wordle", modo),
        "secreto": session[clave_secreto] if terminado else None,
    })


@app.route("/api/jugadores")
def lista_jugadores():
    """Devuelve solo los nombres, para el autocomplete del input.
    Acepta ?liga=mx|argentina para sugerir solo jugadores de esa liga."""
    liga = liga_valida(request.args.get("liga", "todas"))
    nombres = [j["nombre"] for j in JUGADORES_POR_LIGA[liga]]
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

    if finalizar_wordle_por_tiempo(modo):
        return jsonify({"error": f"⏱ Se acabó el tiempo. Era {session[clave_secreto]}."}), 400

    if session.get(clave_terminado):
        return jsonify({"error": "El juego ya terminó."}), 400

    nombre_intento = limpiar_texto(data.get("nombre", ""))
    if not nombre_intento:
        return jsonify({"error": "Nombre de jugador requerido"}), 400

    liga_partida = session.get(f"wordle_{modo}_liga", "todas")
    jugador, error_busqueda = buscar_jugador_flexible(nombre_intento, liga_partida)
    if jugador is None:
        return jsonify({"error": error_busqueda}), 404

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
    if finalizar_wordle_por_tiempo(modo):
        return jsonify({"error": f"⏱ Se acabó el tiempo. Era {session[clave_secreto]}."}), 400
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

    iniciar_partida_wordle(
        "practica",
        session.get("wordle_practica_liga", "todas"),
        session.get("wordle_practica_dificultad", "todas"),
        session.get("wordle_practica_tiempo", TIEMPO_DEFECTO),
    )
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



VALORES_PLACEHOLDER = {"Desconocida", "Desconocido", "Sin equipo"}


def generar_grid_de_liga(generador, pool, max_intentos=100):
    """
    Tablero para una liga específica: filas = 3 equipos de la liga,
    columnas = 3 países o 3 posiciones. (El algoritmo general usa el
    tipo 'liga' en las categorías, pero con el pool filtrado esa
    categoría se vuelve trivial: todos son de la misma liga.)
    Garantía: solo se eligen equipos que tienen al menos un jugador
    para CADA valor de columna.
    """
    if len(pool) < 9:
        return None

    por_equipo = {}
    for jugador in pool:
        if jugador["equipo"] not in VALORES_PLACEHOLDER:
            por_equipo.setdefault(jugador["equipo"], []).append(jugador)
    equipos = [e for e, js in por_equipo.items() if len(js) >= 3]
    if len(equipos) < 3:
        return None

    for _ in range(max_intentos):
        tipo_columnas = generador.choice(["pais", "posicion"])
        equipo_ancla = generador.choice(equipos)
        valores = list(dict.fromkeys(
            j[tipo_columnas] for j in por_equipo[equipo_ancla]
            if j[tipo_columnas] not in VALORES_PLACEHOLDER
        ))
        if len(valores) < 3:
            continue
        columnas = generador.sample(valores, 3)

        equipos_validos = [
            e for e in equipos
            if all(any(j[tipo_columnas] == v for j in por_equipo[e]) for v in columnas)
        ]
        if len(equipos_validos) < 3:
            continue

        return {
            "filas": [{"tipo": "equipo", "valor": e} for e in generador.sample(equipos_validos, 3)],
            "columnas": [{"tipo": tipo_columnas, "valor": v} for v in columnas],
        }
    return None


def _generar_grid_general(generador, pool, max_intentos=500):
    """El algoritmo ancla + testigos sobre el pool que le den."""
    if len(pool) < 9:
        return None

    tipos = ["posicion", "liga", "equipo", "pais"]

    for _ in range(max_intentos):
        ancla = generador.choice(pool)
        tipo_columnas = generador.choice(tipos)
        tipos_filas = [t for t in tipos if t != tipo_columnas]

        if any(ancla[t] in VALORES_PLACEHOLDER for t in tipos_filas):
            continue

        valores_columna = []
        for jugador in pool:
            if all(jugador[t] == ancla[t] for t in tipos_filas):
                valor = jugador[tipo_columnas]
                if valor not in VALORES_PLACEHOLDER and valor not in valores_columna:
                    valores_columna.append(valor)
                    if len(valores_columna) >= 8:
                        break  # con 8 opciones ya hay variedad de sobra

        if len(valores_columna) < 3:
            continue  # ancla demasiado rara (ej. único de su país en su liga)

        return {
            "filas": [{"tipo": t, "valor": ancla[t]} for t in tipos_filas],
            "columnas": [
                {"tipo": tipo_columnas, "valor": v}
                for v in generador.sample(valores_columna, 3)
            ],
        }
    return None


def generar_grid(generador, max_intentos=500, liga="todas", dificultad="todas"):
    """
    Construye el tablero partiendo de jugadores CONCRETOS, no de
    categorías al azar. Con 47,000+ jugadores el método viejo (elegir
    6 categorías y cruzar los dedos para que las 9 intersecciones no
    estuvieran vacías) fallaba prácticamente siempre.

    Cómo funciona (algoritmo general, _generar_grid_general):
    1. Se elige un jugador "ancla" al azar y un tipo para las columnas
       (posición, liga, equipo o país). Los otros 3 tipos, con los
       valores del ancla, son las 3 filas.
    2. Los "testigos" son los jugadores que comparten esos 3 atributos
       con el ancla. Las columnas son 3 valores distintos del tipo de
       columna tomados de los testigos.
    3. Garantía: el testigo de la columna j cumple las 3 filas (por ser
       testigo) y su propia columna, así que las 9 celdas tienen al
       menos un jugador válido — sin verificación extra.

    Con liga filtrada delega en generar_grid_de_liga (equipos × país
    o posición), porque aquí el tipo 'liga' pierde sentido. Con
    dificultad filtrada el tablero se arma con jugadores de ese nivel;
    si el combo no alcanza, se relaja SOLO la dificultad.
    """
    liga = liga_valida(liga)
    dificultad = dificultad_valida(dificultad)
    pool = pool_jugadores(liga, dificultad)

    if liga != "todas":
        grid = generar_grid_de_liga(generador, pool)
        if grid is None and dificultad != "todas":
            grid = generar_grid_de_liga(generador, JUGADORES_POR_LIGA[liga])
        return grid

    grid = _generar_grid_general(generador, pool, max_intentos)
    if grid is None and dificultad != "todas":
        grid = _generar_grid_general(generador, JUGADORES, max_intentos)
    return grid


def jugador_cumple(jugador, tipo, valor):
    """Revisa si un jugador cumple con una categoría específica."""
    return jugador[tipo] == valor


def prefijo_generador(base, liga, dificultad, tiempo=TIEMPO_DEFECTO):
    """Semilla diaria distinta por combinación; el caso todo-default usa
    la base a secas (compatibilidad con los diarios que ya corrían).
    El tiempo también entra: si no, cambiar de reloj repetiría el mismo
    tablero del día con tiempo fresco."""
    partes = [base]
    if liga != "todas":
        partes.append(liga)
    if dificultad != "todas":
        partes.append(dificultad)
    if tiempo != TIEMPO_DEFECTO:
        partes.append(f"t{tiempo}")
    return "-".join(partes)


def iniciar_nuevo_grid(modo, liga="todas", dificultad="todas", tiempo=TIEMPO_DEFECTO):
    liga = liga_valida(liga)
    dificultad = dificultad_valida(dificultad)
    tiempo = tiempo_valido(tiempo)
    generador = obtener_generador(modo, prefijo_generador("grid", liga, dificultad, tiempo))
    grid = generar_grid(generador, liga=liga, dificultad=dificultad)

    session[f"grid_{modo}"] = grid
    session[f"grid_{modo}_usados"] = []
    session[f"grid_{modo}_resueltas"] = {}
    session[f"grid_{modo}_liga"] = liga
    session[f"grid_{modo}_dificultad"] = dificultad
    session[f"grid_{modo}_tiempo"] = tiempo
    session[f"grid_{modo}_por_tiempo"] = False
    iniciar_limite("grid", modo, tiempo)

    if modo == "diario":
        session["grid_diario_fecha"] = datetime.date.today().isoformat()


def necesita_grid_nuevo(modo, liga="todas", dificultad="todas", tiempo=TIEMPO_DEFECTO):
    clave = f"grid_{modo}"
    if clave not in session or session[clave] is None:
        return True
    if session.get(f"grid_{modo}_liga", "todas") != liga_valida(liga):
        return True
    if session.get(f"grid_{modo}_dificultad", "todas") != dificultad_valida(dificultad):
        return True
    if session.get(f"grid_{modo}_tiempo", TIEMPO_DEFECTO) != tiempo_valido(tiempo):
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
    liga = liga_valida(request.args.get("liga", "todas"))
    dificultad = dificultad_valida(request.args.get("dificultad", "todas"))
    tiempo = tiempo_valido(request.args.get("tiempo", TIEMPO_DEFECTO))
    if necesita_grid_nuevo(modo, liga, dificultad, tiempo):
        iniciar_nuevo_grid(modo, liga, dificultad, tiempo)
    return render_template("grid.html")


def finalizar_grid_por_tiempo(modo):
    """El grid se pierde si el reloj llega a cero antes de las 9 celdas."""
    if session.get(f"grid_{modo}_por_tiempo"):
        return False  # ya estaba perdido por tiempo
    completo = len(session.get(f"grid_{modo}_resueltas", {})) == 9
    if not completo and tiempo_agotado("grid", modo):
        session[f"grid_{modo}_por_tiempo"] = True
        registrar_resultado("grid", modo, "perdido", {
            "por_tiempo": True,
            "resueltas": len(session.get(f"grid_{modo}_resueltas", {})),
        })
        return True
    return False


@app.route("/api/grid")
def grid_info():
    modo = request.args.get("modo", "practica")
    if modo not in ("diario", "practica"):
        modo = "practica"

    clave = f"grid_{modo}"
    if clave not in session or session[clave] is None:
        return jsonify({"error": "No hay grid activo"}), 400

    finalizar_grid_por_tiempo(modo)

    return jsonify({
        "modo": modo,
        "filas": session[clave]["filas"],
        "columnas": session[clave]["columnas"],
        "resueltas": session[f"grid_{modo}_resueltas"],
        "por_tiempo": session.get(f"grid_{modo}_por_tiempo", False),
        "tiempo_restante": tiempo_restante("grid", modo),
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

    if finalizar_grid_por_tiempo(modo) or session.get(f"grid_{modo}_por_tiempo"):
        return jsonify({"error": "⏱ Se acabó el tiempo. Reinicia para jugar otro tablero."}), 400

    fila = data.get("fila")
    columna = data.get("columna")
    nombre_intento = limpiar_texto(data.get("nombre", ""))

    if not es_entero_en_rango(fila, 0, 2) or not es_entero_en_rango(columna, 0, 2):
        return jsonify({"error": "Fila y columna deben ser números entre 0 y 2"}), 400
    if not nombre_intento:
        return jsonify({"error": "Nombre de jugador requerido"}), 400

    celda_key = f"{fila}-{columna}"
    clave_resueltas = f"grid_{modo}_resueltas"
    clave_usados = f"grid_{modo}_usados"

    if session[clave_resueltas].get(celda_key):
        return jsonify({"error": "Esta celda ya está resuelta"}), 400

    jugador, error_busqueda = buscar_jugador_flexible(
        nombre_intento, session.get(f"grid_{modo}_liga", "todas")
    )
    if jugador is None:
        return jsonify({"error": error_busqueda}), 404

    if jugador["nombre"] in session[clave_usados]:
        return jsonify({"error": "Ese jugador ya fue usado en este tablero"}), 400

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

    iniciar_nuevo_grid(
        "practica",
        session.get("grid_practica_liga", "todas"),
        session.get("grid_practica_dificultad", "todas"),
        session.get("grid_practica_tiempo", TIEMPO_DEFECTO),
    )
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

    if finalizar_grid_por_tiempo(modo) or session.get(f"grid_{modo}_por_tiempo"):
        return jsonify({"error": "⏱ Se acabó el tiempo. Reinicia para jugar otro tablero."}), 400

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

TAMANO_GRUPO_CONEXIONES = 4


def _generar_conexiones_con_pool(generador, pool, liga, max_intentos):
    """
    Arma 4 grupos de 4 jugadores (estilo NYT Connections), igual que
    el arreglo de generar_grid: partiendo de jugadores CONCRETOS.
    El método viejo agrupaba el pool completo por un solo atributo y
    mandaba los 47,000+ jugadores al tablero — injugable.

    Cómo funciona:
    1. Cada grupo sale de un jugador "ancla" elegido al azar: uno por
       cada tipo (posición, liga, equipo y país), así las 4 categorías
       son de tipos distintos y el tablero tiene variedad. Con liga
       filtrada el tipo 'liga' se vuelve trivial (todos son de la
       misma), así que los 4 grupos salen de posición/equipo/país
       con un tipo repetido (valores distintos).
    2. Los miembros de un grupo cumplen SU categoría y NINGUNA de las
       otras 3, para que cada ficha pertenezca a exactamente un grupo
       y el rompecabezas tenga una sola solución.
    3. Se exigen 16 nombres distintos (hay homónimos en el pool); si
       algo no cuadra, se reintenta con otras anclas.
    """
    if len(pool) < 4 * TAMANO_GRUPO_CONEXIONES:
        return None

    for _ in range(max_intentos):
        if liga == "todas":
            tipos = ["posicion", "liga", "equipo", "pais"]
        else:
            tipos = ["posicion", "equipo", "pais"]
            tipos = tipos + [generador.choice(tipos)]

        categorias = []
        for tipo in tipos:
            ancla = generador.choice(pool)
            categorias.append((tipo, ancla[tipo]))

        valores = [v for _, v in categorias]
        if len(set(valores)) < 4 or any(v in VALORES_PLACEHOLDER for v in valores):
            continue

        grupos = {}
        for tipo, valor in categorias:
            candidatos = list(dict.fromkeys(
                j["nombre"] for j in pool
                if j[tipo] == valor
                and not any(j[t2] == v2 for t2, v2 in categorias if (t2, v2) != (tipo, valor))
            ))
            if len(candidatos) < TAMANO_GRUPO_CONEXIONES:
                break
            grupos[valor] = generador.sample(candidatos, TAMANO_GRUPO_CONEXIONES)

        if len(grupos) < 4:
            continue

        nombres = [n for miembros in grupos.values() for n in miembros]
        if len(set(nombres)) != 4 * TAMANO_GRUPO_CONEXIONES:
            continue  # un homónimo se coló en dos grupos

        return {"tipo": "mixto", "grupos": grupos}
    return None


def generar_conexiones(generador, max_intentos=200, liga="todas", dificultad="todas"):
    """Envuelve el algoritmo de anclas con el pool del combo liga ×
    dificultad; si con ese pool no sale tablero (combo muy chico),
    se relaja SOLO la dificultad y se conserva la liga."""
    liga = liga_valida(liga)
    dificultad = dificultad_valida(dificultad)

    resultado = _generar_conexiones_con_pool(
        generador, pool_jugadores(liga, dificultad), liga, max_intentos
    )
    if resultado is None and dificultad != "todas":
        resultado = _generar_conexiones_con_pool(
            generador, JUGADORES_POR_LIGA[liga], liga, max_intentos
        )
    return resultado


def iniciar_nuevas_conexiones(modo, liga="todas", dificultad="todas", tiempo=TIEMPO_DEFECTO):
    liga = liga_valida(liga)
    dificultad = dificultad_valida(dificultad)
    tiempo = tiempo_valido(tiempo)
    generador = obtener_generador(modo, prefijo_generador("conexiones", liga, dificultad, tiempo))
    resultado = generar_conexiones(generador, liga=liga, dificultad=dificultad)

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
    session[f"conexiones_{modo}_liga"] = liga
    session[f"conexiones_{modo}_dificultad"] = dificultad
    session[f"conexiones_{modo}_tiempo"] = tiempo
    session[f"conexiones_{modo}_por_tiempo"] = False
    iniciar_limite("conexiones", modo, tiempo)

    if modo == "diario":
        session["conexiones_diario_fecha"] = datetime.date.today().isoformat()


def necesita_conexiones_nuevas(modo, liga="todas", dificultad="todas", tiempo=TIEMPO_DEFECTO):
    clave = f"conexiones_{modo}"
    if clave not in session or session[clave] is None:
        return True
    if session.get(f"conexiones_{modo}_liga", "todas") != liga_valida(liga):
        return True
    if session.get(f"conexiones_{modo}_dificultad", "todas") != dificultad_valida(dificultad):
        return True
    if session.get(f"conexiones_{modo}_tiempo", TIEMPO_DEFECTO) != tiempo_valido(tiempo):
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
    liga = liga_valida(request.args.get("liga", "todas"))
    dificultad = dificultad_valida(request.args.get("dificultad", "todas"))
    tiempo = tiempo_valido(request.args.get("tiempo", TIEMPO_DEFECTO))
    if necesita_conexiones_nuevas(modo, liga, dificultad, tiempo):
        iniciar_nuevas_conexiones(modo, liga, dificultad, tiempo)
    return render_template("conexiones.html")


def finalizar_conexiones_por_tiempo(modo):
    """Al agotarse el tiempo se consumen los errores permitidos: así la
    lógica existente de derrota (errores >= máximo) aplica sola."""
    juego = session.get(f"conexiones_{modo}")
    if juego is None or session.get(f"conexiones_{modo}_por_tiempo"):
        return False
    resueltos = session[f"conexiones_{modo}_resueltos"]
    ya_termino = (
        session[f"conexiones_{modo}_errores"] >= MAX_ERRORES_CONEXIONES
        or len(resueltos) == len(juego["grupos"])
    )
    if not ya_termino and tiempo_agotado("conexiones", modo):
        session[f"conexiones_{modo}_errores"] = MAX_ERRORES_CONEXIONES
        session[f"conexiones_{modo}_por_tiempo"] = True
        registrar_resultado("conexiones", modo, "perdido", {"por_tiempo": True})
        return True
    return False


@app.route("/api/conexiones")
def conexiones_info():
    modo = request.args.get("modo", "practica")
    if modo not in ("diario", "practica"):
        modo = "practica"

    clave = f"conexiones_{modo}"
    if clave not in session or session[clave] is None:
        return jsonify({"error": "No hay partida activa"}), 400

    finalizar_conexiones_por_tiempo(modo)

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
        "por_tiempo": session.get(f"conexiones_{modo}_por_tiempo", False),
        "tiempo_restante": tiempo_restante("conexiones", modo),
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

    if finalizar_conexiones_por_tiempo(modo):
        return jsonify({"error": "⏱ Se acabó el tiempo. Reinicia para jugar otro tablero."}), 400

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

    iniciar_nuevas_conexiones(
        "practica",
        session.get("conexiones_practica_liga", "todas"),
        session.get("conexiones_practica_dificultad", "todas"),
        session.get("conexiones_practica_tiempo", TIEMPO_DEFECTO),
    )
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

    if finalizar_conexiones_por_tiempo(modo) or session.get(f"conexiones_{modo}_por_tiempo"):
        return jsonify({"error": "⏱ Se acabó el tiempo. Reinicia para jugar otro tablero."}), 400

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
    Carga UNA SOLA VEZ (al arrancar el servidor) los IDs de partidos
    históricos, clasificados por liga (el torneo dice de dónde viene:
    'mexico-txt/...' y '.../mx.1.json' son Liga MX, 'argentina-txt/...'
    es la liga argentina). Así no consultamos la base completa cada
    vez que alguien empieza una trivia. Si futtrivia.db no existe,
    el juego sigue funcionando con las preguntas fijas, sin tronar.
    """
    por_liga = {"todas": [], "mx": [], "argentina": []}
    try:
        conexion = sqlite3.connect("futtrivia.db")
        cursor = conexion.cursor()
        for id_partido, torneo in cursor.execute("SELECT id, torneo FROM partidos"):
            por_liga["todas"].append(id_partido)
            torneo = (torneo or "").lower()
            if torneo.startswith("mexico-txt/") or "/mx." in torneo:
                por_liga["mx"].append(id_partido)
            elif torneo.startswith("argentina-txt/"):
                por_liga["argentina"].append(id_partido)
        conexion.close()
    except Exception:
        pass
    return por_liga


IDS_PARTIDOS_POR_LIGA = cargar_ids_partidos()
IDS_PARTIDOS = IDS_PARTIDOS_POR_LIGA["todas"]


def cargar_datos_preguntas_nuevas():
    """
    Carga UNA SOLA VEZ (al arrancar) los candidatos para las preguntas
    nuevas de goles, transferencias y valor de mercado. Solo lo barato:
    jugadores con valor de mercado alto (~2,000) y transferencias caras
    (~560). Los goles por jugador NO se precalculan aquí porque agregar
    toda la tabla appearances (1.8M filas) tarda ~25 s; se consultan por
    jugador al generar cada pregunta, usando el índice por player_id.
    Igual que cargar_ids_partidos: si no hay base, listas vacías y el
    juego sigue con el banco fijo.
    """
    try:
        conexion = sqlite3.connect("futtrivia.db")
        cursor = conexion.cursor()
        jugadores = cursor.execute("""
            SELECT j.player_id, j.nombre, j.valor_mercado,
                   COALESCE(c.nombre, j.liga_codigo) AS liga
            FROM jugadores_reales j
            LEFT JOIN competitions c ON j.liga_codigo = c.competition_id
            WHERE j.valor_mercado >= 1000000 AND j.nombre IS NOT NULL
        """).fetchall()
        transferencias = cursor.execute("""
            SELECT t.player_id, t.player_name, t.temporada,
                   t.club_origen_nombre, t.club_destino_nombre, t.monto_transferencia,
                   COALESCE(c.nombre, j.liga_codigo) AS liga
            FROM transfers t
            LEFT JOIN jugadores_reales j ON j.player_id = t.player_id
            LEFT JOIN competitions c ON j.liga_codigo = c.competition_id
            WHERE t.monto_transferencia >= 1000000
              AND t.player_name IS NOT NULL AND t.temporada IS NOT NULL
              AND t.club_origen_nombre IS NOT NULL AND t.club_destino_nombre IS NOT NULL
              AND t.club_origen_nombre != t.club_destino_nombre
        """).fetchall()
        conexion.close()
        return jugadores, transferencias
    except Exception:
        return [], []


_FAMOSOS_CRUDO, _TRANSFERENCIAS_CRUDO = cargar_datos_preguntas_nuevas()

# Por liga: con el pool completo se piden umbrales altos (jugadores
# de 5M+/transferencias de 10M+); dentro de una liga se relajan a 1M
# porque los montos de Liga MX/Argentina son más chicos.
FAMOSOS_POR_LIGA = {
    "todas": [(pid, n, v) for pid, n, v, _ in _FAMOSOS_CRUDO if v >= 5000000],
}
TRANSFERENCIAS_POR_LIGA = {
    "todas": [t[:6] for t in _TRANSFERENCIAS_CRUDO if t[5] >= 10000000],
}
for _clave_liga, _info_liga in LIGAS_JUGABLES.items():
    FAMOSOS_POR_LIGA[_clave_liga] = [
        (pid, n, v) for pid, n, v, liga in _FAMOSOS_CRUDO
        if liga in _info_liga["ligas_jugadores"]
    ]
    TRANSFERENCIAS_POR_LIGA[_clave_liga] = [
        t[:6] for t in _TRANSFERENCIAS_CRUDO
        if t[6] in _info_liga["ligas_jugadores"]
    ]

JUGADORES_FAMOSOS = FAMOSOS_POR_LIGA["todas"]
TRANSFERENCIAS_CARAS = TRANSFERENCIAS_POR_LIGA["todas"]
CLUBES_TRANSFERENCIA = sorted({t[4] for t in TRANSFERENCIAS_CARAS})


def stats_jugador(cursor, player_id):
    """Apariciones y goles de clubes de un jugador (consulta con índice, rápida)."""
    fila = cursor.execute(
        "SELECT COUNT(*), COALESCE(SUM(goles), 0) FROM appearances WHERE player_id = ?",
        (player_id,)
    ).fetchone()
    return fila[0], fila[1]


def dificultad_de_jugador(cursor, conexion, player_id, nombre, valor_mercado):
    """Etiqueta de dificultad de una pregunta centrada en un jugador."""
    apariciones, goles = stats_jugador(cursor, player_id)
    etiqueta, _ = calcular_dificultad_jugador(
        valor_mercado or 0, apariciones, goles, nombre, conexion
    )
    return etiqueta


def generar_pregunta_desde_partido(cursor, partido_id):
    """Convierte un partido real de la base de datos en una pregunta de opción múltiple."""
    cursor.execute(
        "SELECT equipo1, equipo2, goles1, goles2, torneo, fecha FROM partidos WHERE id = ?",
        (partido_id,)
    )
    fila = cursor.fetchone()
    if fila is None:
        return None

    equipo1, equipo2, goles1, goles2, torneo, fecha = fila

    if goles1 > goles2:
        ganador = equipo1
    elif goles2 > goles1:
        ganador = equipo2
    else:
        ganador = "Empate"

    try:
        anio = int((fecha or "")[:4])
    except ValueError:
        anio = None
    dificultad, _ = calcular_dificultad_partido(torneo, anio)

    opciones = [equipo1, equipo2, "Empate"]
    return {
        "pregunta": f"¿Quién ganó el partido {equipo1} vs {equipo2}?",
        "opciones": opciones,
        "correcta": opciones.index(ganador),
        "dificultad": dificultad,
    }


def generar_pregunta_goles(generador, cursor, conexion, famosos):
    """¿Quién marcó más goles? entre 4 jugadores reales (tabla appearances).
    La dificultad sale del jugador de la respuesta correcta."""
    if len(famosos) < 4:
        return None

    for _ in range(10):  # reintenta si hay empate o puros ceros
        candidatos = generador.sample(famosos, 4)
        datos = []
        for player_id, nombre, valor in candidatos:
            apariciones, goles = stats_jugador(cursor, player_id)
            datos.append((player_id, nombre, valor, apariciones, goles))

        goles_lista = [d[4] for d in datos]
        maximo = max(goles_lista)
        if maximo < 10 or goles_lista.count(maximo) > 1:
            continue

        indice = goles_lista.index(maximo)
        player_id, nombre, valor, apariciones, goles = datos[indice]
        etiqueta, _ = calcular_dificultad_jugador(valor, apariciones, goles, nombre, conexion)
        return {
            "pregunta": "¿Cuál de estos jugadores ha marcado más goles a nivel de clubes (desde 2012)?",
            "opciones": [d[1] for d in datos],
            "correcta": indice,
            "dificultad": etiqueta,
        }
    return None


def generar_pregunta_transferencia(generador, cursor, conexion, transferencias, clubes):
    """¿A qué club se transfirió X? con una transferencia real (tabla transfers).
    El club de origen entra como distractor junto con 2 clubes al azar."""
    if not transferencias or len(clubes) < 4:
        return None

    player_id, nombre, temporada, origen, destino, _monto = generador.choice(transferencias)
    distractores = [c for c in clubes if c not in (destino, origen)]
    if len(distractores) < 2:
        return None

    opciones = [destino, origen] + generador.sample(distractores, 2)
    generador.shuffle(opciones)

    fila = cursor.execute(
        "SELECT valor_mercado FROM jugadores_reales WHERE player_id = ?", (player_id,)
    ).fetchone()
    valor = fila[0] if fila else 0

    return {
        "pregunta": f"¿A qué club se transfirió {nombre} en la temporada {temporada}?",
        "opciones": opciones,
        "correcta": opciones.index(destino),
        "dificultad": dificultad_de_jugador(cursor, conexion, player_id, nombre, valor),
    }


def generar_pregunta_valor(generador, cursor, conexion, famosos):
    """¿Quién vale más? entre 4 jugadores reales (tabla jugadores_reales).
    La dificultad sale del jugador de la respuesta correcta."""
    if len(famosos) < 4:
        return None

    for _ in range(10):  # reintenta si hay empate en el valor máximo
        candidatos = generador.sample(famosos, 4)
        valores = [c[2] for c in candidatos]
        maximo = max(valores)
        if valores.count(maximo) > 1:
            continue

        indice = valores.index(maximo)
        player_id, nombre, valor = candidatos[indice]
        return {
            "pregunta": "¿Cuál de estos jugadores tiene el valor de mercado más alto?",
            "opciones": [c[1] for c in candidatos],
            "correcta": indice,
            "dificultad": dificultad_de_jugador(cursor, conexion, player_id, nombre, valor),
        }
    return None


def generar_pool_preguntas(generador, cantidad=10, liga="todas", dificultad="todas"):
    """
    Arma un conjunto mixto de preguntas: las generales (banco fijo de 7),
    varias de "quién ganó" desde los 90,000+ partidos reales, y las nuevas
    de goles (appearances), transferencias (transfers) y valor de mercado
    (jugadores_reales). Con liga filtrada, los partidos y jugadores salen
    solo de esa liga. Con dificultad filtrada solo entran preguntas de esa
    etiqueta (el banco fijo cuenta como Media); si el combo junta menos de
    5 preguntas, se rellena sin filtro de dificultad para que la partida
    siempre sea jugable. Cada pregunta generada lleva su etiqueta de
    dificultad calculada con sistema_dificultad.py.
    """
    liga = liga_valida(liga)
    dificultad = dificultad_valida(dificultad)
    etiqueta = DIFICULTADES_JUGABLES.get(dificultad)  # None si es 'todas'

    ids_partidos = IDS_PARTIDOS_POR_LIGA[liga]
    famosos = FAMOSOS_POR_LIGA[liga]
    transferencias = TRANSFERENCIAS_POR_LIGA[liga]
    if etiqueta:
        famosos = [f for f in famosos if DIFICULTAD_POR_PLAYER_ID.get(f[0]) == etiqueta]
        transferencias = [t for t in transferencias if DIFICULTAD_POR_PLAYER_ID.get(t[0]) == etiqueta]
    clubes = sorted({t[4] for t in transferencias})

    pool = []
    if etiqueta is None or etiqueta == "Media":
        pool = [
            {"pregunta": p["pregunta"], "opciones": p["opciones"], "correcta": p["correcta"], "dificultad": "Media"}
            for p in PREGUNTAS_TRIVIA
        ]

    if ids_partidos or famosos or transferencias:
        conexion = sqlite3.connect("futtrivia.db")
        cursor = conexion.cursor()

        if ids_partidos:
            # Con dificultad filtrada se prueban más candidatos, porque
            # muchos no van a caer en la etiqueta pedida
            candidatos = generador.sample(ids_partidos, min(cantidad * 4, len(ids_partidos)))
            agregadas = 0
            for partido_id in candidatos:
                pregunta = generar_pregunta_desde_partido(cursor, partido_id)
                if pregunta and (etiqueta is None or pregunta["dificultad"] == etiqueta):
                    pool.append(pregunta)
                    if (agregadas := agregadas + 1) >= cantidad:
                        break

        # 2 preguntas de cada tipo nuevo para que el pool tenga variedad
        for _ in range(2):
            for pregunta in (
                generar_pregunta_goles(generador, cursor, conexion, famosos),
                generar_pregunta_transferencia(generador, cursor, conexion, transferencias, clubes),
                generar_pregunta_valor(generador, cursor, conexion, famosos),
            ):
                if pregunta and (etiqueta is None or pregunta["dificultad"] == etiqueta):
                    pool.append(pregunta)

        # Relleno de emergencia: que el combo raro no deje la trivia coja
        if len(pool) < PREGUNTAS_POR_PARTIDA and ids_partidos:
            for partido_id in generador.sample(ids_partidos, min(cantidad, len(ids_partidos))):
                pregunta = generar_pregunta_desde_partido(cursor, partido_id)
                if pregunta:
                    pool.append(pregunta)
                if len(pool) >= PREGUNTAS_POR_PARTIDA:
                    break

        conexion.close()

    return pool


def iniciar_nueva_trivia(modo, liga="todas", dificultad="todas", tiempo=TIEMPO_DEFECTO):
    """
    Ahora arma un pool mixto (preguntas fijas + preguntas reales de
    partidos históricos), lo mezcla, y elige las primeras 5.
    Importante: guardamos las preguntas COMPLETAS en la sesión (con
    todo y la respuesta correcta) porque ya no usamos índices de una
    lista fija — las generamos al vuelo. La respuesta correcta nunca
    se manda al navegador hasta que el usuario contesta.
    """
    liga = liga_valida(liga)
    dificultad = dificultad_valida(dificultad)
    tiempo = tiempo_valido(tiempo)
    generador = obtener_generador(modo, prefijo_generador("trivia", liga, dificultad, tiempo))
    pool = generar_pool_preguntas(generador, cantidad=10, liga=liga, dificultad=dificultad)
    generador.shuffle(pool)

    session[f"trivia_{modo}_preguntas"] = pool[:PREGUNTAS_POR_PARTIDA]
    session[f"trivia_{modo}_actual"] = 0
    session[f"trivia_{modo}_aciertos"] = 0
    session[f"trivia_{modo}_liga"] = liga
    session[f"trivia_{modo}_dificultad"] = dificultad
    session[f"trivia_{modo}_tiempo"] = tiempo
    session[f"trivia_{modo}_por_tiempo"] = False
    # El reloj de trivia es para el QUIZ COMPLETO: un solo límite que
    # corre desde que arranca la partida, compartido por las 5 preguntas.
    iniciar_limite("trivia", modo, tiempo)

    if modo == "diario":
        session["trivia_diario_fecha"] = datetime.date.today().isoformat()


def necesita_trivia_nueva(modo, liga="todas", dificultad="todas", tiempo=TIEMPO_DEFECTO):
    clave = f"trivia_{modo}_preguntas"
    if clave not in session:
        return True
    if session.get(f"trivia_{modo}_liga", "todas") != liga_valida(liga):
        return True
    if session.get(f"trivia_{modo}_dificultad", "todas") != dificultad_valida(dificultad):
        return True
    if session.get(f"trivia_{modo}_tiempo", TIEMPO_DEFECTO) != tiempo_valido(tiempo):
        return True
    if modo == "diario":
        if session.get("trivia_diario_fecha") != datetime.date.today().isoformat():
            return True
    return False


def finalizar_trivia_por_tiempo(modo, total):
    """El reloj del quiz llegó a cero: las preguntas que faltaban se
    pierden y la partida queda registrada una sola vez."""
    if session.get(f"trivia_{modo}_por_tiempo"):
        return
    session[f"trivia_{modo}_por_tiempo"] = True
    session[f"trivia_{modo}_actual"] = total
    registrar_resultado("trivia", modo, "completado", {
        "aciertos": session[f"trivia_{modo}_aciertos"],
        "total": total,
        "por_tiempo": True,
    })


def pregunta_publica(pregunta_completa):
    """Quita el campo 'correcta' antes de mandarla al navegador.
    La dificultad sí se manda: es solo una etiqueta, no revela la respuesta."""
    return {
        "pregunta": pregunta_completa["pregunta"],
        "opciones": pregunta_completa["opciones"],
        "dificultad": pregunta_completa.get("dificultad", "Media"),
    }


@app.route("/trivia")
def trivia_page():
    modo = request.args.get("modo", "practica")
    if modo not in ("diario", "practica"):
        modo = "practica"
    liga = liga_valida(request.args.get("liga", "todas"))
    dificultad = dificultad_valida(request.args.get("dificultad", "todas"))
    tiempo = tiempo_valido(request.args.get("tiempo", TIEMPO_DEFECTO))
    if necesita_trivia_nueva(modo, liga, dificultad, tiempo):
        iniciar_nueva_trivia(modo, liga, dificultad, tiempo)
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

    # ¿Se acabó el reloj del QUIZ? Las preguntas restantes se pierden.
    if actual < total and tiempo_agotado("trivia", modo):
        finalizar_trivia_por_tiempo(modo, total)
        actual = total

    if actual >= total:
        return jsonify({
            "modo": modo, "terminado": True,
            "por_tiempo": session.get(f"trivia_{modo}_por_tiempo", False),
            "aciertos": session[f"trivia_{modo}_aciertos"], "total": total,
        })

    pregunta_actual = preguntas[actual]
    return jsonify({
        "modo": modo, "terminado": False, "numero_pregunta": actual + 1,
        "total_preguntas": total, "aciertos": session[f"trivia_{modo}_aciertos"],
        "tiempo_restante": tiempo_restante("trivia", modo),
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

    # Respuesta que llega con el reloj del quiz vencido: se acabó todo
    if tiempo_agotado("trivia", modo):
        finalizar_trivia_por_tiempo(modo, total)
        return jsonify({
            "modo": modo, "correcto": False, "tiempo_agotado": True,
            "aciertos": session[clave_aciertos], "terminado": True,
        })

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

    iniciar_nueva_trivia(
        "practica",
        session.get("trivia_practica_liga", "todas"),
        session.get("trivia_practica_dificultad", "todas"),
        session.get("trivia_practica_tiempo", TIEMPO_DEFECTO),
    )
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
    total_opciones = len(pregunta["opciones"])

    # Tachamos opciones incorrectas al azar dejando siempre 2 en pie
    # (la correcta y una incorrecta): con 4 opciones se tachan 2, con
    # 3 opciones se tacha 1. Antes se asumían 4 opciones fijas y en las
    # preguntas de 3 la pista podía señalar un índice inexistente o
    # tachar todas las incorrectas y regalar la respuesta.
    incorrectas = [i for i in range(total_opciones) if i != correcta]
    random.shuffle(incorrectas)
    eliminar = incorrectas[:max(total_opciones - 2, 0)]

    return jsonify({"modo": modo, "opciones_eliminadas": eliminar})

# ================================================================
#  JUEGO: ADIVINA EL ESCUDO
#
#  El backend elige un equipo secreto. El usuario tiene 5 intentos.
#  Cada fallo revela una pista nueva (país, liga, inicial, emoji).
#  NOTA: usamos emojis como placeholder temporal de los escudos
#  reales, hasta que Daniel/Juan consigan las imágenes.
# ================================================================

# La dificultad de cada equipo es "qué tan fácil es adivinarlo": los
# clubes globalmente famosos son Fácil; los grandes de su liga, Media;
# los menos mediáticos, Difícil/Legendaria. (Etiquetas a mano porque
# ESCUDOS sigue siendo un placeholder de 13 equipos con emojis.)
ESCUDOS = {
    "Inter Miami": {"emoji": "🌴", "pais": "Estados Unidos", "liga": "MLS", "dificultad": "Media"},
    "Al Nassr": {"emoji": "🌙", "pais": "Arabia Saudita", "liga": "Saudi Pro League", "dificultad": "Media"},
    "Real Madrid": {"emoji": "👑", "pais": "España", "liga": "La Liga", "dificultad": "Fácil"},
    "Manchester City": {"emoji": "🩵", "pais": "Inglaterra", "liga": "Premier League", "dificultad": "Fácil"},
    "Barcelona": {"emoji": "🔵", "pais": "España", "liga": "La Liga", "dificultad": "Fácil"},
    # Liga MX
    "Club América": {"emoji": "🦅", "pais": "México", "liga": "Liga MX", "dificultad": "Fácil"},
    "Chivas": {"emoji": "🐐", "pais": "México", "liga": "Liga MX", "dificultad": "Media"},
    "Cruz Azul": {"emoji": "🚂", "pais": "México", "liga": "Liga MX", "dificultad": "Difícil"},
    "Pumas": {"emoji": "🐆", "pais": "México", "liga": "Liga MX", "dificultad": "Legendaria"},
    # Liga Argentina
    "Boca Juniors": {"emoji": "💛", "pais": "Argentina", "liga": "Liga Argentina", "dificultad": "Fácil"},
    "River Plate": {"emoji": "🎗️", "pais": "Argentina", "liga": "Liga Argentina", "dificultad": "Media"},
    "Racing Club": {"emoji": "🩵", "pais": "Argentina", "liga": "Liga Argentina", "dificultad": "Difícil"},
    "Independiente": {"emoji": "😈", "pais": "Argentina", "liga": "Liga Argentina", "dificultad": "Legendaria"},
}

# Qué equipos entran en cada selección de liga del jugador
ESCUDOS_POR_LIGA = {
    "todas": list(ESCUDOS.keys()),
    "mx": [n for n, info in ESCUDOS.items() if info["liga"] == "Liga MX"],
    "argentina": [n for n, info in ESCUDOS.items() if info["liga"] == "Liga Argentina"],
}

MAX_INTENTOS_ESCUDO = 5


def pool_escudos(liga, dificultad):
    """Equipos del combo liga × dificultad; si queda vacío se relaja
    solo la dificultad, igual que en los otros juegos."""
    equipos = ESCUDOS_POR_LIGA[liga_valida(liga)]
    etiqueta = DIFICULTADES_JUGABLES.get(dificultad_valida(dificultad))
    if etiqueta:
        filtrados = [n for n in equipos if ESCUDOS[n]["dificultad"] == etiqueta]
        if filtrados:
            return filtrados
    return equipos


def iniciar_partida_escudo(modo, liga="todas", dificultad="todas", tiempo=TIEMPO_DEFECTO):
    liga = liga_valida(liga)
    dificultad = dificultad_valida(dificultad)
    tiempo = tiempo_valido(tiempo)
    generador = obtener_generador(modo, prefijo_generador("escudo", liga, dificultad, tiempo))
    equipo_secreto = generador.choice(pool_escudos(liga, dificultad))

    session[f"escudo_{modo}_secreto"] = equipo_secreto
    session[f"escudo_{modo}_intentos"] = 0
    session[f"escudo_{modo}_terminado"] = False
    session[f"escudo_{modo}_liga"] = liga
    session[f"escudo_{modo}_dificultad"] = dificultad
    session[f"escudo_{modo}_tiempo"] = tiempo
    session[f"escudo_{modo}_por_tiempo"] = False
    iniciar_limite("escudo", modo, tiempo)

    if modo == "diario":
        session["escudo_diario_fecha"] = datetime.date.today().isoformat()


def necesita_escudo_nuevo(modo, liga="todas", dificultad="todas", tiempo=TIEMPO_DEFECTO):
    clave = f"escudo_{modo}_secreto"
    if clave not in session:
        return True
    if session.get(f"escudo_{modo}_liga", "todas") != liga_valida(liga):
        return True
    if session.get(f"escudo_{modo}_dificultad", "todas") != dificultad_valida(dificultad):
        return True
    if session.get(f"escudo_{modo}_tiempo", TIEMPO_DEFECTO) != tiempo_valido(tiempo):
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
    liga = liga_valida(request.args.get("liga", "todas"))
    dificultad = dificultad_valida(request.args.get("dificultad", "todas"))
    tiempo = tiempo_valido(request.args.get("tiempo", TIEMPO_DEFECTO))
    if necesita_escudo_nuevo(modo, liga, dificultad, tiempo):
        iniciar_partida_escudo(modo, liga, dificultad, tiempo)
    return render_template("escudo.html")


def finalizar_escudo_por_tiempo(modo):
    """Si el reloj llegó a cero con la partida viva, se pierde."""
    clave_terminado = f"escudo_{modo}_terminado"
    if not session.get(clave_terminado) and tiempo_agotado("escudo", modo):
        session[clave_terminado] = True
        session[f"escudo_{modo}_por_tiempo"] = True
        registrar_resultado("escudo", modo, "perdido", {
            "por_tiempo": True,
            "equipo": session[f"escudo_{modo}_secreto"],
        })
        return True
    return False


@app.route("/api/escudo")
def escudo_info():
    modo = request.args.get("modo", "practica")
    if modo not in ("diario", "practica"):
        modo = "practica"

    clave_secreto = f"escudo_{modo}_secreto"
    if clave_secreto not in session:
        return jsonify({"error": "No hay partida activa"}), 400

    finalizar_escudo_por_tiempo(modo)
    intentos = session[f"escudo_{modo}_intentos"]
    terminado = session[f"escudo_{modo}_terminado"]

    return jsonify({
        "modo": modo,
        "intentos": intentos,
        "intentos_max": MAX_INTENTOS_ESCUDO,
        "terminado": terminado,
        "por_tiempo": session.get(f"escudo_{modo}_por_tiempo", False),
        "tiempo_restante": tiempo_restante("escudo", modo),
        "equipo_secreto": session[clave_secreto] if terminado else None,
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
    if finalizar_escudo_por_tiempo(modo):
        return jsonify({"error": f"⏱ Se acabó el tiempo. Era {session[clave_secreto]}."}), 400
    if session[clave_terminado]:
        return jsonify({"error": "El juego ya terminó"}), 400

    equipo_intento = limpiar_texto(data.get("equipo", ""))
    if not equipo_intento:
        return jsonify({"error": "Equipo requerido"}), 400

    secreto = session[clave_secreto]
    gano = normalizar_nombre(equipo_intento) == normalizar_nombre(secreto)

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

    iniciar_partida_escudo(
        "practica",
        session.get("escudo_practica_liga", "todas"),
        session.get("escudo_practica_dificultad", "todas"),
        session.get("escudo_practica_tiempo", TIEMPO_DEFECTO),
    )
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
    if finalizar_escudo_por_tiempo(modo):
        return jsonify({"error": f"⏱ Se acabó el tiempo. Era {session[clave_secreto]}."}), 400
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