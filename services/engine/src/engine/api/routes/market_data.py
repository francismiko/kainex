from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from engine.api.deps import get_duckdb_store
from engine.api.schemas.market import BarData, LatestQuote, SymbolInfo
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
        bars.append(BarData(
            symbol=symbol,
            market=market,
            timeframe=timeframe,
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            volume=row["volume"],
            timestamp=ts,
        ))
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
            quotes.append(LatestQuote(
                symbol=sym,
                market=market,
                price=float(last_row["close"]),
                change_24h=0.0,
                volume_24h=float(last_row["volume"]),
                timestamp=df.index[-1],
            ))
        else:
            quotes.append(LatestQuote(
                symbol=sym,
                market=market,
                price=0.0,
                change_24h=0.0,
                volume_24h=0.0,
                timestamp=now,
            ))
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
        symbols.append(SymbolInfo(
            symbol=sym,
            market=row[1],
            base=base,
            quote=quote,
        ))
    return symbols
