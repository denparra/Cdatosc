import os
import sys
import importlib
import urllib.parse
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


def test_build_whatsapp_link_rotates_templates():
    app = import_app()
    contacto = {"telefono": "911111111", "nombre": "Ana", "auto": "Sedan"}
    plantillas = ["Hola {nombre}", "Adios {auto}"]
    with patch.object(app.random, "choice", side_effect=plantillas):
        url1, msg1 = app.build_whatsapp_link(plantillas, contacto)
        url2, msg2 = app.build_whatsapp_link(plantillas, contacto)
    assert msg1 == "Hola Ana"
    assert msg2 == "Adios Sedan"
    assert url1.startswith("https://wa.me/56")
    assert urllib.parse.unquote(url1.split("?text=")[1]) == msg1
    assert urllib.parse.unquote(url2.split("?text=")[1]) == msg2
