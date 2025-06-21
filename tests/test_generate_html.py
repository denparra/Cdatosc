import os
import sys
import importlib
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
