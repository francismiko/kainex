import asyncio
import json
import logging
import random
import time
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and channel subscriptions."""

    def __init__(self) -> None:
        self._connections: dict[WebSocket, set[str]] = {}

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections[ws] = set()

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.pop(ws, None)

    def subscribe(self, ws: WebSocket, channel: str) -> None:
        if ws in self._connections:
            self._connections[ws].add(channel)

    def unsubscribe(self, ws: WebSocket, channel: str) -> None:
        if ws in self._connections:
            self._connections[ws].discard(channel)

    def get_channels(self, ws: WebSocket) -> set[str]:
        return self._connections.get(ws, set())

    async def broadcast(self, channel: str, data: dict[str, Any]) -> None:
        """Send data to all clients subscribed to the given channel."""
        for ws, channels in list(self._connections.items()):
            if channel in channels:
                try:
                    await ws.send_json({"channel": channel, "data": data})
                except Exception:
                    self.disconnect(ws)

    @property
    def active_connections(self) -> int:
        return len(self._connections)

    def channels_with_prefix(self, prefix: str) -> set[str]:
        """Return all unique channels across all clients matching a prefix."""
        result: set[str] = set()
        for channels in self._connections.values():
            for ch in channels:
                if ch.startswith(prefix):
                    result.add(ch)
        return result


manager = ConnectionManager()

# Background tasks tracking
_mock_tasks: dict[str, asyncio.Task[None]] = {}


def _generate_mock_bar(symbol: str, timeframe: str) -> dict[str, Any]:
    """Generate a single simulated OHLCV bar."""
    base_prices: dict[str, float] = {
        "BTC/USDT": 62000,
        "ETH/USDT": 3400,
        "SOL/USDT": 145,
    }
    base = base_prices.get(symbol, 100.0)
    volatility = base * 0.002

    open_price = base + random.uniform(-volatility, volatility)
    close_price = open_price + random.uniform(-volatility, volatility)
    high_price = max(open_price, close_price) + random.uniform(0, volatility * 0.5)
    low_price = min(open_price, close_price) - random.uniform(0, volatility * 0.5)
    volume = random.uniform(100, 5000)

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "open": round(open_price, 2),
        "high": round(high_price, 2),
        "low": round(low_price, 2),
        "close": round(close_price, 2),
        "volume": round(volume, 2),
        "timestamp": int(time.time()),
    }


def _generate_mock_signal(strategy_id: str) -> dict[str, Any]:
    """Generate a simulated strategy signal."""
    directions = ["long", "short", "close"]
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    symbol = random.choice(symbols)
    base_prices: dict[str, float] = {
        "BTC/USDT": 62000,
        "ETH/USDT": 3400,
        "SOL/USDT": 145,
    }
    return {
        "strategy_id": strategy_id,
        "symbol": symbol,
        "direction": random.choice(directions),
        "price": round(base_prices.get(symbol, 100) + random.uniform(-50, 50), 2),
        "quantity": round(random.uniform(0.01, 1.0), 4),
        "timestamp": int(time.time()),
    }


def _generate_mock_portfolio() -> dict[str, Any]:
    """Generate a simulated portfolio snapshot."""
    return {
        "total_value": round(random.uniform(90000, 110000), 2),
        "cash": round(random.uniform(10000, 50000), 2),
        "daily_pnl": round(random.uniform(-2000, 2000), 2),
        "total_pnl": round(random.uniform(-5000, 15000), 2),
        "positions_count": random.randint(0, 5),
        "timestamp": int(time.time()),
    }


async def _mock_market_loop(channel: str, symbol: str, timeframe: str) -> None:
    """Background task: emit a simulated bar every second for a market channel."""
    try:
        while True:
            await asyncio.sleep(1)
            bar = _generate_mock_bar(symbol, timeframe)
            await manager.broadcast(channel, bar)
    except asyncio.CancelledError:
        pass


async def _mock_signal_loop(channel: str, strategy_id: str) -> None:
    """Background task: emit a simulated signal every 3 seconds."""
    try:
        while True:
            await asyncio.sleep(3)
            signal = _generate_mock_signal(strategy_id)
            await manager.broadcast(channel, signal)
    except asyncio.CancelledError:
        pass


async def _mock_portfolio_loop(channel: str) -> None:
    """Background task: emit portfolio updates every 2 seconds."""
    try:
        while True:
            await asyncio.sleep(2)
            snapshot = _generate_mock_portfolio()
            await manager.broadcast(channel, snapshot)
    except asyncio.CancelledError:
        pass


def _ensure_mock_task(channel: str) -> None:
    """Start a mock data generator for the channel if not already running."""
    if channel in _mock_tasks and not _mock_tasks[channel].done():
        return

    parts = channel.split(":")
    if parts[0] == "market" and len(parts) == 3:
        symbol, timeframe = parts[1], parts[2]
        _mock_tasks[channel] = asyncio.create_task(
            _mock_market_loop(channel, symbol, timeframe)
        )
    elif parts[0] == "signals" and len(parts) == 2:
        strategy_id = parts[1]
        _mock_tasks[channel] = asyncio.create_task(
            _mock_signal_loop(channel, strategy_id)
        )
    elif parts[0] == "portfolio":
        _mock_tasks[channel] = asyncio.create_task(
            _mock_portfolio_loop(channel)
        )


def _maybe_stop_mock_task(channel: str) -> None:
    """Cancel mock generator if no client is subscribed to the channel anymore."""
    for channels in manager._connections.values():
        if channel in channels:
            return
    task = _mock_tasks.pop(channel, None)
    if task and not task.done():
        task.cancel()


def _parse_channel(channel: str) -> str | None:
    """Validate channel format. Returns None if invalid."""
    parts = channel.split(":")
    if parts[0] == "market" and len(parts) == 3:
        return channel
    if parts[0] == "signals" and len(parts) == 2:
        return channel
    if parts[0] == "portfolio" and len(parts) == 1:
        return channel
    return None


@router.websocket("/stream")
async def stream(ws: WebSocket) -> None:
    await manager.connect(ws)
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"error": "invalid JSON"})
                continue

            action = msg.get("action")
            channel = msg.get("channel", "")

            if action == "subscribe":
                validated = _parse_channel(channel)
                if validated is None:
                    await ws.send_json({"error": f"invalid channel: {channel}"})
                    continue
                manager.subscribe(ws, validated)
                _ensure_mock_task(validated)
                await ws.send_json({"status": "subscribed", "channel": validated})

            elif action == "unsubscribe":
                validated = _parse_channel(channel)
                if validated is None:
                    await ws.send_json({"error": f"invalid channel: {channel}"})
                    continue
                manager.unsubscribe(ws, validated)
                _maybe_stop_mock_task(validated)
                await ws.send_json({"status": "unsubscribed", "channel": validated})

            # Backward-compatible: support legacy {"subscribe": "..."} format
            elif "subscribe" in msg:
                ch = msg["subscribe"]
                validated = _parse_channel(ch)
                if validated is None:
                    await ws.send_json({"error": f"invalid channel: {ch}"})
                    continue
                manager.subscribe(ws, validated)
                _ensure_mock_task(validated)
                await ws.send_json({"status": "subscribed", "channel": validated})

            elif "unsubscribe" in msg:
                ch = msg["unsubscribe"]
                validated = _parse_channel(ch)
                if validated is None:
                    await ws.send_json({"error": f"invalid channel: {ch}"})
                    continue
                manager.unsubscribe(ws, validated)
                _maybe_stop_mock_task(validated)
                await ws.send_json({"status": "unsubscribed", "channel": validated})

            else:
                await ws.send_json(
                    {"error": "unknown command, use {\"action\": \"subscribe\", \"channel\": \"...\"}"}
                )

    except WebSocketDisconnect:
        subscribed = manager.get_channels(ws).copy()
        manager.disconnect(ws)
        for ch in subscribed:
            _maybe_stop_mock_task(ch)


async def broadcast(channel: str, data: dict[str, Any]) -> None:
    """Public helper for other modules to push data into WebSocket channels."""
    await manager.broadcast(channel, data)
