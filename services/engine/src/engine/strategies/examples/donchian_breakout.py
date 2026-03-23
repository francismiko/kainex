import pandas as pd

from engine.strategies.base import (
    AbstractStrategy,
    Market,
    Signal,
    SignalType,
    TimeFrame,
)
from engine.strategies.registry import registry


@registry.register
class DonchianBreakoutStrategy(AbstractStrategy):
    """Modern Donchian channel breakout (improved Turtle strategy).

    Entry:
      - Long:  close > upper channel AND EMA8 > EMA21 > EMA50 (trend filter)
      - Short: close < lower channel AND EMA8 < EMA21 < EMA50
      - ATR expansion: when ATR > 1.5x ATR_MA20 position size is halved.

    Exit:
      - Long:  close < exit lower channel OR stop loss hit
      - Short: close > exit upper channel OR stop loss hit

    Applicable to A-stock, crypto, and US stock markets.
    """

    name = "donchian_breakout"
    description = "现代化 Donchian 通道突破（改进版海龟策略），三市场通用"
    timeframes = [TimeFrame.H4, TimeFrame.D1]
    markets = [Market.A_STOCK, Market.CRYPTO, Market.US_STOCK]
    warmup_periods = 60

    def __init__(
        self,
        entry_period: int = 20,
        exit_period: int = 10,
        atr_period: int = 20,
        atr_stop_multiplier: float = 2.0,
        trend_filter: bool = True,
        risk_pct: float = 0.01,
    ) -> None:
        self.entry_period = entry_period
        self.exit_period = exit_period
        self.atr_period = atr_period
        self.atr_stop_multiplier = atr_stop_multiplier
        self.trend_filter = trend_filter
        self.risk_pct = risk_pct
        self.warmup_periods = max(60, entry_period + 1)

        # Rolling windows for channel calculation
        self._highs: list[float] = []
        self._lows: list[float] = []
        self._closes: list[float] = []
        self._atrs: list[float] = []

        # Position tracking
        self._position: int = 0  # 1=long, -1=short, 0=flat
        self._stop_price: float = 0.0

    # ------------------------------------------------------------------ #
    # channel calculations
    # ------------------------------------------------------------------ #
    def _entry_upper(self) -> float | None:
        if len(self._highs) < self.entry_period:
            return None
        return max(self._highs[-self.entry_period :])

    def _entry_lower(self) -> float | None:
        if len(self._lows) < self.entry_period:
            return None
        return min(self._lows[-self.entry_period :])

    def _exit_upper(self) -> float | None:
        if len(self._highs) < self.exit_period:
            return None
        return max(self._highs[-self.exit_period :])

    def _exit_lower(self) -> float | None:
        if len(self._lows) < self.exit_period:
            return None
        return min(self._lows[-self.exit_period :])

    # ------------------------------------------------------------------ #
    # trend filter via EMA alignment
    # ------------------------------------------------------------------ #
    def _trend_up(self, bar: pd.Series) -> bool:
        if not self.trend_filter:
            return True
        ema8 = bar.get("ema_8")
        ema21 = bar.get("ema_21")
        ema50 = bar.get("ema_50")
        if ema8 is None or ema21 is None or ema50 is None:
            # When EMA data is missing, skip trend filter (allow entry)
            return not self.trend_filter
        return ema8 > ema21 > ema50

    def _trend_down(self, bar: pd.Series) -> bool:
        if not self.trend_filter:
            return True
        ema8 = bar.get("ema_8")
        ema21 = bar.get("ema_21")
        ema50 = bar.get("ema_50")
        if ema8 is None or ema21 is None or ema50 is None:
            return not self.trend_filter
        return ema8 < ema21 < ema50

    # ------------------------------------------------------------------ #
    # ATR expansion detection
    # ------------------------------------------------------------------ #
    def _atr_expanded(self) -> bool:
        """Return True when current ATR > 1.5x its 20-period moving average."""
        if len(self._atrs) < 20:
            return False
        atr_ma = sum(self._atrs[-20:]) / 20
        if atr_ma <= 0:
            return False
        return self._atrs[-1] > 1.5 * atr_ma

    # ------------------------------------------------------------------ #
    # position sizing
    # ------------------------------------------------------------------ #
    def _calc_quantity(self, bar: pd.Series, equity: float = 100_000.0) -> float:
        atr = bar.get("atr")
        close = bar["close"]
        if atr is None or atr <= 0 or close <= 0:
            qty = 1.0
        else:
            risk_per_share = self.atr_stop_multiplier * atr
            qty = (equity * self.risk_pct) / risk_per_share if risk_per_share > 0 else 1.0
            qty = max(qty, 1.0)
        # Halve on ATR expansion
        if self._atr_expanded():
            qty *= 0.5
        return round(qty, 6)

    # ------------------------------------------------------------------ #
    # core
    # ------------------------------------------------------------------ #
    def on_bar(self, bar: pd.Series) -> list[Signal]:
        high = bar.get("high")
        low = bar.get("low")
        close = bar.get("close")
        if close is None or high is None or low is None:
            return []

        close = float(close)
        high = float(high)
        low = float(low)

        # Compute channels from PRIOR bars (before appending current bar)
        entry_upper = self._entry_upper()
        entry_lower = self._entry_lower()
        exit_upper = self._exit_upper()
        exit_lower = self._exit_lower()

        # Now append current bar data
        self._highs.append(high)
        self._lows.append(low)
        self._closes.append(close)

        atr = bar.get("atr")
        if atr is not None:
            self._atrs.append(float(atr))

        symbol = bar.get("symbol", "")
        signals: list[Signal] = []

        # --- exit logic ---
        if self._position == 1:
            stop_hit = close <= self._stop_price if self._stop_price > 0 else False
            if stop_hit or (exit_lower is not None and close < exit_lower):
                signals.append(
                    Signal(
                        symbol=symbol,
                        signal_type=SignalType.SELL,
                        price=close,
                        quantity=1.0,
                        metadata={"reason": "stop_loss" if stop_hit else "exit_channel"},
                    )
                )
                self._position = 0
                self._stop_price = 0.0
            return signals

        if self._position == -1:
            stop_hit = close >= self._stop_price if self._stop_price > 0 else False
            if stop_hit or (exit_upper is not None and close > exit_upper):
                signals.append(
                    Signal(
                        symbol=symbol,
                        signal_type=SignalType.BUY,
                        price=close,
                        quantity=1.0,
                        metadata={"reason": "stop_loss" if stop_hit else "exit_channel"},
                    )
                )
                self._position = 0
                self._stop_price = 0.0
            return signals

        # --- entry logic (flat) ---
        if entry_upper is None or entry_lower is None:
            return signals

        atr_val = bar.get("atr")

        if close > entry_upper and self._trend_up(bar):
            qty = self._calc_quantity(bar)
            stop = (close - self.atr_stop_multiplier * atr_val) if atr_val and atr_val > 0 else None
            signals.append(
                Signal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    price=close,
                    quantity=qty,
                    stop_loss=stop,
                )
            )
            self._position = 1
            self._stop_price = stop if stop is not None else 0.0

        elif close < entry_lower and self._trend_down(bar):
            qty = self._calc_quantity(bar)
            stop = (close + self.atr_stop_multiplier * atr_val) if atr_val and atr_val > 0 else None
            signals.append(
                Signal(
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    price=close,
                    quantity=qty,
                    stop_loss=stop,
                )
            )
            self._position = -1
            self._stop_price = stop if stop is not None else 0.0

        return signals

    def parameters(self) -> dict:
        return {
            "entry_period": self.entry_period,
            "exit_period": self.exit_period,
            "atr_period": self.atr_period,
            "atr_stop_multiplier": self.atr_stop_multiplier,
            "trend_filter": self.trend_filter,
            "risk_pct": self.risk_pct,
        }
