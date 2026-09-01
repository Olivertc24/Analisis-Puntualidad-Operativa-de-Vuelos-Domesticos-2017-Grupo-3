#!/usr/bin/env python3
"""
empaquetar.py
================================================================================
EMPAQUETADO DEL LIBRO PARA TABLEAU PUBLIC (.twbx)
Investigacion: Puntualidad y regularidad operativa de vuelos domesticos, 2017.
Escuela de Estadistica y Ciencias Actuariales (EECA-UCV) — Computacion II
================================================================================

Un `.twbx` es un ZIP que lleva dentro el libro y sus datos, de modo que se abre
en cualquier equipo sin reconfigurar las fuentes y se puede publicar en Tableau
Public de un solo paso.

La convencion de rutas dentro del paquete no es libre: la extraccion debe ir bajo
`Data/`, que es exactamente la ruta que el libro declara en el atributo `dbname`
de su conexion.

ORDEN DE EJECUCION: ultimo, despues de generar_extractos, construir_hyper y
construir_libro.
"""

import os
import zipfile

from construir_libro import DIRECTORIO, HYPER, SALIDA

TWBX = SALIDA.replace(".twb", ".twbx")


def main():
    for ruta in (SALIDA, os.path.join(DIRECTORIO, HYPER)):
        if not os.path.exists(ruta):
            raise SystemExit(f"falta {os.path.basename(ruta)}: ejecute antes "
                             "construir_hyper.py y construir_libro.py")

    with zipfile.ZipFile(TWBX, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.write(SALIDA, os.path.basename(SALIDA))
        z.write(os.path.join(DIRECTORIO, HYPER), f"Data/{HYPER}")

    print(f"{os.path.basename(TWBX)}: {os.path.getsize(TWBX)/1e6:.1f} MB")
    for info in zipfile.ZipFile(TWBX).infolist():
        print(f"   {info.filename:<44}{info.file_size/1e6:>8.1f} MB")


if __name__ == "__main__":
    main()
