"""Transport layer abstractions used by flight data integrations."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, MutableMapping, Optional, Protocol

from primp import Client as PrimpClient


@dataclass(slots=True)
class TransportResponse:
    """Simple transport response wrapper."""

    status_code: int
    text: str
    ok: bool
    raw: Any | None = None


class TransportClient(Protocol):
    """Minimal HTTP transport interface used by the application."""

    def get(
        self,
        url: str,
        /,
        *,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> TransportResponse:
        ...

    def post(
        self,
        url: str,
        /,
        *,
        json: Any | None = None,
        data: Any | None = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> TransportResponse:
        ...


class PrimpTransportClient:
    """Adapter exposing a primp.Client instance as a TransportClient."""

    __slots__ = ("_client", "_default_headers")

    def __init__(
        self,
        *,
        client: Optional[PrimpClient] = None,
        default_headers: Optional[MutableMapping[str, str]] = None,
        timeout: int = 30,
        **client_kwargs: Any,
    ) -> None:
        if client is None:
            client = PrimpClient(timeout=timeout, **client_kwargs)
        self._client = client
        self._default_headers: dict[str, str]
        self._default_headers = dict(default_headers) if default_headers else {}

    def get(
        self,
        url: str,
        /,
        *,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> TransportResponse:
        merged_headers = self._merge_headers(headers)
        response = self._client.get(url, params=params, headers=merged_headers)
        return self._wrap_response(response)

    def post(
        self,
        url: str,
        /,
        *,
        json: Any | None = None,
        data: Any | None = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> TransportResponse:
        merged_headers = self._merge_headers(headers)
        response = self._client.post(url, json=json, data=data, headers=merged_headers)
        return self._wrap_response(response)

    @staticmethod
    def _wrap_response(response: Any) -> TransportResponse:
        text = getattr(response, "text", "")
        status_code = getattr(response, "status_code", 0)
        ok = getattr(response, "ok", status_code < 400)
        return TransportResponse(status_code=status_code, text=text, ok=ok, raw=response)

    def _merge_headers(
        self, headers: Optional[Mapping[str, str]]
    ) -> MutableMapping[str, str] | None:
        if not self._default_headers and headers is None:
            return None
        merged: dict[str, str] = dict(self._default_headers)
        if headers:
            merged.update(headers)
        return merged


def create_browser_transport(
    *,
    proxy: Optional[str] = None,
    timeout: int = 30,
    impersonate: str = "chrome_133",
    impersonate_os: str = "macos",
    referer: bool = True,
    cookie_store: bool = True,
) -> TransportClient:
    """Factory for the default browser-like transport client."""

    client_kwargs: dict[str, Any] = {
        "impersonate": impersonate,
        "impersonate_os": impersonate_os,
        "referer": referer,
        "cookie_store": cookie_store,
    }
    if proxy:
        client_kwargs["proxy"] = proxy
    return PrimpTransportClient(timeout=timeout, **client_kwargs)


__all__ = [
    "TransportClient",
    "TransportResponse",
    "PrimpTransportClient",
    "create_browser_transport",
]
