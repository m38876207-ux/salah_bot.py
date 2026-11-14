"""Tiny async JSON client for the AlAdhan API (Hijri date + city lookup).

The bot is fully functional without network access: every call here has a
local fallback.  Requests are cached and time-limited so a slow network can
never stall a command for long.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import date
from typing import Any
from urllib.parse import quote

import aiohttp

from ..utils.ar import hijri_approx, hijri_text

log = logging.getLogger(__name__)

BASE = "https://api.aladhan.com/v1"
DEFAULT_TIMEOUT = 6.0


class AlAdhanClient:
    """Caches Hijri dates (12 h) and geocoding results (24 h)."""

    def __init__(self, session: aiohttp.ClientSession | None = None) -> None:
        self._session = session
        self._owns_session = session is None
        self._hijri_cache: dict[str, tuple[float, tuple[int, int, int]]] = {}
        self._geo_cache: dict[str, tuple[float, dict[str, Any] | None]] = {}

    # -- session management ---------------------------------------------- #
    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)
            )
            self._owns_session = True
        return self._session

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    # -- helpers ---------------------------------------------------------- #
    async def _get_json(self, url: str) -> dict[str, Any] | None:
        session = await self._ensure_session()
        try:
            async with session.get(url) as resp:
                if resp.status != 200:
                    log.warning("AlAdhan returned HTTP %s for %s", resp.status, url)
                    return None
                return await resp.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            log.info("AlAdhan request failed (%s): %s", type(exc).__name__, exc)
            return None

    # -- public API ------------------------------------------------------- #
    async def hijri_date(self, day, month, year) -> tuple[int, int, int]:
        """Return ``(day, month, year)`` for a Gregorian date.

        Falls back to a local approximation when the network is unavailable.
        """
        key = f"{day:02d}-{month:02d}-{year}"
        cached = self._hijri_cache.get(key)
        if cached and time.monotonic() - cached[0] < 12 * 3600:
            return cached[1]

        result: tuple[int, int, int] | None = None
        payload = await self._get_json(f"{BASE}/gToH/{key}")
        if payload:
            try:
                h = payload["data"]["hijri"]
                result = (int(h["day"]), int(h["month"]["number"]), int(h["year"]))
            except (KeyError, TypeError, ValueError):
                result = None
        if result is None:
            result = hijri_approx(date(year, month, day))

        self._hijri_cache[key] = (time.monotonic(), result)
        return result

    async def hijri_label(self, dt) -> str | None:
        """Formatted Hijri date string, or ``None`` if it had to guess."""
        payload = await self._get_json(
            f"{BASE}/gToH/{dt.day:02d}-{dt.month:02d}-{dt.year}"
        )
        if payload:
            try:
                h = payload["data"]["hijri"]
                return hijri_text(
                    int(h["day"]), int(h["month"]["number"]), int(h["year"])
                )
            except (KeyError, TypeError, ValueError):
                pass
        try:
            return hijri_text(*hijri_approx(dt))
        except Exception:  # noqa: BLE001 - never break a command for a label
            return None

    async def geocode(self, query: str) -> dict[str, Any] | None:
        """Look up a city by name worldwide.

        Returns ``{"city", "country", "latitude", "longitude", "timezone"}``
        or ``None``.
        """
        q = query.strip()
        if not q:
            return None
        cached = self._geo_cache.get(q.lower())
        if cached and time.monotonic() - cached[0] < 24 * 3600:
            return cached[1]

        payload = await self._get_json(f"{BASE}/city/{quote(q)}")
        info: dict[str, Any] | None = None
        if payload:
            try:
                data = payload["data"]
                info = {
                    "city": data.get("city") or q,
                    "country": data.get("country") or "",
                    "latitude": float(data["latitude"]),
                    "longitude": float(data["longitude"]),
                    "timezone": data.get("timezone") or "Africa/Cairo",
                }
            except (KeyError, TypeError, ValueError):
                info = None

        self._geo_cache[q.lower()] = (time.monotonic(), info)
        return info
