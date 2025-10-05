"""HTML extraction utilities for flight search responses."""
from __future__ import annotations

import logging
from typing import Any

import rjsonc
from selectolax.lexbor import LexborHTMLParser

logger = logging.getLogger(__name__)


def extract_script_text(html: str) -> str:
    """Extract the embedded data script from the flights HTML page."""

    parser = LexborHTMLParser(html)
    script = parser.css_first(r"script.ds\:1")
    if script is None:
        error_msg = "Unable to locate flights data script in HTML response"
        logger.error(error_msg)
        raise ValueError(error_msg)
    return script.text()


def extract_raw_payload(html: str) -> Any:
    """Extract and decode the raw JSON payload from the flights page."""

    script_text = extract_script_text(html)
    return parse_script_payload(script_text)


def parse_script_payload(script_text: str) -> Any:
    """Parse the JSON payload embedded inside the script tag."""

    try:
        json_blob = script_text.split("data:", 1)[1].rsplit(",", 1)[0]
    except (IndexError, AttributeError) as exc:
        error_msg = "Unexpected flights script format"
        logger.error(error_msg)
        raise ValueError(error_msg) from exc

    return rjsonc.loads(json_blob)


__all__ = ["extract_raw_payload", "extract_script_text", "parse_script_payload"]
