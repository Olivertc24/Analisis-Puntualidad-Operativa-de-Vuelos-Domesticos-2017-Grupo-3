# Campos calculados del libro de Tableau

Los seis campos calculados del tablero, con su fórmula exacta, el motivo de que
esté escrita así y el valor que produce sobre el universo completo.

---

## La regla que gobierna todos ellos

**Ninguno usa `AVG()`. Todos son cocientes de sumas.**

El motivo es aritmético: el promedio de un conjunto de promedios **no** es el
promedio del conjunto, salvo que todos los grupos tengan exactamente el mismo
tamaño.

Un ejemplo con datos de este tablero. Si el extracto guardase la demora media por
fila y Tableau la promediara al agrupar por aeronave, un grupo de 2 vuelos con 60
minutos de demora media y otro de 200 vuelos con 3 minutos darían:

| Cálculo | Resultado |
|---|---:|
| `AVG` de las medias | (60 + 3) / 2 = **31,5 min** |
| Cociente de sumas | (120 + 600) / 202 = **3,56 min** |

El primero es casi nueve veces el segundo, y es el incorrecto: pondera igual a un
grupo de 2 vuelos que a uno de 200.

Por eso los extractos guardan **sumas y conteos** —`N operados`, `Minutos de
demora`, `N puntuales`— y los campos calculados reconstruyen el promedio correcto
en cualquier nivel de agregación.

---

## 1. `TasaCobertura` — % de la programación operado

```
SUM([N operados]) / SUM([N vuelos])
```

**Formato:** `p0.0%` · **Fuente:** Programación

Proporción de los vuelos programados que llegó a ejecutarse. Es la medida que
justifica la existencia de la primera página del tablero: sin ella, el lector
supondría que los 33.121 vuelos programados son 33.121 vuelos volados.

| Nivel | Valor |
|---|---:|
| Total de la red | **50,64 %** |

---

## 2. `TasaCancelacion` — % de vuelos cancelados

```
SUM([N cancelados]) / SUM([N vuelos])
```

**Formato:** `p0.00%` · **Fuente:** Programación

Proporción de vuelos con estado `Cancelled`. Se calcula sobre **todos** los
vuelos programados, no sobre los operados: un vuelo cancelado nunca se opera, de
modo que el denominador correcto es la programación.

| Nivel | Valor |
|---|---:|
| Total de la red | 1,25 % |
| Bombardier CRJ-200 | **2,00 %** |
| Airbus A321-200 | **0,15 %** |

Un vuelo de CRJ-200 tiene trece veces más probabilidad de cancelarse que uno de
A321-200.

---

## 3. `DemoraMedia` — demora media de salida en minutos

```
SUM([Minutos de demora]) / SUM([N operados])
```

**Formato:** `n#,##0.00` · **Fuentes:** Puntualidad, Aeropuertos

Minutos medios entre la hora real y la programada de despegue. El denominador es
`N operados` y no `N vuelos`, porque un vuelo que nunca despegó no tiene demora
que promediar.

| Nivel | Valor |
|---|---:|
| Total de la red | **12,21 min** |
| Mediana (calculada en el aplicativo) | 3 min |

La media cuadruplica a la mediana. Es la señal de que la distribución es
**bimodal** y de que ninguna medida de tendencia central la describe por sí sola.

---

## 4. `TasaPuntualidad` — % de vuelos puntuales

```
SUM([N puntuales]) / SUM([N operados])
```

**Formato:** `p0.0%` · **Fuentes:** Puntualidad, Aeropuertos

Proporción de vuelos operados que salió con **15 minutos de demora o menos**. El
umbral de 15 minutos no es arbitrario: es el estándar del sector para el
indicador *On-Time Performance*, y viene ya resuelto desde el ETL en la bandera
`puntual` de la tabla de métricas.

| Nivel | Valor |
|---|---:|
| Total de la red | **95,23 %** |

---

## 5. `RecuperacionMedia` — recuperación media en ruta

```
SUM([Minutos recuperados]) / SUM([N con llegada])
```

**Formato:** `n#,##0.000` · **Fuente:** Puntualidad

Minutos que el vuelo recorta —o pierde— entre el despegue y el aterrizaje.
Positiva si llegó relativamente antes de lo que salió.

**El denominador es `N con llegada`, no `N operados`.** Es la corrección más
importante de esta lista: 58 vuelos despegaron pero no habían aterrizado al
cierre de la base, de modo que su recuperación es desconocida. Dividir entre
`N operados` repartiría el numerador entre 16.773 en lugar de entre 16.715 y
sesgaría el resultado hacia cero.

| Nivel | Valor |
|---|---:|
| Total de la red | **−0,006 min** |

Prácticamente cero: un vuelo que sale tarde llega tarde en la misma medida. Esta
red **no aplica *schedule padding***.

---

## 6. `PctDemora` — % de los minutos de demora

```
SUM([Minutos de demora]) / TOTAL(SUM([Minutos de demora]))
```

**Formato:** `p0.00%` · **Fuente:** Puntualidad

Proporción de los minutos de demora acumulados que corresponde a cada categoría.
`TOTAL()` es una función de tabla: devuelve la suma sobre **toda la partición
visible**, de modo que los porcentajes suman 100 % dentro de cada gráfico y se
recalculan solos cuando el lector aplica un filtro.

| Régimen | % de los minutos |
|---|---:|
| 1. Salida puntual | 0,00 % |
| 2. Demora mínima | 19,52 % |
| 3. Demora leve | 4,02 % |
| 4. Demora moderada | — (tramo vacío) |
| 5. Demora severa | **76,47 %** |

El 4,77 % de los vuelos —los de demora severa— concentra tres cuartas partes de
todos los minutos de demora de la red.

---

## Dimensiones calculadas

Además de las seis medidas, el libro define cuatro **dimensiones** calculadas.
Existen por dos razones técnicas concretas.

### Razón 1: la paleta de colores sólo se aplica sobre dimensiones calculadas

Tableau ignora **en silencio** una paleta declarada sobre una columna nativa del
archivo de datos. Para que la correspondencia valor → color se respete, el campo
debe ser una dimensión calculada. `RegimenPuntualidad` y `EstadoVuelo` existen
por eso.

### Razón 2: Tableau ordena las dimensiones discretas alfabéticamente

Sin intervención, los regímenes aparecían en el orden `Demora leve`,
`Demora minima`, `Demora severa`, `Salida puntual`: alfabético y sin sentido
operativo. Anteponer el número de orden fuerza la secuencia correcta.

| Campo | Fórmula | Qué resuelve |
|---|---|---|
| `RegimenPuntualidad` | `STR([Orden de regimen]) + ". " + [Regimen]` | Paleta verde→rojo **y** orden de menor a mayor demora |
| `EstadoVuelo` | `[Estado]` | Paleta por estado del vuelo |
| `FranjaOrdenada` | `STR([Orden de franja]) + ". " + [Franja]` | Orden cronológico de la jornada |
| `DiaOrdenado` | `STR([Orden de dia]) + ". " + [Dia]` | Orden lunes → domingo |

> **Atención al prefijo.** Como la dimensión antepone el número, el valor que
> Tableau ve es `"1. Salida puntual"`, no `"Salida puntual"`. Las claves de la
> paleta deben incluir ese prefijo: si no coinciden **exactamente**, la
> correspondencia se ignora sin aviso y el gráfico sale con la paleta por
> defecto.

---

## Paleta de colores

Los mismos colores del aplicativo de Streamlit. El color **codifica el régimen**
y no es decorativo: va de verde (a tiempo) a rojo (demora severa).

| Valor | Color |
|---|---|
| 1. Salida puntual | `#2e9e7b` |
| 2. Demora mínima | `#7fbf7b` |
| 3. Demora leve | `#ffb020` |
| 4. Demora moderada | `#e8734a` |
| 5. Demora severa | `#d93636` |

| Estado del vuelo | Color |
|---|---|
| Arrived | `#2e9e7b` |
| Departed | `#7fbf7b` |
| Scheduled | `#1e6091` |
| On Time | `#8a9199` |
| Delayed | `#ffb020` |
| Cancelled | `#d93636` |

> Tableau espera el hexadecimal **en minúsculas**. En mayúsculas ignora la
> correspondencia sin avisar.
