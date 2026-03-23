"""Aggregates news from multiple free sources."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

from agent.sentiment.sources.crypto_news import CryptoNewsSource
from agent.sentiment.sources.rss import RSSEntry
from agent.sentiment.sources.stock_news import StockNewsSource

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    """A single news article."""

    title: str
    summary: str  # First 200 chars
    source: str
    url: str
    published_at: str
    symbols: list[str] = field(default_factory=list)


class NewsFetcher:
    """Fetch latest financial news from multiple free sources."""

    def __init__(self, finnhub_api_key: str = "") -> None:
        self._http = httpx.AsyncClient(timeout=15.0)
        self._crypto = CryptoNewsSource(_http=self._http)
        self._stock = StockNewsSource(finnhub_api_key=finnhub_api_key, _http=self._http)

    async def fetch_crypto_news(self, limit: int = 10) -> list[NewsItem]:
        """Fetch crypto news from CryptoCompare."""
        entries = await self._crypto.fetch(limit=limit)
        return [self._to_news_item(e, source="CryptoCompare", symbols=["BTC", "ETH"]) for e in entries]

    async def fetch_stock_news(self, symbol: str, limit: int = 5) -> list[NewsItem]:
        """Fetch stock news for a specific symbol from Finnhub + Yahoo Finance RSS."""
        entries = await self._stock.fetch_symbol(symbol, limit=limit)
        return [self._to_news_item(e, source="Finnhub/Yahoo", symbols=[symbol]) for e in entries]

    async def fetch_general_market(self, limit: int = 10) -> list[NewsItem]:
        """Fetch general market news from Finnhub + Yahoo Finance RSS."""
        entries = await self._stock.fetch_general(limit=limit)
        return [self._to_news_item(e, source="Finnhub/Yahoo", symbols=[]) for e in entries]

    async def fetch_all(self, symbols: list[str] | None = None, limit: int = 15) -> list[NewsItem]:
        """Fetch from all sources and return a combined deduplicated list."""
        items: list[NewsItem] = []
        items.extend(await self.fetch_crypto_news(limit=limit))
        items.extend(await self.fetch_general_market(limit=limit))
        if symbols:
            for sym in symbols:
                # Only fetch per-symbol news for stock-like symbols (no '/')
                if "/" not in sym:
                    items.extend(await self.fetch_stock_news(sym, limit=5))
        # Deduplicate by title
        seen: set[str] = set()
        unique: list[NewsItem] = []
        for item in items:
            key = item.title.strip().lower()
            if key and key not in seen:
                seen.add(key)
                unique.append(item)
        return unique[:limit]

    async def close(self) -> None:
        await self._http.aclose()

    @staticmethod
    def _to_news_item(entry: RSSEntry, source: str, symbols: list[str]) -> NewsItem:
        return NewsItem(
            title=entry.title,
            summary=entry.summary,
            source=source,
            url=entry.link,
            published_at=entry.published,
            symbols=symbols,
        )
