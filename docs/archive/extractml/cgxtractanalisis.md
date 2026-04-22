# Analisis de extraccion - MercadoLibre Autos Chile

Fecha: 2026-03-10
URL de referencia: `https://auto.mercadolibre.cl/MLC-1872936105-renault-express-15-dsl-furgon-zen-mt-2023-248-_JM`

## Resumen ejecutivo

- MercadoLibre Autos no responde como Chileautos: primero entrega una pagina de desafio JavaScript (anti-bot), no el HTML completo del aviso.
- El boton de WhatsApp existe en el DOM (`.ui-vip-action-contact-info`), pero el numero no viene en claro en el HTML base.
- En el estado hidratado de la pagina, para el aviso analizado aparece `action_type: "WHATSAPP"` y `is_login_required: true`.
- Con esto, el numero de WhatsApp depende del flujo de accion de frontend (API interna + reCAPTCHA + estado de sesion).

## Hallazgos tecnicos

### 1) Diferencia clave con Chileautos

- Chileautos: normalmente permite `requests + BeautifulSoup` para extraer telefono si viene en `wa.me`.
- MercadoLibre Autos: requiere resolver desafio JS inicial para acceder al HTML real del aviso.

### 2) Boton y estado de contacto

En el HTML hidratado del aviso se observa:

- Boton con clase: `ui-vip-action-contact-info`
- Texto del boton: `WhatsApp`
- Configuracion de accion en estado de pagina:
  - `action_type: "WHATSAPP"`
  - `is_login_required: true`

Conclusiones:

- No es estable buscar directamente `wa.me` o `api.whatsapp.com/send` en HTML estatico.
- El numero puede no exponerse si no hay sesion valida o si falla el flujo de contacto.

### 3) Flujo real del numero WhatsApp

El numero se obtiene cuando se ejecuta la accion del boton (frontend), no por parseo simple del DOM.

Implica:

- Sesion (segun aviso/configuracion del vendedor)
- Token de reCAPTCHA
- Llamada interna de contacto y/o redireccion final a WhatsApp

## Mejor estrategia de extraccion

### Estrategia recomendada por etapas

1. Resolver HTML real del aviso (desafio anti-bot).
2. Extraer datos publicos del vehiculo (titulo, precio, subtitulo, ubicacion, specs).
3. Intentar WhatsApp con browser real (Playwright): click en boton e inspeccion de popup/request/response.
4. Normalizar telefono chileno a 9 digitos si se captura `phone=56XXXXXXXXX`.
5. Si no se puede obtener numero, devolver estado claro (`No disponible`) sin romper el proceso.

### Por que esta estrategia

- Mantiene velocidad para datos publicos.
- Aisla el riesgo de WhatsApp, que es la parte mas inestable por login/recaptcha.
- Permite observabilidad (saber si fallo por login, por captcha o por falta de boton).

## Resultado para el objetivo principal (numero WhatsApp)

- El numero no se puede garantizar solo con `requests + BeautifulSoup`.
- Para mayor tasa de exito se necesita browser real y, en muchos casos, sesion autenticada en MercadoLibre.
- Aun con browser real, algunos avisos pueden forzar login o no entregar telefono.

## Implementacion entregada en este repo

Se creo un extractor CLI en:

- `scripts/extract_mercadolibre.py`

Capacidades:

- Recibe solo la URL de MercadoLibre.
- Resuelve el desafio inicial para obtener HTML real.
- Extrae datos publicos del aviso y especificaciones.
- Intenta extraer WhatsApp con Playwright (si esta instalado y disponible).
- Devuelve JSON con:
  - `item_id`, `title`, `price`, `subtitle`, `location`, `description`
  - `whatsapp_button_found`, `whatsapp_requires_login`
  - `whatsapp_number` (si se pudo capturar)
  - `specs` y metadatos de diagnostico.

## Uso rapido

```bash
python scripts/extract_mercadolibre.py "https://auto.mercadolibre.cl/MLC-1872936105-renault-express-15-dsl-furgon-zen-mt-2023-248-_JM"
```

Si quieres intentar extraer WhatsApp con browser real:

```bash
pip install playwright
playwright install chromium
python scripts/extract_mercadolibre.py "<URL_ML>"
```

Nota: si el aviso requiere login para contacto, sin sesion autenticada el numero puede quedar como `null`.
