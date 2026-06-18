# Problema analítico y descripción del dataset

## 1. Resumen ejecutivo

| Campo                  | Descripción                                                                                                                                                            |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Proyecto**           | Airline Delay Analysis — Q1 2026                                                                                                                                       |
| **Pregunta analítica** | ¿Qué aerolíneas, periodos y factores operativos presentan mayores niveles de retraso y cancelación en vuelos domésticos de EE.UU. durante el primer trimestre de 2026? |
| **Dataset**            | Reporting Carrier On-Time Performance                                                                                                                                  |
| **Fuente**             | Bureau of Transportation Statistics — BTS TranStats                                                                                                                    |
| **Periodo analizado**  | Enero, febrero y marzo de 2026                                                                                                                                         |
| **Granularidad**       | Un registro por vuelo programado                                                                                                                                       |
| **Destino analítico**  | Aurora PostgreSQL                                                                                                                                                      |
| **Schema**             | `airline_dwh`                                                                                                                                                          |
| **Modelo**             | Modelo dimensional tipo estrella                                                                                                                                       |
| **Tabla de hechos**    | `fact_vuelos`                                                                                                                                                          |
| **Dashboard**          | Streamlit + Plotly                                                                                                                                                     |

---

## 2. Problema y motivación

La puntualidad aérea es un indicador clave para evaluar la eficiencia operativa de las aerolíneas. Los retrasos y cancelaciones afectan directamente la experiencia del pasajero, la planeación de recursos, los costos operativos y la confiabilidad del servicio.

Durante el primer trimestre del año, los vuelos pueden verse afectados por factores como clima invernal, congestión operativa, disponibilidad de aeronaves, demoras acumuladas y variaciones en la demanda. Por ello, analizar el comportamiento de los vuelos durante Q1 permite identificar patrones relevantes de desempeño por aerolínea, periodo y causa operativa.

Este proyecto busca responder la siguiente pregunta analítica:

> **¿Qué aerolíneas, periodos y factores operativos presentan mayores niveles de retraso y cancelación en vuelos domésticos de EE.UU. durante el primer trimestre de 2026?**

A partir de esta pregunta, el análisis se enfoca en identificar:

1. Qué aerolíneas presentan mayor retraso promedio de llegada.
2. Cómo evoluciona el retraso promedio a lo largo del trimestre.
3. Qué días de la semana presentan mayor proporción de vuelos retrasados.
4. Qué causas explican la mayor cantidad de cancelaciones.
5. Qué patrones operativos pueden observarse mediante SQL avanzado y visualizaciones interactivas.

---

## 3. Origen de los datos

Los datos crudos provienen del portal público **TranStats** del **Bureau of Transportation Statistics**, específicamente del dataset **Reporting Carrier On-Time Performance**.

Este dataset contiene información operativa de vuelos domésticos en Estados Unidos, reportada por aerolíneas comerciales. Los datos incluyen información de horarios, retrasos, cancelaciones, causas de retraso, aeropuertos, aerolíneas, distancia y tiempo de vuelo.

Para este proyecto se utilizaron tres archivos mensuales:

```text
datasets/raw/
├── flights_2026_01.csv
├── flights_2026_02.csv
└── flights_2026_03.csv
```

Aurora PostgreSQL no es la fuente original de los datos. La fuente original es BTS TranStats. Aurora funciona como destino analítico, donde los archivos CSV son cargados después del proceso de transformación.

---

## 4. Flujo general del proyecto

El flujo del proyecto sigue una lógica end-to-end:

```text
BTS TranStats
     ↓
Archivos CSV locales
     ↓
ETL en Python
     ↓
Modelo dimensional en Aurora PostgreSQL
     ↓
Consultas SQL avanzadas
     ↓
Dashboard interactivo en Streamlit
     ↓
Resultados y conclusiones
```

El proceso completo permite pasar de datos crudos a una estructura analítica lista para consulta, visualización y generación de hallazgos.

---

## 5. Descripción del dataset

El dataset contiene información a nivel vuelo. Cada fila representa un vuelo programado e incluye variables relacionadas con la operación del vuelo, su puntualidad y posibles causas de retraso o cancelación.

Entre las columnas principales se encuentran:

| Tipo de variable      | Ejemplos                                                                               |
| --------------------- | -------------------------------------------------------------------------------------- |
| **Fecha**             | `FL_DATE`, `YEAR`, `MONTH`, `DAY_OF_MONTH`, `DAY_OF_WEEK`                              |
| **Aerolínea**         | `OP_UNIQUE_CARRIER`, `OP_CARRIER_AIRLINE_ID`                                           |
| **Origen**            | `ORIGIN`, `ORIGIN_CITY_NAME`, `ORIGIN_STATE_ABR`                                       |
| **Destino**           | `DEST`, `DEST_CITY_NAME`, `DEST_STATE_ABR`                                             |
| **Retrasos**          | `DEP_DELAY`, `ARR_DELAY`, `DEP_DEL15`, `ARR_DEL15`                                     |
| **Cancelaciones**     | `CANCELLED`, `CANCELLATION_CODE`                                                       |
| **Causas de retraso** | `CARRIER_DELAY`, `WEATHER_DELAY`, `NAS_DELAY`, `SECURITY_DELAY`, `LATE_AIRCRAFT_DELAY` |
| **Operación**         | `DISTANCE`, `AIR_TIME`, `TAXI_OUT`, `TAXI_IN`                                          |

Estas variables permiten analizar el desempeño operativo desde varias perspectivas: aerolínea, fecha, aeropuerto, ruta, retraso y cancelación.

---

## 6. Relación con el modelo dimensional

El dataset original fue transformado para alimentar un modelo dimensional tipo estrella dentro del schema:

```sql
airline_dwh
```

La tabla central del modelo es:

```text
fact_vuelos
```

Esta tabla concentra las métricas principales de cada vuelo:

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

Este diseño permite consultar la información de forma eficiente y ordenada, separando los atributos descriptivos de las métricas operativas.

---

## 7. Preguntas analíticas derivadas

A partir del dataset y del modelo dimensional, se definieron las siguientes preguntas de análisis:

1. **¿Qué aerolíneas tienen mayor retraso promedio de llegada?**
2. **¿Cómo cambia el retraso promedio a lo largo del trimestre?**
3. **¿Qué días de la semana concentran mayor porcentaje de vuelos con retraso mayor a 15 minutos?**
4. **¿Qué causas explican la mayor cantidad de cancelaciones?**
5. **¿Qué aerolíneas muestran mejor desempeño operativo durante Q1 2026?**

Estas preguntas se responden mediante consultas SQL avanzadas y visualizaciones dentro del dashboard.

---

## 8. Importancia del análisis

El análisis de retrasos y cancelaciones permite identificar diferencias operativas entre aerolíneas y periodos. También ayuda a detectar patrones asociados a clima, demoras acumuladas, días de mayor afectación y desempeño general de las aerolíneas.

Aunque el proyecto tiene fines académicos, el flujo construido reproduce una lógica común en proyectos reales de inteligencia de datos:

1. Definir un problema analítico.
2. Obtener datos crudos desde una fuente pública.
3. Transformar los datos mediante ETL.
4. Cargar la información en una base de datos analítica.
5. Consultar con SQL avanzado.
6. Visualizar resultados en un dashboard.
7. Documentar hallazgos y conclusiones.
