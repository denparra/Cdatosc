"""
scraper_ml.py v2 — Extractor robusto de vehiculos desde MercadoLibre Auto Chile

Uso:
    python scraper_ml.py <URL>
    python scraper_ml.py --login          # guardar sesion ML (para avisos que lo pidan)
    python scraper_ml.py <URL> --debug    # modo verbose

Requiere:
    pip install playwright
    playwright install chromium
"""

import re
import sys
import io
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ---------------------------------------------------------------------------
# Encoding seguro para Windows
# ---------------------------------------------------------------------------
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SESSION_FILE = Path(__file__).parent / "ml_session.json"
DEBUG = "--debug" in sys.argv

TIMEOUT_NAV    = 25_000   # navegacion principal
TIMEOUT_RENDER = 12_000   # espera de renderizado JS
TIMEOUT_PHONE  = 6_000    # espera para capturar telefono

MAX_RETRIES = 2

# Selectores con fallback (se prueban en orden, el primero que funcione gana)
SEL_WA_BUTTON = [
    ".ui-vip-action-contact-info",
    "button:has(svg.ui-pdp-icon--whatsapp)",
    "[data-testid='button-contact-info']",
]
SEL_TITLE = ["h1.ui-pdp-title", "h1"]
SEL_PRICE = [".andes-money-amount__fraction"]
SEL_SUBTITLE = [".ui-pdp-subtitle"]
SEL_DESCRIPTION = [
    ".ui-pdp-description__content",
    "#description .ui-pdp-description__content",
    ".ui-pdp-description p",
]
SEL_SPEC_ROWS = [".andes-table__row", ".ui-vip-specs__table tr"]
SEL_COOKIE_BANNER = [
    "button:has-text('Aceptar cookies')",
    "[data-testid='action:understood-button']",
    "button:has-text('Entendido')",
]


def _log(msg: str):
    if DEBUG:
        print(f"  [DBG] {msg}")


# ---------------------------------------------------------------------------
# Utilidades de selectores
# ---------------------------------------------------------------------------

def _first_match(page, selectors: list, timeout: int = 3000) -> str:
    """Prueba selectores en orden y retorna el texto del primero que exista."""
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count():
                txt = loc.text_content(timeout=timeout)
                if txt and txt.strip():
                    _log(f"Selector OK: {sel}")
                    return txt.strip()
        except Exception:
            continue
    return ""


def _find_button(page, selectors: list, timeout: int = 5000):
    """Espera y retorna el locator del primer boton encontrado."""
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            loc.wait_for(state="visible", timeout=timeout)
            _log(f"Boton encontrado: {sel}")
            return loc
        except Exception:
            continue
    return None


# ---------------------------------------------------------------------------
# Login helper
# ---------------------------------------------------------------------------

def guardar_sesion():
    print("\nSe abrira un browser para iniciar sesion en MercadoLibre.")
    print("1. Inicia sesion con tu cuenta")
    print("2. Vuelve aqui y presiona ENTER\n")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto("https://www.mercadolibre.cl/", wait_until="domcontentloaded")
        input(">> Presiona ENTER cuando hayas iniciado sesion... ")
        ctx.storage_state(path=str(SESSION_FILE))
        browser.close()
    print(f"Sesion guardada en: {SESSION_FILE}")


# ---------------------------------------------------------------------------
# Extractor principal
# ---------------------------------------------------------------------------

def scrape_ml_auto(url: str) -> dict:
    """
    Retorna dict con: nombre, telefono, Auto, precio, descripcion.
    Todos str; string vacio si no se pudo extraer.
    """
    resultado = dict(nombre="", telefono="", Auto="", precio="", descripcion="")
    url_limpia = url.split("#")[0]

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx_kw = dict(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/132.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            locale="es-CL",
        )
        if SESSION_FILE.exists():
            ctx_kw["storage_state"] = str(SESSION_FILE)
            _log("Usando sesion guardada")

        context = browser.new_context(**ctx_kw)
        page = context.new_page()

        # ── Carga con retry ───────────────────────────────────────────────
        loaded = False
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                _log(f"Navegando (intento {attempt})...")
                page.goto(url_limpia, wait_until="domcontentloaded", timeout=TIMEOUT_NAV)
                loaded = True
                break
            except PlaywrightTimeout:
                _log(f"Timeout en intento {attempt}")
                if attempt == MAX_RETRIES:
                    print("[ERROR] No se pudo cargar la pagina tras varios intentos.")
                    browser.close()
                    return resultado

        # ── Esperar renderizado JS ────────────────────────────────────────
        try:
            page.wait_for_selector("h1", timeout=TIMEOUT_RENDER)
        except PlaywrightTimeout:
            print("[ERROR] La pagina no termino de renderizar (JS).")
            browser.close()
            return resultado

        # ── Cerrar banner de cookies si aparece ───────────────────────────
        _cerrar_cookies(page)

        # ── Nombre ────────────────────────────────────────────────────────
        resultado["nombre"] = _first_match(page, SEL_TITLE)

        # ── Precio ────────────────────────────────────────────────────────
        raw_price = _first_match(page, SEL_PRICE)
        if raw_price:
            resultado["precio"] = re.sub(r"\D", "", raw_price)

        # ── Descripcion — expandir si esta colapsada ─────────────────────
        _expandir_descripcion(page)
        resultado["descripcion"] = _first_match(page, SEL_DESCRIPTION, timeout=4000)

        # ── Auto (Ano + Marca + Modelo + Version) ────────────────────────
        resultado["Auto"] = _extraer_auto(page, resultado["descripcion"])

        # ── Telefono (WhatsApp) — siempre al final ───────────────────────
        resultado["telefono"] = _extraer_telefono(page, context)

        _reportar_telefono(resultado["telefono"])

        browser.close()

    return resultado


# ---------------------------------------------------------------------------
# Extractores especializados
# ---------------------------------------------------------------------------

def _cerrar_cookies(page):
    for sel in SEL_COOKIE_BANNER:
        try:
            btn = page.locator(sel).first
            if btn.count() and btn.is_visible():
                btn.click(timeout=2000)
                _log("Banner de cookies cerrado")
                return
        except Exception:
            continue


def _expandir_descripcion(page):
    """Clic en 'Ver descripcion completa' si existe."""
    try:
        expand = page.locator("button.ui-pdp-description-collapse, button:has-text('Ver descripci')").first
        if expand.count() and expand.is_visible():
            expand.click(timeout=2000)
            page.wait_for_timeout(500)
            _log("Descripcion expandida")
    except Exception:
        pass


def _extraer_auto(page, descripcion: str) -> str:
    """
    Construye 'Ano Marca Modelo Version' desde 4 fuentes en orden de confiabilidad.
    """
    # Fuente 1: campos estructurados en la descripcion
    if descripcion:
        auto = _auto_desde_descripcion(descripcion)
        if auto:
            _log(f"Auto desde descripcion: {auto}")
            return auto

    # Fuente 2: tabla de specs del DOM
    auto = _auto_desde_tabla(page)
    if auto:
        _log(f"Auto desde tabla: {auto}")
        return auto

    # Fuente 3: JSON-LD
    auto = _auto_desde_jsonld(page)
    if auto:
        _log(f"Auto desde JSON-LD: {auto}")
        return auto

    # Fuente 4: subtitulo (ano | km)
    sub = _first_match(page, SEL_SUBTITLE, timeout=2000)
    if sub:
        _log(f"Auto desde subtitulo: {sub}")
        return sub

    return ""


def _auto_desde_descripcion(desc: str) -> str:
    patrones = {
        "anio":    re.search(r"\*\s+A[nño]o:\s*(\d{4})", desc, re.I),
        "marca":   re.search(r"\*\s+Marca:\s*([^\n*]+)", desc, re.I),
        "modelo":  re.search(r"\*\s+Modelo:\s*([^\n*]+)", desc, re.I),
        "version": re.search(r"\*\s+(?:Version|Versi[oó]n):\s*([^\n*]+)", desc, re.I),
    }
    partes = [patrones[k].group(1).strip() for k in ("anio", "marca", "modelo", "version") if patrones[k]]
    return " ".join(partes) if partes else ""


def _auto_desde_tabla(page) -> str:
    specs = {}
    for sel in SEL_SPEC_ROWS:
        try:
            rows = page.locator(sel).all()
            if not rows:
                continue
            for row in rows:
                cells = row.locator("td, th").all()
                if len(cells) >= 2:
                    k = cells[0].text_content().strip()
                    v = cells[1].text_content().strip()
                    if k and v:
                        specs[k] = v
            if specs:
                break
        except Exception:
            continue

    claves_auto = [
        ("Año", "Ano"),
        ("Marca",),
        ("Modelo",),
        ("Versión", "Version"),
    ]
    partes = []
    for alternativas in claves_auto:
        for clave in alternativas:
            if clave in specs:
                partes.append(specs[clave])
                break
    return " ".join(partes) if partes else ""


def _auto_desde_jsonld(page) -> str:
    try:
        for script in page.locator('script[type="application/ld+json"]').all():
            data = json.loads(script.text_content())
            if data.get("@type") != "Vehicle":
                continue
            brand = data.get("brand", "")
            name = data.get("name", "")
            m = re.search(r"\b((?:19|20)\d{2})\b", name)
            anio = m.group(1) if m else ""
            # Evitar duplicar marca si ya esta en el nombre
            if brand and brand.lower() in name.lower():
                return f"{anio} {name}".strip()
            return f"{anio} {brand} {name}".strip()
    except Exception:
        pass
    return ""


# ---------------------------------------------------------------------------
# Extraccion de telefono (WhatsApp) — multi-estrategia
# ---------------------------------------------------------------------------

def _extraer_telefono(page, context) -> str:
    """
    Intenta obtener el telefono por 3 vias simultaneas:
      1) Interceptar la respuesta de /contact-info/whatsapp (API interna ML)
      2) Interceptar nueva pestana/popup con URL de WhatsApp
      3) Leer page.url tras navegacion (si el boton navega la pestana actual)

    Si ML redirige al login -> informa.
    Si ML devuelve rate limit -> informa.
    """
    wa_button = _find_button(page, SEL_WA_BUTTON, timeout=5000)
    if not wa_button:
        _log("Boton WhatsApp no encontrado en la pagina")
        return ""

    capturado = []
    login_detectado = False

    # --- Via 1: interceptar respuesta API interna ---
    def on_api_response(response):
        if "contact-info" not in response.url:
            return
        try:
            data = response.json()
            _log(f"API response: success={data.get('success')}")
            if data.get("success"):
                wa_url = data.get("wa_url") or data.get("url") or ""
                if wa_url:
                    capturado.append(wa_url)
            else:
                msg = data.get("display_message", "")
                if msg:
                    print(f"[ML] {msg}")
        except Exception:
            pass

    # --- Via 2: nueva pestana ---
    def on_new_page(p):
        try:
            p.wait_for_load_state("commit", timeout=4000)
        except Exception:
            pass
        nurl = p.url or ""
        _log(f"Nueva pestana: {nurl[:80]}")
        if "whatsapp" in nurl or "wa.me" in nurl:
            capturado.append(nurl)
        try:
            p.close()
        except Exception:
            pass

    page.on("response", on_api_response)
    context.on("page", on_new_page)

    # --- Clic ---
    try:
        wa_button.click(timeout=5000)
        _log("Clic en boton WhatsApp realizado")
        page.wait_for_timeout(TIMEOUT_PHONE)
    except Exception as e:
        _log(f"Error en clic: {e}")

    # --- Via 3: leer URL actual ---
    current = page.url or ""
    _log(f"URL post-clic: {current[:80]}")

    if "whatsapp" in current or "wa.me" in current:
        capturado.append(current)
    elif "login" in current and "mercadolibre" in current:
        login_detectado = True
        print("[AVISO] Este aviso requiere sesion activa de MercadoLibre.")
        print("   -> Ejecuta:  python scraper_ml.py --login")

    # --- Limpiar listeners ---
    try:
        page.remove_listener("response", on_api_response)
    except Exception:
        pass
    try:
        context.remove_listener("page", on_new_page)
    except Exception:
        pass

    # --- Parsear numero de la primera URL valida ---
    phone = _parsear_telefono(capturado)
    if phone:
        _log(f"Telefono extraido: {phone}")
    return phone


def _parsear_telefono(urls: list) -> str:
    """Extrae 9 digitos chilenos de cualquier URL de WhatsApp capturada."""
    for url in urls:
        # Formato: phone=56XXXXXXXXX
        m = re.search(r"phone=56(\d{9})\b", url)
        if m:
            return m.group(1)
        # Formato: wa.me/56XXXXXXXXX
        m = re.search(r"wa\.me/56(\d{9})\b", url)
        if m:
            return m.group(1)
        # Formato generico: cualquier 56 + 9 digitos en la URL
        m = re.search(r"56(\d{9})", url)
        if m:
            return m.group(1)
    return ""


def _reportar_telefono(telefono: str):
    if telefono:
        # Validacion basica: 9 digitos, empieza con 9 (celular chileno)
        if not re.fullmatch(r"9\d{8}", telefono):
            print(f"[AVISO] Telefono extraido ({telefono}) no parece celular chileno (9XXXXXXXX).")
    else:
        print("[AVISO] No se pudo obtener el numero de WhatsApp.")
        if not SESSION_FILE.exists():
            print("   -> Si requiere login:  python scraper_ml.py --login")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]

    if "--login" in flags:
        guardar_sesion()
        return

    if not args:
        print("Uso:")
        print("  python scraper_ml.py <URL>")
        print("  python scraper_ml.py <URL> --debug")
        print("  python scraper_ml.py --login")
        sys.exit(1)

    url = args[0]

    # Validar que sea URL de ML
    if "mercadolibre" not in url:
        print("[ERROR] La URL no parece ser de MercadoLibre.")
        sys.exit(1)

    print(f"\nExtrayendo datos de:\n  {url}\n")
    if SESSION_FILE.exists():
        print("[INFO] Usando sesion guardada de MercadoLibre.\n")

    t0 = time.time()
    datos = scrape_ml_auto(url)
    elapsed = time.time() - t0

    w = 12
    print()
    print("=" * 60)
    print(f"  {'Nombre':<{w}}: {datos['nombre'] or '(no disponible)'}")
    print(f"  {'Telefono':<{w}}: {datos['telefono'] or '(no disponible)'}")
    print(f"  {'Auto':<{w}}: {datos['Auto'] or '(no disponible)'}")
    print(f"  {'Precio':<{w}}: $ {datos['precio'] or '(no disponible)'}")
    desc = datos["descripcion"]
    print(f"  {'Descripcion':<{w}}: {(desc[:100] + '...') if len(desc) > 100 else desc or '(no disponible)'}")
    print(f"  {'Tiempo':<{w}}: {elapsed:.1f}s")
    print("=" * 60)
    print("\nJSON:")
    print(json.dumps(datos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
