"""
pages/06_Bibliografia.py
================================================================================
REFERENCIAS BIBLIOGRAFICAS Y FUENTES CONSULTADAS
Puntualidad y regularidad operativa de vuelos domesticos, 2017.
================================================================================
"""

import streamlit as st

st.set_page_config(page_title="Bibliografia", page_icon="📖", layout="wide")
st.title("Referencias bibliograficas")
st.caption("Fuentes de datos, literatura y documentacion tecnica consultada")

st.header("Fuente de datos primaria")
st.markdown("""
- Haroon, S. (2023). *Airlines Dataset* [Conjunto de datos]. Kaggle.
  https://www.kaggle.com/datasets/saadharoon27/airlines-dataset

- PostgreSQL Professional. *Demo database: airlines*. Documentacion de la base de
  demostracion `demo` de la que procede el conjunto publicado en Kaggle.
  https://postgrespro.com/docs/postgrespro/current/demodb-bookings
""")

st.info("""
**Naturaleza de la fuente.** El conjunto es la exportacion a SQLite de la base de
demostracion `demo` que PostgreSQL distribuye con fines didacticos. Sus registros
**fueron generados de forma sintetica** y no corresponden a una operacion real.
Esta investigacion lo declara en su marco metodologico y lee todos sus hallazgos
como descripcion de este conjunto de datos, no como conclusiones sobre la
aviacion civil.
""")

st.header("Literatura sobre puntualidad aeronautica")
st.markdown("""
- Bureau of Transportation Statistics. *On-Time Performance reporting: definitions
  and methodology*. United States Department of Transportation.
  https://www.bts.gov/topics/airlines-and-airports/understanding-reporting-causes-flight-delays-and-cancellations

- EUROCONTROL. *Standard Inputs for Economic Analyses* y los informes anuales
  *Performance Review Report*, que documentan la medicion de la puntualidad y la
  propagacion de demoras en redes europeas.
  https://www.eurocontrol.int/prudata/dashboard/

- Federal Aviation Administration. *Aviation System Performance Metrics (ASPM)*.
  https://aspm.faa.gov/

- Ball, M., Barnhart, C., Dresner, M., Hansen, M., Neels, K., Odoni, A.,
  Peterson, E., Sherry, L., Trani, A., y Zou, B. (2010). *Total Delay Impact
  Study: A Comprehensive Assessment of the Costs and Impacts of Flight Delay in
  the United States*. NEXTOR.
""")

st.header("Fundamentos metodologicos")
st.markdown("""
- Arias, F. G. (2012). *El proyecto de investigacion: introduccion a la
  metodologia cientifica* (6.ª ed.). Caracas: Editorial Episteme.

- Codd, E. F. (1970). A relational model of data for large shared data banks.
  *Communications of the ACM*, 13(6), 377-387.
  https://doi.org/10.1145/362384.362685

- Kimball, R., y Ross, M. (2013). *The Data Warehouse Toolkit: The Definitive
  Guide to Dimensional Modeling* (3.ª ed.). Indianapolis: John Wiley & Sons.

- Tukey, J. W. (1977). *Exploratory Data Analysis*. Reading: Addison-Wesley.
  Referencia clasica sobre la importancia de examinar la forma de la distribucion
  antes de resumirla.
""")

st.header("Documentacion tecnica de las herramientas")
st.markdown("""
- DuckDB Foundation. *DuckDB Documentation*. https://duckdb.org/docs/
- Apache Software Foundation. *Apache Parquet Documentation*. https://parquet.apache.org/docs/
- Snowflake Inc. *Streamlit Documentation*. https://docs.streamlit.io/
- SQLite Consortium. *SQLite Documentation*. https://www.sqlite.org/docs.html
- Salesforce Inc. *Tableau Help*. https://help.tableau.com/current/pro/desktop/es-es/
- Plotly Technologies Inc. *Plotly Python Open Source Graphing Library*. https://plotly.com/python/
""")

st.markdown("---")
st.caption("Escuela de Estadistica y Ciencias Actuariales · Universidad Central "
           "de Venezuela · Material academico de la asignatura Computacion II.")
