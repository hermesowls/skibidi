#!/usr/bin/env python3
"""Run Quant Shadow Tracking for one or more tickers.

Usage:
  PYTHONPATH=/Users/admin/repos/hermes-agent /Users/admin/repos/hermes-agent/venv/bin/python run_quant_shadow.py AAPL TSLA
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict

from plugins.analyst_trader.finviz_fetcher import FinvizFetcher
from plugins.analyst_trader.databento_ofi_engine import DatabentoOFIEngine
from plugins.analyst_trader.directional_alpha import DirectionalAlphaEngine
from plugins.analyst_trader.gex_downstream_overlay import GEXDownstreamOverlay

CORE_KEYS = [
    "ticker",
    "current_price",
    "directional_bias",
    "execution_bias",
    "p_bullish",
    "target_node",
    "touch_prob_3d",
    "expected_arrival_display",
    "expected_arrival_hours",
    "expected_calendar_hours",
    "brier_score",
    "is_calibrated",
    "primary_driver",
    "gex_regime",
    "gex_vol_multiplier",
    "ofi_score",
    "hawkes_intensity",
    "bid_ask_spread",
    "friction_cost",
    "friction_adjusted_price",
]


def run_one(ticker: str) -> Dict[str, Any]:
    ticker = ticker.strip().upper()
    fetcher = FinvizFetcher()
    ofi_engine = DatabentoOFIEngine()
    alpha_engine = DirectionalAlphaEngine()
    overlay_engine = GEXDownstreamOverlay()

    market_data = fetcher.fetch_ticker_metrics(ticker)
    ofi_info = ofi_engine.compute_l2_ofi_metrics(ticker, market_data)
    alpha = alpha_engine.calculate_directional_probability(ofi_info, market_data)
    final = overlay_engine.apply_overlay_and_friction(alpha, market_data)
    final["market_data"] = market_data
    return {k: final.get(k) for k in CORE_KEYS} | {"market_data": market_data}


def main() -> int:
    tickers = [t.upper() for t in sys.argv[1:] if t.strip()]
    if not tickers:
        print("Usage: run_quant_shadow.py TICKER [TICKER...]", file=sys.stderr)
        return 2
    results = [run_one(t) for t in tickers]
    print(json.dumps({"ok": True, "count": len(results), "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
