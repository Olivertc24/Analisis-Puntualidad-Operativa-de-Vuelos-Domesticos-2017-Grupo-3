#!/usr/bin/env python3
"""
construir_libro.py
================================================================================
GENERACION DEL LIBRO DE TABLEAU (.twb) POR CODIGO
Investigacion: Puntualidad y regularidad operativa de vuelos domesticos, 2017.
Escuela de Estadistica y Ciencias Actuariales (EECA-UCV) — Computacion II
================================================================================

Un archivo .twb es XML: describe fuentes de datos, campos calculados, hojas y
tableros. Este script lo construye entero a partir de los extractos generados por
`generar_extractos.py`, de modo que el tablero es reproducible: si cambian los
datos, basta volver a ejecutar los scripts en orden.

REGLAS DEL FORMATO QUE NO SON OBVIAS
------------------------------------
El validador de Tableau es estricto y su mensaje de error queda enmascarado en el
log (`error-details=["*****"]`); solo el dialogo de la aplicacion lo muestra
entero. Las reglas que hubo que respetar:

  * `<workbook>` necesita el atributo `source-build`.
  * `<document-format-change-manifest>` es obligatorio.
  * Cada `<worksheet>`, `<dashboard>` y `<window>` necesita su `<simple-id>`, y
    va SIEMPRE al final del elemento. Omitirlo produce:
        missing elements in content model '((layout-options?|repository-location?),table,simple-id)'
  * `<aggregation value='true' />` debe cerrar cada `<view>`.
  * El bloque `<windows>` es obligatorio y debe tener al menos una ventana no
    oculta. La ventana de un tablero exige `<viewpoints>` CON contenido (uno por
    hoja) y `<active>`.
  * Los elementos vacios se rechazan: nada de `<slices></slices>` ni `<style />`.
  * El orden dentro de `<view>` es estricto: filter, orden, slices, aggregation.
    Y el elemento de orden se llama `<computed-sort>`, no `<sort>`.
  * En una zona contenedora de tablero, `<zone-style>` va DESPUES de las zonas
    hijas.
  * La paleta de una dimension discreta se declara en el `<style>` de la FUENTE
    DE DATOS, no en el de la hoja; la referencia al campo va SIN el prefijo de la
    fuente; el campo debe ser una dimension CALCULADA, no una columna nativa del
    archivo; y el hexadecimal debe ir en minusculas. Si falla cualquiera de las
    cuatro condiciones, Tableau ignora la paleta EN SILENCIO.
  * Un mapa necesita `<lod>` con un identificador de fila, o Tableau colapsa
    todas las marcas en un unico punto promedio.
  * Dentro de `<datasource>` y de `<datasource-dependencies>`, TODOS los
    `<column>` van antes que TODOS los `<column-instance>`. Declararlos por
    pares —campo, su instancia, siguiente campo— produce:
        element 'column' is not allowed for content model '(...,column,column-instance,...)'
    El fallo solo se manifiesta a partir del SEGUNDO campo calculado.
"""

import csv
import os
import re
import uuid
from xml.sax.saxutils import quoteattr, escape

DIRECTORIO = os.path.dirname(os.path.abspath(__file__))
EXTRACTOS = os.path.join(DIRECTORIO, "extractos")
SALIDA = os.path.join(DIRECTORIO, "Puntualidad_Operativa_Vuelos_2017.twb")

SOURCE_BUILD = "0.0.0 (0000.25.1024.2150)"

MANIFEST = """  <document-format-change-manifest>
    <_.fcp.AccessibleZoneTabOrder.true...AccessibleZoneTabOrder />
    <_.fcp.AnimationOnByDefault.true...AnimationOnByDefault />
    <AutoCreateAndUpdateDSDPhoneLayouts />
    <_.fcp.MarkAnimation.true...MarkAnimation />
    <_.fcp.ObjectModelEncapsulateLegacy.true...ObjectModelEncapsulateLegacy />
    <_.fcp.ObjectModelTableType.true...ObjectModelTableType />
    <_.fcp.SchemaViewerObjectModel.true...SchemaViewerObjectModel />
    <SetMembershipControl />
    <SheetIdentifierTracking />
    <SortTagCleanup />
    <WindowsPersistSimpleIdentifiers />
  </document-format-change-manifest>"""

CARDS = """      <cards>
        <edge name='left'>
          <strip size='160'>
            <card type='pages' />
            <card type='filters' />
            <card type='marks' />
          </strip>
        </edge>
        <edge name='top'>
          <strip size='2147483647'>
            <card type='columns' />
          </strip>
          <strip size='2147483647'>
            <card type='rows' />
          </strip>
        </edge>
      </cards>"""

# ────────────────────────────────────────────────────────── paleta "Pista" ──
# Los mismos colores del aplicativo de Streamlit: el color codifica el regimen de
# puntualidad y no es decorativo. Va de verde (a tiempo) a rojo (demora severa).
VERDE    = "#2E9E7B"   # Salida puntual / operado
VERDE_CL = "#7FBF7B"   # Demora minima
AMBAR    = "#FFB020"   # Demora leve
NARANJA  = "#E8734A"   # Demora moderada
ROJO     = "#D93636"   # Demora severa / cancelado
AZUL     = "#1E6091"   # Programado
GRIS     = "#8A9199"   # Sin operar

PAPEL      = "#F6F8F8"
SUPERFICIE = "#FFFFFF"
FILETE     = "#DDE4E4"
TINTA      = "#16211F"
TINTA_2    = "#35443F"
TINTA_3    = "#6E7C77"

# Las claves llevan el prefijo de orden porque la dimension calculada que
# consume la paleta lo antepone (ver DIMS_REGIMEN). Si la clave no coincide
# EXACTAMENTE con el valor que Tableau ve, la correspondencia se ignora en
# silencio y el grafico sale con la paleta por defecto.
COLOR_REGIMEN = {
    "1. Salida puntual":  VERDE,
    "2. Demora minima":   VERDE_CL,
    "3. Demora leve":     AMBAR,
    "4. Demora moderada": NARANJA,
    "5. Demora severa":   ROJO,
}
COLOR_ESTADO = {
    "Arrived":   VERDE,
    "Departed":  VERDE_CL,
    "Scheduled": AZUL,
    "On Time":   GRIS,
    "Delayed":   AMBAR,
    "Cancelled": ROJO,
}

DS,  CX  = "federated.programacion", "hyper.programacion"
DSP, CXP = "federated.puntualidad",  "hyper.puntualidad"
DSA, CXA = "federated.aeropuertos",  "hyper.aeropuertos"
DSR, CXR = "federated.rutas",        "hyper.rutas"

# Campos numericos que son codigos y no cantidades: deben ser dimension.
DIMENSIONES_NUMERICAS = {
    "Orden de dia", "Orden de franja", "Orden de regimen", "Asientos",
    "Id aeropuerto",
}

# Extraccion Hyper: Tableau Public solo publica libros basados en extracciones.
HYPER = "puntualidad_2017.hyper"

TABLAS_HYPER = {
    "Programacion": "programacion.csv",
    "Puntualidad":  "puntualidad.csv",
    "Aeropuertos":  "aeropuertos.csv",
    "Rutas":        "rutas_criticas.csv",
}
TABLA_DE_CSV = {csv_: tabla for tabla, csv_ in TABLAS_HYPER.items()}

TIPO_REMOTO = {"integer": "20", "real": "5", "string": "130"}


def a(v):
    return quoteattr(str(v))


def sid(nombre):
    """<simple-id>, obligatorio en hojas, tableros y ventanas.

    Se deriva del nombre con UUID v5 para que regenerar el libro no cambie los
    identificadores y el control de versiones muestre solo cambios reales.
    """
    u = uuid.uuid5(uuid.NAMESPACE_URL, "eeca/puntualidad/" + nombre)
    return f"      <simple-id uuid='{{{str(u).upper()}}}' />"


# ──────────────────────────────────────────────────── esquema del extracto ──

def inferir(ruta, filas=400):
    """Deduce el tipo de cada columna del CSV a partir de una muestra."""
    with open(ruta, encoding="utf-8", newline="") as f:
        lector = csv.reader(f)
        cab = next(lector)
        m = {c: [] for c in cab}
        for i, fila in enumerate(lector):
            if i >= filas:
                break
            for c, v in zip(cab, fila):
                if v != "":
                    m[c].append(v)
    salida = []
    for orden, c in enumerate(cab):
        v = m[c]
        if v and all(re.fullmatch(r"-?\d+", x) for x in v):
            t = "integer"
        elif v and all(re.fullmatch(r"-?\d+(\.\d+)?([eE][-+]?\d+)?", x) for x in v):
            t = "real"
        else:
            t = "string"
        medida = t in ("integer", "real") and c not in DIMENSIONES_NUMERICAS
        salida.append({
            "n": c, "t": t, "orden": orden,
            "rol": "measure" if medida else "dimension",
            "clase": "quantitative" if medida else ("ordinal" if t != "string" else "nominal"),
        })
    return salida


# Sufijo del nombre interno segun el tipo del campo: nominal 'nk', ordinal 'ok',
# cuantitativo 'qk'. Equivocarlo hace que Tableau no resuelva la referencia.
SUFIJO = {"nominal": "nk", "ordinal": "ok", "quantitative": "qk"}


def instancia(col, derivacion, clase):
    """Nombre interno del uso concreto de un campo dentro de una hoja."""
    prefijo = "none" if derivacion == "None" else derivacion.lower()
    return f"[{prefijo}:{col}:{SUFIJO[clase]}]"


def ref(inst, ds=DS):
    return f"[{ds}].{inst}"


# ────────────────────────────────────────────────────── campos calculados ──
# TODOS son cocientes de sumas y NINGUNO usa AVG(): promediar promedios produce
# una media no ponderada. Ver calculos/campos-calculados.md.
CALCULADOS = [
    ("TasaCobertura", "% de la programacion operado",
     "SUM([N operados]) / SUM([N vuelos])", "p0.0%"),
    ("TasaCancelacion", "% de vuelos cancelados",
     "SUM([N cancelados]) / SUM([N vuelos])", "p0.00%"),
    ("DemoraMedia", "Demora media de salida (min)",
     "SUM([Minutos de demora]) / SUM([N operados])", "n#,##0.00"),
    ("TasaPuntualidad", "% de vuelos puntuales",
     "SUM([N puntuales]) / SUM([N operados])", "p0.0%"),
    ("RecuperacionMedia", "Recuperacion media en ruta (min)",
     "SUM([Minutos recuperados]) / SUM([N con llegada])", "n#,##0.000"),
    ("PctDemora", "% de los minutos de demora",
     "SUM([Minutos de demora]) / TOTAL(SUM([Minutos de demora]))", "p0.00%"),
]
INST_CALC = {k: f"[usr:{k}:qk]" for k, _, _, _ in CALCULADOS}

# Dimensiones calculadas. Existen por un motivo concreto: la paleta discreta
# declarada en el <style> de la fuente de datos SOLO se aplica sobre una
# dimension CALCULADA; sobre una columna nativa del archivo Tableau la ignora en
# silencio y pinta con su paleta por defecto.
#
# Ademas, las que anteponen el numero de orden resuelven un segundo problema:
# Tableau ordena las dimensiones discretas alfabeticamente, de modo que "Demora
# severa" aparecia antes que "Salida puntual". Anteponer el orden fuerza la
# secuencia logica sin necesidad de un orden manual que el .twb no conserva.
DIM_REGIMEN = "RegimenPuntualidad"
DIM_ESTADO = "EstadoVuelo"
DIM_FRANJA = "FranjaOrdenada"
DIM_DIA = "DiaOrdenado"

DIMS_REGIMEN = [(DIM_REGIMEN, "Regimen de puntualidad",
                 "STR([Orden de regimen]) + '. ' + [Regimen]")]
DIMS_ESTADO = [(DIM_ESTADO, "Estado del vuelo", "[Estado]")]
DIMS_FRANJA = [(DIM_FRANJA, "Franja horaria",
                "STR([Orden de franja]) + '. ' + [Franja]")]
DIMS_DIA = [(DIM_DIA, "Dia de la semana",
             "STR([Orden de dia]) + '. ' + [Dia]")]

INST_REGIMEN = f"[none:{DIM_REGIMEN}:nk]"
INST_ESTADO = f"[none:{DIM_ESTADO}:nk]"
INST_FRANJA = f"[none:{DIM_FRANJA}:nk]"
INST_DIA = f"[none:{DIM_DIA}:nk]"


def bloque_datasource(archivo, ds, cx, caption, calculados=(), paleta=None,
                      semantica=None, dims_calc=()):
    """Fuente de datos sobre una tabla de la extraccion Hyper.

    Tableau Public SOLO publica libros cuyas fuentes sean extracciones: una
    conexion en vivo a los CSV se abre en Tableau Desktop pero es rechazada al
    guardar en Tableau Public. Por eso la conexion es de clase `hyper` y apunta
    a `Data/<archivo>.hyper`, que es la ruta dentro del paquete .twbx.

    El esquema se sigue deduciendo del CSV de origen, de modo que el libro y la
    extraccion no puedan divergir: ambos salen del mismo archivo.
    """
    cols = inferir(os.path.join(EXTRACTOS, archivo))
    tabla = TABLA_DE_CSV[archivo]

    o = [f"  <datasource caption={a(caption)} inline='true' name='{ds}' version='18.1'>",
         "    <connection class='federated'>",
         "      <named-connections>",
         f"        <named-connection caption={a(caption)} name='{cx}'>",
         f"          <connection class='hyper' dbname='Data/{HYPER}' schema='Extract' "
         "server='' username='tableau_internal_user' />",
         "        </named-connection>",
         "      </named-connections>",
         f"      <relation connection='{cx}' name='{tabla}' "
         f"table='[Extract].[{tabla}]' type='table'>",
         "        <columns header='yes' outcome='6'>"]
    for c in cols:
        o.append(f"          <column datatype='{c['t']}' name={a(c['n'])} "
                 f"ordinal='{c['orden']}' />")
    o += ["        </columns>", "      </relation>", "      <metadata-records>"]
    for c in cols:
        o += ["        <metadata-record class='column'>",
              f"          <remote-name>{escape(c['n'])}</remote-name>",
              f"          <remote-type>{TIPO_REMOTO[c['t']]}</remote-type>",
              f"          <local-name>[{escape(c['n'])}]</local-name>",
              f"          <parent-name>[{tabla}]</parent-name>",
              f"          <remote-alias>{escape(c['n'])}</remote-alias>",
              f"          <ordinal>{c['orden']}</ordinal>",
              f"          <local-type>{c['t']}</local-type>",
              f"          <aggregation>{'Sum' if c['rol'] == 'measure' else 'Count'}</aggregation>",
              "          <contains-null>true</contains-null>",
              "        </metadata-record>"]
    o += ["      </metadata-records>", "    </connection>", "    <aliases enabled='yes' />"]

    semantica = semantica or {}
    for c in cols:
        # El rol geografico permite que Tableau dibuje un mapa real en lugar de
        # un diagrama de dispersion.
        rol_geo = (f" semantic-role={a(semantica[c['n']])}" if c["n"] in semantica else "")
        o.append(f"    <column datatype='{c['t']}' name={a('[' + c['n'] + ']')} "
                 f"role='{c['rol']}'{rol_geo} type='{c['clase']}' />")
    for clave, cap, formula, fmt in calculados:
        o += [f"    <column caption={a(cap)} datatype='real' default-format={a(fmt)} "
              f"name='[{clave}]' role='measure' type='quantitative'>",
              f"      <calculation class='tableau' formula={a(formula)} "
              "scope-isolation='false' />",
              "    </column>"]
    # ATENCION AL ORDEN. El modelo de contenido de <datasource> exige que TODOS
    # los <column> precedan a TODOS los <column-instance>. Intercalarlos —un
    # <column> seguido de su instancia, y luego el siguiente par— produce:
    #     element 'column' is not allowed for content model
    #     '(... aliases?,column,column-instance,group? ...)'
    # El error solo aparece a partir de la SEGUNDA dimension calculada, porque
    # con una sola el orden intercalado coincide por casualidad con el correcto.
    for clave, cap, formula in dims_calc:
        # El caption arregla de una vez el encabezado, el eje y el titulo del
        # filtro asociados al campo.
        o += [f"    <column caption={a(cap)} datatype='string' name='[{clave}]' "
              "role='dimension' type='nominal'>",
              f"      <calculation class='tableau' formula={a(formula)} "
              "scope-isolation='false' />",
              "    </column>"]
    for clave, _, _ in dims_calc:
        o.append(f"    <column-instance column='[{clave}]' derivation='None' "
                 f"name={a('[none:' + clave + ':nk]')} pivot='key' type='nominal' />")
    o.append("    <layout dim-ordering='alphabetic' measure-ordering='alphabetic' "
             "show-structure='true' />")
    if paleta:
        campo, mapa = paleta
        # La referencia va SIN el prefijo de la fuente de datos: con el, la
        # paleta se ignora en silencio y Tableau pinta con su paleta por defecto.
        inst = f"[none:{campo}:nk]"
        o += ["    <style>", "      <style-rule element='mark'>",
              f"        <encoding attr='color' field={a(inst)} type='palette'>"]
        for valor, color in mapa.items():
            # Tableau espera el hexadecimal en minusculas; en mayusculas ignora
            # la correspondencia sin avisar.
            o += [f"          <map to='{color.lower()}'>",
                  f"            <bucket>&quot;{escape(valor)}&quot;</bucket>",
                  "          </map>"]
        o += ["        </encoding>", "      </style-rule>", "    </style>"]
    o.append("  </datasource>")
    return o, {c["n"]: c for c in cols}


# ───────────────────────────────────────────────────────────────── hojas ──

def hoja(nombre, titulo, esquema, dims, medidas, calcs, filas, columnas, marca,
         ds=DS, caption="Programacion", color=None, orden=None,
         filtros=(), estilo_extra=(), etiqueta=None, dims_calc=(), detalle=None,
         tamano=None):
    """Construye una hoja de trabajo completa."""
    o = [f"    <worksheet name={a(nombre)}>",
         "      <layout-options>", "        <title>", "          <formatted-text>",
         f"            <run fontcolor='{TINTA_2}' fontsize='11'>{escape(titulo)}</run>",
         "          </formatted-text>", "        </title>", "      </layout-options>",
         "      <table>", "        <view>", "          <datasources>",
         f"            <datasource caption={a(caption)} name='{ds}' />",
         "          </datasources>",
         f"          <datasource-dependencies datasource='{ds}'>"]

    usados = list(dict.fromkeys(list(dims) + list(filtros)))
    for d in usados:
        c = esquema[d]
        o.append(f"            <column datatype='{c['t']}' name={a('[' + d + ']')} "
                 f"role='dimension' type='{c['clase']}' />")
    for m in medidas:
        c = esquema[m]
        o.append(f"            <column datatype='{c['t']}' name={a('[' + m + ']')} "
                 f"role='measure' type='quantitative' />")
    for d in usados:
        c = esquema[d]
        o.append(f"            <column-instance column={a('[' + d + ']')} derivation='None' "
                 f"name={a(instancia(d, 'None', c['clase']))} pivot='key' "
                 f"type='{c['clase']}' />")
    for m in medidas:
        o.append(f"            <column-instance column={a('[' + m + ']')} derivation='Sum' "
                 f"name={a(instancia(m, 'Sum', 'quantitative'))} pivot='key' "
                 "type='quantitative' />")
    # Misma regla que en <datasource>: primero todas las declaraciones de campo
    # calculado, despues todas sus instancias.
    for clave, cap, formula in dims_calc:
        o += [f"            <column caption={a(cap)} datatype='string' name='[{clave}]' "
              "role='dimension' type='nominal'>",
              f"              <calculation class='tableau' formula={a(formula)} "
              "scope-isolation='false' />",
              "            </column>"]
    for clave in calcs:
        cap, formula, fmt = next((c, f, x) for k, c, f, x in CALCULADOS if k == clave)
        o += [f"            <column caption={a(cap)} datatype='real' default-format={a(fmt)} "
              f"name='[{clave}]' role='measure' type='quantitative'>",
              f"              <calculation class='tableau' formula={a(formula)} "
              "scope-isolation='false' />",
              "            </column>"]
    for clave, _, _ in dims_calc:
        o.append(f"            <column-instance column='[{clave}]' derivation='None' "
                 f"name={a('[none:' + clave + ':nk]')} pivot='key' type='nominal' />")
    for clave in calcs:
        o.append(f"            <column-instance column='[{clave}]' derivation='User' "
                 f"name={a(INST_CALC[clave])} pivot='key' type='quantitative' />")
    o.append("          </datasource-dependencies>")

    # Orden dentro de <view>: filter, computed-sort, slices, aggregation.
    for i, f in enumerate(filtros):
        inst = instancia(f, "None", esquema[f]["clase"])
        o += [f"          <filter class='categorical' column={a(ref(inst, ds))} "
              f"filter-group='{100 + i}'>",
              f"            <groupfilter function='level-members' level={a(inst)} "
              "user:ui-enumeration='all' user:ui-marker='enumerate' />",
              "          </filter>"]
    if orden:
        campo_inst, medida_inst = orden
        o.append(f"          <computed-sort column={a(ref(campo_inst, ds))} "
                 f"direction='DESC' using={a(ref(medida_inst, ds))} />")
    if filtros:
        o.append("          <slices>")
        for f in filtros:
            o.append("            <column>"
                     + escape(ref(instancia(f, "None", esquema[f]["clase"]), ds))
                     + "</column>")
        o.append("          </slices>")
    o += ["          <aggregation value='true' />", "        </view>",
          "        <style>",
          "          <style-rule element='worksheet'>",
          "            <format attr='display-field-labels' scope='rows' value='false' />",
          "            <format attr='display-field-labels' scope='cols' value='false' />",
          "          </style-rule>",
          "          <style-rule element='pane'>",
          f"            <format attr='background-color' value='{SUPERFICIE}' />",
          "          </style-rule>",
          "          <style-rule element='axis'>",
          f"            <format attr='color' value='{TINTA_3}' />",
          "          </style-rule>",
          "          <style-rule element='header'>",
          f"            <format attr='color' value='{TINTA_2}' />",
          "          </style-rule>"]
    o += ["          " + l for l in estilo_extra]
    o += ["        </style>", "        <panes>",
          "          <pane selection-relaxation-option='selection-relaxation-allow'>",
          "            <view>", "              <breakdown value='auto' />",
          "            </view>",
          f"            <mark class='{marca}' />"]
    codificaciones = []
    if color:
        codificaciones.append(f"<color column={a(ref(color, ds))} />")
    if tamano:
        codificaciones.append(f"<size column={a(ref(tamano, ds))} />")
    if etiqueta:
        codificaciones.append(f"<text column={a(ref(etiqueta, ds))} />")
    if detalle:
        # <lod> fija el nivel de detalle de las marcas: una marca por valor del
        # campo. Es lo que convierte el mapa en 104 aeropuertos y no en un punto.
        codificaciones.append(f"<lod column={a(ref(detalle, ds))} />")
    if codificaciones:
        o.append("            <encodings>")
        o += ["              " + c for c in codificaciones]
        o.append("            </encodings>")
    o += ["          </pane>", "        </panes>",
          f"        <rows>{escape(filas)}</rows>",
          f"        <cols>{escape(columnas)}</cols>",
          "      </table>", sid(nombre), "    </worksheet>"]
    return o


# ─────────────────────────────────────────────────── definicion del tablero ──

def i_dim(campo, esquema, ds=DS):
    return ref(instancia(campo, "None", esquema[campo]["clase"]), ds)


def i_med(campo, ds=DS):
    return ref(instancia(campo, "Sum", "quantitative"), ds)


def i_calc(clave, ds=DS):
    return ref(INST_CALC[clave], ds)


def construir_hojas(esq, esqp, esqa, esqr):
    """Las doce hojas del tablero, en el orden en que se montan en las paginas."""
    h = []

    # --- Pagina 1: cobertura de la programacion ---------------------------
    h += hoja("Programado por estado",
              "Vuelos programados segun su estado final", esq,
              [], ["N vuelos"], [],
              i_med("N vuelos"), ref(INST_ESTADO), "Bar",
              color=INST_ESTADO, dims_calc=DIMS_ESTADO,
              orden=(INST_ESTADO, instancia("N vuelos", "Sum", "quantitative")),
              filtros=["Mes", "Alcance"])
    h += hoja("Cobertura diaria",
              "Vuelos programados y operados, dia a dia", esq,
              ["Fecha"], ["N vuelos", "N operados"], [],
              # Dos medidas en el mismo estante se separan con ' + ', no con un
              # espacio: el espacio produce "Expresion mal formada: no es posible
              # asociar operadores con operandos".
              i_med("N vuelos") + " + " + i_med("N operados"),
              i_dim("Fecha", esq), "Line",
              filtros=["Mes", "Alcance"])
    h += hoja("Cancelacion por aeronave",
              "Tasa de cancelacion segun el modelo asignado", esq,
              ["Aeronave"], ["N vuelos", "N cancelados"], ["TasaCancelacion"],
              i_dim("Aeronave", esq), i_calc("TasaCancelacion"), "Bar",
              # Se ordena por la MISMA medida que se dibuja. Ordenar por el
              # conteo absoluto mientras se grafica la tasa produce un grafico
              # que parece desordenado sin estarlo.
              orden=(instancia("Aeronave", "None", "nominal"),
                     INST_CALC["TasaCancelacion"]),
              filtros=["Mes", "Alcance"])
    h += hoja("Cobertura por franja",
              "Porcentaje de la programacion que llega a operarse, por franja", esq,
              [], ["N vuelos", "N operados"], ["TasaCobertura"],
              i_calc("TasaCobertura"), ref(INST_FRANJA), "Bar",
              dims_calc=DIMS_FRANJA, filtros=["Mes", "Alcance"])

    # --- Pagina 2: regimenes de puntualidad -------------------------------
    h += hoja("Vuelos por regimen",
              "Distribucion de los vuelos operados por regimen de puntualidad", esqp,
              [], ["N operados"], [],
              i_med("N operados", DSP), ref(INST_REGIMEN, DSP), "Bar",
              ds=DSP, caption="Puntualidad", color=INST_REGIMEN,
              dims_calc=DIMS_REGIMEN, filtros=["Mes", "Alcance"])
    h += hoja("Minutos por regimen",
              "Donde se acumulan los minutos de demora", esqp,
              [], ["Minutos de demora"], ["PctDemora"],
              i_calc("PctDemora", DSP), ref(INST_REGIMEN, DSP), "Bar",
              ds=DSP, caption="Puntualidad", color=INST_REGIMEN,
              dims_calc=DIMS_REGIMEN, filtros=["Mes", "Alcance"])
    h += hoja("Puntualidad por franja",
              "Porcentaje de vuelos con 15 minutos de demora o menos", esqp,
              [], ["N operados", "N puntuales"], ["TasaPuntualidad"],
              i_calc("TasaPuntualidad", DSP), ref(INST_FRANJA, DSP), "Bar",
              ds=DSP, caption="Puntualidad", dims_calc=DIMS_FRANJA,
              filtros=["Mes", "Alcance"])
    h += hoja("Demora media por aeronave",
              "Minutos medios de demora de salida segun el modelo", esqp,
              ["Aeronave"], ["N operados", "Minutos de demora"], ["DemoraMedia"],
              i_dim("Aeronave", esqp, DSP), i_calc("DemoraMedia", DSP), "Bar",
              ds=DSP, caption="Puntualidad",
              orden=(instancia("Aeronave", "None", "nominal"),
                     INST_CALC["DemoraMedia"]),
              filtros=["Mes", "Alcance"])

    # --- Pagina 3: geografia y evolucion ----------------------------------
    # El mapa consume el extracto de aeropuertos.
    # Dispersion geografica: cada aeropuerto en sus coordenadas reales,
    # dimensionado por trafico y coloreado por su demora media de salida.
    # Tableau dibuja los puntos sobre ejes de latitud y longitud, sin capa de
    # mapa base; la silueta de la red se reconoce igualmente.
    h += hoja("Mapa de aeropuertos",
              "Los 104 aeropuertos: tamano = trafico, color = demora media", esqa,
              ["Id aeropuerto", "Ciudad"], ["N vuelos", "N operados",
                                            "Minutos de demora"], ["DemoraMedia"],
              ref(instancia("Latitud", "Avg", "quantitative"), DSA),
              ref(instancia("Longitud", "Avg", "quantitative"), DSA), "Circle",
              ds=DSA, caption="Aeropuertos",
              color=INST_CALC["DemoraMedia"],
              tamano=instancia("N vuelos", "Sum", "quantitative"),
              detalle=instancia("Id aeropuerto", "None", "ordinal"))
    # Consume el extracto ya recortado a veinte rutas: un grafico con las 457
    # rutas de la red no se lee.
    h += hoja("Rutas con mas demora",
              "Las veinte rutas que acumulan mas minutos de demora", esqr,
              ["Ruta"], ["Minutos de demora"], [],
              i_dim("Ruta", esqr, DSR), i_med("Minutos de demora", DSR), "Bar",
              ds=DSR, caption="Rutas criticas", color=INST_REGIMEN,
              dims_calc=DIMS_REGIMEN,
              orden=(instancia("Ruta", "None", "nominal"),
                     instancia("Minutos de demora", "Sum", "quantitative")),
              filtros=["Aeronave"])
    h += hoja("Serie diaria de demora",
              "Evolucion diaria de la demora media de salida", esqp,
              ["Fecha"], ["N operados", "Minutos de demora"], ["DemoraMedia"],
              i_calc("DemoraMedia", DSP), i_dim("Fecha", esqp, DSP), "Line",
              ds=DSP, caption="Puntualidad", filtros=["Alcance"])
    h += hoja("Patron semanal",
              "Puntualidad segun el dia de la semana", esqp,
              [], ["N operados", "N puntuales"], ["TasaPuntualidad"],
              i_calc("TasaPuntualidad", DSP), ref(INST_DIA, DSP), "Bar",
              ds=DSP, caption="Puntualidad", dims_calc=DIMS_DIA,
              filtros=["Mes", "Alcance"])
    return h


# El mapa necesita declarar sus coordenadas con derivacion Avg, que la funcion
# generica declara como Sum. Se corrige el bloque de la hoja del mapa.
def parchar_mapa(lineas):
    salida = []
    for l in lineas:
        salida.append(l)
        if "<datasource-dependencies datasource='" + DSA + "'>" in l:
            for campo in ("Latitud", "Longitud"):
                rol = "Latitude" if campo == "Latitud" else "Longitude"
                salida.append(f"            <column datatype='real' name='[{campo}]' "
                              f"role='measure' semantic-role='[{rol}]' "
                              "type='quantitative' />")
                salida.append(f"            <column-instance column='[{campo}]' "
                              f"derivation='Avg' name='[avg:{campo}:qk]' pivot='key' "
                              "type='quantitative' />")
    return salida


# ─────────────────────────────────────────────────────────────── tableros ──

def zona_hoja(zid, nombre, x, y, w, h):
    return [f"        <zone h='{h}' id='{zid}' name={a(nombre)} w='{w}' x='{x}' y='{y}'>",
            "          <zone-style>",
            f"            <format attr='background-color' value='{SUPERFICIE}' />",
            f"            <format attr='border-color' value='{FILETE}' />",
            "            <format attr='border-style' value='solid' />",
            "            <format attr='border-width' value='1' />",
            "            <format attr='margin' value='5' />",
            "          </zone-style>", "        </zone>"]


def zona_texto(zid, texto, tam, color, negrita, x, y, w, h):
    """Zona de texto suelta. Titulo y subtitulo van en zonas distintas porque un
    salto de linea dentro de un mismo <formatted-text> no se respeta al
    renderizar el tablero."""
    return [f"        <zone h='{h}' id='{zid}' type-v2='text' w='{w}' x='{x}' y='{y}'>",
            "          <formatted-text>",
            f"            <run fontcolor='{color}' fontsize='{tam}'"
            f"{' bold=' + chr(39) + 'true' + chr(39) if negrita else ''}>"
            f"{escape(texto)}</run>",
            "          </formatted-text>",
            "          <zone-style>",
            f"            <format attr='background-color' value='{PAPEL}' />",
            "            <format attr='border-style' value='none' />",
            "            <format attr='border-width' value='0' />",
            "            <format attr='margin' value='4' />",
            "          </zone-style>", "        </zone>"]


def tablero(nombre, titulo, subtitulo, hojas_zonas):
    o = [f"    <dashboard name={a(nombre)}>",
         "      <style>",
         "        <style-rule element='dash-container'>",
         f"          <format attr='background-color' id='dash-zone_1' value='{PAPEL}' />",
         "        </style-rule>",
         "      </style>",
         "      <size maxheight='900' maxwidth='1500' minheight='900' minwidth='1500' />",
         "      <zones>",
         "        <zone h='100000' id='1' type-v2='layout-basic' w='100000' x='0' y='0'>"]
    o += zona_texto(2, titulo, 18, TINTA, True, 0, 0, 100000, 6500)
    o += zona_texto(3, subtitulo, 11, TINTA_3, False, 0, 6500, 100000, 4500)
    for i, (n, x, y, w, h) in enumerate(hojas_zonas, start=4):
        o += zona_hoja(i, n, x, y, w, h)
    # En una zona contenedora, <zone-style> va DESPUES de las zonas hijas.
    o += ["          <zone-style>",
          f"            <format attr='background-color' value='{PAPEL}' />",
          "            <format attr='border-style' value='none' />",
          "          </zone-style>",
          "        </zone>", "      </zones>", sid(nombre), "    </dashboard>"]
    return o


def ventanas(nombres_hojas, nombres_tableros):
    """Bloque <windows>: obligatorio, con al menos una ventana visible, y la de
    cada tablero con <viewpoints> con contenido y <active>."""
    o = ["  <windows source-height='30'>"]
    for i, nt in enumerate(nombres_tableros):
        o += [f"    <window class='dashboard' "
              f"{'maximized=' + chr(39) + 'true' + chr(39) + ' ' if i == 0 else ''}"
              f"name={a(nt)}>",
              "      <viewpoints>"]
        for n in nombres_hojas:
            o += [f"        <viewpoint name={a(n)}>",
                  "          <zoom type='entire-view' />",
                  "        </viewpoint>"]
        o += ["      </viewpoints>", "      <active id='-1' />",
              sid("win/" + nt), "    </window>"]
    for n in nombres_hojas:
        o += [f"    <window class='worksheet' hidden='true' name={a(n)}>",
              CARDS, sid("win/" + n), "    </window>"]
    o.append("  </windows>")
    return o


# ──────────────────────────────────────────────────────────────────── main ──

def main():
    ds_prog, esq = bloque_datasource(
        "programacion.csv", DS, CX, "Programacion",
        CALCULADOS, paleta=(DIM_ESTADO, COLOR_ESTADO),
        dims_calc=DIMS_ESTADO + DIMS_FRANJA + DIMS_DIA)
    ds_punt, esqp = bloque_datasource(
        "puntualidad.csv", DSP, CXP, "Puntualidad",
        CALCULADOS, paleta=(DIM_REGIMEN, COLOR_REGIMEN),
        dims_calc=DIMS_REGIMEN + DIMS_FRANJA + DIMS_DIA)
    # El extracto de aeropuertos no trae `N cancelados`, de modo que solo puede
    # sostener los calculos que no lo usan. Pasarle la lista completa declararia
    # un campo calculado sobre una columna inexistente.
    calc_aero = [c for c in CALCULADOS
                 if c[0] in ("DemoraMedia", "TasaPuntualidad", "TasaCobertura")]
    ds_aero, esqa = bloque_datasource(
        "aeropuertos.csv", DSA, CXA, "Aeropuertos", calc_aero,
        semantica={"Latitud": "[Latitude]", "Longitud": "[Longitude]"})
    ds_rutas, esqr = bloque_datasource(
        "rutas_criticas.csv", DSR, CXR, "Rutas criticas",
        paleta=(DIM_REGIMEN, COLOR_REGIMEN), dims_calc=DIMS_REGIMEN)

    hojas_xml = parchar_mapa(construir_hojas(esq, esqp, esqa, esqr))
    nombres = [l.split("name=")[1].strip().strip(">").strip("'\"")
               for l in hojas_xml if l.startswith("    <worksheet ")]

    tableros = [
        tablero("1. Cobertura de la programacion",
                "Puntualidad operativa de vuelos domesticos, 2017",
                "33.121 vuelos programados  ·  16.773 operados (50,64%)  ·  414 cancelados",
                [("Programado por estado", 0, 11000, 50000, 44500),
                 ("Cobertura diaria", 50000, 11000, 50000, 44500),
                 ("Cancelacion por aeronave", 0, 55500, 50000, 44500),
                 ("Cobertura por franja", 50000, 55500, 50000, 44500)]),
        tablero("2. Regimenes de puntualidad",
                "La demora es bimodal: la media no describe a nadie",
                "95,2% de los vuelos sale con 15 minutos o menos  ·  entre 16 y 59 minutos no hay ninguno",
                [("Vuelos por regimen", 0, 11000, 50000, 44500),
                 ("Minutos por regimen", 50000, 11000, 50000, 44500),
                 ("Puntualidad por franja", 0, 55500, 50000, 44500),
                 ("Demora media por aeronave", 50000, 55500, 50000, 44500)]),
        tablero("3. Geografia y evolucion",
                "Donde y cuando se acumula la demora",
                "104 aeropuertos  ·  487 vuelos (2,9%) concentran la mitad de los minutos de demora",
                [("Mapa de aeropuertos", 0, 11000, 60000, 52000),
                 ("Rutas con mas demora", 60000, 11000, 40000, 89000),
                 ("Serie diaria de demora", 0, 63000, 30000, 37000),
                 ("Patron semanal", 30000, 63000, 30000, 37000)]),
    ]
    nombres_tableros = ["1. Cobertura de la programacion",
                        "2. Regimenes de puntualidad",
                        "3. Geografia y evolucion"]

    o = ["<?xml version='1.0' encoding='utf-8' ?>",
         f"<workbook source-build={a(SOURCE_BUILD)} source-platform='mac' version='18.1' "
         "xmlns:user='http://www.tableausoftware.com/xml/user'>",
         MANIFEST,
         "  <preferences>",
         "    <preference name='ui.encoding.shelf.height' value='24' />",
         "    <preference name='ui.shelf.height' value='26' />",
         "  </preferences>",
         "  <datasources>"]
    o += ds_prog + ds_punt + ds_aero + ds_rutas
    o += ["  </datasources>", "  <worksheets>"]
    o += hojas_xml
    o += ["  </worksheets>", "  <dashboards>"]
    for t in tableros:
        o += t
    o += ["  </dashboards>"]
    o += ventanas(nombres, nombres_tableros)
    o += ["</workbook>"]

    with open(SALIDA, "w", encoding="utf-8") as f:
        f.write("\n".join(o))

    import xml.etree.ElementTree as ET
    ET.parse(SALIDA)   # falla si el XML no esta bien formado
    print(f"{os.path.basename(SALIDA)}: {len(o)} lineas, "
          f"{os.path.getsize(SALIDA)/1024:.0f} KB, XML bien formado")
    print(f"hojas: {len(nombres)} | tableros: {len(tableros)}")


if __name__ == "__main__":
    main()
