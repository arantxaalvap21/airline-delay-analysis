-- ============================================================
-- Proyecto: Airline Delay Analysis
-- Archivo: 03_dim_aerolinea_populate.sql
-- Descripción: Pobla dim_aerolinea con los 13 carriers
--              presentes en el dataset BTS Q1 2026.
--
-- Fuente de DOT_ID: campo OP_CARRIER_AIRLINE_ID del CSV.
-- airline_name: nombre comercial completo para uso en dashboard.
-- Ejecutar DESPUÉS de 01_schema_ddl.sql y ANTES del ETL.
-- ============================================================

SET search_path TO airline_dwh;

INSERT INTO dim_aerolinea (
    carrier_code,
    airline_name,
    dot_id_reporting_airline,
    iata_code_reporting_airline
)
VALUES
    ('AA', 'American Airlines',           19805, 'AA'),
    ('AS', 'Alaska Airlines',             19930, 'AS'),
    ('B6', 'JetBlue Airways',             20409, 'B6'),
    ('DL', 'Delta Air Lines',             19790, 'DL'),
    ('F9', 'Frontier Airlines',           20436, 'F9'),
    ('G4', 'Allegiant Air',               20368, 'G4'),
    ('MQ', 'Envoy Air (American Eagle)',  20398, 'MQ'),
    ('NK', 'Spirit Airlines',             20416, 'NK'),
    ('OH', 'PSA Airlines',                20397, 'OH'),
    ('OO', 'SkyWest Airlines',            20304, 'OO'),
    ('UA', 'United Airlines',             19977, 'UA'),
    ('WN', 'Southwest Airlines',          19393, 'WN'),
    ('YX', 'Republic Airways',            20452, 'YX');

-- ============================================================
-- VERIFICACIÓN
-- SELECT aerolinea_key, carrier_code, airline_name
-- FROM airline_dwh.dim_aerolinea
-- ORDER BY carrier_code;
-- Esperado: 13 filas
-- ============================================================
