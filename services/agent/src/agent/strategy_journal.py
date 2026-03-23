"""Strategy version tracking and trade journal backed by SQLite."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class StrategyJournal:
    """Record AI Agent strategy versions and their trading performance."""

    def __init__(self, db_path: str = "data/agent_journal.db") -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    # ── Schema ────────────────────────────────────────────────────

    def _init_schema(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS strategy_versions (
                version_id   TEXT PRIMARY KEY,
                version_num  INTEGER NOT NULL UNIQUE,
                persona      TEXT NOT NULL,
                model        TEXT NOT NULL,
                parameters   TEXT NOT NULL,     -- JSON
                reasoning    TEXT NOT NULL,
                created_at   TEXT NOT NULL,
                is_active    INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS trades (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                version_id  TEXT NOT NULL REFERENCES strategy_versions(version_id),
                symbol      TEXT NOT NULL,
                action      TEXT NOT NULL,       -- buy / sell
                price       REAL NOT NULL,
                quantity    REAL NOT NULL,
                reason      TEXT NOT NULL DEFAULT '',
                confidence  REAL NOT NULL DEFAULT 0.0,
                pnl         REAL,                -- filled later when position closes
                timestamp   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS decisions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                version_id   TEXT NOT NULL REFERENCES strategy_versions(version_id),
                cycle        INTEGER NOT NULL,
                symbol       TEXT NOT NULL,
                action       TEXT NOT NULL,      -- buy / sell / hold
                confidence   REAL NOT NULL DEFAULT 0.0,
                analysis     TEXT NOT NULL DEFAULT '',
                raw_response TEXT NOT NULL DEFAULT '',  -- full LLM JSON
                timestamp    TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sentiment_snapshots (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                version_id      TEXT NOT NULL REFERENCES strategy_versions(version_id),
                overall_sentiment TEXT NOT NULL,    -- bullish / bearish / neutral
                confidence      REAL NOT NULL DEFAULT 0.0,
                key_events      TEXT NOT NULL DEFAULT '[]',  -- JSON
                risk_factors    TEXT NOT NULL DEFAULT '[]',  -- JSON
                summary         TEXT NOT NULL DEFAULT '',
                news_count      INTEGER NOT NULL DEFAULT 0,
                analyzed_at     TEXT NOT NULL,
                created_at      TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_trades_version ON trades(version_id);
            CREATE INDEX IF NOT EXISTS idx_decisions_version ON decisions(version_id);
            CREATE INDEX IF NOT EXISTS idx_sentiment_version ON sentiment_snapshots(version_id);
        """)
        self._conn.commit()

    # ── Versions ──────────────────────────────────────────────────

    def create_version(
        self,
        persona: str,
        model: str,
        parameters: dict,
        reasoning: str,
    ) -> str:
        """Create a new strategy version and mark it as active.

        Returns the version_id (e.g. ``"v1"``, ``"v2"``).
        """
        row = self._conn.execute(
            "SELECT COALESCE(MAX(version_num), 0) AS n FROM strategy_versions"
        ).fetchone()
        next_num = row["n"] + 1
        version_id = f"v{next_num}"
        now = datetime.now(timezone.utc).isoformat()

        # Deactivate all previous versions.
        self._conn.execute("UPDATE strategy_versions SET is_active = 0")

        self._conn.execute(
            """
            INSERT INTO strategy_versions
                (version_id, version_num, persona, model, parameters, reasoning, created_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (version_id, next_num, persona, model, json.dumps(parameters), reasoning, now),
        )
        self._conn.commit()
        logger.info("Created strategy version %s", version_id)
        return version_id

    def get_active_version(self) -> dict | None:
        """Return the currently active strategy version, or ``None``."""
        row = self._conn.execute(
            "SELECT * FROM strategy_versions WHERE is_active = 1"
        ).fetchone()
        if row is None:
            return None
        return self._row_to_version(row)

    def list_versions(self) -> list[dict]:
        """List all strategy versions with their aggregate stats."""
        rows = self._conn.execute(
            "SELECT * FROM strategy_versions ORDER BY version_num"
        ).fetchall()
        result = []
        for row in rows:
            v = self._row_to_version(row)
            v["stats"] = self.get_version_stats(v["version_id"])
            result.append(v)
        return result

    def get_best_version(self, metric: str = "pnl") -> dict | None:
        """Return the version with the best value for *metric*.

        Supported metrics: ``pnl``, ``win_rate``, ``trade_count``.
        """
        versions = self.list_versions()
        if not versions:
            return None

        def _key(v: dict) -> float:
            stats = v.get("stats", {})
            if metric == "pnl":
                return stats.get("total_pnl", 0.0)
            if metric == "win_rate":
                return stats.get("win_rate", 0.0)
            if metric == "trade_count":
                return float(stats.get("trade_count", 0))
            return stats.get("total_pnl", 0.0)

        return max(versions, key=_key)

    def compare_versions(self, version_ids: list[str]) -> dict:
        """Compare stats for the given version ids."""
        comparison: dict[str, dict] = {}
        for vid in version_ids:
            comparison[vid] = self.get_version_stats(vid)
        return comparison

    # ── Trades ────────────────────────────────────────────────────

    def record_trade(self, version_id: str, trade: dict) -> None:
        """Persist a single trade execution."""
        now = trade.get("timestamp", datetime.now(timezone.utc).isoformat())
        self._conn.execute(
            """
            INSERT INTO trades (version_id, symbol, action, price, quantity, reason, confidence, pnl, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                version_id,
                trade.get("symbol", ""),
                trade.get("action", ""),
                trade.get("price", 0.0),
                trade.get("quantity", 0.0),
                trade.get("reason", ""),
                trade.get("confidence", 0.0),
                trade.get("pnl"),
                now,
            ),
        )
        self._conn.commit()

    def get_trades(self, version_id: str) -> list[dict]:
        """Return all trades for a version."""
        rows = self._conn.execute(
            "SELECT * FROM trades WHERE version_id = ? ORDER BY timestamp",
            (version_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Decisions ─────────────────────────────────────────────────

    def record_decision(self, version_id: str, decision: dict) -> None:
        """Persist an LLM decision (including hold)."""
        now = decision.get("timestamp", datetime.now(timezone.utc).isoformat())
        self._conn.execute(
            """
            INSERT INTO decisions (version_id, cycle, symbol, action, confidence, analysis, raw_response, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                version_id,
                decision.get("cycle", 0),
                decision.get("symbol", ""),
                decision.get("action", "hold"),
                decision.get("confidence", 0.0),
                decision.get("analysis", ""),
                json.dumps(decision.get("raw_response", ""), ensure_ascii=False) if isinstance(decision.get("raw_response"), dict) else str(decision.get("raw_response", "")),
                now,
            ),
        )
        self._conn.commit()

    # ── Sentiment ─────────────────────────────────────────────────

    def record_sentiment(self, version_id: str, result: object) -> None:
        """Persist a sentiment analysis snapshot.

        *result* should be a ``SentimentResult`` (duck-typed for testability).
        """
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """
            INSERT INTO sentiment_snapshots
                (version_id, overall_sentiment, confidence, key_events,
                 risk_factors, summary, news_count, analyzed_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                version_id,
                getattr(result, "overall_sentiment", "neutral"),
                getattr(result, "confidence", 0.0),
                json.dumps(getattr(result, "key_events", []), ensure_ascii=False),
                json.dumps(getattr(result, "risk_factors", []), ensure_ascii=False),
                getattr(result, "summary", ""),
                getattr(result, "news_count", 0),
                getattr(result, "analyzed_at", now),
                now,
            ),
        )
        self._conn.commit()

    def get_latest_sentiment(self, version_id: str | None = None) -> dict | None:
        """Return the most recent sentiment snapshot."""
        if version_id:
            row = self._conn.execute(
                "SELECT * FROM sentiment_snapshots WHERE version_id = ? ORDER BY created_at DESC LIMIT 1",
                (version_id,),
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT * FROM sentiment_snapshots ORDER BY created_at DESC LIMIT 1",
            ).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["key_events"] = json.loads(d["key_events"])
        d["risk_factors"] = json.loads(d["risk_factors"])
        return d

    def get_decisions(self, version_id: str, limit: int = 50) -> list[dict]:
        """Return recent decisions for a version."""
        rows = self._conn.execute(
            "SELECT * FROM decisions WHERE version_id = ? ORDER BY timestamp DESC LIMIT ?",
            (version_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Stats ─────────────────────────────────────────────────────

    def get_version_stats(self, version_id: str) -> dict:
        """Compute aggregate statistics for a strategy version."""
        trades = self.get_trades(version_id)
        decisions = self._conn.execute(
            "SELECT COUNT(*) AS cnt FROM decisions WHERE version_id = ?",
            (version_id,),
        ).fetchone()
        decision_count = decisions["cnt"] if decisions else 0

        trade_count = len(trades)
        if trade_count == 0:
            return {
                "trade_count": 0,
                "decision_count": decision_count,
                "win_count": 0,
                "loss_count": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "avg_confidence": 0.0,
            }

        pnls = [t.get("pnl") or 0.0 for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        total_pnl = sum(pnls)
        win_rate = len(wins) / trade_count * 100 if trade_count else 0.0

        # Max drawdown from cumulative PnL curve.
        cumulative = 0.0
        peak = 0.0
        max_dd = 0.0
        for p in pnls:
            cumulative += p
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_dd:
                max_dd = dd

        # Annualised Sharpe ratio (simplified, assuming daily returns).
        import statistics

        if len(pnls) > 1:
            mean_ret = statistics.mean(pnls)
            std_ret = statistics.stdev(pnls)
            sharpe = (mean_ret / std_ret * (252 ** 0.5)) if std_ret > 0 else 0.0
        else:
            sharpe = 0.0

        confidences = [t.get("confidence", 0.0) for t in trades]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return {
            "trade_count": trade_count,
            "decision_count": decision_count,
            "win_count": len(wins),
            "loss_count": len(losses),
            "win_rate": round(win_rate, 2),
            "total_pnl": round(total_pnl, 2),
            "max_drawdown": round(max_dd, 2),
            "sharpe_ratio": round(sharpe, 4),
            "avg_confidence": round(avg_confidence, 4),
        }

    def get_performance_summary(self, version_id: str) -> str:
        """Return a human-readable summary suitable for embedding in prompts."""
        stats = self.get_version_stats(version_id)
        if stats["trade_count"] == 0 and stats["decision_count"] == 0:
            return "尚无交易和决策记录。"

        lines = [
            f"策略版本: {version_id}",
            f"总决策次数: {stats['decision_count']}",
            f"总交易: {stats['trade_count']} 笔",
            f"胜率: {stats['win_rate']:.1f}% ({stats['win_count']}胜 / {stats['loss_count']}负)",
            f"净 PnL: {stats['total_pnl']:.2f}",
            f"最大回撤: {stats['max_drawdown']:.2f}",
            f"夏普比率: {stats['sharpe_ratio']:.4f}",
            f"平均置信度: {stats['avg_confidence']:.2f}",
        ]
        return "\n".join(lines)

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def _row_to_version(row: sqlite3.Row) -> dict:
        d = dict(row)
        d["parameters"] = json.loads(d["parameters"])
        return d

    def close(self) -> None:
        self._conn.close()
