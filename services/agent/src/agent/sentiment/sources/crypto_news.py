"""Crypto news sources: CryptoCompare RSS."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

import httpx

from agent.sentiment.sources.rss import RSSEntry, parse_rss

logger = logging.getLogger(__name__)

CRYPTOCOMPARE_RSS_URL = "https://min-api.cryptocompare.com/data/news/?feeds=cryptocompare&extraParams=kainex"


@dataclass
class CryptoNewsSource:
    """Fetch crypto news from free sources."""

    _http: httpx.AsyncClient = field(default_factory=lambda: httpx.AsyncClient(timeout=15.0))

    async def fetch(self, limit: int = 10) -> list[RSSEntry]:
        """Fetch latest crypto news from CryptoCompare JSON API."""
        entries: list[RSSEntry] = []
        entries.extend(await self._fetch_cryptocompare(limit))
        return entries[:limit]

    async def _fetch_cryptocompare(self, limit: int) -> list[RSSEntry]:
        """CryptoCompare provides a JSON news endpoint (free, no key required)."""
        try:
            resp = await self._http.get(CRYPTOCOMPARE_RSS_URL)
            resp.raise_for_status()
            data = resp.json()
            articles = data.get("Data", [])
            entries: list[RSSEntry] = []
            for article in articles[:limit]:
                entries.append(RSSEntry(
                    title=article.get("title", ""),
                    summary=(article.get("body", "") or "")[:200],
                    link=article.get("url", ""),
                    published=article.get("published_on", ""),
                ))
            return entries
        except Exception as exc:
            logger.warning("CryptoCompare news fetch failed: %s", exc)
            return []

    async def close(self) -> None:
        await self._http.aclose()
