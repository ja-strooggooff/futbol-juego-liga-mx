import requests
import gzip
import csv
import io

URL = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/competitions.csv.gz"

print("Descargando...")
respuesta = requests.get(URL)
print(f"Status code: {respuesta.status_code}")

if respuesta.status_code != 200:
    print("No se encontró en esa ruta. Puede que el nombre del archivo sea distinto.")
else:
    print(f"Tamaño descargado: {len(respuesta.content) / 1024:.2f} KB")

    contenido_descomprimido = gzip.decompress(respuesta.content)
    texto_csv = contenido_descomprimido.decode("utf-8")

    lector = csv.DictReader(io.StringIO(texto_csv))
    columnas = lector.fieldnames
    print(f"\nColumnas disponibles ({len(columnas)}):")
    for c in columnas:
        print(f"  - {c}")

    print("\nPrimeras 5 filas:")
    for i, fila in enumerate(lector):
        if i >= 5:
            break
        print(fila)