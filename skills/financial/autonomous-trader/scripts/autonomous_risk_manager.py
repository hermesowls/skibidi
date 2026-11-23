#!/usr/bin/env python3
"""
Autonomous Risk Manager & Trade Recommender Module — Modular 2-Card Flow.

Splits trade alerts into two dedicated, clean Discord cards:
  Card 1 (OPEN):
    - Author: OWLFRED
    - Contract & Entry Target
    - Institutional Thesis & Setup Confluence
    - Embedded Flowseeker Tape Chart
  Card 2 (RISK MANAGEMENT & SIZING):
    - Author: OWLFRED RISK MANAGER
    - Tiered Account Sizing (<$1k, $1k-$5k, $5k+)
    - Max Dollar Risk with -30% Hard Stop
    - Realistic Dynamic TP1 (+20% to +25%), TP2 (+45% to +60%), and Stop Loss (-20% to -25%) Targets
    - Tiered Contract-by-Contract Sizing (Micro, Growing, Established)
"""

import os
import sys
import json
import time
import threading
import sqlite3
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import Discord publisher & flow classifier
from discord_poster import DiscordPublisher  # type: ignore[import-not-found]
from flow_classifier import FlowClassifierEngine  # type: ignore[import-not-found]
from alert_card_generator import create_graphic_alert_card  # type: ignore[import-not-found]

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("autonomous_risk_manager")


def generate_occ_symbol(ticker: str, expiration_str: str, call_put: str, strike: float) -> str:
    """
    Generates canonical 21-character OCC Option Symbology (e.g. 'METC  260918C00012000').
    Format: TICKER (exactly 6 chars space-padded) + YYMMDD (6 chars) + C/P (1 char) + 8-digit price (strike * 1000).
    Total length: exactly 21 characters.
    """
    ticker_clean = ticker.upper().strip()[:6]
    cp = "C" if "C" in call_put.upper() else "P"
    
    # Parse expiration date
    try:
        if "/" in expiration_str:
            parts = expiration_str.split("/")
            m, d = int(parts[0]), int(parts[1])
            y = int(parts[2])
            if y < 100:
                y += 2000
            exp_date = datetime(y, m, d)
        elif "-" in expiration_str:
            exp_date = datetime.strptime(expiration_str, "%Y-%m-%d")
        else:
            exp_date = datetime.now(timezone.utc) + timedelta(days=30)
    except Exception:
        exp_date = datetime.now(timezone.utc) + timedelta(days=30)

    yymmdd = exp_date.strftime("%y%m%d")
    strike_int = round(strike * 1000)
    strike_str = f"{strike_int:08d}"
    return f"{ticker_clean:<6}{yymmdd}{cp}{strike_str}"


def get_contract_trim_schedule(quantity: int, tp1_pct: float, tp2_pct: float) -> Dict[str, Any]:
    """
    Explicit, unambiguous quantity-by-quantity trim and free-roll schedule.
    True free-roll occurs ONLY when cumulative revenue recovered >= 100% of initial outlay.
    """
    if quantity <= 1:
        return {
            "quantity": 1,
            "tp1_trim": 0,
            "action_at_tp1": "Full Exit (100%) or Trail Stop to Breakeven",
            "is_free_roll": False,
            "recovery_pct": 0.0,
            "summary": "1 con: Exit 100% at TP1 or Trail SL"
        }

    tp1_trim = 1 if quantity == 2 else (2 if quantity in (3, 4) else max(2, int(quantity * 0.60)))
    tp1_multiplier = 1.0 + (tp1_pct / 100.0)
    recovered_units = tp1_trim * tp1_multiplier
    recovery_pct = round((recovered_units / quantity) * 100.0, 1)
    is_free_roll = recovered_units >= quantity

    if quantity == 2:
        return {
            "quantity": 2,
            "tp1_trim": 1,
            "action_at_tp1": f"Trim 1 at TP1 (+{tp1_pct:.0f}%) [De-Risks {recovery_pct:.0f}%], Trail 1 to TP2",
            "is_free_roll": is_free_roll,
            "recovery_pct": recovery_pct,
            "summary": f"2 cons: Trim 1 at TP1 (+{tp1_pct:.0f}%), Trail 1"
        }
    elif quantity == 3:
        label = "True Free-Roll" if is_free_roll else f"Recovers {recovery_pct:.0f}%"
        return {
            "quantity": 3,
            "tp1_trim": 2,
            "action_at_tp1": f"Trim 2 at TP1 (+{tp1_pct:.0f}%) [{label}], Trail 1 Runner",
            "is_free_roll": is_free_roll,
            "recovery_pct": recovery_pct,
            "summary": f"3 cons: Trim 2 at TP1 (+{tp1_pct:.0f}%) [{label}], Trail 1"
        }
    elif quantity == 4:
        label = "True Free-Roll" if is_free_roll else f"Recovers {recovery_pct:.0f}%"
        return {
            "quantity": 4,
            "tp1_trim": 2,
            "action_at_tp1": f"Trim 2 at TP1 (+{tp1_pct:.0f}%), 1 at TP2 (+{tp2_pct:.0f}%), Trail 1 Runner",
            "is_free_roll": is_free_roll,
            "recovery_pct": recovery_pct,
            "summary": f"4 cons: Trim 2 at TP1, 1 at TP2, Trail 1"
        }
    else:
        label = "True Free-Roll" if is_free_roll else f"Recovers {recovery_pct:.0f}%"
        return {
            "quantity": quantity,
            "tp1_trim": tp1_trim,
            "action_at_tp1": f"Trim {tp1_trim} at TP1 (+{tp1_pct:.0f}%), Trail {quantity - tp1_trim} Runners",
            "is_free_roll": is_free_roll,
            "recovery_pct": recovery_pct,
            "summary": f"{quantity} cons: Trim {tp1_trim} at TP1, Trail {quantity - tp1_trim}"
        }


class AutonomousRiskManager:
    """Institutional Risk Manager, Dynamic Greek/GEX TP Calibration & Execution State Machine."""

    def __init__(self, db_path: Optional[str] = None, *, quote_reader=None, quote_max_age_seconds=None, clock=None,
                 delivery_transport=None, delivery_destinations=(), delivery_clock=None,
                 quant_engine=None, deep_dive_analyzer=None):
        self.delivery_transport = delivery_transport
        self.delivery_destinations = tuple(delivery_destinations)
        self.delivery_clock = delivery_clock or time.time
        self.quote_reader = quote_reader
        self.quote_max_age_seconds = quote_max_age_seconds
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        try:
            from plugins.analyst_trader.db import get_db_path
            self.db_path = db_path or str(get_db_path())
        except ImportError:
            self.db_path = db_path or str(Path.home() / ".hermes" / "analyst_trading.db")
        # Delivery configuration is explicit; construction never discovers
        # messaging credentials or instantiates the old retrying publisher.
        self.poster = None
        self.classifier = FlowClassifierEngine(self.db_path)
        
        try:
            from plugins.analyst_trader.dynamic_shadow_quant import DynamicShadowQuantEngine
            self.quant_engine = quant_engine if quant_engine is not None else DynamicShadowQuantEngine(self.db_path)
        except Exception as e:
            logger.warning("Could not initialize DynamicShadowQuantEngine: %s", e)
            self.quant_engine = None

        try:
            from llm_deep_dive_analyzer import LLMDeepDiveAnalyzer  # type: ignore[import-not-found]
            self.deep_dive_analyzer = deep_dive_analyzer if deep_dive_analyzer is not None else LLMDeepDiveAnalyzer(self.db_path)
        except Exception as e:
            logger.warning("Could not initialize LLMDeepDiveAnalyzer: %s", e)
            self.deep_dive_analyzer = None

    def evaluate_candidate_end_to_end(
        self,
        ticker: str,
        strike: float,
        call_put: str,
        expiration: str,
        dte: int,
        premium_usd: float,
        entry_price: float,
        spot_price: float,
        auto_publish_alerts: bool = True,
        image_path: Optional[str] = None,
        *, execution_decision: Optional[Dict[str, Any]] = None,
        execution_policy_version: Optional[str] = None,
        publication: Optional[Dict[str, Any]] = None,
        learning_context: Optional[Dict[str, Any]] = None,
        research_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Unified Production Pipeline:
          1. Runs Dynamic Shadow Quant (Directional Alpha, Brier Calibration, 3D Touch Prob).
          2. Runs 5-Factor DREAM Setup Checklist (OFI, GEX, TTM/EMA, Macro/Micro, Social).
          3. Runs LLM Deep-Dive Analysis (Dual-Sided Skew, Sympathies, Macro Confluence).
          4. If A+ DREAM Setup Confirmed, automatically publishes the flagship visual card to #owlfred-alerts.
        """
        ticker = ticker.upper().strip()
        logger.info("Running End-to-End Evaluation for $%s %s %s...", ticker, strike, call_put)

        # Validate and persist the actual caller's historical decision before
        # enrichment. Today's provider output cannot enter its recorded inputs.
        learning_decision = None
        learning_inputs = {}
        if learning_context is not None:
            if not isinstance(learning_context, dict) or not isinstance(learning_context.get('inputs'), dict):
                raise ValueError('Explicit learning decision inputs required')
            from plugins.analyst_trader.learning_evidence import aware_time
            if aware_time(learning_context.get('decision_at')) > self.clock():
                raise ValueError('Future learning decision')
            learning_inputs = dict(learning_context['inputs'])
            evaluated = dict(ticker=ticker, strike=strike, call_put=call_put, expiration=expiration,
                             dte=dte, premium_usd=premium_usd, entry_price=entry_price, spot_price=spot_price)
            if any(learning_inputs.get(k) != v for k, v in evaluated.items()):
                raise ValueError('Learning context does not match evaluated candidate')
            learning_inputs.setdefault('is_sweep', None)
            learning_inputs.setdefault('execution_venue', '')
            learning_decision = self.classifier.record_learning_decision(
                learning_context.get('decision_id'), learning_context.get('source_id'),
                learning_context.get('profile_version'), learning_context.get('decision_at'), learning_inputs)

        research_candidate = None
        if research_context is not None:
            from plugins.analyst_trader.kian_research import evaluate_research
            from plugins.analyst_trader.db import AnalystDatabase
            research_candidate = evaluate_research(AnalystDatabase(Path(self.db_path)),
                learning_decision, research_context, self.clock())
            if (not isinstance(publication, dict) or not learning_decision
                    or publication.get('flow_id') != learning_decision['source_id']
                    or publication.get('policy_version') != learning_decision['profile_version']):
                raise ValueError('Research publication lineage mismatch')

        # 1. Shadow Quant Run
        quant_res = {}
        if self.quant_engine:
            try:
                quant_res = self.quant_engine.evaluate_ticker_complete_quant(ticker, spot_price=spot_price or entry_price)
            except Exception as q_err:
                logger.warning("Shadow Quant evaluation warning for %s: %s", ticker, q_err)

        # 2. LLM Deep Dive Analysis
        deep_dive_res = {}
        if self.deep_dive_analyzer:
            try:
                deep_dive_res = self.deep_dive_analyzer.analyze_candidate_deep_dive(
                    ticker=ticker,
                    strike=strike,
                    call_put=call_put,
                    expiration=expiration,
                    dte=dte,
                    premium_usd=premium_usd,
                    current_price=spot_price or entry_price,
                    quant_result=quant_res
                )
            except Exception as dd_err:
                logger.warning("LLM Deep Dive analysis warning for %s: %s", ticker, dd_err)

        # 3. Assess DREAM Setup Qualification
        is_dream_setup = quant_res.get("is_a_plus_dream_setup", False)
        from plugins.analyst_trader.learning_evidence import observed_number
        scored = learning_decision['result'] if learning_decision else {}
        conviction_score = observed_number(scored.get('conviction_score') if learning_decision else
                                           quant_res.get('dream_setup', {}).get('conviction_score'))
        vol_to_oi = observed_number(learning_inputs.get('vol_to_oi'))
        gex_regime = learning_inputs.get('gex_regime') if learning_decision else quant_res.get('gex_overlay', {}).get('gex_regime')
        confluence = self.validate_dream_setup_confluence(conviction_score, dte, vol_to_oi,
            learning_inputs.get('is_sweep'), gex_regime=gex_regime, ticker=ticker,
            profile_version=learning_decision['profile_version'] if learning_decision else None,
            decision_at=learning_decision['decision_at'] if learning_decision else None)
        if learning_decision:
            is_dream_setup = bool(is_dream_setup and confluence['is_dream_setup'])
        
        # 4. Build Trade Recommendation
        rec = self.generate_trade_recommendation(
            ticker=ticker,
            strike=strike,
            call_put=call_put,
            expiration=expiration,
            dte=dte,
            premium_usd=premium_usd,
            entry_price=entry_price,
            spot_price=spot_price,
            conviction_score=conviction_score,
            tier_name=scored.get('tier_name', 'Unclassified research'),
            flow_tags_str=scored.get('flow_tags_str', ''),
            vol_to_oi=vol_to_oi,
            gex_regime=gex_regime
        )

        if research_candidate is not None:
            rec['research_candidate'] = research_candidate

        # 5. Determine Quantitative Strategy Identity
        if is_dream_setup:
            strategy_name = "A+_DREAM_SETUP"
        elif quant_res.get("gex_overlay", {}).get("gex_regime") == "Negative Gamma":
            strategy_name = "GEX_GAMMA_SQUEEZE"
        elif "FULL_BULLISH_STACK" in str(quant_res.get("market_data", {}).get("ta_info", {})):
            strategy_name = "EMA_STACK_BREAKOUT"
        else:
            strategy_name = "UNCLASSIFIED_RESEARCH"

        quant_snapshot = {
            "p_bullish": quant_res.get("directional_alpha", {}).get("p_bullish"),
            "directional_bias": quant_res.get("directional_alpha", {}).get("directional_bias"),
            "target_node": quant_res.get("directional_alpha", {}).get("target_node"),
            "touch_prob_3d": quant_res.get("directional_alpha", {}).get("touch_prob_3d"),
            "brier_score": quant_res.get("directional_alpha", {}).get("brier_score"),
            "is_calibrated": quant_res.get("directional_alpha", {}).get("is_calibrated"),
            "ofi_score": quant_res.get("ofi_metrics", {}).get("ofi_score"),
            "gex_regime": quant_res.get("gex_overlay", {}).get("gex_regime"),
            "setup_grade": quant_res.get("dream_setup", {}).get("setup_grade"),
            "conviction_score": conviction_score,
            "checklist_passed_count": quant_res.get("dream_setup", {}).get("checklist_passed_count"),
            "is_a_plus_dream_setup": is_dream_setup,
        }

        # Separate explicit research policy; never upgrades the A+ qualifier.
        delivery = dict(status='not_requested', units=[])
        research_eligible = research_candidate is not None and research_candidate['baseline_status'] == 'QUALIFIED'
        if (is_dream_setup or research_eligible) and auto_publish_alerts:
            delivery = self.publish_actionable_alert(rec, image_path=image_path, use_graphic_card=False, publication=publication)
            logger.info("%s alert delivery for $%s: %s", 'Research' if research_eligible else 'A+ DREAM', ticker, delivery['status'])
        else:
            logger.info("📊 $%s maintained in watchlist (Dream Setup Confirmed: %s)", ticker, is_dream_setup)
        published = delivery['status'] == 'complete'

        # 6b. Autonomous Strategy Validation Order (Portfolio B)
        paper_trade = None
        # An inference score is not execution permission. Preserve supplied identity.
        decision = execution_decision if execution_decision is not None else quant_res.get('execution_decision')
        if isinstance(decision, dict) and decision.get('execution_authorized') is True:
            try:
                from plugins.analyst_trader.execution_contract import validate_intent
                if research_candidate is not None and research_candidate['baseline_status'] != 'QUALIFIED':
                    raise ValueError('Incomplete/rejected research candidate cannot authorize a paper entry')
                from plugins.analyst_trader.strategy_logger import log_event
                decision = json.loads(json.dumps(decision, allow_nan=False))
                if research_candidate is not None:
                    from plugins.analyst_trader.kian_research import validate_paper_lifecycle
                    decision['research_lifecycle'] = validate_paper_lifecycle(research_candidate, learning_decision, decision, self.clock())
                if not decision.get('policy_version'):
                    decision['policy_version'] = execution_policy_version
                if learning_decision:
                    if (decision.get('parent_trace_id') != learning_decision['decision_id']
                            or decision.get('flow_id') != learning_decision['source_id']
                            or decision.get('policy_version') != learning_decision['profile_version']):
                        raise ValueError('Execution and learning lineage mismatch')
                    if learning_decision['recorded_profile']['classification'] != 'stated_policy':
                        raise ValueError('Learning proposal cannot authorize execution')
                if any(decision.get(k) != v for k,v in dict(ticker=ticker,strike=strike,call_put=call_put,expiration=expiration,entry_price=entry_price).items()):
                    raise ValueError('Execution decision does not match evaluated contract')
                validate_intent(decision, 'growing')
                parent = log_event('paper_execution_decision', dict(decision, trace_id=decision['parent_trace_id']),
                                   source='autonomous_risk_manager.py', db_path=str(self.db_path))
                if parent != decision['parent_trace_id']:
                    raise ValueError('Decision journal not durably acknowledged')
                from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine
                from plugins.analyst_trader.db import AnalystDatabase
                portfolio_db = AnalystDatabase(Path(self.db_path))
                portfolio_engine = DualPortfolioEngine(portfolio_db)
                paper_trade = portfolio_engine.execute_autonomous_trade(decision, account_tier="growing", now=self.clock())
                if paper_trade:
                    logger.info("🤖 Autonomous Paper Validation Order Placed in Portfolio B for $%s (%s contracts)", ticker, paper_trade.get("quantity"))
            except Exception as pt_err:
                logger.warning("Paper trade validator execution error for $%s: %s", ticker, pt_err)

        # 7. Persist Strategy Execution Trace
        trace_id = None
        try:
            from plugins.analyst_trader.strategy_logger import log_event
            trace_id = log_event(
                event_type="flow_candidate_evaluation",
                payload={
                    "ticker": ticker,
                    "decision_id": learning_decision['decision_id'] if learning_decision else None,
                    "flow_id": learning_decision['source_id'] if learning_decision else None,
                    "policy_version": learning_decision['profile_version'] if learning_decision else None,
                    "profile_status": confluence['profile_status'],
                    "strategy_name": strategy_name,
                    "action": "ACTIONABLE_ALERT_PUBLISHED" if (is_dream_setup and published) else "WATCHLIST_RECORDED",
                    "status": "APPROVED",
                    "directional_bias": quant_snapshot.get("directional_bias"),
                    "target_node": quant_snapshot.get("target_node"),
                    "touch_prob_3d": quant_snapshot.get("touch_prob_3d"),
                    "quant_metrics": quant_snapshot,
                    "screenshot_path": image_path,
                    "source_script": "autonomous_risk_manager.py",
                },
                source="autonomous_risk_manager.py",
                db_path=str(self.db_path),
            )
        except Exception as log_err:
            logger.debug("Strategy logger warning: %s", log_err)

        # 8. Record Candidate Telemetry in flow_candidate_analytics
        try:
            from plugins.analyst_trader.db import AnalystDatabase
            db = AnalystDatabase(Path(self.db_path))
            analytics_record = {
                "analytics_id": f"fca_{ticker}_{int(time.time() * 1000)}",
                "flow_id": learning_decision['source_id'] if learning_decision else
                           (execution_decision or publication or {}).get('flow_id'),
                "ticker": ticker,
                "contract_symbol": rec["contract_symbol"],
                "flow_tier": rec.get("tier_name", "Tier 2: Asymmetric Runner"),
                "conviction_score": conviction_score,
                "entry_price": entry_price,
                "peak_price": None,
                "trough_price": None,
                "mfe_pct": None,
                "mae_pct": None,
                "intraday_vol": None,
                "initial_oi": None,
                "next_day_oi": None,
                "oi_change_pct": None,
                "is_overnight_hold": None,
                "outcome_label": "MONITORING",
                "correlations_json": {
                    "strategy_name": strategy_name,
                    "strategy_trace_id": trace_id,
                    "quant_snapshot": quant_snapshot,
                    "is_dream_setup": is_dream_setup,
                    "published_alert": published,
                },
            }
            if analytics_record['flow_id'] is not None:
                db.save_flow_candidate_analytics(analytics_record)
        except Exception as db_save_err:
            logger.debug("Could not record flow candidate analytics trace: %s", db_save_err)

        return {
            "ticker": ticker,
            "is_dream_setup": is_dream_setup,
            "strategy_name": strategy_name,
            "strategy_trace_id": trace_id,
            "quant_result": quant_res,
            "quant_snapshot": quant_snapshot,
            "deep_dive_analysis": deep_dive_res,
            "recommendation": rec,
            "alert_published": published,
            "alert_delivery": delivery,
            "paper_trade": paper_trade,
            "learning_decision": learning_decision,
            "research_candidate": research_candidate,
            "confluence": confluence,
            "profile_status": confluence['profile_status'],
        }

    def validate_dream_setup_confluence(
        self,
        conviction_score: Optional[float],
        dte: int,
        vol_to_oi: Optional[float],
        is_sweep: Optional[bool],
        gex_regime: Optional[str] = None,
        ticker: Optional[str] = None,
        *, profile_version: Optional[str] = None, decision_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Gatekeeper to ensure candidates satisfy full dynamic 'Dream Setup' confluence:
          - Flow Score >= 80.0
          - DTE >= 14 days (prevents immediate theta decay traps)
          - Vol/OI >= 1.8x (strong opening positioning)
          - GEX Structure (clear runway without immediate pinning wall)
          - Analyst Style Confluence verification
        """
        reasons = []
        is_dream_setup = True
        analyst_edge = None

        profile_snapshot = None
        if profile_version is not None:
            if decision_at is None:
                raise ValueError('Explicit decision time required for profile replay')
            from plugins.analyst_trader.db import AnalystDatabase
            profile_snapshot = AnalystDatabase(Path(self.db_path)).get_learning_version(profile_version, decision_at)
            # Recorded descriptive context never becomes an execution gate or edge.

        if conviction_score is None:
            is_dream_setup = False
            reasons.append('Conviction unknown')
        elif conviction_score < 80.0:
            is_dream_setup = False
            reasons.append(f"Conviction score ({conviction_score:.1f}) < 80.0 threshold")

        if dte < 14:
            is_dream_setup = False
            reasons.append(f"DTE ({dte}d) too short for swing runway; high theta decay risk")

        if vol_to_oi is None:
            is_dream_setup = False
            reasons.append('Vol/OI unknown')
        elif vol_to_oi < 1.8:
            is_dream_setup = False
            reasons.append(f"Vol/OI ratio ({vol_to_oi:.2f}x) lacks aggressive opening momentum")

        if not gex_regime:
            is_dream_setup = False
            reasons.append('GEX structure unknown')
        elif "PINNED" in gex_regime.upper() or "HEAVY RESISTANCE" in gex_regime.upper():
            is_dream_setup = False
            reasons.append(f"GEX Market Structure warning: {gex_regime}")

        return {
            "is_dream_setup": is_dream_setup,
            "reasons": reasons,
            "confluence_status": "DREAM SETUP CONFIRMED" if is_dream_setup else "WATCHLIST ONLY",
            "analyst_edge": analyst_edge,
            "profile_snapshot": profile_snapshot,
            "profile_version": profile_version,
            "profile_status": "recorded_unvalidated" if profile_snapshot else "legacy_unknown"
        }

    def calculate_dynamic_tp_setpoints(
        self,
        entry_price: float,
        spot_price: float,
        strike: float,
        call_put: str,
        dte: int,
        target_node: Optional[float] = None
    ) -> Tuple[float, float, float, float, float]:
        """
        Calculates mathematically realistic, Greek & GEX-anchored Take-Profit targets.
        Returns: (tp1_price, tp1_pct, tp2_price, tp2_pct, stop_loss_price)
        """
        cp = "C" if "C" in call_put.upper() else "P"
        # Estimate Delta based on moneyness & DTE
        moneyness = (spot_price / strike) if cp == "C" else (strike / spot_price)
        if moneyness > 1.05:
            delta = 0.70  # Deep ITM
        elif moneyness >= 0.98:
            delta = 0.50  # ATM
        else:
            delta = 0.30  # OTM

        # Dynamic TP1 (1.0x ATR or Nearest Key Level): Realistic +20% to +25%
        # High DTE / ITM gets +25%; Short DTE / OTM gets +20% to +25%
        tp1_pct = 25.0 if (dte > 30 or delta >= 0.60) else 20.0
        tp1_price = round(entry_price * (1.0 + (tp1_pct / 100.0)), 2)

        # Dynamic TP2 (Major GEX Magnet Node Target): Realistic +45% to +60%
        if target_node and spot_price > 0:
            stock_move_pct = abs(target_node - spot_price) / spot_price
            implied_opt_gain_pct = (stock_move_pct * delta * (spot_price / entry_price)) * 100.0
            tp2_pct = round(max(45.0, min(60.0, implied_opt_gain_pct)), 1)
        else:
            tp2_pct = 45.0 if (dte > 30 or delta >= 0.60) else 60.0

        tp2_price = round(entry_price * (1.0 + (tp2_pct / 100.0)), 2)

        # Planned Stop Target: Realistic -20% to -25% (1:1 R:R against dynamic TP1)
        stop_pct = tp1_pct
        stop_loss_price = round(entry_price * (1.0 - (stop_pct / 100.0)), 2)

        return tp1_price, tp1_pct, tp2_price, tp2_pct, stop_loss_price

    def generate_trade_recommendation(
        self,
        ticker: str,
        strike: float,
        call_put: str,
        expiration: str,
        dte: int,
        premium_usd: float,
        entry_price: float,
        spot_price: float,
        conviction_score: Optional[float],
        tier_name: str,
        flow_tags_str: str,
        vol_to_oi: Optional[float] = None,
        gex_regime: Optional[str] = None,
        target_node: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Builds institutional Actionable Alert payload with dynamic Greek TPs,
        integer contract sizing, and true risk disclosures.
        """
        contract_type = "C" if "C" in call_put.upper() else "P"
        contract_symbol = f"{ticker.upper()} {strike:g}{contract_type} {expiration}"
        occ_symbol = generate_occ_symbol(ticker, expiration, contract_type, strike)

        # 1. Dynamic Greek/GEX-Anchored TP Setpoints
        tp1_price, tp1_pct, tp2_price, tp2_pct, stop_loss_price = self.calculate_dynamic_tp_setpoints(
            entry_price=entry_price,
            spot_price=spot_price,
            strike=strike,
            call_put=contract_type,
            dte=dte,
            target_node=target_node
        )

        planned_risk_per_con = round((entry_price - stop_loss_price) * 100, 2)
        max_theoretical_loss = round(entry_price * 100, 2)

        # 2. Explicit Contract-by-Contract Sizing & De-Risking Schedule
        con_cost = int(entry_price * 100)
        stop_risk = int(con_cost * 0.30)
        
        sched_1 = get_contract_trim_schedule(1, tp1_pct, tp2_pct)
        sched_2 = get_contract_trim_schedule(2, tp1_pct, tp2_pct)
        sched_3 = get_contract_trim_schedule(3, tp1_pct, tp2_pct)

        from plugins.analyst_trader.execution_contract import MICRO_MAX_CONTRACT_COST
        if entry_price * 100 > MICRO_MAX_CONTRACT_COST:
            micro_note = "⚠️ PASS (Contract >$200 exceeds 5% risk limit)"
        else:
            micro_note = f"1 con (${con_cost} | Planned SL: ~${stop_risk} | Max Loss: ${max_theoretical_loss:.0f})"

        growing_note = f"{sched_2['summary']} (or {sched_3['summary']})"
        standard_note = f"3–5 cons: {sched_3['action_at_tp1']}"

        clean_contract_line = f"{contract_symbol} at ${entry_price:.2f} ({dte} DTE)"
        clean_thesis = f"Research candidate {ticker.upper()}; {gex_regime or 'GEX structure unknown'}. Targets are heuristic plans, not observed outcomes."
        clean_tp_sl = (
            f"🎯 **TP1:** `${tp1_price:.2f}` (+{tp1_pct:.0f}%) | 🚀 **TP2:** `${tp2_price:.2f}` (+{tp2_pct:.0f}%) | 🛑 **Planned SL:** `${stop_loss_price:.2f}` (-{100-int(stop_loss_price/entry_price*100)}%)\n"
            f"⚠️ **Max Theoretical Loss:** `100% (${max_theoretical_loss:.0f}/con)`\n"
            f"🛡️ **Sizing:** `Micro (<$1k): {micro_note}` · `Growing ($1k-$5k): {growing_note}`"
        )

        return {
            "ticker": ticker.upper(),
            "occ_symbol": occ_symbol,
            "contract_symbol": contract_symbol,
            "strike": strike,
            "call_put": contract_type,
            "expiration": expiration,
            "dte": dte,
            "entry_price": entry_price,
            "spot_price": spot_price,
            "tp1_price": tp1_price,
            "tp1_pct": tp1_pct,
            "tp2_price": tp2_price,
            "tp2_pct": tp2_pct,
            "stop_loss_price": stop_loss_price,
            "planned_risk_per_con": planned_risk_per_con,
            "max_theoretical_loss": max_theoretical_loss,
            "conviction_score": conviction_score,
            "tier_name": tier_name,
            "flow_tags_str": flow_tags_str,
            "vol_to_oi": vol_to_oi,
            "gex_regime": gex_regime,
            "clean_contract_line": clean_contract_line,
            "clean_thesis": clean_thesis,
            "clean_tp_sl": clean_tp_sl,
            "sizing_rules": {
                "micro_account": micro_note,
                "growing_account": growing_note,
                "standard_account": standard_note
            }
        }

    def publish_telegram_alert(self, recommendation, card_image_path=None, *, publication=None):
        """Compatibility entry: explicit Telegram scope, same durable unit logic."""
        if card_image_path is not None:
            return self._unsupported_media()
        from plugins.analyst_trader.alert_delivery import actionable_cards
        return self._publish_cards(recommendation, publication, actionable_cards(recommendation),
                                   tuple(d for d in self.delivery_destinations if d[0]=='telegram'))

    def _publish_cards(self, recommendation, publication, cards, destinations):
        from plugins.analyst_trader.alert_delivery import AlertOutbox
        if not isinstance(publication, dict) or publication.get('publishing_authorized') is not True:
            return dict(status='denied', reason='Explicit publishing authorization required', units=[])
        outbox = AlertOutbox(self.db_path, clock=self.delivery_clock)
        result = outbox.enqueue(recommendation, publication, destinations, cards)
        if result['status'] in ('blocked', 'denied'):
            return result
        return dict(outbox.drain(publication['alert_id'], publication['revision'], self.delivery_transport),
                    capability='text_only', media_delivered=False)

    @staticmethod
    def _unsupported_media():
        return dict(status='unsupported', reason='Media delivery is not supported; request text explicitly',
                    capability='text_only', media_delivered=False, units=[])

    def publish_actionable_alert(
        self, recommendation: Dict[str, Any], image_path: Optional[str] = None,
        use_graphic_card: bool = False, *, publication=None
    ) -> Dict[str, Any]:
        """Persist required cards before send; return durable aggregate, never bool OR.

        The bounded text-card contract replaces the untracked async graphic patch.
        No render threads or provider calls occur outside the durable units.
        """
        if image_path is not None or use_graphic_card is not False:
            return self._unsupported_media()
        from plugins.analyst_trader.alert_delivery import actionable_cards
        return self._publish_cards(recommendation, publication, actionable_cards(recommendation), self.delivery_destinations)

    @staticmethod
    def _position_source_subject(ticker: str, displayed_contract: str,
                                 recommendation: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate the evaluator-to-position boundary without repairing identifiers.

        Display input is literal compact OCC. Source labels may be compact OCC
        or the producer's exact readable contract_symbol / padded occ_symbol.
        Every supplied identity field must agree, including in partial subjects.
        Return a copy retaining all source fields for persisted-source admission.
        """
        from plugins.analyst_trader.execution_contract import contract
        if not isinstance(recommendation, dict) or recommendation.get('ticker') != ticker:
            raise ValueError('Matching source recommendation required')
        compact = contract(dict(recommendation, occ_symbol=displayed_contract))
        if displayed_contract != compact:
            raise ValueError('Position display requires literal compact OCC')
        readable = (f"{ticker} {recommendation['strike']:g}{recommendation['call_put']} "
                    f"{recommendation['expiration']}")
        padded = f'{ticker:<6}{compact[len(ticker):]}'
        for field, accepted in (('contract_symbol', (compact, readable)),
                                ('occ_symbol', (compact, padded))):
            if field in recommendation and recommendation[field] not in accepted:
                raise ValueError('Position contract must exactly match eligible source')
        return dict(recommendation)

    def publish_position_exit_alert(
        self, ticker: str, contract_symbol: str, trigger_label: str, pnl_pct: float,
        current_price: float, entry_price: float, action_note: str, *,
        publication=None, source_recommendation=None
    ) -> Dict[str, Any]:
        """Publish authorized research position guidance, not proof of execution.

        No monitor invokes this automatically. Caller must supply the original
        eligible source identity and separate publication decision.
        """
        if not isinstance(publication,dict) or publication.get('publishing_authorized') is not True:
            return dict(status='denied', reason='Explicit publishing authorization required', units=[])
        source_subject = self._position_source_subject(ticker, contract_symbol, source_recommendation)
        # enqueue and send-intent admission independently match these source
        # fields against the persisted eligible row; no alternate subject allowed.
        rec = dict(source_subject, position_guidance=dict(contract_symbol=contract_symbol,
                   trigger_label=trigger_label,pnl_pct=pnl_pct,current_price=current_price,
                   entry_price=entry_price,action_note=action_note))
        cards = {'position': {'content': f'OWLFRED POSITION GUIDANCE: {trigger_label}\n{contract_symbol}\nBid: {current_price} | Entry: {entry_price} | P/L: {pnl_pct}%\n{action_note}\nResearch guidance, not an execution receipt.'}}
        return self._publish_cards(rec, publication, cards, self.delivery_destinations)

    def process_price_update(self, holding_id: str, quote) -> Optional[Dict[str, Any]]:
        """Shared evidence-gated transition; a bare number is not quote evidence."""
        from plugins.analyst_trader.db import AnalystDatabase
        from plugins.analyst_trader.portfolio_engine import DualPortfolioEngine
        from plugins.analyst_trader.paper_monitor import process_quote
        if self.quote_max_age_seconds is None:
            return None
        db = AnalystDatabase(Path(self.db_path))
        return process_quote(db, DualPortfolioEngine(db), holding_id, quote,
                             now=self.clock(), max_age=self.quote_max_age_seconds)

    def monitor_and_update_positions(self) -> List[Dict[str, Any]]:
        """Scheduled paper path; no synthetic bids, publication, or default freshness."""
        from plugins.analyst_trader.paper_monitor import monitor
        return monitor(self)


if __name__ == "__main__":
    manager = AutonomousRiskManager()
    print("=== Testing Modular 2-Card Alert Generation ===")
    rec = manager.generate_trade_recommendation(
        ticker="MRVL",
        strike=250.0,
        call_put="C",
        expiration="09/25/2026",
        dte=34,
        premium_usd=5300000.0,
        entry_price=20.60,
        spot_price=237.20,
        conviction_score=88.0,
        tier_name="Tier 2: Asymmetric Runner / Mid-Cap Flow",
        flow_tags_str="BIG ASK CALLS | OTM CALLS",
        vol_to_oi=9.82,
        gex_regime="Clear negative GEX acceleration zone"
    )
    print("Recommendation:\n", json.dumps(rec, indent=2, default=str))
