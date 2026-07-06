# Diagnóstico de duplicados: fuentes nuevas de selecciones

Fecha del diagnóstico: 2026-07-06
Script: `diagnostico_duplicados_selecciones.py`

Antes de importar las 2 fuentes nuevas a `futtrivia.db` se contaron los
partidos que ya existían en las tablas `games` y `partidos`, comparando por
**fecha + pareja de equipos** (sin importar orden local/visitante, nombres
normalizados a minúsculas).

## Estado de la base antes de importar

| Tabla    | Partidos |
|----------|----------|
| games    | 88,808   |
| partidos | 99,048 llaves distintas (101,417 filas) |

## Fuente 1: martj42/international_results (results.csv)

Resultados de partidos de selecciones nacionales desde 1872.

| Métrica | Valor |
|---------|-------|
| Partidos distintos en la fuente | 49,486 (49,503 filas; las de más son partidos futuros repetidos/sin marcador) |
| Duplicados contra `games` | 618 |
| Duplicados contra `partidos` | 955 |
| Duplicados contra alguna de las dos | 1,189 |
| **Partidos NUEVOS** | **48,297 (97.6%)** |

## Fuente 2: jfjelstul/worldcup (player_appearances.csv)

Apariciones de jugadores en Mundiales masculinos y femeninos. El CSV tiene
una fila **por jugador por partido** (27,432 filas); para el diagnóstico se
extrajeron los partidos distintos.

| Métrica | Valor |
|---------|-------|
| Partidos distintos en la fuente | 1,015 |
| Duplicados contra `games` | 315 |
| Duplicados contra `partidos` | 712 |
| Duplicados contra alguna de las dos | 735 |
| **Partidos NUEVOS** | **280 (27.6%)** |

Que la mayoría de los partidos de Mundial ya existan es esperado: la tabla
`partidos` ya tenía los Mundiales de openfootball. Lo que esta fuente aporta
de verdad son las **alineaciones/apariciones de jugadores**, que no existían
para selecciones (la tabla `appearances` actual solo cubre partidos de clubes).

## Limitación de la comparación

La llave usa el nombre exacto normalizado del equipo. Si dos fuentes escriben
distinto al mismo país (p. ej. `USA` vs `United States`, `Germany DR` vs
`East Germany`), el partido cuenta como nuevo aunque sea el mismo. Los conteos
de duplicados son por lo tanto un piso, no un techo.

## Decisión de integración

- Los resultados de martj42 se guardan en una tabla nueva
  `resultados_internacionales` (no se mezclan con `partidos`, que conserva su
  fuente openfootball); la tabla tiene UNIQUE(fecha, equipo_local,
  equipo_visitante) para poder re-correr el importador sin duplicar.
- Las apariciones de jfjelstul se guardan en la tabla nueva
  `apariciones_mundial`, separada de `appearances` (clubes) porque el esquema
  es distinto (torneo, fase, titular/suplente, dorsal).
- El traslape documentado arriba queda registrado aquí para cuando se quiera
  cruzar tablas (evitar contar dos veces el mismo partido).

## Resultado de la importación (2026-07-06)

| Tabla nueva | Filas importadas | Detalle |
|-------------|------------------|---------|
| `resultados_internacionales` | 49,501 | 1872-11-30 a 2026-07-11; 49,495 con marcador (las 6 sin marcador son partidos futuros); 2 filas del CSV eran duplicados exactos y el UNIQUE las descartó |
| `apariciones_mundial` | 27,432 | 6,559 jugadores distintos; 14 Mundiales masculinos (1970–2022) y 7 femeninos (1991–2019); la fuente no trae alineaciones anteriores a 1970 |

Scripts: `importar_resultados_internacionales.py` e
`importar_apariciones_mundial.py`. Ambos son re-ejecutables sin duplicar
(UNIQUE + INSERT OR IGNORE).
