import logging
from typing import Any, Optional, Union, overload

from .constants import FLIGHTS_SEARCH_URL
from .exceptions import APIConnectionError, APIError
from .integrations import Integration, get_integration
from .parser import ParsedFlights, parse
from .querying import Query
from .transport import create_browser_transport

# Set up logging
logger = logging.getLogger(__name__)


@overload
def get_flights(
    q: str,
    /,
    *,
    proxy: Optional[str] = None,
    integration: Optional[Union[str, Integration]] = None,
    integration_options: Optional[dict[str, Any]] = None,
):
    """Get flights using a str query.

    Examples:
    - *Flights from TPE to MYJ on 2025-12-22 one way economy class*
    """


@overload
def get_flights(
    q: Query,
    /,
    *,
    proxy: Optional[str] = None,
    integration: Optional[Union[str, Integration]] = None,
    integration_options: Optional[dict[str, Any]] = None,
):
    """Get flights using a structured query.

    Example:
    ```python
    get_flights(
        query(
            flights=[
                FlightQuery(
                    date="2025-12-22",
                    from_airport="TPE",
                    to_airport="MYJ",
                )
            ],
            seat="economy",
            trip="one-way",
            passengers=Passengers(adults=1),
            language="en-US",
            currency="",
        )
    )
    ```
    """


def get_flights(
    q: Union[Query, str],
    /,
    *,
    proxy: Optional[str] = None,
    integration: Optional[Union[str, Integration]] = None,
    integration_options: Optional[dict[str, Any]] = None,
) -> ParsedFlights:
    """Get flights.

    Args:
        q: The query string or Query object.
        proxy: Optional proxy configuration passed to the default transport.
        integration: Integration instance or registered integration name to use when fetching data.
        integration_options: Keyword arguments forwarded to the integration factory when `integration` is a string.
        
    Returns:
        ParsedFlights: Parsed flight data along with metadata.
        
    Raises:
        APIConnectionError: If there's an issue connecting to the flight data source.
        APIError: If the API returns an error or invalid response.
        ValueError: If the input query is invalid.
    """
    try:
        logger.debug("Fetching flight data...")
        html = fetch_flights_html(
            q,
            proxy=proxy,
            integration=integration,
            integration_options=integration_options,
        )
        if not html or not isinstance(html, str):
            raise APIError("Received empty or invalid response from the flight data source")
        return parse(html)
    except Exception as e:
        if isinstance(e, (APIConnectionError, APIError, ValueError)):
            raise
        raise APIConnectionError(f"Failed to fetch flight data: {str(e)}") from e


def fetch_flights_html(
    q: Union[Query, str],
    /,
    *,
    proxy: Optional[str] = None,
    integration: Optional[Union[str, Integration]] = None,
    integration_options: Optional[dict[str, Any]] = None,
) -> str:
    """Fetch flights and get the HTML response.

    Args:
        q: The query string or Query object.
        proxy: Optional proxy configuration passed to the default transport.
        integration: Integration instance or registered integration name to use when fetching data.
        integration_options: Keyword arguments forwarded to the integration factory when `integration` is a string.
        
    Returns:
        str: The HTML content of the flight search results.
        
    Raises:
        APIConnectionError: If there's an issue connecting to the flight data source.
        APIError: If the API returns an error or invalid response.
        ValueError: If the input query is invalid.
    """
    if not q:
        raise ValueError("Query cannot be empty")
    
    try:
        if integration is None:
            return _fetch_with_transport(q, proxy=proxy)

        integration_obj = _resolve_integration(
            integration,
            options=integration_options,
        )
        logger.debug(
            "Using integration '%s' for fetching flight data",
            integration_obj.__class__.__name__,
        )
        try:
            return integration_obj.fetch_html(q)
        except Exception as e:  # pragma: no cover - defensive
            if isinstance(e, (APIConnectionError, APIError, ValueError)):
                raise
            logger.error("Integration error while fetching flight data: %s", e)
            raise APIError(f"Integration failed to fetch flight data: {str(e)}") from e

    except Exception as e:
        if isinstance(e, (APIConnectionError, APIError, ValueError)):
            raise
        raise APIConnectionError(f"Unexpected error while fetching flight data: {str(e)}") from e


def _resolve_integration(
    integration: Union[str, Integration],
    *,
    options: Optional[dict[str, Any]],
) -> Integration:
    if isinstance(integration, Integration):
        if options:
            logger.debug("Ignoring integration_options because an instance was provided.")
        return integration

    if isinstance(integration, str):
        opts = options or {}
        return get_integration(integration, **opts)

    raise ValueError("integration must be an Integration instance or a registered name")


def _fetch_with_transport(
    q: Union[Query, str],
    *,
    proxy: Optional[str],
) -> str:
    logger.debug("Using default transport client for fetching flight data")
    transport = create_browser_transport(proxy=proxy)

    params = _query_params(q)
    logger.debug("Sending request to %s with params: %s", FLIGHTS_SEARCH_URL, params)

    try:
        response = transport.get(FLIGHTS_SEARCH_URL, params=params)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to connect to flight data source: %s", exc)
        raise APIConnectionError(f"Failed to connect to flight data source: {exc}") from exc

    if not response.ok:
        error_msg = f"Flight data API returned status code {response.status_code}"
        logger.error(error_msg)
        raise APIError(error_msg)

    if not response.text:
        error_msg = "Received empty response from the flight data source"
        logger.error(error_msg)
        raise APIError(error_msg)

    return response.text


def _query_params(q: Union[Query, str]) -> dict[str, str]:
    if isinstance(q, Query):
        return q.params()
    if isinstance(q, str):
        return {"q": q}
    raise ValueError("Query must be a string or Query object")
