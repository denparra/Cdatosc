# Análisis de Extracción de Datos — MercadoLibre Autos Chile

**Fecha de análisis**: 2026-03-10
**URL ejemplo**: `https://auto.mercadolibre.cl/MLC-1872936105-renault-express-15-dsl-furgon-zen-mt-2023-248-_JM`
**Item ID**: `MLC1872936105` | **Seller ID**: `1703568676`

---

## Hallazgos Clave

### 1. Arquitectura de la Página — SPA Pura

MercadoLibre Auto es una **Single Page Application (SPA) renderizada 100% por JavaScript**.

```
GET https://auto.mercadolibre.cl/MLC-XXXXXXXXX → HTML de solo 2,429 bytes
Contenido real: <div id="root"><div class="spinner"></div></div>
```

**Consecuencia directa**: `requests + BeautifulSoup` **NO funciona** para ML. Solo devuelve el spinner de carga. Es obligatorio usar un browser headless.

### 2. WhatsApp — NO Requiere Login

El botón WhatsApp tiene en su estado de React la propiedad:

```json
"is_login_required": false,
"is_reauth_required": false,
"action_type": "WHATSAPP"
```

El número está embebido en el runtime de React (closure del componente), **no en el HTML estático ni en atributos del DOM**. Al hacer clic, el botón navega a:

```
https://api.whatsapp.com/send/?phone=56965092544&text=Hola%2C+tengo+algunas+preguntas+...
```

**El número de teléfono se extrae de esa URL de navegación**. No hay login previo requerido.

### 3. API Pública de ML — Bloqueada

```bash
GET https://api.mercadolibre.com/items/MLC1872936105 → 403 Forbidden
GET https://api.mercadolibre.com/users/1703568676   → 403 Forbidden
```

Error: `PA_UNAUTHORIZED_RESULT_FROM_POLICIES`. La API pública de ML para Chile (`MLC`) está restringida a aplicaciones registradas con OAuth token.

### 4. JSON-LD — Datos del Vehículo SIN Phone

La página sí incluye datos estructurados JSON-LD accesibles desde el DOM renderizado:

```json
{
  "@type": "Vehicle",
  "name": "Renault Express 1,5 Dsl Furgon Zen Mt - 2023 | 248",
  "brand": "Renault",
  "offers": { "price": 10190000, "priceCurrency": "CLP" },
  "bodyType": "Furgón",
  "fuelType": "Diésel",
  "numberOfDoors": "4",
  "vehicleTransmission": "Manual",
  "color": "BLANCO GLACIER",
  "productID": "MLC1872936105"
}
```

Estos datos son ricos pero **no incluyen el teléfono/WhatsApp**.

---

## Datos Extraíbles por Elemento DOM

| Dato | Selector CSS | Valor Ejemplo |
|------|-------------|---------------|
| Título | `h1` | `Renault Express 1,5 Dsl Furgon Zen Mt - 2023 \| 248` |
| Precio | `.andes-money-amount__fraction` | `10.190.000` |
| Subtítulo (año/km) | `.ui-pdp-subtitle` | `2023 \| 47.683 km · Publicado hace 4 días` |
| Ubicación | `.ui-vip-location__subtitle` | `Lo Barnechea - RM (Metropolitana)` |
| Vendedor | `.ui-pdp-seller__header__title` | `Concesionaria con identidad verificada` |
| Especificaciones | `.andes-table__row` | Marca, Modelo, Año, Versión, Color, etc. |
| Botón WhatsApp | `.ui-vip-action-contact-info` | `<button>` (no `<a>`, no href) |

**Especificaciones disponibles en tabla**:
- Marca, Modelo, Año, Versión, Color
- Tipo de combustible, Puertas, Transmisión, Carrocería
- Kilómetros
- Aire acondicionado, Cristales eléctricos, Bluetooth
- Airbag, Llantas de aleación, Único dueño

---

## Estrategia de Extracción Recomendada — Playwright Python

### Flujo de Extracción

```
1. Navegar a URL con Playwright (browser headless)
2. Esperar carga completa del DOM (selector `.ui-vip-action-contact-info`)
3. Extraer datos del vehículo desde DOM / JSON-LD
4. Interceptar navegación al hacer clic en botón WhatsApp → capturar URL
5. Parsear phone=56XXXXXXXXX de la URL
6. Retornar dict con todos los datos
```

### Implementación de Referencia (Python + Playwright)

```python
import re
from playwright.sync_api import sync_playwright

def scrape_ml_vehicle(url: str) -> dict | None:
    """
    Extrae datos de un vehículo desde MercadoLibre Auto (Chile).
    Requiere: pip install playwright && playwright install chromium
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/132.0.0.0"
        )
        page = context.new_page()

        # Capturar la URL de navegación del botón WA antes de que salga del dominio
        wa_url_captured = []

        def handle_request(request):
            if "api.whatsapp.com/send" in request.url:
                wa_url_captured.append(request.url)

        page.on("request", handle_request)

        page.goto(url, wait_until="networkidle", timeout=30000)

        # Esperar que el botón WhatsApp esté presente
        page.wait_for_selector(".ui-vip-action-contact-info", timeout=10000)

        # --- Extraer datos del vehículo ---
        title = page.locator("h1").first.text_content().strip()

        price_raw = page.locator(".andes-money-amount__fraction").first.text_content().strip()
        price = price_raw.replace(".", "")  # Convertir "10.190.000" → "10190000"

        subtitle = page.locator(".ui-pdp-subtitle").first.text_content().strip()
        # "2023 | 47.683 km · Publicado hace 4 días"
        year_match = re.search(r"(\d{4})", subtitle)
        km_match = re.search(r"([\d.]+)\s*km", subtitle)
        year = year_match.group(1) if year_match else None
        km = km_match.group(1).replace(".", "") if km_match else None

        location = None
        loc_el = page.locator(".ui-vip-location__subtitle").first
        if loc_el.count():
            location = loc_el.text_content().strip()

        # Especificaciones de tabla
        specs = {}
        rows = page.locator(".andes-table__row").all()
        for row in rows:
            cells = row.locator("td").all()
            if len(cells) >= 2:
                key = cells[0].text_content().strip()
                val = cells[1].text_content().strip()
                specs[key] = val

        # --- Extraer WhatsApp (clic + interceptar navegación) ---
        whatsapp_number = None

        # Bloquear la navegación saliente a WhatsApp para no perder el contexto
        with page.expect_popup(timeout=5000) as popup_info:
            # Algunos builds abren popup; si no, capturamos via on('request')
            try:
                page.locator(".ui-vip-action-contact-info").click()
            except Exception:
                pass

        # Fallback: revisar lo capturado por el event listener
        if wa_url_captured:
            wa_url = wa_url_captured[0]
            m = re.search(r"phone=56(\d{9})", wa_url)
            if m:
                whatsapp_number = m.group(1)

        browser.close()

        return {
            "whatsapp_number": whatsapp_number,
            "nombre": title,
            "precio": price,
            "anio": year,
            "km": km,
            "ubicacion": location,
            "specs": specs,
            "fuente": "mercadolibre"
        }
```

### Implementación Alternativa — Interceptar sin Popup

Si el botón no abre popup sino que navega en la misma pestaña, usar:

```python
def get_wa_number_via_route(page) -> str | None:
    """Intercepta la navegación al WA URL sin perder el contexto."""
    captured = []

    # Bloquear la navegación real, solo capturar la URL
    def intercept(route, request):
        if "api.whatsapp.com" in request.url:
            captured.append(request.url)
            route.abort()  # Evita salir de la página
        else:
            route.continue_()

    page.route("**/*", intercept)
    page.locator(".ui-vip-action-contact-info").click()
    page.wait_for_timeout(1000)
    page.unroute("**/*", intercept)

    if captured:
        m = re.search(r"phone=56(\d{9})", captured[0])
        return m.group(1) if m else None
    return None
```

---

## Comparación con Chileautos

| Aspecto | Chileautos | MercadoLibre Auto |
|---------|------------|-------------------|
| Renderizado | Server-side (HTML completo) | SPA / JavaScript puro |
| Herramienta | `requests + BeautifulSoup` | `Playwright` (obligatorio) |
| WhatsApp link | `<a href="https://wa.me/56...">` en HTML | URL generada al clic del botón |
| Login requerido (WA) | No | No (`is_login_required: false`) |
| API pública | N/A | Bloqueada (403) |
| Anti-bot | DataDome (headers específicos) | No detectado (headless OK) |
| Velocidad extracción | ~1-2 seg | ~5-10 seg (espera JS) |

---

## Limitaciones y Consideraciones

### Lo que NO es posible
- Obtener el número vía API REST sin token OAuth de ML
- Parsear la página con `requests` (solo devuelve spinner)
- Encontrar el número directamente en atributos HTML o scripts inline

### Riesgos
- **Rate limiting**: ML puede bloquear IPs que hagan scraping intensivo
- **Cambios de UI**: Los selectores CSS (`ui-vip-action-contact-info`, `.andes-table__row`) pueden cambiar con actualizaciones de ML
- **IDs de React dinámicos**: El `id` del botón cambia en cada carga (`_R_mdbalmj1r2e_`). Usar siempre el selector por clase.

### Recomendaciones
1. Usar Playwright con `headless=True` y limitar velocidad de requests
2. Agregar delays aleatorios entre scrapes (2-5 seg)
3. Manejar timeout en la espera del botón WA
4. Validar el número extraído con regex `^\d{9}$` (formato chileno)
5. Cachear resultados por URL para no re-scrapear páginas ya procesadas

---

## Integración con el Proyecto Actual

Para integrar ML al flujo existente (que ya soporta Chileautos), la función `scrape_vehicle_details()` en `src/app.py` debe:

1. **Detectar el dominio** de la URL para elegir el scraper correcto:
   ```python
   def scrape_vehicle_details(url: str) -> dict | None:
       if "mercadolibre" in url or "auto.mercadolibre" in url:
           return scrape_ml_vehicle(url)
       else:
           return scrape_chileautos_vehicle(url)  # scraper actual
   ```

2. **Agregar dependencia**: `playwright` + `playwright install chromium`

3. **Normalizar salida**: Asegurar que la función ML retorne las mismas keys que el scraper de Chileautos (`whatsapp_number`, `nombre`, `precio`, `descripcion`).

---

## Endpoint Interno Descubierto (via Playwright)

Al hacer clic en el botón, el frontend de ML llama a su propio backend:

```
GET https://auto.mercadolibre.cl/p/api/items/{itemId}/contact-info/whatsapp
    ?recaptchaToken={token_generado_por_el_browser}
    &is_hide_modal=false
    &vertical=motors
    &ajaxBackendParams[track_from_view]=vip
    &ajaxBackendParams[track_event_source]=button
    &action=classi_contact
```

**Respuesta cuando `success: true`**:
```json
{
  "success": true,
  "wa_url": "https://api.whatsapp.com/send/?phone=56XXXXXXXXX&text=..."
}
```

**Respuesta cuando rate-limitado**:
```json
{
  "success": false,
  "display_message": "Superaste el límite de contactos diarios. Vuelve a intentarlo mañana."
}
```

**Implicaciones**:
- ML tiene un **rate limit diario** por IP/sesión para el botón WhatsApp
- El `recaptchaToken` es generado por el browser real (reCAPTCHA v3) y es de un solo uso
- No se puede llamar este endpoint directamente sin el token válido → Playwright es obligatorio
- La estrategia correcta es interceptar la respuesta HTTP con `page.on("response", ...)`

## Número Extraído del Ejemplo

URL de ejemplo analizada:
```
https://auto.mercadolibre.cl/MLC-1872936105-renault-express-15-dsl-furgon-zen-mt-2023-248-_JM
```

WA URL generada al click:
```
https://api.whatsapp.com/send/?phone=56965092544&text=Hola%2C+tengo+algunas+preguntas+sobre+Renault+Express+...
```

**Número extraído**: `965092544` (9 dígitos, formato chileno sin prefijo 56)
