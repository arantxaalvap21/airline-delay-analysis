-- ============================================================
-- Proyecto: Airline Delay Analysis
-- Archivo: 01_schema_ddl.sql
-- Descripción: Creación del modelo dimensional para análisis
--              de retrasos, cancelaciones y desempeño operativo
--              de vuelos comerciales en EE. UU.
-- ============================================================

DROP SCHEMA IF EXISTS airline_dwh CASCADE;
CREATE SCHEMA airline_dwh;

SET search_path TO airline_dwh;

-- ============================================================
-- Dimensión Fecha
-- Grano: una fila por fecha de vuelo
-- ============================================================

CREATE TABLE dim_fecha (
    fecha_key INTEGER PRIMARY KEY,
    fecha DATE NOT NULL,
    year INTEGER NOT NULL,
    quarter INTEGER,
    month INTEGER NOT NULL,
    day_of_month INTEGER,
    day_of_week INTEGER
);

-- ============================================================
-- Dimensión Aerolínea
-- Grano: una fila por aerolínea operadora
-- ============================================================

CREATE TABLE dim_aerolinea (
    aerolinea_key SERIAL PRIMARY KEY,
    carrier_code VARCHAR(10) NOT NULL,
    dot_id_reporting_airline INTEGER,
    iata_code_reporting_airline VARCHAR(10),
    CONSTRAINT uq_dim_aerolinea UNIQUE (carrier_code)
);

-- ============================================================
-- Dimensión Aeropuerto Origen
-- Grano: una fila por aeropuerto de origen
-- ============================================================

CREATE TABLE dim_aeropuerto_origen (
    origen_key SERIAL PRIMARY KEY,
    origin_airport_id INTEGER,
    origin VARCHAR(10) NOT NULL,
    origin_city_name VARCHAR(100),
    origin_state VARCHAR(10),
    origin_state_name VARCHAR(100),
    CONSTRAINT uq_dim_aeropuerto_origen UNIQUE (origin)
);

-- ============================================================
-- Dimensión Aeropuerto Destino
-- Grano: una fila por aeropuerto de destino
-- ============================================================

CREATE TABLE dim_aeropuerto_destino (
    destino_key SERIAL PRIMARY KEY,
    dest_airport_id INTEGER,
    dest VARCHAR(10) NOT NULL,
    dest_city_name VARCHAR(100),
    dest_state VARCHAR(10),
    dest_state_name VARCHAR(100),
    CONSTRAINT uq_dim_aeropuerto_destino UNIQUE (dest)
);

-- ============================================================
-- Dimensión Ruta
-- Grano: una fila por combinación origen-destino
-- ============================================================

CREATE TABLE dim_ruta (
    ruta_key SERIAL PRIMARY KEY,
    origin VARCHAR(10) NOT NULL,
    dest VARCHAR(10) NOT NULL,
    ruta VARCHAR(25) NOT NULL,
    distance_group INTEGER,
    CONSTRAINT uq_dim_ruta UNIQUE (origin, dest)
);

-- ============================================================
-- Dimensión Cancelación
-- Grano: una fila por código de cancelación
-- ============================================================

CREATE TABLE dim_cancelacion (
    cancelacion_key SERIAL PRIMARY KEY,
    cancellation_code VARCHAR(5),
    cancellation_reason VARCHAR(100),
    CONSTRAINT uq_dim_cancelacion UNIQUE (cancellation_code)
);

-- ============================================================
-- Tabla de Hechos: Vuelos
-- Grano: una fila por vuelo programado
-- ============================================================

CREATE TABLE fact_vuelos (
    vuelo_key BIGSERIAL PRIMARY KEY,

    fecha_key INTEGER NOT NULL,
    aerolinea_key INTEGER NOT NULL,
    origen_key INTEGER NOT NULL,
    destino_key INTEGER NOT NULL,
    ruta_key INTEGER NOT NULL,
    cancelacion_key INTEGER,

    flight_number INTEGER,

    crs_dep_time INTEGER,
    dep_time INTEGER,
    dep_delay NUMERIC(10,2),
    dep_delay_minutes NUMERIC(10,2),
    dep_del15 NUMERIC(5,2),
    dep_time_blk VARCHAR(20),

    crs_arr_time INTEGER,
    arr_time INTEGER,
    arr_delay NUMERIC(10,2),
    arr_delay_minutes NUMERIC(10,2),
    arr_del15 NUMERIC(5,2),
    arr_time_blk VARCHAR(20),

    taxi_out NUMERIC(10,2),
    taxi_in NUMERIC(10,2),
    wheels_off INTEGER,
    wheels_on INTEGER,

    crs_elapsed_time NUMERIC(10,2),
    actual_elapsed_time NUMERIC(10,2),
    air_time NUMERIC(10,2),

    cancelled_flag NUMERIC(5,2),
    diverted_flag NUMERIC(5,2),

    flights NUMERIC(10,2),
    distance NUMERIC(10,2),
    distance_group INTEGER,

    carrier_delay NUMERIC(10,2),
    weather_delay NUMERIC(10,2),
    nas_delay NUMERIC(10,2),
    security_delay NUMERIC(10,2),
    late_aircraft_delay NUMERIC(10,2),

    CONSTRAINT fk_fact_fecha
        FOREIGN KEY (fecha_key) REFERENCES dim_fecha(fecha_key),

    CONSTRAINT fk_fact_aerolinea
        FOREIGN KEY (aerolinea_key) REFERENCES dim_aerolinea(aerolinea_key),

    CONSTRAINT fk_fact_origen
        FOREIGN KEY (origen_key) REFERENCES dim_aeropuerto_origen(origen_key),

    CONSTRAINT fk_fact_destino
        FOREIGN KEY (destino_key) REFERENCES dim_aeropuerto_destino(destino_key),

    CONSTRAINT fk_fact_ruta
        FOREIGN KEY (ruta_key) REFERENCES dim_ruta(ruta_key),

    CONSTRAINT fk_fact_cancelacion
        FOREIGN KEY (cancelacion_key) REFERENCES dim_cancelacion(cancelacion_key)
);

-- ============================================================
-- Índices para consultas analíticas
-- ============================================================

CREATE INDEX idx_fact_fecha ON fact_vuelos(fecha_key);
CREATE INDEX idx_fact_aerolinea ON fact_vuelos(aerolinea_key);
CREATE INDEX idx_fact_origen ON fact_vuelos(origen_key);
CREATE INDEX idx_fact_destino ON fact_vuelos(destino_key);
CREATE INDEX idx_fact_ruta ON fact_vuelos(ruta_key);
CREATE INDEX idx_fact_cancelacion ON fact_vuelos(cancelacion_key);
CREATE INDEX idx_fact_arr_delay ON fact_vuelos(arr_delay_minutes);
CREATE INDEX idx_fact_cancelled ON fact_vuelos(cancelled_flag);
