from .base import Integration
from .bright_data import BrightData
from .registry import available_integrations, get_integration, register_integration

# Register built-in integrations
register_integration("bright_data", BrightData)

__all__ = [
    "Integration",
    "BrightData",
    "available_integrations",
    "get_integration",
    "register_integration",
]
