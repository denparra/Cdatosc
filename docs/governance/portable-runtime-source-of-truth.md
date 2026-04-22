# Fuente de verdad: runtime portable y build ejecutable

Estado: vigente
Fecha: 2026-04-21
Alcance: comportamiento del `.exe` respecto a datos locales y catalogo de marcas.

## Objetivo contractual

Definir de forma auditable el comportamiento esperado al ejecutar `MiAppStreamlit.exe`:

1. Si `data/` no existe junto al ejecutable, se crea automaticamente.
2. Si `data/` ya existe, se reutiliza sin regenerarla.
3. El ejecutable incluye `docs/marcas.json` para que la exportacion con `Marca` funcione sin archivos externos adicionales.

## Evidencia tecnica (codigo)

- Base runtime del ejecutable definida por `DATOS_CONSIGNACION_HOME` en `run.py:32`.
- En modo congelado (`sys.frozen`), la base se fija junto al `.exe` en `run.py:27`.
- Ruta de DB en app construida como `<base>/data/datos_consignacion.db` en `src/app.py:961`.
- Creacion idempotente de carpeta `data` con `os.makedirs(..., exist_ok=True)` en `src/app.py:967`.
- Conexion SQLite sobre `db_filename` (crea archivo si no existe, reutiliza si existe) en `src/app.py:968`.
- Inclusión de `docs/marcas.json` en el bundle PyInstaller en `MiAppStreamlit.spec:4`.
- Carga de marcas desde bundle (`resource_path`) en `src/app.py:1840`.

## Evidencia tecnica (packaging)

- Punto de entrada de build: `run.py` desde `MiAppStreamlit.spec:12`.
- Build oficial onefile: `pyinstaller MiAppStreamlit.spec --noconfirm --clean`.
- Artefacto esperado: `dist/MiAppStreamlit.exe`.

## Criterios de aceptacion

- CA-01: ejecutar el `.exe` en carpeta limpia crea `data/datos_consignacion.db`.
- CA-02: ejecutar nuevamente en la misma carpeta conserva y reutiliza la DB existente.
- CA-03: exportaciones que dependen de marca no fallan por ausencia de `marcas.json` externo.

## Huella de formalizacion

ID de plan: `PLAN-PORTABLE-SOT-2026-04-21`

Registro de acciones aplicadas en esta formalizacion:

1. Reorden de documentacion por dominios (`build`, `governance`, `operations`, `plans`, `assets`, `archive`).
2. Publicacion de este documento como contrato tecnico vigente.
3. Enlace de este contrato desde `docs/README.md`.

## Matriz de verificacion manual

1. Copiar `dist/MiAppStreamlit.exe` a carpeta vacia.
2. Ejecutar una vez y validar creacion de `data/` y `data/datos_consignacion.db`.
3. Cerrar app, volver a abrir y verificar persistencia de datos.
4. Probar exportacion desde `Ver Contactos & Exportar` y validar columna `Marca` poblada cuando aplica.

## Referencias

- Build detallado: `docs/build/portable-build-reference.md`
- Catalogo de marcas: `docs/marcas.json`
