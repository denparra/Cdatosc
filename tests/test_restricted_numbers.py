import os
import sys
import importlib
import sqlite3
import pandas as real_pd
from unittest.mock import MagicMock, patch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def import_app():
    mocks = {
        "streamlit": MagicMock(),
        "streamlit.components": MagicMock(),
        "streamlit.components.v1": MagicMock(),
        "requests": MagicMock(),
        "bs4": MagicMock(),
    }
    with patch.dict(sys.modules, mocks):
        sys.path.insert(0, ROOT)
        import src.app
        importlib.reload(src.app)
        sys.path.remove(ROOT)
        return src.app


def setup_connection(app):
    conn = sqlite3.connect(":memory:")
    conn.create_function("normalize_phone", 1, app.normalize_phone)
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.executescript(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password_hash TEXT,
            role TEXT
        );
        CREATE TABLE links_contactos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_general TEXT,
            fecha_creacion TEXT,
            marca TEXT,
            descripcion TEXT,
            user_id INTEGER
        );
        CREATE TABLE contactos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_auto TEXT UNIQUE,
            telefono TEXT,
            nombre TEXT,
            auto TEXT,
            precio REAL,
            descripcion TEXT,
            id_link INTEGER
        );
        CREATE TABLE contactos_restringidos (
            telefono_normalizado TEXT PRIMARY KEY,
            telefono_original TEXT NOT NULL,
            motivo TEXT,
            created_at TEXT NOT NULL,
            created_by INTEGER NOT NULL
        );
        CREATE TABLE contactos_restringidos_link (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telefono_normalizado TEXT NOT NULL,
            telefono_original TEXT NOT NULL,
            link_id INTEGER NOT NULL,
            motivo TEXT,
            created_at TEXT NOT NULL,
            created_by INTEGER NOT NULL,
            UNIQUE(telefono_normalizado, link_id)
        );
        CREATE TABLE contactos_restringidos_contacto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telefono_normalizado TEXT NOT NULL,
            telefono_original TEXT NOT NULL,
            contact_id INTEGER NOT NULL,
            motivo TEXT,
            created_at TEXT NOT NULL,
            created_by INTEGER NOT NULL,
            UNIQUE(contact_id)
        );
        CREATE TABLE mensajes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descripcion TEXT,
            user_id INTEGER
        );
        """
    )
    conn.execute(
        "INSERT INTO users (id, username, password_hash, role) VALUES (1, 'admin', '', 'admin')"
    )
    conn.execute(
        "INSERT INTO links_contactos (id, link_general, fecha_creacion, marca, descripcion, user_id)"
        " VALUES (1, 'lg', '2024-01-01', 'Marca', 'Descripcion', 1)"
    )
    conn.execute(
        "INSERT INTO contactos (link_auto, telefono, nombre, auto, precio, descripcion, id_link)"
        " VALUES ('auto-1', '99 123 4567', 'Juan', 'Sedan', 100.0, 'desc', 1)"
    )
    conn.commit()
    return conn


def test_fetch_contacts_excludes_restricted_numbers():
    app = import_app()
    conn = setup_connection(app)
    with patch.object(app, "get_connection", return_value=conn), \
         patch.object(app, "pd", real_pd):
        df_initial = app.fetch_contacts_for_link(1, {})
        assert len(df_initial) == 1

        success, message = app.add_restricted_number("991234567", "Duplicado", 1)
        assert success
        assert "restringida" in message

        df_filtered = app.fetch_contacts_for_link(1, {})
        assert df_filtered.empty

        df_including = app.fetch_contacts_for_link(1, {}, include_restricted=True)
        assert len(df_including) == 1

        listado = app.list_restricted_numbers()
        assert not listado.empty
        assert listado.iloc[0]["telefono_normalizado"] == "991234567"


def test_fetch_contacts_respects_contact_scoped_restricted_numbers():
    app = import_app()
    conn = setup_connection(app)
    conn.execute(
        "INSERT INTO links_contactos (id, link_general, fecha_creacion, marca, descripcion, user_id) VALUES (2, 'lg2', '2024-01-01', 'Marca2', 'Desc2', 1)"
    )
    conn.execute(
        "INSERT INTO contactos (link_auto, telefono, nombre, auto, precio, descripcion, id_link) VALUES ('auto-2', '99 123 4567', 'Ana', 'SUV', 200.0, 'desc2', 2)"
    )
    conn.commit()

    with patch.object(app, "get_connection", return_value=conn), \
         patch.object(app, "pd", real_pd):
        success, _ = app.add_restricted_number("991234567", "Solo contacto 1", 1, scope="contact", contact_id=1)
        assert success

        df_link1 = app.fetch_contacts_for_link(1, {})
        assert df_link1.empty

        df_link2 = app.fetch_contacts_for_link(2, {})
        assert len(df_link2) == 1
        assert df_link2.iloc[0]["id_link"] == 2


def test_remove_global_restriction_unblocks_contact():
    app = import_app()
    conn = setup_connection(app)
    with patch.object(app, "get_connection", return_value=conn), \
         patch.object(app, "pd", real_pd):
        success, _ = app.add_restricted_number("991234567", "Global", 1, scope="global")
        assert success
        df_blocked = app.fetch_contacts_for_link(1, {})
        assert df_blocked.empty

        ok, _ = app.remove_restriction("GLOBAL", "991234567")
        assert ok

        df_unblocked = app.fetch_contacts_for_link(1, {})
        assert len(df_unblocked) == 1


def test_remove_contact_restriction_unblocks_only_that_contact():
    app = import_app()
    conn = setup_connection(app)
    conn.execute(
        "INSERT INTO links_contactos (id, link_general, fecha_creacion, marca, descripcion, user_id) VALUES (2, 'lg2', '2024-01-01', 'Marca2', 'Desc2', 1)"
    )
    conn.execute(
        "INSERT INTO contactos (id, link_auto, telefono, nombre, auto, precio, descripcion, id_link) VALUES (2, 'auto-2', '99 123 4567', 'Ana', 'SUV', 200.0, 'desc2', 2)"
    )
    conn.commit()

    with patch.object(app, "get_connection", return_value=conn), \
         patch.object(app, "pd", real_pd):
        success, _ = app.add_restricted_number("991234567", "Contacto 1", 1, scope="contact", contact_id=1)
        assert success

        assert app.fetch_contacts_for_link(1, {}).empty
        assert len(app.fetch_contacts_for_link(2, {})) == 1

        ok, _ = app.remove_restriction("CONTACTO", "991234567", contact_id=1)
        assert ok

        assert len(app.fetch_contacts_for_link(1, {})) == 1
