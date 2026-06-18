# Documentation
Diagramas y documentación complementaria del proyecto.

# Paso 1 — Problema y dataset

---

## Resumen ejecutivo

| Campo | Valor |
|---|---|
| **Pregunta analítica** | ¿Qué aerolíneas, rutas y causas de retraso concentran la mayor pérdida de puntualidad en vuelos domésticos de EE.UU. durante Q1 2026, y cómo varía el desempeño operativo por día de semana y bloque horario? |
| **Dataset** | Reporting Carrier On-Time Performance — Bureau of Transportation Statistics (BTS), enero–marzo 2026. ~1.6 M registros, 50 columnas |
| **Fuente** | [TranStats BTS](https://www.transtats.bts.gov/DL_SelectFields.aspx?QO_fu146_anzr=b0-gvzr&gnoyr_VQ=FGJ) |
| **Modelo** | Estrella con 1 fact + 4 dimensiones (tiempo, aerolínea, aeropuerto origen, aeropuerto destino) |
| **Infraestructura** | Aurora PostgreSQL en AWS (cluster `aurora-mod4`, schema `flights_dwh`) |
| **ETL** | `etl_pipeline.py` end-to-end con pandas + SQLAlchemy + validaciones post-carga |
| **SQL avanzado** | Window functions (ranking de puntualidad semanal), CTE (causa dominante por ruta), `PERCENTILE_CONT` (p50/p95 de retraso), `LAG` (comparación mes a mes), `COUNT FILTER` (% vuelos con retraso >15 min) |
| **Dashboard** | 4 visualizaciones en matplotlib: ranking aerolíneas, mapa de rutas críticas, tendencia diaria Q1, heatmap día×bloque horario |

---

## Problema y motivación

La puntualidad aérea afecta a millones de pasajeros y tiene costos operativos directos para aerolíneas, aeropuertos y sistemas de conexión. Según el BTS, los retrasos aéreos en EE.UU. generan pérdidas superiores a los **28 mil millones de dólares anuales** entre costos directos para aerolíneas y costos indirectos para pasajeros. El Q1 (enero–marzo) es particularmente crítico: concentra disrupciones por clima invernal (CANCELLATION_CODE = B: Weather), congestión posholiday y variabilidad operativa entre aerolíneas de bajo costo y carriers tradicionales.

El dataset del BTS es el estándar de referencia en la industria: cubre **todos los vuelos comerciales domésticos** reportados por los 13 carriers principales de EE.UU., con desglose de retraso por causa (carrier, weather, NAS, security, late aircraft), tiempos de taxi y distancia. Permite responder preguntas operativas reales que un departamento de operaciones o regulación usaría.

Este proyecto responde **tres preguntas concretas**:

1. **¿Qué aerolíneas y rutas concentran el mayor retraso promedio en Q1 2026?**
2. **¿Cuál es la causa dominante de retraso y cómo varía por mes y bloque horario?**
3. **¿Qué porcentaje de vuelos llegan con más de 15 minutos de retraso (ARR_DEL15), por aerolínea y día de semana?**

---

## Origen de los datos

Los datos crudos son públicos y se encuentran en el portal **TranStats** del Bureau of Transportation Statistics, no en Aurora. El ETL los lee desde archivos CSV locales, los transforma y los carga al schema `flights_dwh` del cluster Aurora. Aurora es el **destino analítico**, no la fuente.

### Flujo end-to-end

```
        ┌──────────────────────────────────────────┐
        │  BTS TranStats (portal público EE.UU.)   │
        │  https://www.transtats.bts.gov           │
        │                                          │
        │  • CSVs por mes: ~544k filas / mes       │
        │  • 50 columnas: tiempos, retrasos,       │
        │    causas, aerolínea, aeropuerto          │
        │  • Archivos: flights_2026_01/02/03.csv   │
        └──────────────────┬───────────────────────┘
                           │  lectura local CSV
                           ▼
        ┌──────────────────────────────────────────┐
        │  ETL Python — etl_pipeline.py            │
        │                                          │
        │  Extract:   pd.read_csv(path)            │
        │  Transform: selección de columnas,       │
        │             date_key YYYYMMDD,           │
        │             bloque horario (DEP_TIME_BLK)│
        │             surrogate keys dims          │
        │  Load:      to_sql(method='multi')       │
        └──────────────────┬───────────────────────┘
                           │  INSERT
                           ▼
        ┌──────────────────────────────────────────┐
        │  Aurora PostgreSQL                       │
        │  aurora-mod4.cluster-XXX.rds.amazonaws   │
        │  Schema: flights_dwh                     │
        │                                          │
        │  • 4 dims pobladas con SQL puro          │
        │    (scripts/02-04_*.sql)                 │
        │  • fact_vuelo poblada por ETL            │
        └──────────────────┬───────────────────────┘
                           │  SELECT
                           ▼
        ┌──────────────────────────────────────────┐
        │  Dashboard matplotlib (4 visualizaciones)│
        │  Queries analíticas SQL (5 queries)      │
        └──────────────────────────────────────────┘
```

### Por qué no se incluyen los CSVs en el repositorio

Cada CSV mensual pesa aproximadamente **300–350 MB** y los tres juntos superan el límite de GitHub (100 MB por archivo). Por eso el repositorio incluye únicamente el archivo `datasets/README.md` con instrucciones de descarga reproducibles desde TranStats.

---

## Descripción del dataset

| Atributo | Valor |
|---|---|
| **Fuente** | BTS — Reporting Carrier On-Time Performance |
| **Cobertura** | Vuelos domésticos EE.UU., enero–marzo 2026 |
| **Filas totales (estimado Q1)** | ~1,600,000 (≈ 544k / mes × 3) |
| **Columnas** | 50 |
| **Granularidad** | Un registro por vuelo programado |
| **Carriers cubiertos** | 13 (AA, AS, B6, DL, F9, G4, MQ, NK, OH, OO, UA, WN, YX) |
| **Aeropuertos origen** | 341 únicos en enero; cobertura nacional completa |
| **Rango de distancia** | 31 – 4,983 millas |
| **Tasa de cancelación (enero)** | 4.7 % |
| **Retraso promedio llegada** | 6.4 min (sobre vuelos no cancelados) |

### Columnas clave que alimentan el modelo dimensional

| Columna | Uso en el modelo |
|---|---|
| `FL_DATE`, `YEAR`, `MONTH`, `DAY_OF_MONTH`, `DAY_OF_WEEK` | → `dim_tiempo` |
| `DEP_TIME_BLK` | → bloque horario en `dim_tiempo` |
| `OP_UNIQUE_CARRIER` | → `dim_aerolinea` |
| `ORIGIN`, `ORIGIN_CITY_NAME`, `ORIGIN_STATE_ABR` | → `dim_aeropuerto` (origen) |
| `DEST`, `DEST_CITY_NAME`, `DEST_STATE_ABR` | → `dim_aeropuerto` (destino) |
| `ARR_DELAY`, `DEP_DELAY` | → medidas en `fact_vuelo` |
| `CANCELLED`, `DIVERTED` | → medidas en `fact_vuelo` |
| `CARRIER_DELAY`, `WEATHER_DELAY`, `NAS_DELAY`, `SECURITY_DELAY`, `LATE_AIRCRAFT_DELAY` | → medidas de causa en `fact_vuelo` |
| `DISTANCE`, `AIR_TIME`, `TAXI_OUT`, `TAXI_IN` | → medidas operativas en `fact_vuelo` |
| `ARR_DEL15`, `DEP_DEL15` | → flags de retraso significativo (>15 min) |
