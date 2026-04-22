# Análisis: Soporte Multi-Base de Datos

**Proyecto**: DATOS_CONSIGNACION
**Módulo afectado**: `src/app.py` → `get_connection()` / `db_filename` / login
**Fecha de análisis**: 2026-02-22
**Estado**: Pendiente de implementación

---

## 1. Situación actual

### Cómo está definida la BD hoy

```python
# src/app.py — línea 686
db_filename = resource_path(os.path.join("data", "datos_consignacion.db"))

def get_connection():
    """Retorna una nueva conexión a la base de datos."""
    os.makedirs(os.path.dirname(db_filename), exist_ok=True)
    conn = sqlite3.connect(db_filename, check_same_thread=False)
    conn.create_function("normalize_phone", 1, normalize_phone)
    return conn
```

**Problemas del diseño actual para el caso multi-ejecutiva**:

| Aspecto | Situación |
|---|---|
| Ruta de BD | Hardcodeada como constante al inicio del módulo |
| Selección de BD | Imposible sin reiniciar la app |
| Autenticación | La tabla `users` vive dentro de la misma BD → credenciales separadas por ejecutiva |
| Acceso administrador externo | No existe mecanismo para entrar a la BD de otra ejecutiva |
| Sesión | `st.session_state["user"]` no tiene noción de "BD activa" |

### Flujo actual (simplificado)

```
App inicia
  → db_filename = data/datos_consignacion.db  ← fijo para siempre
  → create_tables() → migrate_*() → ensure_default_users()
  → usuario hace login → authenticate_user() busca en esa BD
  → toda la operación transcurre en esa BD
```

---

## 2. Requisitos del caso de uso

De la solicitud:

1. **Múltiples BDs** — cada ejecutiva tiene su propio archivo `.db` con el mismo esquema.
2. **Selector de BD** — poder elegir a qué BD conectarse desde la UI.
3. **Acceso con todos los permisos** — entrar a la BD de una ejecutiva con rol `admin` sin necesitar sus credenciales individuales.
4. **Mismo formato** — todas las BDs comparten el esquema actual (mismas tablas).

---

## 3. Opciones de implementación

### Opción A — Selector dinámico con credencial maestra (RECOMENDADA)

**Concepto**: antes o durante el login se elige la BD objetivo. Una contraseña maestra (almacenada de forma segura, no en ninguna BD objetivo) otorga acceso admin a cualquier BD seleccionada.

```
┌─────────────────────────────────────────────────────────┐
│  PANTALLA DE INICIO                                      │
│                                                          │
│  1. Selector de BD:  [Ejecutiva A ▼]                    │
│     (lista de .db encontrados en una carpeta)            │
│                                                          │
│  2. Login:  [usuario] [contraseña]                       │
│             — O —                                        │
│             [contraseña maestra] → acceso admin directo  │
│                                                          │
│  3. [Entrar]                                             │
└─────────────────────────────────────────────────────────┘
```

**Cambios necesarios en el código**:

```python
# 1. db_filename deja de ser constante global
# En su lugar se lee desde session_state:

def get_connection():
    db_path = st.session_state.get("active_db_path", _default_db_path())
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.create_function("normalize_phone", 1, normalize_phone)
    return conn

def _default_db_path() -> str:
    return resource_path(os.path.join("data", "datos_consignacion.db"))

# 2. Función para descubrir BDs disponibles:
def discover_databases(search_path: str) -> list[dict]:
    """Encuentra todos los .db válidos en una carpeta."""
    dbs = []
    for root, _, files in os.walk(search_path):
        for f in files:
            if f.endswith(".db"):
                full = os.path.join(root, f)
                dbs.append({"label": f.replace(".db", ""), "path": full})
    return dbs

# 3. Login ampliado con selector y contraseña maestra:
def authenticate_master(password: str) -> bool:
    """Verifica la contraseña maestra (no almacenada en ninguna BD)."""
    master_hash = st.secrets.get("master_password_hash", "")
    return hashlib.sha256(password.encode()).hexdigest() == master_hash
```

**Ventajas**:
- Cambio mínimo en toda la app (`get_connection()` es el único punto de cambio real)
- La credencial maestra no vive en ninguna BD → no se puede comprometer desde la UI
- Las ejecutivas mantienen su login propio sin afectarse entre sí
- Compatible con el sistema de roles actual

**Desventajas**:
- `st.secrets` o un archivo de config adicional para la contraseña maestra
- Hay que definir dónde buscar los `.db` (carpeta fija, variable de entorno, manual)

---

### Opción B — Ingreso manual de ruta de archivo

**Concepto**: el usuario (admin) escribe o pega la ruta completa del `.db` que quiere abrir.

```python
# En pantalla de login, sección admin:
db_path = st.text_input("Ruta de BD", value=_default_db_path())
if st.button("Conectar"):
    if os.path.exists(db_path) and db_path.endswith(".db"):
        st.session_state["active_db_path"] = db_path
```

**Ventajas**: implementación mínima, sin dependencias nuevas.

**Desventajas**: mala UX (hay que conocer la ruta exacta), propenso a errores de tipeo. No recomendado para uso regular.

---

### Opción C — Archivo de configuración con lista de BDs conocidas

**Concepto**: un archivo `databases.json` junto al ejecutable lista las BDs registradas.

```json
{
  "databases": [
    {"label": "Ejecutiva Ana",  "path": "C:/CODEX/data/ejecutiva_ana.db"},
    {"label": "Ejecutiva María", "path": "C:/CODEX/data/ejecutiva_maria.db"},
    {"label": "BD Principal",   "path": "data/datos_consignacion.db"}
  ]
}
```

```python
def load_database_registry() -> list[dict]:
    registry_path = resource_path("databases.json")
    if not os.path.exists(registry_path):
        return [{"label": "Principal", "path": _default_db_path()}]
    with open(registry_path, "r", encoding="utf-8") as f:
        return json.load(f).get("databases", [])
```

**Ventajas**: lista curada, etiquetas legibles, sin búsqueda por sistema de archivos.

**Desventajas**: hay que mantener `databases.json` actualizado manualmente al agregar ejecutivas. No se auto-descubren BDs nuevas.

---

### Opción D — Multi-tenant en una sola BD (descartada)

Agregar columna `ejecutiva_id` a todas las tablas y particionar lógicamente.

**Por qué no aplica aquí**: cada ejecutiva ya tiene su propio `.db` en producción. Migrar todo a una BD única requeriría fusionar datos existentes, cambiar todas las queries, y rediseñar el modelo de acceso. Esfuerzo desproporcionado y riesgo alto.

---

## 4. Recomendación: Opción A + C combinadas

La implementación más robusta combina **descubrimiento automático** (Opción A) con **lista curada** (Opción C) como fallback o complemento, más **contraseña maestra** para acceso admin:

```
Al iniciar la app:
  1. Lee databases.json si existe → lista de BDs conocidas
  2. Permite "Buscar más..." → explorador de archivos o ingreso de ruta
  3. Selector dropdown en la pantalla de login con las BDs disponibles
  4. Login normal → credenciales propias de la BD elegida
     O Contraseña maestra → acceso admin directo a cualquier BD

Session state resultante:
  st.session_state["active_db_path"] = "/ruta/ejecutiva_x.db"
  st.session_state["user"] = {"role": "admin", "username": "master", ...}
```

---

## 5. Análisis de impacto en el código actual

### Cambios necesarios (mínimos)

| Qué | Dónde | Complejidad |
|---|---|---|
| `db_filename` → dinámico desde session_state | `app.py:686` | Baja |
| `get_connection()` → lee `active_db_path` | `app.py:688` | Baja |
| `create_tables()` / `migrate_*()` → llamar al cambiar de BD | `app.py:785+` | Baja |
| `render_login()` → agregar selector de BD | `app.py:~1935` | Media |
| `authenticate_master()` → nueva función | `app.py` nuevo | Baja |
| `discover_databases()` o `load_database_registry()` | `app.py` nuevo | Baja |
| Sidebar → indicador de BD activa | `app.py:~462` | Baja |
| `databases.json` | raíz del proyecto | Baja |
| `st.secrets` o `.streamlit/secrets.toml` → hash contraseña maestra | `.streamlit/` | Baja |

### Lo que NO cambia

- Todas las funciones de negocio (`fetch_contacts_for_link`, `scrape_vehicle_details`, etc.) — usan `get_connection()` que se actualiza solo en un lugar.
- El sistema de roles y menús — sigue funcionando igual.
- Las migraciones de esquema — se ejecutan al conectarse a cada BD nueva por primera vez.
- Los tests — siguen mockeando `get_connection()` con BD en memoria.

### Riesgo principal

`db_filename` es hoy una **variable de módulo** que se evalúa una sola vez al importar `app.py`. En Streamlit, el módulo se importa una vez por proceso (no por sesión). Si múltiples usuarios corren la app simultáneamente (modo servidor), `st.session_state["active_db_path"]` correctamente aísla cada sesión — esto es un punto a verificar si la app corre en Streamlit Cloud o en red.

Para modo `.exe` en una sola máquina, no hay problema porque hay una sola sesión a la vez.

---

## 6. Almacenamiento seguro de la contraseña maestra

**Nunca** almacenar la contraseña maestra en texto plano ni dentro de ninguna BD.

### Opción recomendada: `.streamlit/secrets.toml`

```toml
# .streamlit/secrets.toml  (NO subir a git)
master_password_hash = "sha256_hash_de_tu_contraseña_maestra"
```

Generar el hash:
```python
import hashlib
print(hashlib.sha256("tu_contraseña_maestra".encode()).hexdigest())
```

En el código:
```python
def authenticate_master(password: str) -> bool:
    stored = st.secrets.get("master_password_hash", "")
    if not stored:
        return False
    return hashlib.sha256(password.encode()).hexdigest() == stored
```

Para el `.exe` (sin `st.secrets`), la alternativa es un archivo `master.key` cifrado junto al ejecutable, o una variable de entorno del sistema operativo.

---

## 7. UX propuesta — pantalla de login ampliada

```
┌──────────────────────────────────────────────────┐
│              CODEX — Datos Consignación           │
│                                                   │
│  Base de datos:                                   │
│  ┌────────────────────────────────┐               │
│  │  Principal (datos_consig...)  ▼│               │
│  └────────────────────────────────┘               │
│  [+ Agregar BD...]                                │
│                                                   │
│  ──────────────────────────────                   │
│                                                   │
│  Usuario: [____________]                          │
│  Contraseña: [____________]                       │
│                                                   │
│  [Entrar]                                         │
│                                                   │
│  ──── o acceso administrador ────                 │
│  Contraseña maestra: [____________]               │
│  [Entrar como Admin]                              │
└──────────────────────────────────────────────────┘
```

Indicador en sidebar (cuando hay BD activa distinta a la principal):
```
🗄️ BD: Ejecutiva Ana
```

---

## 8. Checklist de implementación

```
FASE 1 — Dinámica de BD (sin contraseña maestra aún)
  [ ] Mover db_filename a _default_db_path() como función
  [ ] Actualizar get_connection() para leer active_db_path de session_state
  [ ] Crear load_database_registry() que lee databases.json
  [ ] Agregar selector de BD en render_login() con las BDs del registro
  [ ] Al seleccionar BD: llamar create_tables() + migrate_*() sobre la nueva BD
  [ ] Mostrar BD activa en sidebar si no es la principal
  [ ] Crear databases.json con las BDs de cada ejecutiva
  [ ] Tests: verificar que get_connection() usa la BD de session_state

FASE 2 — Contraseña maestra
  [ ] Crear authenticate_master() que verifica hash en st.secrets
  [ ] Generar hash SHA-256 de la contraseña maestra elegida
  [ ] Agregar hash a .streamlit/secrets.toml (o variable de entorno)
  [ ] Agregar campo "Contraseña maestra" en render_login()
  [ ] Al autenticar con maestra: crear user dict con role="admin"
      y guardarlo en session_state como cualquier otro login
  [ ] Verificar que .streamlit/secrets.toml está en .gitignore

FASE 3 — UX avanzada (opcional)
  [ ] Botón "Agregar BD..." con explorador de archivos (st.file_uploader
      o st.text_input para ruta manual)
  [ ] Guardar BDs adicionales en databases.json automáticamente
  [ ] Historial de BDs usadas recientemente
```

---

## 9. Restricciones del entorno `.exe`

El proyecto compila a `.exe` con PyInstaller. Consideraciones:

| Aspecto | Implicación |
|---|---|
| `st.secrets` en `.exe` | Requiere que `.streamlit/secrets.toml` esté junto al `.exe`, no dentro del bundle |
| `databases.json` | Debe estar junto al `.exe` (no empaquetado), editable por el usuario |
| Rutas de BD | Las BDs de otras ejecutivas deben ser accesibles por red o disco local |
| `resource_path()` | Usar solo para archivos empaquetados (estáticos); las BDs externas usan rutas absolutas directamente |

---

*Análisis generado con Claude Code — 2026-02-22*
