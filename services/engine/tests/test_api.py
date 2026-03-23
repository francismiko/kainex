import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from engine.api.main import app
from engine.storage.sqlite_store import SQLiteStore
from engine.storage.duckdb_store import DuckDBStore
from engine.strategies.registry import StrategyRegistry, registry as strategy_registry


@pytest.fixture(autouse=True)
def _mock_stores():
    """Mock SQLiteStore and DuckDBStore on app.state for all tests."""
    mock_sqlite = AsyncMock(spec=SQLiteStore)
    mock_sqlite.db = AsyncMock()
    mock_duckdb = MagicMock(spec=DuckDBStore)

    app.state.sqlite_store = mock_sqlite
    app.state.duckdb_store = mock_duckdb
    app.state.strategy_registry = strategy_registry

    yield mock_sqlite, mock_duckdb


client = TestClient(app, raise_server_exceptions=False)


# --------------- Health ---------------

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"


# --------------- Strategies ---------------

def _make_strategy_row(id="abc123", name="My SMA", class_name="sma_crossover", **overrides):
    now = datetime.now(timezone.utc).isoformat()
    row = {
        "id": id,
        "name": name,
        "class_name": class_name,
        "parameters": {"short_window": 5, "long_window": 20},
        "markets": ["crypto"],
        "timeframes": ["1d"],
        "status": "stopped",
        "created_at": now,
        "updated_at": now,
    }
    row.update(overrides)
    return row


class TestStrategies:
    def test_list_empty(self, _mock_stores):
        mock_sqlite, _ = _mock_stores
        mock_sqlite.list_strategy_configs.return_value = []
        resp = client.get("/api/strategies/")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create(self, _mock_stores):
        mock_sqlite, _ = _mock_stores
        row = _make_strategy_row()
        mock_sqlite.save_strategy_config.return_value = None
        mock_sqlite.get_strategy_config.return_value = row

        resp = client.post("/api/strategies/", json={
            "name": "My SMA",
            "class_name": "sma_crossover",
            "parameters": {"short_window": 5, "long_window": 20},
            "markets": ["crypto"],
            "timeframes": ["1d"],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My SMA"
        assert data["class_name"] == "sma_crossover"
        assert data["status"] == "stopped"

    def test_create_invalid_class(self, _mock_stores):
        resp = client.post("/api/strategies/", json={
            "name": "Bad",
            "class_name": "nonexistent",
            "parameters": {},
            "markets": ["crypto"],
            "timeframes": ["1d"],
        })
        assert resp.status_code == 400

    def test_list_after_create(self, _mock_stores):
        mock_sqlite, _ = _mock_stores
        mock_sqlite.list_strategy_configs.return_value = [_make_strategy_row()]
        resp = client.get("/api/strategies/")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_detail(self, _mock_stores):
        mock_sqlite, _ = _mock_stores
        row = _make_strategy_row(id="test123")
        mock_sqlite.get_strategy_config.return_value = row
        resp = client.get("/api/strategies/test123")
        assert resp.status_code == 200
        assert resp.json()["id"] == "test123"

    def test_get_not_found(self, _mock_stores):
        mock_sqlite, _ = _mock_stores
        mock_sqlite.get_strategy_config.return_value = None
        resp = client.get("/api/strategies/nonexistent")
        assert resp.status_code == 404

    def test_update(self, _mock_stores):
        mock_sqlite, _ = _mock_stores
        row = _make_strategy_row(id="test123")
        updated_row = {**row, "parameters": {"short_window": 3}}
        mock_sqlite.get_strategy_config.side_effect = [row, updated_row]
        mock_sqlite.update_strategy_fields.return_value = None

        resp = client.put("/api/strategies/test123", json={"parameters": {"short_window": 3}})
        assert resp.status_code == 200
        assert resp.json()["parameters"]["short_window"] == 3

    def test_update_not_found(self, _mock_stores):
        mock_sqlite, _ = _mock_stores
        mock_sqlite.get_strategy_config.return_value = None
        resp = client.put("/api/strategies/nonexistent", json={"parameters": {}})
        assert resp.status_code == 404

    def test_start_stop(self, _mock_stores):
        mock_sqlite, _ = _mock_stores
        row = _make_strategy_row(id="test123")
        running_row = {**row, "status": "running"}
        stopped_row = {**row, "status": "stopped"}

        mock_sqlite.get_strategy_config.side_effect = [row, running_row]
        mock_sqlite.update_strategy_fields.return_value = None
        resp = client.post("/api/strategies/test123/start")
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

        mock_sqlite.get_strategy_config.side_effect = [running_row, stopped_row]
        resp = client.post("/api/strategies/test123/stop")
        assert resp.status_code == 200
        assert resp.json()["status"] == "stopped"

    def test_start_not_found(self, _mock_stores):
        mock_sqlite, _ = _mock_stores
        mock_sqlite.get_strategy_config.return_value = None
        resp = client.post("/api/strategies/nonexistent/start")
        assert resp.status_code == 404

    def test_stop_not_found(self, _mock_stores):
        mock_sqlite, _ = _mock_stores
        mock_sqlite.get_strategy_config.return_value = None
        resp = client.post("/api/strategies/nonexistent/stop")
        assert resp.status_code == 404


# --------------- Backtest ---------------

class TestBacktest:
    def test_run_no_data(self, _mock_stores):
        mock_sqlite, mock_duckdb = _mock_stores
        import pandas as pd
        mock_duckdb.query_bars.return_value = pd.DataFrame()
        mock_sqlite.get_strategy_config.return_value = None
        mock_sqlite.save_backtest_result.return_value = None

        resp = client.post("/api/backtest/run", json={
            "strategy_id": "test-strat",
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": "2024-12-31T00:00:00Z",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["strategy_id"] == "test-strat"
        assert data["status"] == "completed"
        assert "metrics" in data

    def test_list_results(self, _mock_stores):
        mock_sqlite, _ = _mock_stores
        now = datetime.now(timezone.utc).isoformat()
        mock_sqlite.list_backtest_results.return_value = [{
            "id": "bt1",
            "strategy_id": "s1",
            "status": "completed",
            "metrics": {"sharpe_ratio": 1.0, "sortino_ratio": 1.5, "max_drawdown": -0.1,
                        "win_rate": 0.5, "profit_factor": 1.2, "annual_return": 0.15, "total_return": 0.3},
            "created_at": now,
        }]
        resp = client.get("/api/backtest/results")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_result(self, _mock_stores):
        mock_sqlite, _ = _mock_stores
        now = datetime.now(timezone.utc).isoformat()
        mock_sqlite.get_backtest_result.return_value = {
            "id": "bt1",
            "strategy_id": "s1",
            "status": "completed",
            "metrics": {"sharpe_ratio": 1.0, "sortino_ratio": 1.5, "max_drawdown": -0.1,
                        "win_rate": 0.5, "profit_factor": 1.2, "annual_return": 0.15, "total_return": 0.3},
            "equity_curve": [100000, 102000, 105000],
            "created_at": now,
        }
        resp = client.get("/api/backtest/results/bt1")
        assert resp.status_code == 200
        assert resp.json()["id"] == "bt1"

    def test_get_result_not_found(self, _mock_stores):
        mock_sqlite, _ = _mock_stores
        mock_sqlite.get_backtest_result.return_value = None
        resp = client.get("/api/backtest/results/nonexistent")
        assert resp.status_code == 404


# --------------- Optimize ---------------

class TestOptimize:
    def _make_price_df(self):
        import numpy as np
        import pandas as pd
        dates = pd.date_range("2025-01-01", periods=120, freq="D")
        np.random.seed(42)
        prices = 50000 + np.cumsum(np.random.randn(120) * 500)
        return pd.DataFrame(
            {
                "open": prices - 100,
                "high": prices + 200,
                "low": prices - 200,
                "close": prices,
                "volume": np.random.randint(100, 1000, 120).astype(float),
                "symbol": "BTC/USDT",
            },
            index=dates,
        )

    def test_optimize_success(self, _mock_stores):
        mock_sqlite, mock_duckdb = _mock_stores
        mock_duckdb.query_bars.return_value = self._make_price_df()
        mock_sqlite.get_strategy_config.return_value = None

        resp = client.post("/api/backtest/optimize", json={
            "strategy_id": "sma_crossover",
            "param_grid": {
                "short_window": [5, 10],
                "long_window": [20, 30],
            },
            "start_date": "2025-01-01T00:00:00Z",
            "end_date": "2025-04-30T00:00:00Z",
            "initial_capital": 100000,
            "market": "crypto",
            "symbols": ["BTC/USDT"],
            "metric": "sharpe_ratio",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_combinations"] == 4
        assert len(data["results"]) == 4
        assert data["results"][0]["rank"] == 1
        assert "best_parameters" in data
        assert "short_window" in data["best_parameters"]
        assert "long_window" in data["best_parameters"]
        # Results should be sorted by rank
        ranks = [r["rank"] for r in data["results"]]
        assert ranks == [1, 2, 3, 4]
        # Each result should have full metrics
        for r in data["results"]:
            assert "sharpe_ratio" in r["metrics"]
            assert "total_return" in r["metrics"]

    def test_optimize_no_data(self, _mock_stores):
        mock_sqlite, mock_duckdb = _mock_stores
        import pandas as pd
        mock_duckdb.query_bars.return_value = pd.DataFrame()
        mock_sqlite.get_strategy_config.return_value = None

        resp = client.post("/api/backtest/optimize", json={
            "strategy_id": "sma_crossover",
            "param_grid": {"short_window": [5, 10], "long_window": [20, 30]},
            "start_date": "2025-01-01T00:00:00Z",
            "end_date": "2025-04-30T00:00:00Z",
        })
        assert resp.status_code == 400
        assert "No historical data" in resp.json()["detail"]

    def test_optimize_invalid_strategy(self, _mock_stores):
        mock_sqlite, mock_duckdb = _mock_stores
        mock_duckdb.query_bars.return_value = self._make_price_df()
        mock_sqlite.get_strategy_config.return_value = None

        resp = client.post("/api/backtest/optimize", json={
            "strategy_id": "nonexistent_strategy",
            "param_grid": {"short_window": [5]},
            "start_date": "2025-01-01T00:00:00Z",
            "end_date": "2025-04-30T00:00:00Z",
        })
        assert resp.status_code == 400
        assert "not registered" in resp.json()["detail"]

    def test_optimize_single_combination(self, _mock_stores):
        mock_sqlite, mock_duckdb = _mock_stores
        mock_duckdb.query_bars.return_value = self._make_price_df()
        mock_sqlite.get_strategy_config.return_value = None

        resp = client.post("/api/backtest/optimize", json={
            "strategy_id": "sma_crossover",
            "param_grid": {"short_window": [10], "long_window": [30]},
            "start_date": "2025-01-01T00:00:00Z",
            "end_date": "2025-04-30T00:00:00Z",
            "metric": "total_return",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_combinations"] == 1
        assert len(data["results"]) == 1
        assert data["best_parameters"] == {"short_window": 10, "long_window": 30}


# --------------- Portfolio ---------------

class TestPortfolio:
    def test_summary(self):
        resp = client.get("/api/portfolio/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_value" in data
        assert "cash" in data
        assert "positions" in data

    def test_positions_empty(self, _mock_stores):
        mock_sqlite, _ = _mock_stores
        cursor_mock = AsyncMock()
        cursor_mock.fetchall.return_value = []
        mock_sqlite.db.execute.return_value = cursor_mock
        resp = client.get("/api/portfolio/positions")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_trades_empty(self, _mock_stores):
        mock_sqlite, _ = _mock_stores
        mock_sqlite.list_trades.return_value = []
        resp = client.get("/api/portfolio/trades")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_trades_with_data(self, _mock_stores):
        mock_sqlite, _ = _mock_stores
        now = datetime.now(timezone.utc).isoformat()
        mock_sqlite.list_trades.return_value = [
            {
                "id": "TXN-001", "strategy_id": "sma", "symbol": "BTC/USDT",
                "side": "buy", "price": 30000.0, "filled_price": 30000.0,
                "quantity": 0.5, "commission": 15.0, "pnl": 0.0,
                "created_at": now,
            },
        ]
        resp = client.get("/api/portfolio/trades")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_performance_empty(self, _mock_stores):
        mock_sqlite, _ = _mock_stores
        mock_sqlite.list_backtest_results.return_value = []
        mock_sqlite.list_trades.return_value = []
        cursor_mock = AsyncMock()
        cursor_mock.fetchone.return_value = (0,)
        mock_sqlite.db.execute.return_value = cursor_mock
        resp = client.get("/api/portfolio/performance")
        assert resp.status_code == 200
        data = resp.json()
        assert "sharpe_ratio" in data
        assert "max_drawdown" in data
        assert "total_trades" in data


# --------------- Market Data ---------------

class TestMarketData:
    def test_bars_empty(self, _mock_stores):
        _, mock_duckdb = _mock_stores
        import pandas as pd
        mock_duckdb.query_bars.return_value = pd.DataFrame()
        resp = client.get("/api/market-data/bars?symbol=BTC/USDT")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_bars_with_data(self, _mock_stores):
        _, mock_duckdb = _mock_stores
        import pandas as pd
        df = pd.DataFrame({
            "symbol": ["BTC/USDT"],
            "market": ["crypto"],
            "timeframe": ["1d"],
            "open": [30000.0],
            "high": [31000.0],
            "low": [29500.0],
            "close": [30500.0],
            "volume": [1500.0],
        }, index=pd.to_datetime(["2024-01-01"]))
        df.index.name = "ts"
        mock_duckdb.query_bars.return_value = df
        resp = client.get("/api/market-data/bars?symbol=BTC/USDT")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["symbol"] == "BTC/USDT"

    def test_bars_with_params(self, _mock_stores):
        _, mock_duckdb = _mock_stores
        import pandas as pd
        mock_duckdb.query_bars.return_value = pd.DataFrame()
        resp = client.get("/api/market-data/bars?symbol=ETH/USDT&market=crypto&timeframe=1h&limit=10")
        assert resp.status_code == 200

    def test_latest_no_data(self, _mock_stores):
        _, mock_duckdb = _mock_stores
        import pandas as pd
        mock_duckdb.query_bars.return_value = pd.DataFrame()
        resp = client.get("/api/market-data/latest?symbols=BTC/USDT,ETH/USDT")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        symbols = {q["symbol"] for q in data}
        assert symbols == {"BTC/USDT", "ETH/USDT"}

    def test_symbols_empty(self, _mock_stores):
        _, mock_duckdb = _mock_stores
        result_mock = MagicMock()
        result_mock.fetchall.return_value = []
        mock_duckdb.execute.return_value = result_mock
        resp = client.get("/api/market-data/symbols")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_symbols_with_data(self, _mock_stores):
        _, mock_duckdb = _mock_stores
        result_mock = MagicMock()
        result_mock.fetchall.return_value = [("BTC/USDT", "crypto"), ("ETH/USDT", "crypto")]
        mock_duckdb.execute.return_value = result_mock
        resp = client.get("/api/market-data/symbols?market=crypto")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert all("symbol" in s for s in data)


# --------------- WebSocket ---------------

class TestWebSocket:
    def test_subscribe_action(self):
        """New action-based subscribe format."""
        with client.websocket_connect("/api/ws/stream") as ws:
            ws.send_text('{"action": "subscribe", "channel": "market:BTC/USDT:1m"}')
            data = ws.receive_json()
            assert data["status"] == "subscribed"
            assert data["channel"] == "market:BTC/USDT:1m"

    def test_unsubscribe_action(self):
        """New action-based unsubscribe format."""
        with client.websocket_connect("/api/ws/stream") as ws:
            ws.send_text('{"action": "subscribe", "channel": "market:BTC/USDT:1m"}')
            ws.receive_json()
            ws.send_text('{"action": "unsubscribe", "channel": "market:BTC/USDT:1m"}')
            data = ws.receive_json()
            assert data["status"] == "unsubscribed"

    def test_subscribe_legacy(self):
        """Backward-compatible legacy subscribe format."""
        with client.websocket_connect("/api/ws/stream") as ws:
            ws.send_text('{"subscribe": "market:BTC/USDT:1m"}')
            data = ws.receive_json()
            assert data["status"] == "subscribed"
            assert data["channel"] == "market:BTC/USDT:1m"

    def test_unsubscribe_legacy(self):
        """Backward-compatible legacy unsubscribe format."""
        with client.websocket_connect("/api/ws/stream") as ws:
            ws.send_text('{"subscribe": "market:BTC/USDT:1m"}')
            ws.receive_json()
            ws.send_text('{"unsubscribe": "market:BTC/USDT:1m"}')
            data = ws.receive_json()
            assert data["status"] == "unsubscribed"

    def test_subscribe_signals_channel(self):
        with client.websocket_connect("/api/ws/stream") as ws:
            ws.send_text('{"action": "subscribe", "channel": "signals:my-strategy"}')
            data = ws.receive_json()
            assert data["status"] == "subscribed"
            assert data["channel"] == "signals:my-strategy"

    def test_subscribe_portfolio_channel(self):
        with client.websocket_connect("/api/ws/stream") as ws:
            ws.send_text('{"action": "subscribe", "channel": "portfolio"}')
            data = ws.receive_json()
            assert data["status"] == "subscribed"
            assert data["channel"] == "portfolio"

    def test_subscribe_invalid_channel(self):
        with client.websocket_connect("/api/ws/stream") as ws:
            ws.send_text('{"action": "subscribe", "channel": "invalid:too:many:parts"}')
            data = ws.receive_json()
            assert "error" in data

    def test_invalid_json(self):
        with client.websocket_connect("/api/ws/stream") as ws:
            ws.send_text("not json")
            data = ws.receive_json()
            assert "error" in data

    def test_unknown_command(self):
        with client.websocket_connect("/api/ws/stream") as ws:
            ws.send_text('{"foo": "bar"}')
            data = ws.receive_json()
            assert "error" in data
