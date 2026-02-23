# UX/UI Alerts Theme Improvement (Diagnostico + Propuesta)

## Contexto y alcance
- Alcance de esta iteracion: solo UX/UI (sin cambios en logica de negocio ni componentes productivos).
- Referencia visual analizada: `docs/img-ref/theme.png`.
- Stack actual detectado: Streamlit + CSS custom embebido en `src/app.py`.

## 1) Diagnostico visual de la referencia (`theme.png`)

### Hallazgos principales
1. Bajo contraste en mensajes de estado
   - El banner tipo warning (amarillo) muestra texto demasiado claro sobre fondo claro.
   - El bloque tipo info (celeste) presenta contraste insuficiente para lectura rapida.
   - Impacto: el mensaje existe, pero no comunica (falla de discoverability).

2. Jerarquia visual debil en estados
   - Alertas, botones y campos compiten en intensidad visual.
   - Los estados (warning/info/success/error) no se distinguen claramente por semantica.

3. Inconsistencia de lenguaje visual
   - Sidebar usa un lenguaje oscuro/saturado moderno.
   - Panel principal usa superficies claras suaves.
   - Las alertas parecen de otro sistema (no integradas al tema de la app).

4. Riesgo de incumplimiento WCAG (aprox.)
   - Casos observados en referencia estiman contraste por debajo de AA para texto normal (4.5:1).
   - Especialmente en warning/info con texto pastel sobre fondos pastel.

## 2) Auditoria del sistema actual

### Tokens/variables existentes
Detectado en `src/app.py` (bloque CSS embebido):
- `--primary-color`
- `--primary-hover`
- `--bg-soft`
- `--card-bg`
- `--border-color`

### Situacion actual de estilo
- No hay tokens semanticos para estados (`success/warning/error/info`).
- No existe sistema dual light/dark para alertas y badges.
- Se detectan colores hardcodeados directos (17 hex unicos) en multiples reglas.
- No hay componentes CSS reutilizables tipo `.alert-*`, `.badge-*`, `.banner-*`.
- Se usan muchas llamadas `st.success`, `st.warning`, `st.error`, `st.info`, pero sin capa de tema semantico unificada.

### Riesgos UX/UI actuales
- Fragilidad al cambiar tema global (las alertas quedan con contraste impredecible).
- Consistencia baja entre componentes (forms/buttons/sidebar/alerts).
- Escalabilidad limitada (cada nueva pantalla puede introducir nuevos hardcodes).

## 3) Propuesta de sistema de color semantico (adaptable light/dark)

## Objetivo
Definir tokens semanticos por estado con cuatro niveles de uso:
- `bg` (fondo principal del estado)
- `bg-soft` (fondo suave para banners)
- `text` (texto del estado)
- `border` (borde y acentos)

### 3.1 Paleta base neutra

Light:
- `--surface-0: #ffffff`
- `--surface-1: #f8fafc`
- `--surface-2: #eef2f7`
- `--text-strong: #0f172a`
- `--text-muted: #334155`
- `--border-subtle: #cbd5e1`

Dark:
- `--surface-0: #0b1220`
- `--surface-1: #111a2e`
- `--surface-2: #1b263d`
- `--text-strong: #e2e8f0`
- `--text-muted: #cbd5e1`
- `--border-subtle: #334155`

### 3.2 Colores semanticos recomendados

#### Light
| Estado | bg | bg-soft | text | border |
|---|---|---|---|---|
| Success | `#166534` | `#ecfdf3` | `#14532d` | `#22c55e` |
| Warning | `#b45309` | `#fff7ed` | `#7c2d12` | `#f59e0b` |
| Error | `#b91c1c` | `#fef2f2` | `#7f1d1d` | `#ef4444` |
| Info | `#1d4ed8` | `#eff6ff` | `#1e3a8a` | `#3b82f6` |
| Neutral | `#334155` | `#f8fafc` | `#1f2937` | `#94a3b8` |

#### Dark
| Estado | bg | bg-soft | text | border |
|---|---|---|---|---|
| Success | `#22c55e` | `#052e1f` | `#86efac` | `#15803d` |
| Warning | `#f59e0b` | `#3a2605` | `#fcd34d` | `#b45309` |
| Error | `#ef4444` | `#3b0a0a` | `#fca5a5` | `#b91c1c` |
| Info | `#60a5fa` | `#0b2347` | `#bfdbfe` | `#2563eb` |
| Neutral | `#94a3b8` | `#111827` | `#e2e8f0` | `#475569` |

Notas de contraste:
- Para texto normal en alertas, usar siempre `*-text` sobre `*-bg-soft`.
- Evitar texto blanco sobre `bg-soft` claros.
- Objetivo minimo: WCAG AA 4.5:1 para texto normal.

## 4) Arquitectura tecnica propuesta

### Opcion A (recomendada en este proyecto): CSS tokens centralizados
Crear `src/theme.css` (o `src/styles/theme.css`) y cargarlo desde app.

```css
:root,
[data-theme="light"] {
  --color-success-bg: #166534;
  --color-success-bg-soft: #ecfdf3;
  --color-success-text: #14532d;
  --color-success-border: #22c55e;

  --color-warning-bg: #b45309;
  --color-warning-bg-soft: #fff7ed;
  --color-warning-text: #7c2d12;
  --color-warning-border: #f59e0b;

  --color-error-bg: #b91c1c;
  --color-error-bg-soft: #fef2f2;
  --color-error-text: #7f1d1d;
  --color-error-border: #ef4444;

  --color-info-bg: #1d4ed8;
  --color-info-bg-soft: #eff6ff;
  --color-info-text: #1e3a8a;
  --color-info-border: #3b82f6;

  --color-neutral-bg: #334155;
  --color-neutral-bg-soft: #f8fafc;
  --color-neutral-text: #1f2937;
  --color-neutral-border: #94a3b8;
}

[data-theme="dark"] {
  --color-success-bg: #22c55e;
  --color-success-bg-soft: #052e1f;
  --color-success-text: #86efac;
  --color-success-border: #15803d;

  --color-warning-bg: #f59e0b;
  --color-warning-bg-soft: #3a2605;
  --color-warning-text: #fcd34d;
  --color-warning-border: #b45309;

  --color-error-bg: #ef4444;
  --color-error-bg-soft: #3b0a0a;
  --color-error-text: #fca5a5;
  --color-error-border: #b91c1c;

  --color-info-bg: #60a5fa;
  --color-info-bg-soft: #0b2347;
  --color-info-text: #bfdbfe;
  --color-info-border: #2563eb;

  --color-neutral-bg: #94a3b8;
  --color-neutral-bg-soft: #111827;
  --color-neutral-text: #e2e8f0;
  --color-neutral-border: #475569;
}
```

### Opcion B (si se migra a Tailwind a futuro)
Usar `theme.extend.colors` con namespaces:
- `semantic.success.{bg,bgSoft,text,border}`
- `semantic.warning.{bg,bgSoft,text,border}`
- etc.

> En el estado actual (Streamlit + CSS custom), Opcion A es la mas simple y mantenible.

## 5) Ejemplos de implementacion (mock)

### Alertas
```css
.alert {
  border: 1px solid;
  border-radius: 12px;
  padding: 0.75rem 0.9rem;
  font-size: 0.95rem;
  line-height: 1.4;
}

.alert-success {
  background: var(--color-success-bg-soft);
  color: var(--color-success-text);
  border-color: var(--color-success-border);
}

.alert-warning {
  background: var(--color-warning-bg-soft);
  color: var(--color-warning-text);
  border-color: var(--color-warning-border);
}

.alert-error {
  background: var(--color-error-bg-soft);
  color: var(--color-error-text);
  border-color: var(--color-error-border);
}

.alert-info {
  background: var(--color-info-bg-soft);
  color: var(--color-info-text);
  border-color: var(--color-info-border);
}
```

### Badges
```css
.badge {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  border: 1px solid;
  padding: 0.18rem 0.55rem;
  font-size: 0.75rem;
  font-weight: 600;
}

.badge-error {
  background: var(--color-error-bg-soft);
  color: var(--color-error-text);
  border-color: var(--color-error-border);
}
```

### Banners (top page)
```css
.banner-info {
  background: linear-gradient(
    135deg,
    color-mix(in srgb, var(--color-info-bg-soft) 80%, white),
    var(--color-info-bg-soft)
  );
  color: var(--color-info-text);
  border: 1px solid var(--color-info-border);
}
```

## 6) Recomendaciones de consistencia futura
- Definir una sola fuente de verdad para color semantico (tokens), no hardcodes por componente.
- Mantener la escala semantica estable: success/warning/error/info/neutral no debe variar por pantalla.
- Estandarizar estados para todos los componentes de feedback (alert, badge, toast, banner, inline hint).
- Agregar QA visual en light/dark antes de release (checklist con contraste AA).
- Evitar texto `#fff` por defecto en alertas; usar siempre token de texto por estado.
- Crear guia breve de uso: cuando usar warning vs info (no solo por color, tambien por severidad).

## 7) Plan de adopcion incremental (sin romper lo actual)
1. Crear `theme.css` con tokens semanticos y mapear solo alertas.
2. Ajustar badges y banners a tokens.
3. Reemplazar hardcodes de color gradualmente (por lotes).
4. Validar contraste y snapshot visual en light/dark.
5. Documentar patron en guia interna de UI.

---

### Resumen ejecutivo
El problema central no es un color puntual, sino la ausencia de tokens semanticos de estado. Con un sistema de tokens light/dark y clases reutilizables para alert/badge/banner, se corrige el bajo contraste observado, se unifica la jerarquia visual y se evita que futuros cambios de tema rompan legibilidad.

## Implementacion aplicada (2026-02-23)

Se implemento una segunda pasada de UI en `src/app.py` enfocada en consistencia visual de feedback y accesibilidad:

- `Tema semantico`:
  - Tokens de estado completos para light/dark (`success`, `warning`, `error`, `info`, `neutral`) con variantes `bg`, `bg-soft`, `text`, `border`.
  - Fallback automatico para dark mediante `@media (prefers-color-scheme: dark)`.

- `Alertas y notificaciones`:
  - Estilado base de `stAlert`/`notification` con bordes y contraste controlado.
  - Mapeo por severidad (`kind`) y fallback por icono (`:has(svg[aria-label=...])`) para mantener compatibilidad.
  - Texto y enlaces internos de alerta heredan color semantico para evitar texto lavado.

- `Controles y foco`:
  - Inputs/textarea/select ahora usan tokens neutros (`surface`, `text`, `border`) en vez de hardcodes.
  - Placeholder legible y consistente.
  - Focus ring unificado con token de info para mejor navegacion por teclado.
  - Soporte de estilo secundario para botones (`kind="secondary"` y selector compatible de base button).

### Verificacion de seguridad
- `python -m compileall src/app.py` -> OK
- `pytest tests/test_sanitize_links.py tests/test_restricted_numbers.py tests/test_search_contacts.py tests/test_update_contact.py` -> 5 passed
