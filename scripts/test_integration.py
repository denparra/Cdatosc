import sys
sys.path.insert(0, 'src')

import pandas as pd
from app import (
    check_chileautos_availability,
    save_availability_result,
    get_availability_for_urls,
    enrich_with_availability,
)

# Test 1: check two URLs
print("=== Test check_chileautos_availability ===")
url1 = "https://www.chileautos.cl/vehiculos/detalles/2024-kia-soluto-1-4-lx-gps/CL-AD-20025686"
url2 = "https://www.chileautos.cl/vehiculos/detalles/2023-kia-sportage-2-0-gsl-auto-ex-bs/CL-AD-20239030/"

for label, url in [("DISPONIBLE", url1), ("NO DISPONIBLE", url2)]:
    print(f"\nTesting: {label}")
    res = check_chileautos_availability(url)
    print(f"  Status: {res['status_code']}")
    print(f"  Available: {res['available']}")
    print(f"  Signals: {res['signals']}")
    print(f"  Error: {res['error']}")

# Test 2: save and retrieve
print("\n=== Test save/get ===")
save_availability_result(url1, "disponible", "-")
save_availability_result(url2, "no_disponible", "gallery_meta sold | badge")

df = get_availability_for_urls([url1, url2])
print(df)

# Test 3: enrich DataFrame
print("\n=== Test enrich_with_availability ===")
test_df = pd.DataFrame({
    "Telefono": ["+56912345678", "+56987654321"],
    "Nombre": ["Juan", "Pedro"],
    "Marca": ["Kia", "Kia"],
    "Modelo": ["Soluto", "Sportage"],
    "Año": [2024, 2023],
    "Precio": [9450000, 21000000],
    "Link": [url1, url2],
    "Origen": ["Norte", "Sur"],
})

enriched = enrich_with_availability(test_df)
print(enriched[["Nombre", "Marca", "Estado"]])
print("\nAll tests passed!")
