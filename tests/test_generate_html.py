import os
import sys
import importlib
from unittest.mock import MagicMock, patch
import urllib.parse

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


def test_generate_html_creates_links():
    app = import_app()
    df = MagicMock()

    class Row(dict):
        def to_dict(self):
            return dict(self)

    df.iterrows.return_value = iter(
        [(0, Row({"telefono": "912345678", "auto": "A", "nombre": "X"}))]
    )
    content, name = app.generate_html(df, "Hola")
    html = content.decode("utf-8")
    assert "CONTACTO 1" in html
    assert "data:image" not in html


def test_generate_html_rotates_messages():
    app = import_app()
    df = MagicMock()

    class Row(dict):
        def to_dict(self):
            return dict(self)

    rows = [
        Row({"telefono": "911111111", "auto": "A", "nombre": "Uno"}),
        Row({"telefono": "922222222", "auto": "B", "nombre": "Dos"}),
    ]
    df.iterrows.return_value = iter(enumerate(rows))
    msgs = ["Hola {nombre}", "Adios {auto}"]
    content, _ = app.generate_html(df, msgs)
    html = content.decode("utf-8")
    links = [
        urllib.parse.unquote(part.split("=")[1])
        for part in [link.split("?")[1] for link in [
            l.split('"')[1] for l in html.splitlines() if "href=" in l
        ]]
    ]
    assert "Hola Uno" in links[0]
    assert "Adios B" in links[1]
