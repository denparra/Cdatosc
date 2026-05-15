#!/usr/bin/env python3
"""
Prueba en vivo: detecta si un aviso de chileautos.cl está disponible o no.

Señales de "no disponible / vendido":
1. Script `gallery_meta` con "salestatus":"Sold" o "issold":"true"
2. Badge HTML <csn-badge type="soldorunavailable">
3. Ausencia del botón "Contacta al vendedor" (csn-btn-lead)
"""

import requests
import re
from bs4 import BeautifulSoup


def check_chileautos_availability(url: str) -> dict:
    """
    Retorna dict con:
      - url
      - status_code
      - available (bool | None)
      - signals (list de strings con las señales encontradas)
      - error (str | None)
    """
    result = {
        "url": url,
        "status_code": None,
        "available": None,
        "signals": [],
        "error": None,
    }

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/132.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "es-CL,es;q=0.9",
        }
        resp = requests.get(url, headers=headers, timeout=30)
        result["status_code"] = resp.status_code
        resp.raise_for_status()
    except Exception as exc:
        result["error"] = f"Request failed: {exc}"
        return result

    soup = BeautifulSoup(resp.text, "html.parser")
    html_text = resp.text.lower()

    # Señal 1: gallery_meta con salestatus Sold o issold true
    gallery_meta_match = re.search(
        r'var\s+gallery_meta\s*=\s*({.*?});', resp.text, re.DOTALL
    )
    if gallery_meta_match:
        meta_raw = gallery_meta_match.group(1).lower()
        if '"salestatus":"sold"' in meta_raw or '"issold":"true"' in meta_raw:
            result["signals"].append("gallery_meta indica vendido (salestatus=Sold / issold=true)")
    else:
        # Fallback: buscar esos strings sueltos en el HTML
        if '"salestatus":"sold"' in html_text or '"issold":"true"' in html_text:
            result["signals"].append("HTML contiene salestatus=Sold / issold=true")

    # Señal 2: badge soldorunavailable
    if '<csn-badge type="soldorunavailable"' in resp.text:
        result["signals"].append("Badge soldorunavailable presente")

    # Señal 3: ausencia de botón contacto
    has_contact_btn = bool(
        soup.find("a", class_="csn-btn-lead")
        or "contacta al vendedor" in html_text
    )
    if not has_contact_btn:
        result["signals"].append("No hay boton 'Contacta al vendedor'")

    # Determinar disponibilidad
    unavailable_signals = [
        s for s in result["signals"]
        if any(k in s.lower() for k in ["vendido", "sold", "unavailable", "no hay"])
    ]
    if unavailable_signals:
        result["available"] = False
    elif has_contact_btn:
        result["available"] = True
    else:
        result["available"] = None  # Indeterminado

    return result


if __name__ == "__main__":
    urls = [
        ("DISPONIBLE", "https://www.chileautos.cl/vehiculos/detalles/2024-kia-soluto-1-4-lx-gps/CL-AD-20025686"),
        ("NO DISPONIBLE", "https://www.chileautos.cl/vehiculos/detalles/2023-kia-sportage-2-0-gsl-auto-ex-bs/CL-AD-20239030/"),
    ]

    for label, url in urls:
        print(f"\n{'='*60}")
        print(f"Testing: {label}")
        print(f"URL: {url}")
        print("=" * 60)
        res = check_chileautos_availability(url)
        print(f"Status HTTP : {res['status_code']}")
        print(f"Error       : {res['error']}")
        print(f"Señales     : {res['signals']}")
        print(f"Disponible  : {res['available']}")
