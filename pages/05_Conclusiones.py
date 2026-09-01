"""
pages/05_Conclusiones.py
================================================================================
CONCLUSIONES DE LA INVESTIGACION
Puntualidad y regularidad operativa de vuelos domesticos, 2017.
================================================================================
"""

import streamlit as st

st.set_page_config(page_title="Conclusiones", page_icon="🏁", layout="wide")
st.title("Conclusiones")
st.caption("Puntualidad operativa de vuelos domesticos · julio-septiembre de 2017")

# ==============================================================================
st.header("1. Sobre la infraestructura de datos construida")

with st.expander("1.1. Depuracion de una fuente heredada", expanded=True):
    st.markdown("""
    La base original es la exportacion a SQLite de una base PostgreSQL pensada para
    **operar** un sistema de reservas, no para analizarlo. Su depuracion exigio
    resolver cuatro problemas que no se anuncian y que, de pasarse por alto,
    producen resultados incorrectos **sin que nada falle**:

    - **Nulos disfrazados.** Las horas reales de los vuelos no operados contienen la
      cadena literal `\\N`, marcador de nulo de los volcados de PostgreSQL.
      `julianday('\\N')` devuelve nulo en silencio: el calculo no da error, la demora
      simplemente sale vacia.
    - **Campos JSON.** Nombres de aeropuerto, ciudad y modelo de aeronave llegan como
      documentos `{"en": ..., "ru": ...}`.
    - **Coordenadas como texto**, en el formato del tipo `point` de PostgreSQL y en
      orden **longitud-latitud**, el inverso del habitual en cartografia.
    - **Desplazamiento horario pegado al sello de tiempo.** Se verifico que todos los
      registros comparten el mismo (+03) antes de decidir recortarlo.

    El esquema resultante es una estrella en Tercera Forma Normal con seis
    dimensiones y dos tablas de hechos. Los **diez controles de integridad**
    ejecutados al cierre del ETL devolvieron cero incidencias sobre 33.121 vuelos.
    """)

with st.expander("1.2. La relacion 1:0..1 como instrumento metodologico"):
    st.markdown("""
    Un diseno convencional habria descartado desde el inicio los vuelos sin hora real
    de salida, quedandose con los 16.773 utiles.

    Este modelo no lo hace: carga los 33.121 en `vuelos`, los marca con una bandera
    y genera fila en `metricas_puntualidad` solo para los operados. La consecuencia
    es que **el hecho de que la mitad de la programacion no se ejecutara se vuelve
    medible en lugar de invisible**, y el aplicativo puede advertirlo en su primera
    pantalla.
    """)

with st.expander("1.3. Eficiencia del Data Lake columnar"):
    st.markdown("""
    La conversion a **Parquet con compresion ZSTD** redujo el volumen de 6,46 MB a
    **0,59 MB**, un factor de **once veces**. El Data Lake completo cabe holgadamente
    en el repositorio, de modo que el aplicativo es **autocontenido**: quien lo clone
    puede ejecutarlo sin descargar los 109 MB de la base original.
    """)

st.markdown("---")

# ==============================================================================
st.header("2. Primer resultado: solo la mitad de la programacion se ejecuto")
st.markdown("""
De los 33.121 vuelos programados, **16.773** tienen hora real de salida: el
**50,64%**. No es una perdida de datos, sino la naturaleza de la fuente: es una
fotografia tomada a mitad de temporada, y los 16.348 restantes estaban programados
a futuro respecto del corte, salvo **414 cancelados**.
""")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Vuelos programados", "33.121")
c2.metric("Operados", "16.773", "50,64 %")
c3.metric("Cancelados", "414", "1,25 %")
c4.metric("Puntualidad", "95,23 %")

st.error("""
**Consecuencia metodologica, aplicada en todo el aplicativo.** Los estadisticos de
demora describen **unicamente al universo de operacion**, no al conjunto de la
programacion. Toda pantalla declara sobre cual de los dos universos se calcula
cada cifra.
""")

st.markdown("---")

# ==============================================================================
st.header("3. Hallazgos principales")

st.subheader("3.1. La demora no es un continuo: es bimodal")
st.markdown("""
El resultado central. La demora de salida no se distribuye de forma continua:

| Regimen | Vuelos | % | Demora media |
|---|---:|---:|---:|
| Salida puntual (0 min) | 717 | 4,27 % | 0,00 min |
| Demora minima (1–5 min) | 13.999 | 83,46 % | 2,85 min |
| Demora leve (6–15 min) | 1.257 | 7,49 % | 6,54 min |
| **Demora moderada (16–59 min)** | **0** | **0,00 %** | — |
| Demora severa (60 min o mas) | 800 | 4,77 % | **195,69 min** |

**El regimen intermedio esta literalmente vacio.** No hay ni un solo vuelo entre 16
y 59 minutos de demora; de hecho, el analisis por decenas muestra que el vacio se
extiende desde los 12 hasta los 120 minutos.

Una operacion real produce una distribucion continua y decreciente. Un hueco de
hora y media sin un solo caso **no ocurre en un sistema real**: es la firma del
procedimiento que genero estos datos de forma sintetica.
""")

st.subheader("3.2. La demora no se recupera en ruta")
st.markdown("""
La recuperacion media —demora de salida menos demora de llegada— es de
**−0,006 minutos**: cero en la practica. Y no cambia al controlar por duracion del
vuelo: en los cuatro cuartiles, desde vuelos de 25 minutos hasta de 530, la
recuperacion media va de −0,0034 a +0,0077 minutos.

**Lo que se pierde en la puerta de embarque llega integro al destino.** El
resultado contradice la practica del *schedule padding*, y es otro indicio de que
el retraso de llegada se genero como copia del de salida sin modelar la operacion
en ruta.
""")

st.subheader("3.3. Los minutos de retraso se concentran en muy pocos vuelos")
st.markdown("""
- **487 vuelos** (el 2,9% de los operados) acumulan el **50%** de todos los minutos
  de demora del periodo.
- **1.893 vuelos** (el 11,3%) acumulan el **80%**.

Es la razon estadistica por la que la demora media (12,21 minutos) no describe a
ningun vuelo real: la mediana es de **3 minutos**.
""")

st.subheader("3.4. Ni la hora del dia ni el dia de la semana explican nada")
st.markdown("""
La teoria de la propagacion predice que la puntualidad se degrada segun avanza la
jornada, porque una misma aeronave encadena vuelos y arrastra el retraso
acumulado. **Aqui esa degradacion no aparece**: la puntualidad se mueve entre el
93,56% y el 96,83% sin patron reconocible ni por franja ni por dia. El domingo por
la tarde sale mejor que el lunes por la manana.

Comprobar que una relacion esperada no existe descarta una hipotesis, y eso es un
resultado. En este caso, ademas, refuerza la lectura del hallazgo 3.1.
""")

st.subheader("3.5. Las cancelaciones si distinguen a la flota")
st.markdown("""
La tasa de cancelacion varia por un factor de **trece** entre extremos: del 2,00%
del Bombardier CRJ-200 al 0,154% del Airbus A321-200. Los aparatos regionales y de
corto alcance cancelan mas que los de fuselaje ancho, patron coherente con el tipo
de rutas que cubren.

Conviene la advertencia: esto **no mide la fiabilidad tecnica del avion**. Un
modelo no se cancela a si mismo; lo que la tabla describe es el tipo de operacion
en que cada aparato se emplea.
""")

st.warning("""
**Implicacion estadistica transversal.** En una distribucion bimodal, la media
aritmetica cae en el hueco que separa las dos modas y **no describe a ninguna
observacion real**. Reportar solo la media de 12,21 minutos daria una imagen falsa
de esta operacion. Es la razon por la que todas las pantallas del aplicativo
muestran la mediana junto a la media, y por la que se incluye un histograma minuto
a minuto ademas del cuadro de estadisticos: **un hueco solo se ve mirando la forma
del dato**.
""")

st.markdown("---")

# ==============================================================================
st.header("4. Limitaciones del estudio")
st.markdown("""
Se declaran explicitamente las siguientes limitaciones:

1. **La fuente es sintetica.** Es la limitacion principal. Los datos proceden de la
   base de demostracion `demo` de PostgreSQL y no de una operacion real. Los
   hallazgos describen este conjunto de datos, no la aviacion civil. El modelo de
   datos y las tecnicas aplicadas si son transferibles a una base real.

2. **Solo la mitad de la programacion se opero.** El universo de analisis es el
   50,64% del de programacion, y no es una muestra aleatoria de el: son los vuelos
   anteriores a la fecha de corte.

3. **Periodo corto.** Dos meses de operacion no permiten describir estacionalidad
   anual ni comparar temporadas.

4. **Inconsistencia declarada.** Ocho vuelos marcados como cancelados tienen hora
   real de salida y de llegada. Se conservan tal cual y se declara el problema, en
   lugar de corregirlo en silencio.

5. **Las comparaciones entre aeronaves o aeropuertos no miden calidad.** Cada
   aparato y cada nodo operan sobre rutas y condiciones distintas; el aplicativo
   muestra siempre el volumen junto a la media para que esa heterogeneidad quede a
   la vista.

6. **Naturaleza descriptiva del diseno.** No se realizaron pruebas de significacion
   ni se estimaron relaciones causales.
""")

st.markdown("---")

# ==============================================================================
st.header("5. Lineas de continuidad")
st.markdown("""
Se sugieren a futuros equipos las siguientes extensiones, viables sobre el modelo
ya construido:

- **Contrastar con una base real.** Repetir exactamente este analisis sobre datos
  de una autoridad aeronautica —el Bureau of Transportation Statistics publica
  microdatos abiertos— permitiria comprobar cuales de estos hallazgos son
  propiedades del fenomeno y cuales artefactos de la generacion sintetica. Es la
  continuacion natural y la mas valiosa.

- **Analisis de propagacion por rotacion.** El modelo conserva `numero_vuelo` y
  `aircraft_code`; reconstruir la secuencia diaria de cada aeronave permitiria medir
  si la demora de un vuelo predice la del siguiente.

- **Modelacion de la duracion de bloque.** El campo `duracion_real_min` esta
  calculado y apenas se explota; permitiria estudiar el margen de programacion por
  ruta.

- **Analisis de supervivencia sobre la demora.** La pregunta "¿cual es la
  probabilidad de que un vuelo retrasado siga sin salir al minuto N?" corresponde a
  un modelo de supervivencia, que excede el nivel descriptivo de este trabajo pero
  que el modelo de datos ya soporta.
""")

st.markdown("---")
st.caption("Escuela de Estadistica y Ciencias Actuariales · Universidad Central "
           "de Venezuela · Material academico de la asignatura Computacion II.")
