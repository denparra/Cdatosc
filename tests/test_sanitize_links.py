import importlib
import os
import sys
import sqlite3
from unittest.mock import MagicMock, patch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def import_app():
    with patch.dict(
        sys.modules,
        {
            "streamlit": MagicMock(),
            "requests": MagicMock(),
            "bs4": MagicMock(),
            "pandas": MagicMock(),
        },
    ):
        sys.path.insert(0, ROOT)
        import src.app
        importlib.reload(src.app)
        sys.path.remove(ROOT)
        return src.app


def setup_db():
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
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
            link_auto TEXT UNIQUE NOT NULL,
            telefono TEXT,
            nombre TEXT,
            auto TEXT,
            precio REAL,
            descripcion TEXT,
            id_link INTEGER
        );
        """
    )
    conn.execute(
        "INSERT INTO links_contactos (link_general, fecha_creacion, marca, descripcion, user_id) VALUES (?,?,?,?,?)",
        ("lg1", "2024-01-01", "m", "d", 1),
    )
    conn.execute(
        "INSERT INTO contactos (link_auto, telefono, nombre, auto, precio, descripcion, id_link) VALUES (?,?,?,?,?,?,?)",
        ("https://example.com/car?a=1", "111", "n1", "auto1", 100, "d1", 1),
    )
    conn.execute(
        "INSERT INTO contactos (link_auto, telefono, nombre, auto, precio, descripcion, id_link) VALUES (?,?,?,?,?,?,?)",
        ("https://example.com/car?a=2", "222", "n2", "auto2", 200, "d2", 1),
    )
    conn.commit()
    return conn


def test_sanitize_existing_links_removes_duplicates():
    app = import_app()
    conn = setup_db()
    with patch.object(app, "get_connection", return_value=conn):
        result = app.sanitize_existing_links(1)
        assert result["sanitized"] == 1
        assert result["deleted"] == 1
        cur = conn.cursor()
        cur.execute("SELECT link_auto FROM contactos")
        rows = [r[0] for r in cur.fetchall()]
        assert rows == ["https://example.com/car"]
