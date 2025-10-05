"""Builders and validation orchestration for query domain objects."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime as Datetime
from typing import Literal, Optional, Union

from .exceptions import FlightQueryError
from .query_mapper import resolve_currency, resolve_language
from .query_models import Query
from .types import Currency, Language, SeatType, TripType
from .validation import (
    validate_airlines,
    validate_and_normalize_date,
    validate_flight_query,
    validate_flights_list,
    validate_language,
    validate_max_stops,
    validate_currency,
    validate_passengers,
    validate_seat_type,
    validate_trip_type,
)


@dataclass
class FlightQuery:
    """Represents an individual flight segment within a search."""

    date: Union[str, Datetime]
    from_airport: str
    to_airport: str
    max_stops: Optional[int] = None
    airlines: Optional[list[str]] = None

    def __post_init__(self) -> None:
        self._normalized_date = validate_and_normalize_date(self.date)
        self.from_airport, self.to_airport = validate_flight_query(
            self.from_airport,
            self.to_airport,
            self._normalized_date,
            self.max_stops,
        )

        if self.airlines is not None:
            try:
                self.airlines = validate_airlines(self.airlines)
            except ValueError as exc:
                raise FlightQueryError(str(exc)) from exc

    @property
    def normalized_date(self) -> str:
        return self._normalized_date

    def to_proto(self):
        from .query_mapper import flight_query_to_proto

        return flight_query_to_proto(self)

    def _setmaxstops(self, max_stops: Optional[int] = None) -> "FlightQuery":
        if max_stops is not None:
            self.max_stops = max_stops
        return self


class Passengers:
    """Represents passenger mix for a flight search."""

    adults: int
    children: int
    infants_in_seat: int
    infants_on_lap: int

    def __init__(
        self,
        *,
        adults: int = 1,
        children: int = 0,
        infants_in_seat: int = 0,
        infants_on_lap: int = 0,
    ) -> None:
        self.adults = int(adults)
        self.children = int(children)
        self.infants_in_seat = int(infants_in_seat)
        self.infants_on_lap = int(infants_on_lap)

        validate_passengers(
            adults=self.adults,
            children=self.children,
            infants_in_seat=self.infants_in_seat,
            infants_on_lap=self.infants_on_lap,
        )

    def to_proto(self):
        from .query_mapper import passengers_to_proto

        return passengers_to_proto(self)


def create_query(
    *,
    flights: list[FlightQuery],
    seat: SeatType = "economy",
    trip: TripType = "one-way",
    passengers: Passengers | None = None,
    language: Union[str, Literal[""], Language] = "en-US",
    currency: Union[str, Literal[""], Currency] = "USD",
    max_stops: Optional[int] = None,
) -> Query:
    """Create a normalized Query domain object."""

    if passengers is None:
        passengers = Passengers()
    if not isinstance(passengers, Passengers):
        raise ValueError("passengers must be an instance of Passengers")

    language_code = validate_language(language) if language else ""
    currency_code = validate_currency(currency) if currency else ""

    validate_flights_list(flights, FlightQuery)

    seat_value = validate_seat_type(seat)
    trip_value = validate_trip_type(trip)

    if max_stops is not None:
        normalized_max_stops = validate_max_stops(max_stops)
        flights = [flight._setmaxstops(normalized_max_stops) for flight in flights]

    normalized_language = resolve_language(language_code) if language_code else ""
    normalized_currency = resolve_currency(currency_code) if currency_code else ""

    return Query(
        flights=flights,
        seat=seat_value,
        trip=trip_value,
        passengers=passengers,
        language=normalized_language,
        currency=normalized_currency,
    )


__all__ = ["FlightQuery", "Passengers", "create_query"]
