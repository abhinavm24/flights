"""BrightData integration for fetching flight data."""
import logging
from urllib.parse import quote_plus
from typing import Optional, Union

from .base import ConfigSource, Integration
from ..constants import FLIGHTS_SEARCH_URL
from ..querying import Query
from ..exceptions import APIConnectionError, APIError
from ..transport import PrimpTransportClient, TransportClient

# Set up logging
logger = logging.getLogger(__name__)

DEFAULT_API_URL = "https://api.brightdata.com/request"
DEFAULT_DATA_SERP_ZONE = "serp_api1"


class BrightData(Integration):
    """BrightData integration for fetching flight data using their API.
    
    This class provides a way to fetch flight data using BrightData's API.
    It requires a valid API key and zone configuration.
    
    Args:
        api_key: BrightData API key. If not provided, will try to get from environment.
        api_url: Base URL for the BrightData API.
        zone: BrightData zone to use for the requests.
        
    Raises:
        ValueError: If required configuration is missing.
    """
    __slots__ = ("api_url", "zone", "_transport", "_auth_header")

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        api_url: str = DEFAULT_API_URL,
        zone: str = DEFAULT_DATA_SERP_ZONE,
        transport: Optional[TransportClient] = None,
        config: Optional[ConfigSource] = None,
    ):
        """Initialize the BrightData integration."""
        super().__init__(config=config)

        self.api_url = api_url or self.require_setting(
            "BRIGHT_DATA_API_URL",
            default=DEFAULT_API_URL,
            label="BrightData API URL",
        )
        # Support both BRIGHT_DATA_ZONE and BRIGHT_DATA_SERP_ZONE for backward compatibility
        self.zone = (
            zone
            or self.config.get("BRIGHT_DATA_ZONE")
            or self.config.get("BRIGHT_DATA_SERP_ZONE")
            or self.require_setting(
                "BRIGHT_DATA_ZONE",
                label="BrightData zone (set BRIGHT_DATA_ZONE or BRIGHT_DATA_SERP_ZONE)",
            )
        )
        api_key = api_key or self.require_setting(
            "BRIGHT_DATA_API_KEY",
            label="BrightData API key",
        )

        logger.debug("Initializing BrightData integration")
        self._auth_header = {"Authorization": f"Bearer {api_key}"}
        if transport is None:
            transport = PrimpTransportClient(
                default_headers=dict(self._auth_header),
                timeout=30,
            )
        self._transport = transport

    def fetch_html(self, q: Union[Query, str], /) -> str:
        """Fetch flight data HTML using BrightData API.
        
        Args:
            q: The query string or Query object.
            
        Returns:
            str: The HTML content of the flight search results.
            
        Raises:
            APIConnectionError: If there's an issue connecting to BrightData API.
            APIError: If the API returns an error or invalid response.
            ValueError: If the input query is invalid.
        """
        if not q:
            raise ValueError("Query cannot be empty")
            
        try:
            # Prepare the request payload
            if isinstance(q, str):
                encoded_query = quote_plus(q)
                url = f"{FLIGHTS_SEARCH_URL}?q={encoded_query}"
            elif isinstance(q, Query):
                url = q.url()
            else:
                raise ValueError("Query must be a string or Query object")
                
            payload = {
                "url": url,
                "zone": self.zone,
            }
            
            logger.debug(f"Sending request to BrightData API: {self.api_url}")
            logger.debug(f"Request payload: {payload}")
            
            # Make the API request
            response = self._transport.post(
                self.api_url,
                json=payload,
                headers={**self._auth_header, "Content-Type": "application/json"},
            )

            # Check for HTTP errors
            if not response.ok:
                error_msg = f"BrightData API returned status code {response.status_code}"
                logger.error(error_msg)
                raise APIError(error_msg)
                
            # Check for empty response
            if not response.text:
                error_msg = "Received empty response from BrightData API"
                logger.error(error_msg)
                raise APIError(error_msg)
                
            return response.text
            
        except Exception as e:
            if isinstance(e, (APIConnectionError, APIError, ValueError)):
                raise
                
            error_msg = f"Failed to fetch data from BrightData: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise APIConnectionError(error_msg) from e
