"""
04_exportacion_parquet.py
================================================================================
CONSTRUCCION DEL DATA LAKE ANALITICO (PARQUET)
Investigacion: Puntualidad y regularidad operativa, julio-septiembre de 2017.
Escuela de Estadistica y Ciencias Actuariales (EECA-UCV) — Computacion II
================================================================================

POR QUE PARQUET Y NO SQLITE EN LA APLICACION
--------------------------------------------
SQLite es un excelente motor TRANSACCIONAL (OLTP): esta optimizado para leer y
escribir filas completas. Nuestro aplicativo, en cambio, hace exclusivamente
consultas ANALITICAS (OLAP): "promedio de demora por regimen", "conteo por
franja horaria", "suma de minutos por aeronave". Ese tipo de consulta toca pocas columnas pero
muchisimas filas.

Parquet es un formato COLUMNAR: guarda juntos todos los valores de una misma
columna. Esto produce dos ventajas decisivas para el proyecto:

    1. LECTURA SELECTIVA (projection pushdown). Una consulta que solo necesita
       `demora_salida_min` lee unicamente ese bloque del archivo e ignora el
       resto. En SQLite habria que recorrer las filas completas.

    2. COMPRESION MUY ALTA. Al estar los valores de una columna juntos, son
       homogeneos y se comprimen mucho mejor. En este proyecto el esquema
       normalizado pasa de 6,5 MB a 0,59 MB: una compresion de 11 veces.

Ademas, los archivos resultantes son lo bastante livianos para versionarse
directamente en el repositorio, de modo que la aplicacion queda AUTOCONTENIDA:
quien clone el proyecto puede ejecutarla sin descargar los 109 MB de la base
cruda de Kaggle.

MOTOR DE CONSULTA
-----------------
Sobre esos Parquet, el aplicativo monta DuckDB, un motor OLAP embebido que lee
los archivos directamente (sin cargarlos a RAM) y resuelve SQL analitico con
ejecucion vectorizada.

ORDEN DE EJECUCION: cuarto y ultimo del bloque de base de datos.
"""

import os
import sqlite3 as sql
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

DB_ORIGEN = 'puntualidad_vuelos_2017.db'

# El Data Lake vive en la carpeta `data/` de la raiz del proyecto, que es donde
# el modulo src/query_manager.py espera encontrarlo.
DIRECTORIO_DESTINO = os.path.join('..', 'data')

# Tablas de hechos: se escriben por lotes para no materializar 33.121
# filas en memoria durante la exportacion.
TABLAS_GRANDES = ['vuelos', 'metricas_puntualidad']

# Tablas que no forman parte del modelo analitico y no deben exportarse.
TABLAS_EXCLUIDAS = {'sqlite_sequence'}

TAMANO_LOTE = 50_000

# Compresion. ZSTD ofrece mejor ratio que SNAPPY con una velocidad de lectura
# equivalente para nuestro volumen, y es soportado nativamente por DuckDB.
COMPRESION = 'zstd'


def exportar_tabla_grande(conn, nombre_tabla, ruta_salida):
    """
    Exporta una tabla de hechos escribiendo lote por lote con ParquetWriter.

    El primer lote define el esquema Arrow del archivo; los siguientes se
    anexan. Asi el pico de memoria queda acotado al tamano de un lote y no al
    de la tabla completa.
    """
    generador = pd.read_sql_query(f"SELECT * FROM {nombre_tabla}", conn, chunksize=TAMANO_LOTE)
    escritor = None
    filas = 0

    for lote in generador:
        tabla_arrow = pa.Table.from_pandas(lote, preserve_index=False)
        if escritor is None:
            escritor = pq.ParquetWriter(ruta_salida, tabla_arrow.schema, compression=COMPRESION)
        escritor.write_table(tabla_arrow)
        filas += len(lote)

    if escritor is not None:
        escritor.close()
    return filas


def exportar_tabla_pequena(conn, nombre_tabla, ruta_salida):
    """Exporta una dimension completa en una sola operacion (son catalogos)."""
    df = pd.read_sql_query(f"SELECT * FROM {nombre_tabla}", conn)
    df.to_parquet(ruta_salida, engine='pyarrow', index=False, compression=COMPRESION)
    return len(df)


def exportar_data_lake():
    """Recorre el esquema normalizado y genera un Parquet por cada tabla."""
    if not os.path.exists(DB_ORIGEN):
        raise FileNotFoundError(
            f"No existe '{DB_ORIGEN}'. Ejecute antes los scripts 01, 02 y 03.")

    os.makedirs(DIRECTORIO_DESTINO, exist_ok=True)
    conn = sql.connect(DB_ORIGEN)

    tablas = [fila[0] for fila in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]

    print(f"{'TABLA':<26}{'FILAS':>12}{'TAMANO PARQUET':>18}")
    print("-" * 56)

    total_bytes = 0
    for nombre in tablas:
        if nombre in TABLAS_EXCLUIDAS:
            continue

        ruta = os.path.join(DIRECTORIO_DESTINO, f"{nombre}.parquet")

        if nombre in TABLAS_GRANDES:
            filas = exportar_tabla_grande(conn, nombre, ruta)
        else:
            filas = exportar_tabla_pequena(conn, nombre, ruta)

        peso = os.path.getsize(ruta)
        total_bytes += peso
        print(f"{nombre:<26}{filas:>12,}{peso/1024/1024:>15.2f} MB")

    conn.close()

    peso_origen = os.path.getsize(DB_ORIGEN)
    print("-" * 56)
    print(f"{'TOTAL DATA LAKE':<26}{'':>12}{total_bytes/1024/1024:>15.2f} MB")
    print(f"\nBase normalizada SQLite : {peso_origen/1024/1024:.2f} MB")
    print(f"Data Lake Parquet       : {total_bytes/1024/1024:.2f} MB")
    print(f"Factor de compresion    : {peso_origen/total_bytes:.1f}x")


# ==============================================================================
# BLOQUE DE EJECUCION
# ==============================================================================
if __name__ == "__main__":
    print("=" * 56)
    print("EXPORTACION A DATA LAKE PARQUET")
    print("=" * 56)
    exportar_data_lake()
