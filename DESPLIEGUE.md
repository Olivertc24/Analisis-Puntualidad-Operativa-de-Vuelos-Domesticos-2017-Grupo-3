# Guía de despliegue

Pasos para publicar en línea los dos productos de esta investigación: el aplicativo web
y el tablero. Ambos servicios exigen iniciar sesión con una cuenta personal, de modo que
estos pasos debe ejecutarlos el titular de la cuenta.

---

## 1. Aplicativo web en Streamlit Community Cloud ✅ publicado

**https://puntualidad-vuelos-grupo3.streamlit.app**

El aplicativo está desplegado y funcionando. Se reconstruye solo con cada `push` a
la rama `main`.

### Configuración del despliegue

| Campo | Valor |
|---|---|
| Repository | `Olivertc24/Analisis-Puntualidad-Operativa-de-Vuelos-Domesticos-2017-Grupo-3` |
| Branch | `main` |
| Main file path | `app.py` |
| App URL | `puntualidad-vuelos-grupo3` |

### Por qué el aplicativo es apto para el plan gratuito

- **No hay que subir datos aparte.** El Data Lake en Parquet está versionado en el
  repositorio (`data/`, 0,59 MB), de modo que el aplicativo es autocontenido: no
  depende de ningún servicio externo de almacenamiento ni de la base de 109 MB de
  Kaggle.
- **Las dependencias están verificadas.** Antes de desplegar se instaló
  `requirements.txt` en un entorno limpio y se ejecutaron las siete páginas del
  aplicativo sin ningún error.
- **El repositorio es público**, requisito del plan gratuito de Community Cloud.
- **El consumo de memoria es bajo.** DuckDB consulta los Parquet directamente desde
  disco en lugar de cargarlos en memoria, de modo que el aplicativo se mantiene muy
  por debajo del límite de recursos del plan gratuito.

### Administrar la aplicación

Desde <https://share.streamlit.io> → *My apps*, el menú de la aplicación permite ver
los registros de construcción, reiniciarla o eliminarla. Se reconstruye sola con cada
`push` a la rama `main`.

---

## 2. Tablero en Tableau Public ✅ publicado

**https://public.tableau.com/app/profile/oliver.triveno/viz/Puntualidad_Operativa_Vuelos_2017/1_Coberturadelaprogramacion**

### Estado de los componentes en este repositorio

| Componente | Estado |
|---|---|
| Extractos de datos (`Tableau/extractos/`) | ✅ Generados, con control automático de consistencia contra el Data Lake |
| Scripts generadores reproducibles | ✅ Los cuatro de `Tableau/` |
| Especificación del tablero hoja por hoja | ✅ `Tableau/README.md` |
| Campos calculados con su fórmula exacta | ✅ `Tableau/calculos/campos-calculados.md` |
| Registro de transformaciones | ✅ `Tableau/preparacion/transformacion-datos.md` |
| Extracción `.hyper` | ✅ Se reconstruye con `construir_hyper.py` y viaja dentro del `.twbx`; no se versiona por separado |
| Libro `.twb` | ✅ `Tableau/Puntualidad_Operativa_Vuelos_2017.twb` |
| Paquete `.twbx` publicable | ✅ `Tableau/Puntualidad_Operativa_Vuelos_2017.twbx` |
| Verificación visual | ✅ Las tres páginas capturadas en `Tableau/capturas/` |

### Por qué hace falta el `.twbx` y no basta el `.twb`

Tableau Public **sólo publica libros cuyas fuentes de datos sean extracciones**. Un
libro conectado en vivo a archivos CSV se abre sin problema en Tableau Desktop, pero al
intentar guardarlo en Tableau Public devuelve:

> Los libros de trabajo guardados en Tableau Public deben usar extracciones. La fuente
> de datos `<nombre>` no es una extracción.

Por eso la cadena incluye dos pasos que no serían necesarios para un uso local:
`construir_hyper.py`, que convierte los CSV en una extracción `.hyper`, y
`empaquetar.py`, que envuelve libro y extracción en un `.twbx` portable.

### Regenerar el tablero

```bash
cd Tableau
python generar_extractos.py    # CSV agregados desde el Data Lake
python construir_hyper.py      # CSV -> extracción .hyper
python construir_libro.py      # libro .twb sobre la extracción
python empaquetar.py           # .twbx portable, listo para publicar
```

Páginas del tablero:

- **1. Cobertura de la programación**
- **2. Regímenes de puntualidad**
- **3. Geografía y evolución**

### Publicación

1. Abrir `Tableau/Puntualidad_Operativa_Vuelos_2017.twbx` con **Tableau Public
   Desktop** (gratuito) o Tableau Desktop.
2. **Servidor → Tableau Public → Guardar en Tableau Public**.
3. Iniciar sesión con la cuenta de Tableau Public (gratuita, se crea en
   <https://public.tableau.com>).
4. Al guardar, Tableau devuelve la URL pública del tablero.
5. Añadir esa URL al `README.md` principal y a `Tableau/README.md`.

> **Nota sobre los datos.** Tableau Public empaqueta la extracción dentro del libro
> publicado, de modo que el tablero funciona en línea sin necesidad de alojar los CSV en
> ningún otro sitio. La extracción de este proyecto pesa 0,4 MB, muy por debajo de los
> límites del servicio.
