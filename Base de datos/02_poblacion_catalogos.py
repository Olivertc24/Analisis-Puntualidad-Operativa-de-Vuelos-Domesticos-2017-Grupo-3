"""
02_poblacion_catalogos.py
================================================================================
POBLACION DE LAS DIMENSIONES (CATALOGOS)
Investigacion: Puntualidad y regularidad operativa, julio-septiembre de 2017.
Escuela de Estadistica y Ciencias Actuariales (EECA-UCV) — Computacion II
================================================================================

Se distinguen dos clases de catalogo:

  A) CONSTRUIDOS POR LA INVESTIGACION, escritos explicitamente aqui porque no
     existen en la fuente: los regimenes de puntualidad, las franjas horarias y
     la descripcion de los estados de vuelo. Declararlos en codigo deja
     constancia del criterio y, gracias a las llaves foraneas, los convierte en
     una regla de validacion: si el ETL encontrara un valor no previsto, la
     carga lo rechazaria.

  B) EXTRAIDOS DE LA FUENTE, que se copian y depuran desde travel.sqlite:
     aeropuertos, aeronaves y el calendario operativo. Aqui esta el trabajo de
     limpieza de los campos JSON y de las coordenadas en texto.

ORDEN DE EJECUCION: segundo, despues de 01_creacion_esquema.py.
"""

import json
import os
import sqlite3 as sql

DB_DESTINO = 'puntualidad_vuelos_2017.db'

# Base original descargada de Kaggle. Por su tamano (109 MB) no se versiona.
DB_ORIGEN = os.environ.get('TRAVEL_DB_PATH', '../../travel.sqlite')


def abrir_conexion():
    conn = sql.connect(DB_DESTINO)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def abrir_origen():
    if not os.path.exists(DB_ORIGEN):
        raise FileNotFoundError(
            f"No se encontro la base original en '{DB_ORIGEN}'. Descarguela de "
            "Kaggle o indique la ruta con la variable de entorno TRAVEL_DB_PATH.")
    return sql.connect(DB_ORIGEN)


# ==============================================================================
# A. CATALOGOS CONSTRUIDOS POR LA INVESTIGACION
# ==============================================================================

def poblar_estados():
    """
    Estados del vuelo, con la bandera que define el universo de analisis.

    'es_operado' vale 1 solo para los vuelos que llegaron a ejecutarse. Los
    programados a futuro y los cancelados no producen metricas de puntualidad,
    pero SI se cargan en la tabla de hechos: la proporcion de la programacion
    que se ejecuta es un resultado del estudio.
    """
    datos = [
        (1, 'Arrived',   'Vuelo operado y finalizado',                  1, 1),
        (2, 'Departed',  'Vuelo en curso: salio pero aun no aterriza',  1, 2),
        (3, 'On Time',   'Vuelo proximo, sin demora anunciada',         0, 3),
        (4, 'Scheduled', 'Vuelo programado a futuro',                   0, 4),
        (5, 'Delayed',   'Vuelo proximo con demora anunciada',          0, 5),
        (6, 'Cancelled', 'Vuelo cancelado: no se opero',                0, 6),
    ]
    conn = abrir_conexion()
    conn.executemany("INSERT OR REPLACE INTO estados_vuelo "
                     "(estado_id, codigo, descripcion, es_operado, orden) "
                     "VALUES (?, ?, ?, ?, ?)", datos)
    conn.commit(); conn.close()
    print(f"[OK] estados_vuelo: {len(datos)} estados cargados.")


def poblar_regimenes():
    """
    Regimenes de puntualidad. Es la variable segmentadora de la investigacion.

    CRITERIO DE CORTE (declarado por transparencia metodologica)
    -----------------------------------------------------------
    Los limites se fijaron a partir de la distribucion empirica observada en la
    propia base, no por convencion externa. Esa distribucion resulto ser
    BIMODAL: de los 16.773 vuelos operados, 15.973 salen entre 0 y 9 minutos
    despues de lo previsto y 800 lo hacen entre 180 y 277 minutos. En el tramo
    intermedio, de 10 a 179 minutos, no hay practicamente ningun vuelo.

    Se emplea ademas el umbral de 15 minutos como frontera de 'puntual', que es
    el estandar habitual del sector para el indicador de puntualidad.
    """
    datos = [
        (1, 'Salida puntual',      0,   0,    'Sale a la hora programada o antes',       1),
        (2, 'Demora minima',       1,   5,    'Entre 1 y 5 minutos de demora',           2),
        (3, 'Demora leve',         6,   15,   'Entre 6 y 15 minutos: aun dentro del '
                                              'umbral de puntualidad del sector',        3),
        (4, 'Demora moderada',     16,  59,   'Entre 16 y 59 minutos',                   4),
        (5, 'Demora severa',       60,  None, 'Una hora o mas de demora',                5),
    ]
    conn = abrir_conexion()
    conn.executemany("INSERT OR REPLACE INTO regimenes_puntualidad "
                     "(regimen_id, etiqueta, limite_inf_min, limite_sup_min, "
                     "descripcion, orden) VALUES (?, ?, ?, ?, ?, ?)", datos)
    conn.commit(); conn.close()
    print(f"[OK] regimenes_puntualidad: {len(datos)} regimenes cargados.")


def poblar_franjas():
    """
    Franjas horarias de la salida programada.

    Se emplean cinco bloques operativos, no las 24 horas sueltas: el interes es
    describir el patron de la jornada (si la demora se acumula segun avanza el
    dia), y 24 categorias fragmentarian esa lectura sin anadir informacion.
    """
    datos = [
        (1, 'Madrugada (00-05)',  0,  5,  1),
        (2, 'Manana (06-11)',     6,  11, 2),
        (3, 'Mediodia (12-15)',   12, 15, 3),
        (4, 'Tarde (16-19)',      16, 19, 4),
        (5, 'Noche (20-23)',      20, 23, 5),
    ]
    conn = abrir_conexion()
    conn.executemany("INSERT OR REPLACE INTO franjas_horarias "
                     "(franja_id, etiqueta, hora_inicio, hora_fin, orden) "
                     "VALUES (?, ?, ?, ?, ?)", datos)
    conn.commit(); conn.close()
    print(f"[OK] franjas_horarias: {len(datos)} franjas cargadas.")


# ==============================================================================
# B. CATALOGOS EXTRAIDOS Y DEPURADOS DE LA FUENTE
# ==============================================================================

def poblar_aeropuertos():
    """
    Copia los 104 aeropuertos depurando los dos formatos heredados de PostgreSQL.

    TRANSFORMACIONES
    ----------------
    * El nombre y la ciudad llegan como documentos JSON con las claves "en" y
      "ru". Se extrae la version inglesa, que es la que usa el aplicativo.
    * Las coordenadas llegan como la representacion textual del tipo `point`:
      la cadena `(129.77099609375,62.0932998657226562)`. Se descompone en dos
      columnas numericas, longitud y latitud EN ESE ORDEN, que es el que usa
      PostgreSQL y el inverso del habitual en cartografia. Invertirlos situaria
      los aeropuertos rusos en el oceano Indico.
    """
    origen = abrir_origen()
    filas = origen.execute(
        "SELECT airport_code, airport_name, city, coordinates, timezone "
        "FROM airports_data").fetchall()
    origen.close()

    registros = []
    for codigo, nombre_json, ciudad_json, punto, zona in filas:
        nombre = json.loads(nombre_json)["en"]
        ciudad = json.loads(ciudad_json)["en"]
        longitud, latitud = (float(v) for v in punto.strip("()").split(","))
        registros.append((codigo, nombre, ciudad, zona, longitud, latitud))

    conn = abrir_conexion()
    conn.executemany("INSERT OR REPLACE INTO aeropuertos "
                     "(airport_code, nombre, ciudad, zona_horaria, longitud, latitud) "
                     "VALUES (?, ?, ?, ?, ?, ?)", registros)
    conn.commit(); conn.close()
    print(f"[OK] aeropuertos: {len(registros)} aeropuertos depurados.")


def poblar_aeronaves():
    """
    Copia el catalogo de aeronaves anadiendo capacidad y categoria de alcance.

    * El modelo tambien viene en JSON; se extrae la clave "en".
    * La capacidad no esta en el catalogo: se cuenta desde la tabla `seats`,
      que lista un asiento por fila.
    * 'categoria_alcance' es una clasificacion propia de la investigacion, para
      comparar la puntualidad entre bloques homogeneos.
    """
    origen = abrir_origen()
    modelos = origen.execute(
        "SELECT aircraft_code, model, range FROM aircrafts_data").fetchall()
    asientos = dict(origen.execute(
        "SELECT aircraft_code, COUNT(*) FROM seats GROUP BY 1").fetchall())
    origen.close()

    def categoria(alcance):
        if alcance < 3000:
            return "Regional"
        if alcance < 6000:
            return "Corto y medio alcance"
        return "Largo alcance"

    registros = [(codigo, json.loads(modelo)["en"], alcance,
                  categoria(alcance), asientos.get(codigo, 0))
                 for codigo, modelo, alcance in modelos]

    conn = abrir_conexion()
    conn.executemany("INSERT OR REPLACE INTO aeronaves "
                     "(aircraft_code, modelo, alcance_km, categoria_alcance, asientos) "
                     "VALUES (?, ?, ?, ?, ?)", registros)
    conn.commit(); conn.close()
    print(f"[OK] aeronaves: {len(registros)} modelos cargados.")


def poblar_calendario():
    """
    Construye el calendario operativo a partir de las fechas realmente
    observadas en la programacion de vuelos.

    Se genera desde el dato y no como un rango fijo, para que el calendario
    cubra exactamente el periodo cargado y ninguna fila de hechos quede sin su
    fecha correspondiente.
    """
    MESES = {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo',
             6: 'Junio', 7: 'Julio', 8: 'Agosto', 9: 'Septiembre',
             10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}
    DIAS = {0: 'Lunes', 1: 'Martes', 2: 'Miercoles', 3: 'Jueves',
            4: 'Viernes', 5: 'Sabado', 6: 'Domingo'}

    origen = abrir_origen()
    # substr(...,1,10) recorta la fecha del sello temporal con desplazamiento
    # horario: '2017-07-16 01:50:00+03' -> '2017-07-16'.
    fechas = [f[0] for f in origen.execute(
        "SELECT DISTINCT substr(scheduled_departure, 1, 10) FROM flights "
        "ORDER BY 1").fetchall()]
    origen.close()

    from datetime import date
    registros = []
    for texto in fechas:
        anio, mes, dia = (int(p) for p in texto.split("-"))
        d = date(anio, mes, dia)
        registros.append((texto, anio, mes, MESES[mes], d.weekday() + 1,
                          DIAS[d.weekday()], 1 if d.weekday() >= 5 else 0))

    conn = abrir_conexion()
    conn.executemany("INSERT OR REPLACE INTO calendario_operativo "
                     "(fecha, anio, mes, nombre_mes, dia_semana, nombre_dia, "
                     "es_fin_semana) VALUES (?, ?, ?, ?, ?, ?, ?)", registros)
    conn.commit(); conn.close()
    print(f"[OK] calendario_operativo: {len(registros)} fechas "
          f"({registros[0][0]} a {registros[-1][0]}).")


# ==============================================================================
# BLOQUE DE EJECUCION
# ==============================================================================
if __name__ == "__main__":
    print("=" * 72)
    print("POBLACION DE CATALOGOS — PUNTUALIDAD DE VUELOS 2017")
    print("=" * 72)

    poblar_estados()
    poblar_regimenes()
    poblar_franjas()
    poblar_aeropuertos()
    poblar_aeronaves()
    poblar_calendario()

    print("-" * 72)
    print("Catalogos listos. Los hechos se cargan con el script 03.")
