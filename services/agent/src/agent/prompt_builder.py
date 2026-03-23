from __future__ import annotations

import json


class PromptBuilder:
    """Constructs structured prompts for the LLM trading analyst."""

    PERSONAS: dict[str, str] = {
        "conservative": (
            "你是一个保守的量化交易员。你偏好低频交易、高胜率、严格止损。"
            "你更倾向于等待明确的趋势信号再入场，宁可错过机会也不冒险。"
            "仓位管理极为保守，单次交易不超过总资金的 10%。"
        ),
        "balanced": (
            "你是一个均衡的量化交易员。你综合技术面和趋势分析做出决策。"
            "你既关注短期波动，也尊重中长期趋势。"
            "仓位管理适中，单次交易不超过总资金的 20%。"
        ),
        "aggressive": (
            "你是一个激进的量化交易员。你善于捕捉短期趋势和波动带来的机会。"
            "你愿意承担更高风险来换取更高收益，但依然遵守止损纪律。"
            "仓位管理激进，单次交易可达总资金的 30%。"
        ),
    }

    def build(
        self,
        persona: str,
        market_summary: dict,
        portfolio: dict,
        risk_constraints: dict,
    ) -> str:
        persona_desc = self.PERSONAS.get(persona, self.PERSONAS["balanced"])

        return f"""{persona_desc}

## 当前市场状态
{self._format_market(market_summary)}

## 当前持仓
{self._format_portfolio(portfolio)}

## 风控约束
{self._format_risk(risk_constraints)}

## 请分析当前市场并给出交易决策

返回严格 JSON 格式（不要包含任何 markdown）：
{{
    "analysis": "对当前市场的分析...",
    "decisions": [
        {{
            "action": "buy" | "sell" | "hold",
            "symbol": "BTC/USDT",
            "quantity": 0.1,
            "reason": "理由...",
            "confidence": 0.85,
            "stop_loss": 60000,
            "take_profit": 70000
        }}
    ],
    "overall_sentiment": "bullish" | "bearish" | "neutral"
}}

规则：
1. decisions 数组中每个 symbol 最多出现一次。
2. action 只能是 "buy"、"sell" 或 "hold"。
3. confidence 范围 0-1，低于 0.6 时应选择 hold。
4. 必须设置 stop_loss 和 take_profit。
5. quantity 必须是正数，且不能超过风控约束。
6. 如果市场数据不可用，选择 hold。
"""

    @staticmethod
    def _format_market(summary: dict) -> str:
        if not summary.get("available", False):
            return f"- {summary.get('symbol', '?')}: 数据不可用"

        lines = [
            f"- 交易对: {summary['symbol']}",
            f"- 最新价: {summary['last_price']:.2f}",
            f"- 前收价: {summary['prev_close']:.2f}",
            f"- 涨跌幅: {summary['change_pct']:+.2f}%",
            f"- 24h 高/低: {summary['high_24h']:.2f} / {summary['low_24h']:.2f}",
            f"- 成交量: {summary['volume']:.2f}",
            f"- SMA(20): {_fmt(summary.get('sma_20'))}",
            f"- SMA(50): {_fmt(summary.get('sma_50'))}",
            f"- RSI(14): {_fmt(summary.get('rsi_14'))}",
            f"- MACD: {_fmt(summary.get('macd'))} / Signal: {_fmt(summary.get('macd_signal'))}",
            f"- 价格 vs SMA20: {summary.get('price_vs_sma20', '?')}",
            f"- 价格 vs SMA50: {summary.get('price_vs_sma50', '?')}",
        ]
        return "\n".join(lines)

    @staticmethod
    def _format_portfolio(portfolio: dict) -> str:
        lines = [
            f"- 总资产: {portfolio.get('total_value', 0):.2f}",
            f"- 可用现金: {portfolio.get('cash', 0):.2f}",
            f"- 总盈亏: {portfolio.get('total_pnl', 0):.2f}",
        ]
        positions = portfolio.get("positions", [])
        if positions:
            lines.append("- 持仓:")
            for p in positions:
                sym = p.get("symbol", "?")
                qty = p.get("quantity", 0)
                entry = p.get("entry_price", 0)
                cur = p.get("current_price", 0)
                pnl = p.get("unrealized_pnl", 0)
                lines.append(f"  - {sym}: 数量={qty}, 成本={entry:.2f}, 现价={cur:.2f}, 浮盈={pnl:.2f}")
        else:
            lines.append("- 持仓: 空仓")
        return "\n".join(lines)

    @staticmethod
    def _format_risk(constraints: dict) -> str:
        lines = [
            f"- 最大仓位比例: {constraints.get('max_position_pct', 0.8) * 100:.0f}%",
            f"- 止损比例: {constraints.get('stop_loss_pct', 0.05) * 100:.0f}%",
            f"- 初始资金: {constraints.get('initial_capital', 100000):.2f}",
        ]
        return "\n".join(lines)


def _fmt(val: float | None) -> str:
    if val is None:
        return "N/A"
    return f"{val:.4f}"
