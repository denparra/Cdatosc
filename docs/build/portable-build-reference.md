# Build portable ejecutable (PyInstaller)

> **Última actualización: 2026-02-24**
> Fix crítico: el ejecutable ahora funciona en cualquier PC sin Python instalado.

---

## Documento normativo asociado

La definicion contractual vigente del comportamiento de runtime se mantiene en:

- `docs/governance/portable-runtime-source-of-truth.md`

Este archivo es una guia operativa de build/distribucion.

---

## Objetivo

Generar un ejecutable portable (`dist/MiAppStreamlit.exe`) que:

- Funcione en cualquier PC con Windows 64-bit, **sin necesitar Python instalado**.
- Use una base de datos local en `data/datos_consignacion.db` junto al `.exe`.
  - Si `data/` y la DB ya existen → las reutiliza sin modificarlas.
  - Si no existen → las crea automáticamente al primer arranque.
- Incluya `docs/marcas.json` dentro del bundle (requerido para normalización y exportación de contactos).

---

## Archivos involucrados

| Archivo | Rol |
|---|---|
| `run.py` | Punto de entrada del ejecutable. Lanza Streamlit. |
| `MiAppStreamlit.spec` | Configuración PyInstaller (onefile). |
| `src/app.py` | Aplicación Streamlit. Contiene lógica de rutas y DB. |
| `docs/marcas.json` | Lista de marcas para parseo y exportación de contactos. |

---

## Historial de cambios

### Fix: ejecutable portable cross-PC (2026-02-24)

**Problema raíz 1 (subprocess)**: `run.py` llamaba `streamlit` como comando del sistema
operativo mediante `subprocess.run(["streamlit", "run", ...])`. En la PC de desarrollo
esto funciona porque Streamlit está instalado en el entorno Python. En cualquier otra PC
sin Python, el comando no existe y el ejecutable falla silenciosamente.

**Fix 1**: Se reemplazó el `subprocess` por importación directa de la CLI de Streamlit
cuando el proceso corre como ejecutable congelado (`sys.frozen`).

**Problema raíz 2 (developmentMode)**: En el bundle PyInstaller, `__file__` de
`streamlit/config.py` apunta a una ruta dentro de `_MEIPASS` que **no contiene
`site-packages`**. Streamlit detecta esto e infiere que está corriendo desde el código
fuente (modo desarrollo), fijando `global.developmentMode = True`. Esto produce dos
consecuencias críticas:

1. `_check_conflicts()` dispara `AssertionError: server.port does not work when
   global.developmentMode is true` si se pasa `--server.port` como argumento.
2. Streamlit intenta conectarse a un webpack dev server (`localhost:3000`) en lugar
   de servir sus assets estáticos empaquetados → la app queda sin frontend.

**Fix 2**: Se establece `STREAMLIT_GLOBAL_DEVELOPMENT_MODE=false` como variable de
entorno **antes** de que `streamlit.config` se inicialice, forzando modo producción.

**Problema raíz 3 (navegador)**: Con `--server.headless=true`, Streamlit no abre el
navegador automáticamente. Con `console=False`, el usuario no ve ninguna señal visible
de que la app está corriendo → parece que "no funciona".

**Fix 3**: Se lanza un hilo daemon que abre `http://localhost:8501` tras 3 segundos
de espera para dar tiempo a que el servidor arranque.

**Solución completa aplicada en `run.py`**:

```python
if getattr(sys, "frozen", False):
    # Fix 2: forzar modo producción en el bundle
    os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"

    # Fix 3: abrir navegador automáticamente
    threading.Thread(target=_open_browser, args=(8501,), daemon=True).start()

    # Fix 1: usar CLI de Streamlit directamente (no subprocess)
    sys.argv = [
        "streamlit", "run", script_path,
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        # NOTA: no pasar --server.port (usar default 8501) para evitar conflicto
        #       con developmentMode incluso si el override de env falla
    ]
    from streamlit.web import cli as stcli
    stcli.main()
```

**Por qué funciona**: `collect_all('streamlit')` empaqueta la librería completa.
Al importar `stcli` directamente se usa esa copia empaquetada. El env var fuerza
`developmentMode=False` antes de que config.py se inicialice, permitiendo que
Streamlit sirva sus assets estáticos y arranque correctamente.

**Cambios en `MiAppStreamlit.spec`** — excludes ampliados:

Se agregaron exclusiones para paquetes presentes en el entorno de desarrollo que
no son necesarios en la app, reduciendo el tamaño del bundle y evitando conflictos:

```python
excludes=[
    # Qt bindings (conflictos de hooks)
    'PyQt6', 'PySide6', 'PyQt5', 'PySide2', 'shiboken6',
    # Paquetes del entorno dev no usados por la app
    'selenium', 'playwright', 'pygame', 'pytesseract',
    'Eel', 'bottle', 'GPUtil', 'screeninfo',
    'gitpython', 'gitdb', 'smmap',
    'auto_py_to_exe',
],
```

`shiboken6` se agregó al exclude porque se colaba en el bundle a pesar de que
`PySide6` ya estaba excluido (era arrastrado por otra dependencia del entorno).

**Resultado**: `dist/MiAppStreamlit.exe` — 124 MB, un solo archivo.

---

### Build inicial portable + fix exportación de marca (sesión anterior)

**Cambios en `src/app.py`**:

- `get_runtime_base_dir()` — resuelve la carpeta base de datos en runtime:
  - Prioridad 1: variable de entorno `DATOS_CONSIGNACION_HOME`.
  - Prioridad 2: si `sys.frozen` → carpeta del `.exe`.
  - Prioridad 3: raíz del proyecto (modo dev).
- `get_connection()` — usa `os.makedirs(db_dir, exist_ok=True)` para crear `data/`
  solo si no existe.
- `load_brands_list()` — busca `marcas.json` en múltiples rutas candidatas:
  1. `resource_path("docs/marcas.json")` → dentro del bundle (`sys._MEIPASS`).
  2. `get_runtime_base_dir()/docs/marcas.json` → junto al exe.
  3. `docs/marcas.json` relativo al CWD → modo dev.
- `prepare_export_dataframe()` — fallback de marca: si el parser devuelve `Unknown`,
  usa `row['marca']` o `row['link_marca']`.
- `fetch_contacts_for_link()` — hace `JOIN links_contactos` y devuelve `marca`
  para exportación por link.

**Cambios en `run.py` (sesión anterior)**:

- Seteaba `DATOS_CONSIGNACION_HOME` al directorio del ejecutable.
- Ejecutaba Streamlit con `cwd` en esa carpeta.

---

## Cómo funciona `marcas.json` en el bundle

El spec incluye:
```python
datas = [('src', 'src'), ('docs/marcas.json', 'docs')]
```

Al ejecutar el `.exe`, PyInstaller extrae los archivos a una carpeta temporal
`sys._MEIPASS`. El `marcas.json` queda en `_MEIPASS/docs/marcas.json`.

`load_brands_list()` lo encuentra a través de `resource_path("docs/marcas.json")`,
que resuelve exactamente esa ruta. **No es necesario distribuir `marcas.json`
por separado** — ya viene dentro del ejecutable.

---

## Comando de build (onefile)

```bash
# Limpieza previa recomendada
rm -rf dist build

# Build
pyinstaller MiAppStreamlit.spec --noconfirm --clean
```

Artefacto generado: `dist/MiAppStreamlit.exe`

---

## Distribución

Solo hay que copiar **un archivo**:

```
MiAppStreamlit.exe
```

No requiere:
- Python instalado.
- Streamlit instalado.
- `marcas.json` por separado (viene dentro del exe).

Al primer arranque crea automáticamente `data/datos_consignacion.db` en la misma
carpeta donde esté el `.exe`. Si ya existe esa carpeta/archivo, los reutiliza.

Para distribuir con una DB pre-cargada:
```
MiAppStreamlit.exe
data/
  datos_consignacion.db   ← copia aquí la DB antes de entregar
```

---

## Verificación recomendada post-build

1. Copiar `dist/MiAppStreamlit.exe` a una carpeta limpia (sin nada más).
2. Ejecutar una vez:
   - Debe crear `data/` y `data/datos_consignacion.db` automáticamente.
   - La app debe abrir en el navegador.
3. Cerrar y volver a abrir:
   - Debe conservar los datos creados (login funcional con `admin/admin`).
4. Verificar exportación:
   - `Ver Contactos & Exportar` → columna `Marca` debe venir poblada.
5. Repetir pasos 1-4 en una PC sin Python instalado.

---

## Troubleshooting

### El exe no abre en otra PC

- Verificar que la PC es Windows 64-bit.
- Si aparece error de DLL (ej. `MSVCP140.dll not found`): instalar
  [Visual C++ Redistributable 2015-2022 x64](https://aka.ms/vs/17/release/vc_redist.x64.exe).
- Si el exe abre y cierra inmediatamente: correr desde terminal `cmd` para ver el error.

### Marca aparece como "Unknown" en exportación

1. Confirmar que se usó `MiAppStreamlit.spec` (tiene `('docs/marcas.json', 'docs')`).
2. Hacer rebuild limpio: `rm -rf dist build && pyinstaller MiAppStreamlit.spec --noconfirm --clean`.

### La DB no se crea

- Verificar que el usuario tiene permisos de escritura en la carpeta del exe.
- Mover el exe a una carpeta sin restricciones (ej. `C:\Users\<usuario>\Desktop\App\`).

### Forzar ruta personalizada de datos

```bash
set DATOS_CONSIGNACION_HOME=C:\ruta\personalizada
MiAppStreamlit.exe
```
