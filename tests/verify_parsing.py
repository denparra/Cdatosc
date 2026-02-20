
import json
import re
import os

def load_brands(json_path):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('marcas', [])
    except Exception as e:
        print(f"Error loading brands: {e}")
        return []

def parse_auto_string(auto_str, brands):
    if not auto_str:
        return "Unknown", "Unknown", "Unknown"
    
    year = "Unknown"
    brand = "Unknown"
    model = "Unknown"
    
    # 1. Year Extraction
    # Strategy: Check start first, then anywhere
    match_start = re.match(r'^((?:19|20)\d{2})\b', auto_str)
    if match_start:
        year = match_start.group(1)
        auto_str = auto_str[match_start.end():].strip()
    else:
        match_any = re.search(r'\b((?:19|20)\d{2})\b', auto_str)
        if match_any:
            year = match_any.group(1)
            auto_str = (auto_str[:match_any.start()] + " " + auto_str[match_any.end():]).strip()
    
    # Clean spaces
    auto_str = re.sub(r'\s+', ' ', auto_str)

    # 2. Brand Extraction
    brands_sorted = sorted(brands, key=len, reverse=True)
    found_brand = False
    for b in brands_sorted:
        pattern = r'\b' + re.escape(b) + r'\b'
        if re.search(pattern, auto_str, re.IGNORECASE):
            brand = b # Use the canonical name from JSON
            auto_str = re.sub(pattern, '', auto_str, count=1, flags=re.IGNORECASE).strip()
            found_brand = True
            break
    
    if not found_brand and "Mercedes-Benz" in brands:
        # Fallback or specific handling if needed (though json has "Mercedes Benz" usually)
        pass

    # 3. Model Extraction
    # What remains is the model
    auto_str = re.sub(r'\s+', ' ', auto_str)
    model = auto_str.strip() if auto_str.strip() else "Unknown"

    return year, brand, model

def main():
    # Mock path since we are running this one-off
    json_path = "docs/marcas.json"
    if not os.path.exists(json_path):
        # Fallback for the test if file not found locally where script runs
        # I'll hardcode some brands for the test if file access fails in this context, 
        # but in the real app it will work. 
        # Actually I can use absolute path from user context.
        json_path = r"c:/Users/denny/OneDrive/Documentos/PRACTICAS/PYTHON/Streamlit/CODEX/DATOS_CONSIGNACION/docs/marcas.json"

    brands = load_brands(json_path)
    if not brands:
        print("Warning: Using hardcoded brands for test")
        brands = ["Hyundai", "Haval", "Toyota", "Suzuki", "Mercedes Benz", "Kia"]

    tests = [
        "2022 Haval H6 2.0 Auto Deluxe 4WD",
        "Toyota Corolla 2018",
        "Suzuki Swift 1.2 GLX 2015",
        "2012 Hyundai Elantra Gls",
        "Vehiculo Desconocido 2020", # Unknown brand
        "Mercedes Benz A200 2019",
        "2023", # Just year
        "", # Empty
    ]

    print(f"{'INPUT':<40} | {'YEAR':<6} | {'BRAND':<15} | {'MODEL'}")
    print("-" * 80)
    for t in tests:
        y, b, m = parse_auto_string(t, brands)
        print(f"{t:<40} | {y:<6} | {b:<15} | {m}")

if __name__ == "__main__":
    main()
