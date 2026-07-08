#  TradingBot — Autonomous, Risk-First Algo-Trading Framework (India / NSE)

A personal-use, paper-first automated trading system for Indian equities. It
scans a universe of stocks, scores them on fundamentals + technicals + news
sentiment, adapts to the market regime, sizes positions by risk, and enforces a
hard daily kill-switch — with the whole thing validated by **walk-forward
testing** so it never fools you with in-sample fantasies.

>  **Honest disclaimer — read first.**
> This bot does **not** make guaranteed profit. No bot does. Every rigorous test
> here (walk-forward: **0/9 out-of-sample windows positive**) shows **no
> profitable edge** on liquid NSE large-caps after costs. SEBI's own data: **93%
> of retail F&O traders lose money.** This project's real value is **discipline +
> honest validation**, not returns. It runs in **paper mode** (simulated fills)
> by default. Do not risk real money without a long, positive, out-of-sample,
> live-paper track record (which you most likely won't get).

---

## What it is

An end-to-end research + execution framework:
- **Autonomous stock picker** (`HAASEY`) — multi-factor, regime-aware.
- **Risk engine** — daily profit/loss kill-switch, per-trade caps, auto square-off.
- **Honest validation** — walk-forward (in-sample vs out-of-sample), cost model.
- **AI layer (out of the execution loop)** — FinBERT sentiment, Gemini chat/parse,
  LangGraph human-approval agent.
- **ML experiments (gated)** — XGBoost signal + SHAP, genetic optimizer, PPO/RL —
  each kept only if it beats a baseline out-of-sample (none did).

**Design rule:** the LLM/ML never places orders. The trade loop is pure,
deterministic Python; AI only *informs* and *proposes* (with human approval).

---

## Tech stack

| Layer | Tech |
|---|---|
| Language | Python 3.11 |
| Broker (live) | Zerodha **Kite Connect** (`kiteconnect`) |
| Free market data | **yfinance** (real NSE prices, candles, fundamentals) |
| Data / math | pandas, numpy |
| Scheduling | APScheduler, pytz (IST) |
| AI — sentiment | **FinBERT** (`transformers` + `torch`, `ProsusAI/finbert`) — local, free |
| AI — chat/agent | **Gemini** (`google-genai`, `gemini-2.5-flash-lite`), **LangGraph** |
| ML experiments | xgboost, scikit-learn, shap, stable-baselines3, gymnasium |
| News | Google News RSS (free) |
| Web UI | FastAPI + uvicorn |
| Storage | SQLite (orders, daily P&L, audit) |
| Tests | pytest (17 tests) |

---

## How it works (one cycle)

```
1. REGIME   classify NIFTY + VIX -> BULL / BEAR / CHOPPY
2. SCAN     for each stock in the universe:
   - resample to 15-min decision bars
   - if holding -> EXIT check (take-profit / ATR trailing stop / square-off)
   - if flat    -> TREND (>SMA50 & >EMA20) + 60-min confluence + time-window
                   + score 7 factors -> if >= buy threshold, it's a candidate
3. RANK     sort candidates by score; BUY the best it can afford within capital
4. SIZE     ATR risk × regime multiplier × fractional-Kelly
5. GATE     every order -> RISK ENGINE (resize/reject) -> broker
6. GUARD    every tick -> daily profit/loss kill-switch (flatten + lock)
```

Full internals: see **[Haasey.md](Haasey.md)** (strategy deep-dive) and
**[Functioning.md](Functioning.md)** (whole-project reference).

---

## The parameters I chose (and why)

The flagship strategy is **`haasey_v3`** (a ₹20,000 account). Current tuned config:

| Parameter | Value | Why |
|---|---|---|
| `capital` | ₹20,000 | account size |
| `universe` | `auto` | scan ~45 liquid NSE names; pick the best |
| `decision_bar_minutes` | 15 | trade on 15-min bars (not tick noise) |
| `buy` / `strong_buy` | 0.46 / 0.65 | score thresholds (0.46 = wider net) |
| `take_profit_pct` | **1.0%** | meaningful 15-min move, not noise (avoids churn) |
| `trail_atr_mult` | **2.0** | tighter trailing stop → faster loss-cut |
| `cooldown_minutes` | **60** | hold ≥4 bars before a stop exit → less whipsaw |
| `min_profit_cost_ratio` | **2.0** | only trade if expected move > 2× round-trip cost |
| `trade_windows` | 09:30–11:30, 13:30–15:00 | skip the choppy midday lull |
| `trend_sma` / `trend_ema` | 50 / 20 | only buy in an uptrend |
| `htf_minutes` / `htf_sma` | 60 / 20 | 60-min trend must agree (confluence) |
| `regime_sma` / `regime_vix_high` | 50 / 20.0 | regime from NIFTY SMA50 + VIX |
| `use_regime_weights` | true | BULL→momentum-led, BEAR→value/quality-led (LIVE) |
| `per_trade_risk_pct` | 0.015 | risk ~1.5% of capital per trade |
| `max_pos_pct` | 0.12 | ≤12% of capital per stock |
| `max_positions` | 25 | uncapped (cash is the real limit ≈ 5–8 names) |

**7-factor score (live weights):** Value 0.25 · Quality 0.22 · Growth 0.22 ·
Momentum 0.13 · Technical 0.08 · Sentiment 0.05 · Stability 0.05. In **backtest**
the weights flip technical/momentum-led (fundamentals can't be backtested without
look-ahead bias). Regime-aware weights override these live.

**Risk kill-switch:** `daily_profit_target` ₹30,000 · `daily_max_loss` ₹2,000 →
flatten + lock the day. Costs modelled (Zerodha brokerage + STT + slippage).

---

## Install & run

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (or: source .venv/bin/activate)
pip install -r requirements.txt
cp .env.example .env              # add GEMINI_API_KEY (optional); paper needs no keys
```

```bash
# backtest with costs
python -m src.main backtest --strategy haasey_v3 --days 30
# the honest test: in-sample vs out-of-sample
python -m src.main walkforward --strategy haasey_v3 --days 60
# live paper (real prices, simulated fills, during 09:15–15:30 IST)
python -m src.main paperlog --strategy haasey_v3 --max-symbols 20
python -m src.main analyze        # performance report
# extras
python -m src.main genetic        # genetic optimizer (walk-forward gated)
python -m src.main mlsignal       # XGBoost OOS vs baseline (+SHAP)
python -m src.main supervisor     # LangGraph regime proposal (human-approval)
python -m src.main web            # dashboard + chat at :8000
```

---

## Results (honest, all paper, all with costs)

| Test | Result |
|---|---|
| **Walk-forward** (rigorous OOS) | **0/9 folds positive** — no edge |
| Walk-forward after tuning | 0/9, OOS loss **halved** (−₹422 → −₹239) |
| XGBoost (OOS) | −₹58 vs baseline −₹198 — loses less, not profitable |
| Genetic optimizer | IS +₹275 → OOS +₹14 — overfitting shrinkage |
| PPO / RL | −₹515 vs baseline −₹87 — dropped |
| Live paper (1 session) | +₹25 (+0.13%) — noise on a rising day |

**Takeaway:** sophisticated and fully working; **not a proven money-maker.** The
framework's job is to prove that honestly — and it does.

---

## Security & compliance

- **Never commit `.env`** — it holds API keys (gitignored by default). Verify with
  `git status` before pushing.
- Rotate any key that's ever been shared.
- **SEBI:** personal use on your own broker account is fine. Offering this to other
  people (trading their accounts) requires exchange empanelment + likely a
  Research Analyst licence. Don't productise it without compliance.

---

## Project layout

```
config/settings.yaml   risk limits, session times, strategies, costs
src/strategies/        haasey_v3 (+ threshold, orb_vwap, supertrend_vwap, rsi_reversion…)
src/data/              regime, fundamentals+VIX, universe
src/ai/                finbert, gemini, news
src/agent/             LangGraph planner + regime supervisor (human-gated)
src/risk/              kill-switch engine + dynamic sizing
src/backtest/          portfolio, walkforward, genetic, costs
src/ml/                xgboost signal + SHAP, PPO env/agent (experimental)
src/engine/            trader loop, scheduler, live paper logger
src/web/app.py         FastAPI dashboard + chat
tests/                 pytest (17)
```

---

*Not investment advice. Trading involves real risk of loss. You are responsible
for every order and for SEBI/exchange compliance.*
