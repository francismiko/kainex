"""Tests for SentimentAnalyzer — mock LLM responses to test analysis logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from agent.sentiment.analyzer import SentimentAnalyzer, SentimentResult, _neutral_result
from agent.sentiment.news_fetcher import NewsItem


def _sample_news() -> list[NewsItem]:
    return [
        NewsItem(
            title="Bitcoin surges past $70k",
            summary="Institutional demand drives BTC to new highs.",
            source="CryptoCompare",
            url="https://example.com/btc",
            published_at="2026-03-23T10:00:00Z",
            symbols=["BTC"],
        ),
        NewsItem(
            title="Fed signals rate cut",
            summary="Federal Reserve hints at rate cuts in next meeting.",
            source="Finnhub",
            url="https://example.com/fed",
            published_at="2026-03-23T09:00:00Z",
            symbols=[],
        ),
    ]


LLM_SENTIMENT_RESPONSE = {
    "overall_sentiment": "bullish",
    "confidence": 0.85,
    "key_events": [
        {"event": "BTC surges past $70k", "impact": "positive", "symbols": ["BTC"]},
        {"event": "Fed signals rate cut", "impact": "positive", "symbols": []},
    ],
    "risk_factors": ["Overheating market", "Regulatory uncertainty"],
    "summary": "Market sentiment is bullish driven by BTC rally and dovish Fed.",
}


class TestSentimentAnalyzer:
    @pytest.fixture
    def mock_llm(self):
        llm = AsyncMock()
        llm.analyze = AsyncMock(return_value=LLM_SENTIMENT_RESPONSE)
        return llm

    async def test_analyze_returns_structured_result(self, mock_llm):
        analyzer = SentimentAnalyzer(llm_client=mock_llm)
        result = await analyzer.analyze(_sample_news())

        assert result.overall_sentiment == "bullish"
        assert result.confidence == 0.85
        assert len(result.key_events) == 2
        assert len(result.risk_factors) == 2
        assert "bullish" in result.summary.lower()
        assert result.news_count == 2
        assert result.analyzed_at != ""

    async def test_analyze_empty_news_returns_neutral(self, mock_llm):
        analyzer = SentimentAnalyzer(llm_client=mock_llm)
        result = await analyzer.analyze([])

        assert result.overall_sentiment == "neutral"
        assert result.confidence == 0.0
        assert result.news_count == 0
        # LLM should not be called
        mock_llm.analyze.assert_not_called()

    async def test_analyze_llm_failure_returns_neutral(self):
        llm = AsyncMock()
        llm.analyze = AsyncMock(side_effect=Exception("LLM timeout"))
        analyzer = SentimentAnalyzer(llm_client=llm)
        result = await analyzer.analyze(_sample_news())

        assert result.overall_sentiment == "neutral"
        assert result.confidence == 0.0
        assert result.news_count == 2

    async def test_analyze_formats_news_for_llm(self, mock_llm):
        analyzer = SentimentAnalyzer(llm_client=mock_llm)
        await analyzer.analyze(_sample_news())

        call_args = mock_llm.analyze.call_args
        prompt = call_args[0][0]
        assert "Bitcoin surges past $70k" in prompt
        assert "Fed signals rate cut" in prompt
        assert "[CryptoCompare]" in prompt

    async def test_analyze_handles_partial_llm_response(self):
        """LLM returns only some fields — defaults fill in."""
        llm = AsyncMock()
        llm.analyze = AsyncMock(return_value={
            "overall_sentiment": "bearish",
            # Missing confidence, key_events, risk_factors, summary
        })
        analyzer = SentimentAnalyzer(llm_client=llm)
        result = await analyzer.analyze(_sample_news())

        assert result.overall_sentiment == "bearish"
        assert result.confidence == 0.5  # default
        assert result.key_events == []
        assert result.risk_factors == []


class TestNeutralResult:
    def test_neutral_result(self):
        result = _neutral_result(news_count=5)
        assert result.overall_sentiment == "neutral"
        assert result.confidence == 0.0
        assert result.news_count == 5
        assert result.analyzed_at != ""
