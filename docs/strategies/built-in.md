# Built-in Strategies

Kainex ships with 9 built-in strategies covering trend-following, mean reversion, momentum, machine learning, statistical arbitrage, and market-making approaches. All strategies are located in `services/engine/src/engine/strategies/examples/`.

## SMA Crossover

**Class:** `SmaCrossoverStrategy` / `SmaCrossoverLegacy`
**File:** `sma_crossover.py`

The classic simple moving average crossover. Buys when the short-period SMA crosses above the long-period SMA, and sells on the cross below. Available in both NautilusTrader (`KainexStrategy`) and legacy (`AbstractStrategy`) variants.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `short_window` | `int` | 10 | Short SMA period |
| `long_window` | `int` | 30 | Long SMA period |

### Supported Markets & Timeframes

- **Markets:** A-Shares, Crypto, US Stocks
- **Timeframes:** 1D, 1H

### How It Works

1. Computes two SMAs: a fast (short window) and a slow (long window).
2. When the fast SMA crosses above the slow SMA (golden cross), a BUY signal is generated.
3. When the fast SMA crosses below the slow SMA (death cross), a SELL signal is generated.
4. Warmup period equals the long window size.

### Best Suited For

Trending markets with clear directional moves. Works well on daily and hourly timeframes for medium-term trend following. Less effective in choppy, range-bound markets where frequent crossovers produce false signals.

---

## Dual MA

**Class:** `DualMaStrategy`
**File:** `dual_ma.py`

An enhanced moving average crossover strategy that supports both EMA and SMA, with configurable periods for the fast and slow averages.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `fast_period` | `int` | 10 | Fast moving average period |
| `slow_period` | `int` | 30 | Slow moving average period |
| `ma_type` | `str` | `"ema"` | Moving average type: `"ema"` or `"sma"` |

### Supported Markets & Timeframes

- **Markets:** A-Shares, Crypto, US Stocks
- **Timeframes:** 1M, 5M, 15M, 1H, 4H, 1D, 1W

### How It Works

1. Reads pre-computed fast and slow moving averages from the bar data (`ma_fast`, `ma_slow`).
2. Generates BUY when the fast MA crosses above the slow MA.
3. Generates SELL when the fast MA crosses below the slow MA.

### Best Suited For

All timeframes from scalping to position trading. EMA mode responds faster to price changes and is preferred for shorter timeframes, while SMA mode provides smoother signals for longer-term trading.

---

## RSI Mean Reversion

**Class:** `RsiMeanReversion`
**File:** `rsi_mean_reversion.py`

A mean reversion strategy based on the Relative Strength Index. Buys when the asset is oversold and sells when overbought.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `rsi_period` | `int` | 14 | RSI calculation period |
| `oversold` | `float` | 30.0 | RSI threshold for buy signal |
| `overbought` | `float` | 70.0 | RSI threshold for sell signal |

### Supported Markets & Timeframes

- **Markets:** A-Shares, Crypto, US Stocks
- **Timeframes:** 1H, 4H, 1D

### How It Works

1. Reads the pre-computed RSI value from the bar.
2. If RSI drops below the oversold threshold, generates a BUY signal (expecting a bounce).
3. If RSI rises above the overbought threshold, generates a SELL signal (expecting a pullback).
4. Warmup period is `rsi_period + 1`.

### Best Suited For

Range-bound and mean-reverting markets. Effective on hourly and daily timeframes when prices oscillate within a range. Combine with trend filters to avoid counter-trend entries during strong moves.

---

## Bollinger Breakout

**Class:** `BollingerBreakout`
**File:** `bollinger_breakout.py`

A breakout strategy using Bollinger Bands. Enters when price breaks above the upper band and exits when it breaks below the lower band.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `bb_period` | `int` | 20 | Bollinger Bands calculation period |
| `bb_std` | `float` | 2.0 | Number of standard deviations for band width |

### Supported Markets & Timeframes

- **Markets:** A-Shares, Crypto, US Stocks
- **Timeframes:** 15M, 1H, 4H

### How It Works

1. Reads pre-computed Bollinger Band values (`bb_upper`, `bb_lower`) from the bar.
2. When price closes above the upper band, generates a BUY signal (breakout momentum).
3. When price closes below the lower band, generates a SELL signal.

### Best Suited For

Volatile markets with breakout tendencies. Best on 15-minute to 4-hour timeframes where volatility expansion signals strong directional moves. Consider adjusting `bb_std` -- wider bands (2.5+) reduce false signals but may miss entries.

---

## MACD Crossover

**Class:** `MacdCrossover`
**File:** `macd_crossover.py`

A momentum/trend strategy based on MACD line and signal line crossovers.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `fast_period` | `int` | 12 | Fast EMA period for MACD |
| `slow_period` | `int` | 26 | Slow EMA period for MACD |
| `signal_period` | `int` | 9 | Signal line EMA period |

### Supported Markets & Timeframes

- **Markets:** A-Shares, Crypto, US Stocks
- **Timeframes:** 1H, 4H, 1D

### How It Works

1. Reads pre-computed MACD and signal line values from the bar.
2. When the MACD line crosses above the signal line, generates a BUY signal.
3. When the MACD line crosses below the signal line, generates a SELL signal.
4. Warmup period is `slow_period + signal_period`.

### Best Suited For

Trending markets where momentum is building. Works well on 1H to 1D timeframes. The MACD histogram can also be used to gauge the strength of the current move. Less reliable in sideways markets.

---

## Momentum

**Class:** `MomentumStrategy`
**File:** `momentum.py`

A pure momentum strategy that trades based on N-period returns exceeding a threshold.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lookback` | `int` | 20 | Number of periods to calculate return |
| `threshold` | `float` | 0.02 | Minimum absolute return to trigger signal (2%) |

### Supported Markets & Timeframes

- **Markets:** A-Shares, Crypto, US Stocks
- **Timeframes:** 1D, 1W

### How It Works

1. Accumulates close prices in a rolling buffer.
2. Computes the return over the lookback period: `(close - close_N_ago) / close_N_ago`.
3. If the return exceeds `+threshold`, generates a BUY signal (upward momentum).
4. If the return is below `-threshold`, generates a SELL signal (downward momentum).

### Best Suited For

Assets exhibiting momentum persistence -- crypto and growth stocks in trending phases. Works on daily and weekly timeframes. Adjust `threshold` based on asset volatility (higher for crypto, lower for large-cap stocks).

---

## ML Signal

**Class:** `MLSignalStrategy`
**File:** `ml_signal.py`

A machine learning-driven strategy that uses the feature store and model registry to generate predictions from OHLCV data.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model_name` | `str` | `"rf_classifier"` | Name of the model in the model registry |
| `threshold` | `float` | 0.5 | Prediction score threshold for signal generation |
| `lookback` | `int` | 60 | Number of bars in the feature computation window |

### Supported Markets & Timeframes

- **Markets:** A-Shares, Crypto, US Stocks
- **Timeframes:** 1D, 1H

### How It Works

1. Accumulates OHLCV bars into an internal buffer.
2. Once `lookback` bars are available, passes the window to the `FeatureStore` to compute 25+ technical features.
3. Feeds the features into the `MLPredictor` which loads a model from the `ModelRegistry`.
4. If the prediction score exceeds `+threshold`, generates a BUY signal.
5. If the prediction score is below `-threshold`, generates a SELL signal.

### Dependencies

- **Feature Store** (`engine.ml.feature_store`) -- Computes features like returns, volatility, RSI, MACD, Bollinger Bands, volume ratios, etc.
- **Model Registry** (`engine.ml.model_registry`) -- Stores versioned models (default: RandomForest).
- **ML Predictor** (`engine.indicators.ml_predictor`) -- Loads and runs inference.

### Best Suited For

Markets where technical patterns have predictive power. Requires training a model first using the ML pipeline. The default RandomForest classifier is a starting point -- consider gradient boosting or neural networks for production use.

---

## Pairs Trading

**Class:** `PairsTradingStrategy`
**File:** `pairs_trading.py`

A market-neutral statistical arbitrage strategy that trades the spread between two correlated assets using z-score of their price ratio.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `symbol_a` | `str` | `"A"` | First asset symbol |
| `symbol_b` | `str` | `"B"` | Second asset symbol |
| `lookback` | `int` | 60 | Rolling window for mean/std calculation |
| `entry_zscore` | `float` | 2.0 | Z-score threshold to enter a position |
| `exit_zscore` | `float` | 0.5 | Z-score threshold to exit (mean reversion) |

### Supported Markets & Timeframes

- **Markets:** A-Shares, Crypto, US Stocks
- **Timeframes:** 1H, 4H, 1D

### How It Works

1. Computes the price ratio `price_a / price_b` on each bar.
2. Calculates a rolling z-score of the ratio over the lookback window.
3. **Entry long A / short B:** z-score < `-entry_zscore` (ratio is unusually low).
4. **Entry short A / long B:** z-score > `+entry_zscore` (ratio is unusually high).
5. **Exit:** z-score returns within `exit_zscore` of the mean (spread has reverted).

### Best Suited For

Highly correlated asset pairs (e.g., BTC/ETH, related sector stocks). Requires careful pair selection and cointegration testing. The strategy is market-neutral by design, profiting from relative price movements rather than directional bets.

---

## Grid Trading

**Class:** `GridTradingStrategy`
**File:** `grid_trading.py`

A market-making strategy that places buy and sell orders at fixed price intervals around a base price, profiting from price oscillation.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `grid_size` | `float` | 0.02 | Price interval between grid levels (2%) |
| `num_grids` | `int` | 10 | Total number of grid levels |
| `base_price` | `float` | 0.0 | Center price (0 = auto-detect from first bar) |

### Supported Markets & Timeframes

- **Markets:** Crypto
- **Timeframes:** 1M, 5M, 15M

### How It Works

1. On the first bar, builds a grid of price levels centered around the base price (or current price if base is 0).
2. Grid levels are spaced by `grid_size` percentage intervals.
3. When price crosses down through a grid level, generates a BUY signal (buying the dip).
4. When price crosses up through a grid level, generates a SELL signal (selling the rally).

### Best Suited For

Range-bound, high-liquidity crypto markets. Most effective when the asset oscillates within a predictable range. Adjust `grid_size` based on typical volatility -- tighter grids for stable pairs, wider grids for volatile ones. Not recommended during strong trending phases.
