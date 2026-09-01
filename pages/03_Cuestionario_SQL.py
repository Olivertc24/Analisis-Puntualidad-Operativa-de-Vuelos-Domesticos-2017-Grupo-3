"""
pages/03_Cuestionario_SQL.py
================================================================================
CUESTIONARIO SQL — SEIS CONSULTAS ANALITICAS RESUELTAS
Puntualidad y regularidad operativa de vuelos domesticos, 2017.
================================================================================

Cada apartado presenta el enunciado, la sentencia que lo resuelve, el resultado
ejecutado en vivo sobre el Data Lake y la interpretacion del hallazgo.

Las consultas se apoyan en funciones de ventana (SUM OVER, RANK, NTILE,
ROW_NUMBER) y en agregacion condicional, tecnicas que resuelven en una sola
pasada problemas que de otro modo exigirian varias consultas encadenadas.
"""

import streamlit as st
import plotly.express as px

from src.query_manager import get_query_manager

st.set_page_config(page_title="Cuestionario SQL", page_icon="🧮", layout="wide")
st.title("Cuestionario SQL")
st.caption("Seis problemas analiticos resueltos sobre el Data Lake de vuelos")

qm = get_query_manager()
if not qm.esta_completo():
    st.error("El Data Lake no esta disponible. Ejecute los scripts de `Base de datos/`.")
    st.stop()


def presentar(numero, titulo, enunciado, tecnica, sql, interpretacion, grafico=None):
    """Renderiza un apartado completo, para que todos se lean de forma homogenea."""
    st.header(f"Consulta {numero}. {titulo}")
    st.markdown(f"**Enunciado.** {enunciado}")
    st.caption(f"Tecnica SQL empleada: {tecnica}")
    with st.expander("Ver sentencia SQL"):
        st.code(sql, language="sql")

    resultado = qm.execute_query(sql)
    if isinstance(resultado, str):
        st.error(resultado); return
    if resultado.empty:
        st.warning("La consulta no devolvio registros."); return

    if grafico:
        col_t, col_g = st.columns([1, 1])
        with col_t:
            st.dataframe(resultado, width="stretch", hide_index=True)
        with col_g:
            st.plotly_chart(grafico(resultado), width="stretch")
    else:
        st.dataframe(resultado, width="stretch", hide_index=True)

    st.success(f"**Interpretacion.** {interpretacion}")
    st.markdown("---")


# ==============================================================================
SQL_1 = """
WITH ordenado AS (
    SELECT
        m.demora_salida_min,
        -- Suma acumulada de minutos, recorriendo los vuelos del mas al menos
        -- retrasado.
        SUM(m.demora_salida_min) OVER (
            ORDER BY m.demora_salida_min DESC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS minutos_acumulados,
        ROW_NUMBER() OVER (ORDER BY m.demora_salida_min DESC) AS posicion
    FROM metricas m
),
totales AS (
    SELECT SUM(demora_salida_min) AS minutos_totales, COUNT(*) AS n_total
    FROM metricas
),
umbrales AS (SELECT UNNEST([50, 80, 90, 95]) AS umbral)
SELECT
    umbral                                                     AS "Umbral (% de los minutos)",
    MIN(posicion)                                              AS "Vuelos necesarios",
    ROUND(MIN(posicion) * 100.0 / (SELECT n_total FROM totales), 3)
                                                               AS "% de los vuelos"
FROM ordenado, umbrales, totales
WHERE minutos_acumulados >= umbral / 100.0 * minutos_totales
GROUP BY umbral
ORDER BY umbral;
"""

presentar(
    1, "Concentracion de los minutos de demora",
    "Ordene los vuelos operados de mayor a menor demora y determine cuantos hacen "
    "falta para acumular el 50%, el 80%, el 90% y el 95% del total de minutos de "
    "retraso del periodo.",
    "Suma acumulada con marco de ventana explicito (`ROWS BETWEEN UNBOUNDED "
    "PRECEDING AND CURRENT ROW`), numeracion de filas y generacion de umbrales con "
    "`UNNEST`.",
    SQL_1,
    "La concentracion es acusada. Bastan **487 vuelos** —el 2,9% de los operados— "
    "para acumular la mitad de todos los minutos de demora del periodo, y **1.893** "
    "(el 11,3%) para acumular el 80%. Dicho de otro modo: casi nueve de cada diez "
    "vuelos aportan, en conjunto, solo la quinta parte del retraso total.\n\n"
    "Esta es la razon estadistica por la que la demora media (12,21 minutos) es un "
    "descriptor enganoso frente a la mediana (3 minutos): la media esta determinada "
    "por una minoria de vuelos con retrasos de mas de tres horas.",
)

# ==============================================================================
SQL_2 = """
SELECT
    CAST(m.demora_salida_min / 10 AS INTEGER) * 10    AS "Decena (min)",
    COUNT(*)                                         AS "Vuelos",
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 3) AS "% del total",
    ROUND(MIN(m.demora_salida_min), 0)               AS "Minimo",
    ROUND(MAX(m.demora_salida_min), 0)               AS "Maximo"
FROM metricas m
GROUP BY 1
ORDER BY 1;
"""


def grafico_2(df):
    figura = px.bar(df, x="Decena (min)", y="Vuelos", log_y=True,
                    title="Vuelos por decena de minutos de demora (escala logaritmica)",
                    color_discrete_sequence=["#2E9E7B"])
    figura.update_layout(template="plotly_dark", height=400)
    return figura


presentar(
    2, "El vacio: la demora no es un continuo",
    "Agrupe los vuelos operados en decenas de minutos de demora y cuente cuantos "
    "caen en cada decena. Observe que decenas quedan vacias.",
    "Agrupacion por division entera (`CAST(x/10 AS INTEGER) * 10`) y funcion de "
    "ventana sin particion para el porcentaje sobre el total.",
    SQL_2,
    "**El hallazgo central de la investigacion.** La tabla no muestra una "
    "progresion decreciente, sino **dos bloques separados por un vacio absoluto**:\n\n"
    "- Las decenas 0 y 10 concentran 15.973 vuelos, el 95,23% del total.\n"
    "- Las decenas de 20 a 110 minutos **no aparecen en el resultado**: no hay "
    "ni un solo vuelo en ese rango.\n"
    "- A partir de los 120 minutos reaparece un segundo grupo de 800 vuelos, con "
    "una demora media de 195,69 minutos.\n\n"
    "Una operacion real produce una distribucion continua y decreciente: muchos "
    "retrasos pequenos, algunos medianos, pocos grandes. Un hueco de hora y media "
    "sin un solo caso **no ocurre en un sistema real**; es la firma del "
    "procedimiento que genero estos datos de forma sintetica. La grafica usa escala "
    "logaritmica precisamente para que los dos bloques y el vacio entre ellos sean "
    "visibles a la vez.",
    grafico_2,
)

# ==============================================================================
SQL_3 = """
WITH cuartilizado AS (
    SELECT
        m.recuperacion_min,
        m.duracion_programada_min,
        NTILE(4) OVER (ORDER BY m.duracion_programada_min) AS cuartil
    FROM metricas m
    WHERE m.recuperacion_min IS NOT NULL
)
SELECT
    cuartil                                     AS "Cuartil de duracion",
    COUNT(*)                                    AS "Vuelos",
    ROUND(MIN(duracion_programada_min), 0)      AS "Duracion minima (min)",
    ROUND(MAX(duracion_programada_min), 0)      AS "Duracion maxima (min)",
    ROUND(AVG(recuperacion_min), 4)             AS "Recuperacion media (min)",
    ROUND(MIN(recuperacion_min), 0)             AS "Peor caso",
    ROUND(MAX(recuperacion_min), 0)             AS "Mejor caso"
FROM cuartilizado
GROUP BY cuartil
ORDER BY cuartil;
"""

presentar(
    3, "¿Se recupera la demora en ruta?",
    "Divida los vuelos operados en cuatro grupos de igual tamano segun su duracion "
    "programada. Para cada cuartil calcule la recuperacion media, entendida como la "
    "demora de salida menos la de llegada.",
    "`NTILE(4)` para construir los cuartiles sobre una variable continua, con "
    "agregacion posterior por grupo.",
    SQL_3,
    "La respuesta es **no, en ningun tramo de duracion**. La recuperacion media va "
    "de −0,0034 a +0,0077 minutos: en la practica, cero.\n\n"
    "El resultado es contraintuitivo desde la teoria operativa. Cabria esperar que "
    "los vuelos largos —el cuarto cuartil llega a 530 minutos de duracion "
    "programada— tuvieran margen para recortar tiempo en el aire, y que los cortos "
    "no. Aqui ni unos ni otros lo hacen: **lo que se pierde en la puerta de "
    "embarque llega integro al destino**.\n\n"
    "Los casos extremos individuales (de −14 a +14 minutos) confirman que existe "
    "variacion vuelo a vuelo, pero se compensa por completo en el agregado. Es otro "
    "indicio de que el retraso de llegada se genero como una copia del de salida, "
    "sin modelar la operacion en ruta.",
)

# ==============================================================================
SQL_4 = """
WITH por_aeropuerto AS (
    SELECT
        v.origen,
        COUNT(*)                        AS vuelos,
        AVG(m.demora_salida_min)        AS demora_media,
        AVG(m.puntual) * 100.0          AS puntualidad
    FROM vuelos   v
    JOIN metricas m ON v.vuelo_id = m.vuelo_id
    GROUP BY v.origen
    HAVING COUNT(*) >= 200
),
-- 'glob' es palabra reservada en DuckDB (operador GLOB): la CTE no puede
-- llamarse asi.
promedio_global AS (SELECT AVG(demora_salida_min) AS demora FROM metricas)
SELECT
    a.ciudad                                             AS "Ciudad",
    a.nombre                                             AS "Aeropuerto",
    p.vuelos                                             AS "Vuelos",
    ROUND(p.demora_media, 2)                             AS "Demora media (min)",
    ROUND(p.demora_media - (SELECT demora FROM promedio_global), 2)
                                                         AS "Desvio vs global",
    ROUND(p.puntualidad, 2)                              AS "Puntualidad (%)",
    RANK() OVER (ORDER BY p.demora_media DESC)           AS "Puesto"
FROM por_aeropuerto p
JOIN aeropuertos a ON p.origen = a.airport_code
ORDER BY p.demora_media DESC
LIMIT 12;
"""

presentar(
    4, "Aeropuertos frente a la media de la red",
    "Para los aeropuertos de origen con al menos 200 vuelos operados, calcule la "
    "demora media y su desvio respecto de la media global de la red, y ordenelos de "
    "peor a mejor.",
    "`RANK()` sobre el conjunto agregado, subconsulta escalar para el promedio "
    "global y `HAVING` para exigir un minimo de casos.",
    SQL_4,
    "Las diferencias entre aeropuertos existen pero son **estrechas**: el peor "
    "(Sovetskiy, 15,28 minutos) supera a la media de la red en apenas 3,08 minutos, "
    "y su puntualidad sigue siendo del 93,88%. Moscu, el nodo de mayor trafico con "
    "870 vuelos, esta 1,16 minutos por encima de la media.\n\n"
    "El filtro de 200 vuelos no es cosmetico: sin el, aeropuertos con una decena de "
    "operaciones apareceraan en los extremos del ranking por puro azar muestral, y "
    "una media calculada sobre diez casos no es comparable con una calculada sobre "
    "ochocientos.",
)

# ==============================================================================
SQL_5 = """
SELECT
    c.nombre_dia                                                   AS "Dia",
    COUNT(*)                                                       AS "Vuelos",
    ROUND(AVG(CASE WHEN f.orden = 2 THEN m.puntual END) * 100, 2)  AS "Manana (%)",
    ROUND(AVG(CASE WHEN f.orden = 3 THEN m.puntual END) * 100, 2)  AS "Mediodia (%)",
    ROUND(AVG(CASE WHEN f.orden = 4 THEN m.puntual END) * 100, 2)  AS "Tarde (%)",
    ROUND(AVG(m.puntual) * 100, 2)                                 AS "Total dia (%)"
FROM vuelos     v
JOIN metricas   m ON v.vuelo_id         = m.vuelo_id
JOIN franjas    f ON v.franja_id        = f.franja_id
JOIN calendario c ON v.fecha_programada = c.fecha
GROUP BY c.nombre_dia, c.dia_semana
ORDER BY c.dia_semana;
"""

presentar(
    5, "Tabla cruzada: dia de la semana por franja horaria",
    "Construya una tabla de doble entrada que muestre la puntualidad por dia de la "
    "semana y franja horaria de salida, con el total de cada dia.",
    "Agregacion condicional (`AVG` sobre `CASE WHEN`) para construir una tabla "
    "cruzada en una sola pasada, sin necesidad de una operacion de pivote.",
    SQL_5,
    "**Hallazgo negativo, y por eso mismo informativo.** La teoria de la propagacion "
    "predice que la puntualidad se degrada segun avanza la jornada, porque una misma "
    "aeronave encadena vuelos y arrastra el retraso acumulado. Aqui esa degradacion "
    "**no aparece**: la puntualidad se mueve entre el 93,56% y el 96,83% sin patron "
    "reconocible ni por dia ni por franja. El domingo por la tarde (96,83%) es mejor "
    "que el lunes por la manana (94,98%), lo contrario de lo que cabria esperar.\n\n"
    "Comprobar que una relacion esperada no existe descarta una hipotesis, y eso es "
    "un resultado. En este caso refuerza ademas la lectura de la Consulta 2: los "
    "datos no fueron generados modelando la operacion real de una red.",
)

# ==============================================================================
SQL_6 = """
SELECT
    n.modelo                                                       AS "Modelo",
    n.categoria_alcance                                            AS "Categoria",
    n.asientos                                                     AS "Asientos",
    COUNT(*)                                                       AS "Programados",
    SUM(CASE WHEN e.codigo = 'Cancelled' THEN 1 ELSE 0 END)        AS "Cancelados",
    ROUND(SUM(CASE WHEN e.codigo = 'Cancelled' THEN 1 ELSE 0 END)
          * 100.0 / COUNT(*), 3)                                   AS "Tasa (%)"
FROM vuelos    v
JOIN estados   e ON v.estado_id     = e.estado_id
JOIN aeronaves n ON v.aircraft_code = n.aircraft_code
GROUP BY n.modelo, n.categoria_alcance, n.asientos
ORDER BY "Tasa (%)" DESC;
"""


def grafico_6(df):
    figura = px.bar(df.sort_values("Tasa (%)"), x="Tasa (%)", y="Modelo",
                    orientation="h", color="Categoria",
                    color_discrete_map={"Regional": "#2E9E7B",
                                        "Corto y medio alcance": "#FFB020",
                                        "Largo alcance": "#1E6091"},
                    title="Tasa de cancelacion por modelo de aeronave")
    figura.update_layout(template="plotly_dark", height=420)
    return figura


presentar(
    6, "Cancelaciones por modelo de aeronave",
    "Para cada modelo de la flota, calcule cuantos vuelos se programaron, cuantos "
    "se cancelaron y que tasa representan. Ordene de mayor a menor tasa.",
    "Agregacion condicional con `SUM(CASE WHEN ...)` para contar un subconjunto "
    "dentro del mismo recorrido que cuenta el total.",
    SQL_6,
    "La tasa de cancelacion varia por un factor de **trece** entre extremos: del "
    "2,00% del Bombardier CRJ-200 al 0,154% del Airbus A321-200.\n\n"
    "El patron tiene sentido operativo: los dos aparatos con mayor tasa son "
    "regionales o de corto alcance, que cubren rutas secundarias con menos "
    "alternativas de sustitucion, mientras que los de fuselaje ancho —Boeing 777-300 "
    "y 767-300, con 610 y 1.221 vuelos programados— cancelan mucho menos.\n\n"
    "Conviene una advertencia: esto **no mide la fiabilidad tecnica del avion**. Un "
    "modelo no se cancela a si mismo; lo que la tabla describe es el tipo de "
    "operacion en que cada aparato se emplea.",
    grafico_6,
)

st.caption("Escuela de Estadistica y Ciencias Actuariales · Universidad Central "
           "de Venezuela · Material academico de la asignatura Computacion II.")
