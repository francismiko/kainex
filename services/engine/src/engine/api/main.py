from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from engine.api.routes import backtest, market_data, portfolio, strategies, websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize connections
    # TODO: setup Redis and DB connections
    app.state.redis = None
    app.state.db = None
    yield
    # Shutdown: close connections
    if app.state.redis:
        await app.state.redis.close()


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
