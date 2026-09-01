"""
01_creacion_esquema.py
================================================================================
CREACION DEL ESQUEMA NORMALIZADO — PUNTUALIDAD DE VUELOS DOMESTICOS
Investigacion: Puntualidad y regularidad operativa, julio-septiembre de 2017.
Escuela de Estadistica y Ciencias Actuariales (EECA-UCV) — Computacion II
================================================================================

PROPOSITO
---------
La base original (travel.sqlite, 109 MB) es la exportacion a SQLite de una base
PostgreSQL de demostracion de una aerolinea. Su modelo esta pensado para OPERAR
un sistema de reservas, no para analizarlo, y arrastra tres rasgos que impiden
usarlo tal cual:

  1. CAMPOS JSON. El nombre del aeropuerto, la ciudad y el modelo de aeronave
     vienen como documentos JSON con las claves "en" y "ru"
     (`{"en": "Yakutsk Airport", "ru": "Якутск"}`). Ningun motor analitico puede
     agrupar por eso sin extraerlo primero.

  2. COORDENADAS COMO TEXTO. La posicion del aeropuerto es una cadena con el
     formato del tipo `point` de PostgreSQL: `(129.77099,62.09329)`.

  3. NULOS DISFRAZADOS. Las horas reales de salida y llegada de los vuelos aun
     no operados no son NULL: contienen la cadena literal `\\N`, el marcador de
     nulo de los volcados de PostgreSQL. Compararlas como fechas sin depurarlas
     produce resultados silenciosamente incorrectos.

Este script construye un ESQUEMA EN ESTRELLA normalizado hasta la Tercera Forma
Normal, con seis dimensiones y dos tablas de hechos.

DECISION DE DISENO: LA RELACION 1:0..1
--------------------------------------
De los 33.121 vuelos de la base, solo 16.773 tienen hora real de salida: el
resto estaban programados a futuro en el momento del corte. Igual que en un
estudio de cobertura, se cargan TODOS los vuelos en `vuelos` y solo los operados
generan fila en `metricas_puntualidad`. Asi la investigacion puede medir que
porcion de la programacion llego a ejecutarse, en lugar de filtrarla y perder de
vista ese hecho.

ORDEN DE EJECUCION: primero, antes de catalogos y ETL.
"""

import os
import sqlite3 as sql

DB_DESTINO = 'puntualidad_vuelos_2017.db'


def abrir_conexion():
    """
    Conexion con integridad referencial activa.

    SQLite ignora las llaves foraneas salvo que se active el PRAGMA en CADA
    conexion; sin esta linea las restricciones serian solo documentacion.
    """
    conn = sql.connect(DB_DESTINO)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


# ==============================================================================
# BLOQUE 1 — DIMENSIONES
# ==============================================================================

def crear_dimension_aeropuertos():
    """
    Catalogo de los 104 aeropuertos de la red.

    Extrae el nombre y la ciudad de los campos JSON y descompone la cadena de
    coordenadas en longitud y latitud numericas, para que el aplicativo pueda
    dibujar mapas sin volver a parsear texto en cada consulta.
    """
    conn = abrir_conexion()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS aeropuertos (
            airport_code  TEXT PRIMARY KEY,   -- Codigo IATA de tres letras
            nombre        TEXT NOT NULL,      -- Extraido del JSON, clave "en"
            ciudad        TEXT NOT NULL,      -- Extraido del JSON, clave "en"
            zona_horaria  TEXT NOT NULL,
            longitud      REAL NOT NULL,      -- Extraida de la cadena point
            latitud       REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    print("[OK] Dimension 'aeropuertos' creada.")


def crear_dimension_aeronaves():
    """
    Catalogo de los modelos de aeronave.

    Se agrega 'categoria_alcance', una clasificacion propia que agrupa los
    modelos en regional, corto y largo alcance. Permite comparar la puntualidad
    entre bloques homogeneos: un turbohelice regional y un Boeing 777 no operan
    en el mismo regimen.
    """
    conn = abrir_conexion()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS aeronaves (
            aircraft_code     TEXT PRIMARY KEY,
            modelo            TEXT NOT NULL,   -- Extraido del JSON, clave "en"
            alcance_km        INTEGER NOT NULL,
            categoria_alcance TEXT NOT NULL,   -- Regional / Corto / Largo alcance
            asientos          INTEGER NOT NULL -- Capacidad, contada desde `seats`
        )
    """)
    conn.commit()
    conn.close()
    print("[OK] Dimension 'aeronaves' creada.")


def crear_dimension_estados():
    """
    Catalogo de los estados del vuelo tal como los define la fuente.

    La columna 'es_operado' distingue los vuelos que llegaron a ejecutarse de
    los programados a futuro y de los cancelados. Es la bandera que gobierna el
    universo de analisis.
    """
    conn = abrir_conexion()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS estados_vuelo (
            estado_id   INTEGER PRIMARY KEY,
            codigo      TEXT NOT NULL UNIQUE,   -- Arrived, Scheduled, Cancelled...
            descripcion TEXT NOT NULL,
            es_operado  INTEGER NOT NULL,       -- 1 = el vuelo se ejecuto
            orden       INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    print("[OK] Dimension 'estados_vuelo' creada.")


def crear_dimension_regimenes():
    """
    Dimension de regimenes de puntualidad. Es la variable segmentadora.

    Los cortes NO son convencionales: se fijaron observando la distribucion
    empirica de la demora, que resulto ser BIMODAL. Casi todos los vuelos
    operados salen entre 0 y 9 minutos despues de lo previsto, y un grupo
    separado lo hace entre 180 y 277 minutos. Entre 10 y 179 minutos no hay
    practicamente ningun vuelo.

    Una particion en intervalos de igual amplitud repartiria esa realidad en
    tramos vacios; los tramos declarados aqui siguen la forma real del dato.
    """
    conn = abrir_conexion()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS regimenes_puntualidad (
            regimen_id      INTEGER PRIMARY KEY,
            etiqueta        TEXT NOT NULL UNIQUE,
            limite_inf_min  INTEGER NOT NULL,
            limite_sup_min  INTEGER,            -- NULL = sin tope
            descripcion     TEXT NOT NULL,
            orden           INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    print("[OK] Dimension 'regimenes_puntualidad' creada.")


def crear_dimension_franjas():
    """
    Franjas horarias de la salida programada.

    La hora del dia es un factor operativo clasico: la congestion de la red y el
    arrastre de demoras acumuladas a lo largo de la jornada afectan a la
    puntualidad. Modelarla como dimension evita recalcular la franja en cada
    consulta sobre 33.121 vuelos.
    """
    conn = abrir_conexion()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS franjas_horarias (
            franja_id   INTEGER PRIMARY KEY,
            etiqueta    TEXT NOT NULL UNIQUE,
            hora_inicio INTEGER NOT NULL,
            hora_fin    INTEGER NOT NULL,
            orden       INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    print("[OK] Dimension 'franjas_horarias' creada.")


def crear_dimension_calendario():
    """
    Calendario operativo, una fila por fecha del periodo observado.

    Incorpora el dia de la semana y la bandera de fin de semana, atributos que
    la fuente no trae y que se necesitan para describir el patron semanal de la
    operacion.
    """
    conn = abrir_conexion()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS calendario_operativo (
            fecha         DATE PRIMARY KEY,   -- AAAA-MM-DD
            anio          INTEGER NOT NULL,
            mes           INTEGER NOT NULL,
            nombre_mes    TEXT NOT NULL,
            dia_semana    INTEGER NOT NULL,   -- 1 = lunes ... 7 = domingo
            nombre_dia    TEXT NOT NULL,
            es_fin_semana INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    print("[OK] Dimension 'calendario_operativo' creada.")


# ==============================================================================
# BLOQUE 2 — TABLAS DE HECHOS
# ==============================================================================

def crear_hechos_vuelos():
    """
    Tabla de hechos primaria: un registro por vuelo programado (33.121).

    Incluye TODOS los vuelos, operados o no, porque la proporcion de la
    programacion que llega a ejecutarse es en si misma un resultado del estudio.
    La bandera `tiene_metricas` materializa esa distincion para no evaluar NULL
    repetidamente.
    """
    conn = abrir_conexion()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vuelos (
            vuelo_id            INTEGER PRIMARY KEY,  -- flight_id de la fuente
            numero_vuelo        TEXT NOT NULL,
            fecha_programada    DATE NOT NULL,        -- FK al calendario
            hora_programada     INTEGER NOT NULL,     -- Hora del dia, 0-23
            franja_id           INTEGER NOT NULL,
            origen              TEXT NOT NULL,
            destino             TEXT NOT NULL,
            aircraft_code       TEXT NOT NULL,
            estado_id           INTEGER NOT NULL,
            salida_programada   TEXT NOT NULL,        -- AAAA-MM-DD HH:MM:SS
            llegada_programada  TEXT NOT NULL,
            salida_real         TEXT,                 -- NULL si no se opero
            llegada_real        TEXT,
            tiene_metricas      INTEGER NOT NULL,     -- 1 = genera fila de metricas
            FOREIGN KEY (fecha_programada) REFERENCES calendario_operativo(fecha),
            FOREIGN KEY (franja_id)        REFERENCES franjas_horarias(franja_id),
            FOREIGN KEY (origen)           REFERENCES aeropuertos(airport_code),
            FOREIGN KEY (destino)          REFERENCES aeropuertos(airport_code),
            FOREIGN KEY (aircraft_code)    REFERENCES aeronaves(aircraft_code),
            FOREIGN KEY (estado_id)        REFERENCES estados_vuelo(estado_id)
        )
    """)
    conn.commit()
    conn.close()
    print("[OK] Tabla de hechos 'vuelos' creada.")


def crear_hechos_metricas():
    """
    Tabla de hechos derivada: metricas de puntualidad de los vuelos operados.

    Relacion 1:0..1 con `vuelos`. Contiene las medidas que la fuente NO trae y
    que constituyen el objeto del estudio:

        * demora_salida_min / demora_llegada_min: minutos entre lo real y lo
          programado.
        * recuperacion_min: demora de salida menos demora de llegada. Positiva
          si el vuelo recupero tiempo en ruta.
        * duracion_programada_min / duracion_real_min: tiempo de bloque.
        * puntual: bandera 1/0 segun el criterio declarado (salida con 15
          minutos de demora o menos), que es el estandar habitual del sector.
    """
    conn = abrir_conexion()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS metricas_puntualidad (
            vuelo_id                INTEGER PRIMARY KEY,
            regimen_id              INTEGER NOT NULL,
            demora_salida_min       INTEGER NOT NULL,
            demora_llegada_min      INTEGER,
            recuperacion_min        INTEGER,
            duracion_programada_min INTEGER NOT NULL,
            duracion_real_min       INTEGER,
            puntual                 INTEGER NOT NULL,
            FOREIGN KEY (vuelo_id)   REFERENCES vuelos(vuelo_id),
            FOREIGN KEY (regimen_id) REFERENCES regimenes_puntualidad(regimen_id)
        )
    """)
    conn.commit()
    conn.close()
    print("[OK] Tabla de hechos 'metricas_puntualidad' creada.")


def crear_indices():
    """
    Indices sobre llaves foraneas y campos de filtrado frecuente.

    SQLite indexa las llaves primarias pero no las foraneas; sin estos indices
    cada JOIN del aplicativo recorreria la tabla completa.
    """
    conn = abrir_conexion()
    for sentencia in [
        "CREATE INDEX IF NOT EXISTS idx_vue_origen  ON vuelos(origen)",
        "CREATE INDEX IF NOT EXISTS idx_vue_destino ON vuelos(destino)",
        "CREATE INDEX IF NOT EXISTS idx_vue_aeronave ON vuelos(aircraft_code)",
        "CREATE INDEX IF NOT EXISTS idx_vue_estado  ON vuelos(estado_id)",
        "CREATE INDEX IF NOT EXISTS idx_vue_fecha   ON vuelos(fecha_programada)",
        "CREATE INDEX IF NOT EXISTS idx_vue_franja  ON vuelos(franja_id)",
        "CREATE INDEX IF NOT EXISTS idx_met_regimen ON metricas_puntualidad(regimen_id)",
    ]:
        conn.execute(sentencia)
    conn.commit()
    conn.close()
    print("[OK] Indices de apoyo creados.")


# ==============================================================================
# BLOQUE DE EJECUCION
# ==============================================================================
if __name__ == "__main__":
    print("=" * 72)
    print("CREACION DEL ESQUEMA — PUNTUALIDAD DE VUELOS DOMESTICOS 2017")
    print("=" * 72)

    crear_dimension_aeropuertos()
    crear_dimension_aeronaves()
    crear_dimension_estados()
    crear_dimension_regimenes()
    crear_dimension_franjas()
    crear_dimension_calendario()

    crear_hechos_vuelos()
    crear_hechos_metricas()

    crear_indices()

    print("-" * 72)
    print(f"Esquema disponible en: {os.path.abspath(DB_DESTINO)}")
