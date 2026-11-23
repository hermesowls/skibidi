# Phase 4: Ingestion Criteria Expansion & Live Quotes Engine

Comprehensive Architecture & Implementation Plan for Phase 4 of the Autonomous Trading System.

---

## 1. Executive Summary & Core Objectives

Phase 4 transitions the autonomous trading system from Discord-only ingestion and static mock quotes into an institutional-grade, multi-source ingestion pipeline with real-time truthful market quotes, dynamic quantitative risk targets, and a closed-loop **Strategy Traceability & Shadow Quant Backtest Feedback Engine**.

### Core Objectives:
1. **Truthful Live Quotes Service**:
   - Upgrade `/api/analyst-trader/live-quotes` from returning `{price: 0, change_pct: 0}` mock data to serving live CBOE delayed quotes with extended-hours detection and 60-second in-memory caching.
   - Strictly maintain backward compatibility with `test_reconciled_checkout_verification.py:291` (`test_live_quotes_truthfulness`) by defaulting `live=false` in offline test suites and activating live market lookups when `live=true` is requested.
2. **Realistic Dynamic TP1/TP2 & Risk Calibration**:
   - Align default TP1 recommendations to **+20% to +25%** (calibrated dynamically per account size, moneyness, DTE, and 1:1 to 1.25:1 Risk/Reward against a 20-25% stop loss), completely retiring unrealistic 45%+ pop requirements for base de-risking.
   - Anchor TP2 to **+45% to +60%** (2:1 to 2.5:1 R:R) aligned with major GEX magnet levels.
   - Calibrate contract-by-contract trim schedules for Micro (<$1k), Growing ($1k-$5k), and Established ($5k+) account tiers.
3. **Institutional Whale Qualification Criteria Engine**:
   - Build `WhaleFilterEngine` in `skills/financial/autonomous-trader/scripts/whale_filter_criteria.py` evaluating:
     - **Whale Size & Aggression**: Premium $\ge \$200\text{k}$ to $\$500\text{k}+$, Vol/OI ratio $\ge 2.5\times$, multi-exchange sweeps at Ask / Above Mid, DTE 14–60 days.
     - **EMA Stack Confluence**: Complete `EMA(8, 21, 50, 100, 200)` stack via `TechnicalIndicatorsEngine` and CBOE historical daily bars. Distinguishes Full Bullish Stacks / 8/21 crosses, and heavily penalizes or rejects calls trapped below the 200 EMA.
     - **Volume & RVOL**: Relative volume $\ge 1.2\times$ or intraday volume $>1\text{M}$ shares.
     - **GEX / VEX Regime**: Integrates `gex_downstream_overlay.py` — negative gamma volatility expansion multiplier vs positive gamma volatility suppression.
     - **Multi-Whale Cluster Memory**: Tracks repeat institutional sweeps on the same ticker/strike across sessions in SQLite, identifying high-conviction institutional accumulation clusters.
4. **Multi-Source Ingress Expansion**:
   - Ingest flow signals across:
     - Discord channels (`#notable-flow` and `#notable-etf-flow`)
     - Skylit Flowseeker tape (`app.skylit.ai/flow/live`)
     - Unusual Whales options sweep feeds
5. **Strategy Traceability & Shadow Quant Backtest Feedback Loop** *(Closing the Missing Loop)*:
   - Implement `plugins/analyst_trader/strategy_logger.py` to persist all strategy executions and heatmap analyses to SQLite (`recorded_strategies` table).
   - Stamping every evaluated flow in `notable_flow` and `flow_candidate_analytics` with:
     - `strategy_name` (`"A+_DREAM_SETUP"`, `"GEX_GAMMA_SQUEEZE"`, `"EMA_STACK_BREAKOUT"`, `"INSTITUTIONAL_WHALE_SWEEP"`)
     - `strategy_trace_id`
     - `quant_metrics_json` ($P(\text{Bullish})$, $P(\text{touch 3d})$, target node, Brier score, OFI score, DREAM checklist score, GEX regime).
   - Integrate with `candidate_correlation_engine.py` so the nightly learning flywheel and backtester audit performance, win rate, and MFE by strategy type, validating the Shadow Quant's touch predictions against observed market outcomes.

---

## 2. Component Architecture & Detailed Specifications

### A. Live Quotes Engine (`plugins/analyst_trader/finviz_fetcher.py` & `hermes_cli/web_server.py`)

#### `FinvizFetcher.fetch_live_quotes(tickers: List[str]) -> Dict[str, Dict[str, Any]]`
- Queries CBOE delayed options/underlying quote endpoint `https://cdn.cboe.com/api/global/delayed_quotes/options/{ticker}.json`.
- Returns dictionary mapping ticker to:
  ```json
  {
    "price": 762.81,
    "change_pct": 0.03,
    "is_extended_hours": true
  }
  ```
- Employs an in-memory TTL cache (60 seconds) to avoid redundant HTTP requests during frontend re-renders.

#### `web_server.py`: `GET /api/analyst-trader/live-quotes`
```python
@app.get("/api/analyst-trader/live-quotes")
async def api_analyst_trader_live_quotes(tickers: str = "", live: bool = False):
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if not live:
        # Strict offline test / mock fallback preserving test_live_quotes_truthfulness
        return {"ok": True, "quotes": {t: {"price": 0, "change_pct": 0} for t in ticker_list}}
    
    quotes = finviz_fetcher.fetch_live_quotes(ticker_list)
    return {"ok": True, "quotes": quotes}
```

#### `web/src/lib/api.ts`:
- Update `getLiveQuotes` to query `/api/analyst-trader/live-quotes?tickers=...&live=true`, enabling the frontend flow table to display real prices and extended-hours badges.

---

### B. Dynamic Realistic TP1/TP2 & Risk Engine (`skills/financial/autonomous-trader/scripts/autonomous_risk_manager.py`)

1. **Greek & DTE Mathematical Calibration**:
   - **Stop Loss**: 
     - Swing / Deep ITM / $>30$ DTE: -20% stop loss.
     - OTM / Short DTE: -25% stop loss.
   - **TP1 (1:1 to 1.25:1 R:R)**:
     - Conservative / Deep ITM ($\Delta \ge 0.60$) or $>30$ DTE: **+20% to +25%**.
     - Momentum / OTM / $<30$ DTE: **+25% to +30%**.
     - Ensures the initial tranche de-risks the position and covers the entire capital outlay.
   - **TP2 (2:1 to 2.5:1 R:R)**:
     - GEX Magnet Node Target: **+45% to +60%**.
2. **Account Tier Contract Execution**:
   - **Micro (<$1k)**: 1 contract. Full exit or trailing stop at TP1 (+20% to +25%).
   - **Growing ($1k-$5k)**: 2 contracts. Trim 1 at TP1 (+20% to +25%), trail 1 to TP2 (+45% to +50%).
   - **Established ($5k+)**: 3–5 contracts. Trim 2 at TP1 (+20% to +25%), trim 1–2 at TP2, trail remaining runners.
3. **Real-Time Monitoring Threshold**:
   - Update `monitor_open_positions_and_manage_risk` so `WIN_TP1` alert fires at `pnl_pct >= 20.0` (or `25.0`), notifying Discord and Telegram immediately.

---

### C. Whale Ingestion Criteria Engine (`skills/financial/autonomous-trader/scripts/whale_filter_criteria.py`)

1. **Whale Qualification Scoring Matrix (0–100 pts)**:
   - **Premium Tier (30 pts)**:
     - Mega-Cap / ETF: $\ge \$1\text{M}$ (25 pts), $\ge \$3\text{M}$ (30 pts).
     - Mid-Cap / Equity: $\ge \$200\text{k}$ (20 pts), $\ge \$500\text{k}$ (25 pts), $\ge \$1\text{M}$ (30 pts).
   - **Volume / Open Interest Aggression (25 pts)**:
     - Vol/OI $\ge 5.0\times$ (25 pts), $\ge 2.5\times$ (20 pts), $\ge 1.5\times$ (15 pts).
   - **Execution Urgency (20 pts)**:
     - Multi-exchange Sweep hitting the Ask or Above Mid (20 pts) vs Split/Floor (10 pts).
   - **Expiration Runway (15 pts)**:
     - 20–60 DTE sweet spot (15 pts), 14–20 DTE (10 pts), 60–120 DTE (12 pts).
   - **Technical Confluence Stack (Bonus / Penalty $\pm 15$ pts)**:
     - `FULL_BULLISH_STACK` or `BULLISH_8_21_CROSS`: +10 pts.
     - RVOL $\ge 1.5\times$ or Intraday Volume $>1\text{M}$: +5 pts.
     - Calls trapped below 200 EMA: -12 pts penalty.
     - Puts below 200 EMA with bearish cross: +10 pts.
   - **GEX / VEX Regime ($\pm 6$ pts)**:
     - Negative GEX volatility squeeze runway: +6 pts.
   - **Multi-Whale Accumulation Memory (+15 pts)**:
     - Detects if 2+ distinct sweeps accumulated this contract/ticker in the last 48 hours.
2. **Threshold Gate**:
   - `FlowScore >= 75.0`: **QUALIFIED WHALE** $\rightarrow$ Dispatches autonomous dual-card alert.
   - `FlowScore < 75.0`: Ingested into database for tracking/analytics but suppressed from broadcasting noisy alerts.

---

### D. Multi-Source Ingress Pipeline Expansion (`skills/financial/autonomous-trader/scripts/flow_ingestion_engine.py`)

- Expand `FlowIngestionEngine`:
  - Discord Notable Flow channels.
  - Skylit Flowseeker tape ingestion (`ingest_skylit_live_tape`).
  - Unusual Whales option sweep ingestion (`ingest_unusual_whales_tape`).
  - Route all ingested flows through `WhaleFilterEngine` and `AutonomousRiskManager`.

---

### E. Strategy Traceability, Strategy Logger & Backtest Calibration Loop (`plugins/analyst_trader/strategy_logger.py`, `plugins/analyst_trader/db.py`, `skills/financial/autonomous-trader/scripts/candidate_correlation_engine.py`)

1. **`strategy_logger.py` Implementation**:
   - Create `plugins/analyst_trader/strategy_logger.py` exporting `log_event(event_type: str, payload: dict, source: str = '') -> None`.
   - Records strategy executions and heatmap runner events to `recorded_strategies` table in `analyst_trading.db`.
   - Schema:
     ```sql
     CREATE TABLE IF NOT EXISTS recorded_strategies (
         trace_id TEXT PRIMARY KEY,
         event_type TEXT NOT NULL,
         strategy_name TEXT NOT NULL,
         ticker TEXT NOT NULL,
         action TEXT NOT NULL,
         status TEXT NOT NULL,
         directional_bias TEXT,
         target_node REAL,
         touch_prob_3d REAL,
         quant_metrics_json TEXT,
         screenshot_path TEXT,
         source_script TEXT,
         timestamp TEXT NOT NULL
     );
     ```
2. **Shadow Quant Strategy Trace Stamping**:
   - In `autonomous_risk_manager.py`: When `evaluate_candidate_end_to_end` runs `DynamicShadowQuantEngine`, stamp the flow record with:
     - `strategy_name`: Derived from the dominant factor (`"A+_DREAM_SETUP"`, `"GEX_GAMMA_SQUEEZE"`, `"EMA_STACK_BREAKOUT"`, `"INSTITUTIONAL_WHALE_SWEEP"`).
     - `strategy_trace_id`: Unique trace ID.
     - `quant_metrics_json`: Full snapshot containing $P(\text{Bullish})$, $P(\text{touch 3d})$, target node, Brier score, OFI score, DREAM checklist score, GEX regime.
     - Log through `strategy_logger.log_event(...)`.
3. **Backtester & Correlation Flywheel Integration**:
   - In `candidate_correlation_engine.py`:
     - Cross-reference `recorded_strategies` and `quant_metrics_json` during nightly audits.
     - Audit performance by strategy: Win rate, average ROI %, MFE/MAE excursions.
     - Brier calibration audit: Compare predicted 3-day touch probabilities against actual price excursion to target magnet nodes.

---

## 3. Verification Plan

### Automated Regression & New Feature Tests:
1. Run complete existing regression suite:
   ```bash
   venv/bin/pytest tests/test_owlfred_multi_confluence_dispatch.py tests/test_analyst_attribution_learning_flywheel.py tests/test_reconciled_checkout_verification.py -v
   ```
   *Expected: All 21 tests pass 100% green.*
2. Create and run `tests/test_phase4_whale_ingestion_criteria.py`:
   - Verify live quotes endpoint returns real CBOE quotes with `live=true` and mock zeroes with `live=false`.
   - Verify `WhaleFilterEngine` accurately scores whale flow, applies EMA(8, 21, 50, 100, 200) filters, detects 200 EMA traps, and credits multi-whale accumulation.
   - Verify dynamic TP1/TP2 setpoint calculations adhere to realistic +20% to +25% parameters.
   - Verify `strategy_logger` records events to `recorded_strategies` and stamps `notable_flow` and `flow_candidate_analytics`.
   - Verify the backtester / correlation flywheel evaluates strategy win rates and Brier touch calibration.
3. Static type and syntax check:
   ```bash
   pyrefly check skills/financial/autonomous-trader/scripts/flow_ingestion_engine.py skills/financial/autonomous-trader/scripts/autonomous_risk_manager.py hermes_cli/web_server.py plugins/analyst_trader/strategy_logger.py
   ```
