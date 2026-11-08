"""Stock universe the autonomous bot chooses from.

Default = liquid NSE large/mid-caps (Nifty-50-ish). The bot scores every name
in the universe and picks the best ones ITSELF — nothing is hardcoded to a
single stock. `affordable()` filters to what actually fits the capital so the
bot never proposes a stock it can't buy at least 1 share of within its
per-position cap.
"""
from __future__ import annotations

# ~45 liquid NSE tradingsymbols. Edit freely; or set `universe: auto` in config
# to use this list. These are the names the bot is allowed to consider.
NIFTY_LIQUID = [
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "ITC", "SBIN",
    "BHARTIARTL", "KOTAKBANK", "LT", "AXISBANK", "HINDUNILVR", "BAJFINANCE",
    "ASIANPAINT", "SUNPHARMA", "TITAN", "WIPRO", "ONGC", "NTPC", "POWERGRID",
    "TATAMOTORS", "TATASTEEL", "JSWSTEEL", "ADANIPORTS", "COALINDIA", "HCLTECH",
    "TECHM", "GRASIM", "HDFCLIFE", "DRREDDY", "CIPLA", "BRITANNIA", "INDUSINDBK",
    "M&M", "SBILIFE", "BPCL", "IOC", "GAIL", "HINDALCO", "TATACONSUM", "UPL",
    "DABUR", "MARICO", "BANKBARODA", "PNB",
]


def default_universe() -> list[str]:
    return list(NIFTY_LIQUID)


def affordable(symbols, prices: dict[str, float], capital: float,
               max_pos_pct: float) -> list[str]:
    """Keep only stocks where at least 1 share fits inside the per-position
    capital cap (capital * max_pos_pct). Skips missing/zero prices."""
    cap_per_pos = capital * max_pos_pct
    out = []
    for s in symbols:
        p = prices.get(s, 0.0)
        if p and 0 < p <= cap_per_pos:
            out.append(s)
    return out
