"""Free fundamentals + macro via yfinance. Cached per-day to avoid hammering
Yahoo. Everything degrades gracefully to None if offline / rate-limited, so
the scorer simply drops the fundamental/macro factor rather than crashing.

NOTE: these are *current* snapshots. Using them in a backtest over past prices
would be look-ahead bias, so HAASEY only consults them in LIVE mode.
"""
from __future__ import annotations

import time
from typing import Optional

class FundamentalsProvider:
    """Best-effort fundamentals from free yfinance, normalised to the units the
    HAASEY scorers expect (ROE/growth in %, debt/equity as a ratio, yields as
    fractions).

    IMPORTANT — data availability with the FREE source:
      Available:   trailingPE, priceToBook, pegRatio, returnOnEquity,
                   debtToEquity, earningsGrowth, revenueGrowth, currentRatio,
                   dividendYield, fiftyTwoWeekHigh, and a computed FCF yield.
      NOT available (need a paid/scraped source like screener.in):
                   ROCE, interestCoverage, promoterHoldingPct.
      Missing keys are simply omitted, so the scorer falls back to a neutral
      default for those factors (they don't fabricate a signal).
    """

    def __init__(self, ttl_seconds: float = 6 * 3600):
        self.ttl = ttl_seconds
        self._cache: dict[str, tuple[float, Optional[dict]]] = {}

    def get(self, symbol: str) -> Optional[dict]:
        hit = self._cache.get(symbol)
        if hit and (time.time() - hit[0] < self.ttl):
            return hit[1]
        data = self._fetch(symbol)
        self._cache[symbol] = (time.time(), data)
        return data

    def _fetch(self, symbol: str) -> Optional[dict]:
        try:
            import yfinance as yf
        except Exception:
            return None
        ticker = symbol if symbol.startswith("^") or "." in symbol else f"{symbol}.NS"
        try:
            info = yf.Ticker(ticker).info
        except Exception:
            return None
        if not info:
            return None

        out: dict = {}

        def put(key, val):
            if val is not None:
                out[key] = val

        put("trailingPE", info.get("trailingPE"))
        put("priceToBook", info.get("priceToBook"))
        put("pegRatio", info.get("trailingPegRatio") or info.get("pegRatio"))
        put("currentRatio", info.get("currentRatio"))
        put("fiftyTwoWeekHigh", info.get("fiftyTwoWeekHigh"))
        put("profitMargins", info.get("profitMargins"))
        put("marketCap", info.get("marketCap"))

        roe = info.get("returnOnEquity")
        put("returnOnEquity", roe * 100 if roe is not None else None)  # fraction -> %
        de = info.get("debtToEquity")
        put("debtToEquity", de / 100 if de is not None else None)      # % -> ratio
        eg = info.get("earningsGrowth")
        put("earningsGrowth", eg * 100 if eg is not None else None)    # fraction -> %
        rg = info.get("revenueGrowth")
        put("revenueGrowth", rg * 100 if rg is not None else None)     # fraction -> %

        dy = info.get("dividendYield")
        if dy is not None:
            put("dividendYield", dy / 100 if dy > 1 else dy)           # normalise to fraction

        fcf, mc = info.get("freeCashflow"), info.get("marketCap")
        if fcf and mc:
            put("freeCashFlowYield", fcf / mc)

        # ROCE / interestCoverage / promoterHoldingPct: not in yfinance -> omitted.
        return out


_vix_cache: tuple[float, Optional[float]] = (0.0, None)


def india_vix(ttl_seconds: float = 900) -> Optional[float]:
    """Latest India VIX close (^INDIAVIX) from Yahoo, cached 15 min."""
    global _vix_cache
    if time.time() - _vix_cache[0] < ttl_seconds and _vix_cache[1] is not None:
        return _vix_cache[1]
    try:
        import yfinance as yf

        hist = yf.Ticker("^INDIAVIX").history(period="5d", interval="1d")
        val = float(hist["Close"].dropna().iloc[-1]) if not hist.empty else None
    except Exception:
        val = None
    _vix_cache = (time.time(), val)
    return val
