"""Mapper converting raw payloads into domain models."""
from __future__ import annotations

from typing import Any, Iterator, List, Tuple

from ..model import (
    Airline,
    Airport,
    Alliance,
    CarbonEmission,
    Flights,
    JsMetadata,
    SimpleDatetime,
    SingleFlight,
)
from .models import ParsedFlights


def map_payload(data: Any) -> ParsedFlights:
    """Convert the raw payload extracted from the HTML into domain objects."""

    alliances, airlines = _parse_metadata(data)
    flights = _parse_flights(data)
    metadata = JsMetadata(alliances=alliances, airlines=airlines)
    return ParsedFlights(flights=flights, metadata=metadata)


def _parse_metadata(data: Any) -> tuple[list[Alliance], list[Airline]]:
    alliances_data = data[7][1][0]
    airlines_data = data[7][1][1]

    alliances: List[Alliance] = [
        Alliance(code=code, name=name) for code, name in _iter_metadata_pairs(alliances_data)
    ]
    airlines: List[Airline] = [
        Airline(code=code, name=name) for code, name in _iter_metadata_pairs(airlines_data)
    ]
    return alliances, airlines


def _iter_metadata_pairs(raw: Any) -> Iterator[Tuple[Any, Any]]:
    """Yield (code, name) pairs from a potentially nested metadata structure."""

    if isinstance(raw, (list, tuple)):
        if (
            len(raw) == 2
            and not isinstance(raw[0], (list, tuple))
            and not isinstance(raw[1], (list, tuple))
        ):
            yield raw[0], raw[1]
            return

        for item in raw:
            yield from _iter_metadata_pairs(item)


def _parse_flights(data: Any) -> list[Flights]:
    flights: list[Flights] = []
    for entry in data[3][0]:
        flight_info = entry[0]
        price = entry[1][0][1]

        flight_type = flight_info[0]
        airlines = flight_info[1]
        segments: list[SingleFlight] = []

        for raw_segment in flight_info[2]:
            segments.append(_map_single_flight(raw_segment))

        extras = flight_info[22]
        carbon_emission = extras[7]
        typical_carbon_emission = extras[8]

        flights.append(
            Flights(
                type=flight_type,
                price=price,
                airlines=airlines,
                flights=segments,
                carbon=CarbonEmission(
                    typical_on_route=typical_carbon_emission,
                    emission=carbon_emission,
                ),
            )
        )

    return flights


def _map_single_flight(raw_segment: list[Any]) -> SingleFlight:
    from_airport = Airport(code=raw_segment[3], name=raw_segment[4])
    to_airport = Airport(code=raw_segment[6], name=raw_segment[5])

    departure = SimpleDatetime(
        date=raw_segment[20],
        time=raw_segment[8],
    )
    arrival = SimpleDatetime(
        date=raw_segment[21],
        time=raw_segment[10],
    )

    return SingleFlight(
        from_airport=from_airport,
        to_airport=to_airport,
        departure=departure,
        arrival=arrival,
        duration=raw_segment[11],
        plane_type=raw_segment[17],
    )


__all__ = ["map_payload"]
