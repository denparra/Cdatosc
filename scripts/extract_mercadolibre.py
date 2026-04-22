import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote, urlparse

import requests
from bs4 import BeautifulSoup


DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/132.0.0.0 Safari/537.36"
)


@dataclass
class PlaywrightResult:
    whatsapp_number: str | None
    status: str
    details: str


def _base_domain(hostname: str) -> str:
    if not hostname:
        return ""
    parts = hostname.split(".")
    if len(parts) < 2:
        return hostname
    return "." + ".".join(parts[-2:])


def _normalize_whatsapp_phone(raw: str | None) -> str | None:
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits.startswith("56"):
        digits = digits[2:]
    if len(digits) == 9 and digits.startswith("9"):
        return digits
    return None


def _extract_phone_from_text(text: str) -> str | None:
    patterns = [
        r"phone=56(9\d{8})",
        r"phone=\+?56(9\d{8})",
        r"(?:\+?56\s*9\s*\d{4}\s*\d{4})",
        r"\b56(9\d{8})\b",
        r"\b(9\d{8})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        if match.groups():
            return _normalize_whatsapp_phone(match.group(1))
        return _normalize_whatsapp_phone(match.group(0))
    return None


def _solve_initial_challenge(session: requests.Session, url: str) -> str:
    response = session.get(url, timeout=30)
    text = response.text

    if "_bmstate" not in session.cookies.get_dict() and "requires JavaScript" not in text:
        return text

    bmstate = session.cookies.get("_bmstate")
    if not bmstate:
        return text

    decoded = unquote(bmstate)
    parts = decoded.split(";")
    if len(parts) < 2:
        return text

    token = parts[0]
    difficulty_raw = parts[1]
    difficulty = int(difficulty_raw) if difficulty_raw.isdigit() else 0
    prefix = "0" * difficulty

    nonce = 0
    while True:
        digest = hashlib.sha256(f"{token}{nonce}".encode("utf-8")).hexdigest()
        if digest.startswith(prefix):
            break
        nonce += 1

    parsed = urlparse(url)
    session.cookies.set(
        "_bmc",
        unquote(f"{token};{nonce}"),
        domain=_base_domain(parsed.hostname or ""),
        path="/",
    )
    second = session.get(url, timeout=30)
    return second.text


def _extract_embedded_flags(html: str) -> dict[str, Any]:
    flags: dict[str, Any] = {
        "whatsapp_requires_login": None,
        "is_guest": None,
    }

    wa_anchor = re.search(r'"action_type"\s*:\s*"WHATSAPP"', html)
    if wa_anchor:
        snippet = html[wa_anchor.start() : wa_anchor.start() + 450]
        wa_login = re.search(r'"is_login_required"\s*:\s*(true|false)', snippet)
        if wa_login:
            flags["whatsapp_requires_login"] = wa_login.group(1) == "true"

    guest_match = re.search(r'"isGuest"\s*:\s*(true|false)', html)
    if guest_match:
        flags["is_guest"] = guest_match.group(1) == "true"

    return flags


def _extract_specs(soup: BeautifulSoup) -> dict[str, str]:
    specs: dict[str, str] = {}
    rows = soup.select(".andes-table__row")
    for row in rows:
        cells = row.select("th, td")
        if len(cells) < 2:
            continue
        key = cells[0].get_text(" ", strip=True)
        value = cells[1].get_text(" ", strip=True)
        if key and value:
            specs[key] = value
    return specs


def _extract_public_data(url: str, html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    h1 = soup.select_one("h1")
    if h1:
        title = h1.get_text(" ", strip=True)

    if not title:
        og_title = soup.find("meta", attrs={"property": "og:title"})
        if og_title and og_title.get("content"):
            title = og_title["content"].strip()

    price = None
    price_node = soup.select_one(".andes-money-amount__fraction")
    if price_node:
        price = price_node.get_text(" ", strip=True)

    subtitle = None
    subtitle_node = soup.select_one(".ui-pdp-subtitle")
    if subtitle_node:
        subtitle = subtitle_node.get_text(" ", strip=True)

    location = None
    location_node = soup.select_one(".ui-vip-location__subtitle")
    if location_node:
        location = location_node.get_text(" ", strip=True)

    description = None
    desc_meta = soup.find("meta", attrs={"name": "description"})
    if desc_meta and desc_meta.get("content"):
        description = desc_meta["content"].strip()

    item_match = re.search(r"(MLC-?\d+)", url.upper())
    if not item_match:
        item_match = re.search(r"(MLC-?\d+)", html)
    item_id = item_match.group(1).replace("-", "") if item_match else None

    flags = _extract_embedded_flags(html)
    specs = _extract_specs(soup)

    return {
        "item_id": item_id,
        "title": title or None,
        "price": price,
        "subtitle": subtitle,
        "location": location,
        "description": description,
        "specs": specs,
        "whatsapp_button_found": bool(soup.select_one(".ui-vip-action-contact-info")),
        "whatsapp_requires_login": flags["whatsapp_requires_login"],
        "is_guest": flags["is_guest"],
    }


def _try_extract_whatsapp_with_playwright(url: str, timeout_ms: int = 20000) -> PlaywrightResult:
    try:
        from playwright.sync_api import TimeoutError as PwTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError:
        return PlaywrightResult(None, "playwright_missing", "Playwright no instalado")

    captured_urls: list[str] = []
    captured_bodies: list[str] = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=DEFAULT_UA, locale="es-CL")
            page = context.new_page()

            def on_request(request: Any) -> None:
                captured_urls.append(request.url)

            def on_response(response: Any) -> None:
                try:
                    ctype = (response.headers or {}).get("content-type", "")
                    if "application/json" in ctype or "contact" in response.url.lower():
                        text = response.text()
                        if text:
                            captured_bodies.append(text[:2000])
                except Exception:
                    return

            page.on("request", on_request)
            page.on("response", on_response)

            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_selector(".ui-vip-action-contact-info", state="attached", timeout=timeout_ms)

            button = page.locator(".ui-vip-action-contact-info").first
            if button.count() == 0:
                browser.close()
                return PlaywrightResult(None, "no_button", "No se encontro boton WhatsApp")

            popup_url = None
            try:
                with page.expect_popup(timeout=4000) as popup_info:
                    button.click(timeout=4000, force=True)
                popup = popup_info.value
                popup.wait_for_load_state("domcontentloaded", timeout=4000)
                popup_url = popup.url
                captured_urls.append(popup_url)
            except PwTimeoutError:
                try:
                    button.click(timeout=3000, force=True)
                except PwTimeoutError:
                    page.evaluate(
                        """
                        () => {
                            const btn = document.querySelector('.ui-vip-action-contact-info');
                            if (btn) {
                                btn.click();
                                return true;
                            }
                            return false;
                        }
                        """
                    )
                page.wait_for_timeout(1800)
                captured_urls.append(page.url)

            browser.close()

            for candidate in captured_urls:
                phone = _extract_phone_from_text(candidate)
                if phone:
                    return PlaywrightResult(phone, "ok", "Numero capturado desde URL")

            for body in captured_bodies:
                phone = _extract_phone_from_text(body)
                if phone:
                    return PlaywrightResult(phone, "ok", "Numero capturado desde respuesta")

            check_urls = [u for u in captured_urls if u]
            if popup_url and "login" in popup_url.lower():
                return PlaywrightResult(None, "login_required", "La accion redirigio a login")
            if any("/jms/" in u.lower() or "login" in u.lower() for u in check_urls):
                return PlaywrightResult(None, "login_required", "La accion requiere sesion activa")

            return PlaywrightResult(None, "not_found", "No se pudo capturar numero WhatsApp")
    except Exception as exc:
        return PlaywrightResult(None, "playwright_error", str(exc))


def extract_mercadolibre_data(url: str) -> dict[str, Any]:
    if "mercadolibre" not in url.lower():
        raise ValueError("La URL no parece ser de MercadoLibre")

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": DEFAULT_UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
        }
    )

    html = _solve_initial_challenge(session, url)
    data = _extract_public_data(url, html)

    pw_result = _try_extract_whatsapp_with_playwright(url)
    data["whatsapp_number"] = pw_result.whatsapp_number
    data["whatsapp_extraction_status"] = pw_result.status
    data["whatsapp_extraction_details"] = pw_result.details

    if not data["whatsapp_number"]:
        data["whatsapp_number"] = None

    return data


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extrae datos de una publicacion de MercadoLibre Autos (Chile)."
    )
    parser.add_argument("url", help="URL de la publicacion de MercadoLibre")
    args = parser.parse_args()

    result = extract_mercadolibre_data(args.url)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
