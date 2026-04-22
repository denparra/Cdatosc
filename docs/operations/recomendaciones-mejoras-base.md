# Recomendaciones base para implementar mejoras

## 1) Blindaje de integridad en base de datos
Objetivo: evitar huérfanos e inconsistencias de tipo para que los datos siempre sean visibles y trazables.

- Activar `PRAGMA foreign_keys = ON` en cada conexión SQLite de la app.
- Migrar `contactos.id_link` a `INTEGER` real (eliminar almacenamiento en BLOB) y validar el tipo antes de insertar/actualizar.
- Mantener `UNIQUE` en `contactos.link_auto`, pero normalizar URL antes de guardar (trim, lowercase, quitar slash final y query params).
- Agregar chequeo de salud DB (huérfanos, tipos inválidos, duplicados semánticos) con reporte para admin.

Resultado esperado:
- No más contactos huérfanos por borrado de link padre.
- Menos errores de "ya existe" por variantes de URL.
- Listados consistentes entre BD y UI.

## 2) Flujo de alta y resolución de duplicados en UI
Objetivo: que el usuario entienda y resuelva conflictos sin fricción.

- Validación en vivo al ingresar `link_auto`: si existe, mostrar registro encontrado antes de enviar.
- Reemplazar mensaje genérico por acciones: `Ver existente`, `Editar`, `Reasignar`, `Cancelar`.
- Mostrar contexto del conflicto (ID contacto, marca/link, fecha de creación).
- Incluir un paso opcional de confirmación cuando la acción sea masiva o destructiva.

Resultado esperado:
- Menos confusión operacional.
- Menos intentos repetidos de inserción.
- Resolución guiada del conflicto en la misma pantalla.

## 3) Módulo admin de mantenimiento y trazabilidad
Objetivo: detectar y corregir problemas de datos de forma segura y auditable.

- Crear una vista "Mantenimiento DB" (solo admin) con:
  - detección de huérfanos,
  - preview de cambios (conteo + muestra de filas),
  - reasignación masiva por link,
  - exportación a CSV/Excel.
- Registrar auditoría en una tabla de cambios (`quien`, `cuando`, `accion`, `filas_afectadas`, `detalle`).
- Hacer backup automático antes de operaciones masivas y mostrar ruta del backup al finalizar.

Resultado esperado:
- Operación más segura y reversible.
- Historial claro para soporte y control.
- Menor dependencia de intervención manual directa en SQL.

## Estado de implementacion (2026-02-23)

### 1) Blindaje de integridad en base de datos -> IMPLEMENTADO (parcial alto impacto)
- [x] `PRAGMA foreign_keys = ON` agregado en `get_connection()`.
- [x] Migracion automatica para convertir `contactos.id_link` legacy BLOB a INTEGER (`migrate_contactos_link_id_values`).
- [x] Validacion de `link_id` como entero al insertar contacto (`int(link_id)`).
- [x] Normalizacion de `link_auto` reforzada (scheme/netloc en lowercase, remove trailing slash, remove query/fragment).
- [ ] Health-check admin de huérfanos/duplicados semanticos (pendiente).

### 2) Flujo de alta y resolucion de duplicados UI -> IMPLEMENTADO (parcial)
- [x] Deteccion previa de duplicado por `link_auto` en "Agregar Contactos".
- [x] Mensaje contextual con datos del registro existente (ID, telefono, auto, marca/descripcion del link).
- [x] Bloqueo preventivo de insercion cuando el link ya existe, con mensaje accionable.
- [x] Mensaje de `IntegrityError` mejorado con ID existente cuando aplica.
- [x] Botones explicitos `Ver/Editar/Reasignar/Cancelar` en UI.

### 3) Mantenimiento y trazabilidad -> IMPLEMENTADO (parcial minimo)
- [x] Proteccion al eliminar links con contactos asociados (evita huerfanos por borrado directo).
- [ ] Vista admin "Mantenimiento DB" (pendiente).
- [ ] Tabla de auditoria de cambios (pendiente).

## Registro operativo (que se hizo y como se hizo)

### Archivos modificados
- `src/app.py`
- `docs/operations/recomendaciones-mejoras-base.md`

### Proceso aplicado
1. Se actualizaron funciones de normalizacion/consistencia:
   - `sanitize_vehicle_link(...)`
   - `decode_link_id(...)` (nuevo helper)
2. Se endurecio la conexion DB:
   - `get_connection()` ahora ejecuta `PRAGMA foreign_keys = ON`.
3. Se agrego migracion de datos legacy:
   - `migrate_contactos_link_id_values()` convierte BLOB -> INTEGER en `contactos.id_link`.
   - La migracion se invoca en el bootstrap de app (junto a `create_tables()` y migraciones existentes).
4. Se mejoro la UX de insercion de contactos:
   - nuevo helper `get_contact_by_link_auto(...)`.
   - deteccion y detalle de duplicado antes del submit.
   - insercion bloqueada si el link ya existe.
5. Se protegió eliminacion de links:
   - `delete_link_record(...)` ahora valida si existen contactos asociados y bloquea la eliminacion.

### Verificaciones ejecutadas
- Sintaxis:
  - `python -m compileall src tests`
- Tests relevantes (pasando):
  - `pytest tests/test_sanitize_links.py tests/test_restricted_numbers.py tests/test_search_contacts.py tests/test_update_contact.py`
- Verificacion de datos actual:
  - Consulta ejecutada: `SELECT typeof(id_link), COUNT(*) FROM contactos GROUP BY typeof(id_link);`
  - Resultado: `id_link` quedo en tipo `integer` para todos los registros actuales.

## Ajuste adicional aplicado (2026-02-23)
- Se ajusto el patron de normalizacion de `link_auto` para mantener slash final en rutas (ej. `.../CL-AD-XXXXX/`), alineado con el formato historico de la base.
- Implementacion: `sanitize_vehicle_link(...)` ahora normaliza host/scheme y deja la ruta con slash final para rutas no raiz.
- Se actualizaron pruebas de sanitizacion para reflejar este comportamiento.
- Se elimino el contacto solicitado `id = 7540`.

Validaciones:
- `DELETE FROM contactos WHERE id = 7540;` -> `changes() = 1`
- `SELECT COUNT(*) FROM contactos WHERE id = 7540;` -> `0`
- Tests: `pytest tests/test_sanitize_links.py tests/test_restricted_numbers.py tests/test_search_contacts.py tests/test_update_contact.py` -> OK

## Ajuste adicional aplicado (2026-02-23, Iteracion UX duplicados)
- Se reforzo la resolucion guiada de duplicados en `Agregar Contactos`.
- Implementado en `src/app.py`:
  - Acciones directas ante duplicado: `Ver existente`, `Editar`, `Reasignar`, `Cancelar`.
  - Contexto ampliado del conflicto: incluye `fecha_creacion` del link asociado.
  - Reasignacion segura del contacto existente a link seleccionado con confirmacion explicita.
  - Navegacion a `Editar` con apertura directa del contacto objetivo (sin repetir busqueda manual).
- Helpers nuevos:
  - `get_contact_for_user(contact_id, user)`
  - `reassign_contact_to_link(contact_id, target_link_id, user)`

Validaciones ejecutadas:
- `python -m compileall src/app.py tests/test_update_contact.py`
- `pytest tests/test_update_contact.py tests/test_sanitize_links.py tests/test_restricted_numbers.py tests/test_search_contacts.py`
- Resultado: `8 passed`.

## Ajuste adicional aplicado (2026-02-23, Restricciones con ciclo completo)
- Se agrego gestion de eliminacion de restricciones desde UI (sin SQL manual).
- Implementado en `Contactos Restringidos`:
  - selector de restriccion existente,
  - confirmacion explicita,
  - boton `Eliminar restricción seleccionada`.
- Soporta eliminacion por alcance:
  - `GLOBAL` (telefono),
  - `LINK` (telefono + link_id),
  - `CONTACTO` (contact_id).
- Backend nuevo: `remove_restriction(...)`.

Validaciones ejecutadas:
- `pytest tests/test_restricted_numbers.py tests/test_search_contacts.py tests/test_sanitize_links.py tests/test_update_contact.py`

## Ajuste adicional aplicado (2026-02-23, Consolidacion + UX restricciones)
- Se consolido `src/app.py` removiendo duplicados de funciones core:
  - `fetch_contacts_for_link`,
  - bloque de usuarios (`hash_password`, `create_user`, `authenticate_user`, `delete_user`, `fetch_all_contacts_for_user`, `ensure_default_users`),
  - bootstrap duplicado (`create_tables` y migraciones).
- Resultado: fuente unica de comportamiento, menor riesgo de divergencias y regresiones.

- Se mejoro UX de `Contactos Restringidos`:
  - filtros por alcance (`Todos`, `Global`, `Contacto`, `Link`),
  - buscador por telefono o `ID contacto`,
  - eliminacion de restriccion sobre lista filtrada con confirmacion.

Validaciones ejecutadas:
- `python -m compileall src/app.py tests/test_restricted_numbers.py tests/test_update_contact.py`
- `pytest tests/test_restricted_numbers.py tests/test_search_contacts.py tests/test_sanitize_links.py tests/test_update_contact.py`
- Resultado: `10 passed`.
