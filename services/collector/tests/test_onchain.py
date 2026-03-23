import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from collector.models.onchain import OnChainMetric
from collector.sources.onchain.blockchain_info import BlockchainInfoSource
from collector.sources.onchain.defillama import DefiLlamaSource
from collector.sources.onchain.fear_greed import FearGreedSource
from collector.storage.duckdb_writer import DuckDBWriter


# ── Helpers ──────────────────────────────────────────────────


def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.side_effect = None if status_code == 200 else Exception("HTTP error")
    return resp


def _mock_client(*responses) -> AsyncMock:
    """Create an AsyncMock httpx client that returns responses in order."""
    client = AsyncMock()
    client.get = AsyncMock(side_effect=list(responses))
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


# ── DefiLlama source tests ──────────────────────────────────


DEFILLAMA_STABLECOINS_RESPONSE = {
    "peggedAssets": [
        {
            "name": "USDT",
            "chainCirculating": {
                "Ethereum": {"current": {"peggedUSD": 80_000_000_000}},
                "Tron": {"current": {"peggedUSD": 60_000_000_000}},
            },
        },
        {
            "name": "USDC",
            "chainCirculating": {
                "Ethereum": {"current": {"peggedUSD": 30_000_000_000}},
            },
        },
    ]
}

DEFILLAMA_CHART_RESPONSE = [
    {"date": str(1700000000 + i * 86400), "totalCirculating": {"peggedUSD": 160e9 + i * 1e9}}
    for i in range(10)
]


class TestDefiLlamaSource:
    @pytest.mark.asyncio
    async def test_fetch_metrics(self) -> None:
        client = _mock_client(
            _mock_response(DEFILLAMA_STABLECOINS_RESPONSE),
            _mock_response(DEFILLAMA_CHART_RESPONSE),
        )

        with patch("collector.sources.onchain.defillama.httpx.AsyncClient", return_value=client):
            source = DefiLlamaSource()
            metrics = await source.fetch_metrics()

        names = [m.metric_name for m in metrics]
        assert "stablecoin_supply" in names
        assert "stablecoin_supply_weekly_change_pct" in names

        supply = next(m for m in metrics if m.metric_name == "stablecoin_supply")
        assert supply.value == 170_000_000_000  # 80B + 60B + 30B
        assert supply.asset == "ALL"
        assert supply.source == "defillama"


# ── Fear & Greed source tests ───────────────────────────────


FNG_RESPONSE = {
    "data": [
        {"value": "25", "value_classification": "Extreme Fear", "timestamp": "1700000000"},
    ]
}


class TestFearGreedSource:
    @pytest.mark.asyncio
    async def test_fetch_metrics(self) -> None:
        client = _mock_client(_mock_response(FNG_RESPONSE))

        with patch("collector.sources.onchain.fear_greed.httpx.AsyncClient", return_value=client):
            source = FearGreedSource()
            metrics = await source.fetch_metrics(limit=1)

        assert len(metrics) == 1
        assert metrics[0].metric_name == "fear_greed_index"
        assert metrics[0].value == 25.0
        assert metrics[0].asset == "BTC"
        assert metrics[0].source == "alternative_me"


# ── Blockchain.info source tests ────────────────────────────


BLOCKCHAIN_RESPONSE = {
    "values": [
        {"x": 1700000000, "y": 500000},
        {"x": 1700086400, "y": 521000},
    ]
}


class TestBlockchainInfoSource:
    @pytest.mark.asyncio
    async def test_fetch_metrics(self) -> None:
        client = _mock_client(
            _mock_response(BLOCKCHAIN_RESPONSE),
            _mock_response(BLOCKCHAIN_RESPONSE),
            _mock_response(BLOCKCHAIN_RESPONSE),
        )

        with patch("collector.sources.onchain.blockchain_info.httpx.AsyncClient", return_value=client):
            source = BlockchainInfoSource()
            metrics = await source.fetch_metrics()

        names = [m.metric_name for m in metrics]
        assert "btc_active_addresses" in names
        assert "btc_transaction_count" in names
        assert "btc_hash_rate" in names

        addr = next(m for m in metrics if m.metric_name == "btc_active_addresses")
        assert addr.value == 521000.0
        assert addr.asset == "BTC"


# ── DuckDB storage tests ────────────────────────────────────


class TestOnChainStorage:
    def _make_writer(self, tmp_dir: str) -> DuckDBWriter:
        db_path = os.path.join(tmp_dir, "test.duckdb")
        writer = DuckDBWriter(db_path=db_path)
        writer._parquet_dir = os.path.join(tmp_dir, "parquet")
        writer.connect()
        return writer

    def test_write_and_query_onchain_metric(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            writer = self._make_writer(tmp)
            try:
                metric = OnChainMetric(
                    metric_name="fear_greed_index",
                    asset="BTC",
                    value=25.0,
                    source="alternative_me",
                    timestamp=datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
                )
                writer.write_onchain_metric(metric)

                results = writer.query_onchain_metrics(metric_name="fear_greed_index")
                assert len(results) == 1
                assert results[0]["metric_name"] == "fear_greed_index"
                assert results[0]["value"] == 25.0
            finally:
                writer.close()

    def test_write_batch_onchain_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            writer = self._make_writer(tmp)
            try:
                metrics = [
                    OnChainMetric(
                        metric_name="stablecoin_supply",
                        asset="ALL",
                        value=170e9,
                        source="defillama",
                        timestamp=datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
                    ),
                    OnChainMetric(
                        metric_name="fear_greed_index",
                        asset="BTC",
                        value=25.0,
                        source="alternative_me",
                        timestamp=datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
                    ),
                ]
                writer.write_onchain_metrics(metrics)

                all_results = writer.query_onchain_metrics()
                assert len(all_results) == 2

                btc_only = writer.query_onchain_metrics(asset="BTC")
                assert len(btc_only) == 1
                assert btc_only[0]["metric_name"] == "fear_greed_index"
            finally:
                writer.close()

    def test_duplicate_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            writer = self._make_writer(tmp)
            try:
                metric = OnChainMetric(
                    metric_name="fear_greed_index",
                    asset="BTC",
                    value=25.0,
                    source="alternative_me",
                    timestamp=datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
                )
                writer.write_onchain_metric(metric)
                writer.write_onchain_metric(metric)

                results = writer.query_onchain_metrics()
                assert len(results) == 1
            finally:
                writer.close()
