"""
03_procesamiento_carga.py
================================================================================
PROCESO ETL: EXTRACCION, TRANSFORMACION Y CARGA
Investigacion: Puntualidad y regularidad operativa, julio-septiembre de 2017.
Escuela de Estadistica y Ciencias Actuariales (EECA-UCV) — Computacion II
================================================================================

PROPOSITO
---------
Migrar los 33.121 vuelos de la tabla `flights` al esquema normalizado y calcular
las medidas de puntualidad, que la fuente NO contiene: solo aporta cuatro sellos
de tiempo y de ellos hay que derivar demoras, recuperacion y duraciones.

TRANSFORMACIONES APLICADAS
--------------------------
 T1. DEPURACION DE NULOS DISFRAZADOS. Las horas reales de los vuelos aun no
     operados no son NULL: contienen la cadena literal `\\N`, marcador de nulo
     de los volcados de PostgreSQL. Se convierten a NULL real. Sin este paso,
     `julianday('\\N')` devuelve NULL en silencio y las demoras salen vacias sin
     que nada avise.

 T2. NORMALIZACION DE LOS SELLOS DE TIEMPO. Llegan como
     '2017-07-16 01:50:00+03', con el desplazamiento horario pegado al final.
     Se recorta a los 19 primeros caracteres. Es correcto porque TODOS los
     sellos de la base comparten el mismo desplazamiento (+03), extremo que se
     verifico antes de decidirlo: no hay mezcla de husos que corregir.

 T3. CALCULO DE LAS DEMORAS. Diferencia en minutos entre el sello real y el
     programado, mediante `julianday`, que devuelve dias decimales y se
     multiplica por 1.440.

 T4. RECUPERACION EN RUTA. Demora de salida menos demora de llegada. Positiva
     si el vuelo recorto tiempo en el aire; negativa si lo perdio.

 T5. ASIGNACION DEL REGIMEN. Segun los cortes declarados en el catalogo, de
     modo que la clasificacion del ETL y la definicion del catalogo no puedan
     divergir.

 T6. RELACION 1:0..1. Solo los vuelos con salida real generan fila en
     `metricas_puntualidad`. Los demas se cargan igualmente en `vuelos` con
     `tiene_metricas = 0`, para poder medir que porcion de la programacion se
     ejecuto.

ORDEN DE EJECUCION: tercero, despues de 01 y 02.
"""

import os
import sqlite3 as sql

DB_DESTINO = 'puntualidad_vuelos_2017.db'
DB_ORIGEN = os.environ.get('TRAVEL_DB_PATH', '../../travel.sqlite')

# Marcador de nulo que arrastran los volcados de PostgreSQL.
NULO_POSTGRES = r'\N'


def limpiar_sello(valor):
    """
    Convierte un sello de tiempo de la fuente en texto ISO, o None.

    Aplica las transformaciones T1 y T2: descarta el marcador de nulo y recorta
    el desplazamiento horario.
    """
    if valor is None or valor == NULO_POSTGRES:
        return None
    return valor[:19]


def franja_de(hora):
    """Traduce la hora del dia al franja_id del catalogo."""
    if hora <= 5:
        return 1
    if hora <= 11:
        return 2
    if hora <= 15:
        return 3
    if hora <= 19:
        return 4
    return 5


def regimen_de(demora):
    """
    Traduce la demora de salida al regimen_id del catalogo.

    Los cortes replican exactamente los limites declarados en el script 02.
    """
    if demora <= 0:
        return 1
    if demora <= 5:
        return 2
    if demora <= 15:
        return 3
    if demora <= 59:
        return 4
    return 5


def procesar_y_cargar():
    """Ejecuta el ETL completo."""
    if not os.path.exists(DB_ORIGEN):
        raise FileNotFoundError(
            f"No se encontro la base original en '{DB_ORIGEN}'. Descarguela de "
            "Kaggle o indique la ruta con la variable de entorno TRAVEL_DB_PATH.")

    conn_origen = sql.connect(DB_ORIGEN)
    conn_destino = sql.connect(DB_DESTINO)
    conn_destino.execute("PRAGMA foreign_keys = ON;")
    conn_destino.execute("PRAGMA journal_mode = WAL;")
    conn_destino.execute("PRAGMA synchronous = OFF;")

    estados = dict(conn_destino.execute(
        "SELECT codigo, estado_id FROM estados_vuelo").fetchall())

    # El calculo de las diferencias se delega al motor de origen: julianday
    # trabaja sobre los sellos ya recortados y devuelve dias decimales.
    consulta = r"""
        SELECT
            flight_id,
            flight_no,
            substr(scheduled_departure, 1, 19) AS salida_prog,
            substr(scheduled_arrival, 1, 19)   AS llegada_prog,
            CASE WHEN actual_departure = '\N' THEN NULL
                 ELSE substr(actual_departure, 1, 19) END AS salida_real,
            CASE WHEN actual_arrival = '\N' THEN NULL
                 ELSE substr(actual_arrival, 1, 19) END   AS llegada_real,
            departure_airport,
            arrival_airport,
            aircraft_code,
            status
        FROM flights
        ORDER BY flight_id
    """

    print("Leyendo la programacion de vuelos...")
    filas = conn_origen.execute(consulta).fetchall()
    conn_origen.close()

    vuelos, metricas = [], []
    sin_operar = cancelados = 0

    for (vid, numero, salida_prog, llegada_prog, salida_real, llegada_real,
         origen, destino, aeronave, estado) in filas:

        fecha = salida_prog[:10]
        hora = int(salida_prog[11:13])
        estado_id = estados[estado]
        opera = salida_real is not None

        vuelos.append((vid, numero, fecha, hora, franja_de(hora), origen, destino,
                       aeronave, estado_id, salida_prog, llegada_prog,
                       salida_real, llegada_real, 1 if opera else 0))

        if not opera:
            sin_operar += 1
            if estado == 'Cancelled':
                cancelados += 1
            continue

        # --- T3, T4 y T5: medidas de puntualidad ---------------------------
        cur = conn_destino.execute(
            "SELECT (julianday(?) - julianday(?)) * 1440, "
            "       (julianday(?) - julianday(?)) * 1440, "
            "       (julianday(?) - julianday(?)) * 1440, "
            "       (julianday(?) - julianday(?)) * 1440",
            (salida_real, salida_prog,
             llegada_real or salida_real, llegada_prog,
             llegada_prog, salida_prog,
             llegada_real or salida_real, salida_real))
        d_salida, d_llegada, dur_prog, dur_real = cur.fetchone()

        d_salida = int(round(d_salida))
        hay_llegada = llegada_real is not None
        d_llegada = int(round(d_llegada)) if hay_llegada else None
        dur_prog = int(round(dur_prog))
        dur_real = int(round(dur_real)) if hay_llegada else None
        recuperacion = (d_salida - d_llegada) if hay_llegada else None

        metricas.append((vid, regimen_de(d_salida), d_salida, d_llegada,
                         recuperacion, dur_prog, dur_real,
                         1 if d_salida <= 15 else 0))

    print(f"Cargando {len(vuelos):,} vuelos y {len(metricas):,} juegos de metricas...")
    conn_destino.executemany(
        "INSERT OR REPLACE INTO vuelos (vuelo_id, numero_vuelo, fecha_programada, "
        "hora_programada, franja_id, origen, destino, aircraft_code, estado_id, "
        "salida_programada, llegada_programada, salida_real, llegada_real, "
        "tiene_metricas) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", vuelos)
    conn_destino.executemany(
        "INSERT OR REPLACE INTO metricas_puntualidad (vuelo_id, regimen_id, "
        "demora_salida_min, demora_llegada_min, recuperacion_min, "
        "duracion_programada_min, duracion_real_min, puntual) "
        "VALUES (?,?,?,?,?,?,?,?)", metricas)
    conn_destino.commit()
    conn_destino.close()

    print("-" * 72)
    print(f"Vuelos programados          : {len(vuelos):,}")
    print(f"Operados (con salida real)  : {len(metricas):,} "
          f"({len(metricas)/len(vuelos)*100:.2f}%)")
    print(f"Sin operar en el corte      : {sin_operar:,} "
          f"({sin_operar/len(vuelos)*100:.2f}%)")
    print(f"   de los cuales cancelados : {cancelados:,}")


def verificar_integridad():
    """
    Control de calidad posterior a la carga.

    Un ETL sin verificacion no es un ETL: es una esperanza.
    """
    conn = sql.connect(DB_DESTINO)
    print("\nVERIFICACION DE INTEGRIDAD")
    print("-" * 72)
    controles = {
        "Vuelos cargados":
            "SELECT COUNT(*) FROM vuelos",
        "Metricas de puntualidad":
            "SELECT COUNT(*) FROM metricas_puntualidad",
        "Vuelos marcados con metricas":
            "SELECT COUNT(*) FROM vuelos WHERE tiene_metricas = 1",
        "Vuelos sin aeropuerto de origen valido (debe ser 0)":
            "SELECT COUNT(*) FROM vuelos v LEFT JOIN aeropuertos a "
            "ON v.origen = a.airport_code WHERE a.airport_code IS NULL",
        "Vuelos sin aeropuerto de destino valido (debe ser 0)":
            "SELECT COUNT(*) FROM vuelos v LEFT JOIN aeropuertos a "
            "ON v.destino = a.airport_code WHERE a.airport_code IS NULL",
        "Vuelos sin aeronave valida (debe ser 0)":
            "SELECT COUNT(*) FROM vuelos v LEFT JOIN aeronaves n "
            "ON v.aircraft_code = n.aircraft_code WHERE n.aircraft_code IS NULL",
        "Vuelos sin fecha en el calendario (debe ser 0)":
            "SELECT COUNT(*) FROM vuelos v LEFT JOIN calendario_operativo c "
            "ON v.fecha_programada = c.fecha WHERE c.fecha IS NULL",
        "Metricas huerfanas (debe ser 0)":
            "SELECT COUNT(*) FROM metricas_puntualidad m LEFT JOIN vuelos v "
            "ON m.vuelo_id = v.vuelo_id WHERE v.vuelo_id IS NULL",
        "Incoherencias bandera/metricas (debe ser 0)":
            "SELECT COUNT(*) FROM vuelos v LEFT JOIN metricas_puntualidad m "
            "ON v.vuelo_id = m.vuelo_id "
            "WHERE (v.tiene_metricas = 1 AND m.vuelo_id IS NULL) "
            "   OR (v.tiene_metricas = 0 AND m.vuelo_id IS NOT NULL)",
        "Demoras de salida negativas (debe ser 0)":
            "SELECT COUNT(*) FROM metricas_puntualidad WHERE demora_salida_min < 0",
    }
    for etiqueta, consulta in controles.items():
        print(f"   {etiqueta:<52} {conn.execute(consulta).fetchone()[0]:>10,}")
    conn.close()


if __name__ == "__main__":
    print("=" * 72)
    print("ETL — PUNTUALIDAD DE VUELOS DOMESTICOS 2017")
    print("=" * 72)
    procesar_y_cargar()
    verificar_integridad()
