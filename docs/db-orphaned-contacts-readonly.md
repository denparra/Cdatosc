# Diagnostico DB (READ-ONLY): contactos "ya existe" pero no visible

## Resumen del problema e hipotesis
Al insertar un contacto, la app devuelve "El link del auto ya existe...". Sin embargo, el registro no aparece en la UI/listado.
Hipotesis iniciales: huerfanos por borrado de links generales y/o restricciones UNIQUE que detectan duplicado no visible.

## Verificacion segura
- DB inspeccionada: `data/datos_consignacion.db`
- Tamano observado: 86,147,072 bytes
- Modo de consulta: solo lectura (`file:...?...mode=ro`)
- No se hicieron escrituras ni cambios de esquema/datos

## Esquema encontrado (tablas relevantes)
- `links_contactos` (equivale a links generales)
  - columnas: `id`, `link_general`, `fecha_creacion`, `marca`, `descripcion`, `user_id`
  - indices explicitos: ninguno
- `contactos`
  - columnas: `id`, `link_auto`, `telefono`, `nombre`, `auto`, `precio`, `descripcion`, `id_link`
  - FK declarada: `id_link -> links_contactos(id)`
  - indice unico: `sqlite_autoindex_contactos_1` sobre `link_auto`
- `contactos_restringidos`
  - PK/indice unico: `telefono_normalizado`
- `clientes_interesados` (no es tabla principal de conflicto de insercion en contactos)

### Estado de integridad referencial
- `PRAGMA foreign_keys;` = `0` (desactivado)
- Consecuencia: SQLite no esta forzando FK en runtime.

## Restricciones UNIQUE relevantes
- `contactos.link_auto` es UNIQUE (causa directa del `sqlite3.IntegrityError` capturado por la app).
- No hay UNIQUE en `contactos.telefono`.
- No existen columnas `email` o `rut` en `contactos` para conflicto UNIQUE directo.

## Hallazgos de datos

### 1) Posibles duplicados (top 20)
#### 1.1 Por telefono normalizado (ultimos 9 digitos)
Top ejemplos:
- `931028901` -> 5
- `994937449` -> 5
- `983174868` -> 4
- `984720816` -> 4
- `985251263` -> 4

#### 1.2 Por link_auto
- Duplicados exactos (`GROUP BY link_auto HAVING COUNT>1`): 0 (esperable por UNIQUE)
- Duplicados semanticos (normalizando `lower/trim` y slash final): 1 caso
  - `https://www.chileautos.cl/vehiculos/detalles/2017-honda-city/CL-AD-18027473/`
  - `https://www.chileautos.cl/vehiculos/detalles/2017-honda-city/CL-AD-18027473`

### 2) Contactos huerfanos
Conteos:
- `total_contactos`: 7455
- Huerfanos "aparentes" por join directo `c.id_link = l.id`: 7455
- Causa detectada: `id_link` almacenado como BLOB (8 bytes little-endian), no INTEGER.
- Al decodificar BLOB->id y comparar contra `links_contactos.id`:
  - Asociables a links existentes: 7120
  - Huerfanos reales: 335

IDs padre faltantes y conteo:
- `1` -> 217
- `17` -> 108
- `38` -> 10

### 3) Contactos ocultos por flags/filtros UI
- No existen columnas de borrado/archivo (`deleted_at`, `is_deleted`, `activo`, etc.) en `contactos`.
- Si existe ocultamiento por logica:
  1. `fetch_contacts_for_link` usa `WHERE id_link = ?` (con `?` entero del link seleccionado).
     - Como `id_link` esta en BLOB, el match directo da 0 en la practica.
  2. Adicionalmente excluye restringidos por defecto:
     - `AND NOT EXISTS (...) contactos_restringidos`
     - contactos potencialmente filtrados por esta regla: 481.

## Conclusion (causa raiz mas probable)
Causa raiz principal:
1. Inconsistencia de tipo en `contactos.id_link` (BLOB en vez de INTEGER), que rompe los filtros por link en UI (`id_link = ?`) y hace que contactos existentes no se vean.
2. `link_auto` UNIQUE global sigue activa y correcta; por eso al reintentar insertar el mismo aviso devuelve "ya existe".
3. Caso secundario real: 335 huerfanos por links historicos eliminados (`id` 1,17,38).

## Plan recomendado (NO ejecutado)

### A) Correccion de datos (SQL, transaccional)
1. Respaldar DB.
2. Migrar `contactos.id_link` a INTEGER real:
   - crear tabla nueva `contactos_new` con mismo esquema;
   - insertar convirtiendo `id_link` BLOB little-endian a entero;
   - validar conteos;
   - swap de tablas.
3. Reasociar huerfanos (`id` padre 1,17,38) a links vigentes segun mapeo de negocio (marca/descripcion) o aislarlos para revision.
4. Activar `PRAGMA foreign_keys = ON` en cada conexion de app para prevenir nuevos huerfanos.

### B) Ajustes de app
1. Asegurar casteo a `int(link_id)` antes de insertar contacto (evitar que pandas/numpy llegue como BLOB).
2. Mantener manejo de `IntegrityError`, pero mostrar detalle util (campo UNIQUE que fallo).
3. Revisar si se requiere opcion visible para incluir restringidos en vistas de consulta.

### C) Validacion posterior
- Verificar que `typeof(contactos.id_link)='integer'` para 100%.
- Confirmar que `fetch_contacts_for_link(link_id)` devuelve filas esperadas.
- Reprobar insercion de contacto existente: debe informar duplicado y ahora si poder localizarse en listado.

## Ejecucion aplicada (2026-02-23)
Se ejecuto la mantencion solicitada por el usuario sobre `data/datos_consignacion.db`.

### Respaldo previo
- Backup generado antes de cambios: `data/datos_consignacion.backup_20260223_175346.db`

### Verificaciones previas
Consultas usadas:

```sql
SELECT id, marca, descripcion
FROM links_contactos
WHERE id IN (43,44)
ORDER BY id;

WITH c AS (
  SELECT unicode(CAST(substr(id_link,1,1) AS TEXT)) AS padre
  FROM contactos
)
SELECT padre, COUNT(*) AS total
FROM c
WHERE padre IN (1,17,38)
GROUP BY padre
ORDER BY padre;
```

Resultado previo:
- Link destino `43` existe: RAM
- Link destino `44` existe: JEEP
- Conteo previo por padres faltantes:
  - `1` -> 217
  - `17` -> 108
  - `38` -> 10

### Cambios ejecutados
Se aplico el siguiente mapeo solicitado:
- Padre faltante `1` -> reasignado a link `44`
- Padre faltante `17` -> reasignado a link `43`
- Padre faltante `38` -> eliminados todos sus contactos

Implementacion aplicada (equivalente SQL, considerando que `id_link` esta almacenado como BLOB little-endian):

```sql
UPDATE contactos
SET id_link = CAST(x'2C00000000000000' AS BLOB)
WHERE unicode(CAST(substr(id_link,1,1) AS TEXT)) = 1;

UPDATE contactos
SET id_link = CAST(x'2B00000000000000' AS BLOB)
WHERE unicode(CAST(substr(id_link,1,1) AS TEXT)) = 17;

DELETE FROM contactos
WHERE unicode(CAST(substr(id_link,1,1) AS TEXT)) = 38;
```

Filas afectadas:
- Reasignadas `1 -> 44`: 217
- Reasignadas `17 -> 43`: 108
- Eliminadas `38`: 10

### Validaciones posteriores
Consultas usadas:

```sql
WITH c AS (
  SELECT unicode(CAST(substr(id_link,1,1) AS TEXT)) AS padre
  FROM contactos
)
SELECT padre, COUNT(*) AS total
FROM c
WHERE padre IN (1,17,38,43,44)
GROUP BY padre
ORDER BY padre;

SELECT COUNT(*) AS total_contactos
FROM contactos;
```

Resultado posterior:
- Ya no quedan contactos con padres faltantes `1`, `17`, `38`
- Conteos actuales:
  - `43` -> 114
  - `44` -> 217
- Total de contactos quedo en `7445` (antes `7455`)

### Nota tecnica
- Se mantuvo el formato actual de `id_link` en BLOB para no mezclar estrategias dentro de esta intervencion puntual.
- Queda recomendado ejecutar la migracion estructural pendiente (`id_link` a INTEGER + `PRAGMA foreign_keys = ON`) para evitar nuevas inconsistencias.
