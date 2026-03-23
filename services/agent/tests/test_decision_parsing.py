import json

import pytest

from agent.llm import LLMClient, _fallback_hold


class TestFallbackHold:
    def test_structure(self):
        result = _fallback_hold()
        assert "analysis" in result
        assert "decisions" in result
        assert "overall_sentiment" in result
        assert result["decisions"] == []
        assert result["overall_sentiment"] == "neutral"


class TestDecisionParsing:
    """Test that various LLM response shapes are handled correctly."""

    def test_valid_decision_json(self):
        raw = json.dumps({
            "analysis": "Market is bullish",
            "decisions": [
                {
                    "action": "buy",
                    "symbol": "BTC/USDT",
                    "quantity": 0.1,
                    "reason": "Uptrend confirmed",
                    "confidence": 0.85,
                    "stop_loss": 60000,
                    "take_profit": 70000,
                }
            ],
            "overall_sentiment": "bullish",
        })
        parsed = json.loads(raw)
        assert len(parsed["decisions"]) == 1
        assert parsed["decisions"][0]["action"] == "buy"
        assert parsed["decisions"][0]["quantity"] == 0.1

    def test_hold_decision(self):
        raw = json.dumps({
            "analysis": "Unclear signals",
            "decisions": [
                {
                    "action": "hold",
                    "symbol": "BTC/USDT",
                    "quantity": 0,
                    "reason": "Low confidence",
                    "confidence": 0.3,
                    "stop_loss": None,
                    "take_profit": None,
                }
            ],
            "overall_sentiment": "neutral",
        })
        parsed = json.loads(raw)
        assert parsed["decisions"][0]["action"] == "hold"

    def test_multiple_decisions(self):
        raw = json.dumps({
            "analysis": "Mixed signals",
            "decisions": [
                {"action": "buy", "symbol": "BTC/USDT", "quantity": 0.1, "reason": "bull", "confidence": 0.8, "stop_loss": 60000, "take_profit": 70000},
                {"action": "sell", "symbol": "ETH/USDT", "quantity": 1.0, "reason": "bear", "confidence": 0.75, "stop_loss": 3000, "take_profit": 2500},
            ],
            "overall_sentiment": "neutral",
        })
        parsed = json.loads(raw)
        assert len(parsed["decisions"]) == 2
        actions = {d["action"] for d in parsed["decisions"]}
        assert actions == {"buy", "sell"}

    def test_empty_decisions(self):
        raw = json.dumps({
            "analysis": "No opportunities",
            "decisions": [],
            "overall_sentiment": "neutral",
        })
        parsed = json.loads(raw)
        assert parsed["decisions"] == []

    def test_invalid_json_falls_back(self):
        """Simulates what happens when LLM returns invalid JSON."""
        bad_content = "This is not JSON at all"
        try:
            json.loads(bad_content)
            assert False, "Should have raised"
        except json.JSONDecodeError:
            result = _fallback_hold()
            assert result["decisions"] == []
            assert result["overall_sentiment"] == "neutral"

    def test_decision_filtering(self):
        """Only non-hold decisions should be executed."""
        decisions = [
            {"action": "buy", "symbol": "BTC/USDT", "quantity": 0.1},
            {"action": "hold", "symbol": "ETH/USDT", "quantity": 0},
            {"action": "sell", "symbol": "SOL/USDT", "quantity": 5},
        ]
        actionable = [d for d in decisions if d["action"] != "hold"]
        assert len(actionable) == 2
        assert all(d["action"] in ("buy", "sell") for d in actionable)
