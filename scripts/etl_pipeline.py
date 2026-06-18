#!/usr/bin/env python3
"""
ETL Pipeline — Airline Delay Analysis (BTS Q1 2026)

Lee los CSVs mensuales del BTS (Reporting Carrier On-Time Performance),
los transforma al modelo dimensional y los carga a Aurora PostgreSQL.

Uso:
    python etl_pipeline.py \\
        --host  aurora-mod4.cluster-XXX.us-east-1.rds.amazonaws.com \\
        --password TU_PASSWORD \\
        --database northwind \\
        --files datasets/raw/flights_2026_01.csv \\
                datasets/raw/flights_2026_02.csv \\
                datasets/raw/flights_2026_03.csv

Prerequisito: las dimensiones estáticas deben estar ya cargadas:
    01_schema_ddl.sql
    02_dim_fecha_populate.sql
    03_dim_aerolinea_populate.sql
    04_dim_cancelacion_populate.sql
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("etl_airline")


# ============================================================
# Extract
# ============================================================

def extract(filepath: str) -> pd.DataFrame:
    """
    Lee un CSV mensual del BTS y devuelve el DataFrame crudo.
    Solo carga las columnas que el modelo dimensional necesita.
    """
    logger.info("Extrayendo: %s", filepath)

    cols = [
        "FL_DATE", "YEAR", "MONTH", "DAY_OF_MONTH", "DAY_OF_WEEK",
        "OP_UNIQUE_CARRIER", "OP_CARRIER_AIRLINE_ID", "OP_CARRIER_FL_NUM",
        "ORIGIN_AIRPORT_ID", "ORIGIN", "ORIGIN_CITY_NAME",
        "ORIGIN_STATE_ABR", "ORIGIN_STATE_NM",
        "DEST_AIRPORT_ID", "DEST", "DEST_CITY_NAME",
        "DEST_STATE_ABR", "DEST_STATE_NM",
        "DEP_TIME_BLK", "CRS_DEP_TIME", "DEP_TIME",
        "DEP_DELAY", "DEP_DELAY_NEW", "DEP_DEL15",
        "CRS_ARR_TIME", "ARR_TIME",
        "ARR_DELAY", "ARR_DELAY_NEW", "ARR_DEL15",
        "TAXI_OUT", "TAXI_IN", "WHEELS_OFF", "WHEELS_ON",
        "CRS_ELAPSED_TIME", "ACTUAL_ELAPSED_TIME", "AIR_TIME",
        "CANCELLED", "CANCELLATION_CODE", "DIVERTED",
        "FLIGHTS", "DISTANCE", "DISTANCE_GROUP",
        "CARRIER_DELAY", "WEATHER_DELAY", "NAS_DELAY",
        "SECURITY_DELAY", "LATE_AIRCRAFT_DELAY",
    ]

    df = pd.read_csv(filepath, usecols=cols, low_memory=False)
    logger.info("  Filas leidas: %s | Columnas: %s", f"{len(df):,}", len(df.columns))
    return df


# ============================================================
# Transform
# ============================================================

def transform(df: pd.DataFrame) -> dict:
    """
    Transforma el DataFrame crudo en los DataFrames listos
    para cada tabla del modelo dimensional.

    Retorna un dict con keys:
        'aeropuertos_origen', 'aeropuertos_destino',
        'rutas', 'fact'
    """
    logger.info("Transformando %s filas...", f"{len(df):,}")
    df = df.copy()

    # ----------------------------------------------------------
    # 1. Parsear fecha y construir fecha_key (YYYYMMDD × bloque)
    # ----------------------------------------------------------
    # FL_DATE viene como '1/1/2026 12:00:00 AM'
    df["_fecha"] = pd.to_datetime(df["FL_DATE"], format="%m/%d/%Y %I:%M:%S %p")
    df["_fecha_str"] = df["_fecha"].dt.strftime("%Y%m%d")

    # El join con dim_fecha usa fecha_key = YYYYMMDD*100 + blk_num
    # Los bloques están numerados 1-19 en 02_dim_fecha_populate.sql
    blk_map = {
        "0001-0559": 1,  "0600-0659": 2,  "0700-0759": 3,
        "0800-0859": 4,  "0900-0959": 5,  "1000-1059": 6,
        "1100-1159": 7,  "1200-1259": 8,  "1300-1359": 9,
        "1400-1459": 10, "1500-1559": 11, "1600-1659": 12,
        "1700-1759": 13, "1800-1859": 14, "1900-1959": 15,
        "2000-2059": 16, "2100-2159": 17, "2200-2259": 18,
        "2300-2359": 19,
    }
    df["_blk_num"] = df["DEP_TIME_BLK"].map(blk_map).fillna(1).astype(int)
    df["fecha_key"] = df["_fecha_str"].astype(int) * 100 + df["_blk_num"]

    # ----------------------------------------------------------
    # 2. Limpiar CANCELLATION_CODE
    #    En el CSV llega como string 'A','B','C','D' o 'NaN'
    # ----------------------------------------------------------
    df["CANCELLATION_CODE"] = df["CANCELLATION_CODE"].replace("NaN", None)

    # ----------------------------------------------------------
    # 3. Dim aeropuerto origen — deduplicar
    # ----------------------------------------------------------
    orig = (
        df[["ORIGIN_AIRPORT_ID", "ORIGIN", "ORIGIN_CITY_NAME",
            "ORIGIN_STATE_ABR", "ORIGIN_STATE_NM"]]
        .drop_duplicates(subset=["ORIGIN"])
        .rename(columns={
            "ORIGIN_AIRPORT_ID": "origin_airport_id",
            "ORIGIN":            "origin",
            "ORIGIN_CITY_NAME":  "origin_city_name",
            "ORIGIN_STATE_ABR":  "origin_state",
            "ORIGIN_STATE_NM":   "origin_state_name",
        })
    )

    # ----------------------------------------------------------
    # 4. Dim aeropuerto destino — deduplicar
    # ----------------------------------------------------------
    dest = (
        df[["DEST_AIRPORT_ID", "DEST", "DEST_CITY_NAME",
            "DEST_STATE_ABR", "DEST_STATE_NM"]]
        .drop_duplicates(subset=["DEST"])
        .rename(columns={
            "DEST_AIRPORT_ID": "dest_airport_id",
            "DEST":            "dest",
            "DEST_CITY_NAME":  "dest_city_name",
            "DEST_STATE_ABR":  "dest_state",
            "DEST_STATE_NM":   "dest_state_name",
        })
    )

    # ----------------------------------------------------------
    # 5. Dim ruta — deduplicar combinaciones origen-destino
    # ----------------------------------------------------------
    rutas = (
        df[["ORIGIN", "DEST", "DISTANCE_GROUP"]]
        .drop_duplicates(subset=["ORIGIN", "DEST"])
        .rename(columns={
            "ORIGIN":         "origin",
            "DEST":           "dest",
            "DISTANCE_GROUP": "distance_group",
        })
    )
    rutas["ruta"] = rutas["origin"] + "-" + rutas["dest"]

    # ----------------------------------------------------------
    # 6. Fact — renombrar y seleccionar columnas finales
    # ----------------------------------------------------------
    fact = df.rename(columns={
        "OP_CARRIER_FL_NUM":    "flight_number",
        "CRS_DEP_TIME":         "crs_dep_time",
        "DEP_TIME":             "dep_time",
        "DEP_DELAY":            "dep_delay",
        "DEP_DELAY_NEW":        "dep_delay_minutes",
        "DEP_DEL15":            "dep_del15",
        "DEP_TIME_BLK":         "dep_time_blk",
        "CRS_ARR_TIME":         "crs_arr_time",
        "ARR_TIME":             "arr_time",
        "ARR_DELAY":            "arr_delay",
        "ARR_DELAY_NEW":        "arr_delay_minutes",
        "ARR_DEL15":            "arr_del15",
        "TAXI_OUT":             "taxi_out",
        "TAXI_IN":              "taxi_in",
        "WHEELS_OFF":           "wheels_off",
        "WHEELS_ON":            "wheels_on",
        "CRS_ELAPSED_TIME":     "crs_elapsed_time",
        "ACTUAL_ELAPSED_TIME":  "actual_elapsed_time",
        "AIR_TIME":             "air_time",
        "CANCELLED":            "cancelled_flag",
        "CANCELLATION_CODE":    "cancellation_code",
        "DIVERTED":             "diverted_flag",
        "FLIGHTS":              "flights",
        "DISTANCE":             "distance",
        "DISTANCE_GROUP":       "distance_group",
        "CARRIER_DELAY":        "carrier_delay",
        "WEATHER_DELAY":        "weather_delay",
        "NAS_DELAY":            "nas_delay",
        "SECURITY_DELAY":       "security_delay",
        "LATE_AIRCRAFT_DELAY":  "late_aircraft_delay",
        "ORIGIN":               "_origin",
        "DEST":                 "_dest",
        "OP_UNIQUE_CARRIER":    "_carrier_code",
    })[
        [
            "fecha_key", "_carrier_code", "_origin", "_dest",
            "flight_number",
            "crs_dep_time", "dep_time", "dep_delay", "dep_delay_minutes",
            "dep_del15", "dep_time_blk",
            "crs_arr_time", "arr_time", "arr_delay", "arr_delay_minutes",
            "arr_del15",
            "taxi_out", "taxi_in", "wheels_off", "wheels_on",
            "crs_elapsed_time", "actual_elapsed_time", "air_time",
            "cancelled_flag", "cancellation_code", "diverted_flag",
            "flights", "distance", "distance_group",
            "carrier_delay", "weather_delay", "nas_delay",
            "security_delay", "late_aircraft_delay",
        ]
    ]

    logger.info(
        "  Origenes únicos: %s | Destinos únicos: %s | Rutas únicas: %s",
        len(orig), len(dest), len(rutas),
    )

    return {
        "aeropuertos_origen":  orig,
        "aeropuertos_destino": dest,
        "rutas":               rutas,
        "fact":                fact,
    }


# ============================================================
# Load helpers
# ============================================================

def _upsert_aeropuertos_origen(df: pd.DataFrame, engine) -> None:
    """INSERT OR IGNORE para dim_aeropuerto_origen."""
    with engine.begin() as conn:
        for _, row in df.iterrows():
            conn.execute(text("""
                INSERT INTO airline_dwh.dim_aeropuerto_origen
                    (origin_airport_id, origin, origin_city_name,
                     origin_state, origin_state_name)
                VALUES
                    (:origin_airport_id, :origin, :origin_city_name,
                     :origin_state, :origin_state_name)
                ON CONFLICT (origin) DO NOTHING
            """), row.to_dict())


def _upsert_aeropuertos_destino(df: pd.DataFrame, engine) -> None:
    """INSERT OR IGNORE para dim_aeropuerto_destino."""
    with engine.begin() as conn:
        for _, row in df.iterrows():
            conn.execute(text("""
                INSERT INTO airline_dwh.dim_aeropuerto_destino
                    (dest_airport_id, dest, dest_city_name,
                     dest_state, dest_state_name)
                VALUES
                    (:dest_airport_id, :dest, :dest_city_name,
                     :dest_state, :dest_state_name)
                ON CONFLICT (dest) DO NOTHING
            """), row.to_dict())


def _upsert_rutas(df: pd.DataFrame, engine) -> None:
    """INSERT OR IGNORE para dim_ruta."""
    with engine.begin() as conn:
        for _, row in df.iterrows():
            conn.execute(text("""
                INSERT INTO airline_dwh.dim_ruta
                    (origin, dest, ruta, distance_group)
                VALUES
                    (:origin, :dest, :ruta, :distance_group)
                ON CONFLICT (origin, dest) DO NOTHING
            """), row.to_dict())


def _resolve_keys(fact: pd.DataFrame, engine) -> pd.DataFrame:
    """
    Sustituye los códigos naturales (_carrier_code, _origin, _dest,
    cancellation_code) por las surrogate keys de las dimensiones.
    """
    logger.info("  Resolviendo surrogate keys...")

    aerolineas = pd.read_sql(
        "SELECT aerolinea_key, carrier_code FROM airline_dwh.dim_aerolinea",
        engine,
    )
    orig_keys = pd.read_sql(
        "SELECT origen_key, origin FROM airline_dwh.dim_aeropuerto_origen",
        engine,
    )
    dest_keys = pd.read_sql(
        "SELECT destino_key, dest FROM airline_dwh.dim_aeropuerto_destino",
        engine,
    )
    ruta_keys = pd.read_sql(
        "SELECT ruta_key, origin, dest FROM airline_dwh.dim_ruta",
        engine,
    )
    cancel_keys = pd.read_sql(
        "SELECT cancelacion_key, cancellation_code FROM airline_dwh.dim_cancelacion",
        engine,
    )

    fact = fact.merge(aerolineas, left_on="_carrier_code",  right_on="carrier_code",  how="left")
    fact = fact.merge(orig_keys,  left_on="_origin",        right_on="origin",        how="left")
    fact = fact.merge(dest_keys,  left_on="_dest",          right_on="dest",          how="left")
    fact = fact.merge(
        ruta_keys,
        left_on=["_origin", "_dest"],
        right_on=["origin", "dest"],
        how="left",
    )
    # cancellation_code puede ser NULL (vuelos no cancelados)
    fact = fact.merge(cancel_keys, on="cancellation_code", how="left")

    fact = fact.rename(columns={"cancellation_code": "_cancel_code"})

    return fact[[
        "fecha_key", "aerolinea_key", "origen_key", "destino_key",
        "ruta_key", "cancelacion_key", "flight_number",
        "crs_dep_time", "dep_time", "dep_delay", "dep_delay_minutes",
        "dep_del15", "dep_time_blk",
        "crs_arr_time", "arr_time", "arr_delay", "arr_delay_minutes",
        "arr_del15",
        "taxi_out", "taxi_in", "wheels_off", "wheels_on",
        "crs_elapsed_time", "actual_elapsed_time", "air_time",
        "cancelled_flag", "diverted_flag",
        "flights", "distance", "distance_group",
        "carrier_delay", "weather_delay", "nas_delay",
        "security_delay", "late_aircraft_delay",
    ]]


# ============================================================
# Load
# ============================================================

def load(transformed: dict, engine, chunksize: int = 5000) -> None:
    """
    Carga todas las tablas en orden:
      1. dim_aeropuerto_origen  (upsert)
      2. dim_aeropuerto_destino (upsert)
      3. dim_ruta               (upsert)
      4. fact_vuelos            (append por chunks)
    """
    logger.info("Cargando dimensiones variables...")
    _upsert_aeropuertos_origen(transformed["aeropuertos_origen"], engine)
    logger.info("  dim_aeropuerto_origen: OK")

    _upsert_aeropuertos_destino(transformed["aeropuertos_destino"], engine)
    logger.info("  dim_aeropuerto_destino: OK")

    _upsert_rutas(transformed["rutas"], engine)
    logger.info("  dim_ruta: OK")

    logger.info("Resolviendo keys y cargando fact_vuelos...")
    fact_ready = _resolve_keys(transformed["fact"], engine)

    total = len(fact_ready)
    loaded = 0
    for i in range(0, total, chunksize):
        chunk = fact_ready.iloc[i: i + chunksize]
        chunk.to_sql(
            name="fact_vuelos",
            schema="airline_dwh",
            con=engine,
            if_exists="append",
            index=False,
            method="multi",
        )
        loaded += len(chunk)
        logger.info("  Cargadas %s / %s filas", f"{loaded:,}", f"{total:,}")

    logger.info("fact_vuelos: %s filas cargadas", f"{total:,}")


# ============================================================
# Validate
# ============================================================

def validate(source_count: int, engine) -> None:
    """
    Compara el total de filas del CSV fuente contra lo que
    quedó en fact_vuelos. Verifica integridad referencial básica.
    """
    logger.info("Validando carga...")

    with engine.connect() as conn:
        db_count = conn.execute(
            text("SELECT COUNT(*) FROM airline_dwh.fact_vuelos")
        ).scalar()

        orphan_aerolinea = conn.execute(text("""
            SELECT COUNT(*) FROM airline_dwh.fact_vuelos
            WHERE aerolinea_key IS NULL
        """)).scalar()

        orphan_origen = conn.execute(text("""
            SELECT COUNT(*) FROM airline_dwh.fact_vuelos
            WHERE origen_key IS NULL
        """)).scalar()

        orphan_destino = conn.execute(text("""
            SELECT COUNT(*) FROM airline_dwh.fact_vuelos
            WHERE destino_key IS NULL
        """)).scalar()

        orphan_fecha = conn.execute(text("""
            SELECT COUNT(*) FROM airline_dwh.fact_vuelos f
            LEFT JOIN airline_dwh.dim_fecha d USING (fecha_key)
            WHERE d.fecha_key IS NULL
        """)).scalar()

    logger.info("  Filas en CSV fuente  : %s", f"{source_count:,}")
    logger.info("  Filas en fact_vuelos : %s", f"{db_count:,}")

    errors = []
    if orphan_aerolinea > 0:
        errors.append(f"aerolinea_key NULL: {orphan_aerolinea}")
    if orphan_origen > 0:
        errors.append(f"origen_key NULL: {orphan_origen}")
    if orphan_destino > 0:
        errors.append(f"destino_key NULL: {orphan_destino}")
    if orphan_fecha > 0:
        errors.append(f"fecha_key sin match en dim_fecha: {orphan_fecha}")

    if errors:
        for e in errors:
            logger.error("  FALLO validación: %s", e)
        sys.exit(1)
    else:
        logger.info("  Validación OK — sin orphans ni claves nulas")


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="ETL — Airline Delay Analysis")
    parser.add_argument("--host",     required=True,  help="Aurora host")
    parser.add_argument("--port",     default=5432,   type=int)
    parser.add_argument("--database", required=True,  help="Nombre de la base de datos")
    parser.add_argument("--user",     default="postgres")
    parser.add_argument("--password", required=True,  help="Password de Aurora")
    parser.add_argument(
        "--files", nargs="+", required=True,
        help="Rutas a los CSVs mensuales (p.ej. datasets/raw/flights_2026_01.csv)",
    )
    parser.add_argument("--chunksize", default=5000, type=int)
    args = parser.parse_args()

    # Conexión
    url = (
        f"postgresql+psycopg2://{args.user}:{args.password}"
        f"@{args.host}:{args.port}/{args.database}"
    )
    engine = create_engine(url, pool_pre_ping=True)
    logger.info("Conexión a Aurora establecida")

    total_source = 0

    for filepath in args.files:
        if not Path(filepath).exists():
            logger.error("Archivo no encontrado: %s", filepath)
            sys.exit(1)

        logger.info("=" * 55)
        logger.info("Procesando: %s", filepath)
        logger.info("=" * 55)

        raw        = extract(filepath)
        total_source += len(raw)
        transformed = transform(raw)
        load(transformed, engine, chunksize=args.chunksize)

    validate(total_source, engine)
    logger.info("ETL completado exitosamente.")


if __name__ == "__main__":
    main()
