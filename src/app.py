import streamlit as st
import sqlite3
import pandas as pd
import datetime
from io import BytesIO
import requests
from bs4 import BeautifulSoup
import re
import urllib.parse
import os
import hashlib

# =============================================================================
# CONFIGURACIÓN BÁSICA Y ESTILOS
# =============================================================================
st.markdown("""
    <style>
    .stApp {
        max-width: 1200px;
        margin: auto;
    }
    input, textarea {
        font-size: 1.1em;
    }
    </style>
    """, unsafe_allow_html=True)

# Evitar envío de formularios con Enter
disable_enter_js = """
<script>
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('input').forEach(input => {
    input.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') { e.preventDefault(); }
    });
  });
});
</script>
"""
st.markdown(disable_enter_js, unsafe_allow_html=True)

if 'user' not in st.session_state:
    st.session_state['user'] = None

# =============================================================================
# CONEXIÓN A LA BASE DE DATOS Y CREACIÓN DE TABLAS
# =============================================================================
db_filename = os.path.join('data', 'datos_consignacion.db')

def get_connection():
    """Retorna una nueva conexión a la base de datos."""
    os.makedirs('data', exist_ok=True)
    return sqlite3.connect(db_filename, check_same_thread=False)

# -----------------------------------------------------------------------------
# MIGRACIÓN DE LA TABLA CONTACTOS
# -----------------------------------------------------------------------------
def migrate_contactos_schema():
    """Ajusta la tabla contactos si el esquema anterior tenia restricciones incorrectas."""
    with get_connection() as con:
        cur = con.cursor()
        # Verificar si la tabla existe
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='contactos'")
        if not cur.fetchone():
            return

        # Obtener definición SQL de la tabla
        cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='contactos'")
        row = cur.fetchone()
        if not row:
            return
        table_sql = row[0].upper()

        telefono_unique = (
            re.search(r"TELEFONO\s+TEXT\s+UNIQUE", table_sql) or
            "UNIQUE(\"TELEFONO\"" in table_sql
        )
        link_auto_unique = (
            re.search(r"LINK_AUTO\s+TEXT\s+UNIQUE", table_sql) or
            "UNIQUE(\"LINK_AUTO\"" in table_sql
        )

        if telefono_unique or not link_auto_unique:
            cur.execute("ALTER TABLE contactos RENAME TO contactos_old")
            cur.execute(
                """
                CREATE TABLE contactos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    link_auto TEXT UNIQUE NOT NULL,
                    telefono TEXT NOT NULL,
                    nombre TEXT NOT NULL,
                    auto TEXT NOT NULL,
                    precio REAL NOT NULL,
                    descripcion TEXT NOT NULL,
                    id_link INTEGER,
                    FOREIGN KEY (id_link) REFERENCES links_contactos(id)
                )
                """
            )
            cur.execute(
                """
                INSERT OR IGNORE INTO contactos (id, link_auto, telefono, nombre, auto, precio, descripcion, id_link)
                SELECT id, link_auto, telefono, nombre, auto, precio, descripcion, id_link
                FROM contactos_old
                """
            )
            cur.execute("DROP TABLE contactos_old")
            con.commit()

def migrate_user_schema():
    """Crea tabla de usuarios y agrega columnas user_id."""
    with get_connection() as con:
        cur = con.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL
            )
            """
        )
        cur.execute("PRAGMA table_info(links_contactos)")
        cols = [r[1] for r in cur.fetchall()]
        if "user_id" not in cols:
            cur.execute("ALTER TABLE links_contactos ADD COLUMN user_id INTEGER")

        cur.execute("PRAGMA table_info(mensajes)")
        cols = [r[1] for r in cur.fetchall()]
        if "user_id" not in cols:
            cur.execute("ALTER TABLE mensajes ADD COLUMN user_id INTEGER")

        con.commit()

def create_tables():
    """Crea las tablas necesarias si no existen."""
    with get_connection() as con:
        cursor = con.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL
            )
            """
        )
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS links_contactos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link_general TEXT NOT NULL,
                fecha_creacion TEXT NOT NULL,
                marca TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                user_id INTEGER
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contactos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link_auto TEXT UNIQUE NOT NULL,
                telefono TEXT NOT NULL,
                nombre TEXT NOT NULL,
                auto TEXT NOT NULL,
                precio REAL NOT NULL,
                descripcion TEXT NOT NULL,
                id_link INTEGER,
                FOREIGN KEY (id_link) REFERENCES links_contactos(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mensajes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                descripcion TEXT NOT NULL,
                user_id INTEGER
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS export_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER NOT NULL,
                mensaje_id INTEGER NOT NULL,
                link_generado TEXT NOT NULL,
                fecha_exportacion TEXT NOT NULL,
                FOREIGN KEY (contact_id) REFERENCES contactos(id),
                FOREIGN KEY (mensaje_id) REFERENCES mensajes(id)
            )
        ''')
        con.commit()



def read_query(query, params=None):
    """Ejecuta una consulta SQL y retorna un DataFrame."""
    with get_connection() as con:
        return pd.read_sql_query(query, con, params=params)

# =============================================================================
# FUNCIONES DE USUARIOS
# =============================================================================
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def create_user(username: str, password: str, role: str = "user"):
    """Crea un nuevo usuario y retorna su id."""
    with get_connection() as con:
        cur = con.cursor()
        cur.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username.strip(), hash_password(password), role),
        )
        con.commit()
        return cur.lastrowid


def authenticate_user(username: str, password: str):
    """Retorna el usuario si las credenciales son correctas."""
    with get_connection() as con:
        cur = con.cursor()
        cur.execute(
            "SELECT id, role FROM users WHERE username=? AND password_hash=?",
            (username.strip(), hash_password(password)),
        )
        row = cur.fetchone()
        if row:
            return {"id": row[0], "role": row[1]}
    return None


def delete_user(user_id: int):
    with get_connection() as con:
        con.execute("DELETE FROM users WHERE id=?", (user_id,))
        con.commit()


def ensure_default_users():
    """Crea un usuario administrador y uno de prueba si no existen."""
    with get_connection() as con:
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE role='admin'")
        admin_count = cur.fetchone()[0]
        if admin_count == 0:
            cur.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                ("admin", hash_password("admin"), "admin"),
            )
            cur.execute(
                "INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                ("test", hash_password("test"), "user"),
            )
        con.commit()

migrate_contactos_schema()
migrate_user_schema()
create_tables()
ensure_default_users()

# =============================================================================
# FUNCIONES DE SCRAPING
# =============================================================================
def extract_whatsapp_number(soup):
    """
    Extrae el número de WhatsApp de un enlace en la página.
    
    Parámetros:
    - soup (BeautifulSoup): Objeto BeautifulSoup con el contenido HTML parseado.
    
    Retorna:
    - str: Número de WhatsApp sin el prefijo "56" si se encuentra, de lo contrario None.
    """
    whatsapp_link = soup.find("a", href=re.compile(r"https://wa\.me/56\d{9}"))
    if whatsapp_link:
        match = re.search(r"https://wa\.me/56(\d{9})", whatsapp_link["href"])
        if match:
            return match.group(1)  # Extrae solo los 9 dígitos sin el prefijo "56"
    return None

def scrape_vehicle_details(url):
    """Extrae detalles de un vehículo desde la URL dada."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://www.chileautos.cl/'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            st.error(f"Error al obtener la página: {response.status_code}")
            return None
    except requests.RequestException as e:
        st.error(f"Error de conexión: {e}")
        return None
    soup = BeautifulSoup(response.content, "html.parser")
    
    # --- Extracción del número de WhatsApp ---
    whatsapp_number = extract_whatsapp_number(soup)

    # Extraer datos del vehículo
    nombre, anio, precio = None, None, None
    vehiculo_elem = soup.find("div", class_="features-item-value-vehculo")
    if vehiculo_elem:
        texto_vehiculo = vehiculo_elem.get_text(strip=True)
        partes = texto_vehiculo.split(" ", 1)
        if partes and partes[0].isdigit() and len(partes[0]) == 4:
            anio = partes[0]
            nombre = partes[1] if len(partes) > 1 else ""
        else:
            nombre = texto_vehiculo
    if not nombre:
        h1_elem = soup.find("h1")
        if h1_elem:
            titulo_texto = h1_elem.get_text(strip=True)
            partes = titulo_texto.split(" ", 1)
            if partes and partes[0].isdigit() and len(partes[0]) == 4:
                anio = partes[0]
                nombre = partes[1] if len(partes) > 1 else titulo_texto
            else:
                nombre = titulo_texto
    nombre_completo = f"{anio} {nombre}" if anio else nombre
    precio_elem = soup.find("div", class_="features-item-value-precio")
    if precio_elem:
        precio_texto = precio_elem.get_text(strip=True)
        match = re.search(r"\$(\d{1,3}(?:,\d{3})+)", precio_texto)
        precio = match.group(1) if match else precio_texto
    descripcion = "No disponible"
    descripcion_container = soup.find("div", class_="view-more-container")
    if descripcion_container:
        view_more_target = descripcion_container.find("div", class_="view-more-target")
        if view_more_target:
            p_elem = view_more_target.find("p")
            if p_elem:
                descripcion = p_elem.get_text(strip=True)
    return {
        "nombre": nombre_completo if nombre_completo else "No disponible",
        "anio": anio if anio else "No disponible",
        "precio": precio if precio else "No disponible",
        "descripcion": descripcion,
        "whatsapp_number": whatsapp_number if whatsapp_number else "No disponible",
    }

# =============================================================================
# FUNCIONES DE ACTUALIZACIÓN Y ELIMINACIÓN EN LA BASE DE DATOS
# =============================================================================
def update_link_record(
    link_id,
    new_link_general,
    new_fecha,
    new_marca,
    new_descripcion,
    new_user_id=None,
):
    """Actualiza un registro en la tabla links_contactos."""
    try:
        with get_connection() as con:
            cursor = con.cursor()
            cursor.execute(
                """
                UPDATE links_contactos
                SET link_general = ?, fecha_creacion = ?, marca = ?, descripcion = ?,
                    user_id = COALESCE(?, user_id)
                WHERE id = ?
                """,
                (
                    new_link_general.strip(),
                    new_fecha.strftime("%Y-%m-%d"),
                    new_marca.strip(),
                    new_descripcion.strip(),
                    new_user_id,
                    link_id,
                ),
            )
            con.commit()
            return True
    except sqlite3.Error as e:
        st.error(f"Error al actualizar link: {e}")
        return False

def update_contact(contact_id, link_auto, telefono, nombre, auto, precio, descripcion):
    """Actualiza un registro en la tabla contactos, limpiando el campo teléfono."""
    try:
        with get_connection() as con:
            cursor = con.cursor()
            telefono = "".join(telefono.split())
            link_auto = "".join(link_auto.split())
            cursor.execute(
                """
                UPDATE contactos
                SET link_auto = ?, telefono = ?, nombre = ?, auto = ?, precio = ?, descripcion = ?
                WHERE id = ?
                """,
                (
                    link_auto,
                    telefono,
                    nombre.strip(),
                    auto.strip(),
                    float(precio),
                    descripcion.strip(),
                    contact_id,
                ),
            )
            con.commit()
            return True
    except Exception as e:
        st.error(f"Error al actualizar el contacto: {e}")
        return False

def delete_link_record(link_id):
    """Elimina un registro de la tabla links_contactos."""
    try:
        with get_connection() as con:
            con.execute("DELETE FROM links_contactos WHERE id = ?", (link_id,))
            con.commit()
            return True
    except Exception as e:
        st.error(f"Error al eliminar el link: {e}")
        return False

def delete_contact(contact_id):
    """Elimina un registro de la tabla contactos."""
    try:
        with get_connection() as con:
            cursor = con.cursor()
            cursor.execute("DELETE FROM contactos WHERE id = ?", (contact_id,))
            con.commit()
            return True
    except Exception as e:
        st.error(f"Error al eliminar el contacto: {e}")
        return False

# =============================================================================
# FUNCIONES PARA MANEJO DE MENSAJES
# =============================================================================
def add_message(texto, user_id=1):
    """Agrega un nuevo mensaje y retorna su id."""
    try:
        with get_connection() as con:
            cur = con.cursor()
            cur.execute(
                "INSERT INTO mensajes (descripcion, user_id) VALUES (?, ?)",
                (texto.strip(), user_id),
            )
            con.commit()
            return cur.lastrowid
    except Exception as e:
        st.error(f"Error al agregar mensaje: {e}")
        return None


def update_message(msg_id, nuevo_texto):
    """Actualiza el texto de un mensaje."""
    try:
        with get_connection() as con:
            cur = con.cursor()
            cur.execute(
                "UPDATE mensajes SET descripcion = ? WHERE id = ?",
                (nuevo_texto.strip(), msg_id),
            )
            con.commit()
            return cur.rowcount > 0
    except Exception as e:
        st.error(f"Error al actualizar el mensaje: {e}")
        return False


def delete_message(msg_id):
    """Elimina un mensaje por id."""
    try:
        with get_connection() as con:
            cur = con.cursor()
            cur.execute("DELETE FROM mensajes WHERE id = ?", (msg_id,))
            con.commit()
            return cur.rowcount > 0
    except Exception as e:
        st.error(f"Error al eliminar el mensaje: {e}")
        return False

# =============================================================================
# FUNCION: GENERAR ARCHIVO HTML
# =============================================================================
def apply_template(template, contacto):
    """Reemplaza los marcadores de la plantilla con los datos del contacto."""
    def repl(match):
        key = match.group(1)
        return str(contacto.get(key, match.group(0)))
    return re.sub(r"{(.*?)}", repl, template)


def generate_html(df, message_template):
    """Genera un archivo HTML con enlaces de WhatsApp.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame con los contactos a exportar.
    message_template : str | Sequence[str]
        Plantilla(s) de mensaje a rotar para cada contacto.
    """
    if isinstance(message_template, str):
        templates = [message_template]
    else:
        templates = list(message_template)
    timestamp = datetime.datetime.now().strftime("%d-%m-%Y_%H%M")
    html_lines = [
        "<html>",
        "<head>",
        "<title>Enlaces</title>",
        "</head>",
        "<body>",
        f"<h1>REPORTE {timestamp}</h1>"
    ]
    for idx, (_, row) in enumerate(df.iterrows(), start=1):
        telefono = "".join(str(row.get("telefono", "")).split())
        contacto = row.get("auto") or row.get("nombre", "")
        template = templates[(idx - 1) % len(templates)]
        personalizado = apply_template(template, row.to_dict())
        encoded = urllib.parse.quote(personalizado)
        link = f"https://wa.me/56{telefono}?text={encoded}"
        html_lines.append(f'<a href="{link}">CONTACTO {idx}</a> {contacto}<br>')
    html_lines.extend(["</body>", "</html>"])
    file_name = f"REPORTE_{timestamp}.html"
    return "\n".join(html_lines).encode("utf-8"), file_name

# =============================================================================
# INTERFAZ DE USUARIO: MENÚ Y NAVEGACIÓN
# =============================================================================
if 'page' not in st.session_state:
    st.session_state.page = "Login" if st.session_state['user'] is None else "Crear Link Contactos"

st.sidebar.title("Navegación")

if st.session_state['user'] is None:
    menu_options = ("Login",)
else:
    menu_options = (
        "Crear Link Contactos",
        "Links Contactos",
        "Agregar Contactos",
        "Ver Contactos & Exportar",
        "Mensajes",
        "Editar",
    )
    if st.session_state['user']['role'] == 'admin':
        menu_options += ("Admin Usuarios",)

default_index = menu_options.index(st.session_state.page) if st.session_state.page in menu_options else 0
page = st.sidebar.radio("Ir a:", menu_options, index=default_index)
st.session_state.page = page

if st.session_state['user']:
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.user = None
        st.session_state.page = "Login"
        st.rerun()

# =============================================================================
# PÁGINA: LOGIN
# =============================================================================
if page == "Login":
    st.title("Iniciar Sesión")
    with st.form("login_form"):
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        submit_login = st.form_submit_button("Entrar")
    if submit_login:
        user = authenticate_user(username, password)
        if user:
            st.session_state.user = user
            st.success("Autenticado")
            st.session_state.page = "Crear Link Contactos"
            st.rerun()
        else:
            st.error("Credenciales inválidas")

# =============================================================================
# PÁGINA: CREAR LINK CONTACTOS
# =============================================================================
if page == "Crear Link Contactos":
    st.title("Crear Link Contactos")
    with st.form("crear_link_form"):
        link_general = st.text_input("Link General")
        fecha_creacion = st.date_input("Fecha de Creación", value=datetime.date.today())
        marca = st.text_input("Marca")
        descripcion = st.text_area("Descripción")
        submitted = st.form_submit_button("Crear Link")
    if submitted:
        if not link_general.strip() or not marca.strip() or not descripcion.strip():
            st.error("Todos los campos son requeridos.")
        else:
            with get_connection() as con:
                cursor = con.cursor()
                cursor.execute(
                    """
                    INSERT INTO links_contactos (link_general, fecha_creacion, marca, descripcion, user_id)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        link_general.strip(),
                        fecha_creacion.strftime("%Y-%m-%d"),
                        marca.strip(),
                        descripcion.strip(),
                        st.session_state['user']['id'],
                    ),
                )
                con.commit()
            st.success("Link Contactos creado exitosamente.")

# =============================================================================
# PÁGINA: LINKS CONTACTOS
# =============================================================================
elif page == "Links Contactos":
    st.title("Links de Contactos")
    if st.session_state['user']['role'] == 'admin':
        df_links = read_query("SELECT * FROM links_contactos")
    else:
        df_links = read_query(
            "SELECT * FROM links_contactos WHERE user_id = ?",
            params=[st.session_state['user']['id']],
        )
    if df_links.empty:
        st.warning("No existen links.")
    else:
        st.dataframe(df_links)
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df_links.to_excel(writer, index=False, sheet_name="Links")
        st.download_button(
            "Exportar Excel",
            data=output.getvalue(),
            file_name="links.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        opciones = df_links.apply(
            lambda row: f"{row['id']} - {row['marca']} - {row['descripcion']}",
            axis=1,
        )
        seleccionado = st.selectbox(
            "Selecciona el Link a modificar o eliminar", opciones)
        link_id = int(seleccionado.split(" - ")[0])
        selected = df_links[df_links["id"] == link_id].iloc[0]
        col1, col2 = st.columns(2)
        with col1:
            with st.form("editar_link_manage_form"):
                new_link = st.text_input("Link General", value=selected["link_general"])
                new_fecha = st.date_input(
                    "Fecha de Creación",
                    value=datetime.datetime.strptime(selected["fecha_creacion"], "%Y-%m-%d").date(),
                )
                new_marca = st.text_input("Marca", value=selected["marca"])
                new_desc = st.text_area("Descripción", value=selected["descripcion"])
                new_user_id = None
                if st.session_state['user']['role'] == 'admin':
                    users_df = read_query("SELECT id, username FROM users")
                    user_options = users_df.apply(lambda r: f"{r['id']} - {r['username']}", axis=1)
                    if selected['user_id'] is not None and selected['user_id'] in users_df['id'].values:
                        default_idx = users_df.index[users_df['id'] == selected['user_id']][0]
                    else:
                        default_idx = 0
                    user_selection = st.selectbox("Asignar a Usuario", user_options, index=default_idx)
                    new_user_id = int(user_selection.split(" - ")[0])
                submit_upd = st.form_submit_button("Actualizar Link")
            if submit_upd:
                if update_link_record(link_id, new_link, new_fecha, new_marca, new_desc, new_user_id):
                    st.success("Link actualizado correctamente!")
                else:
                    st.error("No se pudo actualizar el Link.")
        with col2:
            with st.form("eliminar_link_manage_form"):
                submit_del = st.form_submit_button("Eliminar Link")
            if submit_del:
                if delete_link_record(link_id):
                    st.success("Link eliminado correctamente!")
                else:
                    st.error("Error al eliminar el link.")

# =============================================================================
# PÁGINA: AGREGAR CONTACTOS
# =============================================================================
elif page == "Agregar Contactos":
    st.title("Agregar Contactos")
    if st.session_state['user']['role'] == 'admin':
        df_links = read_query("SELECT * FROM links_contactos")
    else:
        df_links = read_query(
            "SELECT * FROM links_contactos WHERE user_id = ?",
            params=[st.session_state['user']['id']],
        )
    if df_links.empty:
        st.warning("No existen links. Cree un Link Contactos primero.")
    else:
        df_links['display'] = df_links.apply(
            lambda row: f"{row['marca']} - {row['descripcion']}",
            axis=1,
        )
        opcion = st.selectbox("Selecciona el Link Contactos", df_links['display'])
        selected_link = df_links[df_links['display'] == opcion].iloc[0]
        st.markdown(f"**Fecha de Creación:** {selected_link['fecha_creacion']}")
        st.markdown(f"**Marca:** {selected_link['marca']}")
        st.markdown(f"**Descripción:** {selected_link['descripcion']}")
        link_id = selected_link["id"]

        if st.button("Borrar Campos"):
            for k in [
                "link_auto",
                "telefono_input",
                "nombre_input",
                "auto_input",
                "precio_input",
                "descripcion_input",
            ]:
                st.session_state[k] = ""

        st.text_input("Link del Auto", key="link_auto")

        # Después de obtener el valor del link verifica si existe y ejecuta el scraping
        link_auto_value = "".join(st.session_state.get("link_auto", "").split())
        link_exists = False
        scraped_data = {}
        if link_auto_value:
            with get_connection() as con:
                cur = con.cursor()
                cur.execute(
                    "SELECT 1 FROM contactos WHERE link_auto = ? LIMIT 1",
                    (link_auto_value,),
                )
                link_exists = cur.fetchone() is not None
            if link_exists:
                st.warning("El link del auto ya está registrado en la base de datos.")
            scraped_data = scrape_vehicle_details(link_auto_value)

        # Prellenar los campos con los datos extraídos (si existen)
        whatsapp_prefill = scraped_data.get("whatsapp_number", "") if scraped_data else ""
        nombre_prefill = scraped_data.get("nombre", "") if scraped_data else ""
        precio_prefill = scraped_data.get("precio", "") if scraped_data else ""
        descripcion_prefill = scraped_data.get("descripcion", "") if scraped_data else ""


        with st.form("agregar_contacto_form"):
            telefono = st.text_input("Teléfono", value=whatsapp_prefill, key="telefono_input")
            nombre = st.text_input("Nombre", key="nombre_input")
            auto_modelo = st.text_input("Auto", value=nombre_prefill, key="auto_input")  # O asigna otro dato si corresponde
            precio_str = st.text_input("Precio (ej: 10,500,000)", value=precio_prefill, key="precio_input")
            descripcion_contacto = st.text_area("Descripción del Contacto", value=descripcion_prefill, key="descripcion_input")
            submitted_contacto = st.form_submit_button("Agregar Contacto")
        if submitted_contacto:
            telefono = "".join(telefono.split())
            if (not link_auto_value or not telefono or
                not auto_modelo.strip() or not precio_str.strip() or not descripcion_contacto.strip()):
                st.error("Todos los campos son requeridos.")
            else:
                try:
                    precio = float(precio_str.replace(",", "").strip())
                except ValueError:
                    st.error("Precio inválido. Ejemplo: 10,500,000")
                    st.stop()
                try:
                    with get_connection() as con:
                        cursor = con.cursor()
                        cursor.execute('''
                            INSERT INTO contactos (link_auto, telefono, nombre, auto, precio, descripcion, id_link)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (link_auto_value, telefono, nombre.strip(), auto_modelo.strip(), precio, descripcion_contacto.strip(), link_id))
                        con.commit()
                    st.success("Contacto agregado exitosamente.")
                except sqlite3.IntegrityError:
                    st.error("El link del auto ya existe. Ingrese otro enlace.")

# =============================================================================
# PÁGINA: VER CONTACTOS & EXPORTAR
# =============================================================================
elif page == "Ver Contactos & Exportar":
    st.title("Ver Contactos & Exportar")
    if st.session_state['user']['role'] == 'admin':
        df_links = read_query("SELECT * FROM links_contactos")
    else:
        df_links = read_query(
            "SELECT * FROM links_contactos WHERE user_id = ?",
            params=[st.session_state['user']['id']],
        )
    if df_links.empty:
        st.warning("No existen links. Cree un Link Contactos primero.")
    else:
        df_links['display'] = df_links.apply(
            lambda row: f"{row['marca']} - {row['descripcion']}",
            axis=1,
        )
        link_selected = st.selectbox("Selecciona el Link Contactos", df_links['display'])
        selected_link = df_links[df_links['display'] == link_selected].iloc[0]
        link_id = selected_link["id"]
        st.markdown(f"**Fecha de Creación:** {selected_link['fecha_creacion']}")
        st.markdown(f"**Marca:** {selected_link['marca']}")
        st.markdown(f"**Descripción:** {selected_link['descripcion']}")
        st.subheader("Filtros de Búsqueda")
        filter_nombre = st.text_input("Filtrar por Nombre")
        filter_auto = st.text_input("Filtrar por Auto")
        filter_telefono = st.text_input("Filtrar por Teléfono")
        query = "SELECT * FROM contactos WHERE id_link = ?"
        params = [link_id]
        if filter_nombre:
            query += " AND nombre LIKE ?"
            params.append(f"%{filter_nombre}%")
        if filter_auto:
            query += " AND auto LIKE ?"
            params.append(f"%{filter_auto}%")
        if filter_telefono:
            query += " AND telefono LIKE ?"
            params.append(f"%{filter_telefono}%")
        df_contactos = read_query(query, params=params)
        st.session_state['df_contactos'] = df_contactos
        st.subheader("Contactos Registrados")
        mensajes_df = read_query(
            "SELECT * FROM mensajes WHERE user_id = ?",
            params=[st.session_state['user']['id']],
        )
        selected_messages = None
        if mensajes_df.empty:
            st.warning("No existen mensajes. Agregue uno en la sección Mensajes.")
        else:
            mensajes_df['display'] = mensajes_df.apply(lambda r: f"{r['id']} - {r['descripcion'][:30]}", axis=1)
            msg_disp = st.multiselect("Selecciona las plantillas", mensajes_df['display'])
            if msg_disp:
                selected_messages = mensajes_df[mensajes_df['display'].isin(msg_disp)]

        if not df_contactos.empty and selected_messages is not None and not selected_messages.empty:
            messages_raw = selected_messages['descripcion'].tolist()
            message_ids = selected_messages['id'].tolist()
            st.session_state['mensaje_html'] = messages_raw[0]
            links = []
            used_ids = []
            for i, (_, r) in enumerate(df_contactos.iterrows()):
                template = messages_raw[i % len(messages_raw)]
                msg_id = message_ids[i % len(message_ids)]
                links.append(
                    f"https://wa.me/56{''.join(str(r['telefono']).split())}?text=" +
                    urllib.parse.quote(apply_template(template, r.to_dict()))
                )
                used_ids.append(msg_id)
            df_contactos['whatsapp_link'] = links
            df_contactos['mensaje_id'] = used_ids
            st.dataframe(df_contactos)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_contactos.to_excel(writer, index=False, sheet_name='Contactos')

            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "Descargar Excel",
                    data=output.getvalue(),
                    file_name="contactos.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            with col2:
                html_content, html_name = generate_html(df_contactos, messages_raw)
                st.download_button(
                    "Generar HTML",
                    data=html_content,
                    file_name=html_name,
                    mime="text/html",
                )

            with get_connection() as con:
                for _, row in df_contactos.iterrows():
                    con.execute(
                        "INSERT INTO export_logs (contact_id, mensaje_id, link_generado, fecha_exportacion) VALUES (?, ?, ?, ?)",
                        (row['id'], row['mensaje_id'], row['whatsapp_link'], datetime.date.today().isoformat()),
                    )
                con.commit()
        else:
            st.dataframe(df_contactos)

# =============================================================================
# PÁGINA: MENSAJES
# =============================================================================
elif page == "Mensajes":
    st.title("Plantillas de Mensaje")
    df_contactos = st.session_state.get('df_contactos')
    df_mensajes = read_query(
        "SELECT * FROM mensajes WHERE user_id = ?",
        params=[st.session_state['user']['id']],
    )
    st.subheader("Mensajes Registrados")
    st.dataframe(df_mensajes)

    with st.form("nuevo_mensaje_form"):
        mensaje_nuevo = st.text_area("Nuevo Mensaje")
        submit_mensaje = st.form_submit_button("Guardar Mensaje")
    if submit_mensaje and mensaje_nuevo.strip():
        add_message(mensaje_nuevo, st.session_state['user']['id'])
        st.success("Mensaje guardado")
        df_mensajes = read_query(
            "SELECT * FROM mensajes WHERE user_id = ?",
            params=[st.session_state['user']['id']],
        )
        st.dataframe(df_mensajes)

    mensaje_default = st.session_state.get('mensaje_html', '')
    mensaje = st.text_input("Mensaje para WhatsApp", mensaje_default, key="mensaje_html")
    if df_contactos is not None and not df_contactos.empty:
        html_content, html_name = generate_html(df_contactos, mensaje)
        st.download_button(
            "Generar HTML",
            data=html_content,
            file_name=html_name,
            mime="text/html",
        )
    else:
        st.warning(
            "No hay contactos para exportar. Ve a 'Ver Contactos & Exportar' y realiza una búsqueda primero."
        )

# =============================================================================
# PÁGINA: EDITAR
# =============================================================================
elif page == "Editar":
    st.title("Editar Registros")
    opcion_editar = st.radio("Seleccione qué desea editar:", (
        "Editar Contactos",
        "Editar Links",
        "Editar Mensajes",
    ))
    
    # --------------------------------------------------------------------------
    # Opción: Editar Contactos
    # --------------------------------------------------------------------------
    if opcion_editar == "Editar Contactos":
        st.subheader("Editar Contactos por Teléfono")
        phone_query = st.text_input("Ingrese parte o el número completo del teléfono a buscar")
        if phone_query:
            query = (
                "SELECT c.* FROM contactos c JOIN links_contactos l ON c.id_link = l.id "
                "WHERE l.user_id = ? AND c.telefono LIKE ?"
            )
            params = [st.session_state['user']['id'], f"%{phone_query}%"]
            df_search = read_query(query, params=params)
            if df_search.empty:
                st.warning("No se encontraron contactos para ese número.")
            else:
                st.write("Contactos encontrados:")
                # Mostrar resultados en un selectbox (solo se muestran los datos relevantes)
                # Usamos ID y teléfono para identificarlos
                opciones = df_search["id"].astype(str) + " - " + df_search["telefono"]
                seleccionado = st.selectbox("Seleccione el contacto a editar", opciones)
                contact_id = int(seleccionado.split(" - ")[0])
                # Filtrar el DataFrame para obtener el registro seleccionado
                contact = df_search[df_search["id"] == contact_id].iloc[0]

                st.write("Contacto seleccionado:")
                df_contact = contact.to_frame().T.reset_index(drop=True)
                st.dataframe(df_contact, height=150)
                
                # Formulario para editar con dos columnas de botones: actualizar y eliminar
                col1, col2 = st.columns(2)
                with col1:
                    with st.form("editar_contacto_update_form"):
                        new_link_auto = st.text_input("Link del Auto", value=contact["link_auto"])
                        new_telefono = st.text_input("Teléfono", value=contact["telefono"])
                        new_nombre = st.text_input("Nombre", value=contact["nombre"])
                        new_auto = st.text_input("Auto", value=contact["auto"])
                        new_precio = st.text_input("Precio", value=str(contact["precio"]))
                        new_descripcion = st.text_area("Descripción", value=contact["descripcion"])
                        submit_update = st.form_submit_button("Confirmar Actualización")
                    if submit_update:
                        if update_contact(contact_id, new_link_auto, new_telefono, new_nombre, new_auto, new_precio, new_descripcion):
                            st.success("Contacto actualizado correctamente!")
                            updated = read_query("SELECT * FROM contactos WHERE id = ?", params=[contact_id])
                            st.write("Contacto actualizado:", updated)
                        else:
                            st.error("No se pudo actualizar el contacto.")
                with col2:
                    with st.form("editar_contacto_delete_form"):
                        submit_delete = st.form_submit_button("Eliminar Contacto")
                    if submit_delete:
                        if delete_contact(contact_id):
                            st.success("Contacto eliminado correctamente!")
                        else:
                            st.error("Error al eliminar el contacto.")
                        
    # --------------------------------------------------------------------------
    # Opción: Editar Links
    # --------------------------------------------------------------------------
    elif opcion_editar == "Editar Links":
        st.subheader("Editar Links")
        if st.session_state['user']['role'] == 'admin':
            df_links = read_query("SELECT * FROM links_contactos")
        else:
            df_links = read_query(
                "SELECT * FROM links_contactos WHERE user_id = ?",
                params=[st.session_state['user']['id']],
            )
        if df_links.empty:
            st.warning("No existen links. Cree uno primero.")
        else:
            opciones = df_links["id"].astype(str) + " - " + df_links["link_general"]
            seleccionado = st.selectbox("Seleccione el Link a editar", opciones)
            link_id = int(seleccionado.split(" - ")[0])
            selected_link = df_links[df_links["id"] == link_id].iloc[0]
            
            st.write("Link seleccionado:")
            df_contact = selected_link.to_frame().T.reset_index(drop=True)
            st.dataframe(df_contact, height=150)
            
            with st.form("editar_link_form"):
                new_link_general = st.text_input("Link General", value=selected_link["link_general"])
                new_fecha = st.date_input("Fecha de Creación", value=datetime.datetime.strptime(selected_link["fecha_creacion"], "%Y-%m-%d").date())
                new_marca = st.text_input("Marca", value=selected_link["marca"])
                new_descripcion = st.text_area("Descripción", value=selected_link["descripcion"])
                new_user_id = None
                if st.session_state['user']['role'] == 'admin':
                    users_df = read_query("SELECT id, username FROM users")
                    user_opts = users_df.apply(lambda r: f"{r['id']} - {r['username']}", axis=1)
                    if selected_link['user_id'] is not None and selected_link['user_id'] in users_df['id'].values:
                        default_idx = users_df.index[users_df['id'] == selected_link['user_id']][0]
                    else:
                        default_idx = 0
                    user_sel = st.selectbox("Asignar a Usuario", user_opts, index=default_idx)
                    new_user_id = int(user_sel.split(" - ")[0])
                submit_button = st.form_submit_button("Actualizar Link")
            if submit_button:
                if update_link_record(link_id, new_link_general, new_fecha, new_marca, new_descripcion, new_user_id):
                    st.success("Link actualizado correctamente!")
                    updated = read_query("SELECT * FROM links_contactos WHERE id = ?", params=[link_id])
                    st.write("Link actualizado:", updated)
                else:
                    st.error("No se pudo actualizar el Link.")

    # --------------------------------------------------------------------------
    # Opción: Editar Mensajes
    # --------------------------------------------------------------------------
    else:
        st.subheader("Editar Mensajes")
        df_mensajes = read_query(
            "SELECT * FROM mensajes WHERE user_id = ?",
            params=[st.session_state['user']['id']],
        )
        if df_mensajes.empty:
            st.warning("No existen mensajes.")
        else:
            opciones = df_mensajes['id'].astype(str) + " - " + df_mensajes['descripcion'].str[:30]
            seleccionado = st.selectbox("Seleccione el mensaje a editar", opciones)
            msg_id = int(seleccionado.split(" - ")[0])
            mensaje = df_mensajes[df_mensajes['id'] == msg_id].iloc[0]

            st.write("Mensaje seleccionado:")
            df_msg = mensaje.to_frame().T.reset_index(drop=True)
            st.dataframe(df_msg, height=150)

            col1, col2 = st.columns(2)
            with col1:
                with st.form("editar_mensaje_update_form"):
                    nuevo_texto = st.text_area("Mensaje", value=mensaje['descripcion'])
                    submit_update_msg = st.form_submit_button("Confirmar Actualización")
                if submit_update_msg:
                    if update_message(msg_id, nuevo_texto):
                        st.success("Mensaje actualizado correctamente!")
                        updated = read_query("SELECT * FROM mensajes WHERE id = ?", params=[msg_id])
                        st.write("Mensaje actualizado:", updated)
                    else:
                        st.error("No se pudo actualizar el mensaje.")
            with col2:
                with st.form("editar_mensaje_delete_form"):
                    submit_delete_msg = st.form_submit_button("Eliminar Mensaje")
                if submit_delete_msg:
                    if delete_message(msg_id):
                        st.success("Mensaje eliminado correctamente!")
                    else:
                        st.error("Error al eliminar el mensaje.")

            df_mensajes = read_query(
                "SELECT * FROM mensajes WHERE user_id = ?",
                params=[st.session_state['user']['id']],
            )
            st.dataframe(df_mensajes)

# =============================================================================
# PÁGINA: ADMIN USUARIOS
# =============================================================================
elif page == "Admin Usuarios":
    if st.session_state['user']['role'] != 'admin':
        st.error("Acceso denegado")
    else:
        st.title("Administración de Usuarios")
        df_users = read_query("SELECT id, username, role FROM users")
        st.dataframe(df_users)

        with st.form("crear_usuario_form"):
            new_user = st.text_input("Usuario")
            new_pass = st.text_input("Contraseña", type="password")
            new_role = st.selectbox("Rol", ["user", "admin"])
            submit_user = st.form_submit_button("Crear Usuario")
        if submit_user and new_user and new_pass:
            create_user(new_user, new_pass, new_role)
            st.success("Usuario creado")
            st.rerun()

        del_id = st.number_input("ID a eliminar", min_value=1, step=1)
        if st.button("Eliminar Usuario"):
            delete_user(int(del_id))
            st.success("Usuario eliminado")
            st.rerun()
