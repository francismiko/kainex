#!/usr/bin/env python
"""Train an example RandomForest classifier and register it via ModelRegistry.

Usage:
    uv run python scripts/train_example_model.py

The script attempts to load OHLCV data from the project's DuckDB store.
If no data is found, it generates synthetic OHLCV data so the script can
run stand-alone for testing and demonstration purposes.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

# Ensure the engine package is importable when run from repo root.
_ENGINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ENGINE_ROOT / "src"))

from engine.ml.feature_store import FeatureStore
from engine.ml.model_registry import ModelRegistry

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Data loading / generation
# ------------------------------------------------------------------

def _load_from_duckdb() -> pd.DataFrame | None:
    """Try to read OHLCV bars from the project's DuckDB store."""
    try:
        from engine.storage.duckdb_store import DuckDBStore

        store = DuckDBStore()
        # Attempt to find any data
        result = store.execute("SELECT DISTINCT symbol, market, timeframe FROM bars LIMIT 1")
        row = result.fetchone()
        if row is None:
            store.close()
            return None
        symbol, market, timeframe = row
        df = store.query_bars(symbol, market, timeframe)
        store.close()
        if df.empty or len(df) < 100:
            return None
        logger.info(
            "Loaded %d bars for %s/%s/%s from DuckDB.",
            len(df), symbol, market, timeframe,
        )
        return df
    except Exception as exc:
        logger.debug("Could not load from DuckDB: %s", exc)
        return None


def _generate_synthetic(n: int = 500, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic OHLCV data for training."""
    logger.info("Generating %d synthetic OHLCV bars...", n)
    rng = np.random.RandomState(seed)
    dates = pd.bdate_range("2022-01-01", periods=n, freq="D")
    close = 100 + np.cumsum(rng.randn(n) * 0.8)
    close = np.maximum(close, 10.0)
    high = close + rng.uniform(0, 2, n)
    low = close - rng.uniform(0, 2, n)
    open_ = close + rng.uniform(-1, 1, n)
    volume = rng.randint(1000, 50000, n).astype(float)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


# ------------------------------------------------------------------
# Label construction
# ------------------------------------------------------------------

def _make_labels(df: pd.DataFrame, horizon: int = 5, threshold: float = 0.01) -> pd.Series:
    """Create ternary labels based on future returns.

    Returns
    -------
    pd.Series
        Values in ``{-1, 0, 1}`` for sell / hold / buy.
    """
    future_ret = df["close"].pct_change(horizon).shift(-horizon)
    labels = pd.Series(0, index=df.index, dtype=int)
    labels[future_ret > threshold] = 1   # buy
    labels[future_ret < -threshold] = -1  # sell
    return labels


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main() -> None:
    # 1. Load data
    df = _load_from_duckdb()
    if df is None:
        df = _generate_synthetic()

    # 2. Compute features
    fs = FeatureStore()
    features = fs.compute_features(df)
    logger.info("Computed %d features for %d rows.", features.shape[1], features.shape[0])

    # 3. Create labels (aligned with features index)
    labels = _make_labels(df, horizon=5, threshold=0.01)
    labels = labels.reindex(features.index)

    # Drop rows where labels are NaN (last *horizon* rows)
    mask = labels.notna()
    features = features[mask]
    labels = labels[mask].astype(int)

    if len(features) < 50:
        logger.error("Not enough data to train (%d rows). Aborting.", len(features))
        sys.exit(1)

    logger.info("Training set size: %d rows, %d features", *features.shape)
    logger.info("Label distribution:\n%s", labels.value_counts().to_string())

    # 4. Train / test split
    X_train, X_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.2, shuffle=False,
    )

    # 5. Train a RandomForest
    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=6,
        min_samples_leaf=10,
        random_state=42,
        n_jobs=-1,
    )
    clf.fit(X_train, y_train)

    # 6. Evaluate
    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    logger.info("Test accuracy: %.4f", acc)
    logger.info("Classification report:\n%s", classification_report(y_test, y_pred))

    # 7. Register model
    reg = ModelRegistry()
    mv = reg.register(
        name="rf_classifier",
        model=clf,
        metrics={"accuracy": acc},
        metadata={
            "n_features": features.shape[1],
            "feature_names": list(features.columns),
            "n_estimators": 100,
            "max_depth": 6,
        },
    )
    logger.info("Registered model '%s' version %s at %s", mv.name, mv.version, mv.path)
    logger.info("Done.")


if __name__ == "__main__":
    main()
