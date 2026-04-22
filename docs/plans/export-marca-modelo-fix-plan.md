# Plan de correccion: Marca/Modelo en exportaciones

## Contexto
En `Ver Contactos & Exportar` (global y por link), la columna `Modelo` puede repetir la `Marca` al inicio en el ejecutable portable.

Ejemplo observado:
- Marca: `MITSUBISHI`
- Modelo: `Mitsubishi Outlander 2.0 CVT`

Resultado esperado:
- Marca: `MITSUBISHI`
- Modelo: `Outlander 2.0 CVT`

## Diagnostico resumido

1. El armado de exportacion pasa por:
   - `prepare_export_dataframe(...)`
   - `parse_auto_details(...)`

2. Cuando el parser no reconoce la marca en `auto`, se usa fallback (`row['marca']` o `row['link_marca']`).

3. En ese fallback, `Modelo` puede quedar con el string completo original, incluyendo marca al inicio.

4. El catalogo `docs/marcas.json` no contiene algunas variantes esperadas por texto real (ej. `Mitsubishi` vs `Mitsubishi Motors`), lo que aumenta este caso.

5. Medicion sobre datos actuales:
   - Casos con prefijo duplicado de marca en modelo: 944
   - Principales marcas afectadas: `MITSUBISHI`, `MG`, `DS`, `INFINITI`.

## Propuesta de implementacion

### 1) Mejorar catalogo de marcas
- Actualizar `docs/marcas.json` con aliases y variantes frecuentes:
  - `Mitsubishi`
  - `MG`
  - `DS`
  - `Infiniti`
  - (mantener variantes existentes como `Mitsubishi Motors` si se usan en otros contextos)

### 2) Sanitizar `Modelo` tras parse/fallback
- En `prepare_export_dataframe(...)`, agregar limpieza final:
  - si `Modelo` inicia con `Marca` (case-insensitive), remover una sola vez ese prefijo.
  - limpiar espacios sobrantes.

Regla sugerida:
- Input: `Marca=MITSUBISHI`, `Modelo=Mitsubishi Outlander 2.0 CVT`
- Output: `Modelo=Outlander 2.0 CVT`

### 3) Mantener fallback anti-Unknown
- Conservar comportamiento actual:
  - si parser no detecta marca, usar `marca/link_marca`.

## Pruebas a agregar

Archivo sugerido: `tests/test_export_brand_fallback.py`

Casos:
1. Parser detecta marca y no duplica modelo.
2. Fallback de marca + modelo con prefijo de marca -> se limpia correctamente.
3. Export por link incluye columna marca y no produce `Unknown` cuando existe marca en link.

## Criterios de aceptacion
- `Marca` no queda en `Unknown` cuando existe marca en datos de link/contacto.
- `Modelo` no repite prefijo de `Marca`.
- Export global y por link muestran resultados consistentes entre local y ejecutable portable.
- Tests de regresion en verde.

## Comandos de verificacion (post-implementacion)

```bash
python -m compileall src/app.py tests/test_export_brand_fallback.py
pytest tests/test_sanitize_links.py tests/test_restricted_numbers.py tests/test_search_contacts.py tests/test_update_contact.py tests/test_export_brand_fallback.py
```

## Notas
- Esta mejora es de calidad de datos de exportacion (UX/reporting), no cambia logica de negocio.
- Recomendado rebuild portable limpio despues de implementar:
  - borrar `dist/` y `build/`
  - empaquetar de nuevo.
