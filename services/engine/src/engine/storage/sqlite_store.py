from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = Path(__file__).resolve().parents[3] / "data" / "kainex_state.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS strategy_configs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    class_name TEXT NOT NULL,
    parameters TEXT DEFAULT '{}',
    markets TEXT DEFAULT '[]',
    timeframes TEXT DEFAULT '[]',
    status TEXT DEFAULT 'stopped',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    filled_price REAL,
    commission REAL DEFAULT 0.0,
    pnl REAL DEFAULT 0.0,
    status TEXT DEFAULT 'pending',
    created_at TEXT NOT NULL,
    filled_at TEXT
);

CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    quantity REAL NOT NULL DEFAULT 0.0,
    avg_price REAL NOT NULL DEFAULT 0.0,
    market_price REAL DEFAULT 0.0,
    unrealized_pnl REAL DEFAULT 0.0,
    updated_at TEXT NOT NULL,
    UNIQUE(strategy_id, symbol)
);

CREATE TABLE IF NOT EXISTS backtest_results (
    id TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    parameters TEXT DEFAULT '{}',
    market TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    initial_capital REAL NOT NULL,
    metrics TEXT DEFAULT '{}',
    equity_curve TEXT DEFAULT '[]',
    trade_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'completed',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alerts (
    id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    market TEXT NOT NULL DEFAULT 'crypto',
    condition TEXT NOT NULL,
    price REAL NOT NULL,
    message TEXT DEFAULT '',
    enabled INTEGER DEFAULT 1,
    triggered INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


class SQLiteStore:
    """Async SQLite store for OLTP state management."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = str(db_path or _DEFAULT_DB_PATH)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(_SCHEMA)
        await self._db.commit()
        logger.info("SQLite store connected: %s", self.db_path)

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("SQLiteStore not connected. Call connect() first.")
        return self._db

    # --- Strategy Configs ---

    async def save_strategy_config(
        self,
        id: str,
        name: str,
        class_name: str,
        parameters: dict,
        markets: list[str],
        timeframes: list[str],
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.db.execute(
            """INSERT OR REPLACE INTO strategy_configs
               (id, name, class_name, parameters, markets, timeframes, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 'stopped', ?, ?)""",
            (
                id,
                name,
                class_name,
                json.dumps(parameters),
                json.dumps(markets),
                json.dumps(timeframes),
                now,
                now,
            ),
        )
        await self.db.commit()

    async def get_strategy_config(self, id: str) -> dict | None:
        cursor = await self.db.execute(
            "SELECT * FROM strategy_configs WHERE id = ?", (id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return self._row_to_dict(row)

    async def update_strategy_fields(self, id: str, fields: dict) -> None:
        """Update specific fields on a strategy config."""
        now = datetime.now(timezone.utc).isoformat()
        set_clauses = []
        params = []
        for key, value in fields.items():
            if key == "parameters":
                set_clauses.append("parameters = ?")
                params.append(json.dumps(value))
            elif key in ("status", "name", "class_name"):
                set_clauses.append(f"{key} = ?")
                params.append(value)
        set_clauses.append("updated_at = ?")
        params.append(now)
        params.append(id)
        await self.db.execute(
            f"UPDATE strategy_configs SET {', '.join(set_clauses)} WHERE id = ?",
            params,
        )
        await self.db.commit()

    async def list_strategy_configs(self) -> list[dict]:
        cursor = await self.db.execute(
            "SELECT * FROM strategy_configs ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [self._row_to_dict(r) for r in rows]

    # --- Trades ---

    async def save_trade(self, trade: dict) -> None:
        await self.db.execute(
            """INSERT OR REPLACE INTO trades
               (id, strategy_id, symbol, side, quantity, price, filled_price, commission, pnl, status, created_at, filled_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                trade["id"],
                trade["strategy_id"],
                trade["symbol"],
                trade["side"],
                trade["quantity"],
                trade["price"],
                trade.get("filled_price"),
                trade.get("commission", 0.0),
                trade.get("pnl", 0.0),
                trade.get("status", "pending"),
                trade["created_at"],
                trade.get("filled_at"),
            ),
        )
        await self.db.commit()

    async def list_trades(
        self, strategy_id: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[dict]:
        if strategy_id:
            cursor = await self.db.execute(
                "SELECT * FROM trades WHERE strategy_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (strategy_id, limit, offset),
            )
        else:
            cursor = await self.db.execute(
                "SELECT * FROM trades ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
        rows = await cursor.fetchall()
        return [self._row_to_dict(r) for r in rows]

    # --- Backtest Results ---

    async def save_backtest_result(self, result: dict) -> None:
        await self.db.execute(
            """INSERT OR REPLACE INTO backtest_results
               (id, strategy_id, parameters, market, start_date, end_date, initial_capital,
                metrics, equity_curve, trade_count, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                result["id"],
                result["strategy_id"],
                json.dumps(result.get("parameters", {})),
                result["market"],
                result["start_date"],
                result["end_date"],
                result["initial_capital"],
                json.dumps(result.get("metrics", {})),
                json.dumps(result.get("equity_curve", [])),
                result.get("trade_count", 0),
                result.get("status", "completed"),
                result["created_at"],
            ),
        )
        await self.db.commit()

    async def get_backtest_result(self, id: str) -> dict | None:
        cursor = await self.db.execute(
            "SELECT * FROM backtest_results WHERE id = ?", (id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return self._row_to_dict(row)

    async def list_backtest_results(self, limit: int = 50) -> list[dict]:
        cursor = await self.db.execute(
            "SELECT * FROM backtest_results ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [self._row_to_dict(r) for r in rows]

    # --- Alerts ---

    async def create_alert(self, alert: dict) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.db.execute(
            """INSERT INTO alerts
               (id, symbol, market, condition, price, message, enabled, triggered, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                alert["id"],
                alert["symbol"],
                alert.get("market", "crypto"),
                alert["condition"],
                alert["price"],
                alert.get("message", ""),
                1 if alert.get("enabled", True) else 0,
                0,
                now,
                now,
            ),
        )
        await self.db.commit()

    async def get_alert(self, id: str) -> dict | None:
        cursor = await self.db.execute("SELECT * FROM alerts WHERE id = ?", (id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return self._alert_row_to_dict(row)

    async def list_alerts(self) -> list[dict]:
        cursor = await self.db.execute(
            "SELECT * FROM alerts ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [self._alert_row_to_dict(r) for r in rows]

    async def update_alert(self, id: str, fields: dict) -> None:
        now = datetime.now(timezone.utc).isoformat()
        set_clauses = []
        params: list = []
        for key, value in fields.items():
            if key == "enabled":
                set_clauses.append("enabled = ?")
                params.append(1 if value else 0)
            elif key == "triggered":
                set_clauses.append("triggered = ?")
                params.append(1 if value else 0)
            elif key == "message":
                set_clauses.append("message = ?")
                params.append(value)
        if not set_clauses:
            return
        set_clauses.append("updated_at = ?")
        params.append(now)
        params.append(id)
        await self.db.execute(
            f"UPDATE alerts SET {', '.join(set_clauses)} WHERE id = ?",
            params,
        )
        await self.db.commit()

    async def delete_alert(self, id: str) -> bool:
        cursor = await self.db.execute("DELETE FROM alerts WHERE id = ?", (id,))
        await self.db.commit()
        return cursor.rowcount > 0

    @staticmethod
    def _alert_row_to_dict(row: aiosqlite.Row) -> dict:
        d = dict(row)
        d["enabled"] = bool(d.get("enabled", 1))
        d["triggered"] = bool(d.get("triggered", 0))
        return d

    @staticmethod
    def _row_to_dict(row: aiosqlite.Row) -> dict:
        d = dict(row)
        for key in ("parameters", "markets", "timeframes", "metrics", "equity_curve"):
            if key in d and isinstance(d[key], str):
                d[key] = json.loads(d[key])
        return d
