import os
import time
import sqlite3
import datetime
import requests
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
    El campo 'score' viene en distintos formatos según el archivo
    (son datasets armados por mucha gente distinta a lo largo de años):
    - {"ft": [2, 0]}   <- el más común
    - [2, 0]           <- formato alterno, algunos archivos viejos
    Si no podemos entenderlo, devolvemos None y ese partido se salta.
    """
    if isinstance(score_raw, dict):
        ft = score_raw.get("ft")
        if isinstance(ft, list) and len(ft) == 2:
            return ft[0], ft[1]
        return None
    if isinstance(score_raw, list) and len(score_raw) == 2:
        return score_raw[0], score_raw[1]
    return None


def guardar_en_db(conexion, nombre_torneo, datos_json):
    """
    Guarda los partidos de un archivo. Si algún partido individual
    viene en un formato raro o incompleto, lo SALTA sin tronar
    el script completo (try/except por partido).
    """
    if not datos_json or not isinstance(datos_json, dict) or "matches" not in datos_json:
        return 0, 0, 0

    cursor = conexion.cursor()
    nuevos = 0
    ya_existian = 0
    saltados = 0

    for partido in datos_json["matches"]:
        try:
            if not isinstance(partido, dict):
                saltados += 1
                continue

            marcador = extraer_marcador(partido.get("score"))
            if marcador is None:
                saltados += 1
                continue
            goles1, goles2 = marcador

            equipo1 = partido.get("team1")
            equipo2 = partido.get("team2")
            fecha = partido.get("date")

            if not equipo1 or not equipo2:
                saltados += 1
                continue

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
            # Cualquier cosa rara que no anticipamos: saltamos ESE
            # partido nada más, el script sigue con el siguiente.
            saltados += 1
            continue

    conexion.commit()
    return nuevos, ya_existian, saltados


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
    total_saltados = 0

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
                nuevos, existian, saltados = guardar_en_db(conexion, f"{repo}/{archivo}", datos)
                total_nuevos += nuevos
                total_existian += existian
                total_saltados += saltados
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
    print(f"Partidos que ya existían (saltados, no duplicados): {total_existian}")
    print(f"Partidos saltados por formato raro/incompleto: {total_saltados}")
    print(f"Última actualización guardada: {ahora}")


if __name__ == "__main__":
    main()