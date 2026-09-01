"""
generar_extractos.py
================================================================================
GENERACION DE LOS EXTRACTOS PARA EL TABLERO DE TABLEAU
Investigacion: Puntualidad y regularidad operativa de vuelos domesticos, 2017.
Escuela de Estadistica y Ciencias Actuariales (EECA-UCV) — Computacion II
================================================================================

POR QUE EXTRACTOS AGREGADOS Y NO EL DATO CRUDO
----------------------------------------------
Tableau podria conectarse directamente a los 33.121 vuelos del Data Lake. No se
hace, por tres razones:

  1. RENDIMIENTO EN EL TABLERO. Cada interaccion del usuario reevalua las
     consultas. Sobre un extracto agregado la latencia es imperceptible.

  2. PORTABILIDAD. Un CSV se abre en cualquier instalacion de Tableau, incluida
     Tableau Public, sin conectores ni controladores adicionales.

  3. GRANULARIDAD SUFICIENTE. El tablero nunca desciende al vuelo individual:
     su unidad minima de lectura es la combinacion fecha-franja-modelo-estado o
     fecha-franja-modelo-regimen. Agregar a ese nivel no pierde ninguna
     informacion que el tablero necesite.

LA ESTRUCTURA DE DOS EXTRACTOS REPRODUCE LA DEL MODELO
------------------------------------------------------
El modelo de datos tiene dos tablas de hechos en relacion 1:0..1: `vuelos`
(programacion completa) y `metricas_puntualidad` (solo los operados). Los
extractos respetan esa misma separacion:

  * programacion.csv : todos los vuelos, operados o no. Responde "cuanto de lo
                       programado llega a volar".
  * puntualidad.csv  : solo los operados. Responde "como se comporta en el
                       tiempo lo que si vuela".

Mezclarlos produciria denominadores equivocados: una tasa de puntualidad
calculada sobre la programacion total estaria dividida por un universo que
incluye vuelos que nunca despegaron.

LA REGLA DE ORO DE LA AGREGACION
--------------------------------
Los extractos almacenan SUMAS y CONTEOS, nunca PROMEDIOS.

El promedio de un conjunto de promedios NO es el promedio del conjunto, salvo
que todos los grupos tengan el mismo tamano. Si el extracto guardara
`demora_promedio` por fila, cualquier agregacion posterior en Tableau —por dia,
por modelo, por franja— produciria una media NO PONDERADA y por tanto
incorrecta.

Almacenando `N operados` y `Minutos de demora`, Tableau reconstruye la media
correcta en cualquier nivel con `SUM([Minutos de demora]) / SUM([N operados])`.
Esta es la razon por la que todos los campos calculados del libro son cocientes
de sumas y ninguno usa AVG().

SALIDA
------
Cuatro archivos en la carpeta `extractos/`:
  * programacion.csv  : cobertura de la programacion (fuente de la pagina 1)
  * puntualidad.csv   : desempeno temporal de los operados (paginas 2 y 3)
  * aeropuertos.csv   : un punto por aeropuerto, para el mapa
  * rutas_criticas.csv: las veinte rutas que mas minutos de demora acumulan
"""

import os
import duckdb

DIRECTORIO_BASE = os.path.dirname(os.path.abspath(__file__))
DIRECTORIO_DATA = os.path.abspath(os.path.join(DIRECTORIO_BASE, "..", "data"))
DIRECTORIO_SALIDA = os.path.join(DIRECTORIO_BASE, "extractos")


def abrir_conexion():
    """Conexion DuckDB con una vista por cada Parquet del Data Lake."""
    conexion = duckdb.connect()
    for archivo in sorted(os.listdir(DIRECTORIO_DATA)):
        if archivo.endswith(".parquet"):
            nombre = archivo[:-8]
            ruta = os.path.join(DIRECTORIO_DATA, archivo)
            conexion.execute(
                f"CREATE OR REPLACE VIEW {nombre} AS "
                f"SELECT * FROM read_parquet('{ruta}')")
    return conexion


def exportar(conexion, nombre_archivo, consulta):
    """Ejecuta la consulta y escribe el CSV, informando filas y tamano."""
    ruta = os.path.join(DIRECTORIO_SALIDA, nombre_archivo)
    conexion.execute(
        f"COPY ({consulta}) TO '{ruta}' (HEADER, DELIMITER ',')")
    filas = conexion.execute(f"SELECT COUNT(*) FROM ({consulta})").fetchone()[0]
    tam = os.path.getsize(ruta) / 1024
    print(f"{nombre_archivo:<24}{filas:>12,}{tam:>10,.0f} KB")


# ==============================================================================
# EXTRACTO 1 — COBERTURA DE LA PROGRAMACION
# ==============================================================================
# Grano: fecha x franja x modelo x estado x ruta.
#
# Incluye TODOS los vuelos. `N vuelos` es el denominador de cualquier tasa de
# cobertura o de cancelacion; `N operados` y `N cancelados` son los numeradores.
CONSULTA_PROGRAMACION = """
    SELECT
        v.fecha_programada                                  AS "Fecha",
        c.nombre_mes                                        AS "Mes",
        c.nombre_dia                                        AS "Dia",
        c.dia_semana                                        AS "Orden de dia",
        CASE WHEN c.es_fin_semana = 1 THEN 'Fin de semana'
             ELSE 'Dia laborable' END                       AS "Tipo de dia",
        f.etiqueta                                          AS "Franja",
        f.orden                                             AS "Orden de franja",
        a.modelo                                            AS "Aeronave",
        a.categoria_alcance                                 AS "Alcance",
        a.asientos                                          AS "Asientos",
        e.codigo                                            AS "Estado",
        e.descripcion                                       AS "Estado descrito",
        v.origen                                            AS "Origen",
        v.destino                                           AS "Destino",
        v.origen || ' - ' || v.destino                      AS "Ruta",
        COUNT(*)                                            AS "N vuelos",
        SUM(v.tiene_metricas)                               AS "N operados",
        SUM(CASE WHEN e.codigo = 'Cancelled' THEN 1 ELSE 0 END)
                                                            AS "N cancelados"
    FROM vuelos v
    JOIN calendario_operativo c ON v.fecha_programada = c.fecha
    JOIN franjas_horarias      f ON v.franja_id       = f.franja_id
    JOIN aeronaves             a ON v.aircraft_code   = a.aircraft_code
    JOIN estados_vuelo         e ON v.estado_id       = e.estado_id
    GROUP BY ALL
"""


# ==============================================================================
# EXTRACTO 2 — DESEMPENO TEMPORAL DE LOS VUELOS OPERADOS
# ==============================================================================
# Grano: fecha x franja x modelo x regimen x ruta. Solo vuelos con salida real.
#
# Las medidas son SUMAS de minutos y CONTEOS de vuelos, nunca promedios. La
# columna `N con llegada` existe porque 58 vuelos despegaron pero no habian
# aterrizado al cierre de la base: son el denominador correcto de la
# recuperacion y de la duracion real, distinto del de la demora de salida.
CONSULTA_PUNTUALIDAD = """
    SELECT
        v.fecha_programada                                  AS "Fecha",
        c.nombre_mes                                        AS "Mes",
        c.nombre_dia                                        AS "Dia",
        c.dia_semana                                        AS "Orden de dia",
        CASE WHEN c.es_fin_semana = 1 THEN 'Fin de semana'
             ELSE 'Dia laborable' END                       AS "Tipo de dia",
        f.etiqueta                                          AS "Franja",
        f.orden                                             AS "Orden de franja",
        a.modelo                                            AS "Aeronave",
        a.categoria_alcance                                 AS "Alcance",
        r.etiqueta                                          AS "Regimen",
        r.orden                                             AS "Orden de regimen",
        v.origen                                            AS "Origen",
        v.destino                                           AS "Destino",
        v.origen || ' - ' || v.destino                      AS "Ruta",
        COUNT(*)                                            AS "N operados",
        SUM(m.puntual)                                      AS "N puntuales",
        SUM(m.demora_salida_min)                            AS "Minutos de demora",
        SUM(CASE WHEN m.demora_llegada_min IS NOT NULL THEN 1 ELSE 0 END)
                                                            AS "N con llegada",
        COALESCE(SUM(m.recuperacion_min), 0)                AS "Minutos recuperados",
        SUM(m.duracion_programada_min)                      AS "Minutos programados",
        COALESCE(SUM(m.duracion_real_min), 0)               AS "Minutos reales"
    FROM metricas_puntualidad m
    JOIN vuelos                v ON m.vuelo_id        = v.vuelo_id
    JOIN calendario_operativo  c ON v.fecha_programada = c.fecha
    JOIN franjas_horarias      f ON v.franja_id       = f.franja_id
    JOIN aeronaves             a ON v.aircraft_code   = a.aircraft_code
    JOIN regimenes_puntualidad r ON m.regimen_id      = r.regimen_id
    GROUP BY ALL
"""


# ==============================================================================
# EXTRACTO 3 — AEROPUERTOS PARA EL MAPA
# ==============================================================================
# Un punto por aeropuerto, con sus coordenadas depuradas y el trafico y la
# demora acumulados. El mapa colorea por demora media y dimensiona por trafico.
#
# `Id aeropuerto` es un identificador de fila que el libro usa como nivel de
# detalle: sin el, Tableau colapsa las 104 marcas en una sola.
CONSULTA_AEROPUERTOS = """
    SELECT
        ROW_NUMBER() OVER (ORDER BY "Codigo")               AS "Id aeropuerto",
        *
    FROM (
        SELECT
            p.airport_code                                  AS "Codigo",
            p.ciudad                                        AS "Ciudad",
            p.nombre                                        AS "Aeropuerto",
            p.longitud                                      AS "Longitud",
            p.latitud                                       AS "Latitud",
            COUNT(*)                                        AS "N vuelos",
            SUM(v.tiene_metricas)                           AS "N operados",
            COALESCE(SUM(m.demora_salida_min), 0)           AS "Minutos de demora",
            COALESCE(SUM(m.puntual), 0)                     AS "N puntuales"
        FROM vuelos v
        JOIN aeropuertos p ON v.origen = p.airport_code
        LEFT JOIN metricas_puntualidad m ON v.vuelo_id = m.vuelo_id
        GROUP BY ALL
    )
    ORDER BY "N vuelos" DESC
"""


# ==============================================================================
# EXTRACTO 4 — LAS VEINTE RUTAS QUE MAS DEMORA ACUMULAN
# ==============================================================================
# Grano: ruta x regimen, restringido a las veinte rutas con mas minutos de demora.
#
# El recorte se hace AQUI y no en el libro por una razon de legibilidad: la red
# tiene 457 rutas, y un grafico de barras con 457 categorias no se lee. Tableau
# permitiria un filtro de N superiores, pero ese filtro se evaluaria en cada
# interaccion y ademas quedaria oculto para quien inspeccione el extracto.
# Dejandolo escrito en SQL, el criterio de seleccion es explicito y auditable.
CONSULTA_RUTAS = """
    WITH por_ruta AS (
        SELECT v.origen || ' - ' || v.destino AS ruta,
               SUM(m.demora_salida_min)       AS minutos
        FROM metricas_puntualidad m
        JOIN vuelos v ON m.vuelo_id = v.vuelo_id
        GROUP BY 1
        ORDER BY minutos DESC
        LIMIT 20
    )
    SELECT
        v.origen || ' - ' || v.destino                       AS "Ruta",
        po.ciudad                                            AS "Ciudad de origen",
        pd.ciudad                                            AS "Ciudad de destino",
        r.etiqueta                                           AS "Regimen",
        r.orden                                              AS "Orden de regimen",
        a.modelo                                             AS "Aeronave",
        COUNT(*)                                             AS "N operados",
        SUM(m.puntual)                                       AS "N puntuales",
        SUM(m.demora_salida_min)                             AS "Minutos de demora"
    FROM metricas_puntualidad m
    JOIN vuelos                v  ON m.vuelo_id       = v.vuelo_id
    JOIN aeropuertos           po ON v.origen         = po.airport_code
    JOIN aeropuertos           pd ON v.destino        = pd.airport_code
    JOIN aeronaves             a  ON v.aircraft_code  = a.aircraft_code
    JOIN regimenes_puntualidad r  ON m.regimen_id     = r.regimen_id
    WHERE v.origen || ' - ' || v.destino IN (SELECT ruta FROM por_ruta)
    GROUP BY ALL
"""


# ==============================================================================
# BLOQUE DE EJECUCION
# ==============================================================================
if __name__ == "__main__":
    print("=" * 62)
    print("GENERACION DE EXTRACTOS PARA TABLEAU")
    print("=" * 62)

    os.makedirs(DIRECTORIO_SALIDA, exist_ok=True)
    conexion = abrir_conexion()

    print(f"{'ARCHIVO':<24}{'FILAS':>12}{'TAMANO':>13}")
    print("-" * 62)
    exportar(conexion, "programacion.csv", CONSULTA_PROGRAMACION)
    exportar(conexion, "puntualidad.csv", CONSULTA_PUNTUALIDAD)
    exportar(conexion, "aeropuertos.csv", CONSULTA_AEROPUERTOS)
    exportar(conexion, "rutas_criticas.csv", CONSULTA_RUTAS)
    print("-" * 62)

    # --------------------------------------------------------------------
    # CONTROL DE CONSISTENCIA
    # --------------------------------------------------------------------
    # Los extractos agregados deben reproducir EXACTAMENTE los totales del Data
    # Lake. Si no lo hicieran, el tablero mostraria cifras distintas a las del
    # aplicativo de Streamlit, y no habria forma de saber cual de los dos miente.
    lago = conexion.execute("""
        SELECT (SELECT COUNT(*) FROM vuelos),
               (SELECT SUM(tiene_metricas) FROM vuelos),
               (SELECT SUM(demora_salida_min) FROM metricas_puntualidad),
               (SELECT SUM(puntual) FROM metricas_puntualidad)
    """).fetchone()
    prog = conexion.execute(
        f'SELECT SUM("N vuelos"), SUM("N operados") '
        f"FROM ({CONSULTA_PROGRAMACION})").fetchone()
    punt = conexion.execute(
        f'SELECT SUM("Minutos de demora"), SUM("N puntuales"), SUM("N operados") '
        f"FROM ({CONSULTA_PUNTUALIDAD})").fetchone()
    mapa = conexion.execute(
        f'SELECT SUM("N vuelos") FROM ({CONSULTA_AEROPUERTOS})').fetchone()

    controles = [
        ("Vuelos programados",  lago[0], prog[0]),
        ("Vuelos operados",     lago[1], prog[1]),
        ("Vuelos operados",     lago[1], punt[2]),
        ("Minutos de demora",   lago[2], punt[0]),
        ("Vuelos puntuales",    lago[3], punt[1]),
        ("Vuelos en el mapa",   lago[0], mapa[0]),
    ]

    print("CONTROL DE CONSISTENCIA")
    print(f"   {'CONCEPTO':<24}{'DATA LAKE':>14}{'EXTRACTO':>14}{'':>8}")
    todo_bien = True
    for concepto, esperado, obtenido in controles:
        coincide = int(esperado) == int(obtenido)
        todo_bien = todo_bien and coincide
        marca = "OK" if coincide else "DISCREPA"
        print(f"   {concepto:<24}{int(esperado):>14,}{int(obtenido):>14,}{marca:>8}")
    print(f"\n   RESULTADO: {'TODOS LOS TOTALES COINCIDEN' if todo_bien else 'HAY DISCREPANCIAS'}")

    conexion.close()
