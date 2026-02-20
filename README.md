# DATOS_CONSIGNACION

Sistema integral para la gestión de consignaciones de vehículos, optimizado para equipos comerciales. La plataforma centraliza la captación de prospectos, la administración de inventario y facilita la comunicación directa vía WhatsApp mediante plantillas personalizables.

---

## 🚀 Tecnologías y Stack

El proyecto está construido sobre un stack robusto y ligero en Python:

*   **Core**: Python 3.10+
*   **Frontend/Backend**: [Streamlit](https://streamlit.io/) (Framework reactivo para Data Apps)
*   **Base de Datos**: SQLite3 (Integrada, sin servidor)
*   **Manipulación de Datos**: Pandas
*   **Web Scraping**: Requests + BeautifulSoup4 (Extracción de datos de Chileautos)
*   **Reportes**: XlsxWriter (Excel)
*   **Utilitarios**: Urllib, Hashlib, Re (Expresiones regulares)

---

## 🏛️ Arquitectura del Sistema

La aplicación sigue un patrón de diseño monolítico basado en scripts de Streamlit, donde el flujo de ejecución se reinicia con cada interacción del usuario (Reactive Programming Model).

### Estructura de Directorios

```text
DATOS_CONSIGNACION/
├── src/
│   └── app.py            # Controlador Principal: Maneja rutas, lógica y UI.
├── data/
│   └── datos_consignacion.db  # Base de Datos SQLite (Persistencia local).
├── docs/                 # Documentación del proyecto.
├── tests/                # Pruebas unitarias e integración (Pytest).
├── run.py                # Wrapper para ejecución y compilación con PyInstaller.
├── MiAppStreamlit.spec   # Especificación para empaquetado (PyInstaller).
├── requirements.txt      # Dependencias del proyecto.
└── README.md             # Documentación general.
```

### Controladores y Enrutamiento

El archivo `src/app.py` actúa como el controlador único y router. La navegación se gestiona a través de la barra lateral (`st.sidebar`), donde la selección del usuario define qué bloque de código (Vista) se renderiza.

**Flujo Principal:**
1.  **Inicialización**: Configuración de página, estilos CSS y conexión a DB.
2.  **Autenticación**: Verificación de sesión (`st.session_state['user']`). Si no hay usuario, fuerza la vista de `Login`.
3.  **Router**: Un bloque `if-elif` evalúa la variable `page` seleccionada en el menú y llama a la función de renderizado correspondiente (ej. `render_interested_clients_page()`).

---

## 💾 Base de Datos (Esquema Relacional)

La persistencia se maneja con SQLite. Las tablas se crean automáticamente (`create_tables()`) al iniciar la aplicación si no existen.

### 1. Usuarios (`users`)
Controla el acceso y privilegios.
| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `id` | INTEGER PK | Identificador único. |
| `username` | TEXT UNIQUE | Nombre de usuario (ej. `admin`). |
| `password_hash` | TEXT | Contraseña hasheada (SHA-256). |
| `role` | TEXT | Rol: `admin` (acceso total) o `user` (limitado). |

### 2. Links Maestros (`links_contactos`)
Agrupador principal de prospectos (ej. una campaña o fuente de datos).
| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `id` | INTEGER PK | Identificador del link. |
| `link_general` | TEXT | URL o identificador de la fuente. |
| `fecha_creacion`| TEXT | Fecha de registro (YYYY-MM-DD). |
| `marca` | TEXT | Marca asociada al grupo. |
| `descripcion` | TEXT | Detalle o notas de la campaña. |
| `user_id` | INTEGER | Usuario propietario del link. |

### 3. Contactos (`contactos`)
Almacena la información de los prospectos y vehículos específicos.
| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `id` | INTEGER PK | Identificador del contacto. |
| `link_auto` | TEXT UNIQUE | URL específica del vehículo (Clave única). |
| `telefono` | TEXT | Número de contacto (normalizado al guardar). |
| `nombre` | TEXT | Nombre del prospecto. |
| `auto` | TEXT | Modelo/Versión del vehículo. |
| `precio` | REAL | Valor del vehículo. |
| `descripcion` | TEXT | Notas adicionales. |
| `id_link` | INTEGER FK | Referencia a `links_contactos`. |

### 4. Mensajes (`mensajes`)
Plantillas de texto para el envío masivo o individual de WhatsApp.
| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `id` | INTEGER PK | Identificador. |
| `descripcion` | TEXT | Cuerpo del mensaje (soporta placeholders `{nombre}`, `{auto}`). |
| `user_id` | INTEGER | Propietario de la plantilla. |

### 5. Clientes Interesados (`clientes_interesados`)
Módulo CRM ligero para seguimiento de leads calificados.
| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `id` | INTEGER PK | Identificador. |
| `fecha` | TEXT | Fecha de contacto/interés. |
| `auto` | TEXT | Vehículo de interés. |
| `numero` | TEXT | Teléfono de contacto. |
| `link` | TEXT | Enlace de referencia. |
| `correo` | TEXT | Email (opcional). |
| `user_id` | INTEGER FK | Usuario que registró el interés. |
| `created_at` | TEXT | Timestamp de creación. |

### 6. Contactos Restringidos (`contactos_restringidos`)
Lista negra para evitar contactar números bloqueados.
| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `telefono_normalizado` | TEXT PK | Número limpio (sin espacios/+56). |
| `telefono_original` | TEXT | Input original. |
| `motivo` | TEXT | Razón del bloqueo. |
| `created_by` | INTEGER FK | Admin que restringió. |

### 7. Logs de Exportación (`export_logs`)
Auditoría de generación de enlaces/contactos.
| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `contact_id` | INTEGER FK | Contacto exportado. |
| `mensaje_id` | INTEGER FK | Plantilla utilizada. |
| `link_generado` | TEXT | URL final de WhatsApp generada. |
| `fecha_exportacion` | TEXT | Timestamp del evento. |

---

## 🛠️ Instalación y Ejecución

### Requisitos
*   Python 3.8 o superior instalado.
*   Entorno virtual recomendado.

### Configuración del Entorno

1.  **Clonar/Descargar** el proyecto.
2.  **Crear entorno virtual**:
    ```bash
    python -m venv .venv
    .\.venv\Scripts\activate  # Windows
    # source .venv/bin/activate  # Linux/Mac
    ```
3.  **Instalar dependencias**:
    ```bash
    pip install -r requirements.txt
    ```

### Ejecución de la Aplicación

Existen dos modos principales:

**Modo Desarrollo (Directo Streamlit):**
```bash
streamlit run src/app.py
```

**Modo Producción (Wrapper):**
Este script asegura que las rutas relativas funcionen correctamente (útil pre-compilación).
```bash
python run.py
```

### Credenciales Iniciales
Al arrancar por primera vez, el sistema crea usuarios por defecto:
*   **Admin**: Usuario `admin` / Contraseña `admin`
*   **User**: Usuario `test` / Contraseña `test`

---

## 📦 Módulos Principales

### 1. Gestión de Links (`Crear` / `Links Contactos`)
Permite crear "carpetas" o agrupadores (Links Maestros) para organizar los contactos. Cada link tiene una marca y descripción asociada.

### 2. Captación (`Agregar Contactos`)
Incorpora datos de prospectos. Cuenta con una potente funcionalidad de **Scraping Automático**: al pegar una URL de *Chileautos*, el sistema extrae automáticamente:
*   Nombre del vehículo.
*   Año.
*   Precio.
*   Número de WhatsApp (si está público).
*   Descripción.

### 3. Sanitización (`Sanitizar Links`)
Herramienta administrativa para limpiar la base de datos.
*   Normaliza URLs (elimina parámetros de tracking).
*   Detecta y elimina duplicados basándose en la URL del vehículo.

### 4. Comunicación (`CWS Chat WhatsApp`)
Generador de enlaces `wa.me` masivos.
*   Permite seleccionar un Link Maestro y un conjunto de plantillas de mensaje.
*   Rota aleatoriamente las plantillas seleccionadas entre los contactos para evitar spam repetitivo.
*   Genera botones para abrir WhatsApp Web con un clic.

### 5. Exportación (`Ver Contactos & Exportar`)
*   Filtros avanzados por nombre, auto o teléfono.
*   Generación de reporte **Excel** con todos los datos.
*   Generación de reporte **HTML** interactivo con enlaces de WhatsApp listos para usar en móvil.

### 6. CRM (`Clientes Interesados`)
Registro manual o semiautomático (desde contactos existentes) de personas que han mostrado interés real, permitiendo un seguimiento diferenciado del "barrido" general.

---

## ⚠️ Notas de Seguridad

*   **Sanitize User Input**: El sistema implementa limpieza básica de inputs de formularios.
*   **SQL Injection**: Se utiliza parametrización de queries en todas las llamadas a SQLite para prevenir inyecciones.
*   **Roles**: El sistema distingue estrictamente entre `admin` y `user` para operaciones destructivas (sanitizar, borrar usuarios, lista negra).

---
*Documentación actualizada automáticamente por Antigravity.*
