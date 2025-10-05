"""Data structures returned by the parsing pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Sequence, TypeVar

from ..model import Flights, JsMetadata

TFlights = TypeVar("TFlights", bound=Flights)


@dataclass
class ParsedFlights(Sequence[TFlights]):
    """Parsed flight results accompanied by metadata."""

    flights: list[TFlights]
    metadata: JsMetadata

    def __iter__(self) -> Iterator[TFlights]:
        return iter(self.flights)

    def __len__(self) -> int:
        return len(self.flights)

    def __getitem__(self, index: int) -> TFlights:
        return self.flights[index]

    def to_list(self) -> list[TFlights]:
        """Return the underlying list of flights."""

        return list(self.flights)


__all__ = ["ParsedFlights"]
