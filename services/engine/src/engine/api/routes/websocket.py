import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
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

    async def broadcast(self, channel: str, message: dict) -> None:
        for ws, channels in list(self._connections.items()):
            if channel in channels:
                try:
                    await ws.send_json({"channel": channel, "data": message})
                except Exception:
                    self.disconnect(ws)

    @property
    def active_connections(self) -> int:
        return len(self._connections)


manager = ConnectionManager()


@router.websocket("/stream")
async def stream(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"error": "invalid JSON"})
                continue

            if "subscribe" in msg:
                channel = msg["subscribe"]
                manager.subscribe(ws, channel)
                await ws.send_json({"status": "subscribed", "channel": channel})

            elif "unsubscribe" in msg:
                channel = msg["unsubscribe"]
                manager.unsubscribe(ws, channel)
                await ws.send_json({"status": "unsubscribed", "channel": channel})

            else:
                await ws.send_json({"error": "unknown command, use subscribe/unsubscribe"})

    except WebSocketDisconnect:
        manager.disconnect(ws)


async def broadcast(channel: str, message: dict) -> None:
    await manager.broadcast(channel, message)
