"""
pages/02_Marco_Teorico.py
================================================================================
MARCO TEORICO DE LA INVESTIGACION
Puntualidad y regularidad operativa de vuelos domesticos, 2017.
================================================================================

Reune los antecedentes, el marco conceptual de la puntualidad aeronautica, la
naturaleza de la fuente y los fundamentos tecnicos de la arquitectura de datos.
"""

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Marco Teorico", page_icon="📚", layout="wide")
st.markdown("""
<style>
.justificado { text-align: justify; line-height: 1.65; }
.destacado   { color: #2E9E7B; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

st.title("Marco teorico")
st.caption("Fundamentos conceptuales, de la fuente y de la arquitectura de datos")

# ==============================================================================
st.header("1. La puntualidad como indicador")

st.subheader("1.1. El estandar de los quince minutos")
st.markdown("""
<div class="justificado">
La industria aerea no considera "retrasado" cualquier vuelo que salga un minuto
tarde. El indicador universal del sector, conocido como
<b>OTP</b> (<i>on-time performance</i>), define como puntual el vuelo que sale o
llega dentro de una ventana de <span class="destacado">quince minutos</span>
respecto de lo programado. El umbral procede de la practica reguladora
estadounidense y fue adoptado despues por el resto del mundo, de modo que las
cifras de distintas aerolineas resulten comparables.<br><br>

Esta investigacion adopta ese mismo umbral para su indicador de puntualidad, y lo
declara explicitamente en el catalogo de regimenes. Conviene entender lo que
implica: un vuelo que sale con catorce minutos de demora <b>cuenta como puntual</b>.
El indicador mide el cumplimiento de un compromiso operativo, no la ausencia de
retraso.
</div>
""", unsafe_allow_html=True)

st.subheader("1.2. Demora de salida, demora de llegada y recuperacion")
st.markdown("""
<div class="justificado">
Un vuelo tiene dos demoras, y no son la misma. La <b>demora de salida</b> se
produce en tierra: rotacion de la aeronave, embarque, tramitacion, espera de
autorizacion. La <b>demora de llegada</b> es la que sufre el pasajero.<br><br>

Entre ambas media la operacion en ruta, y ahi cabe la <b>recuperacion</b>: la
diferencia entre lo que se perdio en la puerta y lo que se pierde al llegar. Las
aerolineas la buscan deliberadamente mediante el <i>schedule padding</i>, la
practica de programar los vuelos con mas tiempo del estrictamente necesario para
absorber incidencias. Un sistema con holgura muestra recuperaciones positivas; uno
sin ella transmite la demora integra al destino.<br><br>

Medir esa diferencia es uno de los objetivos del estudio, y su resultado en esta
base resulta ser inequivoco.
</div>
""", unsafe_allow_html=True)

st.subheader("1.3. Propagacion de la demora en una red")
st.markdown("""
<div class="justificado">
En una aerolinea de red, una misma aeronave encadena varios vuelos al dia. Si el
primero sale tarde, la demora se arrastra a los siguientes salvo que la
programacion incluya margen suficiente entre rotaciones. Este mecanismo, la
<b>propagacion</b>, explica que en una operacion real la puntualidad se degrade
segun avanza la jornada: los vuelos de la manana salen mejor que los de la tarde.<br><br>

Es una prediccion teorica contrastable, y esta investigacion la contrasta de forma
descriptiva comparando la puntualidad entre franjas horarias. El resultado obtenido
es informativo precisamente por lo que <span class="destacado">no</span> muestra.
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ==============================================================================
st.header("2. La fuente: la base de demostracion de PostgreSQL")

st.markdown("""
<div class="justificado">
El conjunto de datos publicado en Kaggle como <i>Airlines Dataset</i> es la
exportacion a SQLite de <code>demo</code>, la base de demostracion que el proyecto
PostgreSQL distribuye con fines didacticos. Modela una aerolinea de red rusa con
un sistema de reservas completo: reservas, billetes, cupones, vuelos, aeronaves,
asientos y pases de embarque.<br><br>

Sus registros <b>no corresponden a una operacion real</b>: fueron generados de
forma sintetica. Esa condicion no invalida el ejercicio, porque el modelo de
datos, las tecnicas de depuracion y el tratamiento estadistico son los mismos que
exigiria una base real; pero
<span class="destacado">obliga a leer los hallazgos como descripcion de este
conjunto de datos</span> y no como conclusiones sobre la aviacion civil.<br><br>

De hecho, uno de los resultados principales de esta investigacion consiste en
<b>detectar la firma de esa generacion sintetica</b> en la forma de la
distribucion de la demora. Un analisis que no examinara la forma del dato, y se
limitara a reportar la media, no habria advertido nada.
</div>
""", unsafe_allow_html=True)

st.subheader("2.1. Rasgos heredados de PostgreSQL")
rasgos = pd.DataFrame({
    "Rasgo": ["Campos JSON", "Coordenadas como texto", "Nulos disfrazados",
              "Sellos con desplazamiento horario"],
    "Como llega": [
        '{"en": "Yakutsk Airport", "ru": "Якутск"}',
        "(129.77099609375,62.0932998657226562)",
        r"La cadena literal \N en lugar de NULL",
        "2017-07-16 01:50:00+03"],
    "Por que importa": [
        "Ningun motor analitico puede agrupar por un documento JSON sin extraer "
        "antes la clave. Se extrae la version inglesa.",
        "Es la representacion del tipo `point`, en orden longitud-latitud, el "
        "inverso del habitual en cartografia. Invertirlos situaria los "
        "aeropuertos rusos en el oceano Indico.",
        "Es el marcador de nulo de los volcados de PostgreSQL. Compararla como "
        "fecha devuelve nulo en silencio: el calculo no falla, simplemente sale "
        "vacio y nada avisa.",
        "Se recorta el desplazamiento. Es correcto porque todos los sellos "
        "comparten el mismo (+03), extremo que se verifico antes de decidirlo."],
})
st.dataframe(rasgos, width="stretch", hide_index=True)

st.markdown("---")

# ==============================================================================
st.header("3. Bases estadisticas")

col_izq, col_der = st.columns(2)
with col_izq:
    st.subheader("3.1. Distribuciones multimodales")
    st.markdown("""
    <div class="justificado">
    Una distribucion es <b>unimodal</b> cuando sus valores se agrupan en torno a un
    unico centro, y <b>multimodal</b> cuando lo hacen en torno a varios. La
    distincion no es cosmetica: en una distribucion con dos modas separadas, la
    media aritmetica cae en el hueco que las separa y
    <span class="destacado">no describe a ninguna observacion real</span>.<br><br>
    Detectarlo exige mirar la forma del dato, no solo sus resumenes. Por eso este
    estudio incluye un histograma minuto a minuto ademas del cuadro de
    estadisticos: es el unico modo de ver un hueco.
    </div>
    """, unsafe_allow_html=True)

    st.subheader("3.2. Medidas de forma")
    st.markdown("""
    <div class="justificado">
    El <b>coeficiente de asimetria</b> mide si la distribucion tiene una cola mas
    larga a un lado; la <b>curtosis</b>, cuanto peso tienen las colas frente al
    centro. En una distribucion con un nucleo compacto y un grupo alejado, ambos
    coeficientes toman valores muy altos, y esa es justamente la senal numerica
    que acompana a lo que el histograma muestra a simple vista.
    </div>
    """, unsafe_allow_html=True)

with col_der:
    st.subheader("3.3. Medidas robustas frente a la media")
    st.markdown("""
    <div class="justificado">
    La <b>mediana</b> y los <b>cuartiles</b> son medidas robustas: no se mueven
    porque unas pocas observaciones tomen valores extremos. La media, en cambio,
    es sensible a cada valor.<br><br>
    Cuando media y mediana se separan mucho, esa distancia es en si misma un
    resultado: informa de que hay observaciones extremas tirando del promedio. Por
    eso este estudio nunca reporta una sin la otra.
    </div>
    """, unsafe_allow_html=True)

    st.subheader("3.4. Hallazgos negativos")
    st.markdown("""
    <div class="justificado">
    Un <b>hallazgo negativo</b> —comprobar que una relacion esperada no aparece—
    tiene el mismo valor informativo que uno positivo: descarta una hipotesis. La
    teoria de la propagacion predice que la puntualidad se degrada a lo largo de la
    jornada; comprobar que en este conjunto de datos no ocurre es un resultado, no
    una ausencia de resultado, y esta investigacion lo reporta como tal.
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ==============================================================================
st.header("4. Fundamentos de la arquitectura de datos")

st.subheader("4.1. Normalizacion y Tercera Forma Normal")
st.markdown("""
<div class="justificado">
La teoria de la normalizacion, formulada por <b>Edgar F. Codd</b>, elimina
progresivamente la redundancia y las anomalias de actualizacion. Este proyecto
normaliza hasta la <span class="destacado">Tercera Forma Normal</span>.<br><br>

El caso mas ilustrativo aqui es el de la aeronave: su modelo, su alcance y su
capacidad no dependen del vuelo, sino del aparato. Mantenerlos en la tabla de
hechos seria una dependencia transitiva
<code>vuelo_id → aircraft_code → modelo</code>. El modelo los traslada a la
dimension <code>aeronaves</code>, donde cada aparato se describe una sola vez.
</div>
""", unsafe_allow_html=True)

st.subheader("4.2. Modelo dimensional y relacion 1:0..1")
st.markdown("""
<div class="justificado">
El <b>modelo dimensional</b> de <b>Ralph Kimball</b> organiza el almacen analitico
en torno a tablas de <i>hechos</i> rodeadas de tablas de <i>dimension</i>.<br><br>

Este proyecto introduce una particularidad: sus dos tablas de hechos mantienen una
relacion <span class="destacado">1:0..1</span> y no 1:1. Todo vuelo existe en
<code>vuelos</code>, pero solo genera fila en <code>metricas_puntualidad</code> si
llego a operarse. Esa asimetria es deliberada: si se hubiese filtrado desde el
inicio, el hecho de que la mitad de la programacion estuviese a futuro habria
quedado invisible.
</div>
""", unsafe_allow_html=True)

st.subheader("4.3. Procesamiento analitico en linea (OLAP) y almacenamiento columnar")
st.markdown("""
<div class="justificado">
Los motores de bases de datos se disenan para uno de dos perfiles. El perfil
<b>OLTP</b> atiende muchas operaciones pequenas sobre filas completas —y es
exactamente para lo que fue disenada la base de origen, un sistema de reservas—;
el perfil <b>OLAP</b> atiende pocas consultas que leen pocas columnas de muchisimas
filas y las agregan.<br><br>

Esta investigacion es enteramente OLAP. De ahi la decision de trasladar el esquema
normalizado a <b>Parquet</b>, formato columnar que habilita la lectura selectiva de
columnas, el descarte de bloques que no cumplen el filtro y una compresion muy
superior: en este proyecto, <b>once veces</b> respecto de la base normalizada.<br><br>

Sobre esos archivos opera <b>DuckDB</b>, motor analitico embebido de ejecucion
vectorizada que consulta los Parquet directamente, sin cargarlos en memoria.
</div>
""", unsafe_allow_html=True)

st.markdown("---")
st.caption("Escuela de Estadistica y Ciencias Actuariales · Universidad Central "
           "de Venezuela · Material academico de la asignatura Computacion II.")
