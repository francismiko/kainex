# WebSocket Protocol

Kainex uses WebSocket for real-time streaming of market data, strategy signals, portfolio updates, and execution logs.

## Connection

Connect to the WebSocket endpoint:

```
ws://localhost:8001/api/ws/stream
```

All communication uses JSON messages.

## Subscribe / Unsubscribe

### Subscribe to a channel

```json
{"action": "subscribe", "channel": "market:BTC/USDT:1m"}
```

**Response:**

```json
{"status": "subscribed", "channel": "market:BTC/USDT:1m"}
```

### Unsubscribe from a channel

```json
{"action": "unsubscribe", "channel": "market:BTC/USDT:1m"}
```

**Response:**

```json
{"status": "unsubscribed", "channel": "market:BTC/USDT:1m"}
```

### Legacy format

The legacy subscription format is also supported:

```json
{"subscribe": "market:BTC/USDT:1m"}
{"unsubscribe": "market:BTC/USDT:1m"}
```

## Channels

### `market:{symbol}:{timeframe}`

Real-time OHLCV bar data for a specific symbol and timeframe.

**Example:** `market:BTC/USDT:1m`

**Message format:**

```json
{
  "channel": "market:BTC/USDT:1m",
  "data": {
    "symbol": "BTC/USDT",
    "timeframe": "1m",
    "open": 62015.30,
    "high": 62050.00,
    "low": 61990.50,
    "close": 62020.80,
    "volume": 1250.50,
    "timestamp": 1710950400
  }
}
```

### `signals:{strategy_id}`

Strategy signals generated in real time.

**Example:** `signals:sma_crossover`

**Message format:**

```json
{
  "channel": "signals:sma_crossover",
  "data": {
    "strategy_id": "sma_crossover",
    "symbol": "BTC/USDT",
    "direction": "long",
    "price": 62015.30,
    "quantity": 0.5,
    "timestamp": 1710950400
  }
}
```

Signal `direction` values: `"long"`, `"short"`, `"close"`.

### `portfolio`

Portfolio snapshot updates.

**Example:** `portfolio`

**Message format:**

```json
{
  "channel": "portfolio",
  "data": {
    "total_value": 105250.00,
    "cash": 50000.00,
    "daily_pnl": 1250.00,
    "total_pnl": 5250.00,
    "positions_count": 3,
    "timestamp": 1710950400
  }
}
```

### `logs`

Execution log entries streamed in real time.

**Example:** `logs`

**Message format:**

```json
{
  "channel": "logs",
  "data": {
    "timestamp": "2024-03-20T14:30:00Z",
    "level": "INFO",
    "source": "sma_crossover",
    "message": "BUY signal generated for BTC/USDT at 62015.30",
    "metadata": null
  }
}
```

## Error Handling

Invalid channel format:

```json
{"error": "invalid channel: foo:bar:baz:qux"}
```

Unknown command:

```json
{"error": "unknown command, use {\"action\": \"subscribe\", \"channel\": \"...\"}"}
```

Invalid JSON:

```json
{"error": "invalid JSON"}
```

## Connection Management

- The server accepts the WebSocket connection immediately on connect.
- Each connection maintains its own set of subscribed channels.
- Background data generators are started per channel on the first subscription and stopped when the last subscriber disconnects.
- On disconnect, all subscriptions for that connection are cleaned up automatically.

## JavaScript Client Example

```js
const ws = new WebSocket("ws://localhost:8001/api/ws/stream");

ws.onopen = () => {
  // Subscribe to BTC 1-minute bars and portfolio updates
  ws.send(JSON.stringify({ action: "subscribe", channel: "market:BTC/USDT:1m" }));
  ws.send(JSON.stringify({ action: "subscribe", channel: "portfolio" }));
  ws.send(JSON.stringify({ action: "subscribe", channel: "logs" }));
};

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);

  if (msg.channel?.startsWith("market:")) {
    // Handle OHLCV bar update
    console.log("Bar:", msg.data);
  } else if (msg.channel === "portfolio") {
    // Handle portfolio snapshot
    console.log("Portfolio:", msg.data);
  } else if (msg.channel === "logs") {
    // Handle log entry
    console.log("Log:", msg.data);
  } else if (msg.status) {
    // Subscription confirmation
    console.log("Status:", msg.status, msg.channel);
  } else if (msg.error) {
    console.error("Error:", msg.error);
  }
};

ws.onclose = () => {
  console.log("Disconnected");
};
```

## Python Client Example

```python
import asyncio
import json
import websockets


async def main():
    async with websockets.connect("ws://localhost:8001/api/ws/stream") as ws:
        # Subscribe
        await ws.send(json.dumps({
            "action": "subscribe",
            "channel": "market:ETH/USDT:1m",
        }))

        async for message in ws:
            data = json.loads(message)
            if "channel" in data:
                print(f"[{data['channel']}] {data['data']}")
            elif "status" in data:
                print(f"Subscribed to {data['channel']}")


asyncio.run(main())
```
