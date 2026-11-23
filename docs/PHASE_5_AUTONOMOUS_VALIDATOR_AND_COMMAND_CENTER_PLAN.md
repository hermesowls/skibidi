# Phase 5 Implementation Plan: Autonomous Strategy Validator & Trading Command Center

## Executive Summary
This implementation plan operationalizes the unified trading vision:
1. **User-Facing Alerts as the Product**: High-conviction dual-card alerts (Telegram + Discord) with canonical OCC option symbols, realistic Greek/GEX-calibrated TP1 (+20% to +25%) and TP2 (+45% to +60%), stop loss (-20% to -25%), tiered account sizing (Micro, Growing, Established), and multi-factor confluence thesis.
2. **Autonomous Paper Trading as Strategy Validator**: Automated shadow order execution into Portfolio B (`autonomous_ai`) whenever a qualified whale alert ($\ge 80$ score) is published. Real-time tick-by-tick monitoring trims 50% at TP1, moves stops to breakeven, exits at TP2 / SL, records realized returns, and continuously validates strategy performance.
3. **Autonomous Portfolio Management & Robinhood-Ready Architecture**: Modular `ExecutionBroker` interface with `PaperExecutionBroker` (active now) and `RobinhoodExecutionBroker` (ready for live broker credentials), turning the validated strategy engine into an autonomous trading agent.
4. **Dashboard Integration (Strictly Non-Destructive)**: Retains all 17 existing Hermes dashboard tabs intact. Routes `NotableFlowPage` to `/flow` ("Whale Flow" in sidebar) and adds a view switcher (`[🌊 Whale Flow Tape] | [🤖 Strategy Validator (Paper Portfolio)] | [📊 Strategy Alpha & Learnings]`) preserving 100% of existing table, filter, and chart features while providing complete visibility into paper portfolio positions and strategy validation.

---

## User Review & Invariants

> [!IMPORTANT]
> **Dashboard Non-Destructive Invariant**: Zero existing dashboard tabs (Sessions, Files, Analytics, Models, Logs, Cron, Skills, Plugins, MCP, Channels, Webhooks, Pairing, Profiles, Config, Keys, System, Docs, Chat) are overwritten or altered. `NotableFlowPage` is mounted at `/flow` ("Whale Flow") with an internal segmented view switcher that keeps the entire flow tape untouched while surfacing the paper validator.

> [!TIP]
> **Realistic Dynamic TP1/TP2 Calibration**: In line with user feedback, TP1 is strictly locked to **+20% to +25%** (1:1 to 1.25:1 R:R against 20-25% SL), retiring any legacy 45%+ base requirements. TP2 is set to **+45% to +60%** for runners.

---

## Proposed Changes

### Component 1: Database Migration & Holdings Lifecycle (`plugins/analyst_trader/db.py`)
- **[MODIFY] [db.py](file:///Users/admin/repos/hermes-agent/plugins/analyst_trader/db.py)**:
  - Add schema migration for `portfolio_holdings` to add missing lifecycle columns if absent:
    - `status TEXT DEFAULT 'OPEN'` (`OPEN`, `TRIMMED`, `CLOSED`)
    - `realized_pnl REAL DEFAULT 0.0`
    - `closed_at TEXT`
    - `strategy_name TEXT`
    - `target_tp1 REAL`
    - `target_tp2 REAL`
    - `target_sl REAL`
    - `flow_id TEXT`
    - `occ_symbol TEXT`
    - `contracts_trimmed REAL DEFAULT 0.0`
  - Enhance `add_portfolio_holding()` to accept the strategy metadata and targets.
  - Implement `trim_portfolio_holding(holding_id, trim_qty, price, realized_pnl, new_sl)`.
  - Implement `close_portfolio_holding(holding_id, price, realized_pnl, outcome_label)`.
  - Update `list_portfolio_holdings(portfolio_id, status=None)` to filter by lifecycle status.
  - Implement `get_portfolio_stats(portfolio_id)` to aggregate total portfolio value, cash, open count, realized P&L, and win rate.

---

### Component 2: Dual Portfolio Execution Engine & Broker Abstraction (`plugins/analyst_trader/portfolio_engine.py`)
- **[MODIFY] [portfolio_engine.py](file:///Users/admin/repos/hermes-agent/plugins/analyst_trader/portfolio_engine.py)**:
  - Replace the `PermissionError('UNQUALIFIED_AUTONOMOUS_STRATEGY')` prototype stub.
  - Define `ExecutionBroker` interface and `PaperExecutionBroker` implementation:
    ```python
    class ExecutionBroker(ABC):
        @abstractmethod
        def submit_order(self, order: Dict[str, Any]) -> Dict[str, Any]: ...
        @abstractmethod
        def cancel_order(self, order_id: str) -> bool: ...
        @abstractmethod
        def get_positions(self) -> List[Dict[str, Any]]: ...
    ```
  - Implement `RobinhoodExecutionBroker` stub ready for API credentials / session tokens.
  - Implement `DualPortfolioEngine.execute_autonomous_trade(recommendation, account_tier="growing")`:
    - Integer contract sizing: Micro (<$1k: 1 con if $\le \$200$), Growing ($1k-$5k: 2-3 cons), Established ($5k+: 3-5 cons).
    - Uses real CBOE / market option entry price.
    - Decrements cash balance in Portfolio B (`autonomous_ai`), adds holding record with target TP1, TP2, SL, and strategy name.
    - Emits execution event to `strategy_logger`.
  - Implement `execute_autonomous_trim(holding_id, current_price, trim_pct=0.5)`:
    - Trims 50% of contracts at TP1 (+20% to +25%).
    - Credits cash with trade revenue, records partial realized P&L.
    - Moves stop loss on remaining contracts to entry price (breakeven!).
    - Sets holding status to `'TRIMMED'`.
  - Implement `execute_autonomous_exit(holding_id, current_price, outcome_label)`:
    - Closes remaining contracts at TP2 (+45% to +60%) or Stop Loss (-20% to -25%).
    - Credits cash, finalizes realized P&L, sets status to `'CLOSED'`.
    - Persists closed trade analytics to `recorded_strategies`.
  - Upgrade `get_portfolio_summary()` to return live cash, total portfolio value (cash + open holdings mark-to-market), and active position metrics.

---

### Component 3: Closed-Loop Validator Wiring in Risk Manager (`skills/financial/autonomous-trader/scripts/autonomous_risk_manager.py`)
- **[MODIFY] [autonomous_risk_manager.py](file:///Users/admin/repos/hermes-agent/skills/financial/autonomous-trader/scripts/autonomous_risk_manager.py)**:
  - In `evaluate_candidate_end_to_end`:
    - When an actionable alert is published (`is_dream_setup` / conviction $\ge 80$), immediately trigger `DualPortfolioEngine.execute_autonomous_trade(rec, account_tier="growing")`.
    - This launches the paper position as the objective validator of the alert.
  - In `calculate_dynamic_tp_setpoints`:
    - Ensure TP1 defaults strictly to **+20% to +25%** and TP2 defaults to **+45% to +60%**.
  - In `monitor_and_update_positions`:
    - When `WIN_TP1` is hit (+20% to +25%):
      - In addition to updating `notable_flow` and sending Telegram/Discord trim alert, trigger `DualPortfolioEngine.execute_autonomous_trim(holding_id, executable_bid)`.
    - When `WIN_TP2` or `LOSS_STOP_HIT` is hit:
      - Trigger `DualPortfolioEngine.execute_autonomous_exit(holding_id, executable_bid, outcome)`.
      - Record closed trade metrics into `recorded_strategies` with realized P&L, MFE, MAE, and duration.

---

### Component 4: REST API Endpoints (`hermes_cli/web_server.py`)
- **[MODIFY] [web_server.py](file:///Users/admin/repos/hermes-agent/hermes_cli/web_server.py)**:
  - Add `GET /api/analyst-trader/portfolio`: returns Portfolio A (`copy_trader`) and Portfolio B (`autonomous_ai`) summary, balances, and P&L.
  - Add `GET /api/analyst-trader/portfolio-holdings`: returns holdings for a portfolio (`portfolio_id=autonomous_ai`), supporting filter by `status=OPEN|TRIMMED|CLOSED`, enriched with current market prices and unrealized P&L %.
  - Add `GET /api/analyst-trader/strategies`: returns strategy performance breakdown from `recorded_strategies` (win rate %, average return, total trades) for the Strategy Validator tab.

---

### Component 5: Web UI API & Non-Destructive Command Center (`web/src/lib/api.ts`, `web/src/App.tsx`, `web/src/pages/NotableFlowPage.tsx`)
- **[MODIFY] [api.ts](file:///Users/admin/repos/hermes-agent/web/src/lib/api.ts)**:
  - Add `getPortfolioSummary()`, `getPortfolioHoldings()`, and `getRecordedStrategies()`.
- **[MODIFY] [App.tsx](file:///Users/admin/repos/hermes-agent/web/src/App.tsx)**:
  - Add `const NotableFlowPage = lazy(() => import("@/pages/NotableFlowPage"));`
  - Add `/flow`: `NotableFlowPage` to `BUILTIN_ROUTES_CORE`.
  - Add `{ path: "/flow", label: "Whale Flow", icon: Radio }` to `BUILTIN_NAV_REST` (after `/analytics`).
  - Strict preservation: All existing routes and tabs remain untouched.
- **[MODIFY] [NotableFlowPage.tsx](file:///Users/admin/repos/hermes-agent/web/src/pages/NotableFlowPage.tsx)**:
  - Add top-level view selector:
    `[🌊 Whale Flow Tape] | [🤖 Strategy Validator (Paper Portfolio)] | [📊 Strategy Alpha & Learnings]`
  - View 1 (`Whale Flow Tape`): 100% existing functionality, tables, filters, live quotes, modal chart, and legend preserved.
  - View 2 (`Strategy Validator (Paper Portfolio)`):
    - Portfolio B KPI header (Total Value, Cash Balance, Realized P&L, Unrealized P&L, Active Validating Positions).
    - Live Open Holdings Table: Ticker, OCC Contract Symbol, Strategy Archetype, Contracts & Outlay, Entry Price, Live Price, Unrealized ROI %, TP1 (+20-25%), TP2 (+45-60%), Stop Loss, Status (`OPEN`, `TRIMMED`).
    - Closed Trade Journal: Historical paper trades verifying win/loss outcomes.
  - View 3 (`Strategy Alpha & Learnings`):
    - Strategy scorecard aggregating live performance by archetype (`A+_DREAM_SETUP`, `GEX_GAMMA_SQUEEZE`, `EMA_STACK_BREAKOUT`, `INSTITUTIONAL_WHALE_SWEEP`).

---

## Verification Plan

### Automated Tests
1. **Portfolio & Validator Test Suite (`tests/test_phase5_autonomous_validator.py`)**:
   - Test `DualPortfolioEngine.execute_autonomous_trade` integer sizing across Micro, Growing, and Established tiers.
   - Test partial trim at +20% to +25% TP1, realized P&L addition to cash, and stop movement to breakeven.
   - Test full exit at +50% TP2 and -20% Stop Loss, status update to `CLOSED`, and telemetry write to `recorded_strategies`.
   - Test broker interface abstraction (`PaperExecutionBroker` vs `RobinhoodExecutionBroker`).
   - Test `GET /api/analyst-trader/portfolio` and `GET /api/analyst-trader/portfolio-holdings`.
2. **Regression Verification**:
   - Run existing suite: `venv/bin/pytest tests/test_phase4_whale_ingestion_criteria.py tests/test_owlfred_multi_confluence_dispatch.py tests/test_analyst_attribution_learning_flywheel.py tests/test_reconciled_checkout_verification.py -v` (must remain 100% green).
3. **Frontend Compilation**:
   - Run `npm --prefix web run build` to guarantee zero TypeScript or bundle errors.
4. **Daemon Verification**:
   - Verify `owlfred_supervisor.py` runs with zero exceptions under active daemon.
