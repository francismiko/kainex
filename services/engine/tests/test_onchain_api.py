from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from engine.api.main import app
from engine.storage.duckdb_store import DuckDBStore
from engine.storage.sqlite_store import SQLiteStore
from engine.strategies.registry import registry as strategy_registry


@pytest.fixture(autouse=True)
def _mock_stores():
    mock_sqlite = AsyncMock(spec=SQLiteStore)
    mock_sqlite.db = AsyncMock()
    mock_duckdb = MagicMock(spec=DuckDBStore)

    app.state.sqlite_store = mock_sqlite
    app.state.duckdb_store = mock_duckdb
    app.state.strategy_registry = strategy_registry

    yield mock_sqlite, mock_duckdb


client = TestClient(app, raise_server_exceptions=False)


class TestOnChainEndpoint:
    def test_get_onchain_metrics_empty(self, _mock_stores) -> None:
        _, mock_duckdb = _mock_stores
        mock_duckdb.query_onchain_metrics.return_value = pd.DataFrame()

        resp = client.get("/api/market-data/onchain")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_onchain_metrics_with_data(self, _mock_stores) -> None:
        _, mock_duckdb = _mock_stores
        df = pd.DataFrame(
            [
                {
                    "metric_name": "fear_greed_index",
                    "asset": "BTC",
                    "value": 25.0,
                    "source": "alternative_me",
                    "ts": datetime(2026, 1, 15, 12, 0, 0),
                },
                {
                    "metric_name": "stablecoin_supply",
                    "asset": "ALL",
                    "value": 170e9,
                    "source": "defillama",
                    "ts": datetime(2026, 1, 15, 12, 0, 0),
                },
            ]
        )
        mock_duckdb.query_onchain_metrics.return_value = df

        resp = client.get("/api/market-data/onchain")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["metric_name"] == "fear_greed_index"
        assert data[0]["value"] == 25.0
        assert data[1]["metric_name"] == "stablecoin_supply"

    def test_get_onchain_metrics_with_filters(self, _mock_stores) -> None:
        _, mock_duckdb = _mock_stores
        df = pd.DataFrame(
            [
                {
                    "metric_name": "fear_greed_index",
                    "asset": "BTC",
                    "value": 25.0,
                    "source": "alternative_me",
                    "ts": datetime(2026, 1, 15, 12, 0, 0),
                },
            ]
        )
        mock_duckdb.query_onchain_metrics.return_value = df

        resp = client.get(
            "/api/market-data/onchain",
            params={"metric": "fear_greed_index", "asset": "BTC", "limit": 10},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1

        mock_duckdb.query_onchain_metrics.assert_called_once_with(
            metric_name="fear_greed_index", asset="BTC", limit=10
        )
