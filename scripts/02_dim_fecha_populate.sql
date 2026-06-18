-- ============================================================
-- Proyecto: Airline Delay Analysis
-- Archivo: 02_dim_fecha_populate.sql
-- Descripción: Pobla dim_fecha para Q1 2026 (enero–marzo)
--              con todos sus atributos de calendario.
--
-- Estrategia: generate_series produce una fila por fecha;
--   un CROSS JOIN con los 19 bloques horarios del BTS
--   produce una fila por (fecha × bloque), que es el grano
--   real que necesita la fact para resolver queries por hora.
--
-- Ejecutar DESPUÉS de 01_schema_ddl.sql y ANTES del ETL.
-- ============================================================

SET search_path TO airline_dwh;

INSERT INTO dim_fecha (
    fecha_key,
    fecha,
    year,
    quarter,
    month,
    month_name,
    day_of_month,
    day_of_week,
    day_of_week_name,
    is_weekend,
    dep_time_blk,
    banda_dia
)
SELECT
    -- smart key: YYYYMMDD + bloque como sufijo numérico (p.ej. 202601010001)
    -- Usamos solo YYYYMMDD porque el join desde la fact se hace por fecha,
    -- el bloque horario viaja como atributo en la misma dim_fecha.
    -- Para evitar duplicados por bloque, la PK incluye un hash del bloque:
    CAST(TO_CHAR(d.fecha, 'YYYYMMDD') AS INTEGER) * 100
        + bloques.blk_num                          AS fecha_key,
    d.fecha                                        AS fecha,
    EXTRACT(YEAR    FROM d.fecha)::INTEGER         AS year,
    EXTRACT(QUARTER FROM d.fecha)::INTEGER         AS quarter,
    EXTRACT(MONTH   FROM d.fecha)::INTEGER         AS month,
    TO_CHAR(d.fecha, 'Month')                      AS month_name,
    EXTRACT(DAY     FROM d.fecha)::INTEGER         AS day_of_month,
    EXTRACT(ISODOW  FROM d.fecha)::INTEGER         AS day_of_week,   -- 1=Mon … 7=Sun
    TO_CHAR(d.fecha, 'Day')                        AS day_of_week_name,
    EXTRACT(ISODOW  FROM d.fecha) IN (6, 7)        AS is_weekend,
    bloques.blk_label                              AS dep_time_blk,
    bloques.banda                                  AS banda_dia
FROM
    -- todas las fechas de Q1 2026
    generate_series(
        DATE '2026-01-01',
        DATE '2026-03-31',
        INTERVAL '1 day'
    ) AS d(fecha)

    -- los 19 bloques horarios del BTS (DEP_TIME_BLK)
    CROSS JOIN (
        VALUES
            (1,  '0001-0559', 'Red-eye'),
            (2,  '0600-0659', 'Morning'),
            (3,  '0700-0759', 'Morning'),
            (4,  '0800-0859', 'Morning'),
            (5,  '0900-0959', 'Morning'),
            (6,  '1000-1059', 'Morning'),
            (7,  '1100-1159', 'Morning'),
            (8,  '1200-1259', 'Afternoon'),
            (9,  '1300-1359', 'Afternoon'),
            (10, '1400-1459', 'Afternoon'),
            (11, '1500-1559', 'Afternoon'),
            (12, '1600-1659', 'Afternoon'),
            (13, '1700-1759', 'Afternoon'),
            (14, '1800-1859', 'Night'),
            (15, '1900-1959', 'Night'),
            (16, '2000-2059', 'Night'),
            (17, '2100-2159', 'Night'),
            (18, '2200-2259', 'Night'),
            (19, '2300-2359', 'Night')
    ) AS bloques(blk_num, blk_label, banda);

-- ============================================================
-- VERIFICACIÓN
-- SELECT COUNT(*) FROM airline_dwh.dim_fecha;
-- Esperado: 90 fechas × 19 bloques = 1,710 filas
--
-- SELECT fecha_key, fecha, dep_time_blk, banda_dia
-- FROM airline_dwh.dim_fecha
-- WHERE fecha = '2026-01-15'
-- ORDER BY blk_num;
-- ============================================================
