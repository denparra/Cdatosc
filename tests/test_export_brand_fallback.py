import os
import sys
import importlib
import sqlite3
import pandas as real_pd
from unittest.mock import MagicMock, patch


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def import_app():
    with patch.dict(
        sys.modules,
        {
            "streamlit": MagicMock(),
            "streamlit.components": MagicMock(),
            "streamlit.components.v1": MagicMock(),
            "requests": MagicMock(),
            "bs4": MagicMock(),
        },
    ):
        sys.path.insert(0, ROOT)
        import src.app
        importlib.reload(src.app)
        sys.path.remove(ROOT)
        return src.app


def test_prepare_export_dataframe_uses_brand_fallback():
    app = import_app()
    df = real_pd.DataFrame(
        [
            {
                "telefono": "991234567",
                "nombre": "Ana",
                "auto": "2020 modelo sin marca reconocida",
                "precio": 1000,
                "link_auto": "https://x/y",
                "marca": "RAM",
            }
        ]
    )
    with patch.object(app, "load_brands_list", return_value=[]):
        out = app.prepare_export_dataframe(df)
    assert out.iloc[0]["Marca"] == "RAM"


def test_fetch_contacts_for_link_includes_marca_column():
    app = import_app()
    conn = sqlite3.connect(":memory:")
    conn.create_function("normalize_phone", 1, app.normalize_phone)
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
        CREATE TABLE contactos_restringidos (
            telefono_normalizado TEXT PRIMARY KEY,
            telefono_original TEXT,
            motivo TEXT,
            created_at TEXT,
            created_by INTEGER
        );
        CREATE TABLE contactos_restringidos_link (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telefono_normalizado TEXT,
            telefono_original TEXT,
            link_id INTEGER,
            motivo TEXT,
            created_at TEXT,
            created_by INTEGER
        );
        CREATE TABLE contactos_restringidos_contacto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telefono_normalizado TEXT,
            telefono_original TEXT,
            contact_id INTEGER,
            motivo TEXT,
            created_at TEXT,
            created_by INTEGER
        );
        INSERT INTO links_contactos (id, link_general, fecha_creacion, marca, descripcion, user_id)
        VALUES (1, 'a', '2024-01-01', 'JEEP', 'DESC', 1);
        INSERT INTO contactos (link_auto, telefono, nombre, auto, precio, descripcion, id_link)
        VALUES ('auto-1', '991234567', 'Ana', '2021 Jeep Renegade', 100, 'd', 1);
        """
    )
    with patch.object(app, "get_connection", return_value=conn), patch.object(app, "pd", real_pd):
        df = app.fetch_contacts_for_link(1, {})
    assert not df.empty
    assert "marca" in df.columns
    assert df.iloc[0]["marca"] == "JEEP"
