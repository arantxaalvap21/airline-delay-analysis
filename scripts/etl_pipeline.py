# ============================================================
# Proyecto: Airline Delay Analysis
# Archivo: etl_pipeline.py
# Descripción:
#   Pipeline ETL para transformar archivos crudos de BTS
#   en un modelo dimensional tipo estrella en PostgreSQL/Aurora.
#
# Flujo:
#   Extract  -> lectura de CSVs locales
#   Transform -> creación de dimensiones y tabla de hechos
#   Load     -> carga en esquema airline_dwh
#
# Uso:
#   1. Crea un archivo .env con:
#      DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
#   2. Coloca los CSVs en datasets/raw/flights_2026_0X.csv
#   3. python scripts/etl_pipeline.py
# ============================================================

import os
import glob
import logging
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# ------------------------------------------------------------
# Configuración general
# ------------------------------------------------------------

PROJECT_ROOT  = Path(__file__).resolve().parents[1]
RAW_DATA_PATH = PROJECT_ROOT / "datasets" / "raw"
FILE_PATTERN  = "flights_2026_*.csv"
SCHEMA_NAME   = "airline_dwh"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# Mapa de nombre completo por código IATA
AIRLINE_NAMES = {
    "AA": "American Airlines",
    "AS": "Alaska Airlines",
    "B6": "JetBlue Airways",
    "DL": "Delta Air Lines",
    "F9": "Frontier Airlines",
    "G4": "Allegiant Air",
    "MQ": "Envoy Air (American Eagle)",
    "NK": "Spirit Airlines",
    "OH": "PSA Airlines",
    "OO": "SkyWest Airlines",
    "UA": "United Airlines",
    "WN": "Southwest Airlines",
    "YX": "Republic Airways",
}

# Mapa bloque horario → número (para construir fecha_key compuesto)
BLK_NUM = {
    "0001-0559": 1,  "0600-0659": 2,  "0700-0759": 3,
    "0800-0859": 4,  "0900-0959": 5,  "1000-1059": 6,
    "1100-1159": 7,  "1200-1259": 8,  "1300-1359": 9,
    "1400-1459": 10, "1500-1559": 11, "1600-1659": 12,
    "1700-1759": 13, "1800-1859": 14, "1900-1959": 15,
    "2000-2059": 16, "2100-2159": 17, "2200-2259": 18,
    "2300-2359": 19,
}

BLK_BANDA = {
    "0001-0559": "Red-eye",   "0600-0659": "Morning",
    "0700-0759": "Morning",   "0800-0859": "Morning",
    "0900-0959": "Morning",   "1000-1059": "Morning",
    "1100-1159": "Morning",   "1200-1259": "Afternoon",
    "1300-1359": "Afternoon", "1400-1459": "Afternoon",
    "1500-1559": "Afternoon", "1600-1659": "Afternoon",
    "1700-1759": "Afternoon", "1800-1859": "Night",
    "1900-1959": "Night",     "2000-2059": "Night",
    "2100-2159": "Night",     "2200-2259": "Night",
    "2300-2359": "Night",
}

MONTH_NAMES = {
    1: "January", 2: "February", 3: "March",    4: "April",
    5: "May",     6: "June",     7: "July",      8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}

DOW_NAMES = {
    1: "Monday", 2: "Tuesday",  3: "Wednesday", 4: "Thursday",
    5: "Friday", 6: "Saturday", 7: "Sunday",
}


# ------------------------------------------------------------
# Conexión a base de datos
# ------------------------------------------------------------

def get_database_engine():
    """
    Crea la conexión a PostgreSQL/Aurora usando variables de entorno.
    Las credenciales deben estar en un archivo .env local.
    """
    load_dotenv()

    db_host     = os.getenv("DB_HOST")
    db_port     = os.getenv("DB_PORT", "5432")
    db_name     = os.getenv("DB_NAME")
    db_user     = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")

    if not all([db_host, db_name, db_user, db_password]):
        raise ValueError(
            "Faltan variables de entorno. Revisa tu archivo .env: "
            "DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD."
        )

    connection_url = (
        f"postgresql+psycopg2://{db_user}:{db_password}"
        f"@{db_host}:{db_port}/{db_name}"
    )

    return create_engine(connection_url, pool_pre_ping=True)


# ------------------------------------------------------------
# Extract
# ------------------------------------------------------------

def extract_data():
    """
    Lee todos los archivos CSV dentro de datasets/raw/
    que sigan el patrón flights_2026_*.csv.
    """
    files = sorted(glob.glob(str(RAW_DATA_PATH / FILE_PATTERN)))

    if not files:
        raise FileNotFoundError(
            f"No se encontraron archivos en {RAW_DATA_PATH} "
            f"con patrón {FILE_PATTERN}."
        )

    logging.info("Archivos encontrados:")
    for file in files:
        logging.info(f"  - {file}")

    dataframes = []
    for file in files:
        df_temp = pd.read_csv(file, low_memory=False)
        df_temp["source_file"] = Path(file).name
        dataframes.append(df_temp)
        logging.info(f"  Leído: {Path(file).name} — {len(df_temp):,} filas")

    df = pd.concat(dataframes, ignore_index=True)

    logging.info(f"Total filas extraídas: {len(df):,}")
    return df


# ------------------------------------------------------------
# Transform
# ------------------------------------------------------------

def clean_data(df):
    """
    Limpia tipos de datos y crea variables auxiliares necesarias
    para el modelo dimensional.
    """
    df = df.copy()

    # Convertir fecha (formato BTS: '1/1/2026 12:00:00 AM')
    df["FL_DATE"] = pd.to_datetime(df["FL_DATE"], errors="coerce")

    # fecha_key compuesto: YYYYMMDD * 100 + blk_num
    # Permite join directo con dim_fecha que tiene el mismo grano
    df["_blk_num"] = df["DEP_TIME_BLK"].map(BLK_NUM).fillna(1).astype(int)
    df["fecha_key"] = (
        df["FL_DATE"].dt.strftime("%Y%m%d").astype("Int64") * 100
        + df["_blk_num"]
    )

    # Ruta
    df["ruta"] = df["ORIGIN"].astype(str) + "-" + df["DEST"].astype(str)

    # Columnas numéricas
    numeric_columns = [
        "YEAR", "QUARTER", "MONTH", "DAY_OF_MONTH", "DAY_OF_WEEK",
        "OP_CARRIER_AIRLINE_ID", "OP_CARRIER_FL_NUM",
        "ORIGIN_AIRPORT_ID", "DEST_AIRPORT_ID",
        "CRS_DEP_TIME", "DEP_TIME", "DEP_DELAY", "DEP_DELAY_NEW",
        "DEP_DEL15", "TAXI_OUT", "WHEELS_OFF", "WHEELS_ON",
        "TAXI_IN", "CRS_ARR_TIME", "ARR_TIME", "ARR_DELAY",
        "ARR_DELAY_NEW", "ARR_DEL15", "CANCELLED", "DIVERTED",
        "CRS_ELAPSED_TIME", "ACTUAL_ELAPSED_TIME", "AIR_TIME",
        "FLIGHTS", "DISTANCE", "DISTANCE_GROUP",
        "CARRIER_DELAY", "WEATHER_DELAY", "NAS_DELAY",
        "SECURITY_DELAY", "LATE_AIRCRAFT_DELAY",
    ]

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Validación fecha
    missing_dates = df["FL_DATE"].isna().sum()
    if missing_dates > 0:
        logging.warning(f"Registros con FL_DATE inválida: {missing_dates:,}")
        df = df.dropna(subset=["FL_DATE"])

    logging.info(f"Filas después de limpieza: {len(df):,}")
    return df


def build_dim_fecha(df):
    """
    Crea dimensión fecha con todos sus atributos de calendario.
    Grano: una fila por (fecha × bloque horario DEP_TIME_BLK).
    Los campos month_name, day_of_week_name, is_weekend, banda_dia
    son obligatorios en el DDL (NOT NULL) y se calculan aquí.
    """
    dim_fecha = (
        df[[
            "fecha_key", "FL_DATE", "YEAR", "QUARTER", "MONTH",
            "DAY_OF_MONTH", "DAY_OF_WEEK", "DEP_TIME_BLK",
        ]]
        .drop_duplicates(subset=["fecha_key"])
        .copy()
    )

    dim_fecha["month_name"]       = dim_fecha["MONTH"].map(MONTH_NAMES)
    dim_fecha["day_of_week_name"] = dim_fecha["DAY_OF_WEEK"].map(DOW_NAMES)
    dim_fecha["is_weekend"]       = dim_fecha["DAY_OF_WEEK"].isin([6, 7])
    dim_fecha["banda_dia"]        = dim_fecha["DEP_TIME_BLK"].map(BLK_BANDA).fillna("Other")

    dim_fecha = (
        dim_fecha
        .rename(columns={
            "FL_DATE":       "fecha",
            "YEAR":          "year",
            "QUARTER":       "quarter",
            "MONTH":         "month",
            "DAY_OF_MONTH":  "day_of_month",
            "DAY_OF_WEEK":   "day_of_week",
            "DEP_TIME_BLK":  "dep_time_blk",
        })
        .sort_values("fecha_key")
    )

    return dim_fecha


def build_dim_aerolinea(df):
    """
    Crea dimensión aerolínea.
    Grano: una fila por aerolínea operadora.
    airline_name es obligatorio en el DDL (NOT NULL) y se obtiene
    del diccionario AIRLINE_NAMES definido al inicio del script.
    """
    dim_aerolinea = (
        df[["OP_UNIQUE_CARRIER", "OP_CARRIER_AIRLINE_ID", "OP_CARRIER"]]
        .drop_duplicates()
        .rename(columns={
            "OP_UNIQUE_CARRIER":      "carrier_code",
            "OP_CARRIER_AIRLINE_ID":  "dot_id_reporting_airline",
            "OP_CARRIER":             "iata_code_reporting_airline",
        })
        .sort_values("carrier_code")
        .copy()
    )

    dim_aerolinea["airline_name"] = (
        dim_aerolinea["carrier_code"]
        .map(AIRLINE_NAMES)
        .fillna("Unknown Carrier")
    )

    # Reordenar columnas para que coincidan con el DDL
    dim_aerolinea = dim_aerolinea[[
        "carrier_code", "airline_name",
        "dot_id_reporting_airline", "iata_code_reporting_airline",
    ]]

    return dim_aerolinea


def build_dim_aeropuerto_origen(df):
    """
    Crea dimensión aeropuerto origen.
    Grano: una fila por aeropuerto de origen.
    """
    return (
        df[[
            "ORIGIN_AIRPORT_ID", "ORIGIN", "ORIGIN_CITY_NAME",
            "ORIGIN_STATE_ABR", "ORIGIN_STATE_NM",
        ]]
        .drop_duplicates()
        .rename(columns={
            "ORIGIN_AIRPORT_ID": "origin_airport_id",
            "ORIGIN":            "origin",
            "ORIGIN_CITY_NAME":  "origin_city_name",
            "ORIGIN_STATE_ABR":  "origin_state",
            "ORIGIN_STATE_NM":   "origin_state_name",
        })
        .sort_values("origin")
    )


def build_dim_aeropuerto_destino(df):
    """
    Crea dimensión aeropuerto destino.
    Grano: una fila por aeropuerto de destino.
    """
    return (
        df[[
            "DEST_AIRPORT_ID", "DEST", "DEST_CITY_NAME",
            "DEST_STATE_ABR", "DEST_STATE_NM",
        ]]
        .drop_duplicates()
        .rename(columns={
            "DEST_AIRPORT_ID": "dest_airport_id",
            "DEST":            "dest",
            "DEST_CITY_NAME":  "dest_city_name",
            "DEST_STATE_ABR":  "dest_state",
            "DEST_STATE_NM":   "dest_state_name",
        })
        .sort_values("dest")
    )


def build_dim_ruta(df):
    """
    Crea dimensión ruta.
    Grano: una fila por combinación origen-destino.
    """
    return (
        df[["ORIGIN", "DEST", "ruta", "DISTANCE_GROUP"]]
        .drop_duplicates(subset=["ORIGIN", "DEST"])
        .rename(columns={
            "ORIGIN":         "origin",
            "DEST":           "dest",
            "DISTANCE_GROUP": "distance_group",
        })
        .sort_values(["origin", "dest"])
    )


def build_dim_cancelacion():
    """
    Crea dimensión de códigos de cancelación.
    Catálogo fijo del BTS — no depende del CSV.
    Se incluye NULL para vuelos no cancelados.
    """
    return pd.DataFrame({
        "cancellation_code":   ["A",       "B",       "C",                     "D",        None],
        "cancellation_reason": ["Carrier", "Weather", "National Air System",   "Security", "Not cancelled"],
    })


# ------------------------------------------------------------
# Load
# ------------------------------------------------------------

def load_table(engine, df, table_name, if_exists="append"):
    """Carga un DataFrame a PostgreSQL/Aurora."""
    logging.info(f"Cargando {SCHEMA_NAME}.{table_name}: {len(df):,} filas")

    df.to_sql(
        table_name,
        engine,
        schema=SCHEMA_NAME,
        if_exists=if_exists,
        index=False,
        chunksize=10000,
        method="multi",
    )


def truncate_tables(engine):
    """
    Limpia todas las tablas antes de cargar.
    Garantiza idempotencia: el ETL se puede re-ejecutar sin duplicar datos.
    """
    logging.info("Limpiando tablas del modelo dimensional...")

    with engine.begin() as conn:
        conn.execute(text(f"""
            TRUNCATE TABLE
                {SCHEMA_NAME}.fact_vuelos,
                {SCHEMA_NAME}.dim_fecha,
                {SCHEMA_NAME}.dim_aerolinea,
                {SCHEMA_NAME}.dim_aeropuerto_origen,
                {SCHEMA_NAME}.dim_aeropuerto_destino,
                {SCHEMA_NAME}.dim_ruta,
                {SCHEMA_NAME}.dim_cancelacion
            RESTART IDENTITY CASCADE;
        """))


def read_dimension_keys(engine):
    """Lee las surrogate keys de las dimensiones ya cargadas."""
    dim_fecha = pd.read_sql(
        f"SELECT fecha_key FROM {SCHEMA_NAME}.dim_fecha", engine
    )
    dim_aerolinea = pd.read_sql(
        f"SELECT aerolinea_key, carrier_code FROM {SCHEMA_NAME}.dim_aerolinea", engine
    )
    dim_origen = pd.read_sql(
        f"SELECT origen_key, origin FROM {SCHEMA_NAME}.dim_aeropuerto_origen", engine
    )
    dim_destino = pd.read_sql(
        f"SELECT destino_key, dest FROM {SCHEMA_NAME}.dim_aeropuerto_destino", engine
    )
    dim_ruta = pd.read_sql(
        f"SELECT ruta_key, origin, dest FROM {SCHEMA_NAME}.dim_ruta", engine
    )
    dim_cancelacion = pd.read_sql(
        f"SELECT cancelacion_key, cancellation_code FROM {SCHEMA_NAME}.dim_cancelacion", engine
    )
    return dim_fecha, dim_aerolinea, dim_origen, dim_destino, dim_ruta, dim_cancelacion


def build_fact_vuelos(df, engine):
    """
    Construye la tabla de hechos resolviendo todas las surrogate keys.
    Valida que no queden llaves nulas antes de retornar.
    """
    logging.info("Construyendo tabla de hechos...")

    (
        dim_fecha, dim_aerolinea, dim_origen,
        dim_destino, dim_ruta, dim_cancelacion,
    ) = read_dimension_keys(engine)

    fact = df.copy()

    fact = fact.merge(dim_fecha,      on="fecha_key",                           how="left")
    fact = fact.merge(dim_aerolinea,  left_on="OP_UNIQUE_CARRIER",              right_on="carrier_code",  how="left")
    fact = fact.merge(dim_origen,     left_on="ORIGIN",                         right_on="origin",        how="left")
    fact = fact.merge(dim_destino,    left_on="DEST",                           right_on="dest",          how="left")
    fact = fact.merge(dim_ruta,       left_on=["ORIGIN", "DEST"],               right_on=["origin","dest"],how="left", suffixes=("","_ruta"))
    fact = fact.merge(dim_cancelacion,left_on="CANCELLATION_CODE",              right_on="cancellation_code", how="left")

    fact_vuelos = fact[[
        "fecha_key", "aerolinea_key", "origen_key", "destino_key",
        "ruta_key", "cancelacion_key",
        "OP_CARRIER_FL_NUM",
        "CRS_DEP_TIME", "DEP_TIME", "DEP_DELAY", "DEP_DELAY_NEW",
        "DEP_DEL15", "DEP_TIME_BLK",
        "CRS_ARR_TIME", "ARR_TIME", "ARR_DELAY", "ARR_DELAY_NEW",
        "ARR_DEL15", "ARR_TIME_BLK",
        "TAXI_OUT", "TAXI_IN", "WHEELS_OFF", "WHEELS_ON",
        "CRS_ELAPSED_TIME", "ACTUAL_ELAPSED_TIME", "AIR_TIME",
        "CANCELLED", "DIVERTED",
        "FLIGHTS", "DISTANCE", "DISTANCE_GROUP",
        "CARRIER_DELAY", "WEATHER_DELAY", "NAS_DELAY",
        "SECURITY_DELAY", "LATE_AIRCRAFT_DELAY",
    ]].rename(columns={
        "OP_CARRIER_FL_NUM":   "flight_number",
        "CRS_DEP_TIME":        "crs_dep_time",
        "DEP_TIME":            "dep_time",
        "DEP_DELAY":           "dep_delay",
        "DEP_DELAY_NEW":       "dep_delay_minutes",
        "DEP_DEL15":           "dep_del15",
        "DEP_TIME_BLK":        "dep_time_blk",
        "CRS_ARR_TIME":        "crs_arr_time",
        "ARR_TIME":            "arr_time",
        "ARR_DELAY":           "arr_delay",
        "ARR_DELAY_NEW":       "arr_delay_minutes",
        "ARR_DEL15":           "arr_del15",
        "ARR_TIME_BLK":        "arr_time_blk",
        "TAXI_OUT":            "taxi_out",
        "TAXI_IN":             "taxi_in",
        "WHEELS_OFF":          "wheels_off",
        "WHEELS_ON":           "wheels_on",
        "CRS_ELAPSED_TIME":    "crs_elapsed_time",
        "ACTUAL_ELAPSED_TIME": "actual_elapsed_time",
        "AIR_TIME":            "air_time",
        "CANCELLED":           "cancelled_flag",
        "DIVERTED":            "diverted_flag",
        "FLIGHTS":             "flights",
        "DISTANCE":            "distance",
        "DISTANCE_GROUP":      "distance_group",
        "CARRIER_DELAY":       "carrier_delay",
        "WEATHER_DELAY":       "weather_delay",
        "NAS_DELAY":           "nas_delay",
        "SECURITY_DELAY":      "security_delay",
        "LATE_AIRCRAFT_DELAY": "late_aircraft_delay",
    })

    # Validar llaves críticas antes de cargar
    key_cols = ["fecha_key", "aerolinea_key", "origen_key", "destino_key", "ruta_key"]
    missing  = fact_vuelos[key_cols].isna().sum()
    if missing.sum() > 0:
        logging.warning("Llaves faltantes detectadas:")
        logging.warning(missing[missing > 0].to_string())

    logging.info(f"Filas en fact_vuelos: {len(fact_vuelos):,}")
    return fact_vuelos


# ------------------------------------------------------------
# Validaciones post-carga
# ------------------------------------------------------------

def validate_load(engine, expected_rows):
    """
    Validaciones post-carga:
      1. Conteo de filas por tabla
      2. Integridad referencial: sin surrogate keys NULL en la fact
      3. Sin huérfanos: fecha_key presente en dim_fecha
    """
    logging.info("Ejecutando validaciones post-carga...")

    queries = {
        "fact_vuelos":            f"SELECT COUNT(*) FROM {SCHEMA_NAME}.fact_vuelos",
        "dim_fecha":              f"SELECT COUNT(*) FROM {SCHEMA_NAME}.dim_fecha",
        "dim_aerolinea":          f"SELECT COUNT(*) FROM {SCHEMA_NAME}.dim_aerolinea",
        "dim_aeropuerto_origen":  f"SELECT COUNT(*) FROM {SCHEMA_NAME}.dim_aeropuerto_origen",
        "dim_aeropuerto_destino": f"SELECT COUNT(*) FROM {SCHEMA_NAME}.dim_aeropuerto_destino",
        "dim_ruta":               f"SELECT COUNT(*) FROM {SCHEMA_NAME}.dim_ruta",
        "dim_cancelacion":        f"SELECT COUNT(*) FROM {SCHEMA_NAME}.dim_cancelacion",
    }

    with engine.connect() as conn:
        for table_name, query in queries.items():
            count = conn.execute(text(query)).scalar()
            logging.info(f"  {table_name}: {count:,} filas")

        # Integridad referencial
        orphans = {
            "aerolinea_key NULL":  f"SELECT COUNT(*) FROM {SCHEMA_NAME}.fact_vuelos WHERE aerolinea_key IS NULL",
            "origen_key NULL":     f"SELECT COUNT(*) FROM {SCHEMA_NAME}.fact_vuelos WHERE origen_key IS NULL",
            "destino_key NULL":    f"SELECT COUNT(*) FROM {SCHEMA_NAME}.fact_vuelos WHERE destino_key IS NULL",
            "ruta_key NULL":       f"SELECT COUNT(*) FROM {SCHEMA_NAME}.fact_vuelos WHERE ruta_key IS NULL",
            "fecha sin dim_fecha": f"""
                SELECT COUNT(*) FROM {SCHEMA_NAME}.fact_vuelos f
                LEFT JOIN {SCHEMA_NAME}.dim_fecha d USING (fecha_key)
                WHERE d.fecha_key IS NULL
            """,
        }

        errors = []
        for check, query in orphans.items():
            count = conn.execute(text(query)).scalar()
            if count > 0:
                errors.append(f"{check}: {count:,}")

        fact_count = conn.execute(text(queries["fact_vuelos"])).scalar()

    # Reporte
    if errors:
        for e in errors:
            logging.error(f"  FALLO integridad: {e}")
        sys.exit(1)

    if fact_count != expected_rows:
        raise ValueError(
            f"Conteo incorrecto: fact_vuelos tiene {fact_count:,} filas, "
            f"se esperaban {expected_rows:,}."
        )

    logging.info("  Validación completada correctamente — sin errores")


# ------------------------------------------------------------
# Orquestador
# ------------------------------------------------------------

def main():
    """
    Orquesta el pipeline completo:
    Extract -> Transform -> Load -> Validate
    """
    logging.info("=" * 55)
    logging.info("Iniciando ETL Airline Delay Analysis")
    logging.info("=" * 55)

    engine = get_database_engine()

    # Extract
    df_raw = extract_data()

    # Transform
    df_clean       = clean_data(df_raw)
    dim_fecha      = build_dim_fecha(df_clean)
    dim_aerolinea  = build_dim_aerolinea(df_clean)
    dim_origen     = build_dim_aeropuerto_origen(df_clean)
    dim_destino    = build_dim_aeropuerto_destino(df_clean)
    dim_ruta       = build_dim_ruta(df_clean)
    dim_cancelacion = build_dim_cancelacion()

    # Load
    truncate_tables(engine)
    load_table(engine, dim_fecha,       "dim_fecha")
    load_table(engine, dim_aerolinea,   "dim_aerolinea")
    load_table(engine, dim_origen,      "dim_aeropuerto_origen")
    load_table(engine, dim_destino,     "dim_aeropuerto_destino")
    load_table(engine, dim_ruta,        "dim_ruta")
    load_table(engine, dim_cancelacion, "dim_cancelacion")

    fact_vuelos = build_fact_vuelos(df_clean, engine)
    load_table(engine, fact_vuelos, "fact_vuelos")

    # Validate
    validate_load(engine, expected_rows=len(df_clean))

    logging.info("ETL finalizado correctamente.")


if __name__ == "__main__":
    main()
