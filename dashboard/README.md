# Dashboard

Esta carpeta contiene el código del dashboard desarrollado en **Streamlit** y **Plotly** para visualizar los resultados principales del proyecto **Airline Delay Analysis — Q1 2026**.

El dashboard permite explorar el desempeño operativo de vuelos domésticos en Estados Unidos durante enero, febrero y marzo de 2026, utilizando la información cargada en el modelo dimensional `airline_dwh`.

---

## Archivo principal

```text
dashboard.py
```

Para ejecutar el dashboard desde la terminal:

```bash
streamlit run dashboard/dashboard.py
```

---

## Filtros disponibles

El dashboard incluye filtros interactivos para analizar la información por:

* Aerolínea.
* Mes.

Estos filtros permiten comparar el comportamiento de retrasos y cancelaciones entre distintas compañías y periodos del trimestre.

---

## KPIs generales

![KPIs del dashboard](images/kpis_dashboard.png)

La parte superior del dashboard muestra indicadores generales del periodo analizado:

* **Total de vuelos:** cantidad total de registros analizados.
* **Retraso promedio de llegada:** promedio general de minutos de retraso en llegada.
* **Vuelos cancelados:** total de vuelos cancelados.
* **Tasa de cancelación:** porcentaje de vuelos cancelados respecto al total.

Estos indicadores sirven como resumen ejecutivo del desempeño general del trimestre.

---

## Visualizaciones

### 1. Ranking de aerolíneas por retraso promedio de llegada

![Ranking de aerolíneas](images/ranking_aerolineas.png)

Esta gráfica compara el retraso promedio de llegada por aerolínea. Su objetivo es identificar qué compañías presentaron mayores niveles de demora durante el primer trimestre de 2026.

---

### 2. Tendencia diaria de retraso promedio

![Tendencia diaria](images/tendencia_diaria.png)

Esta visualización muestra cómo evolucionó el retraso promedio de llegada a lo largo del trimestre. El promedio móvil de 7 días ayuda a suavizar la variabilidad diaria y permite detectar periodos con aumentos relevantes en los retrasos.

---

### 3. Mapa de calor de vuelos con retraso mayor a 15 minutos

![Heatmap de retrasos](images/heatmap_retrasos.png)

El mapa de calor muestra el porcentaje de vuelos con retraso mayor a 15 minutos por aerolínea y día de la semana. Esta visualización permite identificar patrones operativos asociados a ciertos días y compañías.

---

### 4. Cancelaciones por causa y mes

![Cancelaciones por causa](images/cancelaciones_causa.png)

Esta gráfica muestra la distribución de vuelos cancelados por causa y mes. Permite observar qué factores explicaron la mayor cantidad de cancelaciones, como clima, aerolínea, sistema nacional aéreo o seguridad.

---

## Interpretación general

El dashboard facilita la exploración visual de los principales hallazgos del proyecto. A través de los KPIs y las gráficas, es posible identificar aerolíneas con mayor retraso promedio, periodos con aumentos relevantes en demoras y causas principales de cancelación.

Estas visualizaciones complementan las consultas SQL avanzadas y permiten presentar los resultados de forma más clara e interactiva.
