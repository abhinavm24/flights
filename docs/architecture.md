# Architecture Overview

Fast Flights is organised around three layers to keep scraping logic extensible:

- **Domain** – pure data structures and validation helpers (`fast_flights.query_builder`, `fast_flights.query_models`). They shape flight requests without talking to the network.
- **Infrastructure** – transport clients and integrations (`fast_flights.transport`, `fast_flights.integrations`). They decide *how* we fetch HTML.
- **Parsing** – extractors and mappers (`fast_flights.parsing`). They transform HTML into strongly-typed results.

The public API modules (`fast_flights.querying`, `fast_flights.parser`, `fast_flights.fetcher`) re-export these building blocks so existing imports continue to work.

## Adding a new integration

1. Implement a subclass of `Integration` that consumes a `TransportClient` and pulls configuration via `Integration.require_setting`.
2. Reuse `fast_flights.transport.PrimpTransportClient` or provide your own adapter.
3. Register the integration by calling `register_integration("your-name", YourIntegration)` inside `fast_flights/integrations/__init__.py` or an extension module.
4. Consumers can now call `get_flights(..., integration="your-name", integration_options={...})`.

## Extending query builders

- Use `FlightQuery`/`Passengers` from `fast_flights.query_builder` for validation.
- Convert to protobuf when needed through `query_to_proto` or the convenience methods on `Query`.
- Avoid instantiating protobuf messages directly in application code—centralised mappers make schema upgrades easier.

## Parsing pipeline tips

- `fast_flights.parsing.extractor.extract_raw_payload` isolates HTML scraping logic. Add feature detection or fallbacks here if Google changes their markup.
- `fast_flights.parsing.mapper.map_payload` is the single place that understands the raw payload structure. Keep it small and covered by tests so schema drift is spotted quickly.
- The `ParsedFlights` sequence carries metadata alongside flight listings; prefer returning it instead of plain lists so consumers keep access to airline/alliances data.
