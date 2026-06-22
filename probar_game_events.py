import requests
import gzip
import csv
import io

URL = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/game_events.csv.gz"

print("Descargando...")
respuesta = requests.get(URL)
print(f"Status code: {respuesta.status_code}")

if respuesta.status_code != 200:
    print("No se encontró.")
else:
    print(f"Tamaño: {len(respuesta.content) / 1024 / 1024:.2f} MB")
    contenido = gzip.decompress(respuesta.content).decode("utf-8")
    lector = csv.DictReader(io.StringIO(contenido))
    print(f"\nColumnas ({len(lector.fieldnames)}):")
    for c in lector.fieldnames:
        print(f"  - {c}")
    print("\nPrimeras 3 filas:")
    for i, fila in enumerate(lector):
        if i >= 3:
            break
        print(fila)
        