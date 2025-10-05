"""Tests for the Bright Data integration."""

from datetime import date, timedelta
from typing import Any, Mapping

import pytest

from fast_flights import APIError, FlightQuery, Passengers, create_query
from fast_flights.constants import FLIGHTS_SEARCH_URL
from fast_flights.integrations.bright_data import BrightData
from fast_flights.transport import TransportResponse


class StubTransport:
    def __init__(self, response: TransportResponse):
        self._response = response
        self.calls: list[dict[str, Any]] = []

    def post(
        self,
        url: str,
        /,
        *,
        json: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> TransportResponse:
        self.calls.append({"url": url, "json": json, "headers": dict(headers or {})})
        return self._response


class DummyConfig:
    def __init__(self, data: dict[str, str]):
        self._data = data

    def get(self, key: str, default: str | None = None) -> str | None:
        return self._data.get(key, default)


def _build_sample_query():
    departure = (date.today() + timedelta(days=30)).isoformat()
    flight = FlightQuery(date=departure, from_airport="JFK", to_airport="LAX")
    return create_query(
        flights=[flight],
        trip="one-way",
        passengers=Passengers(adults=1),
        seat="economy",
    )


def test_bright_data_fetch_html_posts_expected_payload():
    response = TransportResponse(status_code=200, text="<html>ok</html>", ok=True)
    transport = StubTransport(response)
    integration = BrightData(
        api_key="secret",
        api_url="https://bright.example/data",
        zone="zone-1",
        transport=transport,
    )

    query = _build_sample_query()
    html = integration.fetch_html(query)

    assert html == "<html>ok</html>"
    assert transport.calls == [
        {
            "url": "https://bright.example/data",
            "json": {"url": query.url(), "zone": "zone-1"},
            "headers": {
                "Authorization": "Bearer secret",
                "Content-Type": "application/json",
            },
        }
    ]


def test_bright_data_fetch_html_encodes_string_query():
    response = TransportResponse(status_code=200, text="<html>ok</html>", ok=True)
    transport = StubTransport(response)
    integration = BrightData(
        api_key="secret",
        api_url="https://bright.example/data",
        zone="zone-1",
        transport=transport,
    )

    description = "Flights from TPE to MYJ"
    integration.fetch_html(description)

    assert transport.calls == [
        {
            "url": "https://bright.example/data",
            "json": {
                "url": f"{FLIGHTS_SEARCH_URL}?q=Flights+from+TPE+to+MYJ",
                "zone": "zone-1",
            },
            "headers": {
                "Authorization": "Bearer secret",
                "Content-Type": "application/json",
            },
        }
    ]


def test_bright_data_fetch_html_errors_when_response_not_ok():
    response = TransportResponse(status_code=500, text="", ok=False)
    integration = BrightData(
        api_key="secret",
        zone="zone-1",
        api_url="https://bright.example/data",
        transport=StubTransport(response),
    )

    query = _build_sample_query()
    with pytest.raises(APIError):
        integration.fetch_html(query)


def test_bright_data_requires_api_key_configuration():
    config = DummyConfig({})
    with pytest.raises(ValueError):
        BrightData(config=config)
