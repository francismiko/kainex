from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import httpx
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class MarketAnalyzer:
    """Reads market data from DuckDB and the Kainex Engine API."""

    def __init__(self, duckdb_path: str, engine_api_url: str) -> None:
        self._db_path = Path(duckdb_path)
        self._engine_url = engine_api_url.rstrip("/")
        self._http = httpx.AsyncClient(base_url=self._engine_url, timeout=30.0)

    # ── Market data (via Engine API, fallback to DuckDB) ────────

    async def _query_bars_api(
        self,
        symbol: str,
        market: str = "crypto",
        timeframe: str = "1d",
        limit: int = 200,
    ) -> pd.DataFrame:
        """Fetch bars from Engine API."""
        try:
            resp = await self._http.get(
                "/api/market-data/bars",
                params={"symbol": symbol, "market": market, "timeframe": timeframe, "limit": limit},
            )
            resp.raise_for_status()
            data = resp.json()
            if not data:
                return pd.DataFrame()
            df = pd.DataFrame(data)
            if "timestamp" in df.columns:
                df["ts"] = pd.to_datetime(df["timestamp"])
                df = df.sort_values("ts").set_index("ts")
            return df
        except Exception:
            return pd.DataFrame()

    def _query_bars_duckdb(
        self,
        symbol: str,
        market: str = "crypto",
        timeframe: str = "1d",
        limit: int = 200,
    ) -> pd.DataFrame:
        """Fallback: read directly from DuckDB."""
        try:
            conn = duckdb.connect(str(self._db_path), read_only=True)
            try:
                df = conn.execute(
                    "SELECT * FROM bars "
                    "WHERE symbol = ? AND market = ? AND timeframe = ? "
                    "ORDER BY ts DESC LIMIT ?",
                    [symbol, market, timeframe, limit],
                ).fetchdf()
            finally:
                conn.close()
            if not df.empty:
                df = df.sort_values("ts").set_index("ts")
            return df
        except Exception:
            return pd.DataFrame()

    async def get_market_summary(
        self,
        symbol: str,
        market: str = "crypto",
        timeframe: str = "1d",
        bar_count: int = 200,
    ) -> dict:
        """Return a structured summary with price data and technical indicators."""
        df = await self._query_bars_api(symbol, market, timeframe, bar_count)
        if df.empty:
            df = self._query_bars_duckdb(symbol, market, timeframe, bar_count)
        if df.empty:
            return {
                "symbol": symbol,
                "available": False,
                "bars": 0,
            }

        close = df["close"]
        high = df["high"]
        low = df["low"]

        # Compute indicators inline (no pandas_ta dependency required)
        sma_20 = close.rolling(20).mean()
        sma_50 = close.rolling(50).mean()
        ema_12 = close.ewm(span=12, adjust=False).mean()
        ema_26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema_12 - ema_26
        macd_signal = macd_line.ewm(span=9, adjust=False).mean()
        rsi = _compute_rsi(close, 14)

        last = close.iloc[-1]
        prev = close.iloc[-2] if len(close) > 1 else last

        return {
            "symbol": symbol,
            "available": True,
            "bars": len(df),
            "last_price": float(last),
            "prev_close": float(prev),
            "change_pct": float((last - prev) / prev * 100) if prev != 0 else 0.0,
            "high_24h": float(high.iloc[-1]),
            "low_24h": float(low.iloc[-1]),
            "volume": float(df["volume"].iloc[-1]),
            "sma_20": _safe_float(sma_20.iloc[-1]),
            "sma_50": _safe_float(sma_50.iloc[-1]),
            "rsi_14": _safe_float(rsi.iloc[-1]),
            "macd": _safe_float(macd_line.iloc[-1]),
            "macd_signal": _safe_float(macd_signal.iloc[-1]),
            "macd_histogram": _safe_float((macd_line - macd_signal).iloc[-1]),
            "price_vs_sma20": "above" if last > _safe_float(sma_20.iloc[-1], 0) else "below",
            "price_vs_sma50": "above" if last > _safe_float(sma_50.iloc[-1], 0) else "below",
        }

    # ── Portfolio (Engine API) ──────────────────────────────────

    async def get_portfolio_state(self) -> dict:
        """Fetch current portfolio from the Engine API."""
        try:
            summary_resp = await self._http.get("/api/portfolio/summary")
            summary_resp.raise_for_status()
            summary = summary_resp.json()

            positions_resp = await self._http.get("/api/portfolio/positions")
            positions_resp.raise_for_status()
            positions = positions_resp.json()

            return {
                "total_value": summary.get("total_value", 0.0),
                "cash": summary.get("cash", 0.0),
                "total_pnl": summary.get("total_pnl", 0.0),
                "positions": positions,
            }
        except httpx.HTTPError as exc:
            logger.warning("Failed to fetch portfolio from Engine API: %s", exc)
            return {
                "total_value": 0.0,
                "cash": 0.0,
                "total_pnl": 0.0,
                "positions": [],
            }

    async def get_recent_trades(self, limit: int = 20) -> list[dict]:
        """Fetch recent trades from the Engine API."""
        try:
            resp = await self._http.get("/api/portfolio/trades", params={"limit": limit})
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as exc:
            logger.warning("Failed to fetch trades: %s", exc)
            return []

    async def close(self) -> None:
        await self._http.aclose()


# ── Helpers ─────────────────────────────────────────────────────


def _compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    # When avg_loss is 0 (all gains), RSI = 100; when avg_gain is 0 (all losses), RSI = 0.
    rsi = pd.Series(np.where(avg_loss == 0, 100.0, 100 - (100 / (1 + avg_gain / avg_loss))), index=series.index)
    return rsi


def _safe_float(val: object, default: float | None = None) -> float | None:
    try:
        f = float(val)  # type: ignore[arg-type]
        if np.isnan(f):
            return default
        return f
    except (TypeError, ValueError):
        return default
