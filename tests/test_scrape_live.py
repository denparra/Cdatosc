"""Live scraping test against Chileautos URL to validate selectors and headers."""
import re
import sys
import os
import requests
from bs4 import BeautifulSoup

TEST_URL = (
    "https://www.chileautos.cl/vehiculos/detalles/"
    "2020-haval-h6-2-0-auto-elite/CP-AD-8512530/"
)

MODERN_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8,"
        "application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Referer": "https://www.chileautos.cl/",
    "Upgrade-Insecure-Requests": "1",
    "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
}


def fetch(url=TEST_URL):
    s = requests.Session()
    s.headers.update(MODERN_HEADERS)
    return s.get(url, timeout=15)


def parse(html_bytes):
    soup = BeautifulSoup(html_bytes, "html.parser")
    results = {}

    # Vehicle name
    v_elem = soup.find("div", class_="features-item-value-vehculo")
    if v_elem:
        results["vehiculo_div"] = v_elem.get_text(strip=True)
    h1 = soup.find("h1")
    results["h1"] = h1.get_text(strip=True) if h1 else None

    # Price
    p_elem = soup.find("div", class_="features-item-value-precio")
    results["precio_div"] = p_elem.get_text(strip=True) if p_elem else None

    # Description
    d_container = soup.find("div", class_="view-more-container")
    if d_container:
        target = d_container.find("div", class_="view-more-target")
        if target:
            p = target.find("p")
            results["descripcion"] = p.get_text(strip=True) if p else None

    # WhatsApp
    wa = soup.find("a", href=re.compile(r"https://wa\.me/56\d{9}"))
    results["whatsapp_href"] = wa["href"] if wa else None

    # Fallback: title
    results["title"] = soup.title.string if soup.title else None

    return results


if __name__ == "__main__":
    print("=" * 60)
    print("LIVE SCRAPING TEST — Chileautos")
    print("=" * 60)

    print(f"\nURL: {TEST_URL}\n")

    # Step 1: HTTP check
    print("[1] HTTP Request...")
    r = fetch()
    print(f"    Status  : {r.status_code}")
    print(f"    Server  : {r.headers.get('Server', '?')}")
    print(f"    Encoding: {r.encoding}")
    assert r.status_code == 200, f"FAIL: expected 200, got {r.status_code}"
    print("    -> OK (200)")

    # Step 2: Parse selectors
    print("\n[2] CSS Selector parsing...")
    data = parse(r.content)
    for k, v in data.items():
        val = (str(v)[:80] + "...") if v and len(str(v)) > 80 else v
        print(f"    {k:<20}: {val}")

    # Step 3: Validate expected data
    print("\n[3] Validation...")
    assert data.get("title") and "haval" in data["title"].lower(), \
        f"FAIL: title missing or wrong: {data.get('title')}"
    print("    title ✓")

    h1_val = data.get("h1") or ""
    assert "haval" in h1_val.lower() or "h6" in h1_val.lower(), \
        f"FAIL: h1 doesn't mention expected vehicle: {h1_val}"
    print("    h1 ✓")

    print("\n" + "=" * 60)
    print("ALL CHECKS PASSED")
    print("=" * 60)
