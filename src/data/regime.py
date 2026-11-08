"""Market-regime detection: BULL / BEAR / CHOPPY.

Replaces the old binary "NIFTY < 0.98*SMA20 → skip" switch with a 3-state view
built from the index trend (price vs SMA + slope) and the India VIX (fear gauge).
The regime tells HAASEY *how* to behave, not just on/off:
  BULL   → normal / full size
  CHOPPY → allowed, reduced size (range-bound, lower conviction)
  BEAR   → no NEW entries + defensive size (existing positions still managed)

This is a transparent, rules-based classifier (no black box). It is the honest
kind of "adaptivity" — trade less/smaller when the whole market is hostile.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class RegimeState:
    label: str                 # BULL / BEAR / CHOPPY / UNKNOWN
    allow_new_entries: bool
    size_mult: float           # scale position size (used by dynamic sizing)
    detail: str


def classify_regime(index_df: Optional[pd.DataFrame], vix: Optional[float] = None,
                    sma_slow: int = 50, slope_lookback: int = 6,
                    vix_high: float = 20.0) -> RegimeState:
    """Classify the current regime from index decision bars + optional VIX."""
    if index_df is None or len(index_df) < sma_slow + slope_lookback + 1:
        # Not enough index data → don't block trading, treat as neutral.
        return RegimeState("UNKNOWN", True, 1.0, "insufficient index data")

    close = index_df["close"]
    price = float(close.iloc[-1])
    sma = close.rolling(sma_slow).mean()
    sma_now = float(sma.iloc[-1])
    sma_prev = float(sma.iloc[-1 - slope_lookback])
    slope_up = sma_now >= sma_prev
    above = price >= sma_now
    high_vol = vix is not None and vix >= vix_high

    # BEAR: downtrend (below a falling SMA) or a volatility spike → risk-off.
    if (not above and not slope_up) or high_vol:
        return RegimeState("BEAR", False, 0.5,
                           f"px{'>' if above else '<'}SMA{sma_slow}, "
                           f"slope={'up' if slope_up else 'down'}, vix={vix}")
    # BULL: uptrend (above a rising SMA) and calm.
    if above and slope_up and not high_vol:
        return RegimeState("BULL", True, 1.0, f"uptrend above SMA{sma_slow}, calm")
    # Everything else = choppy / transitional.
    return RegimeState("CHOPPY", True, 0.75, "range-bound / mixed trend")
