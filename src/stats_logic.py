"""
src/stats_logic.py
================================================================================
LOGICA ESTADISTICA DE LA INVESTIGACION
Puntualidad y regularidad operativa de vuelos domesticos, julio-septiembre 2017.
================================================================================

Concentra toda la estadistica del proyecto. Las paginas del aplicativo llaman
funciones de aqui y solo dibujan el resultado; ninguna calcula por su cuenta.
Esa separacion evita que una misma medida se calcule de dos formas distintas en
dos pantallas distintas.

NOTA METODOLOGICA — LOS DOS UNIVERSOS
-------------------------------------
La investigacion opera sobre DOS universos anidados y nunca los confunde:

  * UNIVERSO DE PROGRAMACION: los 33.121 vuelos de la base. Se emplea para medir
    que porcion de lo programado llego a ejecutarse.
  * UNIVERSO DE OPERACION: los 16.773 vuelos con hora real de salida (el 50,64%
    del anterior). Es el unico sobre el que se calculan demoras.

Toda funcion declara en su documentacion sobre cual de los dos opera.

La investigacion es de nivel DESCRIPTIVO: se trabaja con el universo completo y
no con una muestra, de modo que las medidas son parametros y las formulas de
dispersion son poblacionales.
"""

import streamlit as st
import pandas as pd


# ==============================================================================
# 1. IDENTIDAD VISUAL
# ==============================================================================

# Paleta "Pista": el color codifica la severidad de la demora, del verde
# (puntual) al rojo (demora severa). No es decorativo.
PALETA = {
    "verde_puntual":  "#2E9E7B",
    "verde_claro":    "#7FBF7B",
    "ambar":          "#FFB020",
    "naranja":        "#E8734A",
    "rojo_severo":    "#D93636",
    "azul_operativo": "#1E6091",
    "gris":           "#8A9199",
    "fondo":          "#0F1214",
    "texto":          "#ECEFF1",
}

COLOR_REGIMEN = {
    "Salida puntual":  PALETA["verde_puntual"],
    "Demora minima":   PALETA["verde_claro"],
    "Demora leve":     PALETA["ambar"],
    "Demora moderada": PALETA["naranja"],
    "Demora severa":   PALETA["rojo_severo"],
}

COLOR_CATEGORIA = {
    "Regional":              PALETA["verde_puntual"],
    "Corto y medio alcance": PALETA["ambar"],
    "Largo alcance":         PALETA["azul_operativo"],
}


def formato_numero(valor, decimales=0, sufijo=""):
    """Formatea una cifra para tarjetas de indicadores."""
    if valor is None or pd.isna(valor):
        return "s/d"
    valor = float(valor)
    if abs(valor) >= 1_000_000:
        return f"{valor/1_000_000:,.2f} M{sufijo}"
    if abs(valor) >= 1_000:
        return f"{valor:,.0f}{sufijo}"
    return f"{valor:,.{decimales}f}{sufijo}"


def formato_demora(minutos):
    """
    Expresa una demora con la unidad mas legible.

    Las demoras de esta base van de cero a mas de cuatro horas; mostrarlo todo
    en minutos obliga a leer valores como '195,69 min', poco intuitivos.
    """
    if minutos is None or pd.isna(minutos):
        return "s/d"
    minutos = float(minutos)
    if abs(minutos) < 60:
        return f"{minutos:,.1f} min"
    return f"{minutos/60:,.2f} h"


# ==============================================================================
# 2. FILTRO MAESTRO Y BLOQUES FROM
# ==============================================================================

# Universo de OPERACION: el INNER JOIN con `metricas` ya excluye por
# construccion los vuelos no operados, de modo que no hace falta repetir esa
# condicion en el WHERE.
FROM_OPERACION = """
    FROM vuelos      v
    JOIN metricas    m ON v.vuelo_id      = m.vuelo_id
    JOIN regimenes   r ON m.regimen_id    = r.regimen_id
    JOIN aeronaves   n ON v.aircraft_code = n.aircraft_code
    JOIN franjas     f ON v.franja_id     = f.franja_id
    JOIN calendario  c ON v.fecha_programada = c.fecha
"""

# Universo de PROGRAMACION: todos los vuelos, operados o no.
FROM_PROGRAMACION = """
    FROM vuelos     v
    JOIN estados    e ON v.estado_id     = e.estado_id
    JOIN aeronaves  n ON v.aircraft_code = n.aircraft_code
    JOIN calendario c ON v.fecha_programada = c.fecha
"""


def _escapar(texto):
    return texto.replace("'", "''")


def construir_filtro(categoria="Todas", franja="Todas", dia="Todos", origen="Todos"):
    """
    Genera la clausula WHERE que comparten las consultas del universo de
    operacion.

    Centralizarla garantiza que los indicadores del encabezado y los graficos
    del cuerpo describan SIEMPRE el mismo subconjunto.
    """
    condiciones = ["1 = 1"]
    if categoria and categoria != "Todas":
        condiciones.append(f"n.categoria_alcance = '{_escapar(categoria)}'")
    if franja and franja != "Todas":
        condiciones.append(f"f.etiqueta = '{_escapar(franja)}'")
    if dia and dia != "Todos":
        condiciones.append(f"c.nombre_dia = '{_escapar(dia)}'")
    if origen and origen != "Todos":
        condiciones.append(f"v.origen = '{_escapar(origen)}'")
    return " AND ".join(condiciones)


def construir_filtro_programacion(categoria="Todas", dia="Todos", origen="Todos"):
    """
    Variante del filtro para el universo de PROGRAMACION.

    Omite la franja horaria porque esa dimension se une en el bloque FROM de
    operacion; el universo de programacion se describe sin ella.
    """
    condiciones = ["1 = 1"]
    if categoria and categoria != "Todas":
        condiciones.append(f"n.categoria_alcance = '{_escapar(categoria)}'")
    if dia and dia != "Todos":
        condiciones.append(f"c.nombre_dia = '{_escapar(dia)}'")
    if origen and origen != "Todos":
        condiciones.append(f"v.origen = '{_escapar(origen)}'")
    return " AND ".join(condiciones)


# ==============================================================================
# 3. EJECUCION DE LA PROGRAMACION
# ==============================================================================

@st.cache_data(show_spinner=False)
def ejecucion_programacion(_qm, categoria, dia, origen):
    """
    Mide que proporcion de los vuelos programados llego a ejecutarse.
    Opera sobre el UNIVERSO DE PROGRAMACION.

    No es un preambulo tecnico: la mitad de la programacion de esta base estaba
    a futuro en el momento del corte, y saberlo condiciona la lectura de
    cualquier medida de demora.
    """
    filtro = construir_filtro_programacion(categoria, dia, origen)
    consulta = f"""
        SELECT
            COUNT(*)                                          AS programados,
            SUM(v.tiene_metricas)                             AS operados,
            ROUND(SUM(v.tiene_metricas) * 100.0 / COUNT(*), 2) AS pct_operados,
            SUM(CASE WHEN e.codigo = 'Cancelled' THEN 1 ELSE 0 END) AS cancelados
        {FROM_PROGRAMACION}
        WHERE {filtro}
    """
    return _qm.execute_query(consulta).iloc[0]


@st.cache_data(show_spinner=False)
def estados_programacion(_qm, categoria, dia, origen):
    """Distribucion de los vuelos por estado. UNIVERSO DE PROGRAMACION."""
    filtro = construir_filtro_programacion(categoria, dia, origen)
    consulta = f"""
        SELECT
            e.codigo                                   AS "Estado",
            e.descripcion                              AS "Descripcion",
            COUNT(*)                                   AS "Vuelos",
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS "% del total"
        {FROM_PROGRAMACION}
        WHERE {filtro}
        GROUP BY e.codigo, e.descripcion, e.orden
        ORDER BY e.orden
    """
    return _qm.execute_query(consulta)


# ==============================================================================
# 4. INDICADORES Y ESTADISTICOS DE LA DEMORA
# ==============================================================================

@st.cache_data(show_spinner=False)
def obtener_indicadores(_qm, categoria, franja, dia, origen):
    """
    Indicadores del encabezado. Opera sobre el UNIVERSO DE OPERACION.

    Se reportan juntas la media y la mediana de la demora porque la
    distribucion es bimodal: un nucleo de demoras minimas y un grupo separado de
    demoras de mas de tres horas. La media queda entre ambos y no describe a
    ningun vuelo real.
    """
    filtro = construir_filtro(categoria, franja, dia, origen)
    consulta = f"""
        SELECT
            COUNT(*)                                      AS vuelos,
            AVG(m.demora_salida_min)                      AS demora_media,
            MEDIAN(m.demora_salida_min)                   AS demora_mediana,
            AVG(m.puntual) * 100.0                        AS pct_puntual,
            AVG(m.recuperacion_min)                       AS recuperacion_media,
            MAX(m.demora_salida_min)                      AS demora_maxima,
            AVG(m.duracion_programada_min)                AS duracion_media
        {FROM_OPERACION}
        WHERE {filtro}
    """
    return _qm.execute_query(consulta).iloc[0]


@st.cache_data(show_spinner=False)
def resumen_estadistico(_qm, categoria, franja, dia, origen):
    """
    Cuadro completo de estadisticos descriptivos de la demora de salida.
    UNIVERSO DE OPERACION.

    Incluye las cuatro familias que exige un analisis descriptivo:
      * TENDENCIA CENTRAL: media y mediana.
      * POSICION: cuartiles y percentiles 90, 95 y 99. Son imprescindibles: con
        una distribucion bimodal, los cuartiles describen el nucleo y los
        percentiles altos, la cola separada.
      * DISPERSION: rango, rango intercuartilico, desviacion tipica, varianza y
        coeficiente de variacion (poblacionales, por tratarse del universo).
      * FORMA: coeficiente de asimetria y curtosis.
    """
    filtro = construir_filtro(categoria, franja, dia, origen)
    consulta = f"""
        SELECT
            COUNT(*)                                 AS n,
            MIN(m.demora_salida_min)                 AS minimo,
            MAX(m.demora_salida_min)                 AS maximo,
            AVG(m.demora_salida_min)                 AS media,
            MEDIAN(m.demora_salida_min)              AS mediana,
            QUANTILE_CONT(m.demora_salida_min, 0.25) AS q1,
            QUANTILE_CONT(m.demora_salida_min, 0.75) AS q3,
            QUANTILE_CONT(m.demora_salida_min, 0.90) AS p90,
            QUANTILE_CONT(m.demora_salida_min, 0.95) AS p95,
            QUANTILE_CONT(m.demora_salida_min, 0.99) AS p99,
            STDDEV_POP(m.demora_salida_min)          AS desviacion,
            VAR_POP(m.demora_salida_min)             AS varianza,
            SKEWNESS(m.demora_salida_min)            AS asimetria,
            KURTOSIS(m.demora_salida_min)            AS curtosis
        {FROM_OPERACION}
        WHERE {filtro}
    """
    fila = _qm.execute_query(consulta).iloc[0]
    return {
        "n": fila["n"], "minimo": fila["minimo"], "maximo": fila["maximo"],
        "media": fila["media"], "mediana": fila["mediana"],
        "q1": fila["q1"], "q3": fila["q3"], "p90": fila["p90"],
        "p95": fila["p95"], "p99": fila["p99"],
        "rango": fila["maximo"] - fila["minimo"],
        "rango_intercuartilico": fila["q3"] - fila["q1"],
        "desviacion": fila["desviacion"], "varianza": fila["varianza"],
        "coef_variacion": (fila["desviacion"] / fila["media"] * 100) if fila["media"] else None,
        "asimetria": fila["asimetria"], "curtosis": fila["curtosis"],
    }


# ==============================================================================
# 5. DISTRIBUCIONES
# ==============================================================================

@st.cache_data(show_spinner=False)
def distribucion_regimenes(_qm, categoria, franja, dia, origen):
    """
    Cuadro de distribucion de frecuencias por regimen de puntualidad.
    UNIVERSO DE OPERACION.

    Entrega las cuatro columnas de un cuadro clasico: frecuencia absoluta,
    relativa, y ambas acumuladas, calculadas con funciones de ventana para no
    acumular en Python.
    """
    filtro = construir_filtro(categoria, franja, dia, origen)
    consulta = f"""
        WITH conteo AS (
            SELECT r.etiqueta AS regimen, r.descripcion, r.orden,
                   COUNT(*) AS frecuencia,
                   AVG(m.demora_salida_min) AS demora_media
            {FROM_OPERACION}
            WHERE {filtro}
            GROUP BY r.etiqueta, r.descripcion, r.orden
        )
        SELECT
            regimen                                              AS "Regimen",
            descripcion                                          AS "Definicion",
            frecuencia                                           AS "Frec. absoluta (fi)",
            ROUND(frecuencia * 100.0 / SUM(frecuencia) OVER (), 3)
                                                                 AS "Frec. relativa (hi %)",
            SUM(frecuencia) OVER (ORDER BY orden)                AS "Frec. acumulada (Fi)",
            ROUND(SUM(frecuencia) OVER (ORDER BY orden) * 100.0
                  / SUM(frecuencia) OVER (), 3)                  AS "Frec. rel. acumulada (Hi %)",
            ROUND(demora_media, 2)                               AS "Demora media (min)"
        FROM conteo
        ORDER BY orden
    """
    return _qm.execute_query(consulta)


@st.cache_data(show_spinner=False)
def histograma_demora(_qm, categoria, franja, dia, origen, tope=60):
    """
    Distribucion minuto a minuto de la demora, hasta un tope.
    UNIVERSO DE OPERACION.

    Es la evidencia directa de la bimodalidad: permite ver que el nucleo se
    agota a los nueve minutos y que despues no hay nada hasta las tres horas.
    """
    filtro = construir_filtro(categoria, franja, dia, origen)
    consulta = f"""
        SELECT
            m.demora_salida_min                        AS "Demora (min)",
            COUNT(*)                                   AS "Vuelos"
        {FROM_OPERACION}
        WHERE {filtro} AND m.demora_salida_min <= {int(tope)}
        GROUP BY m.demora_salida_min
        ORDER BY m.demora_salida_min
    """
    return _qm.execute_query(consulta)


@st.cache_data(show_spinner=False)
def puntualidad_por_franja(_qm, categoria, dia, origen):
    """Puntualidad y demora media por franja horaria. UNIVERSO DE OPERACION."""
    filtro = construir_filtro(categoria, "Todas", dia, origen)
    consulta = f"""
        SELECT
            f.etiqueta                                 AS "Franja",
            COUNT(*)                                   AS "Vuelos",
            ROUND(AVG(m.demora_salida_min), 2)         AS "Demora media (min)",
            ROUND(MEDIAN(m.demora_salida_min), 1)      AS "Demora mediana (min)",
            ROUND(AVG(m.puntual) * 100.0, 2)           AS "Puntualidad (%)"
        {FROM_OPERACION}
        WHERE {filtro}
        GROUP BY f.etiqueta, f.orden
        ORDER BY f.orden
    """
    return _qm.execute_query(consulta)


@st.cache_data(show_spinner=False)
def puntualidad_por_aeronave(_qm, franja, dia, origen):
    """
    Puntualidad por modelo de aeronave. UNIVERSO DE OPERACION.

    ADVERTENCIA INTERPRETATIVA: estas cifras no miden la fiabilidad tecnica del
    avion. Cada modelo cubre rutas, aeropuertos y frecuencias distintas, y esas
    condiciones pesan sobre la puntualidad tanto o mas que la aeronave.
    """
    filtro = construir_filtro("Todas", franja, dia, origen)
    consulta = f"""
        SELECT
            n.modelo                                   AS "Modelo",
            n.categoria_alcance                        AS "Categoria",
            n.asientos                                 AS "Asientos",
            COUNT(*)                                   AS "Vuelos",
            ROUND(AVG(m.demora_salida_min), 2)         AS "Demora media (min)",
            ROUND(AVG(m.puntual) * 100.0, 2)           AS "Puntualidad (%)",
            ROUND(AVG(m.duracion_programada_min), 1)   AS "Duracion media (min)"
        {FROM_OPERACION}
        WHERE {filtro}
        GROUP BY n.modelo, n.categoria_alcance, n.asientos
        ORDER BY "Vuelos" DESC
    """
    return _qm.execute_query(consulta)


@st.cache_data(show_spinner=False)
def serie_diaria(_qm, categoria, franja, dia, origen):
    """Serie temporal diaria de la puntualidad. UNIVERSO DE OPERACION."""
    filtro = construir_filtro(categoria, franja, dia, origen)
    consulta = f"""
        SELECT
            v.fecha_programada                         AS "Fecha",
            c.nombre_dia                               AS "Dia",
            COUNT(*)                                   AS "Vuelos",
            ROUND(AVG(m.demora_salida_min), 2)         AS "Demora media (min)",
            ROUND(AVG(m.puntual) * 100.0, 2)           AS "Puntualidad (%)"
        {FROM_OPERACION}
        WHERE {filtro}
        GROUP BY v.fecha_programada, c.nombre_dia
        ORDER BY v.fecha_programada
    """
    return _qm.execute_query(consulta)


@st.cache_data(show_spinner=False)
def ranking_aeropuertos(_qm, categoria, franja, dia, n=15, criterio="Vuelos"):
    """
    Ranking de aeropuertos de origen. UNIVERSO DE OPERACION.

    Se exige un minimo de 100 vuelos: una media calculada sobre unos pocos casos
    no es comparable con una calculada sobre miles.
    """
    filtro = construir_filtro(categoria, franja, dia, "Todos")
    consulta = f"""
        SELECT
            a.ciudad                                   AS "Ciudad",
            a.nombre                                   AS "Aeropuerto",
            v.origen                                   AS "Codigo",
            COUNT(*)                                   AS "Vuelos",
            ROUND(AVG(m.demora_salida_min), 2)         AS "Demora media (min)",
            ROUND(AVG(m.puntual) * 100.0, 2)           AS "Puntualidad (%)"
        {FROM_OPERACION}
        JOIN aeropuertos a ON v.origen = a.airport_code
        WHERE {filtro}
        GROUP BY a.ciudad, a.nombre, v.origen
        HAVING COUNT(*) >= 100
        ORDER BY "{criterio}" DESC
        LIMIT {int(n)}
    """
    return _qm.execute_query(consulta)


@st.cache_data(show_spinner=False)
def mapa_aeropuertos(_qm, categoria, franja, dia):
    """
    Aeropuertos con sus coordenadas y su puntualidad, para el mapa.
    UNIVERSO DE OPERACION.

    Las coordenadas provienen del catalogo depurado en el ETL: la fuente las
    entrega como una cadena con el formato del tipo `point` de PostgreSQL.
    """
    filtro = construir_filtro(categoria, franja, dia, "Todos")
    consulta = f"""
        SELECT
            a.ciudad                                   AS ciudad,
            a.nombre                                   AS aeropuerto,
            a.latitud                                  AS lat,
            a.longitud                                 AS lon,
            COUNT(*)                                   AS vuelos,
            ROUND(AVG(m.demora_salida_min), 2)         AS demora,
            ROUND(AVG(m.puntual) * 100.0, 2)           AS puntualidad
        {FROM_OPERACION}
        JOIN aeropuertos a ON v.origen = a.airport_code
        WHERE {filtro}
        GROUP BY a.ciudad, a.nombre, a.latitud, a.longitud
        HAVING COUNT(*) >= 20
        ORDER BY vuelos DESC
    """
    return _qm.execute_query(consulta)


# ==============================================================================
# 6. LECTURAS AUTOMATICAS
# ==============================================================================

def lectura_automatica(indicadores, ejecucion):
    """
    Redacta una lectura breve de los indicadores segun el filtro activo.

    Se apoya en la distancia entre media y mediana, que es la senal estadistica
    de una distribucion con cola separada.
    """
    if indicadores["vuelos"] == 0:
        return "No hay vuelos operados que cumplan los criterios seleccionados."
    return (
        f"**Perfil del universo de operacion.** Se describen "
        f"{formato_numero(indicadores['vuelos'])} vuelos con hora real de salida, "
        f"el {ejecucion['pct_operados']:.2f}% de los programados. La puntualidad "
        f"es del {indicadores['pct_puntual']:.2f}% con el criterio del sector "
        f"(15 minutos o menos). La demora media es de "
        f"{indicadores['demora_media']:.2f} minutos frente a una mediana de "
        f"{indicadores['demora_mediana']:.0f}: la media queda muy por encima "
        f"porque una minoria de vuelos acumula demoras de mas de tres horas. "
        f"La recuperacion media en ruta es de "
        f"{indicadores['recuperacion_media']:.3f} minutos."
    )


def ejecutar_consulta_libre(_qm, sentencia):
    """
    Ejecuta una consulta escrita por el usuario en la terminal SQL.

    Devuelve la tupla (DataFrame, error). Nunca lanza excepcion: la terminal
    debe informar el fallo sin tumbar la aplicacion.
    """
    resultado = _qm.execute_query(sentencia)
    if isinstance(resultado, str):
        return None, resultado
    return resultado, None
