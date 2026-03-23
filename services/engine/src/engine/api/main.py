from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from engine.api.routes import backtest, market_data, portfolio, strategies, websocket
from engine.storage.sqlite_store import SQLiteStore
from engine.storage.duckdb_store import DuckDBStore
from engine.strategies.registry import StrategyRegistry, registry as strategy_registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize storage connections
    sqlite_store = SQLiteStore()
    await sqlite_store.connect()
    duckdb_store = DuckDBStore()
    app.state.sqlite_store = sqlite_store
    app.state.duckdb_store = duckdb_store
    app.state.strategy_registry = strategy_registry
    yield
    # Shutdown: close connections
    await sqlite_store.close()
    duckdb_store.close()


app = FastAPI(
    title="Kainex Engine API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(strategies.router, prefix="/api/strategies", tags=["strategies"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["backtest"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(market_data.router, prefix="/api/market-data", tags=["market-data"])
app.include_router(websocket.router, prefix="/api/ws", tags=["websocket"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


def run():
    uvicorn.run("engine.api.main:app", host="0.0.0.0", port=8001, reload=True)
