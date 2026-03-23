"""Integration test: news fetch -> sentiment analysis -> journal persistence."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from agent.sentiment.analyzer import SentimentAnalyzer, SentimentResult
from agent.sentiment.news_fetcher import NewsFetcher
from agent.strategy_journal import StrategyJournal


def _mock_response(status_code: int = 200, *, json: object = None, text: str = "") -> httpx.Response:
    """Create a mock httpx.Response with a request attached."""
    if json is not None:
        import json as _json
        resp = httpx.Response(status_code, text=_json.dumps(json), request=httpx.Request("GET", "https://mock"))
        resp._content = _json.dumps(json).encode()  # noqa: SLF001
        resp.headers["content-type"] = "application/json"
        return resp
    return httpx.Response(status_code, text=text, request=httpx.Request("GET", "https://mock"))


CRYPTOCOMPARE_DATA = {
    "Data": [
        {
            "title": "Bitcoin rallies on ETF news",
            "body": "BTC spot ETF sees record inflows.",
            "url": "https://example.com/btc-etf",
            "published_on": "1711184400",
        },
    ]
}

LLM_RESPONSE = {
    "overall_sentiment": "bullish",
    "confidence": 0.9,
    "key_events": [
        {"event": "BTC ETF record inflows", "impact": "positive", "symbols": ["BTC"]}
    ],
    "risk_factors": ["Overvaluation risk"],
    "summary": "Strong bullish sentiment driven by ETF inflows.",
}


class TestSentimentIntegration:
    async def test_full_pipeline(self, tmp_path):
        """news fetch -> LLM analysis -> journal persistence."""
        # 1. Setup
        fetcher = NewsFetcher(finnhub_api_key="")
        mock_llm = AsyncMock()
        mock_llm.analyze = AsyncMock(return_value=LLM_RESPONSE)
        analyzer = SentimentAnalyzer(llm_client=mock_llm)

        journal = StrategyJournal(db_path=str(tmp_path / "test_journal.db"))
        version_id = journal.create_version(
            persona="balanced",
            model="test-model",
            parameters={"symbols": ["BTC/USDT"]},
            reasoning="test",
        )

        # 2. Fetch news (mocked HTTP)
        async def mock_get(url, **kwargs):
            if "cryptocompare" in url:
                return _mock_response(200, json=CRYPTOCOMPARE_DATA)
            return _mock_response(200, text="<rss><channel></channel></rss>")

        with patch.object(fetcher._http, "get", side_effect=mock_get):
            news_items = await fetcher.fetch_all(limit=10)

        assert len(news_items) >= 1
        assert news_items[0].title == "Bitcoin rallies on ETF news"

        # 3. Analyze sentiment
        sentiment = await analyzer.analyze(news_items)
        assert sentiment.overall_sentiment == "bullish"
        assert sentiment.confidence == 0.9

        # 4. Persist to journal
        journal.record_sentiment(version_id, sentiment)

        # 5. Verify persistence
        stored = journal.get_latest_sentiment(version_id)
        assert stored is not None
        assert stored["overall_sentiment"] == "bullish"
        assert stored["confidence"] == 0.9
        assert stored["news_count"] == 1
        assert len(stored["key_events"]) == 1
        assert stored["risk_factors"] == ["Overvaluation risk"]

        journal.close()

    async def test_sentiment_in_prompt(self):
        """Verify PromptBuilder includes sentiment section."""
        from agent.prompt_builder import PromptBuilder

        sentiment = SentimentResult(
            overall_sentiment="bearish",
            confidence=0.75,
            key_events=[{"event": "Market crash", "impact": "negative"}],
            risk_factors=["Liquidity crisis"],
            summary="Market sentiment is bearish.",
            news_count=5,
            analyzed_at="2026-03-23T10:00:00Z",
        )

        builder = PromptBuilder()
        prompt = builder.build(
            persona="balanced",
            market_summary={"symbol": "BTC/USDT", "available": False, "bars": 0},
            portfolio={"total_value": 100000, "cash": 100000, "total_pnl": 0, "positions": []},
            risk_constraints={"max_position_pct": 0.8, "stop_loss_pct": 0.05, "initial_capital": 100000},
            sentiment=sentiment,
        )

        assert "市场情绪" in prompt
        assert "bearish" in prompt
        assert "0.75" in prompt
        assert "Market crash" in prompt
        assert "Liquidity crisis" in prompt

    async def test_prompt_without_sentiment(self):
        """PromptBuilder works without sentiment (backward compatible)."""
        from agent.prompt_builder import PromptBuilder

        builder = PromptBuilder()
        prompt = builder.build(
            persona="balanced",
            market_summary={"symbol": "BTC/USDT", "available": False, "bars": 0},
            portfolio={"total_value": 100000, "cash": 100000, "total_pnl": 0, "positions": []},
            risk_constraints={"max_position_pct": 0.8, "stop_loss_pct": 0.05, "initial_capital": 100000},
        )

        assert "市场情绪" not in prompt
        assert "当前市场状态" in prompt

    async def test_journal_sentiment_without_version(self, tmp_path):
        """get_latest_sentiment() without version_id returns the latest."""
        journal = StrategyJournal(db_path=str(tmp_path / "test_journal.db"))
        v1 = journal.create_version("balanced", "test", {}, "v1")
        v2 = journal.create_version("balanced", "test", {}, "v2")

        s1 = SentimentResult(
            overall_sentiment="bullish", confidence=0.8, summary="v1 sentiment",
            news_count=3, analyzed_at="2026-03-23T08:00:00Z",
        )
        s2 = SentimentResult(
            overall_sentiment="bearish", confidence=0.6, summary="v2 sentiment",
            news_count=5, analyzed_at="2026-03-23T10:00:00Z",
        )

        journal.record_sentiment(v1, s1)
        journal.record_sentiment(v2, s2)

        latest = journal.get_latest_sentiment()
        assert latest is not None
        assert latest["overall_sentiment"] == "bearish"
        assert latest["version_id"] == v2

        v1_latest = journal.get_latest_sentiment(v1)
        assert v1_latest is not None
        assert v1_latest["overall_sentiment"] == "bullish"

        journal.close()
