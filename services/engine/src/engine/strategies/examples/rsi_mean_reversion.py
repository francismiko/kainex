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
class RsiMeanReversion(AbstractStrategy):
    """Enhanced RSI mean reversion with volatility filter.

    Entry: RSI < oversold AND BBW > min_bbw (not squeezed) AND ADX < max_adx (no strong trend).
    Exit: RSI > exit_rsi OR held for max_hold_bars bars.
    Position sizing: fixed risk fraction with ATR-based stop loss.

    Applicable to A-stock, crypto, and US stock markets.
    """

    name = "rsi_mean_reversion"
    description = (
        "Enhanced RSI mean reversion with Bollinger bandwidth and ADX filters, "
        "three-market universal"
    )
    timeframes = [TimeFrame.H1, TimeFrame.H4, TimeFrame.D1]
    markets = [Market.A_STOCK, Market.CRYPTO, Market.US_STOCK]

    def __init__(
        self,
        rsi_period: int = 14,
        oversold: float = 30.0,
        overbought: float = 70.0,
        # --- new volatility / trend filter params ---
        min_bbw: float = 0.02,
        max_adx: float = 25.0,
        exit_rsi: float = 50.0,
        max_hold_bars: int = 10,
        atr_multiplier: float = 2.0,
        risk_pct: float = 0.01,
    ) -> None:
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
        self.min_bbw = min_bbw
        self.max_adx = max_adx
        self.exit_rsi = exit_rsi
        self.max_hold_bars = max_hold_bars
        self.atr_multiplier = atr_multiplier
        self.risk_pct = risk_pct
        self.warmup_periods = max(rsi_period + 1, 20)

        # Internal state for exit tracking
        self._bars_held: int = 0
        self._in_position: bool = False
        self._entry_price: float = 0.0

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _volatility_ok(self, bar: pd.Series) -> bool:
        """Return True when volatility filters pass (or are unavailable)."""
        bbw = bar.get("bbw")
        adx = bar.get("adx")
        # If indicators are absent fall back to legacy behaviour (no filter)
        if bbw is not None and bbw < self.min_bbw:
            return False
        if adx is not None and adx > self.max_adx:
            return False
        return True

    def _calc_quantity(self, bar: pd.Series, equity: float = 100_000.0) -> float:
        """Fixed-risk position sizing via ATR stop."""
        atr = bar.get("atr")
        close = bar["close"]
        if atr is None or atr <= 0 or close <= 0:
            return 1.0
        risk_per_share = self.atr_multiplier * atr
        if risk_per_share <= 0:
            return 1.0
        qty = (equity * self.risk_pct) / risk_per_share
        return round(max(qty, 1.0), 6)

    def _calc_stop_loss(self, bar: pd.Series) -> float | None:
        atr = bar.get("atr")
        if atr is None or atr <= 0:
            return None
        return bar["close"] - self.atr_multiplier * atr

    # ------------------------------------------------------------------ #
    # core
    # ------------------------------------------------------------------ #
    def on_bar(self, bar: pd.Series) -> list[Signal]:
        rsi = bar.get("rsi")
        if rsi is None:
            return []

        symbol = bar.get("symbol", "")
        close = bar["close"]
        signals: list[Signal] = []

        # --- exit logic ---
        if self._in_position:
            self._bars_held += 1
            if rsi > self.exit_rsi or self._bars_held >= self.max_hold_bars:
                signals.append(
                    Signal(
                        symbol=symbol,
                        signal_type=SignalType.SELL,
                        price=close,
                        quantity=1.0,
                        metadata={"reason": "exit_rsi" if rsi > self.exit_rsi else "max_hold"},
                    )
                )
                self._in_position = False
                self._bars_held = 0
                self._entry_price = 0.0
            return signals

        # --- entry logic ---
        if rsi < self.oversold and self._volatility_ok(bar):
            qty = self._calc_quantity(bar)
            stop = self._calc_stop_loss(bar)
            signals.append(
                Signal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    price=close,
                    quantity=qty,
                    stop_loss=stop,
                )
            )
            self._in_position = True
            self._bars_held = 0
            self._entry_price = close
        elif rsi > self.overbought:
            signals.append(
                Signal(
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    price=close,
                    quantity=1.0,
                )
            )
        return signals

    def parameters(self) -> dict:
        return {
            "rsi_period": self.rsi_period,
            "oversold": self.oversold,
            "overbought": self.overbought,
            "min_bbw": self.min_bbw,
            "max_adx": self.max_adx,
            "exit_rsi": self.exit_rsi,
            "max_hold_bars": self.max_hold_bars,
            "atr_multiplier": self.atr_multiplier,
            "risk_pct": self.risk_pct,
        }
