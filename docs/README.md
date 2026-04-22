# Documentacion del proyecto

Este directorio esta ordenado por categoria para mantener trazabilidad y facilitar mantenimiento.

## Fuente de verdad

- Runtime y empaquetado portable: `docs/governance/portable-runtime-source-of-truth.md`
- Plan y huella de reorganizacion documental: `docs/governance/documentation-reorg-plan-2026-04-21.md`
- Referencia operativa de build: `docs/build/portable-build-reference.md`

## Estructura

- `docs/build/`: guias de compilacion y distribucion.
- `docs/governance/`: contratos tecnicos, decisiones y huella de cambios.
- `docs/operations/`: incidentes, diagnosticos y mejoras operativas.
- `docs/plans/`: analisis y planes funcionales/tecnicos pendientes.
- `docs/assets/`: imagenes de referencia de UI.
- `docs/archive/`: material historico o de laboratorio no esencial para operacion diaria.
- `docs/marcas.json`: catalogo de marcas usado por la app/exportacion.

## Regla practica

Si un documento define comportamiento vigente de runtime/build, debe vivir en `docs/governance/` y ser enlazado desde este indice.
