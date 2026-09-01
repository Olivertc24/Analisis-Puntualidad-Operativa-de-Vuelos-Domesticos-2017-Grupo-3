# Registro de transformaciones aplicadas a los extractos

Documento del recorrido que sigue el dato desde el Data Lake Parquet hasta el
libro de Tableau, con la justificación de cada paso.

---

## Cadena completa

```
   data/*.parquet          →   extractos/*.csv   →   *.hyper   →   *.twb   →   *.twbx
   (Data Lake, 0,59 MB)        (agregados)           (extracción)  (libro)    (paquete)

   generar_extractos.py        construir_hyper.py    construir_libro.py   empaquetar.py
```

Cada paso es un script ejecutable y verificable. El proceso completo se repite
con cuatro órdenes y no depende de ninguna manipulación manual dentro de Tableau.

---

## T1 — Agregación desde el Data Lake

**Script:** `generar_extractos.py`

Tableau podría conectarse directamente a los 33.121 vuelos del Data Lake. No se
hace, por tres razones:

| Razón | Detalle |
|---|---|
| **Rendimiento** | Cada interacción del lector reevalúa las consultas del tablero. Sobre extractos agregados la latencia es imperceptible. |
| **Portabilidad** | Un CSV se abre en cualquier instalación de Tableau, incluida Tableau Public, sin conectores ni controladores adicionales. |
| **Granularidad suficiente** | El tablero nunca desciende al vuelo individual: su unidad mínima de lectura es la combinación fecha-franja-modelo-estado o fecha-franja-modelo-régimen. |

---

## T2 — Dos extractos, uno por cada grano del modelo

El modelo de datos tiene **dos tablas de hechos en relación 1:0..1**. Los
extractos respetan esa misma separación, y no es una decisión estética:

| Extracto | Universo | Filas | Responde a |
|---|---|---:|---|
| `programacion.csv` | Los 33.121 vuelos programados | 30.300 | *¿Cuánto de lo programado llega a volar?* |
| `puntualidad.csv` | Los 16.773 vuelos operados | 15.762 | *¿Cómo se comporta en el tiempo lo que sí vuela?* |

Mezclarlos produciría denominadores equivocados. Una tasa de puntualidad
calculada sobre la programación total estaría dividida por un universo que
incluye 16.348 vuelos que nunca despegaron, y arrojaría un 48 % donde el valor
correcto es 95 %.

---

## T3 — Sumas y conteos, nunca promedios

**Los extractos no contienen ni una sola columna de promedio.** Guardan
`N operados`, `N puntuales`, `Minutos de demora`, `Minutos recuperados`.

El motivo está desarrollado en
[`calculos/campos-calculados.md`](../calculos/campos-calculados.md): el promedio
de un conjunto de promedios no es el promedio del conjunto salvo que todos los
grupos tengan el mismo tamaño. Guardando sumas y conteos, Tableau reconstruye el
promedio correcto en cualquier nivel de agregación.

---

## T4 — Columnas de orden para las dimensiones discretas

Tableau ordena las dimensiones discretas **alfabéticamente**. Sin intervención,
los regímenes aparecían como `Demora leve`, `Demora minima`, `Demora severa`,
`Salida puntual`, y los días de la semana como `Domingo`, `Jueves`, `Lunes`…

Los extractos incorporan por eso tres columnas de orden —`Orden de regimen`,
`Orden de franja`, `Orden de dia`— que el libro antepone al texto mediante una
dimensión calculada. El resultado se ordena solo y el orden sobrevive a
cualquier filtro que aplique el lector.

---

## T5 — Denominadores separados para las llegadas

`puntualidad.csv` incluye una columna `N con llegada` distinta de `N operados`.

La razón: **58 vuelos despegaron pero no habían aterrizado** al cierre de la
base. Su demora de salida es válida; su demora de llegada, su recuperación y su
duración real, no. Sin esa columna, la recuperación media se dividiría entre
16.773 en lugar de entre 16.715 y quedaría sesgada hacia cero.

---

## T6 — Recorte del extracto de rutas

**El recorte a las veinte rutas con más demora se hace en SQL, no en Tableau.**

La red tiene 457 rutas, y un gráfico de barras con 457 categorías no se lee.
Tableau permitiría un filtro de N superiores, pero ese filtro se reevaluaría en
cada interacción y —lo que importa más— quedaría oculto para quien inspeccione
el extracto. Escrito en SQL, el criterio de selección es explícito y auditable:

```sql
WITH por_ruta AS (
    SELECT v.origen || ' - ' || v.destino AS ruta,
           SUM(m.demora_salida_min)       AS minutos
    FROM metricas_puntualidad m
    JOIN vuelos v ON m.vuelo_id = v.vuelo_id
    GROUP BY 1 ORDER BY minutos DESC LIMIT 20
)
```

---

## T7 — Identificador de fila para la dispersión geográfica

`aeropuertos.csv` incorpora una columna `Id aeropuerto` generada con
`ROW_NUMBER() OVER (ORDER BY "Codigo")`.

No es decorativa: **sin un identificador de fila en el nivel de detalle
(`<lod>`), Tableau colapsa las 104 marcas en un único punto promedio.** El
identificador es lo que obliga al motor a dibujar una marca por aeropuerto.

---

## T8 — Conversión a extracción Hyper

**Script:** `construir_hyper.py`

Tableau Public **sólo publica libros cuyas fuentes de datos sean extracciones**.
Un libro conectado en vivo a CSV se abre sin problema en Tableau Desktop, pero al
guardarlo en Tableau Public devuelve:

> Los libros de trabajo guardados en Tableau Public deben usar extracciones. La
> fuente de datos `<nombre>` no es una extracción.

El script convierte los cuatro CSV en un único `.hyper` con una tabla por
extracto. El motor Hyper carga mucho más rápido desde Parquet que fila a fila, de
modo que cada CSV se convierte primero a un Parquet temporal y después se
ingiere con `CREATE TABLE ... AS (SELECT * FROM external('...'))`. Los
temporales se borran al terminar.

Los tipos de columna se deducen con **la misma función** que emplea
`construir_libro.py`, de modo que el esquema declarado en el libro y el esquema
real de la extracción no puedan divergir.

| Tabla de la extracción | Origen | Filas | Columnas |
|---|---|---:|---:|
| `Programacion` | `programacion.csv` | 30.300 | 18 |
| `Puntualidad` | `puntualidad.csv` | 15.762 | 21 |
| `Aeropuertos` | `aeropuertos.csv` | 104 | 10 |
| `Rutas` | `rutas_criticas.csv` | 77 | 9 |

---

## T9 — Empaquetado en `.twbx`

**Script:** `empaquetar.py`

Un `.twbx` es un ZIP que lleva dentro el libro y sus datos, de modo que se abre
en cualquier equipo sin reconfigurar las fuentes y se publica en un solo paso.

La convención de rutas dentro del paquete **no es libre**: la extracción debe ir
bajo `Data/`, que es exactamente la ruta que el libro declara en el atributo
`dbname` de su conexión.

---

## Control de consistencia

`generar_extractos.py` termina comprobando que los extractos agregados
reproduzcan **exactamente** los totales del Data Lake. Si no lo hicieran, el
tablero mostraría cifras distintas a las del aplicativo de Streamlit y no habría
forma de saber cuál de los dos miente.

Resultado de la ejecución de referencia:

| Concepto | Data Lake | Extracto | |
|---|---:|---:|---|
| Vuelos programados | 33.121 | 33.121 | OK |
| Vuelos operados (`programacion.csv`) | 16.773 | 16.773 | OK |
| Vuelos operados (`puntualidad.csv`) | 16.773 | 16.773 | OK |
| Minutos de demora | 204.740 | 204.740 | OK |
| Vuelos puntuales | 15.973 | 15.973 | OK |
| Vuelos en la dispersión geográfica | 33.121 | 33.121 | OK |

---

## Reproducción

```bash
cd Tableau
python generar_extractos.py    # CSV agregados desde el Data Lake
python construir_hyper.py      # CSV -> extracción .hyper
python construir_libro.py      # libro .twb sobre la extracción
python empaquetar.py           # .twbx portable, listo para publicar
```

El orden importa: cada script consume la salida del anterior.
