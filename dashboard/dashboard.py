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
from sqlalchemy import create_engine, text, bindparam


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
# Conexión a Aurora/PostgreSQL
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
# Función auxiliar para queries con filtros IN
# ------------------------------------------------------------

def query_with_filters(sql: str):
    """
    Permite usar filtros dinámicos tipo:
        WHERE campo IN :airlines
        WHERE campo IN :months
    con SQLAlchemy.
    """
    return text(sql).bindparams(
        bindparam("airlines", expanding=True),
        bindparam("months", expanding=True),
    )


# ------------------------------------------------------------
# Catálogos para filtros
# ------------------------------------------------------------

@st.cache_data(ttl=600)
def load_filter_options():
    airlines = pd.read_sql(
        text("""
            SELECT DISTINCT
                airline_name
            FROM airline_dwh.dim_aerolinea
            WHERE airline_name IS NOT NULL
            ORDER BY airline_name;
        """),
        engine,
    )

    months = pd.read_sql(
        text("""
            SELECT DISTINCT
                month,
                month_name
            FROM airline_dwh.dim_fecha
            WHERE month_name IS NOT NULL
            ORDER BY month;
        """),
        engine,
    )

    return airlines, months


# ------------------------------------------------------------
# KPIs principales
# ------------------------------------------------------------

@st.cache_data(ttl=600)
def load_kpis(airlines: tuple, months: tuple):
    stmt = query_with_filters("""
        WITH vuelos_base AS (
            SELECT
                f.vuelo_key,
                f.arr_delay,

                CASE
                    WHEN UPPER(TRIM(COALESCE(c.cancellation_code, ''))) IN ('A', 'B', 'C', 'D')
                        THEN 1
                    ELSE 0
                END AS cancelled_flag

            FROM airline_dwh.fact_vuelos f

            JOIN airline_dwh.dim_fecha d
                ON f.fecha_key = d.fecha_key

            JOIN airline_dwh.dim_aerolinea a
                ON f.aerolinea_key = a.aerolinea_key

            LEFT JOIN airline_dwh.dim_cancelacion c
                ON f.cancelacion_key = c.cancelacion_key

            WHERE a.airline_name IN :airlines
              AND d.month_name IN :months
        )

        SELECT
            COUNT(*) AS total_vuelos,
            ROUND(AVG(arr_delay)::NUMERIC, 2) AS avg_arr_delay,
            SUM(cancelled_flag)::BIGINT AS total_cancelados,
            ROUND(
                100.0 * SUM(cancelled_flag) / NULLIF(COUNT(*), 0),
                2
            ) AS pct_cancelados
        FROM vuelos_base;
    """)

    return pd.read_sql(
        stmt,
        engine,
        params={"airlines": airlines, "months": months},
    )


# ------------------------------------------------------------
# Visualización 1 — Ranking aerolíneas
# ------------------------------------------------------------

@st.cache_data(ttl=600)
def load_ranking_aerolineas(airlines: tuple, months: tuple):
    stmt = query_with_filters("""
        WITH vuelos_base AS (
            SELECT
                a.airline_name,
                a.carrier_code,
                f.arr_delay,

                CASE
                    WHEN UPPER(TRIM(COALESCE(c.cancellation_code, ''))) IN ('A', 'B', 'C', 'D')
                        THEN 1
                    ELSE 0
                END AS cancelled_flag

            FROM airline_dwh.fact_vuelos f

            JOIN airline_dwh.dim_fecha d
                ON f.fecha_key = d.fecha_key

            JOIN airline_dwh.dim_aerolinea a
                ON f.aerolinea_key = a.aerolinea_key

            LEFT JOIN airline_dwh.dim_cancelacion c
                ON f.cancelacion_key = c.cancelacion_key

            WHERE a.airline_name IN :airlines
              AND d.month_name IN :months
        ),

        promedios AS (
            SELECT
                airline_name,
                carrier_code,
                ROUND(AVG(arr_delay)::NUMERIC, 2) AS avg_arr_delay,
                COUNT(*) AS total_vuelos,
                SUM(cancelled_flag)::BIGINT AS cancelados
            FROM vuelos_base
            GROUP BY airline_name, carrier_code
        )

        SELECT
            RANK() OVER (ORDER BY avg_arr_delay DESC)::INT AS ranking,
            airline_name,
            carrier_code,
            avg_arr_delay,
            total_vuelos,
            cancelados,
            ROUND(
                100.0 * cancelados / NULLIF(total_vuelos, 0),
                2
            ) AS pct_cancelados
        FROM promedios
        ORDER BY ranking;
    """)

    return pd.read_sql(
        stmt,
        engine,
        params={"airlines": airlines, "months": months},
    )


# ------------------------------------------------------------
# Visualización 2 — Tendencia diaria
# ------------------------------------------------------------

@st.cache_data(ttl=600)
def load_tendencia_diaria(airlines: tuple, months: tuple):
    stmt = query_with_filters("""
        WITH vuelos_base AS (
            SELECT
                d.fecha,
                d.month_name,
                f.arr_delay

            FROM airline_dwh.fact_vuelos f

            JOIN airline_dwh.dim_fecha d
                ON f.fecha_key = d.fecha_key

            JOIN airline_dwh.dim_aerolinea a
                ON f.aerolinea_key = a.aerolinea_key

            WHERE a.airline_name IN :airlines
              AND d.month_name IN :months
        ),

        tendencia AS (
            SELECT
                fecha,
                month_name,
                ROUND(AVG(arr_delay)::NUMERIC, 2) AS avg_diario
            FROM vuelos_base
            GROUP BY fecha, month_name
        )

        SELECT
            fecha,
            month_name,
            avg_diario,
            ROUND(
                AVG(avg_diario) OVER (
                    ORDER BY fecha
                    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                )::NUMERIC,
                2
            ) AS promedio_movil_7d
        FROM tendencia
        ORDER BY fecha;
    """)

    return pd.read_sql(
        stmt,
        engine,
        params={"airlines": airlines, "months": months},
    )


# ------------------------------------------------------------
# Visualización 3 — % retraso por día de semana
# ------------------------------------------------------------

@st.cache_data(ttl=600)
def load_pct_retraso_dia_semana(airlines: tuple, months: tuple):
    stmt = query_with_filters("""
        SELECT
            a.airline_name,
            d.day_of_week_name,
            d.day_of_week,
            d.is_weekend,
            COUNT(*) AS total_vuelos,
            COUNT(*) FILTER (WHERE f.arr_del15 = 1) AS retrasados,
            ROUND(
                100.0 * COUNT(*) FILTER (WHERE f.arr_del15 = 1)
                / NULLIF(COUNT(*), 0),
                1
            ) AS pct_retrasados

        FROM airline_dwh.fact_vuelos f

        JOIN airline_dwh.dim_aerolinea a
            ON f.aerolinea_key = a.aerolinea_key

        JOIN airline_dwh.dim_fecha d
            ON f.fecha_key = d.fecha_key

        WHERE a.airline_name IN :airlines
          AND d.month_name IN :months

        GROUP BY
            a.airline_name,
            d.day_of_week_name,
            d.day_of_week,
            d.is_weekend

        ORDER BY d.day_of_week;
    """)

    return pd.read_sql(
        stmt,
        engine,
        params={"airlines": airlines, "months": months},
    )


# ------------------------------------------------------------
# Visualización 4 — Cancelaciones por causa y mes
# ------------------------------------------------------------

@st.cache_data(ttl=600)
def load_cancelaciones_por_mes(airlines: tuple, months: tuple):
    stmt = query_with_filters("""
        SELECT
            d.month_name,
            d.month,
            c.cancellation_code,
            c.cancellation_reason,
            COUNT(*) AS total

        FROM airline_dwh.fact_vuelos f

        JOIN airline_dwh.dim_fecha d
            ON f.fecha_key = d.fecha_key

        JOIN airline_dwh.dim_aerolinea a
            ON f.aerolinea_key = a.aerolinea_key

        LEFT JOIN airline_dwh.dim_cancelacion c
            ON f.cancelacion_key = c.cancelacion_key

        WHERE a.airline_name IN :airlines
          AND d.month_name IN :months
          AND UPPER(TRIM(COALESCE(c.cancellation_code, ''))) IN ('A', 'B', 'C', 'D')

        GROUP BY
            d.month_name,
            d.month,
            c.cancellation_code,
            c.cancellation_reason

        ORDER BY
            d.month,
            total DESC;
    """)

    return pd.read_sql(
        stmt,
        engine,
        params={"airlines": airlines, "months": months},
    )


# ------------------------------------------------------------
# Sidebar — filtros globales
# ------------------------------------------------------------

st.sidebar.header("Filtros")

with st.spinner("Cargando filtros..."):
    df_airlines_options, df_months_options = load_filter_options()

aerolineas_disponibles = df_airlines_options["airline_name"].dropna().tolist()
meses_disponibles = df_months_options["month_name"].dropna().tolist()

aerolineas_sel = st.sidebar.multiselect(
    "Aerolíneas",
    options=aerolineas_disponibles,
    default=aerolineas_disponibles,
)

meses_sel = st.sidebar.multiselect(
    "Meses",
    options=meses_disponibles,
    default=meses_disponibles,
)

st.sidebar.markdown("---")
st.sidebar.caption("Datos: BTS On-Time Performance · Q1 2026")

if not aerolineas_sel:
    st.warning("Selecciona al menos una aerolínea para mostrar el dashboard.")
    st.stop()

if not meses_sel:
    st.warning("Selecciona al menos un mes para mostrar el dashboard.")
    st.stop()

airlines_param = tuple(aerolineas_sel)
months_param = tuple(meses_sel)


# ------------------------------------------------------------
# Carga de datos ya filtrados
# ------------------------------------------------------------

with st.spinner("Cargando datos del dashboard..."):
    df_kpis = load_kpis(airlines_param, months_param)
    df_ranking = load_ranking_aerolineas(airlines_param, months_param)
    df_tendencia = load_tendencia_diaria(airlines_param, months_param)
    df_dias = load_pct_retraso_dia_semana(airlines_param, months_param)
    df_canceladas = load_cancelaciones_por_mes(airlines_param, months_param)


# ------------------------------------------------------------
# Métricas resumen
# ------------------------------------------------------------

if df_kpis.empty:
    st.error("No se encontraron datos con los filtros seleccionados.")
    st.stop()

kpis = df_kpis.iloc[0]

total_vuelos = int(kpis["total_vuelos"]) if pd.notna(kpis["total_vuelos"]) else 0
avg_delay_global = float(kpis["avg_arr_delay"]) if pd.notna(kpis["avg_arr_delay"]) else 0.0
total_cancelados = int(kpis["total_cancelados"]) if pd.notna(kpis["total_cancelados"]) else 0
pct_cancel_global = float(kpis["pct_cancelados"]) if pd.notna(kpis["pct_cancelados"]) else 0.0

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total vuelos Q1", f"{total_vuelos:,.0f}")
col2.metric("Retraso promedio llegada", f"{avg_delay_global:.1f} min")
col3.metric("Vuelos cancelados", f"{total_cancelados:,.0f}")
col4.metric("Tasa de cancelación", f"{pct_cancel_global:.2f}%")

st.divider()


# ------------------------------------------------------------
# Visualización 1 — Ranking aerolíneas por retraso promedio
# ------------------------------------------------------------

st.subheader("① Ranking de aerolíneas por retraso promedio de llegada")

if df_ranking.empty:
    st.info("No hay datos suficientes para construir el ranking con los filtros seleccionados.")
else:
    fig1 = px.bar(
        df_ranking.sort_values("avg_arr_delay", ascending=True),
        x="avg_arr_delay",
        y="airline_name",
        orientation="h",
        color="avg_arr_delay",
        color_continuous_scale="RdYlGn_r",
        text="avg_arr_delay",
        labels={
            "avg_arr_delay": "Retraso promedio (min)",
            "airline_name": "Aerolínea",
        },
        title="Retraso promedio de llegada por aerolínea — Q1 2026",
    )

    fig1.update_traces(
        texttemplate="%{text:.1f} min",
        textposition="outside",
    )

    fig1.update_layout(
        coloraxis_showscale=False,
        height=420,
        margin=dict(l=20, r=40, t=60, b=40),
    )

    st.plotly_chart(fig1, use_container_width=True)


# ------------------------------------------------------------
# Visualización 2 — Tendencia diaria con promedio móvil 7d
# ------------------------------------------------------------

st.subheader("② Tendencia diaria de retraso — promedio móvil 7 días")

if df_tendencia.empty:
    st.info("No hay datos suficientes para construir la tendencia diaria.")
else:
    fig2 = go.Figure()

    fig2.add_trace(
        go.Scatter(
            x=df_tendencia["fecha"],
            y=df_tendencia["avg_diario"],
            mode="lines",
            name="Retraso diario",
            line=dict(color="#b0c4de", width=1),
            opacity=0.6,
        )
    )

    fig2.add_trace(
        go.Scatter(
            x=df_tendencia["fecha"],
            y=df_tendencia["promedio_movil_7d"],
            mode="lines",
            name="Promedio móvil 7d",
            line=dict(color="#e63946", width=2.5),
        )
    )

    fig2.add_hline(
        y=0,
        line_dash="dash",
        line_color="gray",
        opacity=0.5,
    )

    fig2.update_layout(
        title="Retraso promedio de llegada diario — Q1 2026",
        xaxis_title="Fecha",
        yaxis_title="Minutos de retraso",
        height=380,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=20, r=40, t=60, b=40),
    )

    st.plotly_chart(fig2, use_container_width=True)


# ------------------------------------------------------------
# Visualización 3 — Heatmap % retraso por aerolínea × día semana
# ------------------------------------------------------------

st.subheader("③ % vuelos con retraso > 15 min por aerolínea y día de semana")

if df_dias.empty:
    st.info("No hay datos suficientes para construir el heatmap.")
else:
    orden_dias = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    pivot = (
        df_dias.pivot_table(
            index="airline_name",
            columns="day_of_week_name",
            values="pct_retrasados",
            aggfunc="mean",
        )
        .reindex(columns=orden_dias)
    )

    fig3 = px.imshow(
        pivot,
        color_continuous_scale="RdYlGn_r",
        aspect="auto",
        text_auto=".1f",
        labels=dict(
            x="Día de semana",
            y="Aerolínea",
            color="% retrasados",
        ),
        title="% vuelos con ARR_DEL15 por aerolínea y día — Q1 2026",
    )

    fig3.update_layout(
        height=420,
        margin=dict(l=20, r=40, t=60, b=40),
    )

    st.plotly_chart(fig3, use_container_width=True)


# ------------------------------------------------------------
# Visualización 4 — Cancelaciones por causa y mes
# ------------------------------------------------------------

st.subheader("④ Cancelaciones por causa y mes")

if df_canceladas.empty:
    st.info("No hay vuelos cancelados con los filtros seleccionados.")
else:
    fig4 = px.bar(
        df_canceladas,
        x="month_name",
        y="total",
        color="cancellation_reason",
        barmode="group",
        category_orders={"month_name": meses_disponibles},
        labels={
            "total": "Vuelos cancelados",
            "month_name": "Mes",
            "cancellation_reason": "Causa",
        },
        title="Cancelaciones por causa y mes — Q1 2026",
        color_discrete_map={
            "Weather": "#e63946",
            "Carrier": "#457b9d",
            "National Air System": "#2a9d8f",
            "Security": "#e9c46a",
        },
    )

    fig4.update_layout(
        height=380,
        margin=dict(l=20, r=40, t=60, b=40),
    )

    st.plotly_chart(fig4, use_container_width=True)


# ------------------------------------------------------------
# Tabla de datos descargable
# ------------------------------------------------------------

with st.expander("Ver datos del ranking completo"):
    if df_ranking.empty:
        st.info("No hay datos para mostrar.")
    else:
        st.dataframe(
            df_ranking.sort_values("avg_arr_delay", ascending=False),
            use_container_width=True,
        )

        csv = df_ranking.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Descargar ranking en CSV",
            data=csv,
            file_name="ranking_aerolineas_q1_2026.csv",
            mime="text/csv",
        )
