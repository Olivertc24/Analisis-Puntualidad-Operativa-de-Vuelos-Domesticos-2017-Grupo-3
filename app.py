"""
app.py
================================================================================
TABLERO PRINCIPAL DEL APLICATIVO
Investigacion: Puntualidad y regularidad operativa de vuelos domesticos
Julio-septiembre de 2017. 33.121 vuelos programados, 16.773 operados.
Escuela de Estadistica y Ciencias Actuariales (EECA-UCV) — Computacion II
================================================================================

Vista de sintesis, en este orden deliberado:

    0. La ejecucion de la programacion, porque la mitad de los vuelos de la base
       estaba a futuro en el momento del corte y ninguna medida de demora puede
       leerse sin saberlo.
    1. La bimodalidad de la demora: el hallazgo central del estudio.
    2. La demora frente al calendario y la jornada.
    3. El perfil por aeronave y por aeropuerto.

Toda la estadistica proviene de `src/stats_logic.py`; aqui solo se dibuja.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from src.query_manager import get_query_manager
from src.stats_logic import (
    PALETA, COLOR_REGIMEN, COLOR_CATEGORIA,
    formato_numero, formato_demora,
    ejecucion_programacion, estados_programacion, obtener_indicadores,
    distribucion_regimenes, histograma_demora, puntualidad_por_franja,
    puntualidad_por_aeronave, serie_diaria, ranking_aeropuertos,
    mapa_aeropuertos, lectura_automatica,
)

st.set_page_config(
    page_title="Puntualidad Operativa | Vuelos 2017",
    page_icon="🛫",
    layout="wide",
    initial_sidebar_state="expanded",
)

qm = get_query_manager()
if not qm.esta_completo():
    st.error("No se encontro el Data Lake. Faltan en `data/`: "
             + ", ".join(qm.tablas_faltantes))
    st.info("Ejecute en orden los scripts de `Base de datos/`:\n\n"
            "```\npython 01_creacion_esquema.py\npython 02_poblacion_catalogos.py\n"
            "python 03_procesamiento_carga.py\npython 04_exportacion_parquet.py\n```")
    st.stop()


# ==============================================================================
# BARRA LATERAL
# ==============================================================================
with st.sidebar:
    st.title("🛫 Panel operativo")
    st.caption("Los controles delimitan el subconjunto sobre el que se calculan "
               "todos los estadisticos de esta pantalla.")

    categoria_sel = st.radio(
        "Categoria de aeronave",
        ["Todas", "Regional", "Corto y medio alcance", "Largo alcance"],
        help="Agrupa los nueve modelos de la flota segun su alcance. Un "
             "turbohelice regional y un Boeing 777 no operan en el mismo regimen.")

    franja_sel = st.selectbox(
        "Franja horaria de salida",
        ["Todas", "Madrugada (00-05)", "Manana (06-11)", "Mediodia (12-15)",
         "Tarde (16-19)", "Noche (20-23)"])

    dia_sel = st.selectbox(
        "Dia de la semana",
        ["Todos", "Lunes", "Martes", "Miercoles", "Jueves", "Viernes",
         "Sabado", "Domingo"])

    st.markdown(
        f"<div style='border-left:6px solid {PALETA['verde_puntual']}; "
        f"padding:10px 14px; background:#161B1F; border-radius:4px; margin-top:10px;'>"
        f"<span style='color:{PALETA['verde_puntual']}; font-weight:700;'>Filtro activo</span><br>"
        f"<span style='color:#B9C2C9; font-size:13px;'>{categoria_sel} · {franja_sel} · {dia_sel}</span>"
        f"</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.caption("Fuente: *Airlines Dataset* (Kaggle), exportacion de la base de "
               "demostracion `demo` de PostgreSQL. Vuelos domesticos operados "
               "entre el 16 de julio y el 14 de septiembre de 2017.")


# ==============================================================================
# ENCABEZADO E INDICADORES
# ==============================================================================
st.image("assets/banner_puntualidad.png", width="stretch")
st.markdown("#### Regularidad de la operacion, julio-septiembre de 2017")

ejecucion = ejecucion_programacion(qm, categoria_sel, dia_sel, "Todos")
ind = obtener_indicadores(qm, categoria_sel, franja_sel, dia_sel, "Todos")

if ind["vuelos"] == 0:
    st.warning("Ningun vuelo operado cumple los criterios seleccionados.")
    st.stop()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Vuelos operados", formato_numero(ind["vuelos"]))
c2.metric("Puntualidad", f"{ind['pct_puntual']:,.2f} %",
          help="Criterio del sector: salida con 15 minutos de demora o menos.")
c3.metric("Demora media", formato_demora(ind["demora_media"]))
c4.metric("Demora mediana", formato_demora(ind["demora_mediana"]))
c5.metric("Recuperacion en ruta", f"{ind['recuperacion_media']:,.3f} min",
          help="Demora de salida menos demora de llegada. Positiva si el vuelo "
               "recorto tiempo en el aire.")

st.info(lectura_automatica(ind, ejecucion))
st.markdown("---")


# ==============================================================================
# BLOQUE 0 — EJECUCION DE LA PROGRAMACION
# ==============================================================================
st.header("0. Ejecucion de la programacion")
st.markdown(
    "Antes de describir demoras hay que responder una pregunta previa: "
    "**¿que porcion de los vuelos programados llego a ejecutarse?** La base es "
    "una fotografia tomada a mitad de temporada, y la mitad de su programacion "
    "estaba todavia a futuro."
)

col_izq, col_der = st.columns([1, 2])
with col_izq:
    st.metric("Vuelos programados", formato_numero(ejecucion["programados"]))
    st.metric("Con hora real de salida", formato_numero(ejecucion["operados"]))
    st.metric("Ejecucion", f"{ejecucion['pct_operados']:,.2f} %")
    st.metric("Cancelados", formato_numero(ejecucion["cancelados"]))
    st.caption("El universo de analisis de esta investigacion es el subconjunto "
               "operado. Los estadisticos de demora **no** describen al conjunto "
               "de la programacion.")

with col_der:
    df_estados = estados_programacion(qm, categoria_sel, dia_sel, "Todos")
    figura = px.bar(
        df_estados, x="Vuelos", y="Estado", orientation="h",
        color="Estado", text="Vuelos",
        color_discrete_sequence=[PALETA["verde_puntual"], PALETA["verde_claro"],
                                 PALETA["ambar"], PALETA["azul_operativo"],
                                 PALETA["naranja"], PALETA["rojo_severo"]],
        hover_data=["Descripcion", "% del total"],
        title="Vuelos por estado en el momento del corte")
    figura.update_layout(template="plotly_dark", height=380, showlegend=False,
                         margin=dict(l=20, r=20, t=60, b=20))
    st.plotly_chart(figura, width="stretch")

st.warning(
    "**Anomalia documentada.** De los 414 vuelos marcados como cancelados, "
    "**8 tienen hora real de salida y de llegada**: no pueden estar cancelados si "
    "despegaron y aterrizaron. Se conservan tal cual y se declara la "
    "inconsistencia, en lugar de corregirla en silencio."
)
st.markdown("---")


# ==============================================================================
# BLOQUE 1 — LA BIMODALIDAD DE LA DEMORA
# ==============================================================================
st.header("1. La demora no es un continuo: es bimodal")
st.markdown(
    "El hallazgo central de la investigacion. La demora de salida no se "
    "distribuye de forma continua entre cero y cuatro horas: hay **dos regimenes "
    "separados por un vacio**."
)

df_regimenes = distribucion_regimenes(qm, categoria_sel, franja_sel, dia_sel, "Todos")
df_hist = histograma_demora(qm, categoria_sel, franja_sel, dia_sel, "Todos", 60)

col_h, col_t = st.columns([3, 2])
with col_h:
    figura_h = px.bar(
        df_hist, x="Demora (min)", y="Vuelos",
        title="Distribucion minuto a minuto de la demora de salida (0 a 60 min)",
        color_discrete_sequence=[PALETA["verde_puntual"]])
    figura_h.update_layout(template="plotly_dark", height=420,
                           margin=dict(l=20, r=20, t=60, b=20))
    st.plotly_chart(figura_h, width="stretch")
    st.caption(
        "El nucleo se agota en el minuto 11. A partir de ahi, y hasta las tres "
        "horas, **no hay practicamente ningun vuelo**: el eje esta vacio. Es la "
        "firma de una base de datos generada de forma sintetica, y se declara "
        "como tal en las conclusiones."
    )

with col_t:
    st.subheader("Cuadro de distribucion")
    st.dataframe(
        df_regimenes[["Regimen", "Frec. absoluta (fi)", "Frec. relativa (hi %)",
                      "Frec. rel. acumulada (Hi %)", "Demora media (min)"]].style.format({
            "Frec. absoluta (fi)": "{:,.0f}", "Frec. relativa (hi %)": "{:.3f}%",
            "Frec. rel. acumulada (Hi %)": "{:.3f}%", "Demora media (min)": "{:,.2f}"}),
        width="stretch", hide_index=True)
    st.caption(
        "El regimen de **demora moderada (16 a 59 minutos) esta vacio**: ni un "
        "solo vuelo. La distribucion salta directamente de la demora leve a la "
        "severa, cuya media supera los 195 minutos."
    )

figura_r = px.bar(
    df_regimenes, x="Regimen", y="Frec. absoluta (fi)",
    color="Regimen", color_discrete_map=COLOR_REGIMEN,
    text="Frec. relativa (hi %)",
    title="Vuelos por regimen de puntualidad")
figura_r.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
figura_r.update_layout(template="plotly_dark", height=380, showlegend=False,
                       margin=dict(l=20, r=20, t=60, b=20))
st.plotly_chart(figura_r, width="stretch")

st.success(
    f"**La demora no se recupera en el aire.** La recuperacion media es de "
    f"{ind['recuperacion_media']:.3f} minutos: practicamente cero. Lo que se "
    f"pierde en la puerta de embarque llega integro al destino."
)
st.markdown("---")


# ==============================================================================
# BLOQUE 2 — CALENDARIO Y JORNADA
# ==============================================================================
st.header("2. La demora frente al calendario y la jornada")

tab_franja, tab_serie = st.tabs(["Por franja horaria", "Serie diaria"])

with tab_franja:
    df_franjas = puntualidad_por_franja(qm, categoria_sel, dia_sel, "Todos")
    figura_f = go.Figure()
    figura_f.add_trace(go.Bar(
        name="Vuelos", x=df_franjas["Franja"], y=df_franjas["Vuelos"],
        marker_color=PALETA["azul_operativo"], yaxis="y"))
    figura_f.add_trace(go.Scatter(
        name="Puntualidad (%)", x=df_franjas["Franja"],
        y=df_franjas["Puntualidad (%)"], mode="lines+markers",
        line=dict(color=PALETA["verde_puntual"], width=3),
        marker=dict(size=11), yaxis="y2"))
    figura_f.update_layout(
        template="plotly_dark", height=430,
        title="Volumen y puntualidad segun la franja horaria de salida",
        yaxis=dict(title="Vuelos"),
        yaxis2=dict(title="Puntualidad (%)", overlaying="y", side="right",
                    range=[90, 100]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(l=20, r=20, t=60, b=20))
    st.plotly_chart(figura_f, width="stretch")
    st.dataframe(df_franjas, width="stretch", hide_index=True)
    st.caption(
        "**Hallazgo negativo, igual de informativo.** La hora del dia apenas "
        "mueve la puntualidad: va del 95,4% en madrugada al 94,1% de noche, poco "
        "mas de un punto de diferencia. En una operacion real cabria esperar el "
        "arrastre de demoras a lo largo de la jornada; aqui no aparece."
    )

with tab_serie:
    df_serie = serie_diaria(qm, categoria_sel, franja_sel, dia_sel, "Todos")
    figura_s = px.line(
        df_serie, x="Fecha", y="Puntualidad (%)", markers=True,
        hover_data=["Vuelos", "Demora media (min)", "Dia"],
        title="Puntualidad diaria a lo largo del periodo observado")
    figura_s.update_traces(line_color=PALETA["verde_puntual"], line_width=2)
    figura_s.update_layout(template="plotly_dark", height=430,
                           margin=dict(l=20, r=20, t=60, b=20))
    st.plotly_chart(figura_s, width="stretch")
    st.caption("Al tratarse de un estudio descriptivo, la serie se lee como "
               "descripcion del periodo observado y no como base de pronostico.")

st.markdown("---")


# ==============================================================================
# BLOQUE 3 — AERONAVE Y TERRITORIO
# ==============================================================================
st.header("3. Perfil por aeronave y por aeropuerto")

tab_aeronave, tab_mapa = st.tabs(["Por modelo de aeronave", "Mapa de la red"])

with tab_aeronave:
    df_aeronaves = puntualidad_por_aeronave(qm, franja_sel, dia_sel, "Todos")
    col_g, col_d = st.columns([3, 2])
    with col_g:
        figura_a = px.scatter(
            df_aeronaves, x="Duracion media (min)", y="Demora media (min)",
            size="Vuelos", color="Categoria", color_discrete_map=COLOR_CATEGORIA,
            text="Modelo", size_max=55,
            hover_data=["Asientos", "Puntualidad (%)"],
            title="Demora frente a duracion programada, por modelo")
        figura_a.update_traces(textposition="top center")
        figura_a.update_layout(template="plotly_dark", height=460,
                               margin=dict(l=20, r=20, t=60, b=20))
        st.plotly_chart(figura_a, width="stretch")
    with col_d:
        st.dataframe(
            df_aeronaves[["Modelo", "Vuelos", "Demora media (min)",
                          "Puntualidad (%)"]],
            width="stretch", hide_index=True)
        st.caption(
            "**Este grafico no mide la fiabilidad tecnica del avion.** Cada "
            "modelo cubre rutas, aeropuertos y frecuencias distintas, y esas "
            "condiciones pesan sobre la puntualidad tanto o mas que la aeronave."
        )

with tab_mapa:
    col_m, col_r = st.columns([3, 2])
    with col_m:
        df_mapa = mapa_aeropuertos(qm, categoria_sel, franja_sel, dia_sel)
        figura_m = px.scatter_geo(
            df_mapa, lat="lat", lon="lon", size="vuelos", color="puntualidad",
            color_continuous_scale=[PALETA["rojo_severo"], PALETA["ambar"],
                                    PALETA["verde_puntual"]],
            size_max=34, opacity=0.85,
            hover_name="ciudad",
            hover_data={"aeropuerto": True, "vuelos": True, "demora": ":,.1f",
                        "lat": False, "lon": False},
            title=f"Aeropuertos de origen con 20 vuelos o mas ({len(df_mapa)} nodos)")
        figura_m.update_layout(template="plotly_dark", height=520,
                               margin=dict(l=0, r=0, t=60, b=0))
        figura_m.update_geos(bgcolor="rgba(0,0,0,0)", landcolor="#171C20",
                             lakecolor="#0F1720", subunitcolor="#39424A",
                             showcountries=True, countrycolor="#39424A")
        st.plotly_chart(figura_m, width="stretch")
    with col_r:
        criterio = st.radio("Ordenar aeropuertos por",
                            ["Vuelos", "Demora media (min)", "Puntualidad (%)"],
                            help="Se exige un minimo de 100 vuelos para que las "
                                 "medias sean comparables.")
        df_rank = ranking_aeropuertos(qm, categoria_sel, franja_sel, dia_sel, 12, criterio)
        figura_rank = px.bar(
            df_rank.sort_values(criterio), x=criterio, y="Ciudad", orientation="h",
            color=criterio,
            color_continuous_scale=[PALETA["verde_puntual"], PALETA["ambar"],
                                    PALETA["rojo_severo"]],
            title=f"Doce primeros por {criterio.lower()}")
        figura_rank.update_layout(template="plotly_dark", height=560,
                                  coloraxis_showscale=False,
                                  margin=dict(l=20, r=20, t=60, b=20))
        st.plotly_chart(figura_rank, width="stretch")

st.markdown("---")
st.caption("Escuela de Estadistica y Ciencias Actuariales · Universidad Central "
           "de Venezuela · Material academico de la asignatura Computacion II.")
