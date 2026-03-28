"""Command line interface for fast_flights_opinionated."""
from __future__ import annotations

import argparse
import json
import logging
import shlex
import sys
from dataclasses import asdict
from decimal import Decimal, ROUND_HALF_UP
from importlib import metadata
from typing import Any, Iterable, Mapping, Optional, Sequence

from .exceptions import (
    APIConnectionError,
    APIError,
    FastFlightsError,
    FlightQueryError,
    PassengerError,
    ValidationError,
)
from .fetcher import get_flights
from .integrations import available_integrations
from .model import Flights, SingleFlight
from .parsing.models import ParsedFlights
from .query_builder import FlightQuery, Passengers
from .querying import Query, create_query


TRIP_CHOICES: tuple[str, ...] = ("one-way", "round-trip", "multi-city")
SEAT_CHOICES: tuple[str, ...] = ("economy", "premium-economy", "business", "first")


class SegmentParseError(ValueError):
    """Raised when a --segment argument cannot be parsed."""


def _pkg_version() -> str:
    """Best effort retrieval of the installed package version."""

    try:
        return metadata.version("fast-flights-opinionated")
    except metadata.PackageNotFoundError:
        return "0.0.dev0"


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""

    integration_names = sorted(available_integrations())
    integration_hint = (
        f" Known integrations: {', '.join(integration_names)}." if integration_names else ""
    )

    parser = argparse.ArgumentParser(
        prog="flights-cli",
        description="Query Google Flights data using fast_flights_opinionated.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_pkg_version()}",
    )

    trip_group = parser.add_mutually_exclusive_group()
    trip_group.add_argument(
        "--trip",
        choices=TRIP_CHOICES,
        help="Explicitly set the trip type.",
    )
    trip_group.add_argument(
        "--one",
        dest="trip_one",
        action="store_true",
        help="Shortcut for --trip one-way.",
    )
    trip_group.add_argument(
        "--round",
        dest="trip_round",
        action="store_true",
        help="Shortcut for --trip round-trip.",
    )
    trip_group.add_argument(
        "--multi",
        dest="trip_multi",
        action="store_true",
        help="Shortcut for --trip multi-city.",
    )

    parser.add_argument(
        "--segment",
        dest="segments",
        action="append",
        metavar='"date=YYYY-MM-DD from=AAA to=BBB [max_stops=N] [airlines=AA,BB]"',
        help="Flight segment definition. Provide multiple times for multi-leg searches.",
    )

    parser.add_argument(
        "--max-stops",
        type=int,
        default=None,
        help="Apply a global stops limit across all segments (overrides per-segment values).",
    )

    parser.add_argument(
        "--seat",
        choices=SEAT_CHOICES,
        default="economy",
        help="Seat / cabin class.",
    )

    parser.add_argument(
        "--language",
        default="en-US",
        help="Preferred language code. Use '' to defer to Google defaults.",
    )

    parser.add_argument(
        "--currency",
        default="USD",
        help="Preferred currency code. Use '' to defer to Google defaults.",
    )

    parser.add_argument("--proxy", help="Proxy string passed to the default transport (optional).")

    parser.add_argument(
        "--integration",
        help=f"Fetch flights using a registered integration instead of the default transport.{integration_hint}",
    )
    parser.add_argument(
        "--integration-option",
        action="append",
        dest="integration_options",
        metavar="KEY=VALUE",
        help="Forward an option to the integration factory; repeatable.",
    )

    parser.add_argument(
        "--adults",
        type=int,
        default=1,
        help="Number of adult passengers.",
    )
    parser.add_argument(
        "--children",
        type=int,
        default=0,
        help="Number of child passengers.",
    )
    parser.add_argument(
        "--infants-in-seat",
        type=int,
        default=0,
        help="Number of infants in their own seat.",
    )
    parser.add_argument(
        "--infants-on-lap",
        type=int,
        default=0,
        help="Number of lap infants.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of itineraries displayed (applies to both text and JSON).",
    )

    parser.add_argument(
        "--output",
        choices=("text", "json"),
        default="text",
        help="Select the output format.",
    )
    parser.add_argument(
        "--json",
        dest="output",
        action="store_const",
        const="json",
        help="Shortcut for --output json.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output (ignored in text mode).",
    )
    parser.add_argument(
        "--show-metadata",
        action="store_true",
        help="Display metadata about airlines and alliances (or include in JSON).",
    )
    parser.add_argument(
        "--raw-price",
        action="store_true",
        help="Display price values without converting from minor currency units.",
    )
    parser.add_argument(
        "--show-query",
        action="store_true",
        help="Echo the normalized query summary to stderr before fetching.",
    )
    parser.add_argument(
        "--show-url",
        action="store_true",
        help="Print the Google Flights URL for the query to stderr before fetching.",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable informative logging to stderr.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging (overrides --verbose).",
    )

    return parser


def _configure_logging(*, verbose: bool, debug: bool) -> None:
    level = logging.WARNING
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    logging.basicConfig(level=level, stream=sys.stderr, format="[%(levelname)s] %(message)s")


def _parse_segment_definition(segment: str, index: int) -> FlightQuery:
    """Parse a --segment string into a FlightQuery."""

    key_map = {
        "date": "date",
        "from": "from_airport",
        "from_airport": "from_airport",
        "to": "to_airport",
        "to_airport": "to_airport",
        "max_stops": "max_stops",
        "airlines": "airlines",
    }

    try:
        tokens = shlex.split(segment)
    except ValueError as exc:  # pragma: no cover - shlex raises rarely
        raise SegmentParseError(f"Unable to parse --segment #{index}: {exc}") from exc

    if not tokens:
        raise SegmentParseError("Segment cannot be empty")

    parsed: dict[str, Any] = {}
    for token in tokens:
        if "=" not in token:
            raise SegmentParseError(
                f"Invalid token '{token}' in --segment #{index}. Wrap the full segment in quotes and use key=value pairs."
            )
        raw_key, value = token.split("=", 1)
        key = raw_key.strip().lower()
        if key not in key_map:
            raise SegmentParseError(
                f"Unsupported key '{raw_key}' in --segment #{index}. Allowed keys: {', '.join(sorted(key_map))}."
            )
        mapped_key = key_map[key]
        if mapped_key in parsed:
            raise SegmentParseError(
                f"Duplicate '{raw_key}' in --segment #{index}. Provide each key at most once."
            )
        parsed[mapped_key] = value.strip()

    missing = [field for field in ("date", "from_airport", "to_airport") if field not in parsed]
    if missing:
        pretty = ", ".join(missing)
        raise SegmentParseError(
            f"Missing required key(s) {pretty} in --segment #{index}."
        )

    airlines_value = parsed.get("airlines")
    airlines: list[str] | None = None
    if airlines_value:
        airlines = [code.strip().upper() for code in airlines_value.split(",") if code.strip()]
        if not airlines:
            airlines = None

    max_stops_str = parsed.get("max_stops")
    max_stops: Optional[int] = None
    if max_stops_str:
        try:
            max_stops = int(max_stops_str)
        except ValueError as exc:
            raise SegmentParseError(
                f"Invalid max_stops value '{max_stops_str}' in --segment #{index}. Expected integer."
            ) from exc

    try:
        return FlightQuery(
            date=parsed["date"],
            from_airport=parsed["from_airport"],
            to_airport=parsed["to_airport"],
            max_stops=max_stops,
            airlines=airlines,
        )
    except FlightQueryError as exc:
        raise SegmentParseError(f"Invalid data in --segment #{index}: {exc}") from exc


def _parse_integration_options(raw_options: Iterable[str] | None, *, parser: argparse.ArgumentParser) -> dict[str, str]:
    options: dict[str, str] = {}
    if not raw_options:
        return options
    for raw in raw_options:
        if "=" not in raw:
            parser.error(f"Invalid --integration-option '{raw}'. Expected KEY=VALUE format.")
        key, value = raw.split("=", 1)
        key = key.strip()
        if not key:
            parser.error("Integration option keys cannot be empty.")
        options[key] = value.strip()
    return options


def _resolve_trip(args: argparse.Namespace, *, segment_count: int) -> str:
    if args.trip:
        return args.trip
    if getattr(args, "trip_one", False):
        return "one-way"
    if getattr(args, "trip_round", False):
        return "round-trip"
    if getattr(args, "trip_multi", False):
        return "multi-city"
    if segment_count == 2:
        return "round-trip"
    return "one-way"


def _format_price(value: int, *, currency: str | None, raw: bool) -> str:
    if raw:
        return f"{value} {currency}" if currency else str(value)

    amount = Decimal(value) / Decimal(100)
    normalized = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if currency:
        return f"{normalized} {currency}"
    return f"{normalized}"


def _format_date(parts: Sequence[int]) -> str:
    if len(parts) != 3:
        return "????-??-??"
    year, month, day = (int(parts[0]), int(parts[1]), int(parts[2]))
    return f"{year:04d}-{month:02d}-{day:02d}"


def _format_time(parts: Sequence[int]) -> str:
    if len(parts) < 2:
        return "??:??"
    hour, minute = (int(parts[0]), int(parts[1]))
    return f"{hour:02d}:{minute:02d}"


def _format_duration(minutes: int) -> str:
    hours, remainder = divmod(int(minutes), 60)
    if hours and remainder:
        return f"{hours}h {remainder}m"
    if hours:
        return f"{hours}h"
    return f"{remainder}m"


def _serialize_segment(segment: SingleFlight) -> dict[str, Any]:
    departure_date = _format_date(segment.departure.date)
    departure_time = _format_time(segment.departure.time)
    arrival_date = _format_date(segment.arrival.date)
    arrival_time = _format_time(segment.arrival.time)
    return {
        "from": asdict(segment.from_airport),
        "to": asdict(segment.to_airport),
        "departure": {
            "date": departure_date,
            "time": departure_time,
            "iso": f"{departure_date}T{departure_time}",
        },
        "arrival": {
            "date": arrival_date,
            "time": arrival_time,
            "iso": f"{arrival_date}T{arrival_time}",
        },
        "duration_minutes": segment.duration,
        "duration_text": _format_duration(segment.duration),
        "plane": segment.plane_type,
    }


def _serialize_flights(
    result: ParsedFlights,
    *,
    currency: str | None,
    limit: int | None,
    raw_price: bool,
    include_metadata: bool,
) -> dict[str, Any]:
    flights_seq: Sequence[Flights] = result.flights
    if limit is not None:
        flights_seq = flights_seq[: limit if limit >= 0 else 0]

    flights_payload: list[dict[str, Any]] = []
    for flight in flights_seq:
        flights_payload.append(
            {
                "type": flight.type,
                "airlines": flight.airlines,
                "price": {
                    "raw": flight.price,
                    "display": _format_price(
                        flight.price,
                        currency=currency,
                        raw=raw_price,
                    ),
                    "currency": currency or None,
                    "converted": None if raw_price else float(
                        (Decimal(flight.price) / Decimal(100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    ),
                },
                "segments": [_serialize_segment(segment) for segment in flight.flights],
                "carbon": {
                    "emission_grams": flight.carbon.emission,
                    "typical_route_grams": flight.carbon.typical_on_route,
                },
            }
        )

    payload: dict[str, Any] = {"flights": flights_payload}

    if include_metadata:
        payload["metadata"] = {
            "airlines": [asdict(airline) for airline in result.metadata.airlines],
            "alliances": [asdict(alliance) for alliance in result.metadata.alliances],
        }

    return payload


def _print_text_result(
    result: ParsedFlights,
    *,
    currency: str | None,
    limit: int | None,
    raw_price: bool,
    show_metadata: bool,
) -> None:
    total = len(result)
    if limit is not None and limit >= 0:
        flights = result.flights[:limit]
    else:
        flights = result.flights

    print(f"Found {total} option(s). Displaying {len(flights)}.")

    if not flights:
        return

    for index, flight in enumerate(flights, start=1):
        airlines = ", ".join(flight.airlines) if flight.airlines else "Unknown carriers"
        price_text = _format_price(flight.price, currency=currency, raw=raw_price)
        carbon = f"CO₂: {flight.carbon.emission}g (typical {flight.carbon.typical_on_route}g)"
        print(f"{index}. {airlines} | {price_text} | {len(flight.flights)} leg(s) | {carbon}")

        for leg_index, segment in enumerate(flight.flights, start=1):
            departure_date = _format_date(segment.departure.date)
            departure_time = _format_time(segment.departure.time)
            arrival_date = _format_date(segment.arrival.date)
            arrival_time = _format_time(segment.arrival.time)

            origin = f"{segment.from_airport.code} ({segment.from_airport.name})"
            destination = f"{segment.to_airport.code} ({segment.to_airport.name})"
            duration = _format_duration(segment.duration)
            plane = segment.plane_type or "Unknown aircraft"

            print(
                f"   {leg_index}) {origin} -> {destination} | Depart {departure_date} {departure_time} | "
                f"Arrive {arrival_date} {arrival_time} | Duration {duration} | Plane {plane}"
            )

    if show_metadata:
        airlines_meta = ", ".join(
            f"{airline.name} ({airline.code})" for airline in result.metadata.airlines
        ) or "(none)"
        alliances_meta = ", ".join(
            f"{alliance.name} ({alliance.code})" for alliance in result.metadata.alliances
        ) or "(none)"
        print("\nMetadata:")
        print(f"  Airlines: {airlines_meta}")
        print(f"  Alliances: {alliances_meta}")


def _ensure_positive_limit(limit: int | None, parser: argparse.ArgumentParser) -> int | None:
    if limit is None:
        return None
    if limit < 0:
        parser.error("--limit must be zero or a positive integer")
    return limit


def _emit_query_details(query: Query, *, show_query: bool, show_url: bool) -> None:
    if not (show_query or show_url):
        return
    if show_query:
        print(query, file=sys.stderr)
    if show_url:
        print(f"Google Flights URL: {query.url()}", file=sys.stderr)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    _configure_logging(verbose=args.verbose, debug=args.debug)

    if not args.segments:
        parser.error("At least one --segment must be provided.")

    limit = _ensure_positive_limit(args.limit, parser)

    segments: list[FlightQuery] = []
    for index, raw_segment in enumerate(args.segments, start=1):
        try:
            segments.append(_parse_segment_definition(raw_segment, index))
        except SegmentParseError as exc:
            parser.error(str(exc))

    try:
        passengers = Passengers(
            adults=args.adults,
            children=args.children,
            infants_in_seat=args.infants_in_seat,
            infants_on_lap=args.infants_on_lap,
        )
    except PassengerError as exc:
        parser.error(f"Invalid passenger configuration: {exc}")

    trip = _resolve_trip(args, segment_count=len(segments))

    integration_options = _parse_integration_options(args.integration_options, parser=parser)

    query: Query
    try:
        query = create_query(
            flights=segments,
            seat=args.seat,
            trip=trip,
            passengers=passengers,
            language=args.language,
            currency=args.currency,
            max_stops=args.max_stops,
        )
    except ValidationError as exc:
        parser.error(f"Invalid query: {exc}")

    _emit_query_details(query, show_query=args.show_query, show_url=args.show_url)

    try:
        result = get_flights(
            query,
            proxy=args.proxy,
            integration=args.integration,
            integration_options=integration_options or None,
        )
    except APIConnectionError as exc:
        parser.exit(1, f"Connection error: {exc}\n")
    except APIError as exc:
        parser.exit(1, f"API error: {exc}\n")
    except FastFlightsError as exc:
        parser.exit(1, f"Failed to fetch flights: {exc}\n")
    except Exception as exc:  # pragma: no cover - defensive fallback
        parser.exit(1, f"Unexpected error: {exc}\n")

    currency = args.currency or None

    if args.output == "json":
        payload = _serialize_flights(
            result,
            currency=currency,
            limit=limit,
            raw_price=args.raw_price,
            include_metadata=args.show_metadata,
        )
        json.dump(payload, sys.stdout, indent=2 if args.pretty else None)
        if args.pretty:
            sys.stdout.write("\n")
    else:
        _print_text_result(
            result,
            currency=currency,
            limit=limit,
            raw_price=args.raw_price,
            show_metadata=args.show_metadata,
        )

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
