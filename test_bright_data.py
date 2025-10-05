#!/usr/bin/env python3
"""Manual test script for the Bright Data integration."""

import os
from typing import Optional

import pytest

from fast_flights_opinionated import FlightQuery, Passengers, create_query, get_flights


BRIGHT_DATA_API_KEY = os.environ.get("BRIGHT_DATA_API_KEY")

if BRIGHT_DATA_API_KEY is None and "PYTEST_CURRENT_TEST" in os.environ:
    pytest.skip(
        "Skipping Bright Data integration test because BRIGHT_DATA_API_KEY is not set",
        allow_module_level=True,
    )


def build_query() -> "fast_flights_opinionated.query_models.Query":
    return create_query(
        flights=[
            FlightQuery(
                date="2025-08-06",
                from_airport="JFK",  # New York
                to_airport="LAX",    # Los Angeles
            ),
            FlightQuery(
                date="2025-08-10",
                from_airport="LAX",
                to_airport="JFK",
            ),
        ],
        trip="round-trip",
        passengers=Passengers(adults=1, children=0, infants_in_seat=0, infants_on_lap=0),
        seat="economy",
        max_stops=None,  # Any number of stops
    )


def display_results(query) -> None:
    print("Testing Bright Data integration...")
    print(f"Query URL: {query.url()}")
    print(
        "Using Bright Data API URL: "
        f"{os.environ.get('BRIGHT_DATA_API_URL', 'https://api.brightdata.com/request')}"
    )
    print(f"Using zone: {os.environ.get('BRIGHT_DATA_SERP_ZONE', 'serp_api1')}")
    print("-" * 80)

    parsed = get_flights(query, integration="bright_data")

    flights = list(parsed)
    current_price: Optional[int] = flights[0].price if flights else None

    print(f"Current price: {current_price}")
    print(f"Found {len(flights)} flights\n")

    for i, flight in enumerate(flights, 1):
        print(f"Flight {i}:")
        print(f"  Airlines: {', '.join(flight.airlines)}")
        print(f"  Price: {flight.price}")
        print(f"  Segments: {len(flight.flights)}")
        if flight.flights:
            first_segment = flight.flights[0]
            last_segment = flight.flights[-1]
            print(
                f"  Departure: {first_segment.departure.date} {first_segment.departure.time}"
            )
            print(
                f"  Arrival: {last_segment.arrival.date} {last_segment.arrival.time}"
            )
            print(f"  Duration (minutes): {sum(seg.duration for seg in flight.flights)}")
        print()


def main() -> None:
    if BRIGHT_DATA_API_KEY is None:
        print("Error: BRIGHT_DATA_API_KEY environment variable is required")
        print("Usage: export BRIGHT_DATA_API_KEY='your-api-key'")
        print("\nOptional environment variables:")
        print("  BRIGHT_DATA_API_URL (defaults to: https://api.brightdata.com/request)")
        print("  BRIGHT_DATA_SERP_ZONE (defaults to: serp_api1)")
        raise SystemExit(1)

    try:
        query = build_query()
        display_results(query)
    except Exception as exc:  # pragma: no cover - manual script guard
        print(f"Error occurred: {type(exc).__name__}: {exc}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
