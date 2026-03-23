from __future__ import annotations

import logging
from datetime import datetime, timezone

import ccxt.async_support as ccxt_async

logger = logging.getLogger(__name__)


class FundingRateSource:
    """Fetch perpetual contract funding rates via CCXT."""

    def __init__(self, exchange_id: str = "binance") -> None:
        self._exchange_id = exchange_id

    def _create_exchange(self) -> ccxt_async.Exchange:
        cls = getattr(ccxt_async, self._exchange_id)
        return cls({"enableRateLimit": True})

    async def fetch_funding_rate(self, symbol: str) -> dict:
        """Fetch current funding rate for a perpetual contract symbol.

        Returns a dict with keys: symbol, rate, timestamp.
        """
        exchange = self._create_exchange()
        try:
            result = await exchange.fetch_funding_rate(symbol)
            return {
                "symbol": symbol,
                "rate": float(result.get("fundingRate", 0.0)),
                "next_funding_time": result.get("fundingDatetime"),
                "timestamp": datetime.now(tz=timezone.utc),
            }
        finally:
            await exchange.close()

    async def fetch_funding_rates(self, symbols: list[str]) -> list[dict]:
        """Fetch funding rates for multiple symbols."""
        exchange = self._create_exchange()
        results: list[dict] = []
        try:
            for symbol in symbols:
                try:
                    result = await exchange.fetch_funding_rate(symbol)
                    results.append(
                        {
                            "symbol": symbol,
                            "rate": float(result.get("fundingRate", 0.0)),
                            "next_funding_time": result.get("fundingDatetime"),
                            "timestamp": datetime.now(tz=timezone.utc),
                        }
                    )
                except Exception:
                    logger.exception("Failed to fetch funding rate for %s", symbol)
        finally:
            await exchange.close()
        return results
