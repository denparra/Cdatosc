import importlib
import os
import sqlite3
import sys
import tempfile
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


def test_has_admin_access_accepts_superadmin_role():
    app = import_app()
    assert app.has_admin_access({"role": "superadmin"}) is True
    assert app.has_admin_access({"role": "admin"}) is True
    assert app.has_admin_access({"role": "user"}) is False


def test_normalize_db_alias_keeps_safe_slug():
    app = import_app()
    assert app.normalize_db_alias(" Sucursal Norte 01 ") == "sucursal_norte_01"


def test_build_menu_options_adds_superadmin_page():
    app = import_app()
    options = app.build_menu_options({"role": "superadmin"})
    assert "SuperAdmin Multi-BD" in options
    assert "Admin Usuarios" in options


def test_validate_external_db_schema_reports_missing_tables():
    app = import_app()
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        con = sqlite3.connect(db_path)
        con.execute("CREATE TABLE contactos (id INTEGER PRIMARY KEY)")
        con.commit()
        con.close()
        ok, msg = app.validate_external_db_schema(db_path)
        assert ok is False
        assert "Faltan tablas" in msg
    finally:
        pass


def test_validate_external_db_schema_accepts_expected_minimum():
    app = import_app()
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        con = sqlite3.connect(db_path)
        con.execute("CREATE TABLE contactos (id INTEGER PRIMARY KEY)")
        con.execute("CREATE TABLE links_contactos (id INTEGER PRIMARY KEY)")
        con.execute("CREATE TABLE users (id INTEGER PRIMARY KEY)")
        con.commit()
        con.close()
        ok, msg = app.validate_external_db_schema(db_path)
        assert ok is True
        assert msg == "OK"
    finally:
        pass


def test_replace_file_with_retry_recovers_after_transient_lock():
    app = import_app()
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "source.db")
        dst = os.path.join(tmp, "target.db")
        with open(src, "wb") as f:
            f.write(b"new")
        with open(dst, "wb") as f:
            f.write(b"old")

        state = {"calls": 0}
        real_replace = os.replace

        def flaky_replace(src_path, dst_path):
            state["calls"] += 1
            if state["calls"] == 1:
                raise OSError("winerror 32 simulated lock")
            return real_replace(src_path, dst_path)

        with patch.object(app.os, "replace", side_effect=flaky_replace):
            ok, err = app.replace_file_with_retry(src, dst, retries=3, delay_seconds=0)

        assert ok is True
        assert err == ""
        assert state["calls"] == 2
        with open(dst, "rb") as f:
            assert f.read() == b"new"
