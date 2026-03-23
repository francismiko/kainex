import json
from pathlib import Path

import pytest

from agent.strategy_journal import StrategyJournal


@pytest.fixture()
def journal(tmp_path: Path) -> StrategyJournal:
    """Create a StrategyJournal backed by a temporary SQLite database."""
    db = tmp_path / "test_journal.db"
    j = StrategyJournal(db_path=str(db))
    yield j
    j.close()


# ── Version management ────────────────────────────────────────────


class TestCreateVersion:
    def test_first_version_is_v1(self, journal: StrategyJournal):
        vid = journal.create_version("balanced", "gpt-5.4", {"a": 1}, "init")
        assert vid == "v1"

    def test_versions_increment(self, journal: StrategyJournal):
        v1 = journal.create_version("balanced", "gpt-5.4", {}, "first")
        v2 = journal.create_version("aggressive", "gpt-5.4", {}, "second")
        assert v1 == "v1"
        assert v2 == "v2"

    def test_latest_version_is_active(self, journal: StrategyJournal):
        journal.create_version("balanced", "m1", {}, "a")
        journal.create_version("aggressive", "m2", {}, "b")
        active = journal.get_active_version()
        assert active is not None
        assert active["version_id"] == "v2"
        assert active["persona"] == "aggressive"

    def test_only_one_active(self, journal: StrategyJournal):
        journal.create_version("balanced", "m1", {}, "a")
        journal.create_version("balanced", "m2", {}, "b")
        journal.create_version("balanced", "m3", {}, "c")
        versions = journal.list_versions()
        active_count = sum(1 for v in versions if v["is_active"])
        assert active_count == 1

    def test_parameters_serialized(self, journal: StrategyJournal):
        params = {"stop_loss_pct": 0.05, "symbols": ["BTC/USDT"]}
        journal.create_version("balanced", "m", params, "r")
        v = journal.get_active_version()
        assert v is not None
        assert v["parameters"] == params


class TestListVersions:
    def test_empty(self, journal: StrategyJournal):
        assert journal.list_versions() == []

    def test_lists_all(self, journal: StrategyJournal):
        journal.create_version("balanced", "m", {}, "a")
        journal.create_version("aggressive", "m", {}, "b")
        versions = journal.list_versions()
        assert len(versions) == 2
        assert versions[0]["version_id"] == "v1"
        assert versions[1]["version_id"] == "v2"

    def test_includes_stats(self, journal: StrategyJournal):
        journal.create_version("balanced", "m", {}, "a")
        versions = journal.list_versions()
        assert "stats" in versions[0]
        assert "trade_count" in versions[0]["stats"]


# ── Trade recording ───────────────────────────────────────────────


class TestRecordTrade:
    def test_record_and_retrieve(self, journal: StrategyJournal):
        vid = journal.create_version("balanced", "m", {}, "a")
        journal.record_trade(vid, {
            "symbol": "BTC/USDT",
            "action": "buy",
            "price": 65000.0,
            "quantity": 0.1,
            "reason": "uptrend",
            "confidence": 0.85,
        })
        trades = journal.get_trades(vid)
        assert len(trades) == 1
        assert trades[0]["symbol"] == "BTC/USDT"
        assert trades[0]["action"] == "buy"
        assert trades[0]["price"] == 65000.0
        assert trades[0]["quantity"] == 0.1

    def test_multiple_trades(self, journal: StrategyJournal):
        vid = journal.create_version("balanced", "m", {}, "a")
        for i in range(5):
            journal.record_trade(vid, {
                "symbol": "BTC/USDT",
                "action": "buy" if i % 2 == 0 else "sell",
                "price": 60000 + i * 1000,
                "quantity": 0.1,
                "pnl": 100.0 if i % 2 == 0 else -50.0,
            })
        trades = journal.get_trades(vid)
        assert len(trades) == 5

    def test_trades_isolated_per_version(self, journal: StrategyJournal):
        v1 = journal.create_version("balanced", "m", {}, "a")
        v2 = journal.create_version("balanced", "m", {}, "b")
        journal.record_trade(v1, {"symbol": "BTC", "action": "buy", "price": 1, "quantity": 1})
        journal.record_trade(v2, {"symbol": "ETH", "action": "sell", "price": 2, "quantity": 2})
        assert len(journal.get_trades(v1)) == 1
        assert len(journal.get_trades(v2)) == 1
        assert journal.get_trades(v1)[0]["symbol"] == "BTC"
        assert journal.get_trades(v2)[0]["symbol"] == "ETH"


# ── Decision recording ───────────────────────────────────────────


class TestRecordDecision:
    def test_record_and_retrieve(self, journal: StrategyJournal):
        vid = journal.create_version("balanced", "m", {}, "a")
        journal.record_decision(vid, {
            "cycle": 0,
            "symbol": "BTC/USDT",
            "action": "hold",
            "confidence": 0.4,
            "analysis": "unclear signals",
            "raw_response": '{"decisions":[]}',
        })
        decisions = journal.get_decisions(vid)
        assert len(decisions) == 1
        assert decisions[0]["action"] == "hold"
        assert decisions[0]["cycle"] == 0

    def test_decision_limit(self, journal: StrategyJournal):
        vid = journal.create_version("balanced", "m", {}, "a")
        for i in range(10):
            journal.record_decision(vid, {
                "cycle": i,
                "symbol": "BTC/USDT",
                "action": "hold",
            })
        assert len(journal.get_decisions(vid, limit=5)) == 5
        assert len(journal.get_decisions(vid, limit=50)) == 10


# ── Stats ─────────────────────────────────────────────────────────


class TestGetVersionStats:
    def test_empty_stats(self, journal: StrategyJournal):
        vid = journal.create_version("balanced", "m", {}, "a")
        stats = journal.get_version_stats(vid)
        assert stats["trade_count"] == 0
        assert stats["win_rate"] == 0.0
        assert stats["total_pnl"] == 0.0
        assert stats["max_drawdown"] == 0.0
        assert stats["sharpe_ratio"] == 0.0

    def test_all_wins(self, journal: StrategyJournal):
        vid = journal.create_version("balanced", "m", {}, "a")
        for _ in range(5):
            journal.record_trade(vid, {
                "symbol": "BTC", "action": "buy", "price": 100, "quantity": 1,
                "pnl": 50.0,
            })
        stats = journal.get_version_stats(vid)
        assert stats["trade_count"] == 5
        assert stats["win_rate"] == 100.0
        assert stats["total_pnl"] == 250.0
        assert stats["win_count"] == 5
        assert stats["loss_count"] == 0

    def test_mixed_trades(self, journal: StrategyJournal):
        vid = journal.create_version("balanced", "m", {}, "a")
        pnls = [100, -30, 50, -20, 80]
        for p in pnls:
            journal.record_trade(vid, {
                "symbol": "BTC", "action": "buy", "price": 100, "quantity": 1,
                "pnl": float(p),
            })
        stats = journal.get_version_stats(vid)
        assert stats["trade_count"] == 5
        assert stats["win_count"] == 3
        assert stats["loss_count"] == 2
        assert stats["win_rate"] == 60.0
        assert stats["total_pnl"] == 180.0

    def test_max_drawdown(self, journal: StrategyJournal):
        vid = journal.create_version("balanced", "m", {}, "a")
        # Cumulative: 100, 80, 60, 110, 90
        # Peak at 100, drawdown to 60 => DD=40; peak at 110, dd to 90 => DD=20
        pnls = [100, -20, -20, 50, -20]
        for p in pnls:
            journal.record_trade(vid, {
                "symbol": "BTC", "action": "buy", "price": 100, "quantity": 1,
                "pnl": float(p),
            })
        stats = journal.get_version_stats(vid)
        assert stats["max_drawdown"] == 40.0

    def test_decisions_counted(self, journal: StrategyJournal):
        vid = journal.create_version("balanced", "m", {}, "a")
        for i in range(3):
            journal.record_decision(vid, {"cycle": i, "symbol": "BTC", "action": "hold"})
        stats = journal.get_version_stats(vid)
        assert stats["decision_count"] == 3


# ── Performance summary ──────────────────────────────────────────


class TestPerformanceSummary:
    def test_empty(self, journal: StrategyJournal):
        vid = journal.create_version("balanced", "m", {}, "a")
        summary = journal.get_performance_summary(vid)
        assert "尚无" in summary

    def test_with_data(self, journal: StrategyJournal):
        vid = journal.create_version("balanced", "m", {}, "a")
        journal.record_trade(vid, {
            "symbol": "BTC", "action": "buy", "price": 100, "quantity": 1, "pnl": 50.0,
        })
        journal.record_decision(vid, {"cycle": 0, "symbol": "BTC", "action": "buy"})
        summary = journal.get_performance_summary(vid)
        assert vid in summary
        assert "胜率" in summary
        assert "PnL" in summary


# ── Best version / comparison ─────────────────────────────────────


class TestBestVersion:
    def test_no_versions(self, journal: StrategyJournal):
        assert journal.get_best_version() is None

    def test_single_version(self, journal: StrategyJournal):
        journal.create_version("balanced", "m", {}, "a")
        best = journal.get_best_version()
        assert best is not None
        assert best["version_id"] == "v1"

    def test_selects_highest_pnl(self, journal: StrategyJournal):
        v1 = journal.create_version("balanced", "m", {}, "a")
        v2 = journal.create_version("aggressive", "m", {}, "b")
        journal.record_trade(v1, {"symbol": "BTC", "action": "buy", "price": 1, "quantity": 1, "pnl": 100.0})
        journal.record_trade(v2, {"symbol": "BTC", "action": "buy", "price": 1, "quantity": 1, "pnl": 200.0})
        best = journal.get_best_version(metric="pnl")
        assert best is not None
        assert best["version_id"] == "v2"

    def test_selects_highest_win_rate(self, journal: StrategyJournal):
        v1 = journal.create_version("balanced", "m", {}, "a")
        v2 = journal.create_version("aggressive", "m", {}, "b")
        # v1: 1 win, 1 loss = 50%
        journal.record_trade(v1, {"symbol": "BTC", "action": "buy", "price": 1, "quantity": 1, "pnl": 10.0})
        journal.record_trade(v1, {"symbol": "BTC", "action": "sell", "price": 1, "quantity": 1, "pnl": -5.0})
        # v2: 2 wins = 100%
        journal.record_trade(v2, {"symbol": "BTC", "action": "buy", "price": 1, "quantity": 1, "pnl": 1.0})
        journal.record_trade(v2, {"symbol": "BTC", "action": "buy", "price": 1, "quantity": 1, "pnl": 1.0})
        best = journal.get_best_version(metric="win_rate")
        assert best is not None
        assert best["version_id"] == "v2"


class TestCompareVersions:
    def test_compare(self, journal: StrategyJournal):
        v1 = journal.create_version("balanced", "m", {}, "a")
        v2 = journal.create_version("aggressive", "m", {}, "b")
        journal.record_trade(v1, {"symbol": "BTC", "action": "buy", "price": 1, "quantity": 1, "pnl": 100.0})
        comparison = journal.compare_versions([v1, v2])
        assert v1 in comparison
        assert v2 in comparison
        assert comparison[v1]["total_pnl"] == 100.0
        assert comparison[v2]["total_pnl"] == 0.0
