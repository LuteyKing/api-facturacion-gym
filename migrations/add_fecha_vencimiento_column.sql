-- Migración: Agregar columna fecha_vencimiento a la tabla clientes
-- Fecha: 2026-03-31
-- Descripción: Permite registrar la fecha de vencimiento de la membresía de cada cliente.

ALTER TABLE clientes ADD COLUMN fecha_vencimiento DATE NULL;
