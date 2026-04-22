# Guia operativa SuperAdmin Multi-BD

## Objetivo
Consolidar dos bases SQLite con la misma estructura para analizar y exportar resultados desde un solo panel.

## Ruta de almacenamiento
- Bases activas: `data/multi_db_sources/current/`
- Respaldos historicos: `data/multi_db_sources/archive/`
- Registro de fuentes: `data/multi_db_sources/registry.json`

## Flujo recomendado (diario)
1. Abrir la opcion `SuperAdmin Multi-BD`.
2. En `Registrar o actualizar una base fuente`, subir cada archivo `.db` con su alias estable.
   - Ejemplos de alias: `norte`, `sur`.
   - El alias debe mantenerse en el tiempo para conservar trazabilidad.
3. Seleccionar `Fuente A` y `Fuente B`.
4. Presionar `Preparar consolidado`.
5. Aplicar filtros por origen, marca y anio.
6. Exportar en CSV o Excel.

## Politica de reemplazo y respaldo
- Si subes una BD con un alias existente, la activa se reemplaza.
- Antes de reemplazar, se crea automaticamente un respaldo en `archive/`.
- El sistema mantiene por defecto los ultimos 15 respaldos por alias.

## Limpieza de respaldos
Desde la seccion `Mantenimiento de respaldos`:
1. Elegir la fuente por alias.
2. Definir cuantos respaldos conservar.
3. Ejecutar `Limpiar respaldos antiguos`.

## Buenas practicas
- No usar alias distintos para la misma sucursal.
- Trabajar con copias estables de Drive (evitar archivos en sincronizacion activa).
- Antes de exportar reportes finales, preparar consolidado nuevamente para refrescar datos.
