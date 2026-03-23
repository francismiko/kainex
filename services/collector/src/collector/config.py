from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "KAINEX_"}

    # Storage paths
    data_dir: str = "data"
    duckdb_path: str = "data/kainex.duckdb"
    sqlite_path: str = "data/kainex_state.db"
    parquet_dir: str = "data/parquet"

    # Finnhub API key (free tier)
    finnhub_api_key: str = ""

    # A-stock schedule (CST)
    astock_cron_start_hour: int = 9
    astock_cron_start_minute: int = 30
    astock_cron_end_hour: int = 15
    astock_cron_end_minute: int = 0
    astock_interval_minutes: int = 1

    # US-stock schedule (ET)
    us_stock_cron_start_hour: int = 9
    us_stock_cron_start_minute: int = 30
    us_stock_cron_end_hour: int = 16
    us_stock_cron_end_minute: int = 0
    us_stock_interval_minutes: int = 5

    # Crypto schedule (24/7)
    crypto_interval_minutes: int = 1

    # Default symbols to track
    astock_symbols: list[str] = ["000001", "600519"]
    us_stock_symbols: list[str] = ["AAPL", "MSFT"]
    crypto_symbols: list[str] = ["BTC/USDT", "ETH/USDT"]

    # Data source priority (fallback order)
    astock_sources: list[str] = ["akshare", "baostock"]
    us_stock_sources: list[str] = ["finnhub", "yfinance"]
    crypto_sources: list[str] = ["ccxt"]


settings = Settings()
