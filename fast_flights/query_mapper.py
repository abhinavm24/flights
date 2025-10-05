"""Mapping utilities between domain queries and protobuf representations."""
from __future__ import annotations

from base64 import b64encode
from typing import Any, Dict, Literal, Optional, TYPE_CHECKING, TypeVar, Union, get_args, get_origin

from .pb.flights_pb2 import Airport, FlightData, Info, Passenger as PbPassenger, Seat, Trip
from .query_models import Query
from .types import Currency, Language, SeatType, TripType

if TYPE_CHECKING:
    from .query_builder import FlightQuery, Passengers


T = TypeVar("T")


def flight_query_to_proto(flight: "FlightQuery") -> FlightData:
    """Convert a FlightQuery domain object into its protobuf counterpart."""

    airlines = getattr(flight, "airlines", None)
    max_stops = getattr(flight, "max_stops", None)
    normalized_date = getattr(flight, "normalized_date", getattr(flight, "_normalized_date", ""))

    flight_data = FlightData(
        date=normalized_date,
        from_airport=Airport(airport=getattr(flight, "from_airport")),
        to_airport=Airport(airport=getattr(flight, "to_airport")),
    )

    if max_stops is not None:
        flight_data.max_stops = max_stops

    if airlines:
        flight_data.airlines.extend(airlines)

    return flight_data


def passengers_to_proto(passengers: "Passengers") -> list[PbPassenger]:
    """Convert Passengers domain object into a list of passenger protobuf enums."""

    return [
        *(PbPassenger.ADULT for _ in range(getattr(passengers, "adults", 0))),
        *(PbPassenger.CHILD for _ in range(getattr(passengers, "children", 0))),
        *(PbPassenger.INFANT_IN_SEAT for _ in range(getattr(passengers, "infants_in_seat", 0))),
        *(PbPassenger.INFANT_ON_LAP for _ in range(getattr(passengers, "infants_on_lap", 0))),
    ]


def query_to_proto(query: Query) -> Info:
    """Convert a Query domain object into the protobuf Info message."""

    seat_enum = _SEAT_LOOKUP[query.seat]
    trip_enum = _TRIP_LOOKUP[query.trip]
    passengers = passengers_to_proto(query.passengers)
    flights = [flight_query_to_proto(flight) for flight in query.flights]

    return Info(
        data=flights,
        seat=seat_enum,
        trip=trip_enum,
        passengers=passengers,
    )


def query_to_bytes(query: Query) -> bytes:
    """Serialize a Query domain object into protobuf bytes."""

    return query_to_proto(query).SerializeToString()


def query_to_str(query: Query) -> str:
    """Serialize a Query domain object into the base64 `tfs` payload."""

    return b64encode(query_to_bytes(query)).decode("utf-8")


def query_to_url(query: Query) -> str:
    """Build the Google Travel flight search URL for the query."""

    language = query.language or ""
    currency = query.currency or ""
    return (
        "https://www.google.com/travel/flights/search?tfs="
        + query_to_str(query)
        + "&hl="
        + language
        + "&curr="
        + currency
    )


def query_params(query: Query) -> Dict[str, str]:
    """Build request parameters for a Query."""

    params = {"tfs": query_to_str(query)}
    params["hl"] = query.language or ""
    params["curr"] = query.currency or ""
    return params


def _create_enum_lookup(enum_type: Any, literal_type: Any) -> Dict[str, Any]:
    """Create a lookup dictionary aligning literals with protobuf enums."""

    literal_values = _get_literal_values(literal_type)
    if not literal_values:
        return {}

    if enum_type is str:
        return {value: value for value in literal_values if isinstance(value, str)}

    lookup: Dict[str, Any] = {}
    for value in literal_values:
        if not isinstance(value, str):
            continue
        enum_name = value.upper().replace("-", "_")
        try:
            enum_value = getattr(enum_type, enum_name)
        except AttributeError:
            continue
        lookup[value] = enum_value
    return lookup


def _get_literal_values(tp: Any) -> tuple[str, ...]:
    origin = get_origin(tp)
    if origin is not Literal:
        return ()

    args = get_args(tp)
    if not args:
        return ()

    return tuple(str(arg) for arg in args if isinstance(arg, (str, int, bool, float)))


_SEAT_LOOKUP = _create_enum_lookup(Seat, SeatType)
_TRIP_LOOKUP = _create_enum_lookup(Trip, TripType)
_LANGUAGE_LOOKUP = _create_enum_lookup(str, Language)
_CURRENCY_LOOKUP = _create_enum_lookup(str, Currency)


def resolve_language(language: Optional[Union[str, Literal[""]]]) -> str:
    if not language:
        return ""
    return _LANGUAGE_LOOKUP.get(language, "")


def resolve_currency(currency: Optional[Union[str, Literal[""]]]) -> str:
    if not currency:
        return ""
    return _CURRENCY_LOOKUP.get(currency, "")


__all__ = [
    "flight_query_to_proto",
    "passengers_to_proto",
    "query_to_proto",
    "query_to_bytes",
    "query_to_str",
    "query_to_url",
    "query_params",
    "resolve_language",
    "resolve_currency",
]
