"""Integration registry for lookup and instantiation."""
from __future__ import annotations

from typing import Any, Callable, Dict, Iterable

from .base import Integration

IntegrationFactory = Callable[..., Integration]


class IntegrationRegistry:
    """Simple registry that maps identifiers to integration factories."""

    __slots__ = ("_registry",)

    def __init__(self) -> None:
        self._registry: Dict[str, IntegrationFactory] = {}

    def register(self, name: str, factory: IntegrationFactory) -> None:
        key = name.lower()
        self._registry[key] = factory

    def get(self, name: str, /, **kwargs: Any) -> Integration:
        key = name.lower()
        try:
            factory = self._registry[key]
        except KeyError as exc:
            available = ", ".join(sorted(self._registry)) or "(none)"
            raise KeyError(f"Unknown integration '{name}'. Known integrations: {available}") from exc
        integration = factory(**kwargs)
        if not isinstance(integration, Integration):
            raise TypeError(f"Factory for '{name}' did not return an Integration instance")
        return integration

    def names(self) -> Iterable[str]:
        return tuple(sorted(self._registry))


_REGISTRY = IntegrationRegistry()


def register_integration(name: str, factory: IntegrationFactory) -> None:
    """Register a new integration factory."""

    _REGISTRY.register(name, factory)


def get_integration(name: str, /, **kwargs: Any) -> Integration:
    """Retrieve an integration instance by name."""

    return _REGISTRY.get(name, **kwargs)


def available_integrations() -> Iterable[str]:
    """List all registered integration names."""

    return _REGISTRY.names()


__all__ = ["register_integration", "get_integration", "available_integrations"]
