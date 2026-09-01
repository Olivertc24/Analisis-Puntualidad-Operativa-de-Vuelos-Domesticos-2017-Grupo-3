"""
pages/01_Marco_Metodologico.py
================================================================================
MARCO METODOLOGICO DE LA INVESTIGACION
Puntualidad y regularidad operativa de vuelos domesticos, 2017.
================================================================================

Documenta el diseno de la investigacion: el problema, la pregunta que la ordena,
su nivel, la justificacion, los objetivos, la delimitacion de los dos universos
y la operacionalizacion de las variables. No realiza calculos.
"""

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Marco Metodologico", page_icon="📐", layout="wide")

st.markdown("""
<style>
.justificado { text-align: justify; line-height: 1.65; }
.destacado   { color: #2E9E7B; font-weight: 700; }
.tarjeta { background-color:#161B1F; border-left:5px solid #2E9E7B; border-radius:6px;
           padding:16px 20px; margin-bottom:12px; height:100%; }
.caja-pregunta { background-color:#10161A; border-top:4px solid #2E9E7B;
                 border-bottom:4px solid #2E9E7B; padding:28px; border-radius:8px;
                 margin:30px 0; }
.etiqueta { color:#2E9E7B; font-size:13px; text-transform:uppercase;
            letter-spacing:2px; display:block; margin-bottom:10px; }
.texto-pregunta { color:#FFFFFF; font-size:21px; font-style:italic;
                  line-height:1.55; text-align:center; margin:0; }
</style>
""", unsafe_allow_html=True)

st.image("assets/banner_puntualidad.png", width="stretch")
st.title("Marco metodologico")
st.caption("Puntualidad operativa de vuelos domesticos · julio-septiembre de 2017")

# ==============================================================================
st.header("1. Planteamiento del problema")
st.markdown("""
<div class="justificado">
La puntualidad es el indicador con el que una aerolinea se mide a si misma y con
el que la miden sus pasajeros. Pero es un indicador enganoso si se resume en un
solo numero: decir que una operacion tiene una demora media de doce minutos no
informa de si esos doce minutos se reparten de forma pareja entre todos los
vuelos o si son el promedio entre una mayoria que sale casi a la hora y una
minoria que sale con horas de retraso.<br><br>

Esa distincion no es academica. Una operacion con demoras pequenas y homogeneas
y otra con demoras nulas salpicadas de episodios severos pueden tener
<span class="destacado">exactamente la misma media</span> y exigir respuestas de
gestion opuestas: la primera pide ajustes de programacion; la segunda, capacidad
de reaccion ante incidentes.<br><br>

La base analizada permite abordar esa pregunta. Recoge la programacion completa
de una aerolinea de red durante dos meses de 2017 —33.121 vuelos entre 104
aeropuertos— con las horas programadas y las reales de salida y de llegada. Con
esos cuatro sellos de tiempo se puede reconstruir no solo cuanto se retrasa un
vuelo, sino <b>como se distribuye</b> ese retraso y <b>si se recupera en ruta</b>.<br><br>

Ahora bien, el dato crudo no responde nada por si mismo. La fuente es la
exportacion a SQLite de una base PostgreSQL pensada para <i>operar</i> un sistema
de reservas: los nombres de aeropuerto y de aeronave vienen como documentos JSON,
las coordenadas como cadenas de texto y las horas de los vuelos aun no operados
contienen la cadena literal <code>\\N</code> en lugar de un nulo. Para que el
conocimiento sea, en terminos de <b>Arias (2012)</b>,
<span class="destacado">metodicamente obtenido y sistematicamente organizado</span>,
hace falta un trabajo previo de normalizacion y depuracion que es parte
sustantiva de esta investigacion.
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="caja-pregunta">
    <span class="etiqueta">Interrogante de investigacion</span>
    <p class="texto-pregunta">
    "¿Como se distribuye la demora de salida de los vuelos domesticos operados
    entre julio y septiembre de 2017, y como se relaciona esa demora con la hora
    del dia, el dia de la semana, el modelo de aeronave y el aeropuerto de
    origen?"
    </p>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
st.header("2. Nivel y diseno de la investigacion")

with st.expander("2.1. Nivel descriptivo", expanded=True):
    st.markdown("""
    <div class="justificado">
    Conforme a los objetivos planteados, la investigacion es de
    <span class="destacado">nivel descriptivo</span>. Segun <b>Arias (2012)</b>, la
    investigacion descriptiva consiste en la caracterizacion de un hecho o fenomeno
    con el fin de establecer su estructura o comportamiento.<br><br>

    El estudio se limita a caracterizar el comportamiento de la demora en el
    universo delimitado. No se formulan hipotesis a contrastar ni se realizan
    pruebas de significacion; las diferencias reportadas entre aeropuertos,
    aeronaves o franjas horarias son <b>diferencias observadas</b>, no inferencias
    sobre una poblacion mayor.<br><br>

    Al trabajar con la totalidad de los registros disponibles y no con una muestra,
    las medidas calculadas son <b>parametros del universo</b> y no estimadores. En
    consecuencia, todas las formulas de dispersion empleadas son poblacionales.
    </div>
    """, unsafe_allow_html=True)

with st.expander("2.2. Naturaleza de la fuente: una advertencia necesaria"):
    st.markdown("""
    <div class="justificado">
    La base analizada es la exportacion de <code>demo</code>, la base de
    demostracion que PostgreSQL distribuye con fines didacticos. Sus registros
    <b>no corresponden a una operacion real</b>: fueron generados de forma
    sintetica para ilustrar un modelo de datos de aerolinea.<br><br>

    Esto no invalida el ejercicio —el modelo de datos, las tecnicas de depuracion y
    el tratamiento estadistico son exactamente los mismos que exigiria una base
    real—, pero <span class="destacado">obliga a leer los hallazgos como
    descripcion de este conjunto de datos y no como conclusiones sobre la aviacion
    civil</span>. La investigacion declara esa condicion en cada resultado que la
    delata, y de hecho uno de sus hallazgos principales consiste precisamente en
    detectar la firma de esa generacion sintetica en la forma de la distribucion.
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ==============================================================================
st.header("3. Delimitacion: los dos universos del estudio")
st.markdown("""
<div class="justificado">
La investigacion maneja <b>dos universos anidados</b> y nunca los confunde. Toda
cifra publicada en el aplicativo declara sobre cual de los dos se calcula.
</div>
""", unsafe_allow_html=True)

col_a, col_b = st.columns(2)
with col_a:
    st.markdown("""
    <div class="tarjeta" style="border-left-color:#1E6091;">
    <h4 style="color:#4FA3F7; margin-top:0;">Universo de programacion</h4>
    <p style="font-size:26px; font-weight:700; color:#FFF; margin:6px 0;">33.121</p>
    <p style="font-size:14px;">Todos los vuelos programados en la base entre el 16
    de julio y el 14 de septiembre de 2017.<br><br>
    <b>Se emplea para:</b> medir que porcion de la programacion llego a ejecutarse
    y describir los estados del vuelo, incluidas las cancelaciones.</p>
    </div>""", unsafe_allow_html=True)
with col_b:
    st.markdown("""
    <div class="tarjeta" style="border-left-color:#2E9E7B;">
    <h4 style="color:#2E9E7B; margin-top:0;">Universo de operacion</h4>
    <p style="font-size:26px; font-weight:700; color:#FFF; margin:6px 0;">16.773</p>
    <p style="font-size:14px;">Los vuelos con hora real de salida registrada: el
    <b>50,64%</b> del universo de programacion.<br><br>
    <b>Se emplea para:</b> todos los estadisticos de demora, recuperacion y
    puntualidad. Ninguna medida de demora se atribuye jamas al universo completo.</p>
    </div>""", unsafe_allow_html=True)

st.info("""
**Por que la mitad de la programacion no se opero.** No es una anomalia ni una
perdida de datos: la base es una **fotografia tomada a mitad de temporada**. Los
16.348 vuelos sin hora real estaban programados a futuro respecto del momento del
corte, salvo 406 cancelados. Es la razon por la que el modelo de datos carga todos
los vuelos y solo genera metricas para los operados, en lugar de filtrar desde el
principio y perder de vista ese hecho.
""")

st.markdown("")
col_u, col_un, col_t = st.columns(3)
with col_u:
    st.markdown("""
    <div class="tarjeta"><h4 style="color:#2E9E7B; margin-top:0;">Unidad de analisis</h4>
    <p style="font-size:14px;">Cada <b>vuelo</b> individual, identificado por
    <code>vuelo_id</code> y trazable hasta la fuente por el mismo
    <code>flight_id</code>.</p></div>""", unsafe_allow_html=True)
with col_un:
    st.markdown("""
    <div class="tarjeta"><h4 style="color:#2E9E7B; margin-top:0;">Variable principal</h4>
    <p style="font-size:14px;"><b>Demora de salida</b>, en minutos entre la hora
    real y la programada. Se calcula en el ETL; la fuente solo aporta los dos
    sellos de tiempo.</p></div>""", unsafe_allow_html=True)
with col_t:
    st.markdown("""
    <div class="tarjeta"><h4 style="color:#2E9E7B; margin-top:0;">Tecnicas</h4>
    <p style="font-size:14px;">Analisis documental de fuente secundaria y
    tratamiento estadistico descriptivo: distribuciones de frecuencias y medidas
    de tendencia central, posicion, dispersion y forma.</p></div>""",
    unsafe_allow_html=True)

st.markdown("---")

# ==============================================================================
st.header("4. Criterios de depuracion aplicados")
st.markdown("""
| Criterio | Decision | Justificacion |
|---|---|---|
| Horas reales con el valor `\\N` | Se convierten a nulo real | Es el marcador de nulo de los volcados de PostgreSQL. Compararlas como fechas sin depurarlas devuelve nulos en silencio, sin que nada avise del error. |
| Sello de tiempo con desplazamiento horario | Se recorta a los 19 primeros caracteres | Todos los sellos de la base comparten el mismo desplazamiento (+03), extremo verificado antes de decidirlo: no hay husos mezclados que corregir. |
| Nombres y ciudades en JSON | Se extrae la clave `"en"` | La fuente entrega documentos `{"en": ..., "ru": ...}`. Ningun motor puede agrupar por eso sin extraerlo. |
| Coordenadas como texto | Se descomponen en longitud y latitud | La fuente usa la representacion del tipo `point` de PostgreSQL, en orden **longitud-latitud**, el inverso del habitual en cartografia. Invertirlos situaria los aeropuertos en el oceano Indico. |
| Vuelos cancelados con hora real de salida | **Se conservan y se declara la inconsistencia** | Ocho vuelos marcados como cancelados tienen salida y llegada reales. Corregirlos en silencio ocultaria un problema de calidad del dato que el lector debe conocer. |
| Vuelos sin hora real de salida | Se cargan con `tiene_metricas = 0` | Permite medir la ejecucion de la programacion en lugar de ocultarla. |
""")

st.markdown("---")

# ==============================================================================
st.header("5. Definicion de objetivos")
st.markdown("""
<div style="background-color:#161B1F; border-top:4px solid #2E9E7B;
            border-bottom:4px solid #2E9E7B; padding:24px; border-radius:6px;
            margin-bottom:22px;">
    <p style="color:#2E9E7B; font-weight:700; text-transform:uppercase;
              letter-spacing:1px; font-size:13px; margin-bottom:8px;">Objetivo general</p>
    <p style="color:#FFF; font-size:18px; font-style:italic; line-height:1.55; margin:0;">
    Caracterizar la distribucion de la demora de salida de los vuelos domesticos
    operados entre julio y septiembre de 2017, y describir su relacion con la hora
    del dia, el dia de la semana, el modelo de aeronave y el aeropuerto de origen.
    </p>
</div>
""", unsafe_allow_html=True)

st.subheader("Objetivos especificos")
for i, obj in enumerate([
    "Normalizar la base original hasta la Tercera Forma Normal mediante un esquema "
    "en estrella, depurando los campos JSON, las coordenadas en texto y los nulos "
    "disfrazados que arrastra la exportacion de PostgreSQL.",
    "Construir las medidas de puntualidad que la fuente no provee: demora de "
    "salida y de llegada, recuperacion en ruta y duracion real de bloque.",
    "Cuantificar que porcion de la programacion llego a ejecutarse, como condicion "
    "previa a cualquier lectura de los resultados de demora.",
    "Calcular los estadisticos descriptivos de tendencia central, posicion, "
    "dispersion y forma de la demora de salida.",
    "Describir la forma de la distribucion de la demora y verificar si se comporta "
    "como un continuo o como regimenes separados.",
    "Describir el perfil de la puntualidad por franja horaria, dia de la semana, "
    "modelo de aeronave y aeropuerto de origen.",
    "Desarrollar un aplicativo en Streamlit y un tablero en Tableau que permitan "
    "explorar la investigacion y reproducir sus resultados.",
], start=1):
    st.markdown(f"**{i}.** {obj}")

st.markdown("---")

# ==============================================================================
st.header("6. Operacionalizacion de las variables")
variables = pd.DataFrame({
    "Dimension": ["Puntualidad", "Puntualidad", "Puntualidad", "Puntualidad",
                  "Ejecucion", "Temporalidad", "Temporalidad", "Temporalidad",
                  "Flota", "Flota", "Territorio"],
    "Variable / indicador": [
        "Demora de salida", "Demora de llegada", "Recuperacion en ruta",
        "Regimen de puntualidad", "Ejecucion de la programacion",
        "Franja horaria", "Dia de la semana", "Fecha de operacion",
        "Modelo de aeronave", "Categoria de alcance", "Aeropuerto de origen"],
    "Naturaleza": [
        "Cuantitativa discreta", "Cuantitativa discreta", "Cuantitativa discreta",
        "Cualitativa ordinal", "Cualitativa dicotomica",
        "Cualitativa ordinal", "Cualitativa ordinal", "Cuantitativa discreta",
        "Cualitativa nominal", "Cualitativa ordinal", "Cualitativa nominal"],
    "Campo en el modelo": [
        "metricas_puntualidad.demora_salida_min",
        "metricas_puntualidad.demora_llegada_min",
        "metricas_puntualidad.recuperacion_min",
        "regimenes_puntualidad.etiqueta",
        "vuelos.tiene_metricas",
        "franjas_horarias.etiqueta", "calendario_operativo.nombre_dia",
        "vuelos.fecha_programada",
        "aeronaves.modelo", "aeronaves.categoria_alcance", "aeropuertos.ciudad"],
    "Medidas aplicables": [
        "Media, mediana, cuartiles, percentiles, desviacion, CV, asimetria, curtosis",
        "Media y mediana sobre el subconjunto con llegada registrada",
        "Media y rango; el signo indica si se recorto o se perdio tiempo",
        "Frecuencias absolutas, relativas y acumuladas",
        "Proporcion",
        "Frecuencias y puntualidad por grupo", "Frecuencias y puntualidad por grupo",
        "Serie temporal diaria",
        "Frecuencias, demora media por grupo", "Comparacion entre bloques homogeneos",
        "Frecuencias, ranking, desvio respecto de la media global"],
})
st.dataframe(variables, width="stretch", hide_index=True)

st.markdown("---")

# ==============================================================================
st.header("7. Procesamiento de la informacion")
fases = pd.DataFrame({
    "Fase": ["1. Diseno del esquema", "2. Carga de catalogos",
             "3. Extraccion, transformacion y carga", "4. Data Lake analitico"],
    "Script": ["01_creacion_esquema.py", "02_poblacion_catalogos.py",
               "03_procesamiento_carga.py", "04_exportacion_parquet.py"],
    "Descripcion": [
        "Esquema en estrella en Tercera Forma Normal: seis dimensiones y dos tablas "
        "de hechos en relacion 1:0..1, con llaves foraneas e indices de apoyo.",
        "Catalogos construidos por la investigacion (regimenes, franjas, estados) y "
        "catalogos depurados de la fuente (aeropuertos, aeronaves, calendario), "
        "extrayendo los campos JSON y descomponiendo las coordenadas.",
        "Depuracion de los nulos disfrazados, normalizacion de los sellos de tiempo "
        "y calculo de las medidas de puntualidad, con verificacion posterior de "
        "integridad referencial.",
        "Exportacion a formato columnar Parquet con compresion ZSTD, sobre el que "
        "el aplicativo monta un motor DuckDB en memoria.",
    ]})
st.dataframe(fases, width="stretch", hide_index=True)

st.success("""
**Verificacion de la carga.** Al finalizar el ETL se ejecutan diez controles de
integridad: conteos por tabla, ausencia de vuelos huerfanos respecto de cada una
de las cuatro dimensiones referenciadas, ausencia de metricas huerfanas,
coherencia entre la bandera `tiene_metricas` y la existencia de fila en
`metricas_puntualidad`, y ausencia de demoras negativas. Los diez controles
devuelven cero incidencias sobre los 33.121 vuelos cargados.
""")

st.markdown("---")
st.caption("Escuela de Estadistica y Ciencias Actuariales · Universidad Central "
           "de Venezuela · Material academico de la asignatura Computacion II.")
