# ============================================================
# Proyecto: Airline Delay Analysis
# Archivo: dashboard/dashboard.py
# Descripción: Dashboard interactivo con 4 visualizaciones
#   que responden la pregunta analítica del proyecto.
#
# Uso:
#   pip install streamlit pandas sqlalchemy psycopg2-binary plotly python-dotenv
#   streamlit run dashboard/dashboard.py
# ============================================================

import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# ------------------------------------------------------------
# Configuración de página
# ------------------------------------------------------------

st.set_page_config(
    page_title="Airline Delay Analysis — Q1 2026",
    page_icon="✈️",
    layout="wide",
)

st.title("✈️ Airline Delay Analysis — Q1 2026")
st.caption(
    "Análisis de puntualidad de vuelos domésticos EE.UU. · "
    "Fuente: BTS Reporting Carrier On-Time Performance"
)

# ------------------------------------------------------------
# Conexión a Aurora
# ------------------------------------------------------------

@st.cache_resource
def get_engine():
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    url = (
        f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', 5432)}/{os.getenv('DB_NAME')}"
    )
    return create_engine(url, pool_pre_ping=True)

engine = get_engine()

# ------------------------------------------------------------
# Queries — cacheadas para no re-ejecutar en cada interacción
# ------------------------------------------------------------

@st.cache_data(ttl=600)
def load_ranking_aerolineas():
    return pd.read_sql(text("""
        WITH promedios AS (
            SELECT
                a.airline_name,
                a.carrier_code,
                ROUND(AVG(f.arr_delay)::NUMERIC, 2)              AS avg_arr_delay,
                COUNT(*)                                          AS total_vuelos,
                COUNT(*) FILTER (WHERE f.cancelled_flag = 1)     AS cancelados
            FROM      airline_dwh.fact_vuelos f
            JOIN      airline_dwh.dim_aerolinea a USING (aerolinea_key)
            WHERE     f.arr_delay IS NOT NULL
            GROUP BY  a.airline_name, a.carrier_code
        )
        SELECT
            RANK() OVER (ORDER BY avg_arr_delay DESC)::INT AS ranking,
            airline_name,
            carrier_code,
            avg_arr_delay,
            total_vuelos,
            cancelados,
            ROUND((100.0 * cancelados / total_vuelos)::NUMERIC, 2) AS pct_cancelados
        FROM promedios
        ORDER BY ranking
    """), engine)


@st.cache_data(ttl=600)
def load_tendencia_diaria():
    return pd.read_sql(text("""
        SELECT
            d.fecha,
            d.month_name,
            ROUND(AVG(f.arr_delay)::NUMERIC, 2)   AS avg_diario,
            ROUND(AVG(AVG(f.arr_delay)::NUMERIC) OVER (
                ORDER BY d.fecha
                ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
            ), 2)                                  AS promedio_movil_7d
        FROM      airline_dwh.fact_vuelos f
        JOIN      airline_dwh.dim_fecha   d USING (fecha_key)
        WHERE     f.arr_delay IS NOT NULL
        GROUP BY  d.fecha, d.month_name
        ORDER BY  d.fecha
    """), engine)


@st.cache_data(ttl=600)
def load_pct_retraso_dia_semana():
    return pd.read_sql(text("""
        SELECT
            a.airline_name,
            d.day_of_week_name,
            d.day_of_week,
            d.is_weekend,
            COUNT(*)                                              AS total_vuelos,
            COUNT(*) FILTER (WHERE f.arr_del15 = 1)             AS retrasados,
            ROUND((100.0 * COUNT(*) FILTER (WHERE f.arr_del15 = 1)
                / NULLIF(COUNT(*), 0))::NUMERIC, 1)             AS pct_retrasados
        FROM      airline_dwh.fact_vuelos f
        JOIN      airline_dwh.dim_aerolinea a USING (aerolinea_key)
        JOIN      airline_dwh.dim_fecha     d USING (fecha_key)
        GROUP BY  a.airline_name, d.day_of_week_name,
                  d.day_of_week, d.is_weekend
        ORDER BY  d.day_of_week
    """), engine)


@st.cache_data(ttl=600)
def load_cancelaciones_por_mes():
    return pd.read_sql(text("""
        SELECT
            d.month_name,
            d.month,
            c.cancellation_reason,
            COUNT(*) AS total
        FROM      airline_dwh.fact_vuelos     f
        JOIN      airline_dwh.dim_fecha       d USING (fecha_key)
        JOIN      airline_dwh.dim_cancelacion c USING (cancelacion_key)
        WHERE     f.cancelled_flag = 1
          AND     c.cancellation_code IS NOT NULL
        GROUP BY  d.month_name, d.month, c.cancellation_reason
        ORDER BY  d.month, total DESC
    """), engine)


# ------------------------------------------------------------
# Sidebar — filtros globales
# ------------------------------------------------------------

st.sidebar.header("Filtros")

with st.spinner("Cargando datos..."):
    df_ranking    = load_ranking_aerolineas()
    df_tendencia  = load_tendencia_diaria()
    df_dias       = load_pct_retraso_dia_semana()
    df_canceladas = load_cancelaciones_por_mes()

aerolineas_disponibles = sorted(df_ranking["airline_name"].tolist())
aerolineas_sel = st.sidebar.multiselect(
    "Aerolíneas",
    options=aerolineas_disponibles,
    default=aerolineas_disponibles,
)

meses_disponibles = ["January", "February", "March"]
meses_sel = st.sidebar.multiselect(
    "Meses",
    options=meses_disponibles,
    default=meses_disponibles,
)

st.sidebar.markdown("---")
st.sidebar.caption("Datos: BTS On-Time Performance · Q1 2026")

# ------------------------------------------------------------
# Métricas resumen
# ------------------------------------------------------------

col1, col2, col3, col4 = st.columns(4)

total_vuelos    = df_ranking["total_vuelos"].sum()
avg_delay_global = (
    df_ranking["avg_arr_delay"] * df_ranking["total_vuelos"]
).sum() / total_vuelos
total_cancelados = df_ranking["cancelados"].sum()
pct_cancel_global = 100.0 * total_cancelados / total_vuelos

col1.metric("Total vuelos Q1", f"{total_vuelos:,.0f}")
col2.metric("Retraso promedio llegada", f"{avg_delay_global:.1f} min")
col3.metric("Vuelos cancelados", f"{total_cancelados:,.0f}")
col4.metric("Tasa de cancelación", f"{pct_cancel_global:.1f}%")

st.divider()

# ------------------------------------------------------------
# Visualización 1 — Ranking aerolíneas por retraso promedio
# ------------------------------------------------------------

st.subheader("① Ranking de aerolíneas por retraso promedio de llegada")

df_v1 = df_ranking[df_ranking["airline_name"].isin(aerolineas_sel)].copy()

fig1 = px.bar(
    df_v1.sort_values("avg_arr_delay", ascending=True),
    x="avg_arr_delay",
    y="airline_name",
    orientation="h",
    color="avg_arr_delay",
    color_continuous_scale="RdYlGn_r",
    text="avg_arr_delay",
    labels={
        "avg_arr_delay": "Retraso promedio (min)",
        "airline_name":  "Aerolínea",
    },
    title="Retraso promedio de llegada por aerolínea — Q1 2026",
)
fig1.update_traces(texttemplate="%{text:.1f} min", textposition="outside")
fig1.update_layout(coloraxis_showscale=False, height=420)
st.plotly_chart(fig1, use_container_width=True)

# ------------------------------------------------------------
# Visualización 2 — Tendencia diaria con promedio móvil 7d
# ------------------------------------------------------------

st.subheader("② Tendencia diaria de retraso — promedio móvil 7 días")

df_v2 = df_tendencia[df_tendencia["month_name"].isin(meses_sel)].copy()

fig2 = go.Figure()
fig2.add_trace(go.Scatter(
    x=df_v2["fecha"], y=df_v2["avg_diario"],
    mode="lines", name="Retraso diario",
    line=dict(color="#b0c4de", width=1),
    opacity=0.6,
))
fig2.add_trace(go.Scatter(
    x=df_v2["fecha"], y=df_v2["promedio_movil_7d"],
    mode="lines", name="Promedio móvil 7d",
    line=dict(color="#e63946", width=2.5),
))
fig2.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
fig2.update_layout(
    title="Retraso promedio de llegada diario — Q1 2026",
    xaxis_title="Fecha",
    yaxis_title="Minutos de retraso",
    height=380,
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
)
st.plotly_chart(fig2, use_container_width=True)

# ------------------------------------------------------------
# Visualización 3 — Heatmap % retraso por aerolínea × día semana
# ------------------------------------------------------------

st.subheader("③ % vuelos con retraso > 15 min por aerolínea y día de semana")

df_v3 = df_dias[df_dias["airline_name"].isin(aerolineas_sel)].copy()

orden_dias = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
pivot = df_v3.pivot_table(
    index="airline_name",
    columns="day_of_week_name",
    values="pct_retrasados",
    aggfunc="mean",
)[orden_dias]

fig3 = px.imshow(
    pivot,
    color_continuous_scale="RdYlGn_r",
    aspect="auto",
    text_auto=".1f",
    labels=dict(x="Día de semana", y="Aerolínea", color="% retrasados"),
    title="% vuelos con ARR_DEL15 por aerolínea y día — Q1 2026",
)
fig3.update_layout(height=420)
st.plotly_chart(fig3, use_container_width=True)

# ------------------------------------------------------------
# Visualización 4 — Cancelaciones por causa y mes
# ------------------------------------------------------------

st.subheader("④ Cancelaciones por causa y mes")

df_v4 = df_canceladas[df_canceladas["month_name"].isin(meses_sel)].copy()

fig4 = px.bar(
    df_v4,
    x="month_name",
    y="total",
    color="cancellation_reason",
    barmode="group",
    category_orders={"month_name": meses_disponibles},
    labels={
        "total":               "Vuelos cancelados",
        "month_name":          "Mes",
        "cancellation_reason": "Causa",
    },
    title="Cancelaciones por causa y mes — Q1 2026",
    color_discrete_map={
        "Weather":              "#e63946",
        "Carrier":              "#457b9d",
        "National Air System":  "#2a9d8f",
        "Security":             "#e9c46a",
    },
)
fig4.update_layout(height=380)
st.plotly_chart(fig4, use_container_width=True)

# ------------------------------------------------------------
# Tabla de datos descargable
# ------------------------------------------------------------

with st.expander("Ver datos del ranking completo"):
    st.dataframe(
        df_v1.sort_values("avg_arr_delay", ascending=False),
        use_container_width=True,
    )
