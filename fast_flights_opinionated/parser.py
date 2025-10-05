"""High-level parsing entry points for flight search responses."""
from __future__ import annotations

from .parsing import (
    ParsedFlights,
    extract_raw_payload,
    map_payload,
)


def parse(html: str) -> ParsedFlights:
    """Parse the flights HTML into domain objects and metadata."""

    raw_payload = extract_raw_payload(html)
    return map_payload(raw_payload)


__all__ = ["ParsedFlights", "parse"]
