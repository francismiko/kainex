from agent.prompt_builder import PromptBuilder


def _sample_market() -> dict:
    return {
        "symbol": "BTC/USDT",
        "available": True,
        "bars": 200,
        "last_price": 65000.0,
        "prev_close": 64000.0,
        "change_pct": 1.5625,
        "high_24h": 66000.0,
        "low_24h": 63500.0,
        "volume": 12345.67,
        "sma_20": 63000.0,
        "sma_50": 60000.0,
        "rsi_14": 58.5,
        "macd": 120.5,
        "macd_signal": 100.3,
        "macd_histogram": 20.2,
        "price_vs_sma20": "above",
        "price_vs_sma50": "above",
    }


def _sample_portfolio() -> dict:
    return {
        "total_value": 105000.0,
        "cash": 50000.0,
        "total_pnl": 5000.0,
        "positions": [
            {
                "symbol": "BTC/USDT",
                "quantity": 0.5,
                "entry_price": 60000.0,
                "current_price": 65000.0,
                "unrealized_pnl": 2500.0,
            }
        ],
    }


def _risk_constraints() -> dict:
    return {
        "max_position_pct": 0.8,
        "stop_loss_pct": 0.05,
        "initial_capital": 100000.0,
    }


class TestPromptBuilder:
    def test_build_contains_persona(self):
        builder = PromptBuilder()
        prompt = builder.build("balanced", _sample_market(), _sample_portfolio(), _risk_constraints())
        assert "均衡" in prompt

    def test_build_contains_market_data(self):
        builder = PromptBuilder()
        prompt = builder.build("balanced", _sample_market(), _sample_portfolio(), _risk_constraints())
        assert "BTC/USDT" in prompt
        assert "65000" in prompt
        assert "SMA(20)" in prompt
        assert "RSI(14)" in prompt

    def test_build_contains_portfolio(self):
        builder = PromptBuilder()
        prompt = builder.build("balanced", _sample_market(), _sample_portfolio(), _risk_constraints())
        assert "105000" in prompt
        assert "50000" in prompt

    def test_build_contains_risk_constraints(self):
        builder = PromptBuilder()
        prompt = builder.build("balanced", _sample_market(), _sample_portfolio(), _risk_constraints())
        assert "80%" in prompt
        assert "5%" in prompt

    def test_build_contains_json_format_instructions(self):
        builder = PromptBuilder()
        prompt = builder.build("balanced", _sample_market(), _sample_portfolio(), _risk_constraints())
        assert '"action"' in prompt
        assert '"decisions"' in prompt
        assert '"overall_sentiment"' in prompt

    def test_all_personas_work(self):
        builder = PromptBuilder()
        for persona in ("conservative", "balanced", "aggressive"):
            prompt = builder.build(persona, _sample_market(), _sample_portfolio(), _risk_constraints())
            assert len(prompt) > 100

    def test_unavailable_market(self):
        builder = PromptBuilder()
        market = {"symbol": "XYZ/USDT", "available": False, "bars": 0}
        prompt = builder.build("balanced", market, _sample_portfolio(), _risk_constraints())
        assert "数据不可用" in prompt

    def test_empty_positions(self):
        builder = PromptBuilder()
        portfolio = {"total_value": 100000, "cash": 100000, "total_pnl": 0, "positions": []}
        prompt = builder.build("balanced", _sample_market(), portfolio, _risk_constraints())
        assert "空仓" in prompt
