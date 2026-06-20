import os
import time
import sqlite3
import datetime
import requests
from collections import Counter
from dotenv import load_dotenv

load_dotenv()
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}


def listar_repos_openfootball():
    repos = []
    pagina = 1
    while True:
        url = f"https://api.github.com/orgs/openfootball/repos?per_page=100&page={pagina}"
        respuesta = requests.get(url, headers=HEADERS)
        datos = respuesta.json()
        if not datos or isinstance(datos, dict):
            break
        repos.extend([repo["name"] for repo in datos])
        pagina += 1
    return repos


def listar_archivos_json(nombre_repo):
    url = f"https://api.github.com/repos/openfootball/{nombre_repo}/git/trees/master?recursive=1"
    respuesta = requests.get(url, headers=HEADERS)
    datos = respuesta.json()
    archivos = datos.get("tree", [])
    return [a["path"] for a in archivos if a["path"].endswith(".json")]


def descargar_json(nombre_repo, ruta_archivo):
    url = f"https://raw.githubusercontent.com/openfootball/{nombre_repo}/master/{ruta_archivo}"
    respuesta = requests.get(url)
    try:
        return respuesta.json()
    except ValueError:
        return None


def extraer_marcador(score_raw):
    """
    Intenta leer el marcador en TODOS los formatos que hemos visto:
    - {"ft": [2, 0]}                          formato normal
    - [2, 0]                                  formato alterno (lista directa)
    - {"ft": {"home": 2, "away": 0}}          formato con diccionario anidado (algunos archivos viejos)
    """
    if isinstance(score_raw, dict):
        ft = score_raw.get("ft")
        if isinstance(ft, list) and len(ft) == 2:
            return ft[0], ft[1]
        if isinstance(ft, dict) and "home" in ft and "away" in ft:
            return ft["home"], ft["away"]
        return None
    if isinstance(score_raw, list) and len(score_raw) == 2:
        return score_raw[0], score_raw[1]
    return None


def diagnosticar_partido(partido):
    """Devuelve por qué un partido NO se pudo guardar, o 'ok' si está bien."""
    if not isinstance(partido, dict):
        return "no_es_diccionario"
    score = partido.get("score")
    if score is None:
        return "sin_score_partido_futuro"
    marcador = extraer_marcador(score)
    if marcador is None:
        return "formato_score_desconocido"
    if not partido.get("team1") or not partido.get("team2"):
        return "faltan_nombres_equipo"
    return "ok"


def guardar_en_db(conexion, nombre_torneo, datos_json, contador_motivos, ejemplos_formato_raro):
    if not datos_json or not isinstance(datos_json, dict) or "matches" not in datos_json:
        return 0, 0

    cursor = conexion.cursor()
    nuevos = 0
    ya_existian = 0

    for partido in datos_json["matches"]:
        try:
            motivo = diagnosticar_partido(partido)
            if motivo != "ok":
                contador_motivos[motivo] += 1
                if motivo == "formato_score_desconocido" and len(ejemplos_formato_raro) < 5:
                    ejemplos_formato_raro.append({
                        "torneo": nombre_torneo,
                        "score_raw": partido.get("score"),
                        "team1": partido.get("team1"),
                        "team2": partido.get("team2"),
                    })
                continue

            goles1, goles2 = extraer_marcador(partido.get("score"))
            equipo1 = partido.get("team1")
            equipo2 = partido.get("team2")
            fecha = partido.get("date")

            cursor.execute("""
                INSERT OR IGNORE INTO partidos
                (torneo, fecha, equipo1, equipo2, goles1, goles2, estadio, grupo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                nombre_torneo, fecha, equipo1, equipo2,
                goles1, goles2, partido.get("ground"), partido.get("group"),
            ))

            if cursor.rowcount == 0:
                ya_existian += 1
            else:
                nuevos += 1

            cursor.execute("""
                SELECT id FROM partidos
                WHERE torneo = ? AND fecha = ? AND equipo1 = ? AND equipo2 = ?
            """, (nombre_torneo, fecha, equipo1, equipo2))
            fila = cursor.fetchone()
            if fila is None:
                continue
            partido_id = fila[0]

            goles_lista = partido.get("goals1", []) + partido.get("goals2", [])
            for gol in goles_lista:
                if not isinstance(gol, dict):
                    continue
                cursor.execute("""
                    INSERT OR IGNORE INTO goles (partido_id, jugador, minuto)
                    VALUES (?, ?, ?)
                """, (partido_id, gol.get("name"), str(gol.get("minute"))))

        except Exception:
            contador_motivos["error_inesperado"] += 1
            continue

    conexion.commit()
    return nuevos, ya_existian


def main():
    if not GITHUB_TOKEN:
        print("ADVERTENCIA: no se encontró GITHUB_TOKEN. Límite de 60 peticiones/hora.")

    conexion = sqlite3.connect("futtrivia.db")
    cursor = conexion.cursor()

    print("Buscando todos los repositorios de openfootball...")
    repos = listar_repos_openfootball()
    print(f"Se encontraron {len(repos)} repositorios.")

    total_nuevos = 0
    total_existian = 0
    contador_motivos = Counter()
    ejemplos_formato_raro = []


    for repo in repos:
        print(f"\nRevisando repo: {repo}")
        try:
            archivos = listar_archivos_json(repo)
        except Exception as e:
            print(f"  No se pudo listar archivos de este repo, lo saltamos: {e}")
            continue

        print(f"  {len(archivos)} archivos JSON encontrados")

        for archivo in archivos:
            try:
                datos = descargar_json(repo, archivo)
                nuevos, existian = guardar_en_db(conexion, f"{repo}/{archivo}", datos, contador_motivos, ejemplos_formato_raro)
                total_nuevos += nuevos
                total_existian += existian
            except Exception as e:
                print(f"  Error con {archivo}, lo saltamos: {e}")
            time.sleep(0.1)

    ahora = datetime.datetime.now().isoformat()
    cursor.execute("""
        INSERT OR REPLACE INTO metadatos (clave, valor) VALUES ('ultima_actualizacion', ?)
    """, (ahora,))
    conexion.commit()
    conexion.close()

    print(f"\n¡Listo!")
    print(f"Partidos nuevos agregados: {total_nuevos}")
    print(f"Partidos que ya existían (no duplicados): {total_existian}")
    print(f"\nDesglose de partidos saltados (por qué):")
    for motivo, cantidad in contador_motivos.most_common():
        print(f"  {motivo}: {cantidad}")
    print(f"\nÚltima actualización guardada: {ahora}")
    print(f"\nEjemplos reales de 'formato_score_desconocido':")
    for ej in ejemplos_formato_raro:
        print(f"  {ej['team1']} vs {ej['team2']} ({ej['torneo']}): score = {ej['score_raw']}")


if __name__ == "__main__":
    main()