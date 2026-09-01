"""
pages/04_FlightQuery.py
================================================================================
FLIGHTQUERY — TERMINAL SQL INTERACTIVA Y DICCIONARIO DE DATOS
Puntualidad y regularidad operativa de vuelos domesticos, 2017.
================================================================================

Abre el Data Lake al usuario: permite escribir y ejecutar sentencias SQL contra
el modelo en estrella, e incorpora el diccionario de datos completo.

MEDIDAS DE ESTABILIDAD
----------------------
  * Limite de 5.000 filas en el resultado mostrado.
  * Captura de errores: una consulta mal escrita devuelve el mensaje del motor,
    nunca interrumpe la aplicacion.
  * Sin estado acumulado: cada ejecucion reemplaza el resultado anterior.
"""

import streamlit as st
import pandas as pd

from src.query_manager import get_query_manager
from src.stats_logic import ejecutar_consulta_libre

st.set_page_config(page_title="FlightQuery", page_icon="🛰️", layout="wide")
LIMITE_FILAS = 5_000

st.title("FlightQuery")
st.markdown("Terminal analitica sobre el Data Lake de vuelos. Las consultas se "
            "ejecutan con **DuckDB** directamente sobre los archivos Parquet.")

qm = get_query_manager()
if not qm.esta_completo():
    st.error("El Data Lake no esta disponible. Ejecute los scripts de `Base de datos/`.")
    st.stop()

with st.expander("Guia del esquema en estrella", expanded=True):
    st.warning(
        "**Antes de escribir la primera consulta.** El modelo maneja dos "
        "universos. `vuelos` contiene **todos** los vuelos programados (33.121). "
        "`metricas` contiene **solo** los 16.773 que llegaron a operarse. Un "
        "`JOIN` entre ambas restringe automaticamente al universo de operacion; "
        "consultar `vuelos` en solitario describe la programacion completa. "
        "Confundirlos produce cifras que no significan lo que parecen."
    )
    col_h, col_d = st.columns(2)
    with col_h:
        st.markdown("""
        **Tablas de hechos** (relacion 1:0..1)

        | Nombre en SQL | Contenido | Filas |
        |---|---|---|
        | `vuelos` | Programacion completa: horarios, ruta, aeronave, estado | 33.121 |
        | `metricas` | Medidas calculadas: demora, recuperacion, duracion real | 16.773 |

        Ambas se unen por `vuelo_id`.
        """)
    with col_d:
        st.markdown("""
        **Tablas de dimension**

        | Nombre en SQL | Contenido | Filas |
        |---|---|---|
        | `aeropuertos` | Nombre, ciudad, huso y coordenadas | 104 |
        | `aeronaves` | Modelo, alcance, capacidad y categoria | 9 |
        | `regimenes` | Regimenes de puntualidad | 5 |
        | `franjas` | Franjas horarias de salida | 5 |
        | `estados` | Estados del vuelo | 6 |
        | `calendario` | Fecha, dia de la semana, fin de semana | 61 |
        """)
    st.markdown("""
    **Relaciones para escribir los JOIN**

    ```
    vuelos.vuelo_id         = metricas.vuelo_id        (1:0..1)
    vuelos.origen           = aeropuertos.airport_code
    vuelos.destino          = aeropuertos.airport_code
    vuelos.aircraft_code    = aeronaves.aircraft_code
    vuelos.estado_id        = estados.estado_id
    vuelos.franja_id        = franjas.franja_id
    vuelos.fecha_programada = calendario.fecha
    metricas.regimen_id     = regimenes.regimen_id
    ```
    """)

col_g, col_l = st.columns(2)
with col_g:
    st.markdown("""
    **Como escribir una consulta**

    1. Use los nombres logicos de la tabla anterior, no los de los archivos Parquet.
    2. Especifique las columnas que necesita en lugar de `SELECT *`: el formato
       columnar lee solo las solicitadas, de modo que enumerarlas acelera la consulta.
    3. Las fechas se almacenan como texto ISO. Para operar con ellas use un `CAST`
       explicito: `CAST(v.fecha_programada AS DATE)`.
    """)
with col_l:
    st.markdown(f"""
    **Limites del entorno**

    1. El resultado se trunca a **{LIMITE_FILAS:,} filas**. Si necesita mas, agregue
       en la consulta en lugar de listar.
    2. La terminal no conserva resultados anteriores.
    3. El motor es DuckDB, cuyo dialecto es cercano al de PostgreSQL: admite
       `QUALIFY`, `NTILE`, `FILTER`, `MEDIAN`, `QUANTILE_CONT` y `UNNEST`.
       **Cuidado**: `glob` es palabra reservada y no puede usarse como alias.
    """)

st.markdown("---")
st.subheader("Consultas de ejemplo")

EJEMPLOS = {
    "Puntualidad por regimen":
        "SELECT r.etiqueta AS regimen,\n"
        "       COUNT(*) AS vuelos,\n"
        "       ROUND(AVG(m.demora_salida_min), 2) AS demora_media,\n"
        "       ROUND(AVG(m.puntual) * 100, 2) AS puntualidad_pct\n"
        "FROM metricas  m\n"
        "JOIN regimenes r ON m.regimen_id = r.regimen_id\n"
        "GROUP BY r.etiqueta, r.orden\n"
        "ORDER BY r.orden;",

    "Los 20 vuelos mas retrasados":
        "SELECT v.numero_vuelo,\n"
        "       og.ciudad AS origen,\n"
        "       dt.ciudad AS destino,\n"
        "       v.salida_programada,\n"
        "       m.demora_salida_min AS demora,\n"
        "       n.modelo\n"
        "FROM vuelos      v\n"
        "JOIN metricas    m  ON v.vuelo_id      = m.vuelo_id\n"
        "JOIN aeropuertos og ON v.origen        = og.airport_code\n"
        "JOIN aeropuertos dt ON v.destino       = dt.airport_code\n"
        "JOIN aeronaves   n  ON v.aircraft_code = n.aircraft_code\n"
        "ORDER BY m.demora_salida_min DESC\n"
        "LIMIT 20;",

    "Ejecucion de la programacion por dia":
        "SELECT v.fecha_programada AS fecha,\n"
        "       COUNT(*) AS programados,\n"
        "       SUM(v.tiene_metricas) AS operados,\n"
        "       ROUND(SUM(v.tiene_metricas) * 100.0 / COUNT(*), 2) AS ejecucion_pct\n"
        "FROM vuelos v\n"
        "GROUP BY v.fecha_programada\n"
        "ORDER BY v.fecha_programada;",

    "Rutas con mas trafico":
        "SELECT og.ciudad || ' - ' || dt.ciudad AS ruta,\n"
        "       COUNT(*) AS vuelos,\n"
        "       ROUND(AVG(m.demora_salida_min), 2) AS demora_media,\n"
        "       ROUND(AVG(m.duracion_programada_min), 0) AS duracion_min\n"
        "FROM vuelos      v\n"
        "JOIN metricas    m  ON v.vuelo_id = m.vuelo_id\n"
        "JOIN aeropuertos og ON v.origen   = og.airport_code\n"
        "JOIN aeropuertos dt ON v.destino  = dt.airport_code\n"
        "GROUP BY og.ciudad, dt.ciudad\n"
        "HAVING COUNT(*) >= 100\n"
        "ORDER BY vuelos DESC\n"
        "LIMIT 15;",
}

if "consulta_activa" not in st.session_state:
    st.session_state.consulta_activa = EJEMPLOS["Puntualidad por regimen"]

columnas = st.columns(len(EJEMPLOS))
for columna, (titulo, sentencia) in zip(columnas, EJEMPLOS.items()):
    with columna:
        if st.button(titulo, width="stretch"):
            st.session_state.consulta_activa = sentencia
            st.rerun()

st.subheader("Terminal")
consulta_usuario = st.text_area("Sentencia SQL", value=st.session_state.consulta_activa,
                                height=230, label_visibility="collapsed")

if st.button("Ejecutar consulta", type="primary"):
    st.session_state.pop("resultado_flightquery", None)
    with st.spinner("Consultando el Data Lake..."):
        resultado, error = ejecutar_consulta_libre(qm, consulta_usuario)
    if error:
        st.error(f"El motor rechazo la consulta:\n\n```\n{error}\n```")
    elif resultado is None or resultado.empty:
        st.warning("La consulta se ejecuto correctamente pero no devolvio filas.")
    else:
        filas = len(resultado)
        if filas > LIMITE_FILAS:
            st.warning(f"La consulta devolvio {filas:,} filas. Se muestran las "
                       f"primeras {LIMITE_FILAS:,} por estabilidad del navegador.")
            resultado = resultado.head(LIMITE_FILAS)
        st.success(f"Consulta ejecutada: {filas:,} filas devueltas.")
        st.session_state.resultado_flightquery = resultado
        st.dataframe(resultado, width="stretch")

st.markdown("---")
st.header("Diccionario de datos")
st.caption("La documentacion completa, con la trazabilidad hacia los campos "
           "originales, esta en `Base de datos/DICCIONARIO_DE_DATOS.md`.")

diccionarios = {
    "vuelos — tabla de hechos (universo de programacion)": pd.DataFrame({
        "Campo": ["vuelo_id", "numero_vuelo", "fecha_programada", "hora_programada",
                  "franja_id", "origen", "destino", "aircraft_code", "estado_id",
                  "salida_programada", "llegada_programada", "salida_real",
                  "llegada_real", "tiene_metricas"],
        "Tipo": ["Entero", "Texto", "Fecha", "Entero", "Entero", "Texto", "Texto",
                 "Texto", "Entero", "Texto", "Texto", "Texto", "Texto", "Entero"],
        "Descripcion": [
            "Llave primaria. Coincide con el `flight_id` de la fuente, lo que garantiza la trazabilidad.",
            "Codigo comercial del vuelo, por ejemplo PG0134.",
            "Fecha de la salida programada. Llave foranea hacia el calendario.",
            "Hora del dia de la salida programada, de 0 a 23.",
            "Llave foranea hacia la franja horaria.",
            "Aeropuerto de origen. Llave foranea hacia `aeropuertos`.",
            "Aeropuerto de destino. Llave foranea hacia `aeropuertos`.",
            "Modelo de aeronave. Llave foranea hacia `aeronaves`.",
            "Estado del vuelo. Llave foranea hacia `estados`.",
            "Sello de tiempo programado de salida, ya sin el desplazamiento horario.",
            "Sello de tiempo programado de llegada.",
            "Sello real de salida. **Nulo si el vuelo no se opero**; en la fuente venia como la cadena `\\N`.",
            "Sello real de llegada. Nulo en 16.406 registros de la fuente.",
            "Bandera 1/0. Vale 1 si el vuelo genera fila en `metricas`. Materializa la relacion 1:0..1.",
        ]}),
    "metricas — tabla de hechos (universo de operacion)": pd.DataFrame({
        "Campo": ["vuelo_id", "regimen_id", "demora_salida_min", "demora_llegada_min",
                  "recuperacion_min", "duracion_programada_min", "duracion_real_min",
                  "puntual"],
        "Tipo": ["Entero", "Entero", "Entero", "Entero", "Entero", "Entero",
                 "Entero", "Entero"],
        "Descripcion": [
            "Llave primaria y foranea hacia `vuelos`. Su sola existencia indica que el vuelo se opero.",
            "Llave foranea hacia `regimenes`, asignada segun la demora de salida.",
            "**Variable principal.** Minutos entre la salida real y la programada. Campo derivado.",
            "Minutos entre la llegada real y la programada. Nulo si no consta la llegada.",
            "Demora de salida menos demora de llegada. **Positiva si el vuelo recorto tiempo en ruta.**",
            "Tiempo de bloque programado, en minutos.",
            "Tiempo de bloque real, en minutos. Nulo si no consta la llegada.",
            "Bandera 1/0 segun el criterio del sector: salida con 15 minutos de demora o menos.",
        ]}),
    "aeropuertos y aeronaves — dimensiones": pd.DataFrame({
        "Campo": ["aeropuertos.airport_code", "aeropuertos.nombre", "aeropuertos.ciudad",
                  "aeropuertos.zona_horaria", "aeropuertos.longitud", "aeropuertos.latitud",
                  "aeronaves.aircraft_code", "aeronaves.modelo", "aeronaves.alcance_km",
                  "aeronaves.categoria_alcance", "aeronaves.asientos"],
        "Tipo": ["Texto", "Texto", "Texto", "Texto", "Real", "Real", "Texto",
                 "Texto", "Entero", "Texto", "Entero"],
        "Descripcion": [
            "Codigo IATA de tres letras.",
            "Nombre del aeropuerto. **Extraido del campo JSON** de la fuente, clave `en`.",
            "Ciudad. Extraida del mismo modo.",
            "Huso horario en formato IANA.",
            "Longitud en grados decimales. **Extraida de la cadena tipo `point`**, primer valor.",
            "Latitud en grados decimales. Segundo valor de la misma cadena.",
            "Codigo del modelo, por ejemplo 773.",
            "Nombre del modelo. Extraido del campo JSON.",
            "Alcance maximo en kilometros.",
            "**Construido por la investigacion**: Regional, Corto y medio alcance, o Largo alcance.",
            "Capacidad total, contada desde la tabla `seats` de la fuente.",
        ]}),
    "regimenes, franjas, estados y calendario — dimensiones": pd.DataFrame({
        "Campo": ["regimenes.etiqueta", "regimenes.limite_inf_min", "regimenes.limite_sup_min",
                  "franjas.etiqueta", "estados.codigo", "estados.es_operado",
                  "calendario.nombre_dia", "calendario.es_fin_semana"],
        "Tipo": ["Texto", "Entero", "Entero", "Texto", "Texto", "Entero", "Texto", "Entero"],
        "Descripcion": [
            "Nombre del regimen de puntualidad. **Construido por la investigacion** sobre la distribucion observada.",
            "Cota inferior del intervalo, en minutos.",
            "Cota superior. Nula en el regimen severo, que no tiene tope.",
            "Franja horaria de la salida programada, en cinco bloques operativos.",
            "Estado del vuelo tal como lo define la fuente.",
            "Bandera 1/0. Vale 1 en los estados que implican que el vuelo se ejecuto.",
            "Nombre del dia de la semana, en espanol.",
            "Bandera 1/0 para sabado y domingo.",
        ]}),
}

for titulo, tabla in diccionarios.items():
    st.subheader(titulo)
    st.dataframe(tabla, width="stretch", hide_index=True)

st.caption("Escuela de Estadistica y Ciencias Actuariales · Universidad Central "
           "de Venezuela · Material academico de la asignatura Computacion II.")
