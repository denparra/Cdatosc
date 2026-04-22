import importlib
import os
import sys
from unittest.mock import MagicMock, patch

import pandas as real_pd


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


def _sample_export_df():
    return real_pd.DataFrame(
        [
            {"Telefono": "+56911111111", "Nombre": "Ana", "Marca": "TOYOTA", "Modelo": "Yaris", "Año": "2020", "Precio": 1, "Link": "a"},
            {"Telefono": "+56922222222", "Nombre": "Ben", "Marca": "KIA", "Modelo": "Rio", "Año": "2021", "Precio": 2, "Link": "b"},
            {"Telefono": "+56933333333", "Nombre": "Carla", "Marca": "TOYOTA", "Modelo": "Corolla", "Año": "", "Precio": 3, "Link": "c"},
        ]
    )


def test_apply_vehicle_export_filters_without_filters_returns_all_rows():
    app = import_app()
    df = _sample_export_df()

    out = app.apply_vehicle_export_filters(df, [], None, include_missing_year=True)

    assert len(out) == 3


def test_apply_vehicle_export_filters_by_year_range_inclusive():
    app = import_app()
    df = _sample_export_df()

    out = app.apply_vehicle_export_filters(df, [], (2020, 2021), include_missing_year=False)

    assert len(out) == 2
    assert set(out["Año"].tolist()) == {"2020", "2021"}


def test_apply_vehicle_export_filters_by_brand():
    app = import_app()
    df = _sample_export_df()

    out = app.apply_vehicle_export_filters(df, ["TOYOTA"], None, include_missing_year=True)

    assert len(out) == 2
    assert set(out["Marca"].tolist()) == {"TOYOTA"}


def test_apply_vehicle_export_filters_by_brand_and_year_range():
    app = import_app()
    df = _sample_export_df()

    out = app.apply_vehicle_export_filters(df, ["TOYOTA"], (2020, 2020), include_missing_year=False)

    assert len(out) == 1
    assert out.iloc[0]["Nombre"] == "Ana"


def test_apply_vehicle_export_filters_excludes_missing_year_by_default():
    app = import_app()
    df = _sample_export_df()

    out = app.apply_vehicle_export_filters(df, [], (2020, 2021), include_missing_year=False)

    assert "Carla" not in set(out["Nombre"].tolist())


def test_apply_vehicle_export_filters_can_include_missing_year_in_range_mode():
    app = import_app()
    df = _sample_export_df()

    out = app.apply_vehicle_export_filters(df, [], (2020, 2021), include_missing_year=True)

    assert "Carla" in set(out["Nombre"].tolist())
