# Airline Delay Analysis — Q1 2026

Proyecto final de análisis de datos con modelo dimensional tipo estrella, ETL en Python, consultas SQL avanzadas y dashboard interactivo en Streamlit.

El proyecto analiza el desempeño de vuelos domésticos en Estados Unidos durante el primer trimestre de 2026, usando información de puntualidad, retrasos y cancelaciones proveniente del dataset **BTS Reporting Carrier On-Time Performance**.

---

## 1. Problema analítico

La puntualidad aérea es un indicador clave para evaluar la eficiencia operativa de las aerolíneas. Los retrasos y cancelaciones afectan la experiencia del pasajero, la planeación de recursos, los costos operativos y la confiabilidad del servicio.

Este proyecto busca responder la siguiente pregunta analítica:

> **¿Qué aerolíneas, periodos y factores operativos presentan mayores niveles de retraso y cancelación en vuelos domésticos de EE.UU. durante el primer trimestre de 2026?**

Para responderla, se construyó un flujo completo de análisis de datos que incluye:

* Diseño de un modelo dimensional.
* Carga y transformación de datos mediante ETL.
* Análisis con SQL avanzado.
* Visualización interactiva en Streamlit.
* Documentación de hallazgos principales.

---

## 2. Dataset utilizado

Se utilizaron archivos mensuales del dataset **Reporting Carrier On-Time Performance**, correspondientes a enero, febrero y marzo de 2026.

Los archivos utilizados se encuentran en:

```text
datasets/raw/
├── flights_2026_01.csv
├── flights_2026_02.csv
└── flights_2026_03.csv
```

El dataset contiene información a nivel vuelo, incluyendo:

* Fecha del vuelo.
* Aerolínea operadora.
* Aeropuerto de origen.
* Aeropuerto de destino.
* Ruta.
* Horarios programados y reales.
* Retrasos de salida y llegada.
* Indicadores de retraso mayor a 15 minutos.
* Cancelaciones.
* Causas de retraso.
* Distancia y tiempo de vuelo.

---

## 3. Estructura del repositorio

```text
airline-delay-analysis/
├── README.md
├── LICENSE
├── analisis/
│   └── queries_analiticas.sql
├── dashboard/
│   └── dashboard.py
├── datasets/
│   ├── README.md
│   └── raw/
│       ├── flights_2026_01.csv
│       ├── flights_2026_02.csv
│       └── flights_2026_03.csv
├── docs/
│   ├── README.md
│   └── esquema_estrella_flights_dwh.png
└── scripts/
    ├── 01_schema_ddl.sql
    ├── 02_dim_fecha_populate.sql
    ├── 03_dim_aerolinea_populate.sql
    ├── 04_dim_cancelacion_populate.sql
    ├── etl_pipeline.py
    └── README.md
```

---

## 4. Modelo de datos

El proyecto utiliza un modelo dimensional orientado a análisis, implementado en PostgreSQL dentro del esquema:

```sql
airline_dwh
```

La tabla central del modelo es:

```text
fact_vuelos
```

Esta tabla contiene las métricas principales de cada vuelo:

* Retraso de salida.
* Retraso de llegada.
* Indicadores de retraso mayor a 15 minutos.
* Tiempo de vuelo.
* Distancia.
* Causas de retraso.
* Llaves hacia dimensiones.

Las dimensiones utilizadas son:

```text
dim_fecha
dim_aerolinea
dim_aeropuerto_origen
dim_aeropuerto_destino
dim_ruta
dim_cancelacion
```

El modelo permite analizar los vuelos por fecha, mes, aerolínea, origen, destino, ruta y causa de cancelación.

La cancelación se modeló mediante la dimensión `dim_cancelacion`, usando los campos:

```text
cancelacion_key
cancellation_code
cancellation_reason
```

Los vuelos cancelados se identifican mediante los códigos:

```text
A = Carrier
B = Weather
C = National Air System
D = Security
```

---

## 5. Proceso ETL

El proceso ETL se encuentra en:

```text
scripts/etl_pipeline.py
```

El pipeline realiza las siguientes tareas:

1. Lee los archivos CSV mensuales desde `datasets/raw/`.
2. Normaliza nombres de columnas.
3. Limpia y convierte tipos de datos.
4. Valida columnas necesarias.
5. Carga dimensiones.
6. Genera llaves para el modelo dimensional.
7. Inserta los registros en `fact_vuelos`.
8. Registra eventos mediante logging.

El ETL permite transformar archivos crudos de vuelos en un modelo analítico listo para consultas SQL y visualización.

---

## 6. Consultas SQL avanzadas

El archivo de análisis se encuentra en:

```text
analisis/queries_analiticas.sql
```

Las consultas incluyen técnicas avanzadas de SQL, como:

* `CTE`.
* `WINDOW FUNCTIONS`.
* `RANK()`.
* `LAG()`.
* `PERCENTILE_CONT`.
* `COUNT(*) FILTER`.
* Promedios móviles.
* Agrupaciones por aerolínea, fecha, día de semana y causa de cancelación.

Estas consultas permiten responder preguntas como:

* ¿Qué aerolíneas tienen mayor retraso promedio?
* ¿Cómo evoluciona el retraso promedio por día?
* ¿Qué días de la semana presentan mayor porcentaje de retrasos?
* ¿Qué causas explican más cancelaciones?
* ¿Existen variaciones relevantes entre meses?

---

## 7. Dashboard interactivo

El dashboard se encuentra en:

```text
dashboard/dashboard.py
```

Se desarrolló con Streamlit y Plotly. Para ejecutarlo:

```bash
streamlit run dashboard/dashboard.py
```

El dashboard incluye filtros interactivos por:

* Aerolínea.
* Mes.

También incluye cuatro visualizaciones principales:

1. **Ranking de aerolíneas por retraso promedio de llegada.**
2. **Tendencia diaria de retraso con promedio móvil de 7 días.**
3. **Mapa de calor de porcentaje de vuelos con retraso mayor a 15 minutos por aerolínea y día de semana.**
4. **Cancelaciones por causa y mes.**

Además, incluye KPIs generales:

* Total de vuelos.
* Retraso promedio de llegada.
* Vuelos cancelados.
* Tasa de cancelación.

---

## 8. Resultados principales

Con datos de enero, febrero y marzo de 2026, el dashboard muestra los siguientes resultados generales:

```text
Total vuelos Q1: 1,671,142
Retraso promedio de llegada: 7.3 minutos
Vuelos cancelados: 55,006
Tasa de cancelación: 3.29%
```

### Hallazgos principales

1. **Spirit Airlines presentó el mayor retraso promedio de llegada**, con aproximadamente 19.7 minutos.

2. **PSA Airlines y JetBlue Airways también registraron retrasos promedio elevados**, por encima de 15 minutos.

3. **Alaska Airlines y Southwest Airlines aparecen entre las aerolíneas con menor retraso promedio**, con valores cercanos a 3 minutos.

4. **La causa principal de cancelación fue Weather**, especialmente durante enero.

5. **Enero concentró un volumen alto de cancelaciones**, principalmente asociadas a clima.

6. **El porcentaje de vuelos con retraso mayor a 15 minutos varía por aerolínea y día de la semana**, lo que sugiere patrones operativos distintos entre compañías.

7. **El promedio móvil de 7 días permite observar periodos específicos con aumentos relevantes de retraso**, especialmente hacia finales de enero y mediados de marzo.

---

## 9. Corrección importante en el dashboard

Durante la validación del dashboard se detectó que las cancelaciones aparecían inicialmente como cero. El problema no estaba en la base de datos, sino en la forma en que el dashboard calculaba el indicador.

El código original intentaba calcular cancelaciones usando una columna tipo:

```sql
f.cancelled_flag
```

Sin embargo, en el modelo final `fact_vuelos` no contiene esa columna. La cancelación está normalizada en la dimensión:

```text
dim_cancelacion
```

Por ello, se corrigió la lógica usando un `JOIN` con `dim_cancelacion` y creando una bandera calculada:

```sql
CASE
    WHEN UPPER(TRIM(COALESCE(c.cancellation_code, ''))) IN ('A', 'B', 'C', 'D')
        THEN 1
    ELSE 0
END AS cancelled_flag
```

Después de esta corrección, el dashboard mostró correctamente:

```text
Vuelos cancelados: 55,006
Tasa de cancelación: 3.29%
```

---

## 10. Tecnologías utilizadas

* Python
* Pandas
* SQLAlchemy
* PostgreSQL / Aurora PostgreSQL
* DBeaver
* Streamlit
* Plotly
* GitHub
* Markdown

---

## 11. Cómo reproducir el proyecto

### 1. Clonar el repositorio

```bash
git clone <URL_DEL_REPOSITORIO>
cd airline-delay-analysis
```

### 2. Crear archivo `.env`

En la raíz del proyecto crear un archivo `.env` con las credenciales de conexión:

```text
DB_USER=usuario
DB_PASSWORD=contraseña
DB_HOST=host
DB_PORT=5432
DB_NAME=nombre_base
```

### 3. Instalar dependencias

```bash
pip install pandas sqlalchemy psycopg2-binary streamlit plotly python-dotenv
```

### 4. Crear el esquema y tablas

Ejecutar en DBeaver o PostgreSQL:

```text
scripts/01_schema_ddl.sql
```

### 5. Poblar dimensiones estáticas

Ejecutar:

```text
scripts/02_dim_fecha_populate.sql
scripts/03_dim_aerolinea_populate.sql
scripts/04_dim_cancelacion_populate.sql
```

### 6. Ejecutar el ETL

```bash
python scripts/etl_pipeline.py
```

### 7. Ejecutar consultas analíticas

```text
analisis/queries_analiticas.sql
```

### 8. Ejecutar dashboard

```bash
streamlit run dashboard/dashboard.py
```

---

## 12. Evidencias de ejecución

La carpeta [`docs/evidencias`](docs/evidencias/) contiene capturas de validación del modelo cargado en DBeaver/Aurora PostgreSQL.

Las evidencias incluyen:

* Visualización del schema `airline_dwh` y sus tablas.
* Conteo de registros cargados en `fact_vuelos`.
* Consulta analítica de validación sobre cancelaciones por causa.

---

## 13. Relación con la rúbrica

| Criterio                | Evidencia en el proyecto                                                |
| ----------------------- | ----------------------------------------------------------------------- |
| C1 — Problema analítico | Definición del problema, pregunta analítica y justificación del dataset |
| C2 — Modelo de datos    | Modelo dimensional, DDL PostgreSQL y diagrama estrella                  |
| C3 — Dimensiones        | Scripts SQL para poblar dimensiones                                     |
| C4 — ETL                | Pipeline modular en Python con carga, transformación y validaciones     |
| C5 — SQL avanzado       | Consultas con CTE, window functions, percentiles y filtros agregados    |
| C6 — Dashboard          | Dashboard interactivo en Streamlit con 4 visualizaciones                |
| C7 — Documentación      | README completo con metodología, resultados, instrucciones y hallazgos  |

---

## 14. Conclusión

Este proyecto desarrolló un flujo completo de análisis de datos para estudiar la puntualidad de vuelos domésticos en Estados Unidos durante el primer trimestre de 2026. A partir de archivos CSV públicos del Bureau of Transportation Statistics, se diseñó un modelo dimensional tipo estrella en Aurora PostgreSQL, se construyó un proceso ETL en Python y se generaron consultas SQL avanzadas para analizar retrasos, cancelaciones y patrones operativos por aerolínea, fecha y causa.

El modelo dimensional permitió organizar la información en una estructura analítica clara, facilitando consultas por aerolínea, ruta, fecha, aeropuerto y causa de cancelación. Además, el dashboard interactivo en Streamlit permitió visualizar los principales indicadores del proyecto: total de vuelos, retraso promedio de llegada, vuelos cancelados, tasa de cancelación, ranking de aerolíneas, tendencia diaria de retrasos y distribución de cancelaciones por causa.

Los resultados muestran que existen diferencias relevantes entre aerolíneas en términos de puntualidad. Spirit Airlines presentó el mayor retraso promedio de llegada, mientras que Alaska Airlines y Southwest Airlines registraron mejores niveles de desempeño operativo. También se observó que las cancelaciones estuvieron fuertemente asociadas al clima, especialmente durante enero, lo cual confirma la importancia de analizar el comportamiento de los vuelos por mes y causa operativa.

Finalmente, el proyecto cumple con los elementos principales de un flujo de inteligencia de datos: definición del problema analítico, obtención y preparación de datos, modelado dimensional, carga a base de datos, análisis SQL, visualización interactiva y documentación reproducible. Esto permite que el análisis pueda ser consultado, validado y extendido en futuros trabajos.

