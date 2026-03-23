import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from engine.api.deps import get_duckdb_store
from engine.api.schemas.market import (
    BarData,
    LatestQuote,
    MarketDataStatusResponse,
    MarketStatus,
    SymbolInfo,
)
from engine.storage.duckdb_store import DuckDBStore

router = APIRouter()


@router.get("/bars", response_model=list[BarData])
async def get_bars(
    symbol: str = Query(..., description="Trading pair symbol"),
    market: str = Query("crypto", description="Market type"),
    timeframe: str = Query("1d", description="Bar timeframe"),
    start: datetime | None = Query(None, description="Start time"),
    end: datetime | None = Query(None, description="End time"),
    limit: int = Query(100, ge=1, le=5000, description="Max bars to return"),
    duckdb_store: DuckDBStore = Depends(get_duckdb_store),
):
    df = duckdb_store.query_bars(
        symbol=symbol,
        market=market,
        timeframe=timeframe,
        start=start.isoformat() if start else None,
        end=end.isoformat() if end else None,
    )
    bars = []
    for ts, row in df.head(limit).iterrows():
        bars.append(
            BarData(
                symbol=symbol,
                market=market,
                timeframe=timeframe,
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"],
                timestamp=ts,
            )
        )
    return bars


@router.get("/latest", response_model=list[LatestQuote])
async def get_latest_quotes(
    symbols: str = Query("BTC/USDT", description="Comma-separated symbols"),
    market: str = Query("crypto", description="Market type"),
    duckdb_store: DuckDBStore = Depends(get_duckdb_store),
):
    now = datetime.now(timezone.utc)
    quotes = []
    for sym in symbols.split(","):
        sym = sym.strip()
        # Query the latest bar for this symbol
        df = duckdb_store.query_bars(symbol=sym, market=market, timeframe="1d")
        if not df.empty:
            last_row = df.iloc[-1]
            quotes.append(
                LatestQuote(
                    symbol=sym,
                    market=market,
                    price=float(last_row["close"]),
                    change_24h=0.0,
                    volume_24h=float(last_row["volume"]),
                    timestamp=df.index[-1],
                )
            )
        else:
            quotes.append(
                LatestQuote(
                    symbol=sym,
                    market=market,
                    price=0.0,
                    change_24h=0.0,
                    volume_24h=0.0,
                    timestamp=now,
                )
            )
    return quotes


@router.get("/symbols", response_model=list[SymbolInfo])
async def list_symbols(
    market: str = Query("crypto", description="Market type"),
    duckdb_store: DuckDBStore = Depends(get_duckdb_store),
):
    result = duckdb_store.execute(
        "SELECT DISTINCT symbol, market FROM bars WHERE market = ? ORDER BY symbol",
        [market],
    )
    rows = result.fetchall()
    symbols = []
    for row in rows:
        sym = row[0]
        parts = sym.split("/")
        base = parts[0] if len(parts) > 1 else sym
        quote = parts[1] if len(parts) > 1 else ""
        symbols.append(
            SymbolInfo(
                symbol=sym,
                market=row[1],
                base=base,
                quote=quote,
            )
        )
    return symbols


@router.get("/status", response_model=MarketDataStatusResponse)
async def market_data_status(
    duckdb_store: DuckDBStore = Depends(get_duckdb_store),
):
    """Return data quality status for each market including staleness and gap detection."""
    now = datetime.now(timezone.utc)

    # Aggregate stats per market: symbols, count, min/max timestamp
    result = duckdb_store.execute("""
        SELECT
            market,
            LIST(DISTINCT symbol ORDER BY symbol) AS symbols,
            COUNT(*) AS total_bars,
            MAX(ts) AS latest_ts,
            MIN(ts) AS earliest_ts
        FROM bars
        GROUP BY market
        ORDER BY market
    """)
    rows = result.fetchall()

    markets: list[MarketStatus] = []
    grand_total = 0

    for row in rows:
        market_name = row[0]
        symbol_list = row[1]
        count = row[2]
        latest_ts = row[3]
        earliest_ts = row[4]
        grand_total += count

        staleness: float | None = None
        if latest_ts is not None:
            # DuckDB may return a datetime or a Timestamp; normalise to UTC-aware
            if latest_ts.tzinfo is None:
                latest_ts = latest_ts.replace(tzinfo=timezone.utc)
            staleness = (now - latest_ts).total_seconds()

        # Simple gap detection: check if count matches expected based on
        # earliest/latest and 1-day timeframe (heuristic – only flags large gaps)
        has_gaps = False
        if earliest_ts is not None and latest_ts is not None and count > 1:
            span_days = (latest_ts - earliest_ts).days
            if span_days > 0:
                expected_min = span_days * 0.5  # generous lower-bound
                if count < expected_min:
                    has_gaps = True

        markets.append(
            MarketStatus(
                market=market_name,
                symbols=symbol_list if isinstance(symbol_list, list) else [symbol_list],
                total_bars=count,
                latest_bar_time=latest_ts,
                staleness_seconds=round(staleness, 1)
                if staleness is not None
                else None,
                has_gaps=has_gaps,
            )
        )

    # DuckDB file size
    db_path = str(duckdb_store.db_path)
    try:
        size_bytes = os.path.getsize(db_path)
        size_mb = round(size_bytes / (1024 * 1024), 2)
    except OSError:
        size_mb = 0.0

    return MarketDataStatusResponse(
        markets=markets,
        total_bars=grand_total,
        duckdb_size_mb=size_mb,
    )
