# Diccionario de datos

Descripción campo por campo de las ocho tablas del modelo, con su procedencia,
tipo, dominio y porcentaje de nulos medido sobre el Data Lake generado.

## Convención de procedencia

Cada campo se marca con una de tres etiquetas:

| Etiqueta | Significado |
|---|---|
| **FUENTE** | Se toma tal cual de `travel.sqlite`, sin modificar su valor. |
| **DERIVADO** | Se calcula a partir de campos de la fuente mediante una regla explícita. |
| **CONSTRUIDO** | No existe en la fuente ni se deduce de un solo campo: es una categoría o medida definida por esta investigación. |

Esta distinción importa: permite al lector saber en todo momento qué está
observando en el dato y qué está observando en las decisiones del equipo.

---

## 1. Tabla de hechos `vuelos` — 33.121 filas

Grano: **un registro por vuelo programado**. Es el universo de programación.

| Campo | Tipo | Procedencia | Descripción | Nulos |
|---|---|---|---|---:|
| `vuelo_id` | INTEGER PK | **FUENTE** (`flights.flight_id`) | Identificador único del vuelo. Se conserva la llave natural de la fuente: ya es estable y única. | 0,00 % |
| `numero_vuelo` | TEXT | **FUENTE** (`flight_no`) | Designador comercial del vuelo (p. ej. `PG0405`). | 0,00 % |
| `fecha_programada` | DATE | **DERIVADO** | Fecha de `scheduled_departure`, formato `AAAA-MM-DD`. Llave foránea al calendario. | 0,00 % |
| `hora_programada` | INTEGER | **DERIVADO** | Hora del día de la salida programada, 0–23. | 0,00 % |
| `franja_id` | INTEGER FK | **CONSTRUIDO** | Franja horaria a la que pertenece la hora programada. | 0,00 % |
| `origen` | TEXT FK | **FUENTE** (`departure_airport`) | Código IATA del aeropuerto de salida. | 0,00 % |
| `destino` | TEXT FK | **FUENTE** (`arrival_airport`) | Código IATA del aeropuerto de llegada. | 0,00 % |
| `aircraft_code` | TEXT FK | **FUENTE** (`aircraft_code`) | Modelo de aeronave asignado. | 0,00 % |
| `estado_id` | INTEGER FK | **DERIVADO** | Estado del vuelo, resuelto contra el catálogo `estados_vuelo`. | 0,00 % |
| `salida_programada` | TEXT | **DERIVADO** (T2) | Sello `AAAA-MM-DD HH:MM:SS`. Se retira el desplazamiento `+03`. | 0,00 % |
| `llegada_programada` | TEXT | **DERIVADO** (T2) | Ídem para la llegada prevista. | 0,00 % |
| `salida_real` | TEXT | **DERIVADO** (T1+T2) | Hora efectiva de despegue. **Nula si el vuelo no se operó.** El valor `\N` de la fuente se convierte aquí a NULL. | **49,36 %** |
| `llegada_real` | TEXT | **DERIVADO** (T1+T2) | Hora efectiva de aterrizaje. | **49,53 %** |
| `tiene_metricas` | INTEGER | **CONSTRUIDO** | `1` si el vuelo generó fila en `metricas_puntualidad`; `0` en caso contrario. Materializa la relación 1:0..1. | 0,00 % |

> **Lectura del 49,36 % de nulos.** No es un defecto del dato: es el resultado
> principal de la primera parte del estudio. Casi la mitad de la programación
> del período corresponde a vuelos futuros respecto del corte de la base o a
> vuelos cancelados. El modelo lo expone en lugar de descartarlo.

---

## 2. Tabla de hechos `metricas_puntualidad` — 16.773 filas

Grano: **un registro por vuelo efectivamente operado**. Es el universo de
operación. **Ninguna de sus medidas existe en la fuente.**

| Campo | Tipo | Procedencia | Descripción | Nulos |
|---|---|---|---|---:|
| `vuelo_id` | INTEGER PK/FK | **FUENTE** | Mismo identificador que en `vuelos`. Llave primaria y foránea a la vez: es lo que hace la relación 1:0..1. | 0,00 % |
| `regimen_id` | INTEGER FK | **CONSTRUIDO** (T5) | Régimen de puntualidad asignado según la demora de salida. | 0,00 % |
| `demora_salida_min` | INTEGER | **DERIVADO** (T3) | `(julianday(salida_real) − julianday(salida_programada)) × 1440`, redondeado. Positiva = salió tarde. | 0,00 % |
| `demora_llegada_min` | INTEGER | **DERIVADO** (T3) | Ídem sobre los sellos de llegada. | 0,35 % |
| `recuperacion_min` | INTEGER | **CONSTRUIDO** (T4) | `demora_salida_min − demora_llegada_min`. **Positiva si el vuelo recortó tiempo en ruta.** | 0,35 % |
| `duracion_programada_min` | INTEGER | **DERIVADO** | Minutos entre los dos sellos programados (tiempo de bloque previsto). | 0,00 % |
| `duracion_real_min` | INTEGER | **DERIVADO** | Minutos entre los dos sellos reales. | 0,35 % |
| `puntual` | INTEGER | **CONSTRUIDO** | `1` si `demora_salida_min ≤ 15`. Criterio estándar del sector (*On-Time Performance*). | 0,00 % |

> **El 0,35 % de nulos** (58 registros) son vuelos con despegue registrado pero
> sin aterrizaje: estaban en el aire en el momento del corte de la base. Sus
> demoras de salida sí son válidas y se usan; las de llegada quedan excluidas de
> los promedios correspondientes.

---

## 3. Dimensión `aeropuertos` — 104 filas

| Campo | Tipo | Procedencia | Descripción | Nulos |
|---|---|---|---|---:|
| `airport_code` | TEXT PK | **FUENTE** | Código IATA de tres letras. | 0,00 % |
| `nombre` | TEXT | **DERIVADO** (T7) | Nombre del aeropuerto, extraído de la clave `"en"` del JSON `airport_name`. | 0,00 % |
| `ciudad` | TEXT | **DERIVADO** (T7) | Ciudad, extraída de la clave `"en"` del JSON `city`. | 0,00 % |
| `zona_horaria` | TEXT | **FUENTE** | Huso horario en formato IANA (p. ej. `Asia/Novokuznetsk`). | 0,00 % |
| `longitud` | REAL | **DERIVADO** (T8) | Primer componente de la cadena `point`. | 0,00 % |
| `latitud` | REAL | **DERIVADO** (T8) | Segundo componente de la cadena `point`. | 0,00 % |

> **El orden importa.** El tipo `point` de PostgreSQL almacena
> `(longitud,latitud)`, el inverso de la convención cartográfica habitual.
> Leerlos al revés desplazaría todos los aeropuertos miles de kilómetros.

---

## 4. Dimensión `aeronaves` — 9 filas

| Campo | Tipo | Procedencia | Descripción | Nulos |
|---|---|---|---|---:|
| `aircraft_code` | TEXT PK | **FUENTE** | Código del modelo (p. ej. `773`, `SU9`, `CR2`). | 0,00 % |
| `modelo` | TEXT | **DERIVADO** (T7) | Nombre comercial, clave `"en"` del JSON `model`. | 0,00 % |
| `alcance_km` | INTEGER | **FUENTE** | Alcance máximo declarado en kilómetros. | 0,00 % |
| `categoria_alcance` | TEXT | **CONSTRUIDO** | `Regional` (< 3.000 km), `Corto y medio alcance` (3.000–6.000), `Largo alcance` (> 6.000). | 0,00 % |
| `asientos` | INTEGER | **DERIVADO** | Capacidad, obtenida contando las filas de `seats` de ese modelo. La fuente no trae un campo de capacidad. | 0,00 % |

Contenido íntegro del catálogo:

| Código | Modelo | Alcance (km) | Categoría | Asientos |
|---|---|---:|---|---:|
| `CN1` | Cessna 208 Caravan | 1.200 | Regional | 12 |
| `CR2` | Bombardier CRJ-200 | 2.700 | Regional | 50 |
| `SU9` | Sukhoi Superjet-100 | 3.000 | Corto y medio alcance | 97 |
| `733` | Boeing 737-300 | 4.200 | Corto y medio alcance | 130 |
| `321` | Airbus A321-200 | 5.600 | Corto y medio alcance | 170 |
| `320` | Airbus A320-200 | 5.700 | Corto y medio alcance | 140 |
| `319` | Airbus A319-100 | 6.700 | Largo alcance | 116 |
| `763` | Boeing 767-300 | 7.900 | Largo alcance | 222 |
| `773` | Boeing 777-300 | 11.100 | Largo alcance | 402 |

---

## 5. Dimensión `estados_vuelo` — 6 filas

| Campo | Tipo | Procedencia | Descripción |
|---|---|---|---|
| `estado_id` | INTEGER PK | **CONSTRUIDO** | Identificador correlativo del catálogo. |
| `codigo` | TEXT | **FUENTE** | Valor literal del campo `status`. |
| `descripcion` | TEXT | **CONSTRUIDO** | Explicación en español del estado. |
| `es_operado` | INTEGER | **CONSTRUIDO** | `1` si el vuelo llegó a ejecutarse. **Gobierna el universo de análisis.** |
| `orden` | INTEGER | **CONSTRUIDO** | Secuencia lógica de presentación. |

| id | Código | Descripción | Operado | Vuelos |
|---:|---|---|:---:|---:|
| 1 | `Arrived` | Vuelo completado: despegó y aterrizó | 1 | 16.707 |
| 2 | `Departed` | Despegó, aún en vuelo al cierre de la base | 1 | 58 |
| 3 | `On Time` | Programado en horario, aún no operado | 0 | 518 |
| 4 | `Scheduled` | Programado a futuro | 0 | 15.383 |
| 5 | `Delayed` | Programado con demora anunciada | 0 | 41 |
| 6 | `Cancelled` | Cancelado | 0 | 414 |

---

## 6. Dimensión `regimenes_puntualidad` — 5 filas

**Es la variable segmentadora del estudio.**

| Campo | Tipo | Procedencia | Descripción |
|---|---|---|---|
| `regimen_id` | INTEGER PK | **CONSTRUIDO** | Identificador del régimen. |
| `etiqueta` | TEXT | **CONSTRUIDO** | Nombre del tramo. |
| `limite_inf_min` | INTEGER | **CONSTRUIDO** | Cota inferior en minutos, inclusiva. |
| `limite_sup_min` | INTEGER | **CONSTRUIDO** | Cota superior, inclusiva. NULL = sin tope. |
| `descripcion` | TEXT | **CONSTRUIDO** | Criterio operativo del tramo. |
| `orden` | INTEGER | **CONSTRUIDO** | Secuencia de menor a mayor demora. |

| id | Etiqueta | Intervalo (min) | Vuelos | % |
|---:|---|---|---:|---:|
| 1 | Salida puntual | 0 | 717 | 4,27 % |
| 2 | Demora mínima | 1 – 5 | 13.999 | 83,46 % |
| 3 | Demora leve | 6 – 15 | 1.257 | 7,49 % |
| 4 | Demora moderada | 16 – 59 | **0** | **0,00 %** |
| 5 | Demora severa | ≥ 60 | 800 | 4,77 % |

> **El tramo vacío es un hallazgo, no un error de diseño.** La distribución de
> la demora resultó ser **bimodal**: el 95,2 % de los vuelos sale con 15 minutos
> de demora o menos, y un grupo separado lo hace con más de tres horas. Entre 16
> y 59 minutos **no hay un solo vuelo**. Se conserva el tramo declarado
> precisamente para que ese vacío quede a la vista del lector.

---

## 7. Dimensión `franjas_horarias` — 5 filas

| Campo | Tipo | Procedencia | Descripción |
|---|---|---|---|
| `franja_id` | INTEGER PK | **CONSTRUIDO** | Identificador de la franja. |
| `etiqueta` | TEXT | **CONSTRUIDO** | Nombre del bloque. |
| `hora_inicio` | INTEGER | **CONSTRUIDO** | Hora inicial, inclusiva. |
| `hora_fin` | INTEGER | **CONSTRUIDO** | Hora final, inclusiva. |
| `orden` | INTEGER | **CONSTRUIDO** | Secuencia cronológica. |

| id | Etiqueta | Horas |
|---:|---|---|
| 1 | Madrugada (00-05) | 00 – 05 |
| 2 | Mañana (06-11) | 06 – 11 |
| 3 | Mediodía (12-15) | 12 – 15 |
| 4 | Tarde (16-19) | 16 – 19 |
| 5 | Noche (20-23) | 20 – 23 |

---

## 8. Dimensión `calendario_operativo` — 61 filas

Una fila por fecha del período observado: **del 16 de julio al 14 de septiembre
de 2017**, 61 días consecutivos sin huecos.

| Campo | Tipo | Procedencia | Descripción |
|---|---|---|---|
| `fecha` | DATE PK | **DERIVADO** | Fecha en formato `AAAA-MM-DD`. |
| `anio` | INTEGER | **DERIVADO** | Año. |
| `mes` | INTEGER | **DERIVADO** | Mes, 1–12. |
| `nombre_mes` | TEXT | **CONSTRUIDO** | Nombre del mes en español. |
| `dia_semana` | INTEGER | **DERIVADO** | 1 = lunes … 7 = domingo. |
| `nombre_dia` | TEXT | **CONSTRUIDO** | Nombre del día en español. |
| `es_fin_semana` | INTEGER | **CONSTRUIDO** | `1` si es sábado o domingo. |

---

## 9. Campos de la fuente deliberadamente descartados

Documentar lo que **no** se cargó es tan importante como documentar lo cargado:
evita que un lector suponga una omisión por descuido.

| Origen | Campo | Motivo de la exclusión |
|---|---|---|
| `airports_data` | `airport_name` (ru), `city` (ru) | Se conserva sólo la variante inglesa. Mantener ambas duplicaría la dimensión sin añadir información analítica. |
| `aircrafts_data` | `model` (ru) | Ídem. |
| `seats` | `seat_no`, `fare_conditions` | El asiento individual no es relevante para la puntualidad; sólo se usa el conteo para derivar la capacidad. |
| `tickets`, `bookings`, `ticket_flights`, `boarding_passes` | Todos | Son la dimensión comercial de la operación, ajena al objeto de esta investigación. **Se analizan en el proyecto del Grupo 10**, que trabaja sobre la misma base con un modelo distinto. |

---

## 10. Verificación del diccionario

Los porcentajes de nulos de este documento se obtienen del Data Lake, no de la
fuente. Para reproducirlos:

```bash
python -c "
import duckdb
for t in ['vuelos','metricas_puntualidad']:
    df = duckdb.connect().execute(f\"SELECT * FROM 'data/{t}.parquet'\").df()
    print(t, len(df))
    print((df.isna().sum() / len(df) * 100).round(2))
"
```
