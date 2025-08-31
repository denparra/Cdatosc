import sqlite3
import importlib
import os
import sys
from unittest.mock import MagicMock, patch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class FakeDataFrame(list):
    @property
    def empty(self):
        return len(self) == 0

    class _ILoc:
        def __init__(self, data):
            self.data = data

        def __getitem__(self, idx):
            return self.data[idx]

    @property
    def iloc(self):
        return FakeDataFrame._ILoc(self)

    def __getitem__(self, key):
        if isinstance(key, str):
            return [row[key] for row in self]
        return list.__getitem__(self, key)


def import_app():
    fake_pd = MagicMock()

    def read_sql_query(query, con, params=None):
        cur = con.cursor()
        cur.execute(query, params or [])
        cols = [c[0] for c in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        return FakeDataFrame(rows)

    fake_pd.read_sql_query.side_effect = read_sql_query

    with patch.dict(
        sys.modules,
        {
            "streamlit": MagicMock(),
            "streamlit.components": MagicMock(),
            "streamlit.components.v1": MagicMock(),
            "requests": MagicMock(),
            "bs4": MagicMock(),
            "pandas": fake_pd,
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
            link_auto TEXT UNIQUE,
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
        "INSERT INTO links_contactos (link_general, fecha_creacion, marca, descripcion, user_id) VALUES (?,?,?,?,?)",
        ("lg2", "2024-01-01", "m", "d", 2),
    )
    conn.execute(
        "INSERT INTO contactos (link_auto, telefono, nombre, auto, precio, descripcion, id_link) VALUES (?,?,?,?,?,?,?)",
        ("a1", "111", "n1", "auto1", 100, "d1", 1),
    )
    conn.execute(
        "INSERT INTO contactos (link_auto, telefono, nombre, auto, precio, descripcion, id_link) VALUES (?,?,?,?,?,?,?)",
        ("a2", "222", "n2", "auto2", 200, "d2", 2),
    )
    conn.execute(
        "INSERT INTO contactos (link_auto, telefono, nombre, auto, precio, descripcion, id_link) VALUES (?,?,?,?,?,?,?)",
        ("a3", "333", "n3", "auto3", 300, "d3", None),
    )
    conn.commit()
    return conn


def test_search_contacts_filters_by_user_and_role():
    app = import_app()
    conn = setup_db()
    with patch.object(app, "get_connection", return_value=conn):
        user = {"id": 1, "role": "user"}
        df_user = app.search_contacts("222", user)
        assert df_user.empty
        df_user = app.search_contacts("111", user)
        assert len(df_user) == 1
        assert df_user.iloc[0]["telefono"] == "111"
        admin = {"id": 99, "role": "admin"}
        df_admin = app.search_contacts("333", admin)
        assert len(df_admin) == 1
        assert df_admin.iloc[0]["telefono"] == "333"
