#!/usr/bin/env python3
"""
construir_hyper.py
================================================================================
CONSTRUCCION DE LA EXTRACCION HYPER PARA TABLEAU PUBLIC
Investigacion: Puntualidad y regularidad operativa de vuelos domesticos, 2017.
Escuela de Estadistica y Ciencias Actuariales (EECA-UCV) — Computacion II
================================================================================

POR QUE HACE FALTA
------------------
Tableau Public **solo publica libros cuyas fuentes de datos sean extracciones**.
Un libro conectado en vivo a archivos CSV se puede abrir en Tableau Desktop, pero
al intentar guardarlo en Tableau Public devuelve:

    Los libros de trabajo guardados en Tableau Public deben usar extracciones.
    La fuente de datos <nombre> no es una extraccion.

Este script convierte los extractos CSV de `extractos/` en un unico archivo
`.hyper` —el formato columnar propio de Tableau— con una tabla por extracto.

COMO SE CONSTRUYE
-----------------
El motor Hyper carga mucho mas rapido desde Parquet que fila a fila, asi que cada
CSV se convierte primero a un Parquet temporal y despues se ingiere con
`CREATE TABLE ... AS (SELECT * FROM external('...'))`. Los temporales se borran
al terminar.

Los tipos de columna se deducen con la misma logica que emplea
`construir_libro.py`, de modo que el esquema declarado en el libro y el esquema
real de la extraccion no puedan divergir.

ORDEN DE EJECUCION
------------------
    python generar_extractos.py    # CSV desde el Data Lake
    python construir_hyper.py      # este script: CSV -> .hyper
    python construir_libro.py      # libro .twb sobre la extraccion
    python empaquetar.py           # .twbx portable, listo para publicar
"""

import os
import shutil

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from tableauhyperapi import HyperProcess, Connection, Telemetry, CreateMode

from construir_libro import inferir, EXTRACTOS, DIRECTORIO, TABLAS_HYPER, HYPER

TIPO_PANDAS = {"integer": "int64", "real": "float64", "string": "string"}


def cargar(nombre_csv, tipos):
    """Lee un extracto CSV imponiendo los tipos deducidos del propio archivo."""
    df = pd.read_csv(os.path.join(EXTRACTOS, nombre_csv))
    for col in tipos:
        destino = TIPO_PANDAS[col["t"]]
        if destino == "string":
            df[col["n"]] = df[col["n"]].astype("string").fillna("")
        else:
            df[col["n"]] = pd.to_numeric(df[col["n"]], errors="coerce")
            if destino == "int64":
                df[col["n"]] = df[col["n"]].fillna(0).astype("int64")
    return df


def main():
    ruta_hyper = os.path.join(DIRECTORIO, HYPER)
    if os.path.exists(ruta_hyper):
        os.remove(ruta_hyper)

    print("=" * 62)
    print("CONSTRUCCION DE LA EXTRACCION HYPER")
    print("=" * 62)
    print(f"{'TABLA':<16}{'ORIGEN':<28}{'FILAS':>10}{'COLUMNAS':>10}")
    print("-" * 62)

    primero = True
    for tabla, archivo in TABLAS_HYPER.items():
        tipos = inferir(os.path.join(EXTRACTOS, archivo))
        df = cargar(archivo, tipos)

        temporal = os.path.join(DIRECTORIO, f"_{tabla}.parquet")
        pq.write_table(pa.Table.from_pandas(df, preserve_index=False), temporal)

        modo = CreateMode.CREATE_AND_REPLACE if primero else CreateMode.NONE
        with HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
            with Connection(hp.endpoint, ruta_hyper, modo) as cn:
                if primero:
                    cn.catalog.create_schema("Extract")
                cn.execute_command(
                    f'CREATE TABLE "Extract"."{tabla}" AS '
                    f"(SELECT * FROM external('{temporal}'))")
                filas = cn.execute_scalar_query(
                    f'SELECT COUNT(*) FROM "Extract"."{tabla}"')
        os.remove(temporal)
        primero = False
        print(f"{tabla:<16}{archivo:<28}{filas:>10,}{len(df.columns):>10}")

    print("-" * 62)
    print(f"{HYPER}: {os.path.getsize(ruta_hyper)/1e6:.1f} MB")


if __name__ == "__main__":
    main()
