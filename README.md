![Puntualidad operativa de vuelos domésticos](assets/banner_puntualidad.png)

### ▶ Aplicativo en vivo: **[puntualidad-vuelos-grupo3.streamlit.app](https://puntualidad-vuelos-grupo3.streamlit.app)**

# Puntualidad y regularidad operativa de vuelos domésticos (julio–septiembre de 2017)

Investigación estadística descriptiva sobre **33.121 vuelos programados** en una red
aérea doméstica durante 61 días consecutivos, de los cuales **16.773 llegaron a
operarse**.

El proyecto separa dos preguntas que suelen mezclarse cuando se habla de puntualidad
aérea: **cuánto de lo programado llega a volar**, y **cómo se comporta en el tiempo lo
que sí vuela**. Son dos fenómenos distintos —uno de cobertura, otro de desempeño— y
confundirlos produce indicadores que parecen razonables y no lo son.

---

## Los hallazgos centrales

### 1. La mitad de la programación nunca se ejecutó

| Estado | Vuelos | % | ¿Genera métricas? |
|---|---:|---:|:---:|
| Programados **(total)** | **33.121** | **100 %** | — |
| `Arrived` — completado | 16.707 | 50,44 % | Sí |
| `Departed` — en vuelo al cierre de la base | 58 | 0,18 % | Sí |
| `Scheduled` — programado a futuro | 15.383 | 46,44 % | No |
| `On Time` — en horario, aún no operado | 518 | 1,56 % | No |
| `Delayed` — con demora anunciada, aún no operado | 41 | 0,12 % | No |
| `Cancelled` — cancelado | 414 | 1,25 % | 8 sí, 406 no |
| **Operados (con métricas)** | **16.773** | **50,64 %** | — |

Los ocho vuelos `Cancelled` que sí generan métricas son la anomalía de la fuente que se
declara más abajo: están marcados como cancelados y sin embargo tienen hora real de
despegue y de aterrizaje.

Cualquier indicador de puntualidad calculado sobre el total programado estaría dividido
por un denominador equivocado. Por eso el modelo carga **los 33.121 vuelos** y marca
cuáles generan métricas, en lugar de descartar los demás: la cobertura del registro es
en sí misma un resultado del estudio.

### 2. La demora es bimodal: la media no describe a nadie

| Estadístico de la demora de salida | Valor |
|---|---:|
| Media | 12,21 min |
| **Mediana** | **3 min** |
| Desviación típica | 41,41 min |
| Coeficiente de variación | 339 % |
| Máximo | 277 min |

La media cuadruplica a la mediana. La razón es que la distribución **no tiene una sola
moda**: el 95,23 % de los vuelos sale con 15 minutos de demora o menos, y un grupo
separado lo hace con más de una hora. **Entre 16 y 59 minutos no hay un solo vuelo.**

| Régimen | Intervalo | Vuelos | % |
|---|---|---:|---:|
| Salida puntual | 0 min | 717 | 4,27 % |
| Demora mínima | 1 – 5 min | 13.999 | 83,46 % |
| Demora leve | 6 – 15 min | 1.257 | 7,49 % |
| **Demora moderada** | **16 – 59 min** | **0** | **0,00 %** |
| Demora severa | ≥ 60 min | 800 | 4,77 % |

El tramo vacío se conserva en el catálogo precisamente para que quede a la vista.

### 3. Una minoría concentra el problema

**487 vuelos —el 2,9 % de los operados— acumulan la mitad de todos los minutos de
demora del período.** No hay un problema general de puntualidad: hay un problema
concentrado en una fracción muy pequeña de la operación.

### 4. No hay recuperación en ruta

La **recuperación media es de −0,006 minutos**: prácticamente cero. Un vuelo que sale
tarde llega tarde exactamente en la misma medida. Esta red **no aplica *schedule
padding***, la práctica de inflar el tiempo de bloque programado para absorber demoras
de salida.

### 5. La cancelación depende del tipo de aeronave

| Modelo | Vuelos | Cancelados | Tasa |
|---|---:|---:|---:|
| Bombardier CRJ-200 | 9.048 | 181 | **2,000 %** |
| Airbus A319-100 | 1.239 | 24 | 1,937 % |
| Cessna 208 Caravan | 9.273 | 115 | 1,240 % |
| Boeing 737-300 | 1.274 | 15 | 1,177 % |
| Sukhoi Superjet-100 | 8.504 | 69 | 0,811 % |
| Boeing 767-300 | 1.221 | 6 | 0,491 % |
| Boeing 777-300 | 610 | 1 | 0,164 % |
| Airbus A321-200 | 1.952 | 3 | **0,154 %** |

Un vuelo de CRJ-200 tiene **trece veces más probabilidad de cancelarse** que uno de
A321-200.

---

## Arquitectura del proyecto

```
                    Kaggle: travel.sqlite  (109 MB, 8 tablas)
                                  │
                                  ▼
        [ETL]  Normalización a 3FN · esquema en estrella · relación 1:0..1
                                  │
                                  ▼
              SQLite normalizado  (6,5 MB, 8 tablas, 6 dimensiones)
                                  │
                                  ▼
         [Exportación]  Formato columnar Parquet + compresión ZSTD
                                  │
                                  ▼
                   Data Lake  (0,59 MB — versionado en el repositorio)
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
            DuckDB + Streamlit             Tableau Desktop
         (investigación interactiva)      (tablero ejecutivo)
```

### ¿Por qué este conjunto de herramientas?

| Herramienta | Papel en el proyecto | Razón de la elección |
|---|---|---|
| **SQLite** | Motor del esquema normalizado | Sin servidor, portable, con integridad referencial completa. |
| **pandas** | Transformación en el ETL | Manejo cómodo del tipado y de los nulos durante la depuración. |
| **Parquet** | Formato del Data Lake | Almacenamiento columnar: reduce el volumen **11×** y permite leer sólo las columnas que cada consulta necesita. |
| **DuckDB** | Motor analítico del aplicativo | OLAP embebido y vectorizado; consulta los Parquet directamente, sin cargarlos en memoria. |
| **Streamlit** | Aplicativo de la investigación | Publica el análisis completo —metodología, resultados y terminal SQL— en una interfaz navegable. |
| **Tableau** | Tablero ejecutivo | Lectura visual de las métricas macro, complementaria al detalle estadístico del aplicativo. |

---

## Metodología

Investigación de **nivel descriptivo**, diseño **no experimental** y **documental sobre
fuente secundaria**. Al trabajar con el universo completo de registros y no con una
muestra, las medidas calculadas son **parámetros** y no estimadores: no se realizan
pruebas de significación ni inferencias más allá del universo procesado.

### Pregunta de investigación

> ¿Qué proporción de la programación aérea llega a ejecutarse, y cómo se distribuye la
> demora de salida de los vuelos que sí se operan, según su régimen de puntualidad, su
> franja horaria, su ruta y el tipo de aeronave asignada?

### Objetivo general

Caracterizar la puntualidad y la regularidad operativa de una red aérea doméstica
durante el período observado, distinguiendo entre la cobertura de la programación y el
desempeño temporal de los vuelos efectivamente operados.

### Objetivos específicos

1. Normalizar la base original hasta la Tercera Forma Normal mediante un esquema en
   estrella con integridad referencial verificada.
2. Modelar la relación entre programación y operación como **1:0..1**, de modo que la
   proporción de vuelos no ejecutados sea medible en lugar de quedar oculta.
3. Construir las medidas de puntualidad —demora de salida y de llegada, recuperación en
   ruta y duración de bloque—, que **no existen en la fuente**.
4. Definir una variable segmentadora de regímenes de puntualidad ajustada a la
   distribución empírica observada.
5. Calcular los estadísticos descriptivos de tendencia central, posición, dispersión y
   forma de la demora.
6. Describir el patrón horario, semanal, geográfico y por tipo de aeronave de la
   operación.
7. Desarrollar un aplicativo en Streamlit y un tablero en Tableau que permitan explorar
   la investigación y reproducir sus resultados.

### Universo y unidad de análisis

- **Universo de programación:** los 33.121 vuelos programados entre el 16 de julio y el
  14 de septiembre de 2017 registrados en la base.
- **Universo de operación:** los 16.773 vuelos de ese conjunto con hora real de salida
  registrada.
- **Unidad de análisis:** cada vuelo individual (`vuelo_id`), trazable hasta la fuente
  mediante el mismo identificador.
- **Técnicas:** distribuciones de frecuencias absolutas, relativas y acumuladas;
  medidas de tendencia central, posición, dispersión y forma; concentración acumulada
  mediante funciones de ventana.

### Criterio de clasificación de los regímenes

Los cortes **no son convencionales**. Se fijaron tras observar la distribución empírica
de la demora, que resultó ser bimodal, e incorporan el umbral de 15 minutos que el
sector emplea como estándar del indicador de puntualidad (*On-Time Performance*). Una
partición en intervalos de igual amplitud habría repartido esa realidad en tramos sin
significado operativo.

---

## Advertencias sobre la fuente

Este proyecto trabaja con la base de demostración que PostgreSQL distribuye con fines
didácticos, exportada a SQLite. Es un conjunto **sintético**, y el aplicativo lo declara
en su primera pantalla:

1. **Ocho vuelos marcados como cancelados tienen hora real de salida y de llegada.** No
   pueden estar cancelados si despegaron y aterrizaron. El ETL **los conserva tal cual**
   y la inconsistencia se declara, en lugar de reclasificarlos en silencio.
2. **El tramo de demora moderada está vacío.** En una operación real esa franja está
   poblada; su ausencia delata el generador que produjo los datos.

Ninguna de las dos se corrige. Hacerlo ocultaría al lector que está trabajando con datos
sintéticos, un hecho que condiciona la interpretación de todo lo demás.

---

## Estructura del repositorio

```
├── app.py                          Tablero principal de la investigación
├── requirements.txt
├── .streamlit/config.toml          Tema visual "Pista"
│
├── Base de datos/
│   ├── 01_creacion_esquema.py      Esquema en estrella + índices
│   ├── 02_poblacion_catalogos.py   Catálogos depurados y dimensiones construidas
│   ├── 03_procesamiento_carga.py   ETL + diez controles de integridad
│   ├── 04_exportacion_parquet.py   Generación del Data Lake
│   ├── MODELADO_DE_DATOS.md        Diseño del modelo y decisiones justificadas
│   └── DICCIONARIO_DE_DATOS.md     Diccionario campo por campo
│
├── data/                           Data Lake Parquet (8 archivos, 0,59 MB)
│
├── src/
│   ├── query_manager.py            Motor DuckDB sobre el Data Lake
│   └── stats_logic.py              Toda la lógica estadística del proyecto
│
├── pages/
│   ├── 01_Marco_Metodologico.py    Problema, objetivos, operacionalización
│   ├── 02_Marco_Teorico.py         Antecedentes y fundamentos
│   ├── 03_Cuestionario_SQL.py      Seis consultas analíticas resueltas
│   ├── 04_FlightQuery.py           Terminal SQL + diccionario de datos
│   ├── 05_Conclusiones.py          Resultados, limitaciones y continuidad
│   └── 06_Bibliografia.py          Referencias
│
└── Tableau/
    ├── README.md                   Documentación del tablero
    ├── extractos/                  Fuentes de datos del tablero (CSV)
    ├── preparacion/                Transformaciones aplicadas
    └── calculos/                   Campos calculados y su fórmula
```

---

## Puesta en marcha

### 1. Clonar el repositorio

```bash
git clone https://github.com/Olivertc24/Analisis-Puntualidad-Operativa-de-Vuelos-Domesticos-2017-Grupo-3.git
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Ejecutar el aplicativo

```bash
streamlit run app.py
```

El Data Lake viene incluido en el repositorio, de modo que **el aplicativo funciona sin
descargar nada más**.

### Aplicativo publicado

El aplicativo está desplegado en Streamlit Community Cloud y es accesible sin instalar
nada:

**https://puntualidad-vuelos-grupo3.streamlit.app**

Se actualiza solo: cada `push` a la rama `main` vuelve a construir la aplicación. Los
detalles del despliegue están en la [guía de despliegue](DESPLIEGUE.md).

### 4. (Opcional) Reconstruir la base desde cero

Sólo si desea reproducir el proceso completo. Requiere descargar
[la base original de Kaggle](https://www.kaggle.com/datasets/saadharoon27/airlines-dataset)
y colocar `travel.sqlite` en la carpeta padre del repositorio:

```bash
cd "Base de datos"
python 01_creacion_esquema.py
python 02_poblacion_catalogos.py
python 03_procesamiento_carga.py
python 04_exportacion_parquet.py
```

Tiempo total de referencia: **menos de cinco segundos**. Para indicar otra ubicación de
la base cruda, use la variable de entorno `TRAVEL_DB_PATH`.

---

## Proyecto complementario

La misma base sostiene un segundo estudio con un modelo de datos completamente distinto:
**[Comercialización y ocupación de vuelos domésticos — Grupo 10](https://github.com/Olivertc24/Analisis-Comercializacion-y-Ocupacion-de-Vuelos-Domesticos-2017-Grupo-10)**,
que analiza el ingreso por clase tarifaria y el llenado de la cabina. Ambos proyectos
usan tablas distintas de la fuente y no comparten ni esquema ni Data Lake.

---

## Fuente de datos

**Airlines Dataset** · Kaggle
https://www.kaggle.com/datasets/saadharoon27/airlines-dataset

El archivo `travel.sqlite` es la exportación a SQLite de `demo`, la base de demostración
que PostgreSQL distribuye con fines didácticos:

> Postgres Professional. *Demo database — airlines*.
> https://postgrespro.com/docs/postgrespro/current/demodb-bookings

---

## Créditos

Material académico elaborado para los estudiantes de la **Escuela de Estadística y
Ciencias Actuariales** de la Universidad Central de Venezuela, asignatura
**Computación II**.
