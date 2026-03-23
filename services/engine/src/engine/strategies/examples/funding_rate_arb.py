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
class FundingRateArbStrategy(AbstractStrategy):
    """Funding rate arbitrage (crypto only): spot long + perpetual short to earn funding."""

    name = "funding_rate_arb"
    description = "资金费率套利（加密货币专用）：现货多头 + 永续空头，赚取资金费率"
    timeframes = [TimeFrame.H4, TimeFrame.D1]
    markets = [Market.CRYPTO]
    warmup_periods = 24

    def __init__(
        self,
        min_funding_rate: float = 0.0005,
        consecutive_positive: int = 3,
        exit_rate_threshold: float = 0.0001,
        max_position_pct: float = 0.3,
    ) -> None:
        self.min_funding_rate = min_funding_rate
        self.consecutive_positive = consecutive_positive
        self.exit_rate_threshold = exit_rate_threshold
        self.max_position_pct = max_position_pct
        self._funding_rates: list[float] = []
        self._in_position: bool = False
        self._cumulative_funding: float = 0.0
        self._entry_price: float = 0.0
        self._below_threshold_count: int = 0

    def _estimate_funding_rate(self, bar: pd.Series) -> float:
        """Estimate funding rate from price volatility when actual rate is unavailable."""
        high = bar.get("high")
        low = bar.get("low")
        close = bar.get("close")
        if high is None or low is None or close is None or close == 0:
            return 0.0
        volatility = (float(high) - float(low)) / float(close)
        return volatility * 0.01

    def on_bar(self, bar: pd.Series) -> list[Signal]:
        funding_rate = bar.get("funding_rate")
        if funding_rate is None:
            funding_rate = self._estimate_funding_rate(bar)
        else:
            funding_rate = float(funding_rate)

        self._funding_rates.append(funding_rate)

        close = bar.get("close")
        if close is None:
            return []
        close = float(close)

        symbol = bar.get("symbol", "")

        signals: list[Signal] = []

        if self._in_position:
            # Accumulate funding income (each bar represents one funding period)
            self._cumulative_funding += funding_rate * close

            if funding_rate < 0:
                # Negative rate: exit immediately
                signals.append(
                    Signal(
                        symbol=symbol,
                        signal_type=SignalType.SELL,
                        price=close,
                        quantity=1.0,
                        metadata={
                            "type": "funding_arb",
                            "action": "exit",
                            "reason": "negative_rate",
                            "cumulative_funding": self._cumulative_funding,
                        },
                    )
                )
                self._reset_position()
            elif funding_rate < self.exit_rate_threshold:
                self._below_threshold_count += 1
                if self._below_threshold_count >= 2:
                    signals.append(
                        Signal(
                            symbol=symbol,
                            signal_type=SignalType.SELL,
                            price=close,
                            quantity=1.0,
                            metadata={
                                "type": "funding_arb",
                                "action": "exit",
                                "reason": "below_threshold",
                                "cumulative_funding": self._cumulative_funding,
                            },
                        )
                    )
                    self._reset_position()
            else:
                self._below_threshold_count = 0
        else:
            # Check entry condition: last N rates all above min_funding_rate
            n = self.consecutive_positive
            if len(self._funding_rates) >= n:
                recent = self._funding_rates[-n:]
                if all(r > self.min_funding_rate for r in recent):
                    signals.append(
                        Signal(
                            symbol=symbol,
                            signal_type=SignalType.BUY,
                            price=close,
                            quantity=1.0,
                            metadata={
                                "type": "funding_arb",
                                "hedge": "short_perp",
                                "action": "entry",
                                "avg_funding_rate": sum(recent) / len(recent),
                            },
                        )
                    )
                    self._in_position = True
                    self._entry_price = close
                    self._cumulative_funding = 0.0
                    self._below_threshold_count = 0

        return signals

    def _reset_position(self) -> None:
        self._in_position = False
        self._entry_price = 0.0
        self._cumulative_funding = 0.0
        self._below_threshold_count = 0

    def parameters(self) -> dict:
        return {
            "min_funding_rate": self.min_funding_rate,
            "consecutive_positive": self.consecutive_positive,
            "exit_rate_threshold": self.exit_rate_threshold,
            "max_position_pct": self.max_position_pct,
        }
