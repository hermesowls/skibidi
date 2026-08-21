---
name: quant-shadow-tracking
description: Use when running Quant Shadow Tracking for a ticker.
version: 1.0.0
author: Skibidi / Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [trading, quant, shadow-tracking, directional-alpha, backtest, brier]
    related_skills: [strategy-backtester, financial-market-data, skylit-atlas]
---

# Quant Shadow Tracking

## Overview

Use this skill when Amar gives a ticker and wants the Quant Shadow Tracking process run end-to-end: directional-alpha backtest/signal run, bullish probability, target node, Brier calibration value, 3D touch probability, and expected time till touch.

The current capability lives in the Hermes repo under:

- `/Users/admin/repos/hermes-agent/plugins/analyst_trader/directional_alpha.py`
- `/Users/admin/repos/hermes-agent/plugins/analyst_trader/finviz_fetcher.py`
- `/Users/admin/repos/hermes-agent/plugins/analyst_trader/databento_ofi_engine.py`
- `/Users/admin/repos/hermes-agent/plugins/analyst_trader/gex_downstream_overlay.py`
- `/Users/admin/repos/hermes-agent/hermes_cli/web_server.py` endpoints `/api/quant/signal-matrix` and `/api/quant/shadow-tracking`

The core model is **Directional Alpha v0.1**, a 100% GEX-free probability engine using Finviz/Yahoo market data, OFI proxy, Hawkes intensity, queue depletion velocity, relative volume, short-float squeeze risk, VWAP momentum, and Amihud illiquidity. GEX is applied downstream as an execution overlay only.

## When to Use

Use this skill when the user asks to:

- Run quant shadow tracking for a ticker.
- Get bullish %, target node, Brier score/value, 3D probability, and time till touch.
- Compare discretionary bias against model bias.
- Add a ticker to the Quant Signal Matrix / Shadow Tracker workflow.
- Produce a concise quant card from the Directional Alpha engine.

Do not use this skill for live or paper trading execution. This is signal/shadow tracking and calibration, not order placement.

## Required Runtime

Run from the Hermes repo venv because the default system Python may not have `requests` installed.

```bash
cd /Users/admin/repos/hermes-agent
PYTHONPATH=/Users/admin/repos/hermes-agent /Users/admin/repos/hermes-agent/venv/bin/python <script>
```

If the venv path fails, inspect available Python envs before installing anything. Do not expose API keys. Databento key is read from env or `~/.hermes/.env` by the OFI engine when available; the current implementation can still run via proxy estimates without directly printing secrets.

## One-Ticker Runner

Preferred command after this skill is installed:

```bash
PYTHONPATH=/Users/admin/repos/hermes-agent /Users/admin/repos/hermes-agent/venv/bin/python /Users/admin/.hermes/skills/financial/quant-shadow-tracking/scripts/run_quant_shadow.py AAPL
```

If the script is missing, use this fallback one-liner pattern from repo root:

```bash
PYTHONPATH=/Users/admin/repos/hermes-agent /Users/admin/repos/hermes-agent/venv/bin/python - <<'PY'
import json, sys
from plugins.analyst_trader.finviz_fetcher import FinvizFetcher
from plugins.analyst_trader.databento_ofi_engine import DatabentoOFIEngine
from plugins.analyst_trader.directional_alpha import DirectionalAlphaEngine
from plugins.analyst_trader.gex_downstream_overlay import GEXDownstreamOverlay

ticker = (sys.argv[1] if len(sys.argv) > 1 else "AAPL").upper()
fetcher = FinvizFetcher()
ofi_engine = DatabentoOFIEngine()
alpha_engine = DirectionalAlphaEngine()
overlay_engine = GEXDownstreamOverlay()
md = fetcher.fetch_ticker_metrics(ticker)
ofi = ofi_engine.compute_l2_ofi_metrics(ticker, md)
alpha = alpha_engine.calculate_directional_probability(ofi, md)
final = overlay_engine.apply_overlay_and_friction(alpha, md)
print(json.dumps(final, indent=2))
PY
```

## Output Contract

Always return these core fields to Amar:

**Ticker**: symbol analyzed.
**Current Price**: `current_price`.
**Model Bias**: `directional_bias` and `execution_bias`.
**Bullish %**: `p_bullish * 100`.
**Target Node**: `target_node`.
**3D Touch Probability**: `touch_prob_3d * 100`.
**Time Till Touch**: `expected_arrival_display` or `expected_arrival_hours`.
**Brier Value**: `brier_score`.
**Calibration**: `is_calibrated` using target max Brier 0.18.
**Primary Driver**: `primary_driver`.
**GEX Overlay**: `gex_regime`, `gex_vol_multiplier`, `execution_bias`.
**Microstructure Inputs**: `ofi_score`, `hawkes_intensity`, `bid_ask_spread`, `friction_cost` when present.

## Card Format

Use this concise card format in chat:

```markdown
**Quant Shadow — TICKER**
**Price**: $...
**Model Bias**: Bullish/Bearish/Neutral — EXECUTION_BIAS
**Bullish %**: ...%
**Target Node**: $...
**3D Touch Probability**: ...%
**Time Till Touch**: ...
**Brier Value**: ... — Calibrated/Not calibrated
**Primary Driver**: ...
**GEX Overlay**: ...
**Read**: hold/reclaim X → target Y; lose X → invalidation/downside Z
```

Do not use bullets inside this card if the user is asking for a clean trading read; use bold line labels.

## Interpretation Rules

- `p_bullish >= 0.75`: aggressive bullish if execution overlay also supports it.
- `p_bullish >= 0.60`: bullish/grinding drift.
- `0.45 < p_bullish < 0.60`: neutral/grind unless target-touch probability is unusually high.
- `p_bullish <= 0.35`: bearish/fade.
- `brier_score <= 0.18`: calibrated enough for shadow tracking.
- `touch_prob_3d >= 0.55`: target-touch probability is strong.
- `touch_prob_3d < 0.30`: target may be valid but timing confidence is weak.

## Backtest / Shadow Tracking Language

The current engine returns a calibrated directional shadow signal and first-passage/touch probability. If the user asks for a “backtest,” report it as a **Quant Shadow signal/backtest run** unless a historical labeled-trades backtest has actually been run. Do not imply full P/L strategy validation unless `strategy-backtester` was used with a historical trades ledger.

If historical validation is requested, chain into `strategy-backtester` and produce separate metrics like win rate, expectancy, profit factor, and drawdown. Keep those separate from this skill’s Brier/touch-probability outputs.

## Verification Checklist

Before final response:

- [ ] The command actually ran with the Hermes repo venv.
- [ ] Ticker in output matches requested ticker.
- [ ] Bullish %, target node, Brier value, 3D touch probability, and time till touch are present.
- [ ] If any source failed, disclose the failed source and whether fallback/proxy fields were used.
- [ ] No secrets/API keys printed.
- [ ] If presenting as “backtest,” clarify whether this was the quant shadow signal run or a full historical P/L backtest.

## Common Pitfalls

1. **Wrong Python**: default `python3` may lack `requests`; use `/Users/admin/repos/hermes-agent/venv/bin/python`.
2. **Overclaiming backtest**: the signal engine is not a full P/L backtest by itself.
3. **Missing Finviz fields**: if Finviz parsing fails, Yahoo fallback can still supply price/change; mark missing rel-vol/ATR fields if they remain defaults.
4. **Secrets leakage**: never print `DATABENTO_API_KEY` or `.env` contents.
5. **Dashboard endpoint dependency**: direct Python runner is more reliable than requiring the web dashboard server to be running.
