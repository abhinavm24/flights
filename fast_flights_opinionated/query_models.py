"""Domain models representing flight queries."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .query_builder import FlightQuery, Passengers


@dataclass
class Query:
    """Domain representation of a flight search query."""

    flights: list["FlightQuery"]
    seat: str
    trip: str
    passengers: "Passengers"
    language: str
    currency: str

    def __str__(self) -> str:
        """Return a human-readable summary of the query."""

        segments: list[str] = []
        for index, flight in enumerate(self.flights, start=1):
            segments.append(f"  Flight {index}:")
            segments.append(f"    From: {getattr(flight, 'from_airport', 'N/A')}")
            segments.append(f"    To: {getattr(flight, 'to_airport', 'N/A')}")
            segments.append(f"    Date: {getattr(flight, 'normalized_date', getattr(flight, '_normalized_date', 'N/A'))}")

            airlines = getattr(flight, 'airlines', None) or []
            if airlines:
                segments.append(f"    Airlines: {', '.join(airlines)}")

            max_stops = getattr(flight, 'max_stops', None)
            if max_stops is not None:
                segments.append(f"    Max Stops: {max_stops}")

        passenger_summary = self._passenger_summary()

        return (
            "Query Details:\n"
            f"Seat Class: {self.seat}\n"
            f"Trip Type: {self.trip}\n"
            f"Passengers: {passenger_summary}\n"
            f"Language: {self.language or 'Default'}\n"
            f"Currency: {self.currency or 'Default'}\n"
            f"Flights:\n" + "\n".join(segments)
        )

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return "Query(...)"

    def to_proto(self):
        """Convert this query into the protobuf Info representation."""

        from .query_mapper import query_to_proto

        return query_to_proto(self)

    def to_bytes(self) -> bytes:
        """Serialize this query into the protobuf binary representation."""

        from .query_mapper import query_to_bytes

        return query_to_bytes(self)

    def to_str(self) -> str:
        """Encode this query into the base64 string used by Google Travel."""

        from .query_mapper import query_to_str

        return query_to_str(self)

    def url(self) -> str:
        """Generate the Google Travel URL for this query."""

        from .query_mapper import query_to_url

        return query_to_url(self)

    def params(self) -> dict[str, str]:
        """Return request parameters for the Google Travel flights page."""

        from .query_mapper import query_params

        return query_params(self)

    @property
    def flight_data(self) -> list:
        """Backwards compatible access to protobuf flight segments."""

        from .query_mapper import flight_query_to_proto

        return [flight_query_to_proto(flight) for flight in self.flights]

    def _passenger_summary(self) -> str:
        passengers = self.passengers
        summary_parts: list[str] = []

        adults = getattr(passengers, "adults", 0)
        if adults:
            summary_parts.append(f"{adults} Adults")

        children = getattr(passengers, "children", 0)
        if children:
            summary_parts.append(f"{children} Children")

        infants_seat = getattr(passengers, "infants_in_seat", 0)
        infants_lap = getattr(passengers, "infants_on_lap", 0)
        infants_total = infants_seat + infants_lap
        if infants_total:
            summary_parts.append(f"{infants_total} Infants")

        return ", ".join(summary_parts) if summary_parts else "None"


__all__ = ["Query"]
