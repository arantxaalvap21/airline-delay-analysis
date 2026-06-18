-- ============================================================
-- Proyecto: Airline Delay Analysis
-- Archivo: 04_dim_cancelacion_populate.sql
-- Descripción: Pobla dim_cancelacion con los 4 códigos
--              oficiales del BTS + una fila para vuelos
--              no cancelados (NULL).
--
-- Distribución en enero 2026:
--   B (Weather)  → 22,463 vuelos  (87.6 % de cancelaciones)
--   A (Carrier)  →  2,246 vuelos  ( 8.8 %)
--   C (NAS)      →    879 vuelos  ( 3.4 %)
--   D (Security) →     47 vuelos  ( 0.2 %)
--
-- Ejecutar DESPUÉS de 01_schema_ddl.sql y ANTES del ETL.
-- ============================================================

SET search_path TO airline_dwh;

INSERT INTO dim_cancelacion (
    cancellation_code,
    cancellation_reason
)
VALUES
    ('A', 'Carrier — mechanical, crew, or operational issue'),
    ('B', 'Weather — adverse meteorological conditions'),
    ('C', 'NAS — National Airspace System / ATC / airport operations'),
    ('D', 'Security — evacuation, threat, or TSA-related delay'),
    (NULL, 'Not cancelled');

-- ============================================================
-- VERIFICACIÓN
-- SELECT * FROM airline_dwh.dim_cancelacion
-- ORDER BY cancellation_code NULLS LAST;
-- Esperado: 5 filas (A, B, C, D, NULL)
-- ============================================================
