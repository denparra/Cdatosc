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
