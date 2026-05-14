# SDD: Producción en Railway con Supabase

**Proyecto**: DATOS_CONSIGNACION  
**Fecha**: 2026-04-30  
**Estado**: Propuesta / No implementado  
**Tipo**: SDD unificado (exploración + propuesta + spec + diseño + tareas + verificación)  
**Objetivo**: dejar una guía completa para migrar el proyecto a un entorno de producción accesible públicamente usando **Railway** como runtime y **Supabase Postgres** como base de datos administrada.

---

## 0. Resumen ejecutivo

Hoy la app funciona como un monolito Streamlit con persistencia local en SQLite.
Eso sirve para escritorio o uso local, pero NO es una base sana para producción pública en Railway.

Los bloqueos verificados en el repo son:

1. **Persistencia local**: la app escribe en `data/datos_consignacion.db` y en `data/multi_db_sources/`.
2. **Wrapper no cloud-ready**: `run.py` está pensado para PyInstaller/local y no para un servicio web en contenedor.
3. **Dependencias no portables a Linux**: `requirements.txt` incluye paquetes Windows-only.
4. **Seguridad insuficiente para internet**: contraseñas con SHA-256 directo y usuarios por defecto inseguros.

La decisión recomendada a futuro es:

- **Railway** para ejecutar el proceso Streamlit.
- **Supabase Postgres** para reemplazar SQLite.
- **Mantener la app de Streamlit** como backend/UI inicial.
- **NO usar Supabase Auth en la primera fase**; primero migrar datos y endurecer auth propia.
- **NO implementar nada ahora**; este documento deja el camino completo para ejecutar después.

---

## 1. Situación actual verificada

### 1.1 Arquitectura actual

El proyecto está acoplado a un único archivo principal:

- `src/app.py` → UI, routing, negocio, acceso DB, migraciones, auth.
- `run.py` → wrapper local/PyInstaller.
- `data/datos_consignacion.db` → persistencia principal.

### 1.2 Persistencia actual

Evidencia verificada:

- `src/app.py:1048-1054` define:
  - `db_dir = <runtime>/data`
  - `db_filename = <runtime>/data/datos_consignacion.db`
  - `multi_db_root_dir = <runtime>/data/multi_db_sources`
- `src/app.py:1306-1312` usa `sqlite3.connect(...)` en `get_connection()`.
- `src/app.py:1057-1228` crea y gestiona archivos `.db` adicionales y `registry.json` para la funcionalidad multi-DB.

### 1.3 Arranque actual

Evidencia verificada:

- `run.py:8` fija `_PORT = 8501`.
- `run.py:19-23` abre navegador local.
- `run.py:60-65` ejecuta `streamlit run ...` sin usar `$PORT`.

Conclusión: `run.py` sirve para escritorio/local, NO como contrato de arranque cloud en Railway.

### 1.4 Seguridad actual

Evidencia verificada:

- `src/app.py:1987-1988`:

```python
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()
```

- `src/app.py:2053-2067` crea usuarios por defecto:
  - `admin/admin`
  - `superadmin/superadmin`
  - `test/test`

Conclusión: eso NO es aceptable para una instancia pública.

### 1.5 Portabilidad de dependencias

Evidencia verificada:

- `requirements.txt` contiene `pywin32==308` y `WMI==1.5.1`.

Conclusión: el build Linux de Railway puede fallar o quedar contaminado con dependencias irrelevantes.

---

## 2. Problema a resolver

Se necesita que la aplicación pueda ser usada por terceros a través de internet con un despliegue estable, persistente y mantenible.

### Problemas de la solución actual para ese objetivo

| Área | Situación actual | Riesgo en producción |
|---|---|---|
| Runtime | Streamlit monolítico ejecutado como script local | Baja trazabilidad operativa |
| Base de datos | SQLite en disco local | Riesgo de corrupción, bloqueo y mala escalabilidad |
| Infraestructura | Sin contrato cloud explícito | Deploy frágil |
| Seguridad | SHA-256 simple + usuarios default | Compromiso de credenciales |
| Multiusuario | SQLite concurrente | Limitado para acceso real concurrente |
| Secretos | Sin estrategia formal de secretos server-side | Riesgo de exposición |

---

## 3. Objetivos

### 3.1 Objetivos funcionales

1. Publicar la app en internet desde Railway.
2. Reemplazar SQLite por Supabase Postgres.
3. Conservar el comportamiento funcional principal de la app.
4. Permitir persistencia estable sin depender del filesystem del contenedor.
5. Mantener login por usuario/rol en la primera etapa.

### 3.2 Objetivos no funcionales

1. Evitar pérdida de datos en reinicios/redeploys.
2. Mejorar seguridad de contraseñas y credenciales iniciales.
3. Reducir dependencia de particularidades de Windows.
4. Dejar una base lista para evolución futura.
5. Tener una ruta de rollback razonable durante la migración.

### 3.3 No objetivos

1. Reescribir la app en otro framework.
2. Separar frontend y backend en esta primera iniciativa.
3. Implementar Supabase Auth de entrada.
4. Resolver ahora scraping avanzado/DataDome.
5. Implementar CI/CD completo en esta fase documental.

---

## 4. Decisión propuesta

### 4.1 Decisión principal

La opción recomendada es:

**Railway + Streamlit + conexión directa a Supabase Postgres**.

### 4.2 Por qué esta opción

Porque equilibra velocidad, costo y riesgo:

- Railway resuelve el hosting del proceso web.
- Supabase resuelve persistencia administrada, backups y Postgres real.
- Streamlit se mantiene, evitando una reescritura total.
- Se elimina el principal problema operativo: depender de SQLite en disco local.

### 4.3 Decisiones técnicas derivadas

1. **La app NO debe seguir usando SQLite en producción.**
2. **La app debe conectarse a Postgres como backend server-side**, no desde el navegador.
3. **La conexión recomendada en Railway debe ser por cadena Postgres con SSL**.
4. **Para cliente persistente**, usar el **pooler en session mode** de Supabase cuando corresponda.
5. **Supabase Auth queda fuera de la primera fase**.
6. **RLS no es obligatoria en fase 1** si la app sólo usa conexión backend privada; si luego se expone Data API/Auth, ahí sí debe diseñarse RLS formalmente.

---

## 5. Alternativas evaluadas

### Opción A — Railway + SQLite + volumen

**Ventaja**: implementación más rápida.  
**Desventaja**: conserva el cuello de botella arquitectónico principal y limita la concurrencia real.

**Veredicto**: útil como parche temporal, NO como destino objetivo.

### Opción B — Railway + Supabase Postgres (**RECOMENDADA**)

**Ventaja**: persistencia real, backups, mejor concurrencia, camino más profesional.  
**Desventaja**: exige migrar capa de acceso a datos y SQL específico de SQLite.

**Veredicto**: mejor inversión para producción.

### Opción C — Reescritura completa antes de salir

**Ventaja**: arquitectura más limpia.  
**Desventaja**: costo, tiempo y riesgo desproporcionados.

**Veredicto**: descartada para esta etapa.

---

## 6. Requisitos tipo spec

### RQ-01 — Runtime cloud válido

La aplicación debe poder arrancar en Railway como servicio HTTP público usando un comando de inicio compatible con variable `PORT`.

**Escenario**
- **Dado** un deploy de Railway
- **Cuando** el contenedor inicie
- **Entonces** Streamlit debe escuchar en `0.0.0.0:$PORT`
- **Y** Railway debe poder publicar el dominio público

### RQ-02 — Persistencia desacoplada del contenedor

La aplicación no debe depender del filesystem del contenedor para su base transaccional principal.

**Escenario**
- **Dado** un redeploy o reinicio del servicio
- **Cuando** la app vuelva a iniciar
- **Entonces** los datos deben seguir íntegros

### RQ-03 — Reemplazo de SQLite por Postgres

La aplicación debe migrar su almacenamiento principal desde SQLite a Postgres administrado por Supabase.

**Escenario**
- **Dado** una tabla actual en SQLite
- **Cuando** se complete la migración
- **Entonces** su equivalente debe existir en Supabase con constraints y tipos compatibles

### RQ-04 — Conservación funcional

Los módulos críticos deben seguir funcionando:

- autenticación
- links/contactos
- mensajes
- clientes interesados
- restricciones
- exportaciones
- administración de usuarios

### RQ-05 — Endurecimiento de autenticación

La app no debe usar contraseñas con SHA-256 simple ni credenciales por defecto públicas.

**Escenario**
- **Dado** un ambiente productivo nuevo
- **Cuando** se provisiona el primer usuario administrador
- **Entonces** la contraseña debe almacenarse con hash fuerte
- **Y** no deben existir credenciales default reutilizables

### RQ-06 — Compatibilidad Linux/Railway

El proyecto debe poder instalar dependencias en Railway/Linux sin fallar por paquetes Windows-only.

### RQ-07 — Secretos externos

Las credenciales de BD y cualquier secreto sensible deben vivir en variables de entorno del servicio, no hardcodeadas en el repo.

### RQ-08 — Observabilidad básica

El deploy debe dejar trazabilidad mínima en logs para:

- arranque
- conexión DB
- migración
- fallos de autenticación
- errores de scraping / exportación críticos

---

## 7. Diseño técnico propuesto

## 7.1 Arquitectura objetivo

```text
Usuario final
   │
   ▼
Dominio público Railway
   │
   ▼
Servicio Streamlit (Railway)
   │
   ├── UI + lógica de negocio
   ├── autenticación interna endurecida
   ├── capa de acceso a datos compatible con Postgres
   │
   ▼
Supabase Postgres
   ├── tablas de negocio
   ├── backups administrados
   └── pooler / conexión SSL
```

## 7.2 Principio clave de diseño

NO conviene intentar “cambiar `sqlite3.connect()` por Postgres y listo”.
Eso sería una mala decisión porque el problema no es sólo la conexión, sino el **acople a SQL y comportamientos de SQLite** dentro de `src/app.py`.

### Qué está acoplado hoy

1. Placeholders `?` en queries.
2. `sqlite3` como API base.
3. `PRAGMA foreign_keys = ON`.
4. DDL y defaults pensados para SQLite.
5. funciones y expresiones específicas (`typeof`, blobs legacy, etc.).
6. `create_function("normalize_phone", ...)`.

Conclusión: la migración correcta requiere una **capa de acceso a datos explícita**.

## 7.3 Estrategia de acceso a datos recomendada

### Decisión

Crear una capa nueva de infraestructura DB y mover gradualmente el acceso desde `src/app.py`.

### Recomendación concreta

- **Usar SQLAlchemy + driver Postgres (`psycopg`)** para la nueva capa.

### Por qué

Tradeoff real:

- **Seguir con `sqlite3`-style puro** implicaría reescribir manualmente muchas queries y placeholders.
- **SQLAlchemy Core/Engine** permite una transición más ordenada y deja puerta abierta a testear mejor.
- **No hace falta usar ORM completo**; alcanza con capa de engine + consultas explícitas.

### Regla de migración

Primero mover infraestructura y consultas críticas. Después refactorizar módulos secundarios.

## 7.4 Estrategia de autenticación

### Fase 1 recomendada

Mantener la tabla `users` dentro de la base de negocio, PERO:

1. reemplazar SHA-256 por **bcrypt o Argon2**;
2. eliminar creación automática de usuarios inseguros;
3. crear bootstrap controlado del primer admin por variable de entorno o script manual;
4. mantener roles `user`, `admin`, `superadmin` si siguen siendo funcionalmente válidos.

### Por qué NO usar Supabase Auth de entrada

Porque meter dos cambios grandes a la vez sería mala disciplina:

1. migración SQLite → Postgres,
2. rediseño de auth.

Eso mezcla demasiadas variables y complica el rollback.

### Fase futura opcional

Evaluar Supabase Auth si luego se decide:

- separar frontend/backend,
- exponer APIs,
- o delegar login/recuperación de contraseña a Supabase.

## 7.5 Estrategia de datos

### Tablas esperables a migrar

Según README y `src/app.py`, al menos:

- `users`
- `links_contactos`
- `contactos`
- `mensajes`
- `clientes_interesados`
- `contactos_restringidos`
- `contactos_restringidos_link`
- `contactos_restringidos_contacto`
- `export_logs`

### Consideraciones de migración

1. Revisar tipos `TEXT`, `REAL`, `INTEGER`, timestamps y defaults.
2. Reemplazar `AUTOINCREMENT` por `GENERATED ... AS IDENTITY` o `BIGSERIAL` según decisión futura.
3. Revisar unicidad real de `link_auto` y normalización previa.
4. Revisar blobs legacy en `id_link` documentados por la app.
5. Redefinir índices para búsquedas frecuentes.

## 7.6 Estrategia multi-DB / superadmin

La funcionalidad actual de múltiples archivos `.db` NO debe migrarse tal cual a producción Supabase.

### Decisión recomendada

Con Supabase, la estrategia sana es:

- **una sola base Postgres principal**,
- multi-tenancy lógica si realmente hiciera falta en el futuro,
- o aislamiento por tablas/columnas/entidades, NO por archivos `.db` subidos por UI.

### Implicancia

La feature actual de `data/multi_db_sources/` debe tratarse como una capacidad histórica/local, no como patrón target de producción web.

## 7.7 Estrategia de Railway

### Contrato de arranque esperado

Railway debe iniciar con algo equivalente a:

```bash
streamlit run src/app.py --server.port=$PORT --server.address=0.0.0.0
```

### Configuración recomendada

- Public networking habilitado.
- Healthcheck sobre `/_stcore/health`.
- Variables de entorno para DB y bootstrap.
- Sin dependencia del volumen para la base principal.

### Nota importante

Con Supabase, el volumen de Railway deja de ser crítico para la BD.
Podría seguir siendo útil sólo para archivos temporales o assets operativos, pero NO como almacenamiento transaccional principal.

## 7.8 Variables de entorno previstas

Variables recomendadas para documentar e implementar a futuro:

```text
APP_ENV=production
APP_BASE_URL=https://<dominio-publico>

DATABASE_URL=<supabase pooled connection string with ssl>
DATABASE_DIRECT_URL=<supabase direct connection string optional>

BOOTSTRAP_ADMIN_USERNAME=<solo para provision inicial controlado>
BOOTSTRAP_ADMIN_PASSWORD=<solo para provision inicial controlado>

DISABLE_DEFAULT_USERS=true
PASSWORD_HASH_SCHEME=bcrypt
```

Opcionales:

```text
SUPABASE_URL=<si luego se usa storage/auth/api>
SUPABASE_ANON_KEY=<solo si hiciera falta desde cliente>
SUPABASE_SERVICE_ROLE_KEY=<solo backend y con máximo cuidado>
```

### Regla de seguridad

Si la app se conecta directo a Postgres como backend server-side, **no necesita** exponer `SUPABASE_ANON_KEY` al navegador para la operación core.

## 7.9 Observabilidad y operación

Mínimos recomendados:

1. log claro al arrancar app;
2. log claro cuando falla conexión a DB;
3. log de bootstrap admin;
4. log de errores de migración;
5. log de operaciones críticas fallidas.

No hace falta sobrediseñar observabilidad en fase 1, pero sí dejar trazabilidad útil.

---

## 8. Impacto esperado en el código

## 8.1 Áreas más afectadas

| Área | Archivo actual | Tipo de cambio esperado |
|---|---|---|
| Runtime/start | `run.py` / config Railway | Alto |
| DB bootstrap | `src/app.py` | Alto |
| Auth | `src/app.py` | Alto |
| Queries y repositorios | `src/app.py` | Muy alto |
| Exportaciones | `src/app.py` | Medio |
| Multi-DB local | `src/app.py` | Medio/Alto |
| Dependencias | `requirements.txt` | Medio |

## 8.2 Refactor estructural recomendado

Antes o durante la migración, conviene partir `src/app.py` conceptualmente en:

- `db/connection.py`
- `db/migrations.py`
- `services/auth.py`
- `services/contacts.py`
- `services/export.py`
- `ui/...` o helpers de render

No porque “queda lindo”, sino porque intentar migrar Postgres dentro del monolito de 4000+ líneas aumenta el riesgo de romper producción.

---

## 9. Plan de migración por fases

## Fase 0 — Preparación y hardening

Objetivo: dejar el repo listo para poder migrar sin improvisación.

Incluye:

1. limpiar dependencias Windows-only o condicionarlas por plataforma;
2. definir contrato de arranque Railway;
3. introducir configuración por variables de entorno;
4. desactivar usuarios por defecto en producción;
5. definir hash fuerte para contraseñas nuevas.

## Fase 1 — Abstracción de acceso a datos

Objetivo: dejar de depender de `sqlite3` directamente en la lógica principal.

Incluye:

1. extraer conexión DB;
2. encapsular operaciones críticas;
3. identificar SQL específico de SQLite;
4. preparar capa compatible con Postgres.

## Fase 2 — Diseño y creación del esquema en Supabase

Objetivo: tener una base Postgres funcionalmente equivalente.

Incluye:

1. modelado de tablas;
2. constraints e índices;
3. estrategia de migración de datos existentes;
4. scripts de carga inicial.

## Fase 3 — Migración de autenticación

Objetivo: llevar `users` a un esquema seguro.

Incluye:

1. hash fuerte;
2. bootstrap admin controlado;
3. transición de credenciales existentes si aplica;
4. bloqueo de defaults inseguros.

## Fase 4 — Conmutación de app a Supabase Postgres

Objetivo: ejecutar la app contra Postgres en un entorno de prueba y luego producción.

Incluye:

1. pruebas funcionales;
2. deploy a Railway;
3. smoke tests;
4. observación inicial.

## Fase 5 — Limpieza post-migración

Objetivo: retirar deuda técnica y comportamiento legado innecesario.

Incluye:

1. eliminar rutas exclusivas de SQLite si ya no tienen sentido;
2. redefinir o desactivar multi-DB por archivo;
3. consolidar documentación operativa.

---

## 10. Checklist de tareas futuras

## 10.1 Infraestructura

- [ ] Crear proyecto Supabase.
- [ ] Definir región y política de backups.
- [ ] Crear servicio Railway conectado al repo.
- [ ] Configurar dominio público y healthcheck.
- [ ] Definir variables de entorno del servicio.

## 10.2 Base de datos

- [ ] Inventariar todas las tablas y constraints reales del SQLite actual.
- [ ] Diseñar esquema Postgres equivalente.
- [ ] Crear migraciones SQL iniciales.
- [ ] Diseñar estrategia de importación de datos existentes.
- [ ] Validar índices de lectura/escritura.

## 10.3 Aplicación

- [ ] Extraer módulo de conexión DB.
- [ ] Introducir configuración por entorno.
- [ ] Reemplazar llamadas directas a `sqlite3`.
- [ ] Adaptar queries incompatibles con Postgres.
- [ ] Adaptar manejo de errores transaccionales.

## 10.4 Seguridad

- [ ] Reemplazar SHA-256 por bcrypt/Argon2.
- [ ] Desactivar creación automática de `admin/admin`, `superadmin/superadmin`, `test/test`.
- [ ] Diseñar bootstrap seguro del primer admin.
- [ ] Revisar manejo de secretos y permisos.

## 10.5 Calidad

- [ ] Agregar tests para capa DB desacoplada.
- [ ] Agregar tests de autenticación.
- [ ] Agregar pruebas de exportación contra Postgres.
- [ ] Ejecutar smoke tests post-deploy.

## 10.6 Documentación

- [ ] Crear guía operativa de deploy Railway.
- [ ] Crear guía operativa Supabase.
- [ ] Registrar estrategia de rollback.
- [ ] Actualizar README principal cuando se implemente.

---

## 11. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Migración subestimada por acople a SQLite | Alto | extraer capa DB antes de conmutar |
| Queries incompatibles con Postgres | Alto | inventario + refactor gradual |
| Fallo de build en Railway | Medio | limpiar `requirements.txt` antes |
| Exposición por usuarios default | Crítico | bloquear defaults y bootstrap seguro |
| Hash débil heredado | Alto | migración a bcrypt/Argon2 |
| Feature multi-DB no encaja con target | Medio | redefinir alcance para web productiva |
| Datos legacy inconsistentes | Alto | script de validación previo a importación |

---

## 12. Estrategia de verificación futura

## 12.1 Verificación técnica mínima

1. La app arranca en Railway usando `$PORT`.
2. El login funciona contra Supabase Postgres.
3. CRUD de usuarios/contactos/links/mensajes sigue operativo.
4. Exportaciones siguen generando archivos correctos.
5. No se crean usuarios default inseguros.

## 12.2 Smoke tests sugeridos

1. abrir dominio público;
2. iniciar sesión con admin real;
3. crear contacto;
4. editar contacto;
5. exportar reporte;
6. reiniciar deploy y verificar persistencia.

## 12.3 Criterios de aceptación

La migración se considera exitosa cuando:

- la app queda públicamente accesible;
- la persistencia depende de Supabase, no del disco local;
- la autenticación deja de usar defaults y hash débil;
- el flujo funcional principal sigue íntegro.

---

## 13. Estrategia de rollback

Si la migración falla durante la implementación futura:

1. mantener una copia íntegra del SQLite original;
2. no destruir datos ni credenciales previas hasta validar Postgres;
3. habilitar despliegue de contingencia apuntando temporalmente a la versión anterior;
4. ejecutar rollback por release, no por edición manual de emergencia.

Principio: **no cortar la rama donde estás parado**. Primero validás el puente nuevo; recién después soltás el viejo.

---

## 14. Preguntas abiertas

1. ¿Se mantendrá el modelo de roles actual tal cual, o habrá rediseño?
2. ¿La funcionalidad multi-DB debe sobrevivir como feature productiva o sólo como herramienta de migración/admin?
3. ¿Se quiere preservar compatibilidad local con SQLite para desarrollo, o converger todo a Postgres?
4. ¿Se migrarán contraseñas existentes en lote o se forzará reseteo?
5. ¿Habrá una sola instancia para todos o segmentación futura por tenant/empresa?

---

## 15. Recomendación final

La decisión correcta a futuro NO es “subir el proyecto tal como está a Railway”.
Eso sería patear el problema para adelante.

La ruta profesional es:

1. endurecer runtime y seguridad;
2. abstraer acceso a datos;
3. migrar a Supabase Postgres;
4. recién ahí abrirlo al público de forma estable.

Si se implementa este plan, el proyecto pasa de una app local funcional a una base razonable para producción real.

---

## 16. Archivos y documentos relacionados

### Del repo actual

- `README.md`
- `docs/README.md`
- `src/app.py`
- `run.py`
- `requirements.txt`
- `.streamlit/config.toml`
- `.gitignore`

### Documentos relacionados existentes

- `docs/plans/multidb-selector-analysis.md`
- `docs/plans/scraping-datadome-roadmap.md`

### Referencias externas verificadas durante el análisis

- Railway Volumes docs
- Railway Public Networking docs
- Railway Config as Code docs
- Railway Build and Start Commands docs
- Supabase docs: conexión a Postgres, SSL y pooler

---

## 17. Nota de alcance

Este documento **NO implementa** cambios.
Su propósito es dejar una especificación operativa y arquitectónica completa para que la migración pueda ejecutarse más adelante con criterio, no a los ponchazos.
