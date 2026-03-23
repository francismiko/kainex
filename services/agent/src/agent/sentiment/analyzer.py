"""LLM-based news sentiment analyzer."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from agent.llm import LLMClient
from agent.sentiment.news_fetcher import NewsItem

logger = logging.getLogger(__name__)


@dataclass
class SentimentResult:
    """Result of LLM sentiment analysis on a batch of news items."""

    overall_sentiment: str  # bullish / bearish / neutral
    confidence: float
    key_events: list[dict] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    summary: str = ""
    news_count: int = 0
    analyzed_at: str = ""


SENTIMENT_PROMPT_TEMPLATE = """你是一位专业的金融市场情绪分析师。请分析以下新闻标题和摘要，给出整体市场情绪判断。

## 新闻列表
{news_text}

请严格返回以下 JSON 格式（不要包含任何 markdown）：
{{
    "overall_sentiment": "bullish" 或 "bearish" 或 "neutral",
    "confidence": 0.0 到 1.0 之间的置信度,
    "key_events": [
        {{"event": "事件描述", "impact": "positive" 或 "negative" 或 "neutral", "symbols": ["BTC"]}}
    ],
    "risk_factors": ["风险因素1", "风险因素2"],
    "summary": "一句话市场情绪摘要"
}}

规则：
1. overall_sentiment 只能是 "bullish"、"bearish" 或 "neutral"。
2. confidence 反映你对判断的确信程度。
3. key_events 列出最重要的 3-5 个事件。
4. risk_factors 列出当前可能影响市场的风险。
5. summary 用一句话概括当前市场情绪。
"""


class SentimentAnalyzer:
    """Analyze news sentiment using LLM."""

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm = llm_client

    async def analyze(self, news_items: list[NewsItem]) -> SentimentResult:
        """Send news items to LLM and return structured sentiment analysis."""
        if not news_items:
            return _neutral_result(news_count=0)

        news_text = self._format_news(news_items)
        prompt = SENTIMENT_PROMPT_TEMPLATE.format(news_text=news_text)

        try:
            result = await self._llm.analyze(prompt)
            return SentimentResult(
                overall_sentiment=result.get("overall_sentiment", "neutral"),
                confidence=float(result.get("confidence", 0.5)),
                key_events=result.get("key_events", []),
                risk_factors=result.get("risk_factors", []),
                summary=result.get("summary", ""),
                news_count=len(news_items),
                analyzed_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as exc:
            logger.warning("Sentiment analysis failed, defaulting to neutral: %s", exc)
            return _neutral_result(news_count=len(news_items))

    @staticmethod
    def _format_news(items: list[NewsItem]) -> str:
        lines: list[str] = []
        for i, item in enumerate(items, 1):
            line = f"{i}. [{item.source}] {item.title}"
            if item.summary:
                line += f"\n   {item.summary}"
            lines.append(line)
        return "\n\n".join(lines)


def _neutral_result(news_count: int) -> SentimentResult:
    """Return a safe neutral sentiment when analysis fails or no news available."""
    return SentimentResult(
        overall_sentiment="neutral",
        confidence=0.0,
        key_events=[],
        risk_factors=[],
        summary="No news available or analysis failed.",
        news_count=news_count,
        analyzed_at=datetime.now(timezone.utc).isoformat(),
    )
