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
