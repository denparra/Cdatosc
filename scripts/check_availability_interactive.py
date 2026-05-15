#!/usr/bin/env python3
"""
Verificador interactivo de disponibilidad de avisos chileautos.cl.

Uso:
    python scripts/check_availability_interactive.py

Pide links uno a uno. Escribe 'no' para terminar.
Muestra tabla de resultados al final.
"""

import sys
import time
from typing import Any

# Reutilizamos el helper del script anterior
from test_chileautos_availability import check_chileautos_availability


def prompt_links() -> list[str]:
    """Pide links al usuario hasta que escriba 'no'."""
    print("=" * 60)
    print("  Verificador de disponibilidad - chileautos.cl")
    print("=" * 60)
    print("\nIngresá los links de los avisos.")
    print("Escribí 'no' (o dejalo vacío) cuando termines.\n")

    links: list[str] = []
    while True:
        raw = input(f"Link {len(links) + 1}: ").strip()
        if not raw or raw.lower() == "no":
            break
        links.append(raw)

    return links


def run_checks(links: list[str]) -> list[dict[str, Any]]:
    """Ejecuta la verificación para cada link mostrando progreso."""
    results: list[dict[str, Any]] = []
    total = len(links)

    print(f"\nVerificando {total} aviso(s)...\n")
    for i, url in enumerate(links, 1):
        print(f"  [{i}/{total}] {url[:70]}...", end=" ", flush=True)
        try:
            res = check_chileautos_availability(url)
            label = "DISPONIBLE" if res["available"] is True else ("NO DISPONIBLE" if res["available"] is False else "INDETERMINADO")
            print(label)
            results.append(res)
            # Pequeña pausa para no saturar al servidor
            time.sleep(1.0)
        except Exception as exc:
            print(f"ERROR: {exc}")
            results.append({
                "url": url,
                "status_code": None,
                "available": None,
                "signals": [],
                "error": str(exc),
            })
    return results


def print_results(results: list[dict[str, Any]]) -> None:
    """Muestra tabla final con todos los resultados."""
    print("\n" + "=" * 80)
    print("  RESULTADOS")
    print("=" * 80)
    print(f"{'#':<4} {'DISPONIBLE':<14} {'SEÑALES':<30} {'URL'}")
    print("-" * 80)

    for i, r in enumerate(results, 1):
        disp = "SI" if r["available"] is True else ("NO" if r["available"] is False else "?")
        señales = " | ".join(r["signals"]) if r["signals"] else "-"
        url = r["url"][:55]
        print(f"{i:<4} {disp:<14} {señales:<30} {url}")

    print("-" * 80)
    disponibles = sum(1 for r in results if r["available"] is True)
    no_disponibles = sum(1 for r in results if r["available"] is False)
    indeterminados = sum(1 for r in results if r["available"] is None and not r["error"])
    errores = sum(1 for r in results if r["error"])
    print(f"\nResumen: {disponibles} disponible(s) | {no_disponibles} no disponible(s) | {indeterminados} indeterminado(s) | {errores} error(es)")
    print("=" * 80)


def main() -> None:
    links = prompt_links()
    if not links:
        print("No ingresaste ningún link. Saliendo.")
        sys.exit(0)

    results = run_checks(links)
    print_results(results)


if __name__ == "__main__":
    main()
