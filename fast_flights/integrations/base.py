"""Base integration module for flight data providers."""
import logging
import os
from abc import ABC, abstractmethod
from typing import Optional, Protocol, Union

from ..exceptions import APIConnectionError, APIError
from ..querying import Query

# Set up logging
logger = logging.getLogger(__name__)

try:
    import dotenv  # pip install python-dotenv
    dotenv.load_dotenv()
except ModuleNotFoundError:
    logger.debug("python-dotenv not installed, skipping .env file loading")



class ConfigSource(Protocol):
    """A configuration provider for integrations."""

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        ...


class EnvironmentConfig:
    """Default configuration provider backed by environment variables."""

    __slots__ = ("_environ",)

    def __init__(self, environ: Optional[dict[str, str]] = None) -> None:
        self._environ = environ if environ is not None else os.environ

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        value = self._environ.get(key, default)
        if value is None:
            logger.error("Required environment variable not found: %r", key)
        return value


class Integration(ABC):
    """Abstract base class for flight data integrations."""

    def __init__(self, *, config: Optional[ConfigSource] = None) -> None:
        self._config = config or EnvironmentConfig()

    @abstractmethod
    def fetch_html(self, q: Union[Query, str], /) -> str:
        """Fetch the flights page HTML from a query.

        Args:
            q: The query string or Query object.
                
        Returns:
            str: The HTML content of the flight search results.
            
        Raises:
            APIConnectionError: If there's an issue connecting to the data source.
            APIError: If the API returns an error or invalid response.
            ValueError: If the input query is invalid.
        """
        raise NotImplementedError("Subclasses must implement this method")

    def get_setting(self, key: str, /, *, default: Optional[str] = None) -> Optional[str]:
        """Retrieve an optional configuration value for the integration."""

        return self._config.get(key, default)

    def require_setting(
        self,
        key: str,
        /,
        *,
        default: Optional[str] = None,
        label: Optional[str] = None,
    ) -> str:
        """Retrieve a required configuration value or raise a ValueError."""

        value = self.get_setting(key, default=default)
        if value is None:
            descriptor = label or key
            raise ValueError(f"Missing required configuration value: {descriptor}")
        return value


def get_env(k: str, /, default: Optional[str] = None) -> str:
    """Get environment variable with optional default value.
    
    Args:
        k: The name of the environment variable.
        default: Default value to return if the environment variable is not found.
                If not provided, raises an OSError when the variable is not found.
                
    Returns:
        str: The value of the environment variable, or the default value if provided.
        
    Raises:
        OSError: If the environment variable is not found and no default is provided.
    """
    value = EnvironmentConfig().get(k, default)
    if value is None:
        raise OSError(f"Required environment variable not found: {k!r}")
    return value
