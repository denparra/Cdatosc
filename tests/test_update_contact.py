import sqlite3
import importlib
import os
import sys
from unittest.mock import MagicMock, patch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def import_app():
    with patch.dict(
        sys.modules,
        {
            "streamlit": MagicMock(),
            "streamlit.components": MagicMock(),
            "streamlit.components.v1": MagicMock(),
            "pandas": MagicMock(),
            "requests": MagicMock(),
            "bs4": MagicMock(),
        },
    ):
        sys.path.insert(0, ROOT)
        import src.app
        importlib.reload(src.app)
        sys.path.remove(ROOT)
        return src.app


def make_contact_db():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE contactos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_auto TEXT UNIQUE NOT NULL,
            telefono TEXT NOT NULL,
            nombre TEXT NOT NULL,
            auto TEXT NOT NULL,
            precio REAL NOT NULL,
            descripcion TEXT NOT NULL,
            id_link INTEGER
        )
        """
    )
    conn.execute(
        "INSERT INTO contactos (link_auto, telefono, nombre, auto, precio, descripcion) VALUES (?,?,?,?,?,?)",
        ("a", "111", "n", "auto", 1000, "desc"),
    )
    conn.commit()
    return conn


def make_reassign_db():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE links_contactos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_general TEXT,
            fecha_creacion TEXT,
            marca TEXT,
            descripcion TEXT,
            user_id INTEGER
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE contactos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_auto TEXT UNIQUE NOT NULL,
            telefono TEXT NOT NULL,
            nombre TEXT NOT NULL,
            auto TEXT NOT NULL,
            precio REAL NOT NULL,
            descripcion TEXT NOT NULL,
            id_link INTEGER
        )
        """
    )
    conn.execute(
        "INSERT INTO links_contactos (id, link_general, fecha_creacion, marca, descripcion, user_id) VALUES (1, 'l1', '2024-01-01', 'A', 'A1', 10)"
    )
    conn.execute(
        "INSERT INTO links_contactos (id, link_general, fecha_creacion, marca, descripcion, user_id) VALUES (2, 'l2', '2024-01-01', 'B', 'B1', 10)"
    )
    conn.execute(
        "INSERT INTO links_contactos (id, link_general, fecha_creacion, marca, descripcion, user_id) VALUES (3, 'l3', '2024-01-01', 'C', 'C1', 99)"
    )
    conn.execute(
        "INSERT INTO contactos (id, link_auto, telefono, nombre, auto, precio, descripcion, id_link) VALUES (1, 'a1', '111', 'n', 'auto', 1000, 'desc', 1)"
    )
    conn.commit()
    return conn


def test_update_contact_handles_thousands_separator():
    conn = make_contact_db()
    app = import_app()
    with patch.object(app, "get_connection", return_value=conn):
        result = app.update_contact(1, "a", "111", "n", "auto", "10,500", "desc")
    assert result is True
    cur = conn.cursor()
    cur.execute("SELECT precio FROM contactos WHERE id=1")
    value = cur.fetchone()[0]
    assert value == 10500.0


def test_reassign_contact_to_link_allows_same_owner_user():
    conn = make_reassign_db()
    app = import_app()
    user = {"id": 10, "role": "user"}
    with patch.object(app, "get_connection", return_value=conn):
        ok, _ = app.reassign_contact_to_link(1, 2, user)
    assert ok is True
    cur = conn.cursor()
    cur.execute("SELECT id_link FROM contactos WHERE id=1")
    assert cur.fetchone()[0] == 2


def test_reassign_contact_to_link_rejects_other_owner_user():
    conn = make_reassign_db()
    app = import_app()
    user = {"id": 10, "role": "user"}
    with patch.object(app, "get_connection", return_value=conn):
        ok, message = app.reassign_contact_to_link(1, 3, user)
    assert ok is False
    assert "permisos" in message.lower()
