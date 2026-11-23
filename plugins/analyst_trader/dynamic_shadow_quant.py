#!/usr/bin/env python3
"""
dynamic_shadow_quant.py - Dynamic Shadow Quant Directional Alpha & Backtest Engine.

Integrates:
  1. Finviz & Market Data Fetcher (Price, Moving Averages, Rel Vol, Short Float, Insider Buys)
  2. Databento L2 Order Flow Imbalance (OFI) & Hawkes Metaorder Intensity (λ_t)
  3. Directional Alpha v0.1 Probability Engine (GEX-Free Core Signal Alignment)
  4. Skylit GEX / VEX Downstream Overlay (Gamma Magnet Nodes, Squeeze Multipliers)
  5. 5-Factor DREAM Setup Hurdle Validation (OFI, GEX, TTM/EMA, Macro/Micro, Social)
  6. Risk & Position Sizing Agent (ATR Stop, Take Profit, Max Position Dollar Risk)
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from plugins.analyst_trader.finviz_fetcher import FinvizFetcher
from plugins.analyst_trader.databento_ofi_engine import DatabentoOFIEngine
from plugins.analyst_trader.directional_alpha import DirectionalAlphaEngine
from plugins.analyst_trader.gex_downstream_overlay import GEXDownstreamOverlay
from plugins.analyst_trader.execution_orchestrator import ExecutionOrchestrator
from plugins.analyst_trader.risk_agent import RiskManagementAgent
from plugins.analyst_trader.position_agent import PositionSizingAgent
from plugins.analyst_trader.quant_storage_cache import QuantStorageCache
from plugins.analyst_trader.quant_storage_cache import observed_l2
from hermes_constants import get_hermes_home

logger = logging.getLogger("DynamicShadowQuant")


class DynamicShadowQuantEngine:
    """Production Dynamic Shadow Quant Engine supporting arbitrary tickers with 1 TB HD caching."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(get_hermes_home() / 'data/analyst_trading.db')
        self.fetcher = FinvizFetcher()
        self.ofi_engine = DatabentoOFIEngine()
        self.alpha_engine = DirectionalAlphaEngine()
        self.overlay_engine = GEXDownstreamOverlay()
        self.orchestrator = ExecutionOrchestrator()
        self.risk_agent = RiskManagementAgent()
        self.position_agent = PositionSizingAgent()
        self.cache = QuantStorageCache()

    def evaluate_ticker_complete_quant(
        self,
        ticker: str,
        force_refresh: bool = False,
        spot_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Executes the quantitative alpha, dream checklist, risk, and positioning pipeline.
        Implements 2-Tier Caching (120s L2 vs 24h Static) & Databento API cost throttling (max 3/session).
        """
        ticker = ticker.upper().strip()

        # 0. Check Two-Tier NVMe Storage Cache
        cached_profile, is_micro_valid = self.cache.get_cached_profile(
            ticker, microstructure_ttl_seconds=120.0, static_ttl_hours=24.0
        )
        # Recompute derived output on cache hits; old actionable flags cannot
        # bypass evidence checks or an explicit invalid price override.
        is_micro_valid = bool(is_micro_valid and cached_profile and observed_l2(cached_profile.get('ofi_metrics'), ticker))

        logger.info("Evaluating Dynamic Shadow Quant for $%s (Micro Valid: %s)...", ticker, is_micro_valid)

        # Stage 1: Fetch Market & Technical Data
        market_data = (cached_profile.get("market_data") if (cached_profile and not force_refresh)
                       else self.fetcher.fetch_ticker_metrics(ticker))
        
        market_data = dict(market_data) if isinstance(market_data, dict) else {}
        # An explicit invalid quote must not silently fall back to another price.
        current_price = spot_price if spot_price is not None else market_data.get("current_price", market_data.get("price"))
        import math
        try:
            valid_price = not isinstance(current_price, bool) and math.isfinite(float(current_price)) and float(current_price) > 0
        except (TypeError, ValueError, OverflowError):
            valid_price = False
        if not valid_price:
            return {
                "ticker": ticker, "current_price": None, "market_data": market_data,
                "fail_closed_status": "FAIL_CLOSED_INVALID_PRICE",
                "is_actionable_alert_ready": False, "is_a_plus_dream_setup": False,
            }
        market_data["current_price"] = current_price

        # Stage 2: Cost-Throttled Databento L2 OFI & Hawkes Intensity Query
        can_query = self.cache.can_query_databento_l2(ticker, max_session_evals=3)
        should_query_l2 = can_query and (force_refresh or not is_micro_valid)
        
        fail_closed_status = None
        if should_query_l2:
            logger.info("📡 Querying Databento L2 Order Book & OFI for $%s...", ticker)
            if self.cache.reserve_l2_query(ticker, max_session_evals=3):
                try:
                    ofi_metrics = self.ofi_engine.compute_l2_ofi_metrics(ticker, market_data)
                except Exception:
                    ofi_metrics = {}
            else:
                ofi_metrics = {}
                fail_closed_status = 'FAIL_CLOSED_BUDGET_EXHAUSTED'
        elif cached_profile and is_micro_valid:
            logger.info("Using fresh cached L2 OFI metrics for $%s.", ticker)
            ofi_metrics = cached_profile.get("ofi_metrics", {})
        elif cached_profile and not can_query:
            logger.warning("Session evaluation limit (3) reached for $%s. Marking DATA_STALE/BUDGET_EXHAUSTED.", ticker)
            ofi_metrics = cached_profile.get("ofi_metrics", {})
            fail_closed_status = "FAIL_CLOSED_BUDGET_EXHAUSTED"
        else:
            logger.warning("No microstructure data available and budget reached for $%s.", ticker)
            ofi_metrics = {}
            fail_closed_status = "FAIL_CLOSED_DATA_UNAVAILABLE"

        # A query attempt is not a successful observation. Empty results must
        # not renew the L2 cache timestamp or produce actionable output.
        if not observed_l2(ofi_metrics, ticker):
            ofi_metrics = {}
            should_query_l2 = False
            fail_closed_status = fail_closed_status or "FAIL_CLOSED_DATA_UNAVAILABLE"

        # Stage 3: Calculate 100% GEX-Free Core Directional Probability
        alpha_output = self.alpha_engine.calculate_directional_probability(ofi_metrics, market_data)

        # Stage 4: Apply Skylit GEX Downstream Overlay & Volatility Friction
        overlay_output = self.overlay_engine.apply_overlay_and_friction(alpha_output, market_data)

        # Stage 5: Evaluate 5-Factor DREAM Setup Checklist (with Hard Directional Alpha Veto)
        # Only supplied evidence may enter the checklist; missing is unknown.
        ta_info = market_data.get("ta_info") or {}
        event_info = market_data.get("event_info") or {}

        dream_setup = self.orchestrator.evaluate_dream_setup(
            ticker=ticker,
            price=current_price,
            ofi_info=ofi_metrics,
            alpha_info=alpha_output,
            gex_info=overlay_output,
            ta_info=ta_info,
            event_info=event_info
        )

        # Stage 6: Compute Risk Bounds & 3-Tier Position Sizing
        target_node = alpha_output.get("target_node")
        atr = market_data.get("atr")
        directional_bias = alpha_output.get("directional_bias")
        risk_info = {}
        position_options = []
        if atr is not None and target_node is not None and directional_bias is not None:
            risk_info = self.risk_agent.calculate_risk_parameters(
                ticker=ticker, current_price=current_price, target_node=target_node,
                directional_bias=directional_bias, atr=atr,
            )
            position_options = self.position_agent.generate_position_options(
                ticker=ticker, current_price=current_price, target_node=target_node,
                risk_info=risk_info,
            )
        else:
            fail_closed_status = fail_closed_status or "FAIL_CLOSED_RISK_DATA_UNAVAILABLE"

        # Compile Comprehensive Quant Package
        quant_result = {
            "ticker": ticker,
            "current_price": current_price,
            "market_data": market_data,
            "ofi_metrics": ofi_metrics,
            "directional_alpha": alpha_output,
            "gex_overlay": overlay_output,
            "dream_setup": dream_setup,
            "risk_parameters": risk_info,
            "position_sizing_options": position_options,
            "fail_closed_status": fail_closed_status,
            "is_a_plus_dream_setup": (fail_closed_status is None) and (dream_setup.get("setup_grade") == "A+ DREAM SETUP"),
            "is_actionable_alert_ready": (
                (fail_closed_status is None) and
                dream_setup.get("hurdle_passed", False) and
                dream_setup.get("conviction_score", 0.0) >= 75.0 and
                alpha_output.get("touch_prob_3d", 0.0) >= 0.50
            )
        }

        # Persist to 1 TB HD Cache
        try:
            self.cache.save_quant_profile(ticker, quant_result, is_l2_fresh=should_query_l2)
        except Exception as c_err:
            logger.debug("Failed to cache profile for %s: %s", ticker, c_err)

        return quant_result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    test_ticker = sys.argv[1].upper() if len(sys.argv) > 1 else "METC"
    engine = DynamicShadowQuantEngine()
    result = engine.evaluate_ticker_complete_quant(test_ticker)
    
    print(f"\n==================================================")
    print(f"🎯 SHADOW QUANT & 5-FACTOR DREAM RESULT: {test_ticker}")
    print(f"==================================================")
    print(f"Current Price:           ${result['current_price']:.2f}")
    print(f"Directional Probability: {result['directional_alpha']['p_bullish']*100:.1f}% ({result['directional_alpha']['directional_bias']})")
    print(f"Target Magnet Node:      ${result['directional_alpha']['target_node']:.2f}")
    print(f"3-Day Touch Probability: {result['directional_alpha']['touch_prob_3d']*100:.1f}%")
    print(f"Brier Calibration Score: {result['directional_alpha']['brier_score']:.4f} (Calibrated: {result['directional_alpha']['is_calibrated']})")
    print(f"--------------------------------------------------")
    print(f"DREAM Setup Grade:       {result['dream_setup']['setup_grade']} ({result['dream_setup']['conviction_score']}%)")
    print(f"Checklist Passed:        {result['dream_setup']['checklist_passed_count']}/{result['dream_setup']['checklist_total']} Factors Met")
    print(f"A+ Dream Setup:          {'✅ YES' if result['is_a_plus_dream_setup'] else '❌ NO'}")
    print(f"Actionable Alert Ready:  {'🔥 ESCALATE TO #OWLFRED-ALERTS' if result['is_actionable_alert_ready'] else '📊 WATCHLIST ONLY'}")
    print(f"==================================================\n")
