import pandas as pd
import pandas_ta as ta


class TechnicalIndicators:
    """Wrapper around pandas-ta for common technical indicators."""

    @staticmethod
    def sma(series: pd.Series, length: int = 20) -> pd.Series:
        return ta.sma(series, length=length)

    @staticmethod
    def ema(series: pd.Series, length: int = 20) -> pd.Series:
        return ta.ema(series, length=length)

    @staticmethod
    def rsi(series: pd.Series, length: int = 14) -> pd.Series:
        return ta.rsi(series, length=length)

    @staticmethod
    def macd(
        series: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> pd.DataFrame:
        return ta.macd(series, fast=fast, slow=slow, signal=signal)

    @staticmethod
    def bbands(
        series: pd.Series,
        length: int = 20,
        std: float = 2.0,
    ) -> pd.DataFrame:
        return ta.bbands(series, length=length, std=std)

    @staticmethod
    def atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        length: int = 14,
    ) -> pd.Series:
        return ta.atr(high=high, low=low, close=close, length=length)

    @staticmethod
    def stoch(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        k: int = 14,
        d: int = 3,
    ) -> pd.DataFrame:
        return ta.stoch(high=high, low=low, close=close, k=k, d=d)
