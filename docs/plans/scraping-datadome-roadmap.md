# Guía: Scraping Chileautos y Protección DataDome

**Proyecto**: DATOS_CONSIGNACION
**Módulo afectado**: `src/app.py` → `scrape_vehicle_details()` / `Agregar Contactos`
**Fecha de análisis**: 2026-02-19
**Última actualización**: 2026-02-22
**Tag de referencia**: `v-mejoras-claude-001`

---

## Estado de implementación

| Fase | Descripción | Estado |
|---|---|---|
| Fase 1 — Trigger manual | Botón + caché session_state + detección DataDome | ✅ Implementado |
| Fase 2 — Playwright headless | Fallback con browser real cuando hay 403 | ⏳ Pendiente |
| Fase 3 — Caché cookie DataDome | Cookie válida compartida entre requests | ⏳ Pendiente (depende de Fase 2) |
| Fase 4 — Worker background | Scraping asíncrono en lote | ⏳ Pendiente (decidir por volumen) |

---

## 1. Contexto del problema

La función `scrape_vehicle_details(url)` extrae automáticamente datos de un aviso en Chileautos.cl (nombre del vehículo, precio, teléfono WhatsApp, descripción) cada vez que el usuario pega un link en el campo **"Link del Auto"** de la página **Agregar Contactos**.

### Cómo funcionaba el trigger original (el problema raíz — ya corregido)

```
src/app.py — página "Agregar Contactos" (comportamiento ANTERIOR):

  st.text_input("Link del Auto", key="link_auto")   ← widget fuera del form
         ↓
  raw_link_auto = st.session_state.get("link_auto", "")
         ↓
  if link_auto_value:
      scraped_data = scrape_vehicle_details(link_auto_value)  ← se ejecutaba aquí
```

**Problema**: En Streamlit, cada interacción con cualquier widget relanza el script completo. El scrape se ejecutaba **en cada rerender**, no solo al enviar el formulario. Cuando el usuario escribía una URL carácter a carácter, se disparaban decenas de requests HTTP a Chileautos en segundos.

**Este trigger fue reemplazado por el botón manual en la Fase 1** (ver sección 4).

---

## 2. Capas de protección de Chileautos

Chileautos utiliza **dos sistemas de protección** independientes:

### Capa 1 — CloudFront (CDN/WAF de AWS)
- Bloquea User-Agents obsoletos (Chrome antiguo, bots conocidos)
- Verifica cabeceras HTTP básicas
- **Solución aplicada** (commit `8f8078b`): actualizar a Chrome 132 + cabeceras `sec-fetch-*` + `sec-ch-ua`

### Capa 2 — DataDome (bot protection con ML)
- **Sistema de puntuación de riesgo por IP** (score 0–6553)
- Cada request de Python sin validación JS suma puntos de riesgo
- Al superar el umbral → responde con challenge page (403 + "Please enable JS")
- El score se acumula en tiempo real durante la sesión

#### Respuesta DataDome detectada en producción:
```
Header:  x-datadome: protected
Cookie:  datadome=<token_no_validado>
Body:    {"rt":"c", "s":6522, "host":"geo.captcha-delivery.com"}
```

- `rt: "c"` → tipo "challenge" (requiere JS)
- `s: 6522` → score de riesgo 6522/6553 → IP esencialmente bloqueada
- `host: geo.captcha-delivery.com` → redirección a CAPTCHA

#### Flujo de validación DataDome (browser real vs Python):

```
BROWSER REAL                          PYTHON requests
─────────────────────────────         ────────────────────────────
1. GET /vehiculos/detalles/...        1. GET /vehiculos/detalles/...
2. Recibe HTML + JS de DataDome       2. Recibe HTML + JS de DataDome
3. Ejecuta JS: canvas, WebGL,         3. NO puede ejecutar JS
   timing, resolución, etc.           4. Recibe cookie datadome=<inválida>
4. POST a geo.captcha-delivery.com    5. Envía cookie inválida
5. Recibe cookie datadome=<válida>    6. → 403 Forbidden
6. → 200 OK con contenido real
```

---

## 3. Por qué funcionó y luego dejó de funcionar

El score de riesgo de DataDome es **acumulativo por IP y sesión**:

| Momento | Requests | Score aprox. | Resultado |
|---|---|---|---|
| Primer test (IP limpia) | 1–3 | < 1000 | ✅ 200 OK |
| Durante desarrollo/debug | 10–20 | 1000–4000 | ⚠️ Inestable |
| Después de tests intensivos | 30+ | > 5000 | ❌ 403 permanente |
| IP reseteada (router/VPN) | 1 | 0 | ✅ 200 OK |

**La causa directa**: el trigger de Streamlit fuera del formulario genera ráfagas de requests durante las pruebas (cada tecla = 1 request), acelerando el score exponencialmente.

---

## 4. Soluciones por orden de prioridad

---

### Solución 1 — Trigger manual con botón ✅ IMPLEMENTADO

**Qué cambió**: el scrape ahora ocurre solo al presionar el botón **🔍 Obtener datos**, no en cada rerender.

**Código implementado** (`src/app.py`):
```python
st.text_input("Link del Auto", key="link_auto")

col_scrape, _ = st.columns([1, 3])
scrape_triggered = col_scrape.button("🔍 Obtener datos", key="btn_scrape")

scraped_data = {}
if scrape_triggered and link_auto_value:
    cached = st.session_state.get("scraped_cache", {})
    if cached.get("url") == link_auto_value:
        scraped_data = cached["data"]          # reutiliza si es la misma URL
    else:
        with st.spinner("Obteniendo datos del aviso..."):
            scraped_data = scrape_vehicle_details(link_auto_value)
        if scraped_data:
            st.session_state["scraped_cache"] = {"url": link_auto_value, "data": scraped_data}
    if scraped_data:
        st.session_state["telefono_input"] = scraped_data.get("whatsapp_number", "") or ""
        st.session_state["auto_input"]     = scraped_data.get("nombre", "") or ""
        st.session_state["precio_input"]   = scraped_data.get("precio", "") or ""
        st.session_state["descripcion_input"] = scraped_data.get("descripcion", "") or ""
elif st.session_state.get("scraped_cache", {}).get("url") == link_auto_value and link_auto_value:
    scraped_data = st.session_state["scraped_cache"]["data"]
```

**Cambios adicionales incluidos en esta fase**:
- Detección específica de DataDome: header `x-datadome: protected` → `st.warning` con mensaje claro en lugar de `st.error` genérico.
- `clear_contact_form_fields()` ahora también limpia `scraped_cache` al pulsar "Borrar Campos".
- Eliminación de la función `scrape_vehicle_details()` duplicada y corrupta que existía en `app.py:1138`.
- 5 tests nuevos en `tests/test_scraping.py`: 403 genérico, 403 DataDome, sin WhatsApp, caché.

**Impacto**: reduce requests de ~50/sesión a 1–2/aviso. El score DataDome se mantiene seguro en condiciones normales de uso.

---

### Solución 2 — Playwright headless ⏳ PENDIENTE (esfuerzo medio)

Playwright es un browser Chromium real que ejecuta el JS de DataDome. Ya está instalado (`playwright==1.50.0` en `requirements.txt`).

**Ventaja**: DataDome no puede distinguirlo de un usuario real → nunca 403.
**Desventaja**: 2–5 segundos por scrape vs. ~1 segundo con requests.

**Implementación propuesta** — función reemplazable como drop-in:
```python
from playwright.sync_api import sync_playwright

def scrape_vehicle_details_playwright(url: str) -> dict | None:
    """Versión con browser real — evita DataDome completamente."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/132.0.0.0 Safari/537.36"
            ),
            locale="es-CL",
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=20000)
            html = page.content()
        except Exception as e:
            browser.close()
            return None
        browser.close()

    # El resto del parsing con BeautifulSoup es idéntico al actual
    soup = BeautifulSoup(html, "html.parser")
    whatsapp_number = extract_whatsapp_number(soup)
    # ... mismo código de extracción que scrape_vehicle_details() ...
    return { "nombre": ..., "precio": ..., "whatsapp_number": ..., "descripcion": ... }
```

**Nota**: requiere instalar los browsers de Playwright una vez:
```bash
playwright install chromium
```

**Estrategia de integración**: función wrapper que intenta `requests` primero (rápido), y si recibe 403 activa Playwright automáticamente:
```python
def scrape_vehicle_details(url: str) -> dict | None:
    result = _scrape_with_requests(url)
    if result is None:                          # 403 o error
        result = scrape_vehicle_details_playwright(url)   # fallback
    return result
```

**Condiciones para implementar**:
- Los 403 de DataDome siguen ocurriendo frecuentemente a pesar del trigger manual.
- El entorno de ejecución permite `playwright install chromium` (desarrollo local o servidor).
- **No aplica para el `.exe` distribuido** sin configuración adicional del spec de PyInstaller.

---

### Solución 3 — Caché de cookie DataDome ⏳ PENDIENTE (esfuerzo medio, depende de Fase 2)

Una cookie DataDome válida dura varias horas. Si Playwright la obtiene una vez, `requests` puede reutilizarla para scrapes posteriores sin necesitar el browser.

**Implementación propuesta**:
```python
import time

_datadome_cookie_cache = {"value": None, "expires_at": 0}

def _get_valid_datadome_cookie() -> str | None:
    """Obtiene cookie DataDome via Playwright y la cachea."""
    now = time.time()
    if _datadome_cookie_cache["value"] and now < _datadome_cookie_cache["expires_at"]:
        return _datadome_cookie_cache["value"]

    # Playwright para obtener cookie fresca
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.chileautos.cl/", wait_until="networkidle")
        cookies = page.context.cookies()
        browser.close()

    for c in cookies:
        if c["name"] == "datadome":
            _datadome_cookie_cache["value"] = c["value"]
            _datadome_cookie_cache["expires_at"] = now + 3600  # 1 hora
            return c["value"]
    return None

def _scrape_with_requests(url: str) -> dict | None:
    cookie = _get_valid_datadome_cookie()
    session = requests.Session()
    session.headers.update(HEADERS_CHROME_132)
    if cookie:
        session.cookies.set("datadome", cookie, domain=".chileautos.cl")
    response = session.get(url, timeout=15)
    if response.status_code != 200:
        return None
    # ... parsing ...
```

**Ventaja**: lanza Playwright solo 1 vez por hora, los demás scrapes usan `requests` (rápidos).

---

### Solución 4 — Scraping por lote en background ⏳ PENDIENTE (esfuerzo alto, decidir por volumen)

Para cuando el volumen de avisos sea grande. En lugar de scrapear en tiempo real desde la UI, un proceso separado scrappea en horario de bajo tráfico y guarda en BD.

**Arquitectura**:
```
[UI Streamlit]                    [Worker background]
      |                                   |
      | pega link                         | corre cada N horas
      ↓                                   ↓
  guarda link_auto               SELECT * FROM contactos
  en BD con estado               WHERE datos_scraped = 0
  datos_scraped = 0                       |
      |                          scrape_vehicle_details(url)
      | al recargar               UPDATE contactos SET
      ↓                           nombre=?, precio=?, ...
  muestra datos                   datos_scraped = 1
  si ya scraped = 1
```

**Nueva columna en tabla `contactos`**:
```sql
ALTER TABLE contactos ADD COLUMN datos_scraped INTEGER DEFAULT 0;
```

**Worker** (script independiente o `APScheduler`):
```python
# scripts/scrape_worker.py
from apscheduler.schedulers.background import BackgroundScheduler

def scrape_pendientes():
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, link_auto FROM contactos WHERE datos_scraped = 0 LIMIT 20"
    ).fetchall()
    for row in rows:
        data = scrape_vehicle_details(row["link_auto"])
        if data:
            conn.execute(
                "UPDATE contactos SET nombre=?, precio=?, descripcion=?, datos_scraped=1 WHERE id=?",
                (data["nombre"], data["precio"], data["descripcion"], row["id"])
            )
    conn.commit()

scheduler = BackgroundScheduler()
scheduler.add_job(scrape_pendientes, "interval", minutes=30)
scheduler.start()
```

---

## 5. Matriz de decisión

| Solución | Esfuerzo | Elimina 403 | Velocidad | Estado | Recomendada cuando |
|---|---|---|---|---|---|
| Trigger manual | Bajo | Parcial (reduce score) | Sin cambio | ✅ Hecho | — |
| Playwright headless | Medio (1 día) | Sí, definitivamente | 2–5 seg/scrape | ⏳ Pendiente | 403 frecuentes tras Fase 1 |
| Caché cookie | Medio (horas) | Sí | ~1 seg/scrape | ⏳ Pendiente | Junto con Playwright |
| Lote nocturno | Alto (2–3 días) | Sí | Asíncrono | ⏳ Pendiente | > 100 scrapes/día |

---

## 6. Checklist de implementación

```
FASE 1 — Inmediata ✅ COMPLETADA (2026-02-22)
  [x] Mover scrape fuera del rerender de Streamlit
  [x] Añadir botón "🔍 Obtener datos" explícito con st.spinner()
  [x] Añadir caché en st.session_state["scraped_cache"] por URL
  [x] Prefill de campos via session_state al hacer clic en el botón
  [x] Limpiar scraped_cache al pulsar "Borrar Campos"
  [x] Detección específica de DataDome (header x-datadome → st.warning)
  [x] Eliminar función scrape_vehicle_details() duplicada y corrupta
  [x] 7 tests en tests/test_scraping.py (todos pasan)

FASE 2 — Playwright ⏳ PENDIENTE (requiere: playwright install chromium)
  [ ] Extraer lógica de parsing a _parse_vehicle_html(html_bytes) → dict
  [ ] Crear _scrape_with_playwright(url) usando sync_playwright
  [ ] Modificar scrape_vehicle_details() para usar requests primero,
      Playwright como fallback automático en 403 DataDome
  [ ] Añadir try/except ImportError para que falle silencioso sin Chromium
  [ ] Tests: mock de sync_playwright para verificar el fallback
  [ ] Validar compatibilidad con .exe (PyInstaller) antes de activar

FASE 3 — Cookie cache ⏳ PENDIENTE (depende de Fase 2)
  [ ] Implementar _get_valid_datadome_cookie() con TTL de 1 hora
  [ ] Inyectar cookie en sesión de requests
  [ ] Medir reducción de tiempo promedio de scrape

FASE 4 — Background worker ⏳ PENDIENTE (decidir por volumen)
  [ ] Evaluar si el volumen supera 50–100 scrapes/día
  [ ] Añadir columna datos_scraped a tabla contactos
  [ ] Migrar BD existente con ALTER TABLE
  [ ] Crear scripts/scrape_worker.py con APScheduler
```

---

## 7. Señales de alerta — cómo detectar bloqueo DataDome

La detección ya está implementada en `scrape_vehicle_details()` desde la Fase 1:

```python
if response.status_code == 403 and response.headers.get("x-datadome") == "protected":
    st.warning("⚠️ Chileautos bloqueó la solicitud (DataDome). "
               "Espera unos minutos o cambia de red.")
else:
    st.error(f"Error al obtener la página: {response.status_code}")
return None
```

Si el warning de DataDome aparece con frecuencia después de la Fase 1, es la señal para avanzar a la Fase 2 (Playwright).

---

*Documentación generada con Claude Code — tag `v-mejoras-claude-001` | Actualizada 2026-02-22*
