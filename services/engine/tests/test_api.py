from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from engine.api.main import app
from engine.api.routes.strategies import _strategy_configs
from engine.api.routes.backtest import _backtest_results

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clear_stores():
    _strategy_configs.clear()
    _backtest_results.clear()
    yield
    _strategy_configs.clear()
    _backtest_results.clear()


# --------------- Health ---------------

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"


# --------------- Strategies ---------------

def _create_strategy(**overrides):
    payload = {
        "name": "My SMA",
        "class_name": "sma_crossover",
        "parameters": {"short_window": 5, "long_window": 20},
        "markets": ["crypto"],
        "timeframes": ["1d"],
    }
    payload.update(overrides)
    return client.post("/api/strategies/", json=payload)


class TestStrategies:
    def test_list_empty(self):
        resp = client.get("/api/strategies/")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create(self):
        resp = _create_strategy()
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My SMA"
        assert data["class_name"] == "sma_crossover"
        assert data["status"] == "stopped"
        assert "id" in data

    def test_create_invalid_class(self):
        resp = _create_strategy(class_name="nonexistent")
        assert resp.status_code == 400

    def test_list_after_create(self):
        _create_strategy()
        resp = client.get("/api/strategies/")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_detail(self):
        create_resp = _create_strategy()
        sid = create_resp.json()["id"]
        resp = client.get(f"/api/strategies/{sid}")
        assert resp.status_code == 200
        assert resp.json()["id"] == sid

    def test_get_not_found(self):
        resp = client.get("/api/strategies/nonexistent")
        assert resp.status_code == 404

    def test_update(self):
        create_resp = _create_strategy()
        sid = create_resp.json()["id"]
        resp = client.put(f"/api/strategies/{sid}", json={"parameters": {"short_window": 3}})
        assert resp.status_code == 200
        assert resp.json()["parameters"]["short_window"] == 3

    def test_update_not_found(self):
        resp = client.put("/api/strategies/nonexistent", json={"parameters": {}})
        assert resp.status_code == 404

    def test_start_stop(self):
        create_resp = _create_strategy()
        sid = create_resp.json()["id"]

        resp = client.post(f"/api/strategies/{sid}/start")
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

        resp = client.post(f"/api/strategies/{sid}/stop")
        assert resp.status_code == 200
        assert resp.json()["status"] == "stopped"

    def test_start_not_found(self):
        resp = client.post("/api/strategies/nonexistent/start")
        assert resp.status_code == 404

    def test_stop_not_found(self):
        resp = client.post("/api/strategies/nonexistent/stop")
        assert resp.status_code == 404


# --------------- Backtest ---------------

class TestBacktest:
    def test_run(self):
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
        assert len(data["equity_curve"]) > 0

    def test_list_results(self):
        client.post("/api/backtest/run", json={
            "strategy_id": "s1",
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": "2024-06-01T00:00:00Z",
        })
        resp = client.get("/api/backtest/results")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_result(self):
        run_resp = client.post("/api/backtest/run", json={
            "strategy_id": "s1",
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": "2024-06-01T00:00:00Z",
        })
        bid = run_resp.json()["id"]
        resp = client.get(f"/api/backtest/results/{bid}")
        assert resp.status_code == 200
        assert resp.json()["id"] == bid

    def test_get_result_not_found(self):
        resp = client.get("/api/backtest/results/nonexistent")
        assert resp.status_code == 404


# --------------- Portfolio ---------------

class TestPortfolio:
    def test_summary(self):
        resp = client.get("/api/portfolio/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_value" in data
        assert "cash" in data
        assert "positions" in data

    def test_positions(self):
        resp = client.get("/api/portfolio/positions")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_trades(self):
        resp = client.get("/api/portfolio/trades")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_trades_pagination(self):
        resp = client.get("/api/portfolio/trades?offset=1&limit=1")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_performance(self):
        resp = client.get("/api/portfolio/performance")
        assert resp.status_code == 200
        data = resp.json()
        assert "sharpe_ratio" in data
        assert "max_drawdown" in data
        assert "total_trades" in data


# --------------- Market Data ---------------

class TestMarketData:
    def test_bars(self):
        resp = client.get("/api/market-data/bars?symbol=BTC/USDT")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["symbol"] == "BTC/USDT"

    def test_bars_with_params(self):
        resp = client.get("/api/market-data/bars?symbol=ETH/USDT&market=crypto&timeframe=1h&limit=10")
        assert resp.status_code == 200

    def test_latest(self):
        resp = client.get("/api/market-data/latest?symbols=BTC/USDT,ETH/USDT")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        symbols = {q["symbol"] for q in data}
        assert symbols == {"BTC/USDT", "ETH/USDT"}

    def test_symbols(self):
        resp = client.get("/api/market-data/symbols")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert all("symbol" in s for s in data)

    def test_symbols_filter(self):
        resp = client.get("/api/market-data/symbols?market=crypto")
        assert resp.status_code == 200


# --------------- WebSocket ---------------

class TestWebSocket:
    def test_subscribe(self):
        with client.websocket_connect("/api/ws/stream") as ws:
            ws.send_text('{"subscribe": "market:BTC/USDT:1m"}')
            data = ws.receive_json()
            assert data["status"] == "subscribed"
            assert data["channel"] == "market:BTC/USDT:1m"

    def test_unsubscribe(self):
        with client.websocket_connect("/api/ws/stream") as ws:
            ws.send_text('{"subscribe": "market:BTC/USDT:1m"}')
            ws.receive_json()
            ws.send_text('{"unsubscribe": "market:BTC/USDT:1m"}')
            data = ws.receive_json()
            assert data["status"] == "unsubscribed"

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
