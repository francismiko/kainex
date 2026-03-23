from __future__ import annotations

from pydantic_settings import BaseSettings


class AgentSettings(BaseSettings):
    model_config = {"env_prefix": "KAINEX_AGENT_"}

    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    model: str = "anthropic/claude-sonnet-4"

    # Kainex Engine API
    engine_api_url: str = "http://localhost:8001"

    # Trading
    trading_interval_minutes: int = 60
    markets: list[str] = ["crypto"]
    symbols: list[str] = ["BTC/USDT", "ETH/USDT"]

    # Risk
    max_position_pct: float = 0.8
    stop_loss_pct: float = 0.05
    initial_capital: float = 100_000.0

    # Data
    duckdb_path: str = "../../data/kainex.duckdb"

    # Agent persona
    persona: str = "balanced"  # conservative, balanced, aggressive
