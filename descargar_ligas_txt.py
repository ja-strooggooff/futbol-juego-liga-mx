import re
import time
import sqlite3
import requests

# ================================================================
#  PARSER DEL FORMATO FOOTBALL.TXT
#
#  A diferencia de los archivos JSON, estos vienen en texto plano
#  estructurado. Tuvimos que diseñar un parser con expresiones
#  regulares, probado contra archivos reales de México y Argentina
#  (338/340 y 378/378 partidos extraídos correctamente).
# ================================================================

PATRON_FECHA = re.compile(r'^\s{2}(\w{3}) (\w{3}) (\d{1,2})(?: (\d{4}))?\s*$')

PATRON_PARTIDO = re.compile(
    r'^\s+(?:(\d{1,2}:\d{2})\s+)?(.+?)\s+v\s+(.+?)\s+(\d+)-(\d+)(?:\s*\((\d+)-(\d+)\))?\s*$'
)


MESES = {
    "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
    "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
    "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
}


def parsear_football_txt(contenido, anio_default):
    """
    Convierte el contenido de un archivo .txt de openfootball en
    una lista de diccionarios de partidos. Las fechas se guardan
    en formato ISO (YYYY-MM-DD) para que ordenen correctamente,
    igual que las fechas que vienen de los archivos JSON.
    """
    lineas = contenido.split("\n")
    partidos = []
    fecha_actual = None
    anio_actual = str(anio_default)

    for linea in lineas:
        linea_limpia = linea.rstrip("\r")

        m_fecha = PATRON_FECHA.match(linea_limpia)
        if m_fecha:
            dia_semana, mes, dia, anio = m_fecha.groups()
            if anio:
                anio_actual = anio
            mes_numero = MESES.get(mes, "01")
            dia_relleno = dia.zfill(2)
            fecha_actual = f"{anio_actual}-{mes_numero}-{dia_relleno}"
            continue

        m_partido = PATRON_PARTIDO.match(linea_limpia)
        if m_partido:
            hora, equipo1, equipo2, g1, g2, h1, h2 = m_partido.groups()
            partidos.append({
                "date": fecha_actual,
                "team1": equipo1.strip(),
                "team2": equipo2.strip(),
                "goles1": int(g1),
                "goles2": int(g2),
            })

    return partidos


def guardar_partidos_txt(conexion, nombre_torneo, partidos):
    cursor = conexion.cursor()
    nuevos = 0
    ya_existian = 0

    for p in partidos:
        cursor.execute("""
            INSERT OR IGNORE INTO partidos
            (torneo, fecha, equipo1, equipo2, goles1, goles2, estadio, grupo)
            VALUES (?, ?, ?, ?, ?, ?, NULL, NULL)
        """, (nombre_torneo, p["date"], p["team1"], p["team2"], p["goles1"], p["goles2"]))

        if cursor.rowcount == 0:
            ya_existian += 1
        else:
            nuevos += 1

    conexion.commit()
    return nuevos, ya_existian


# ================================================================
#  ARCHIVOS A DESCARGAR
# ================================================================

TEMPORADAS_MEXICO = [
    "2010-11", "2011-12", "2012-13", "2013-14", "2014-15", "2015-16",
    "2016-17", "2017-18", "2018-19", "2019-20", "2020-21", "2021-22",
    "2022-23", "2023-24", "2024-25",
]


def construir_nombres_archivo_mexico(temporada):
    """
    Liga MX siempre se llama 'mx1'. La segunda división cambió de
    nombre con los años: 'mx2ascenso' en temporadas viejas,
    'mx2expansion' en las nuevas. Probamos ambos nombres.
    """
    return [
        f"{temporada}_mx1.txt",
        f"{temporada}_mx2ascenso.txt",
        f"{temporada}_mx2expansion.txt",
    ]

ARCHIVOS_ARGENTINA = [
    f"{temporada}_ar1.txt"
    for temporada in ["2018-19", "2019-20", "2020", "2021", "2022", "2023", "2024", "2025"]
]


def descargar_archivo_txt(url):
    respuesta = requests.get(url)
    if respuesta.status_code != 200:
        return None
    return respuesta.text


def main():
    conexion = sqlite3.connect("futtrivia.db")
    total_nuevos = 0
    total_existian = 0
    total_fallidos = 0

    print("=== Descargando Liga MX + Segunda División (2010-2025) ===")
    for temporada in TEMPORADAS_MEXICO:
        for archivo in construir_nombres_archivo_mexico(temporada):
            url = f"https://raw.githubusercontent.com/openfootball/world/master/north-america/mexico/{archivo}"
            anio = temporada.split("-")[0]
            contenido = descargar_archivo_txt(url)

            if contenido is None:
                continue  # normal: algunos nombres no existen para esa temporada, los saltamos sin avisar

            partidos = parsear_football_txt(contenido, anio)
            nuevos, existian = guardar_partidos_txt(conexion, f"mexico-txt/{archivo}", partidos)
            total_nuevos += nuevos
            total_existian += existian
            print(f"  {archivo}: {len(partidos)} partidos encontrados, {nuevos} nuevos")
            time.sleep(0.2)

    print("\n=== Descargando Liga Argentina (2018-2025) ===")
    for archivo in ARCHIVOS_ARGENTINA:
        url = f"https://raw.githubusercontent.com/openfootball/south-america/master/argentina/{archivo}"
        anio = archivo.split("_")[0]
        contenido = descargar_archivo_txt(url)

        if contenido is None:
            print(f"  No se encontró: {archivo}")
            total_fallidos += 1
            continue

        partidos = parsear_football_txt(contenido, anio)
        nuevos, existian = guardar_partidos_txt(conexion, f"argentina-txt/{archivo}", partidos)
        total_nuevos += nuevos
        total_existian += existian
        print(f"  {archivo}: {len(partidos)} partidos encontrados, {nuevos} nuevos")
        time.sleep(0.2)

    conexion.close()

    print(f"\n¡Listo!")
    print(f"Partidos nuevos: {total_nuevos}")
    print(f"Ya existían: {total_existian}")
    print(f"Archivos no encontrados: {total_fallidos}")


if __name__ == "__main__":
    main()