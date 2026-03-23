from __future__ import annotations

import logging

from agent.llm import LLMClient

logger = logging.getLogger(__name__)


class FeedbackAnalyzer:
    """Reviews recent trading performance and asks the LLM for improvement suggestions."""

    async def review_performance(
        self,
        llm: LLMClient,
        trades: list[dict],
        portfolio: dict,
    ) -> dict:
        """Let the LLM analyze recent trades and suggest adjustments.

        Returns a JSON dict with the LLM's analysis, or a fallback if
        there are no trades to review.
        """
        if not trades:
            return {
                "review": "No recent trades to review.",
                "good_decisions": [],
                "bad_decisions": [],
                "suggestions": [],
            }

        trades_text = _format_trades(trades)
        portfolio_text = _format_portfolio(portfolio)

        prompt = f"""你是一位量化交易顾问，负责回顾最近的交易表现并给出改进建议。

## 最近的交易记录
{trades_text}

## 当前组合表现
{portfolio_text}

请分析并返回严格 JSON 格式（不要包含 markdown）：
{{
    "review": "整体表现总结...",
    "good_decisions": [
        {{"trade": "描述", "reason": "为什么这是好的决策"}}
    ],
    "bad_decisions": [
        {{"trade": "描述", "reason": "为什么这是差的决策", "lesson": "教训"}}
    ],
    "suggestions": [
        "下一步应该调整的策略建议..."
    ]
}}
"""
        return await llm.analyze(prompt)


def _format_trades(trades: list[dict]) -> str:
    if not trades:
        return "无交易记录"
    lines = []
    for t in trades:
        side = t.get("side", "?")
        symbol = t.get("symbol", "?")
        price = t.get("price", 0)
        qty = t.get("quantity", 0)
        pnl = t.get("pnl", 0)
        ts = t.get("timestamp", "?")
        lines.append(f"- [{ts}] {side} {symbol} x{qty} @ {price}, PnL={pnl:.2f}")
    return "\n".join(lines)


def _format_portfolio(portfolio: dict) -> str:
    lines = [
        f"- 总资产: {portfolio.get('total_value', 0):.2f}",
        f"- 现金: {portfolio.get('cash', 0):.2f}",
        f"- 总盈亏: {portfolio.get('total_pnl', 0):.2f}",
    ]
    return "\n".join(lines)
