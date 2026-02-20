import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import pandas as pd
import datetime
from io import BytesIO
import requests
from bs4 import BeautifulSoup
import re
import urllib.parse
import os
import sys
import hashlib
import random
import json
from html import escape
from typing import Any


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath('.')
    return os.path.join(base_path, relative_path)


def sanitize_vehicle_link(url: str) -> str:
    """Normalize a vehicle URL by removing query strings and fragments."""
    parsed = urllib.parse.urlparse("".join(url.split()))
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def normalize_phone(value):
    """Return a digits-only phone number trimmed to its core 9 digits when applicable."""
    if value is None:
        return ""
    digits = ''.join(ch for ch in str(value) if ch.isdigit())
    if len(digits) > 9:
        digits = digits[-9:]
    return digits


# =============================================================================
# CONFIGURACIÓN BÁSICA Y ESTILOS
# =============================================================================
st.markdown("""
    <style>
    :root {
        --primary-color: #2563eb;
        --primary-hover: #1d4ed8;
        --bg-soft: #f4f7ff;
        --card-bg: #ffffff;
        --border-color: #dfe5f1;
    }
    .stApp {
        max-width: 1200px;
        margin: auto;
        background: var(--bg-soft);
    }
    div[data-testid="stAppViewContainer"] > .main {
        padding: 2rem 2.5rem 3rem;
    }
    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e3a8a 0%, #312e81 100%);
        color: #f8fafc;
    }
    div[data-testid="stSidebar"] svg,
    div[data-testid="stSidebar"] h1,
    div[data-testid="stSidebar"] h2,
    div[data-testid="stSidebar"] label {
        color: inherit !important;
        fill: inherit !important;
    }
    div[data-testid="stSidebar"] section > div {
        padding-right: 0.75rem;
    }
    .page-hero {
        background: linear-gradient(135deg, rgba(37,99,235,0.16), rgba(129,140,248,0.16));
        border: 1px solid var(--border-color);
        border-radius: 18px;
        padding: 1.1rem 1.4rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
    }
    .page-hero__title {
        font-size: 1.9rem;
        font-weight: 700;
        color: #1e3a8a;
        margin-bottom: 0.35rem;
        display: flex;
        align-items: center;
        gap: 0.6rem;
    }
    .page-hero__icon {
        font-size: 2rem;
        line-height: 1;
    }
    .page-hero__subtitle {
        color: #475569;
        font-size: 0.95rem;
        margin: 0;
    }
    .stButton button,
    .stDownloadButton button {
        background: var(--primary-color);
        color: #fff;
        border-radius: 999px;
        padding: 0.55rem 1.6rem;
        border: none;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
        box-shadow: 0 8px 16px rgba(37,99,235,0.25);
    }
    .stButton button:hover,
    .stDownloadButton button:hover {
        background: var(--primary-hover);
        box-shadow: 0 10px 22px rgba(37,99,235,0.35);
        transform: translateY(-1px);
    }
    div[data-testid="stForm"] {
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 12px 24px rgba(15, 23, 42, 0.06);
        margin-bottom: 1.5rem;
    }
    div[data-testid="stForm"] label {
        font-weight: 600;
        color: #1f2937 !important;
    }
    input, textarea, select {
        font-size: 1.05em;
        border-radius: 10px !important;
        border: 1px solid #cbd5f5 !important;
    }
    input:focus, textarea:focus, select:focus {
        border-color: var(--primary-color) !important;
        box-shadow: 0 0 0 1px rgba(37,99,235,0.35) !important;
    }
    .sidebar-card {
        border-radius: 14px;
        padding: 1rem;
        background: rgba(15,23,42,0.88);
        box-shadow: 0 8px 18px rgba(15,23,42,0.4);
        color: #f8fafc;
        border: 1px solid rgba(148,163,184,0.3);
        position: relative;
    }
    .sidebar-card__title {
        margin-bottom: 0.6rem;
        font-size: 1.05rem;
        font-weight: 600;
        letter-spacing: 0.01em;
    }
    .sidebar-card__body {
        max-height: 280px;
        overflow-y: auto;
        margin-bottom: 0.75rem;
        font-family: "Source Code Pro", monospace;
        font-size: 0.9rem;
        white-space: pre-wrap;
        word-wrap: break-word;
    }
    .sidebar-card button {
        width: 100%;
        border-radius: 999px;
        background: linear-gradient(135deg, #22d3ee 0%, #6366f1 100%);
        border: none;
        color: #0f172a;
        font-weight: 600;
        padding: 0.55rem 1rem;
        cursor: pointer;
        transition: all 0.2s ease-in-out;
    }
    .sidebar-card button:hover {
        opacity: 0.92;
        transform: translateY(-1px);
    }
    table td, table th {
        border-color: rgba(100,116,139,0.18) !important;
        padding: 0.6rem 0.75rem !important;
    }
    .sidebar-user-card {
        display: flex;
        align-items: center;
        gap: 0.85rem;
        padding: 1rem;
        border-radius: 16px;
        background: rgba(15,23,42,0.45);
        border: 1px solid rgba(148,163,184,0.35);
        margin-bottom: 1.1rem;
    }
    .sidebar-user-card__initials {
        width: 46px;
        height: 46px;
        border-radius: 14px;
        background: linear-gradient(135deg, rgba(14,116,144,0.4), rgba(129,140,248,0.7));
        display: grid;
        place-items: center;
        font-weight: 700;
        font-size: 1.05rem;
        color: #0f172a;
    }
    .sidebar-user-card__meta {
        display: flex;
        flex-direction: column;
        gap: 0.15rem;
    }
    .sidebar-user-card__name {
        margin: 0;
        font-weight: 600;
        color: #e2e8f0;
    }
    .sidebar-user-card__role {
        font-size: 0.75rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: rgba(226,232,240,0.75);
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] {
        display: grid;
        gap: 0.55rem;
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] > label {
        position: relative;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        border-radius: 14px;
        padding: 0.75rem 1rem;
        margin: 0;
        border: 1px solid rgba(148,163,184,0.22);
        transition: background 0.2s ease, border 0.2s ease, box-shadow 0.2s ease, transform 0.15s ease;
        background: rgba(148,163,184,0.12);
        box-shadow: inset 0 0 0 1px rgba(15,23,42,0.18), 0 8px 20px rgba(15,23,42,0.05);
        color: #e2e8f0;
        font-weight: 600;
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
        background: rgba(148,163,184,0.22);
        border-color: rgba(148,163,184,0.38);
        box-shadow: inset 0 0 0 1px rgba(15,23,42,0.22), 0 12px 24px rgba(15,23,42,0.08);
        transform: translateX(2px);
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] > label:focus-within {
        outline: 3px solid rgba(94,234,212,0.6);
        outline-offset: 2px;
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] > label[aria-checked="true"] {
        background: linear-gradient(135deg, rgba(79,70,229,0.18), rgba(6,182,212,0.24));
        border-color: rgba(94,234,212,0.8);
        box-shadow: inset 0 0 0 1px rgba(14,116,144,0.35), 0 16px 32px rgba(14,116,144,0.25);
        transform: translateX(2px);
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] > label div[part="radio"] {
        display: none;
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {
        display: none !important;
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] > label > div:last-child {
        flex: 1;
    }
    .sidebar-section-title {
        margin: 1.2rem 0 0.5rem;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        font-weight: 700;
        color: rgba(226,232,240,0.65);
    }
    .sidebar-section-title:first-child {
        margin-top: 0.2rem;
    }
    .sidebar-divider {
        height: 1px;
        width: 100%;
        margin: 1.3rem 0 0.9rem;
        background: linear-gradient(90deg, rgba(94,234,212,0.65) 0%, rgba(129,140,248,0) 100%);
        border-radius: 999px;
    }
    .sidebar-group-hint {
        font-size: 0.75rem;
        color: rgba(226,232,240,0.65);
        margin: 0.25rem 0 0;
    }
    .sidebar-message-card {
        border-radius: 16px;
        background: rgba(30,41,59,0.9);
        border: 1px solid rgba(148,163,184,0.35);
        padding: 1rem;
        display: flex;
        flex-direction: column;
        gap: 0.6rem;
    }
    .sidebar-message-card__header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.5rem;
    }
    .sidebar-message-card__title {
        font-weight: 600;
        color: #e2e8f0;
        margin: 0;
    }
    .sidebar-message-card__body {
        background: rgba(15,23,42,0.65);
        border-radius: 12px;
        padding: 0.75rem;
        max-height: 170px;
        overflow-y: auto;
        border: 1px dashed rgba(148,163,184,0.35);
        color: #cbd5f5;
        font-size: 0.88rem;
    }
    .sidebar-message-card__copy {
        border-radius: 999px;
        border: none;
        padding: 0.4rem 0.9rem;
        background: linear-gradient(135deg, #22d3ee 0%, #818cf8 100%);
        color: #0f172a;
        font-weight: 600;
        cursor: pointer;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .sidebar-message-card__copy:hover {
        transform: translateY(-1px);
        box-shadow: 0 8px 18px rgba(14,165,233,0.25);
    }
    button:focus-visible, .sidebar-message-card__copy:focus-visible {
        outline: 3px solid rgba(94,234,212,0.7);
        outline-offset: 2px;
    }
    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            transition-duration: 0.001ms !important;
            animation-duration: 0.001ms !important;
        }
    }
    @media (max-width: 820px) {
        div[data-testid="stAppViewContainer"] > .main {
            padding: 1.5rem 1rem 2.5rem;
        }
        .page-hero__title {
            font-size: 1.6rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)

def render_page_header(title: str, subtitle: str = "", icon: str | None = None) -> None:
    icon_html = f"<span class='page-hero__icon'>{escape(icon)}</span>" if icon else ""
    subtitle_html = f"<p class='page-hero__subtitle'>{escape(subtitle)}</p>" if subtitle else ""
    st.markdown(
        f"""
        <div class="page-hero">
            <div class="page-hero__title">{icon_html}{escape(title)}</div>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


NAV_METADATA: dict[str, dict[str, str]] = {
    "Login": {"icon": "🔐", "caption": "Autentícate para gestionar consignaciones y exportaciones."},
    "Crear Link Contactos": {"icon": "🧷", "caption": "Genera enlaces base para capturar nuevos prospectos."},
    "Links Contactos": {"icon": "🗂️", "caption": "Consulta y actualiza enlaces existentes de manera segura."},
    "Sanitizar Links": {"icon": "🧹", "caption": "Limpia URLs duplicadas o con ruido antes de compartirlas."},
    "Agregar Contactos": {"icon": "➕", "caption": "Registra personas interesadas y toma notas relevantes."},
    "Ver Contactos & Exportar": {"icon": "📤", "caption": "Filtra contactos y genera reportes listos para compartir."},
    "CWS Chat WhatsApp": {"icon": "💬", "caption": "Prepara mensajes personalizados y abre WhatsApp rápidamente."},
    "Mensajes": {"icon": "✉️", "caption": "Organiza plantillas para responder con consistencia."},
    "Clientes Interesados": {"icon": "⭐", "caption": "Registra solicitudes de información y haz seguimiento rápido."},
    "Editar": {"icon": "🛠️", "caption": "Actualiza contactos, links o mensajes sin duplicar registros."},
    "Contactos Restringidos": {"icon": "🚫", "caption": "Administra la lista global de números bloqueados."},
    "Admin Usuarios": {"icon": "🧑‍💼", "caption": "Crea cuentas nuevas y ajusta roles del equipo."},
}


def nav_display_label(option: str) -> str:
    """Return the labeled navigation option decorated with iconography."""
    meta = NAV_METADATA.get(option, {})
    icon = meta.get("icon", "")
    label = meta.get("label", option)
    return f"{icon} {label}".strip()


def nav_caption(option: str) -> str:
    """Return the contextual caption for the selected navigation option."""
    return NAV_METADATA.get(option, {}).get("caption", "")


def render_sidebar_user_panel(user: dict[str, Any]) -> None:
    """Render a compact user card in the sidebar with role details."""
    username = str(user.get("username", "Usuario"))
    initials_source = "".join(ch for ch in username if ch.isalpha()) or username
    initials = escape(initials_source[:2].upper())
    role = str(user.get("role", "user"))
    role_label = "Administrador" if role == "admin" else "Usuario"
    user_html = f"""
    <div class="sidebar-user-card" role="complementary" aria-label="Perfil activo">
        <div class="sidebar-user-card__initials" aria-hidden="true">{initials}</div>
        <div class="sidebar-user-card__meta">
            <p class="sidebar-user-card__name">{escape(username)}</p>
            <span class="sidebar-user-card__role">{escape(role_label)}</span>
        </div>
    </div>
    """
    st.sidebar.markdown(user_html, unsafe_allow_html=True)


def build_menu_options(user: dict[str, Any] | None) -> tuple[str, ...]:
    """Compose the navigation menu according to the user's role."""
    if not user:
        return ("Login",)
    menu_list = [
        "Crear Link Contactos",
        "Links Contactos",
        "Sanitizar Links",
        "Agregar Contactos",
        "Ver Contactos & Exportar",
        "CWS Chat WhatsApp",
        "Mensajes",
        "Clientes Interesados",
        "Editar",
    ]
    if user.get("role") == "admin":
        menu_list += ["Contactos Restringidos", "Admin Usuarios"]
    return tuple(menu_list)


def render_sidebar_message_card() -> None:
    """Show the latest generated WhatsApp message with a quick copy action."""
    message = st.session_state.get("cws_msg")
    if not message:
        return
    mensaje_html = escape(message)
    html_card = f"""
    <div class="sidebar-message-card" role="region" aria-live="polite" aria-label="Mensaje generado">
        <div class="sidebar-message-card__header">
            <p class="sidebar-message-card__title">Mensaje generado</p>
            <button class="sidebar-message-card__copy" type="button" onclick="(function() {{
                const text = document.getElementById('cws-message').innerText;
                navigator.clipboard.writeText(text).then(function() {{
                    alert('Mensaje copiado.');
                }}).catch(function(err) {{
                    alert('Error al copiar: ' + err);
                }});
            }})()">Copiar</button>
        </div>
        <pre id="cws-message" class="sidebar-message-card__body" tabindex="0">{mensaje_html}</pre>
    </div>
    """
    with st.sidebar:
        components.html(html_card, height=320)


def render_navigation_sidebar(current_page: str) -> str:
    """Render the navigation sidebar and return the selected page name."""
    user = st.session_state.get("user")
    st.sidebar.title("Navegación")
    if user:
        render_sidebar_user_panel(user)
    else:
        st.sidebar.info("Inicia sesión para acceder a la gestión de consignaciones.")

    st.sidebar.markdown("<p class='sidebar-section-title'>Accesos principales</p>", unsafe_allow_html=True)

    menu_options = build_menu_options(user)

    if user and user.get("role") == "admin" and "Contactos Restringidos" in menu_options:
        admin_start = menu_options.index("Contactos Restringidos") + 1  # nth-child es 1-based
        st.sidebar.markdown(
            f"""
            <style>
            div[data-testid="stSidebar"] div[role="radiogroup"] > label:nth-child({admin_start}) {{
                margin-top: 1.4rem;
            }}
            div[data-testid="stSidebar"] div[role="radiogroup"] > label:nth-child(n+{admin_start}):not([aria-checked="true"]) {{
                background: rgba(148,163,184,0.1);
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )

    try:
        default_index = menu_options.index(current_page)
    except ValueError:
        default_index = 0
    page = st.sidebar.radio(
        "Ir a:",
        menu_options,
        index=default_index,
        format_func=nav_display_label,
        key="navigation_menu",
    )
    if user:
        if st.sidebar.button("Cerrar Sesión", use_container_width=True):
            st.session_state.user = None
            st.session_state.page = "Login"
            st.session_state['cws_msg'] = ''
            st.rerun()

    caption = nav_caption(page)
    if caption:
        st.sidebar.caption(caption)

    if user and user.get("role") == "admin":
        st.sidebar.markdown("<div class='sidebar-divider'></div>", unsafe_allow_html=True)
        st.sidebar.markdown(
            "<p class='sidebar-group-hint'>Las últimas opciones corresponden a herramientas administrativas.</p>",
            unsafe_allow_html=True,
        )

    render_sidebar_message_card()
    return page


def render_interested_clients_page() -> None:
    """Renderiza la gestión de clientes interesados con autocompletado desde contactos."""
    user = st.session_state.get("user")
    if not user:
        st.warning("Inicia sesión para registrar clientes interesados.")
        return

    render_page_header(
        "Clientes interesados",
        "Centraliza quienes solicitaron información y haz seguimiento oportuno.",
        "⭐",
    )

    # Inicializar valores de estado
    defaults: dict[str, Any] = {
        "interested_numero_field": "",
        "interested_auto_field": "",
        "interested_link_field": "",
        "interested_correo_field": "",
        "interested_selected_contact_id": None,
    }
    for key, default in defaults.items():
        st.session_state.setdefault(key, default)
    if "interested_fecha_field" not in st.session_state:
        st.session_state["interested_fecha_field"] = datetime.date.today()

    if st.session_state.pop("interested_reset_form", False):
        st.session_state["interested_numero_field"] = ""
        st.session_state["interested_auto_field"] = ""
        st.session_state["interested_link_field"] = ""
        st.session_state["interested_correo_field"] = ""
        st.session_state["interested_lookup_input"] = ""
        st.session_state["interested_fecha_field"] = datetime.date.today()
        st.session_state["interested_selected_contact_id"] = None
        st.session_state.pop("interested_contact_select", None)

    lookup_number = st.text_input(
        "Buscar por número de contacto",
        key="interested_lookup_input",
        placeholder="Ingresa un número para cargar datos existentes",
    )
    contacts_df = get_contacts_by_phone(lookup_number) if lookup_number else pd.DataFrame()
    selected_contact: pd.Series | None = None

    if not contacts_df.empty:
        st.caption("Se encontraron coincidencias en la base de contactos.")
        options = contacts_df.apply(
            lambda row: f"{row['id']} · {row['auto']} · {row['telefono']}",
            axis=1,
        ).tolist()
        last_selected_id = st.session_state.get("interested_selected_contact_id")
        index = 0
        if last_selected_id in contacts_df["id"].tolist():
            index = int(contacts_df.index[contacts_df["id"] == last_selected_id][0])
        selected_option = st.selectbox(
            "Selecciona el registro para precargar los datos",
            options,
            index=index,
            key="interested_contact_select",
        )
        selected_id = int(selected_option.split(" · ")[0])
        selected_contact = contacts_df[contacts_df["id"] == selected_id].iloc[0]
    else:
        if lookup_number:
            st.info("No se encontraron contactos con ese número. Puedes registrar los datos manualmente.")
        if "interested_contact_select" in st.session_state:
            st.session_state.pop("interested_contact_select")
        st.session_state["interested_selected_contact_id"] = None

    if selected_contact is not None:
        if st.session_state.get("interested_selected_contact_id") != int(selected_contact["id"]):
            st.session_state["interested_selected_contact_id"] = int(selected_contact["id"])
            st.session_state["interested_auto_field"] = selected_contact.get("auto", "") or ""
            st.session_state["interested_link_field"] = selected_contact.get("link_auto", "") or ""
            st.session_state["interested_numero_field"] = selected_contact.get("telefono", "") or ""
    else:
        if lookup_number and lookup_number.strip():
            st.session_state["interested_numero_field"] = lookup_number.strip()

    with st.form("interested_client_form"):
        fecha_contacto = st.date_input(
            "Fecha de contacto",
            key="interested_fecha_field",
        )
        col_left, col_right = st.columns(2)
        with col_left:
            numero = st.text_input("Teléfono", key="interested_numero_field")
            correo = st.text_input(
                "Correo (opcional)",
                key="interested_correo_field",
                placeholder="cliente@correo.com",
            )
        with col_right:
            auto = st.text_input("Auto de interés", key="interested_auto_field")
            link = st.text_input("Link de referencia", key="interested_link_field")
        submitted = st.form_submit_button("Guardar cliente interesado", use_container_width=True)

    if submitted:
        if not numero.strip() or not auto.strip() or not link.strip():
            st.error("Completa al menos teléfono, auto y link para registrar el interés.")
        else:
            success, message = add_interested_client(
                fecha_contacto,
                auto,
                numero,
                link,
                correo,
                user_id=user.get("id"),
            )
            if success:
                st.success(message)
                st.session_state["interested_reset_form"] = True
                st.rerun()
            else:
                st.error(message)

    st.subheader("Historial de clientes interesados")
    filter_phone = st.text_input(
        "Filtrar por teléfono",
        key="interested_filter_phone",
        placeholder="Busca dentro del historial",
    )
    filters: dict[str, Any] = {}
    if filter_phone:
        filters["telefono"] = filter_phone
    interesados_df = list_interested_clients(filters)
    if interesados_df.empty:
        st.info("Aún no hay clientes interesados registrados.")
    else:
        st.dataframe(interesados_df)
        export_buffer = BytesIO()
        with pd.ExcelWriter(export_buffer, engine="xlsxwriter") as writer:
            interesados_df.to_excel(writer, index=False, sheet_name="Clientes")
        st.download_button(
            "Exportar a Excel",
            data=export_buffer.getvalue(),
            file_name="clientes_interesados.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

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
if 'cws_msg' not in st.session_state:
    st.session_state['cws_msg'] = ''

# =============================================================================
# CONEXIÓN A LA BASE DE DATOS Y CREACIÓN DE TABLAS
# =============================================================================
db_filename = resource_path(os.path.join("data", "datos_consignacion.db"))

def get_connection():
    """Retorna una nueva conexión a la base de datos."""
    os.makedirs(os.path.dirname(db_filename), exist_ok=True)
    conn = sqlite3.connect(db_filename, check_same_thread=False)
    conn.create_function("normalize_phone", 1, normalize_phone)
    return conn

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
    """Crea tabla de usuarios y agrega columnas ``user_id`` si faltan."""
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

        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='links_contactos'"
        )
        if cur.fetchone():
            cur.execute("PRAGMA table_info(links_contactos)")
            cols = [r[1] for r in cur.fetchall()]
            if "user_id" not in cols:
                cur.execute("ALTER TABLE links_contactos ADD COLUMN user_id INTEGER")

        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='mensajes'"
        )
        if cur.fetchone():
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
            CREATE TABLE IF NOT EXISTS contactos_restringidos (
                telefono_normalizado TEXT PRIMARY KEY,
                telefono_original TEXT NOT NULL,
                motivo TEXT,
                created_at TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                FOREIGN KEY (created_by) REFERENCES users(id)
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
            CREATE TABLE IF NOT EXISTS clientes_interesados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                auto TEXT NOT NULL,
                numero TEXT NOT NULL,
                link TEXT NOT NULL,
                correo TEXT,
                user_id INTEGER,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
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


def list_restricted_numbers():
    """Retorna el listado de números restringidos con metadatos básicos."""
    query = """
        SELECT
            r.telefono_original,
            r.telefono_normalizado,
            COALESCE(r.motivo, '') AS motivo,
            r.created_at,
            r.created_by,
            COALESCE(u.username, '') AS created_by_username
        FROM contactos_restringidos r
        LEFT JOIN users u ON r.created_by = u.id
        ORDER BY r.created_at DESC
    """
    return read_query(query)



def add_interested_client(
    fecha: datetime.date | datetime.datetime | str,
    auto: str,
    numero: str,
    link: str,
    correo: str | None,
    user_id: int | None,
) -> tuple[bool, str]:
    """Registra un cliente interesado y devuelve el resultado de la operación."""
    fecha_str = fecha.isoformat() if hasattr(fecha, "isoformat") else str(fecha).strip()
    numero_limpio = "".join(str(numero).split())
    try:
        with get_connection() as con:
            con.execute(
                """
                INSERT INTO clientes_interesados (fecha, auto, numero, link, correo, user_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (fecha_str, auto.strip(), numero_limpio, link.strip(), (correo or "").strip() or None, user_id),
            )
            con.commit()
        return True, "Cliente interesado registrado correctamente."
    except sqlite3.Error as exc:
        st.error(f"No se pudo registrar el interés: {exc}")
        return False, "Ocurrió un error al guardar el registro."


def list_interested_clients(filters: dict | None = None) -> pd.DataFrame:
    """Devuelve los clientes interesados aplicando filtros opcionales."""
    filters = filters or {}
    clauses = [
        """
        SELECT
            ci.id,
            ci.fecha,
            ci.auto,
            ci.numero,
            ci.link,
            ci.correo,
            ci.user_id,
            COALESCE(u.username, '') AS usuario
        FROM clientes_interesados ci
        LEFT JOIN users u ON ci.user_id = u.id
        WHERE 1=1
        """
    ]
    params: list = []

    telefono = filters.get("telefono")
    if telefono:
        clauses.append("AND ci.numero LIKE ?")
        params.append(f"%{telefono.strip()}%")

    fecha = filters.get("fecha")
    if fecha:
        fecha_str = fecha.isoformat() if hasattr(fecha, "isoformat") else str(fecha).strip()
        clauses.append("AND ci.fecha = ?")
        params.append(fecha_str)

    clauses.append("ORDER BY datetime(ci.fecha) DESC, ci.id DESC")
    query = " ".join(clauses)
    return read_query(query, params=params)


def add_restricted_number(phone: str, motivo: str, user_id: int) -> tuple[bool, str]:
    """Inserta o actualiza un número restringido y retorna el resultado."""
    normalized = normalize_phone(phone)
    if not normalized:
        return False, "Ingresa un número válido."

    existed = False
    with get_connection() as con:
        cur = con.cursor()
        cur.execute(
            "SELECT 1 FROM contactos_restringidos WHERE telefono_normalizado = ?",
            (normalized,),
        )
        existed = cur.fetchone() is not None
        cur.execute(
            """
            INSERT INTO contactos_restringidos (telefono_normalizado, telefono_original, motivo, created_at, created_by)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(telefono_normalizado) DO UPDATE SET
                telefono_original = excluded.telefono_original,
                motivo = excluded.motivo,
                created_at = excluded.created_at,
                created_by = excluded.created_by
            """,
            (
                normalized,
                phone.strip(),
                motivo.strip(),
                datetime.datetime.now(datetime.UTC).isoformat(timespec='seconds'),
                user_id,
            ),
        )
        con.commit()
    message = "Número actualizado en la lista restringida." if existed else "Número agregado a la lista restringida."
    return True, message



def get_contacts_by_phone(phone: str) -> pd.DataFrame:
    """Obtiene los contactos cuyo teléfono coincide con el número normalizado."""
    normalized = normalize_phone(phone)
    if not normalized:
        return pd.DataFrame()
    query = """
        SELECT
            c.id,
            c.link_auto,
            c.telefono,
            c.nombre,
            c.auto,
            c.precio,
            c.descripcion AS contacto_descripcion,
            c.id_link,
            l.marca AS link_marca,
            l.descripcion AS link_descripcion,
            l.link_general
        FROM contactos c
        LEFT JOIN links_contactos l ON c.id_link = l.id
        WHERE normalize_phone(c.telefono) = ?
    """
    return read_query(query, params=[normalized])



def fetch_contacts_for_link(link_id: int, filters: dict | None = None, include_restricted: bool = False) -> pd.DataFrame:
    """Recupera contactos asociados a un link aplicando filtros opcionales."""
    filters = filters or {}
    clauses = ["SELECT * FROM contactos WHERE id_link = ?"]
    params: list = [link_id]

    nombre = filters.get('nombre')
    if nombre:
        clauses.append("AND nombre LIKE ?")
        params.append(f"%{nombre}%")

    auto = filters.get('auto')
    if auto:
        clauses.append("AND auto LIKE ?")
        params.append(f"%{auto}%")

    telefono = filters.get('telefono')
    if telefono:
        phone_filter = f"%{telefono}%"
        normalized_filter = normalize_phone(telefono)
        clauses.append("AND (telefono LIKE ?" + (" OR normalize_phone(telefono) LIKE ?" if normalized_filter else "") + ")")
        params.append(phone_filter)
        if normalized_filter:
            params.append(f"%{normalized_filter}%")

    if not include_restricted:
        clauses.append(
            "AND NOT EXISTS (SELECT 1 FROM contactos_restringidos r WHERE r.telefono_normalizado = normalize_phone(telefono))"
        )

    clauses.append("ORDER BY id DESC")
    query = " ".join(clauses)
    return read_query(query, params=params)

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



def fetch_all_contacts_for_user(user: dict) -> pd.DataFrame:
    """Recupera TODOS los contactos visibles para el usuario (Admin: todos, User: los suyos)."""
    import pandas as pd # Ensure pd is available here if needed, though it is imported at top
    if user['role'] == 'admin':
        # Admin ve todo. Join con links para tener datos extra si se requiere, o directo.
        query = """
            SELECT c.*, l.marca, l.descripcion as link_desc 
            FROM contactos c 
            LEFT JOIN links_contactos l ON c.id_link = l.id
            ORDER BY c.id DESC
        """
        return read_query(query)
    else:
        # User ve solo sus contactos
        query = """
            SELECT c.*, l.marca, l.descripcion as link_desc
            FROM contactos c 
            JOIN links_contactos l ON c.id_link = l.id 
            WHERE l.user_id = ?
            ORDER BY c.id DESC
        """
        return read_query(query, params=[user['id']])

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

create_tables()
migrate_contactos_schema()
migrate_user_schema()
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
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'es-CL,es;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Referer': 'https://www.chileautos.cl/',
        'Upgrade-Insecure-Requests': '1',
        'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
    }
    try:
        session = requests.Session()
        session.headers.update(headers)
        response = session.get(url, timeout=15)
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
    normalized = normalize_phone(phone)
    if not normalized:
        return pd.DataFrame()
    query = """
        SELECT
            c.id,
            c.link_auto,
            c.telefono,
            c.nombre,
            c.auto,
            c.precio,
            c.descripcion AS contacto_descripcion,
            c.id_link,
            l.marca AS link_marca,
            l.descripcion AS link_descripcion,
            l.link_general
        FROM contactos c
        LEFT JOIN links_contactos l ON c.id_link = l.id
        WHERE normalize_phone(c.telefono) = ?
    """
    return read_query(query, params=[normalized])



def fetch_contacts_for_link(link_id: int, filters: dict | None = None, include_restricted: bool = False) -> pd.DataFrame:
    """Recupera contactos asociados a un link aplicando filtros opcionales."""
    filters = filters or {}
    clauses = ["SELECT * FROM contactos WHERE id_link = ?"]
    params: list = [link_id]

    nombre = filters.get('nombre')
    if nombre:
        clauses.append("AND nombre LIKE ?")
        params.append(f"%{nombre}%")

    auto = filters.get('auto')
    if auto:
        clauses.append("AND auto LIKE ?")
        params.append(f"%{auto}%")

    telefono = filters.get('telefono')
    if telefono:
        phone_filter = f"%{telefono}%"
        normalized_filter = normalize_phone(telefono)
        clauses.append("AND (telefono LIKE ?" + (" OR normalize_phone(telefono) LIKE ?" if normalized_filter else "") + ")")
        params.append(phone_filter)
        if normalized_filter:
            params.append(f"%{normalized_filter}%")

    if not include_restricted:
        clauses.append(
            "AND NOT EXISTS (SELECT 1 FROM contactos_restringidos r WHERE r.telefono_normalizado = normalize_phone(telefono))"
        )

    clauses.append("ORDER BY id DESC")
    query = " ".join(clauses)
    return read_query(query, params=params)

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



def fetch_all_contacts_for_user(user: dict) -> pd.DataFrame:
    """Recupera TODOS los contactos visibles para el usuario (Admin: todos, User: los suyos)."""
    import pandas as pd # Ensure pd is available here if needed, though it is imported at top
    if user['role'] == 'admin':
        # Admin ve todo. Join con links para tener datos extra si se requiere, o directo.
        query = """
            SELECT c.*, l.marca, l.descripcion as link_desc 
            FROM contactos c 
            LEFT JOIN links_contactos l ON c.id_link = l.id
            ORDER BY c.id DESC
        """
        return read_query(query)
    else:
        # User ve solo sus contactos
        query = """
            SELECT c.*, l.marca, l.descripcion as link_desc
            FROM contactos c 
            JOIN links_contactos l ON c.id_link = l.id 
            WHERE l.user_id = ?
            ORDER BY c.id DESC
        """
        return read_query(query, params=[user['id']])

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

create_tables()
migrate_contactos_schema()
migrate_user_schema()
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
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'es-CL,es;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Referer': 'https://www.chileautos.cl/',
        'Upgrade-Insecure-Requests': '1',
        'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
    }
    try:
        session = requests.Session()
        session.headers.update(headers)
        response = session.get(url, timeout=15)
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
# FUNCIONES DE PARSEO Y EXPORTACIÓN
# =============================================================================
def load_brands_list() -> list[str]:
    """Carga la lista de marcas desde el archivo JSON."""
    try:
        # Intenta cargar desde la raíz del proyecto
        json_path = resource_path(os.path.join("docs", "marcas.json"))
        if not os.path.exists(json_path):
             return []
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('marcas', [])
    except Exception as e:
        st.error(f"Error cargando marcas: {e}")
        return []

def parse_auto_details(auto_str: str, brands: list[str]) -> tuple[str, str, str]:
    """
    Analiza la cadena 'auto' para extraer Año, Marca y Modelo.
    Retorna: (Año, Marca, Modelo)
    """
    if not auto_str:
        return "", "Unknown", "Unknown"
    
    year = ""
    brand = "Unknown"
    model = "Unknown"
    
    clean_str = str(auto_str).strip()
    
    # 1. Extraer Año (prioridad al inicio)
    match_start = re.match(r'^((?:19|20)\d{2})\b', clean_str)
    if match_start:
        year = match_start.group(1)
        clean_str = clean_str[match_start.end():].strip()
    else:
        # Buscar en cualquier parte
        match_any = re.search(r'\b((?:19|20)\d{2})\b', clean_str)
        if match_any:
            year = match_any.group(1)
            # Remover el año encontrado
            clean_str = (clean_str[:match_any.start()] + " " + clean_str[match_any.end():]).strip()
            
    clean_str = re.sub(r'\s+', ' ', clean_str) # Limpiar espacios extra

    # 2. Extraer Marca
    # Ordenar marcas por longitud descendente para evitar falsos positivos parciales
    brands_sorted = sorted(brands, key=len, reverse=True)
    
    for b in brands_sorted:
        pattern = r'\b' + re.escape(b) + r'\b'
        if re.search(pattern, clean_str, re.IGNORECASE):
            brand = b # Usar la capitalización del JSON
            # Remover marca del string
            clean_str = re.sub(pattern, '', clean_str, count=1, flags=re.IGNORECASE).strip()
            break
            
    # 3. El resto es el Modelo
    clean_str = re.sub(r'\s+', ' ', clean_str)
    model = clean_str if clean_str else "Unknown"
    
    return year, brand, model

def prepare_export_dataframe(df_source: pd.DataFrame) -> pd.DataFrame:
    """Prepara el DataFrame final para exportación (CSV/Excel) con columnas específicas."""
    brands = load_brands_list()
    export_rows = []
    
    for _, row in df_source.iterrows():
        # Parsing de auto
        raw_auto = row.get('auto', '')
        year, brand, model = parse_auto_details(raw_auto, brands)
        
        # Normalización de teléfono a E.164 (asumiendo +569 por defecto si es chileno, o manteniendo lo que hay)
        # La función normalize_phone del sistema devuelve 9 dígitos. Agregamos +56.
        phone_raw = row.get('telefono', '')
        phone_norm = normalize_phone(phone_raw)
        phone_final = f"+56{phone_norm}" if phone_norm else phone_raw

        export_rows.append({
            "Telefono": phone_final,
            "Nombre": row.get('nombre', ''),
            "Marca": brand,
            "Modelo": model,
            "Año": year,
            "Precio": row.get('precio', 0),
            "Link": row.get('link_auto', '')
        })
        
    return pd.DataFrame(export_rows)

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
            link_auto = sanitize_vehicle_link(link_auto)
            # Aceptar precios con separadores de miles y espacios
            if isinstance(precio, str):
                precio = precio.replace(",", "").replace(" ", "").strip()
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


def search_contacts(phone_query, user):
    """Busca contactos filtrando por teléfono y rol del usuario."""
    if user["role"] == "admin":
        query = "SELECT * FROM contactos WHERE telefono LIKE ?"
        params = [f"%{phone_query}%"]
    else:
        query = (
            "SELECT c.* FROM contactos c JOIN links_contactos l ON c.id_link = l.id "
            "WHERE l.user_id = ? AND c.telefono LIKE ?"
        )
        params = [user["id"], f"%{phone_query}%"]
    return read_query(query, params=params)

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


def sanitize_existing_links(link_id: int) -> dict:
    """Normaliza enlaces de contactos asociados a ``link_id`` y elimina duplicados.

    Parameters
    ----------
    link_id: int
        Identificador de la entrada en ``links_contactos`` cuyos contactos se procesarán.

    Returns
    -------
    dict
        Diccionario con las claves ``sanitized`` y ``deleted`` que indican la cantidad
        de enlaces actualizados y de registros eliminados respectivamente.
    """
    sanitized, deleted = 0, 0
    with get_connection() as con:
        cur = con.cursor()
        cur.execute(
            "SELECT id, link_auto FROM contactos WHERE id_link = ?", (link_id,)
        )
        rows = cur.fetchall()
        for contact_id, link in rows:
            normalized = sanitize_vehicle_link(link)
            cur.execute(
                "SELECT id FROM contactos WHERE link_auto = ? AND id != ?",
                (normalized, contact_id),
            )
            existing = cur.fetchone()
            if existing:
                cur.execute("DELETE FROM contactos WHERE id = ?", (contact_id,))
                deleted += 1
            else:
                if normalized != link:
                    cur.execute(
                        "UPDATE contactos SET link_auto = ? WHERE id = ?",
                        (normalized, contact_id),
                    )
                    sanitized += 1
        con.commit()
    return {"sanitized": sanitized, "deleted": deleted}


def sanitize_all_links() -> dict:
    """Normaliza todos los enlaces de vehículos y elimina duplicados.

    Returns
    -------
    dict
        Diccionario con las claves ``sanitized`` y ``deleted`` que indican la
        cantidad de enlaces actualizados y de registros eliminados
        respectivamente en toda la tabla ``contactos``.
    """
    sanitized, deleted = 0, 0
    with get_connection() as con:
        cur = con.cursor()
        cur.execute("SELECT id, link_auto FROM contactos")
        rows = cur.fetchall()
        seen = {}
        for contact_id, link in rows:
            normalized = sanitize_vehicle_link(link)
            if normalized in seen:
                cur.execute("DELETE FROM contactos WHERE id = ?", (contact_id,))
                deleted += 1
            else:
                if normalized != link:
                    cur.execute(
                        "UPDATE contactos SET link_auto = ? WHERE id = ?",
                        (normalized, contact_id),
                    )
                    sanitized += 1
                seen[normalized] = contact_id
        con.commit()
    return {"sanitized": sanitized, "deleted": deleted}

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


def build_whatsapp_link(plantillas, contacto):
    """Genera un enlace de WhatsApp rotando las plantillas disponibles.

    Parameters
    ----------
    plantillas : Sequence[str]
        Lista de plantillas de mensaje.
    contacto : Mapping
        Diccionario con los datos del contacto.

    Returns
    -------
    tuple[str, str]
        Enlace completo de WhatsApp y el mensaje ya personalizado.
    """
    template = random.choice(list(plantillas))
    mensaje = apply_template(template, contacto)
    telefono = normalize_phone(contacto.get("telefono", ""))
    link = f"https://wa.me/56{telefono}?text=" + urllib.parse.quote(mensaje)
    return link, mensaje


def open_whatsapp(link, msg):
    """Actualiza el mensaje actual y abre el enlace de WhatsApp en una nueva pestaña."""
    st.session_state['cws_msg'] = msg
    components.html(
        f"<script>window.open('{link}', '_blank');</script>",
        height=0,
        width=0,
    )


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
        telefono = normalize_phone(row.get("telefono", ""))
        contacto = row.get("auto") or row.get("nombre", "")
        template = templates[(idx - 1) % len(templates)]
        personalizado = apply_template(template, row.to_dict())
        encoded = urllib.parse.quote(personalizado)
        link = f"https://wa.me/56{telefono}?text={encoded}"
        html_lines.append(f'<a href="{link}">CONTACTO {idx}</a> {contacto}<br>')
    html_lines.extend(["</body>", "</html>"])
    file_name = f"REPORTE_{timestamp}.html"
    return "\n".join(html_lines).encode("utf-8"), file_name


def render_edit_contactos_tab() -> None:
    """Renderiza el tab para editar contactos existentes."""
    st.subheader("Editar contactos por teléfono")
    phone_query = st.text_input("Ingrese parte o el número completo del teléfono a buscar")
    if not phone_query:
        return
    df_search = search_contacts(phone_query, st.session_state['user'])
    if df_search.empty:
        st.warning("No se encontraron contactos para ese número.")
        return

    st.write("Contactos encontrados:")
    opciones = df_search["id"].astype(str) + " - " + df_search["telefono"]
    seleccionado = st.selectbox("Seleccione el contacto a editar", opciones)
    contact_id = int(seleccionado.split(" - ")[0])
    contact = df_search[df_search["id"] == contact_id].iloc[0]

    st.write("Contacto seleccionado:")
    df_contact = contact.to_frame().T.reset_index(drop=True)
    st.dataframe(df_contact, height=150)

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
            if update_contact(
                contact_id,
                new_link_auto,
                new_telefono,
                new_nombre,
                new_auto,
                new_precio,
                new_descripcion,
            ):
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


def render_edit_links_tab() -> None:
    """Renderiza el tab para editar enlaces existentes."""
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
        return

    opciones = df_links["id"].astype(str) + " - " + df_links["link_general"]
    seleccionado = st.selectbox("Seleccione el Link a editar", opciones)
    link_id = int(seleccionado.split(" - ")[0])
    selected_link = df_links[df_links["id"] == link_id].iloc[0]

    st.write("Link seleccionado:")
    df_contact = selected_link.to_frame().T.reset_index(drop=True)
    st.dataframe(df_contact, height=150)

    with st.form("editar_link_form"):
        new_link_general = st.text_input("Link General", value=selected_link["link_general"])
        new_fecha = st.date_input(
            "Fecha de Creación",
            value=datetime.datetime.strptime(selected_link["fecha_creacion"], "%Y-%m-%d").date(),
        )
        new_marca = st.text_input("Marca", value=selected_link["marca"])
        new_descripcion = st.text_area("Descripción", value=selected_link["descripcion"])
        new_user_id = None
        if st.session_state['user']['role'] == 'admin':
            users_df = read_query("SELECT id, username FROM users")
            user_opts = users_df.apply(lambda r: f"{r['id']} - {r['username']}", axis=1)
            if selected_link['user_id'] is not None and selected_link['user_id'] in users_df['id'].values:
                default_idx = int(users_df.index[users_df['id'] == selected_link['user_id']][0])
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


def render_edit_mensajes_tab() -> None:
    """Renderiza el tab para editar mensajes existentes."""
    st.subheader("Editar Mensajes")
    df_mensajes = read_query(
        "SELECT * FROM mensajes WHERE user_id = ?",
        params=[st.session_state['user']['id']],
    )
    if df_mensajes.empty:
        st.warning("No existen mensajes.")
        return

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


def render_edit_tabs() -> None:
    """Renderiza la interfaz de edición organizada en pestañas."""
    tab_contactos, tab_links, tab_mensajes = st.tabs(["Contactos", "Links", "Mensajes"])
    with tab_contactos:
        render_edit_contactos_tab()
    with tab_links:
        render_edit_links_tab()
    with tab_mensajes:
        render_edit_mensajes_tab()

# =============================================================================
# INTERFAZ DE USUARIO: MENÚ Y NAVEGACIÓN
# =============================================================================
if 'page' not in st.session_state:
    st.session_state.page = "Login" if st.session_state['user'] is None else "Crear Link Contactos"

page = render_navigation_sidebar(st.session_state.page)
st.session_state.page = page

# =============================================================================
# PÁGINA: LOGIN
# =============================================================================
if page == "Login":
    render_page_header("Iniciar sesión", "Accede para gestionar consignaciones con tu cuenta.", "🔒")
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
    render_page_header("Crear link de contactos", "Genera nuevos enlaces generales para compartir inventario.", "🔗")
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
    render_page_header("Links de contactos", "Consulta, edita y exporta los enlaces existentes.", "📚")
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
                        default_idx = int(users_df.index[users_df['id'] == selected['user_id']][0])
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
# PÁGINA: SANITIZAR LINKS
# =============================================================================
elif page == "Sanitizar Links":
    render_page_header("Sanitizar links", "Limpia URLs antes de compartirlas con clientes.", "🧹")
    if st.session_state['user']['role'] != 'admin':
        st.warning("Solo el administrador puede sanitizar enlaces.")
    else:
        if st.button("Sanitizar toda la base de datos"):
            result = sanitize_all_links()
            st.success(
                f"Links sanitizados: {result['sanitized']}. Eliminados: {result['deleted']}"
            )

# =============================================================================
# PÁGINA: AGREGAR CONTACTOS
# =============================================================================
elif page == "Agregar Contactos":
    render_page_header("Agregar contactos", "Registra prospectos y relaciona cada contacto con su enlace.", "➕")
    if st.session_state.pop("contacto_agregado", False):
        st.success("Contacto agregado exitosamente.")
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

        def clear_contact_form_fields():
            for k in [
                "link_auto",
                "telefono_input",
                "nombre_input",
                "auto_input",
                "precio_input",
                "descripcion_input",
            ]:
                if k in st.session_state:
                    st.session_state[k] = ""

        if st.session_state.get("clear_contact_form", False):
            clear_contact_form_fields()
            st.session_state["clear_contact_form"] = False

        if st.button("Borrar Campos"):
            clear_contact_form_fields()

        st.text_input("Link del Auto", key="link_auto")

        # Después de obtener el valor del link, normalizarlo y verificar duplicados
        raw_link_auto = st.session_state.get("link_auto", "")
        link_auto_value = sanitize_vehicle_link(raw_link_auto) if raw_link_auto else ""
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
            col_telefono, col_nombre = st.columns(2)
            with col_telefono:
                telefono = st.text_input("Teléfono", value=whatsapp_prefill, key="telefono_input")
                auto_modelo = st.text_input(
                    "Auto",
                    value=nombre_prefill,
                    key="auto_input",
                    help="Ingresa modelo o versión del vehículo.",
                )
            with col_nombre:
                nombre = st.text_input("Nombre", key="nombre_input")
                precio_str = st.text_input(
                    "Precio (ej: 10,500,000)",
                    value=precio_prefill,
                    key="precio_input",
                )
            descripcion_contacto = st.text_area(
                "Descripción del Contacto",
                value=descripcion_prefill,
                key="descripcion_input",
                help="Añade contexto relevante para futuras conversaciones.",
            )
            submitted_contacto = st.form_submit_button("Agregar Contacto", use_container_width=True)
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
                        cursor.execute(
                            '''
                            INSERT INTO contactos (link_auto, telefono, nombre, auto, precio, descripcion, id_link)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            ''',
                            (
                                link_auto_value,
                                telefono,
                                nombre.strip(),
                                auto_modelo.strip(),
                                precio,
                                descripcion_contacto.strip(),
                                link_id,
                            ),
                        )
                        con.commit()
                    st.session_state["contacto_agregado"] = True
                    st.session_state["clear_contact_form"] = True
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("El link del auto ya existe. Ingrese otro enlace.")

# =============================================================================
# PÁGINA: VER CONTACTOS & EXPORTAR
# =============================================================================
elif page == "Ver Contactos & Exportar":
    render_page_header("Ver contactos y exportar", "Filtra registros y descarga reportes para seguimiento.", "👥")
    
    # --- EXPORTACIÓN GLOBAL (NUEVO) ---
    with st.expander("🌍 Exportación Global (Toda la Base de Datos)", expanded=False):
        st.info("Descarga la tabla completa de contactos a los que tienes acceso.")
        if st.button("Preparar Exportación Global"):
            with st.spinner("Cargando todos los contactos..."):
                df_global = fetch_all_contacts_for_user(st.session_state['user'])
                if df_global.empty:
                    st.warning("No hay contactos disponibles para exportar.")
                else:
                    df_global_exp = prepare_export_dataframe(df_global)
                    
                    c_glob1, c_glob2 = st.columns(2)
                    with c_glob1:
                        csv_glob = df_global_exp.to_csv(index=False).encode('utf-8-sig')
                        fname_glob_csv = f"TODOS_contactos_{datetime.date.today().isoformat()}.csv"
                        st.download_button(
                            "📄 Descargar Todo en CSV", 
                            data=csv_glob, 
                            file_name=fname_glob_csv, 
                            mime="text/csv",
                            use_container_width=True
                        )
                    with c_glob2:
                        out_glob_xlsx = BytesIO()
                        with pd.ExcelWriter(out_glob_xlsx, engine='xlsxwriter') as writer:
                            df_global_exp.to_excel(writer, index=False, sheet_name='Todos_Contactos')
                        fname_glob_xlsx = f"TODOS_contactos_{datetime.date.today().isoformat()}.xlsx"
                        st.download_button(
                            "📊 Descargar Todo en Excel", 
                            data=out_glob_xlsx.getvalue(), 
                            file_name=fname_glob_xlsx, 
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
    
    st.divider()

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
        col_nombre, col_auto, col_tel = st.columns(3)
        with col_nombre:
            filter_nombre = st.text_input("Filtrar por Nombre", placeholder="Ej: Juan")
        with col_auto:
            filter_auto = st.text_input("Filtrar por Auto", placeholder="Ej: Corolla")
        with col_tel:
            filter_telefono = st.text_input("Filtrar por Teléfono", placeholder="Incluye prefijo o últimos dígitos")
        filters = {
            "nombre": filter_nombre.strip() if filter_nombre else "",
            "auto": filter_auto.strip() if filter_auto else "",
            "telefono": filter_telefono.strip() if filter_telefono else "",
        }
        df_contactos = fetch_contacts_for_link(link_id, filters)
        st.session_state['df_contactos'] = df_contactos

        # --- EXPORTACIÓN AVANZADA (NUEVO) ---
        if not df_contactos.empty:
            st.markdown("---")
            st.markdown("### 📤 Exportar Datos")
            st.caption("Descarga la lista con columnas detalladas: Telefono, Nombre, Marca, Modelo, Año, Precio, Link.")
            
            # Preparar DF una sola vez
            df_export = prepare_export_dataframe(df_contactos)
            
            col_exp1, col_exp2 = st.columns(2)
            with col_exp1:
                # CSV
                csv_data = df_export.to_csv(index=False).encode('utf-8-sig')
                file_name_csv = f"contactos_{datetime.date.today().isoformat()}.csv"
                st.download_button(
                    label="📄 Exportar a CSV",
                    data=csv_data,
                    file_name=file_name_csv,
                    mime="text/csv",
                    use_container_width=True
                )
            with col_exp2:
                # Excel
                output_xlsx = BytesIO()
                with pd.ExcelWriter(output_xlsx, engine='xlsxwriter') as writer:
                    df_export.to_excel(writer, index=False, sheet_name='Contactos')
                file_name_xlsx = f"contactos_{datetime.date.today().isoformat()}.xlsx"
                st.download_button(
                    label="📊 Exportar a Excel",
                    data=output_xlsx.getvalue(),
                    file_name=file_name_xlsx,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            st.markdown("---")

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
                    f"https://wa.me/56{normalize_phone(r['telefono'])}?text=" +
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
                    "Descargar Excel (Original)",
                    data=output.getvalue(),
                    file_name="contactos_simple.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            with col2:
                html_content, html_name = generate_html(df_contactos, messages_raw)
                st.download_button(
                    "Generar HTML Mensajería",
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
# PÁGINA: CWS CHAT WHATSAPP
# =============================================================================
elif page == "CWS Chat WhatsApp":
    render_page_header("CWS Chat WhatsApp", "Genera mensajes personalizados listos para copiar en WhatsApp.", "💬")
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
            lambda row: f"{row['marca']} - {row['descripcion']}", axis=1
        )
        link_selected = st.selectbox(
            "Selecciona el Link Contactos", df_links['display']
        )
        selected_link = df_links[df_links['display'] == link_selected].iloc[0]
        link_id = selected_link['id']

        mensajes_df = read_query(
            "SELECT * FROM mensajes WHERE user_id = ?",
            params=[st.session_state['user']['id']],
        )
        if mensajes_df.empty:
            st.warning("No existen mensajes. Agregue uno en la sección Mensajes.")
        else:
            mensajes_df['display'] = mensajes_df.apply(
                lambda r: f"{r['id']} - {r['descripcion'][:30]}", axis=1
            )
            msg_disp = st.multiselect(
                "Selecciona las plantillas", mensajes_df['display']
            )
            if msg_disp:
                plantillas = mensajes_df[
                    mensajes_df['display'].isin(msg_disp)
                ]['descripcion'].tolist()
                df_contactos = fetch_contacts_for_link(link_id)
                if df_contactos.empty:
                    st.info("No hay contactos para este link.")
                else:
                    header = st.columns([3, 1, 2, 2, 1])
                    header[0].write("Auto")
                    header[1].write("Precio")
                    header[2].write("Teléfono")
                    header[3].write("Link_CA")
                    header[4].write("")
                    for _, row in df_contactos.iterrows():
                        cols = st.columns([3, 1, 2, 2, 1])
                        cols[0].write(row['auto'])
                        cols[1].write(row['precio'])
                        cols[2].write(row['telefono'])
                        cols[3].markdown(
                            f"[Link_CA]({row['link_auto']})", unsafe_allow_html=True
                        )
                        link, msg = build_whatsapp_link(
                            plantillas, row.to_dict()
                        )
                        cols[4].button(
                            "Link_WS",
                            key=f"ws_{row['id']}",
                            on_click=open_whatsapp,
                            args=(link, msg),
                        )
            else:
                st.info("Seleccione al menos una plantilla.")

# =============================================================================
# PÁGINA: MENSAJES
# =============================================================================
elif page == "Mensajes":
    render_page_header("Plantillas de mensaje", "Guarda respuestas frecuentes y optimiza la atención al cliente.", "✉️")
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
# PÁGINA: CLIENTES INTERESADOS
# =============================================================================
elif page == "Clientes Interesados":
    render_interested_clients_page()

# =============================================================================
# PÁGINA: EDITAR
# =============================================================================
elif page == "Editar":
    render_page_header("Editar registros", "Actualiza información existente sin duplicar datos.", "🛠️")
    render_edit_tabs()

# =============================================================================
# PÁGINA: ADMIN USUARIOS
# =============================================================================
elif page == "Contactos Restringidos":
    render_page_header("Contactos restringidos", "Gestiona el listado global de números excluidos de exportaciones.", "🚫")
    if st.session_state['user']['role'] != 'admin':
        st.warning("Solo el administrador puede gestionar la lista de restricciones.")
    else:
        telefono_input = st.text_input("Número a restringir", key="restricted_phone_input")
        restricted_df = list_restricted_numbers()
        if 'restricted_reason' not in st.session_state:
            st.session_state['restricted_reason'] = ''
        if st.session_state.pop('restricted_form_reset', False):
            st.session_state['restricted_reason'] = ''


        normalized = normalize_phone(telefono_input) if telefono_input else ""
        if telefono_input:
            if normalized:
                st.caption(f"Se analizará el teléfono normalizado: **{normalized}**")
                contacto_df = get_contacts_by_phone(telefono_input)
                if contacto_df.empty:
                    st.info("No se encontraron contactos con ese número.")
                else:
                    links_count = contacto_df['id_link'].dropna().nunique()
                    st.metric("Links asociados", int(links_count) if links_count else 0)
                    st.dataframe(contacto_df)
            else:
                st.warning("Ingresa un número con dígitos válidos.")

        if normalized and not restricted_df.empty:
            coincidencias = restricted_df[restricted_df['telefono_normalizado'] == normalized]
            if not coincidencias.empty:
                fila = coincidencias.iloc[0]
                responsable = fila.get('created_by_username') or 'usuario desconocido'
                st.info(
                    f"El número ya está restringido desde {fila['created_at']} por {responsable}.",
                )

        with st.form("restricted_number_form"):
            motivo = st.text_area(
                "Motivo (opcional)",
                key="restricted_reason",
                placeholder="Describe brevemente la razón de la restricción.",
            )
            submit_restricted = st.form_submit_button("Guardar número restringido")

        if submit_restricted:
            success, message = add_restricted_number(
                telefono_input,
                motivo,
                st.session_state['user']['id'],
            )
            if success:
                st.success(message)
                st.session_state['restricted_form_reset'] = True
                st.rerun()
            else:
                st.error(message)

        st.subheader("Lista de números restringidos")
        if restricted_df.empty:
            st.info("No hay números restringidos registrados.")
        else:
            display_df = restricted_df.rename(
                columns={
                    'telefono_original': 'Teléfono',
                    'telefono_normalizado': 'Teléfono normalizado',
                    'motivo': 'Motivo',
                    'created_at': 'Registrado el',
                    'created_by_username': 'Registrado por',
                }
            )
            columnas = [col for col in ['Teléfono', 'Teléfono normalizado', 'Motivo', 'Registrado el', 'Registrado por'] if col in display_df.columns]
            st.dataframe(display_df[columnas])

elif page == "Admin Usuarios":
    if st.session_state['user']['role'] != 'admin':
        st.error("Acceso denegado")
    else:
        render_page_header("Administración de usuarios", "Gestiona cuentas y roles del equipo.", "🧑‍💼")
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
