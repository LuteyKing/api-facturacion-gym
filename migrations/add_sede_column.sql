-- ═══════════════════════════════════════════════════════════════
-- Migración: Agregar columna "sede" a facturas, clientes, productos
-- Ejecutar contra la BD PostgreSQL en Render si las tablas ya existen
-- ═══════════════════════════════════════════════════════════════

-- 1. Facturas
ALTER TABLE facturas
    ADD COLUMN IF NOT EXISTS sede VARCHAR(10) DEFAULT 'gym';

CREATE INDEX IF NOT EXISTS ix_facturas_sede ON facturas (sede);

UPDATE facturas SET sede = 'gym' WHERE sede IS NULL;

-- 2. Clientes
ALTER TABLE clientes
    ADD COLUMN IF NOT EXISTS sede VARCHAR(10) DEFAULT 'gym';

CREATE INDEX IF NOT EXISTS ix_clientes_sede ON clientes (sede);

UPDATE clientes SET sede = 'gym' WHERE sede IS NULL;

-- 3. Productos
ALTER TABLE productos
    ADD COLUMN IF NOT EXISTS sede VARCHAR(10) DEFAULT 'gym';

CREATE INDEX IF NOT EXISTS ix_productos_sede ON productos (sede);

UPDATE productos SET sede = 'gym' WHERE sede IS NULL;
