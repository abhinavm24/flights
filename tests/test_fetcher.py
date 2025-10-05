from fast_flights_opinionated.exceptions import APIConnectionError
from fast_flights_opinionated.fetcher import fetch_flights_html
from fast_flights_opinionated.integrations.base import Integration


def test_fetch_flights_html_falls_back_to_bright_data(monkeypatch):
    def fail_fetch(q, *, proxy=None):
        raise APIConnectionError("primary transport failed")

    monkeypatch.setattr("fast_flights_opinionated.fetcher._fetch_with_transport", fail_fetch)

    seen: dict[str, object] = {"options": None, "queries": []}

    class DummyIntegration(Integration):
        def __init__(self) -> None:
            super().__init__()

        def fetch_html(self, q, /):
            seen["queries"].append(q)
            return "<html>fallback</html>"

    def fake_resolve(name, *, options):
        assert name == "bright_data"
        seen["options"] = options
        return DummyIntegration()

    monkeypatch.setattr("fast_flights_opinionated.fetcher._resolve_integration", fake_resolve)

    result = fetch_flights_html(
        "Flights from TPE to MYJ",
        integration_options={"api_key": "abc"},
    )

    assert result == "<html>fallback</html>"
    assert seen["options"] == {"api_key": "abc"}
    assert seen["queries"] == ["Flights from TPE to MYJ"]
