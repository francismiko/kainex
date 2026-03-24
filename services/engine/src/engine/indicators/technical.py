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

    # --- Tier 1: Must-have indicators ---

    @staticmethod
    def adx(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        length: int = 14,
    ) -> pd.DataFrame | None:
        """ADX + DI+ + DI-"""
        result = ta.adx(high, low, close, length=length)
        return result

    @staticmethod
    def vwap(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
    ) -> pd.Series | None:
        """Volume Weighted Average Price"""
        result = ta.vwap(high, low, close, volume)
        return result

    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series | None:
        """On Balance Volume"""
        result = ta.obv(close, volume)
        return result

    @staticmethod
    def willr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        length: int = 14,
    ) -> pd.Series | None:
        """Williams %R"""
        result = ta.willr(high, low, close, length=length)
        return result

    @staticmethod
    def cci(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        length: int = 20,
    ) -> pd.Series | None:
        """Commodity Channel Index"""
        result = ta.cci(high, low, close, length=length)
        return result

    @staticmethod
    def mfi(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
        length: int = 14,
    ) -> pd.Series | None:
        """Money Flow Index"""
        result = ta.mfi(high, low, close, volume, length=length)
        return result

    # --- Tier 2: Recommended indicators ---

    @staticmethod
    def supertrend(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        length: int = 7,
        multiplier: float = 3.0,
    ) -> pd.DataFrame | None:
        """Supertrend indicator"""
        result = ta.supertrend(high, low, close, length=length, multiplier=multiplier)
        return result

    @staticmethod
    def keltner(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        length: int = 20,
        multiplier: float = 1.5,
    ) -> pd.DataFrame | None:
        """Keltner Channel"""
        result = ta.kc(high, low, close, length=length, scalar=multiplier)
        return result

    @staticmethod
    def cmf(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
        length: int = 20,
    ) -> pd.Series | None:
        """Chaikin Money Flow"""
        result = ta.cmf(high, low, close, volume, length=length)
        return result

    @staticmethod
    def psar(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        af: float = 0.02,
        max_af: float = 0.2,
    ) -> pd.DataFrame | None:
        """Parabolic SAR"""
        result = ta.psar(high, low, close, af0=af, af=af, max_af=max_af)
        return result

    @staticmethod
    def ichimoku(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        tenkan: int = 9,
        kijun: int = 26,
        senkou: int = 52,
    ) -> pd.DataFrame | None:
        """Ichimoku Cloud"""
        result = ta.ichimoku(high, low, close, tenkan=tenkan, kijun=kijun, senkou=senkou)
        if result is None:
            return None
        # ta.ichimoku returns (DataFrame, DataFrame) — we want the first
        ichi, _ = result
        return ichi
