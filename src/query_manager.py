"""
src/query_manager.py
================================================================================
MOTOR DE CONSULTA ANALITICA (DuckDB sobre el Data Lake Parquet)
================================================================================

Este modulo es la unica puerta de entrada al dato dentro del aplicativo. Encapsula
tres decisiones de arquitectura:

1. DuckDB EN MEMORIA, PARQUET EN DISCO
   Se abre una conexion DuckDB `:memory:` y sobre ella se declaran VISTAS que
   apuntan a los archivos Parquet. DuckDB no copia los datos: los lee bajo
   demanda desde el archivo columnar. Esto significa que el aplicativo puede
   consultar 33.121 vuelos sin que ocupen memoria.

2. RUTAS RELATIVAS
   La ubicacion del Data Lake se resuelve a partir de la posicion de este
   archivo, nunca con rutas absolutas. Asi el proyecto funciona igual en el
   equipo de cualquier integrante y en el despliegue en la nube.

3. CACHE DE RECURSO
   La conexion se crea una sola vez por sesion mediante `st.cache_resource`.
   Sin ese cache, cada interaccion del usuario reabriria la conexion y volveria
   a declarar las vistas.
"""

import os
import duckdb
import streamlit as st


class QueryManager:
    """
    Administrador de consultas sobre el Data Lake.

    Expone un unico metodo publico, `execute_query`, que devuelve siempre un
    DataFrame de pandas listo para graficar o tabular.
    """

    # Mapeo entre el nombre logico que usan las consultas del aplicativo y el
    # archivo fisico del Data Lake. Cambiar aqui un nombre lo cambia en todo el
    # proyecto: es la unica fuente de verdad del esquema.
    TABLAS = {
        # --- Tablas de hechos ---
        "vuelos":     "vuelos.parquet",                  # Universo de programacion
        "metricas":   "metricas_puntualidad.parquet",    # Universo de operacion
        # --- Dimensiones ---
        "aeropuertos": "aeropuertos.parquet",
        "aeronaves":   "aeronaves.parquet",
        "estados":     "estados_vuelo.parquet",
        "regimenes":   "regimenes_puntualidad.parquet",
        "franjas":     "franjas_horarias.parquet",
        "calendario":  "calendario_operativo.parquet",
    }

    def __init__(self):
        self.con = duckdb.connect(database=':memory:')
        self.tablas_faltantes = []
        self._registrar_vistas()

    def _ruta_data_lake(self):
        """Resuelve la carpeta `data/` subiendo un nivel desde `src/`."""
        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        return os.path.abspath(os.path.join(directorio_actual, "..", "data"))

    def _registrar_vistas(self):
        """
        Declara una vista DuckDB por cada Parquet del Data Lake.

        Se usa CREATE OR REPLACE VIEW y no CREATE TABLE de forma deliberada: la
        vista deja el dato en el archivo y permite que DuckDB aplique
        'projection pushdown' (leer solo las columnas que la consulta pide) y
        'filter pushdown' (saltarse bloques que no cumplen el WHERE).
        """
        ruta_data = self._ruta_data_lake()

        for nombre_logico, archivo in self.TABLAS.items():
            ruta_archivo = os.path.join(ruta_data, archivo)
            if os.path.exists(ruta_archivo):
                self.con.execute(
                    f"CREATE OR REPLACE VIEW {nombre_logico} AS "
                    f"SELECT * FROM read_parquet('{ruta_archivo}')")
            else:
                self.tablas_faltantes.append(archivo)

    def esta_completo(self):
        """Indica si todas las tablas del modelo pudieron registrarse."""
        return len(self.tablas_faltantes) == 0

    def execute_query(self, sql):
        """
        Ejecuta SQL y devuelve un DataFrame.

        Ante un error de sintaxis o de nombre, se devuelve el mensaje en lugar
        de propagar la excepcion: el aplicativo debe informar el problema, no
        interrumpirse. Esto es especialmente importante en la terminal SQL
        abierta al usuario.
        """
        try:
            return self.con.execute(sql).df()
        except Exception as error:
            return f"Error en la consulta: {error}"


@st.cache_resource(show_spinner="Montando el Data Lake de vuelos...")
def get_query_manager():
    """
    Devuelve la instancia unica del motor de consulta para toda la sesion.

    `st.cache_resource` es el decorador adecuado para objetos no serializables
    con estado, como una conexion de base de datos. Usar `st.cache_data` aqui
    seria un error: intentaria copiar la conexion.
    """
    return QueryManager()
