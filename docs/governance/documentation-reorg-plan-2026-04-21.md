# Plan formal: reorganizacion de documentacion

ID: `PLAN-DOCS-REORG-2026-04-21`
Estado: completado
Fecha: 2026-04-21

## Objetivo

Mejorar la legibilidad y profesionalidad de la documentacion sin tocar logica funcional de la aplicacion.

## Alcance

- Reorden de archivos de `docs/` por dominio.
- Publicacion de un indice unico de documentacion.
- Definicion de fuente de verdad para runtime portable.

## No alcance

- Cambios de comportamiento en `src/app.py` o `run.py`.
- Cambios de esquema de base de datos.
- Cambios de build spec.

## Plan ejecutado

1. Crear estructura por dominios (`build`, `governance`, `operations`, `plans`, `assets`, `archive`).
2. Mover documentos sueltos de raiz de `docs/` a carpetas correspondientes.
3. Mover material historico/no esencial a `docs/archive/`.
4. Publicar `docs/README.md` como indice central.
5. Publicar contrato tecnico en `docs/governance/portable-runtime-source-of-truth.md`.
6. Referenciar la fuente de verdad desde `README.md` y desde la guia de build.

## Huella (audit trail)

- Documento indice creado: `docs/README.md`.
- Contrato runtime creado: `docs/governance/portable-runtime-source-of-truth.md`.
- Plan de reorganizacion creado: `docs/governance/documentation-reorg-plan-2026-04-21.md`.
- Referencia cruzada agregada en `README.md` y `docs/build/portable-build-reference.md`.

## Criterios de aceptacion

- CA-01: existe indice de documentacion unico (`docs/README.md`).
- CA-02: existe contrato tecnico vigente de runtime portable (`docs/governance/portable-runtime-source-of-truth.md`).
- CA-03: archivos no esenciales de laboratorio quedan fuera de la raiz de `docs/`.
- CA-04: no se modifican rutas funcionales de la app para DB y marcas.
