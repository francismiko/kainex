from datetime import datetime, timezone

from fastapi import APIRouter, Query

from engine.api.schemas.market import BarData, LatestQuote, SymbolInfo

router = APIRouter()


@router.get("/bars", response_model=list[BarData])
async def get_bars(
    symbol: str = Query(..., description="Trading pair symbol"),
    market: str = Query("crypto", description="Market type"),
    timeframe: str = Query("1d", description="Bar timeframe"),
    start: datetime | None = Query(None, description="Start time"),
    end: datetime | None = Query(None, description="End time"),
    limit: int = Query(100, ge=1, le=5000, description="Max bars to return"),
):
    # Mock bar data - will be replaced with real data source
    now = datetime.now(timezone.utc)
    mock_bars = [
        BarData(
            symbol=symbol,
            market=market,
            timeframe=timeframe,
            open=30000.0,
            high=31000.0,
            low=29500.0,
            close=30500.0,
            volume=1500.0,
            timestamp=now,
        ),
    ]
    return mock_bars[:limit]


@router.get("/latest", response_model=list[LatestQuote])
async def get_latest_quotes(
    symbols: str = Query("BTC/USDT", description="Comma-separated symbols"),
    market: str = Query("crypto", description="Market type"),
):
    now = datetime.now(timezone.utc)
    quotes = []
    for sym in symbols.split(","):
        sym = sym.strip()
        quotes.append(
            LatestQuote(
                symbol=sym,
                market=market,
                price=30500.0,
                change_24h=2.5,
                volume_24h=15000.0,
                timestamp=now,
            )
        )
    return quotes


@router.get("/symbols", response_model=list[SymbolInfo])
async def list_symbols(
    market: str = Query("crypto", description="Market type"),
):
    # Mock symbol list
    symbols = [
        SymbolInfo(symbol="BTC/USDT", market="crypto", base="BTC", quote="USDT"),
        SymbolInfo(symbol="ETH/USDT", market="crypto", base="ETH", quote="USDT"),
        SymbolInfo(symbol="SOL/USDT", market="crypto", base="SOL", quote="USDT"),
    ]
    return [s for s in symbols if s.market == market]
