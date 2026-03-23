"""Stock/general market news sources: Finnhub API + Yahoo Finance RSS."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import httpx

from agent.sentiment.sources.rss import RSSEntry, parse_rss

logger = logging.getLogger(__name__)

FINNHUB_NEWS_URL = "https://finnhub.io/api/v1/news"
FINNHUB_COMPANY_NEWS_URL = "https://finnhub.io/api/v1/company-news"
YAHOO_FINANCE_RSS_URL = "https://feeds.finance.yahoo.com/rss/2.0/headline"


@dataclass
class StockNewsSource:
    """Fetch stock/market news from Finnhub and Yahoo Finance RSS."""

    finnhub_api_key: str = ""
    _http: httpx.AsyncClient = field(default_factory=lambda: httpx.AsyncClient(timeout=15.0))

    async def fetch_general(self, limit: int = 10) -> list[RSSEntry]:
        """Fetch general market news."""
        entries: list[RSSEntry] = []
        if self.finnhub_api_key:
            entries.extend(await self._fetch_finnhub_general(limit))
        entries.extend(await self._fetch_yahoo_rss(limit))
        return entries[:limit]

    async def fetch_symbol(self, symbol: str, limit: int = 5) -> list[RSSEntry]:
        """Fetch news for a specific stock symbol."""
        entries: list[RSSEntry] = []
        if self.finnhub_api_key:
            entries.extend(await self._fetch_finnhub_company(symbol, limit))
        # Yahoo Finance RSS also supports per-symbol feeds
        entries.extend(await self._fetch_yahoo_rss(limit, symbol=symbol))
        return entries[:limit]

    async def _fetch_finnhub_general(self, limit: int) -> list[RSSEntry]:
        try:
            resp = await self._http.get(
                FINNHUB_NEWS_URL,
                params={"category": "general", "token": self.finnhub_api_key},
            )
            resp.raise_for_status()
            articles = resp.json()
            return [
                RSSEntry(
                    title=a.get("headline", ""),
                    summary=(a.get("summary", "") or "")[:200],
                    link=a.get("url", ""),
                    published=str(a.get("datetime", "")),
                )
                for a in articles[:limit]
            ]
        except Exception as exc:
            logger.warning("Finnhub general news fetch failed: %s", exc)
            return []

    async def _fetch_finnhub_company(self, symbol: str, limit: int) -> list[RSSEntry]:
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        from_date = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        to_date = now.strftime("%Y-%m-%d")
        try:
            resp = await self._http.get(
                FINNHUB_COMPANY_NEWS_URL,
                params={
                    "symbol": symbol,
                    "from": from_date,
                    "to": to_date,
                    "token": self.finnhub_api_key,
                },
            )
            resp.raise_for_status()
            articles = resp.json()
            return [
                RSSEntry(
                    title=a.get("headline", ""),
                    summary=(a.get("summary", "") or "")[:200],
                    link=a.get("url", ""),
                    published=str(a.get("datetime", "")),
                )
                for a in articles[:limit]
            ]
        except Exception as exc:
            logger.warning("Finnhub company news fetch failed for %s: %s", symbol, exc)
            return []

    async def _fetch_yahoo_rss(self, limit: int, symbol: str | None = None) -> list[RSSEntry]:
        try:
            params: dict[str, str] = {"lang": "en-US", "region": "US"}
            if symbol:
                params["s"] = symbol
            resp = await self._http.get(YAHOO_FINANCE_RSS_URL, params=params)
            resp.raise_for_status()
            return parse_rss(resp.text, limit=limit)
        except Exception as exc:
            logger.warning("Yahoo Finance RSS fetch failed: %s", exc)
            return []

    async def close(self) -> None:
        await self._http.aclose()
