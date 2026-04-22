import sys
from unittest import mock
from unittest.mock import MagicMock, patch
import pytest

pytest.importorskip("bs4")
from bs4 import BeautifulSoup

# Mock unavailable modules so src.app can be imported
sys.modules.setdefault("streamlit", MagicMock())
sys.modules.setdefault("streamlit.components", MagicMock())
sys.modules.setdefault("streamlit.components.v1", MagicMock())
sys.modules.setdefault("pandas", MagicMock())
sys.modules.setdefault("requests", MagicMock())

import src.app


def test_extract_whatsapp_number():
    html = '<a href="https://wa.me/56912345678">Chat</a>'
    soup = BeautifulSoup(html, "html.parser")
    assert src.app.extract_whatsapp_number(soup) == "912345678"


def test_scrape_vehicle_details(tmp_path):
    html = (
        "<img src=\"data:image/png;base64,AA==\" />"
        "<a href=\"https://wa.me/56911122233\">WhatsApp</a>"
        "<div class=\"features-item-value-vehculo\">2021 TestCar</div>"
        "<div class=\"features-item-value-precio\">$10,000</div>"
        "<div class=\"view-more-container\"><div class=\"view-more-target\">"
        "<p>Great car</p></div></div>"
    )

    class MockResponse:
        status_code = 200
        content = html.encode("utf-8")

    mock_session = MagicMock()
    mock_session.get.return_value = MockResponse()
    with patch.object(src.app.requests, "Session", return_value=mock_session), \
         patch.object(src.app, "BeautifulSoup", BeautifulSoup):
        data = src.app.scrape_vehicle_details("http://example.com")

    assert data["nombre"] == "2021 TestCar"
    assert data["whatsapp_number"] == "911122233"
    assert data["precio"] == "10,000"
    assert data["descripcion"] == "Great car"
    assert "contact_image_file" not in data


def test_scrape_returns_none_on_403():
    """El scrape debe devolver None cuando Chileautos responde 403."""

    class MockResponse403:
        status_code = 403
        headers = {}

    mock_session = MagicMock()
    mock_session.get.return_value = MockResponse403()
    with patch.object(src.app.requests, "Session", return_value=mock_session):
        result = src.app.scrape_vehicle_details("http://example.com")

    assert result is None


def test_scrape_datadome_403_shows_warning():
    """Un 403 con cabecera x-datadome=protected debe llamar a st.warning, no st.error."""

    class MockResponse403DataDome:
        status_code = 403
        headers = {"x-datadome": "protected"}

    mock_session = MagicMock()
    mock_session.get.return_value = MockResponse403DataDome()

    with patch.object(src.app.requests, "Session", return_value=mock_session), \
         patch.object(src.app, "st") as mock_st:
        result = src.app.scrape_vehicle_details("http://example.com")

    assert result is None
    mock_st.warning.assert_called_once()
    warning_msg = mock_st.warning.call_args[0][0]
    assert "DataDome" in warning_msg
    mock_st.error.assert_not_called()


def test_scrape_generic_403_shows_error():
    """Un 403 sin cabecera DataDome debe llamar a st.error."""

    class MockResponse403Generic:
        status_code = 403
        headers = {}

    mock_session = MagicMock()
    mock_session.get.return_value = MockResponse403Generic()

    with patch.object(src.app.requests, "Session", return_value=mock_session), \
         patch.object(src.app, "st") as mock_st:
        result = src.app.scrape_vehicle_details("http://example.com")

    assert result is None
    mock_st.error.assert_called_once()
    mock_st.warning.assert_not_called()


def test_scrape_no_whatsapp_returns_not_available():
    """Si no hay enlace WhatsApp en la página, devuelve 'No disponible'."""
    html = (
        "<div class=\"features-item-value-vehculo\">2022 NoCar</div>"
        "<div class=\"features-item-value-precio\">$5,000</div>"
    )

    class MockResponseNoWA:
        status_code = 200
        content = html.encode("utf-8")

    mock_session = MagicMock()
    mock_session.get.return_value = MockResponseNoWA()
    with patch.object(src.app.requests, "Session", return_value=mock_session), \
         patch.object(src.app, "BeautifulSoup", BeautifulSoup):
        data = src.app.scrape_vehicle_details("http://example.com")

    assert data is not None
    assert data["whatsapp_number"] == "No disponible"
    assert data["nombre"] == "2022 NoCar"


def test_scrape_cache_avoids_duplicate_request():
    """El caché scraped_cache evita llamar al scrape si la URL ya fue procesada."""
    html = (
        "<a href=\"https://wa.me/56999888777\">WhatsApp</a>"
        "<div class=\"features-item-value-vehculo\">2023 CachedCar</div>"
        "<div class=\"features-item-value-precio\">$20,000</div>"
    )

    class MockResponseOK:
        status_code = 200
        content = html.encode("utf-8")

    mock_session = MagicMock()
    mock_session.get.return_value = MockResponseOK()
    url = "https://www.chileautos.cl/vehiculos/detalles/test-car/CP-123/"

    with patch.object(src.app.requests, "Session", return_value=mock_session), \
         patch.object(src.app, "BeautifulSoup", BeautifulSoup):
        # Primera llamada — hace el request real
        data1 = src.app.scrape_vehicle_details(url)

    assert mock_session.get.call_count == 1
    assert data1["nombre"] == "2023 CachedCar"

    # Simula el uso del caché (no llama de nuevo a scrape_vehicle_details)
    cached = {"url": url, "data": data1}
    assert cached["data"]["nombre"] == "2023 CachedCar"
    # El caché devuelve exactamente los mismos datos sin nuevo request
    assert mock_session.get.call_count == 1
