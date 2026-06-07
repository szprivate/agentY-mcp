"""
Web search tools for agentY — powered by DuckDuckGo (no API key required).

Provides two Strands-compatible tools:
- ``web_search``        — full-text search returning titles, URLs, and snippets.
- ``web_search_images`` — image search returning image URLs with metadata.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from strands import tool

logger = logging.getLogger(__name__)


@tool
def web_search(
    query: str,
    max_results: int = 10,
    timelimit: Optional[str] = None,
    region: Optional[str] = None,
) -> str:
    """Search the web using DuckDuckGo and return relevant results as JSON.

    Use this tool when you need up-to-date information, external references,
    or real-world context that is not available in local files or tools.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return (1–25). Default 10.
        timelimit: Restrict results by age: "d" (day), "w" (week), "m" (month),
                   "y" (year). Omit for all-time results.
        region: Region code for localised results, e.g. "us-en", "de-de",
                "fr-fr". Defaults to global results when omitted.

    Returns:
        JSON array of result objects, each containing:
          - ``title``   – page title
          - ``url``     – page URL
          - ``snippet`` – short description / extract
        On error, returns a JSON object ``{"error": "<message>"}``.
    """
    try:
        from ddgs import DDGS  # type: ignore[import]

        # ddgs takes the query positionally; pass only the filters that are set
        # (it tolerates omission better than explicit None values).
        kwargs: dict = {"max_results": max(1, min(max_results, 25))}
        if region:
            kwargs["region"] = region
        if timelimit:
            kwargs["timelimit"] = timelimit

        with DDGS() as ddgs:
            raw = ddgs.text(query, **kwargs)

        if not raw:
            return json.dumps([])

        results = [
            {
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            }
            for r in raw
        ]
        return json.dumps(results, ensure_ascii=False, indent=2)

    except Exception as exc:  # noqa: BLE001
        logger.warning("web_search failed: %s", exc)
        return json.dumps({"error": str(exc)})


@tool
def web_search_images(
    query: str,
    max_results: int = 10,
    size: Optional[str] = None,
    type_image: Optional[str] = None,
    license_image: Optional[str] = None,
    timelimit: Optional[str] = None,
    region: str = "us-en",
) -> str:
    """Search the web for images using DuckDuckGo and return image URLs with metadata.

    Use this tool when you need to find reference images, inspiration images,
    or visual examples from the web — for example to understand a visual style,
    find a reference for a character or product, or retrieve example artwork.

    Args:
        query: Image search query string.
        max_results: Maximum number of images to return (1–25). Default 10.
        size: Filter by size: "Small", "Medium", "Large", "Wallpaper".
              Omit for all sizes.
        type_image: Filter by type: "photo", "clipart", "gif",
                    "transparent", "line". Omit for all types.
        license_image: Filter by license:
            "any"               – All Creative Commons,
            "Public"            – Public Domain,
            "Share"             – Free to Share and Use,
            "ShareCommercially" – Free to Share and Use Commercially,
            "Modify"            – Free to Modify, Share, and Use,
            "ModifyCommercially"– Free to Modify, Share, and Use Commercially.
            Omit to include all licenses.
        timelimit: Restrict by age: "Day", "Week", "Month", "Year". Omit for all.
        region: Region code for localised results. Default "us-en".

    Returns:
        JSON array of image result objects, each containing:
          - ``title``      – image / page title
          - ``image_url``  – direct URL to the image file
          - ``page_url``   – URL of the page where the image appears
          - ``thumbnail``  – URL of a smaller thumbnail version
          - ``width``      – image width in pixels (if available)
          - ``height``     – image height in pixels (if available)
          - ``source``     – source website hostname
        On error, returns a JSON object ``{"error": "<message>"}``.
    """
    try:
        from ddgs import DDGS  # type: ignore[import]

        # ddgs takes the query positionally; pass only the filters that are set.
        kwargs: dict = {
            "region": region,
            "max_results": max(1, min(max_results, 25)),
        }
        if timelimit:
            kwargs["timelimit"] = timelimit
        if size:
            kwargs["size"] = size
        if type_image:
            kwargs["type_image"] = type_image
        if license_image:
            kwargs["license_image"] = license_image

        with DDGS() as ddgs:
            raw = ddgs.images(query, **kwargs)

        if not raw:
            return json.dumps([])

        results = [
            {
                "title": r.get("title", ""),
                "image_url": r.get("image", ""),
                "page_url": r.get("url", ""),
                "thumbnail": r.get("thumbnail", ""),
                "width": r.get("width"),
                "height": r.get("height"),
                "source": r.get("source", ""),
            }
            for r in raw
        ]
        return json.dumps(results, ensure_ascii=False, indent=2)

    except Exception as exc:  # noqa: BLE001
        logger.warning("web_search_images failed: %s", exc)
        return json.dumps({"error": str(exc)})
