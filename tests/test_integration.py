"""Integration-style tests that exercise the full query → fetch → parse pipeline."""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from fast_flights import APIError, FlightQuery, Passengers, create_query, get_flights
from fast_flights.integrations import register_integration
from fast_flights.integrations.base import Integration
from fast_flights.integrations import registry as integrations_registry


FIXTURE_PATH = Path(__file__).parent / "data" / "sample_flights_response.html"


class FixtureIntegration(Integration):
    """Integration that replays a previously captured API response."""

    def __init__(self, *, html: str) -> None:
        super().__init__()
        self._html = html

    def fetch_html(self, q, /):
        if not q:
            raise ValueError("Query cannot be empty")
        return self._html


def _build_sample_query():
    future_date = (date.today() + timedelta(days=45)).isoformat()
    flight = FlightQuery(date=future_date, from_airport="MYJ", to_airport="TPE")
    return create_query(
        flights=[flight],
        seat="economy",
        trip="one-way",
        passengers=Passengers(adults=2),
        language="en-US",
    )


def _load_recorded_html() -> str:
    if not FIXTURE_PATH.exists():
        pytest.skip("Recorded integration fixture is missing")
    return FIXTURE_PATH.read_text(encoding="utf-8")


def test_get_flights_with_recorded_response_produces_expected_data():
    integration = FixtureIntegration(html=_load_recorded_html())
    query = _build_sample_query()

    results = get_flights(query, integration=integration)

    assert len(results) == 1
    flight = results[0]
    assert flight.price == 35200
    assert flight.airlines == ["JL"]
    assert flight.flights[0].from_airport.code == "MYJ"
    assert flight.flights[0].to_airport.code == "TPE"
    assert flight.flights[0].duration == 165
    assert flight.flights[0].plane_type == "Boeing 737"
    assert flight.carbon.emission == 104
    assert flight.carbon.typical_on_route == 142
    assert results.metadata.airlines[0].code == "JL"
    assert results.metadata.alliances[0].code == "OW"


def test_get_flights_accepts_string_queries_with_recorded_response():
    integration = FixtureIntegration(html=_load_recorded_html())
    description = "Flights from MYJ to TPE on Google Travel"

    results = get_flights(description, integration=integration)

    assert len(results) == 1
    assert results[0].airlines == ["JL"]
    assert results[0].flights[0].to_airport.code == "TPE"


def test_get_flights_errors_when_integration_returns_empty_html():
    integration = FixtureIntegration(html="")
    query = _build_sample_query()

    with pytest.raises(APIError):
        get_flights(query, integration=integration)


def test_get_flights_resolves_registered_integration_with_options(monkeypatch):
    registry_copy = dict(integrations_registry._REGISTRY._registry)
    monkeypatch.setattr(
        integrations_registry._REGISTRY,
        "_registry",
        registry_copy,
        raising=False,
    )

    seen_kwargs: list[dict[str, str]] = []

    def factory(*, html: str, marker: str) -> Integration:
        seen_kwargs.append({"html": html, "marker": marker})
        return FixtureIntegration(html=html)

    register_integration("fixture", factory)

    query = _build_sample_query()
    html = _load_recorded_html()

    results = get_flights(
        query,
        integration="fixture",
        integration_options={"html": html, "marker": "option-passed"},
    )

    assert seen_kwargs == [{"html": html, "marker": "option-passed"}]
    assert len(results) == 1
    assert results[0].airlines == ["JL"]
