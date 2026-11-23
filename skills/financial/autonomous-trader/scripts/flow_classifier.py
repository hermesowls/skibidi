#!/usr/bin/env python3
"""
Dynamic Multi-Tier Flow Classifier & Scoring Engine — Calibrated to Skylit Flowseeker.

Matches Skylit Flowseeker card architecture:
  - Exact Score Badges:
      * 90 - 100: ELITE (Whale Institutional Conviction)
      * 80 - 89:  EXCELLENT / STRONG
      * 70 - 79:  SOLID (e.g. CBRS $1.6M 78 SOLID)
      * 60 - 69:  MODERATE
      * < 60:     SPECULATIVE / LOTTO
  - Quantitative Fields:
      * Spot Price, Entry Price, Far OTM %
      * Size / OI Ratio (e.g. 4.94x)
      * Break-Even Price ($270.10, +24.9% from spot)
      * Position Intent (Bought Calls, Bought Puts)
      * Execution Type (Above Mid, At Ask, Sweep)
      * AI Interpretation Generator
"""

import os
import sys
import json
import sqlite3
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from plugins.analyst_trader.db import get_db_path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("flow_classifier")

MEGA_CAP_TICKERS = {
    "SPY", "QQQ", "IWM", "NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "GOOG", "AMD", "GLD"
}


def get_flowseeker_badge(score: float) -> str:
    """Matches Skylit Flowseeker score badge taxonomy."""
    if score >= 90:
        return "ELITE"
    elif score >= 80:
        return "STRONG"
    elif score >= 70:
        return "SOLID"
    elif score >= 60:
        return "MODERATE"
    else:
        return "SPECULATIVE"


class FlowClassifierEngine:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(get_db_path())

    def classify_and_score_flow(
        self,
        ticker: str,
        strike: float,
        call_put: str,
        expiration: str,
        dte: int,
        premium_usd: float,
        asset_type: str = "equity",
        spot_price: Optional[float] = None,
        entry_price: Optional[float] = None,
        vol_to_oi: Optional[float] = None,
        is_sweep: Optional[bool] = None,
        execution_venue: str = "",
        market_cap: Optional[float] = None,
        technical_data: Optional[Dict[str, Any]] = None,
        gex_regime: Optional[str] = None,
        profile_version: Optional[str] = None,
        decision_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Classifies flow, incorporates Technical EMA(8, 21, 50, 100, 200) Stack,
        GEX regimes, and calculates moneyness/breakevens.
        """
        ticker_upper = ticker.upper().strip()
        call_put_upper = "C" if "C" in call_put.upper() else "P"
        is_call = call_put_upper == "C"
        is_mega_cap = ticker_upper in MEGA_CAP_TICKERS or (market_cap is not None and market_cap >= 200_000_000_000.0)
        is_etf = asset_type.lower() == "etf" or ticker_upper in {"SPY", "QQQ", "IWM", "GLD", "SLV", "SMH", "XLE", "XLF", "TLT"}

        # Dynamic Technical Confluence Fetch (if not passed)
        if technical_data is None:
            try:
                from plugins.analyst_trader.finviz_fetcher import FinvizFetcher
                from plugins.analyst_trader.technical_indicators import TechnicalIndicatorsEngine
                fetcher = FinvizFetcher()
                mdata = fetcher.fetch_ticker_metrics(ticker_upper)
                tech_engine = TechnicalIndicatorsEngine()
                technical_data = tech_engine.compute_technical_indicators(
                    mdata.get("historical_closes", []),
                    atr=mdata.get("atr", 0.50),
                    rel_volume=mdata.get("rel_volume", 1.0),
                    intraday_volume=mdata.get("volume", 0)
                )
                if not spot_price or spot_price <= 0:
                    spot_price = mdata.get("price") or technical_data.get("current_price")
            except Exception as tech_err:
                logger.debug("Technical confluence query bypassed for %s: %s", ticker_upper, tech_err)

        # 1. Tier Allocation
        if is_mega_cap or is_etf:
            tier_name = "Tier 1: Mega-Cap / ETF Institutional Block"
            min_premium = 500_000.0
            tier_id = 1
        elif dte >= 90 and premium_usd >= 250_000.0:
            tier_name = "Tier 3: Long-Dated LEAP / Macro Accumulation"
            min_premium = 250_000.0
            tier_id = 3
        else:
            tier_name = "Tier 2: Asymmetric Runner / Mid-Cap Flow"
            min_premium = 75_000.0
            tier_id = 2

        is_qualified = premium_usd >= min_premium

        # 2. Moneyness & Break-Even Calculation
        otm_pct = 0.0
        breakeven_price = 0.0
        breakeven_pct = 0.0
        moneyness_tag = "ATM"

        if spot_price and spot_price > 0:
            if is_call:
                otm_pct = max(0.0, ((strike - spot_price) / spot_price) * 100.0)
                moneyness_tag = "OTM" if strike > spot_price else "ITM"
                if entry_price and entry_price > 0:
                    breakeven_price = strike + entry_price
                    breakeven_pct = ((breakeven_price - spot_price) / spot_price) * 100.0
            else:
                otm_pct = max(0.0, ((spot_price - strike) / spot_price) * 100.0)
                moneyness_tag = "OTM" if strike < spot_price else "ITM"
                if entry_price and entry_price > 0:
                    breakeven_price = strike - entry_price
                    breakeven_pct = ((spot_price - breakeven_price) / spot_price) * 100.0

        # 3. Flowseeker Score Points Model (0 - 100)
        score = 0.0

        # Factor A: Premium Magnitude (Max 35 pts)
        if tier_id == 1:
            if premium_usd >= 5_000_000: score += 35
            elif premium_usd >= 2_000_000: score += 30
            elif premium_usd >= 1_000_000: score += 25
            elif premium_usd >= 500_000: score += 20
            else: score += (premium_usd / 500_000) * 15
        elif tier_id == 2:
            if premium_usd >= 1_000_000: score += 35
            elif premium_usd >= 300_000: score += 30
            elif premium_usd >= 150_000: score += 26
            elif premium_usd >= 100_000: score += 22
            elif premium_usd >= 75_000: score += 18
            else: score += (premium_usd / 75_000) * 14
        else: # Tier 3
            if premium_usd >= 1_000_000: score += 35
            elif premium_usd >= 500_000: score += 30
            elif premium_usd >= 250_000: score += 24
            else: score += (premium_usd / 250_000) * 15

        # Factor B: Size / OI Aggression Ratio (Max 25 pts)
        ratio = vol_to_oi
        if ratio is None: pass  # unavailable evidence contributes no points
        elif ratio >= 5.0: score += 25
        elif ratio >= 3.0: score += 20
        elif ratio >= 1.5: score += 15
        elif ratio >= 1.0: score += 10
        else: score += 5

        # Factor C: Sweep & Execution Venue (Max 20 pts)
        if is_sweep or "ASK" in execution_venue.upper() or "ABOVE MID" in execution_venue.upper():
            score += 20
        elif is_sweep is not None or execution_venue:
            score += 10

        # Factor D: Expiration Timing Runway (Max 20 pts)
        if 20 <= dte <= 60: score += 20
        elif 61 <= dte <= 120: score += 16
        elif 14 <= dte < 20: score += 15
        elif dte >= 121: score += 14
        else: score += 10

        # Factor E: Technical Confluence & EMA Stack (Bonus / Penalty)
        tech_modifier = 0.0
        tech_tags = []
        if technical_data:
            stack_state = technical_data.get("ema_stack_state", "")
            is_above_200 = technical_data.get("is_above_200_ema")
            volume_confirmed = technical_data.get("volume_confirmed", False)
            ttm_fired = "FIRED" in technical_data.get("ttm_squeeze_state", "")

            if is_call:
                if stack_state == "FULL_BULLISH_STACK":
                    tech_modifier += 10.0
                    tech_tags.append("FULL EMA BULL STACK")
                elif "BULLISH" in stack_state:
                    tech_modifier += 6.0
                    tech_tags.append("BULLISH EMA CROSS/PULLBACK")
                
                # Penalty if call is trapped below 200 EMA
                if is_above_200 is False:
                    tech_modifier -= 12.0
                    tech_tags.append("TRAPPED BELOW 200 EMA")
            else:  # Put
                if stack_state == "FULL_BEARISH_STACK":
                    tech_modifier += 10.0
                    tech_tags.append("FULL EMA BEAR STACK")
                elif "BEARISH" in stack_state:
                    tech_modifier += 6.0
                    tech_tags.append("BEARISH EMA CROSS/PULLBACK")
                if is_above_200:
                    tech_modifier -= 10.0
                    tech_tags.append("CALL TREND OPPOSITION")

            if volume_confirmed:
                tech_modifier += 4.0
                tech_tags.append(f"RVOL {technical_data.get('rel_volume', 1.0):.1f}x")
            
            if ttm_fired:
                tech_modifier += 4.0
                tech_tags.append("TTM SQUEEZE EXPANSION")

        # Factor F: GEX Regime Modifier
        gex_modifier = 0.0
        if gex_regime:
            if "NEGATIVE GAMMA" in gex_regime.upper():
                gex_modifier += 6.0
                tech_tags.append("NEG GEX SQUEEZE RUNWAY")
            elif "POSITIVE GAMMA" in gex_regime.upper():
                tech_tags.append("POS GEX BUFFER")

        # Learned descriptions are immutable context, not execution bonuses.
        analyst_modifier = 0.0
        analyst_tags = []
        profile_snapshot = None
        if profile_version is not None:
            if decision_at is None:
                raise ValueError('Explicit decision time required for profile replay')
            from plugins.analyst_trader.db import AnalystDatabase
            db = AnalystDatabase(Path(self.db_path))
            profile_snapshot = db.get_learning_version(profile_version, decision_at)
            analyst_tags.append('EXPLORATORY PROFILE: ' + profile_version)

        score = score + tech_modifier + gex_modifier + analyst_modifier
        score = min(100.0, max(0.0, score))
        score_badge = get_flowseeker_badge(score)

        # 4. Classification Tags
        flow_tags = []
        if is_call:
            if is_sweep or premium_usd >= 150_000:
                flow_tags.append("BIG ASK CALLS")
            if otm_pct >= 5.0 or moneyness_tag == "OTM":
                flow_tags.append("OTM CALLS")
        else:
            if is_sweep or premium_usd >= 150_000:
                flow_tags.append("BIG ASK PUTS")
            if otm_pct >= 5.0 or moneyness_tag == "OTM":
                flow_tags.append("OTM PUTS")

        flow_tags.extend(tech_tags)
        flow_tags.extend(analyst_tags)
        flow_tags_str = " | ".join(flow_tags)
        position_intent = ("Bought Calls" if is_call else "Bought Puts") if (
            'ASK' in execution_venue.upper() or 'ABOVE MID' in execution_venue.upper()) else 'Unknown'

        # 5. AI Synthesis Interpretation (Flowseeker style)
        otm_desc = f"{otm_pct:.1f}% OTM" if otm_pct > 0 else moneyness_tag
        interpretation = (
            f"Large {'call' if is_call else 'put'} {'sweep' if is_sweep is True else 'flow'} on {ticker_upper}. "
            f"{otm_desc} — {dte}-day expiry ({expiration}). "
            f"Size/OI: {str(round(ratio, 2)) + 'x' if ratio is not None else 'UNKNOWN'}. "
            f"Technical Alignment: {technical_data.get('ema_stack_state', 'N/A') if technical_data else 'N/A'}."
        )
        if analyst_tags:
            interpretation += f" Analyst Attribution: {', '.join(analyst_tags)}."

        return {
            "ticker": ticker_upper,
            "strike": strike,
            "call_put": call_put_upper,
            "expiration": expiration,
            "dte": dte,
            "premium_usd": premium_usd,
            "spot_price": spot_price,
            "entry_price": entry_price,
            "otm_pct": round(otm_pct, 1),
            "breakeven_price": round(breakeven_price, 2) if breakeven_price > 0 else None,
            "breakeven_pct": round(breakeven_pct, 1) if breakeven_pct > 0 else None,
            "size_to_oi": round(ratio, 2) if ratio is not None else None,
            "position_intent": position_intent,
            "execution": execution_venue,
            "tier_id": tier_id,
            "tier_name": tier_name,
            "flow_tags": flow_tags,
            "flow_tags_str": flow_tags_str,
            "conviction_score": round(score, 1),
            "score_badge": score_badge,
            "interpretation": interpretation,
            "technical_data": technical_data,
            "profile_version": profile_version,
            "profile_snapshot": profile_snapshot,
            "profile_status": "recorded_unvalidated" if profile_snapshot else "legacy_unknown",
            "gex_regime": gex_regime,
            "is_qualified": is_qualified
        }

    def record_learning_decision(self, decision_id, source_id, profile_version, decision_at, inputs):
        from plugins.analyst_trader.db import AnalystDatabase
        from plugins.analyst_trader.learning_store import record_decision
        return record_decision(AnalystDatabase(Path(self.db_path)), self,
                               decision_id, source_id, profile_version, decision_at, inputs)

    def replay_learning_decision(self, decision_id):
        from plugins.analyst_trader.db import AnalystDatabase
        from plugins.analyst_trader.learning_store import replay_decision
        return replay_decision(AnalystDatabase(Path(self.db_path)), decision_id)

    def score_all_db_notable_flows(self, update_db: bool = True) -> List[Dict[str, Any]]:
        """
        Scores all records in notable_flow and saves Flowseeker interpretation.
        """
        if not os.path.exists(self.db_path):
            logger.error("DB not found: %s", self.db_path)
            return []

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
            SELECT flow_id, ticker, strike, call_put, expiration, dte, premium_usd, asset_type, vol_to_oi_ratio, is_sweep
            FROM notable_flow
            WHERE (is_quarantined = 0 OR is_quarantined IS NULL)
              AND NOT EXISTS (SELECT 1 FROM flow_candidate_analytics a
                  WHERE a.flow_id=notable_flow.flow_id AND COALESCE(a.is_quarantined,0)<>0)
            ORDER BY premium_usd DESC
        """)
        rows = cur.fetchall()
        results = []

        for r in rows:
            res = self.classify_and_score_flow(
                ticker=r["ticker"],
                strike=r["strike"],
                call_put=r["call_put"],
                expiration=r["expiration"],
                dte=r["dte"] or 30,
                premium_usd=r["premium_usd"],
                asset_type=r["asset_type"],
                vol_to_oi=r["vol_to_oi_ratio"],
                is_sweep=bool(r["is_sweep"])
            )
            res["flow_id"] = r["flow_id"]
            results.append(res)

            if update_db:
                reasoning_str = f"[{res['score_badge']} {res['conviction_score']}] {res['interpretation']}"
                cur.execute("""
                    UPDATE notable_flow 
                    SET flow_score = ?, llm_reasoning = ?
                    WHERE flow_id = ?
                """, (res["conviction_score"], reasoning_str, r["flow_id"]))

        if update_db:
            conn.commit()
            logger.info("Updated %d notable flow records with Flowseeker score taxonomy.", len(results))

        conn.close()
        return results


if __name__ == "__main__":
    classifier = FlowClassifierEngine()

    print("=== Testing Exact CBRS Flowseeker Screenshot Case ===")
    cbrs_result = classifier.classify_and_score_flow(
        ticker="CBRS",
        strike=260.0,
        call_put="CALL",
        expiration="SEP 18",
        dte=30,
        premium_usd=1_600_000.0,
        spot_price=216.26,
        entry_price=10.10,
        vol_to_oi=4.94,
        is_sweep=True,
        execution_venue="Above Mid"
    )
    print(json.dumps(cbrs_result, indent=2))

    print("\n=== Testing BNTX Asymmetric Runner Case ===")
    bntx_result = classifier.classify_and_score_flow(
        ticker="BNTX",
        strike=115.0,
        call_put="CALL",
        expiration="SEP 18",
        dte=27,
        premium_usd=120_000.0,
        spot_price=98.50,
        entry_price=4.20,
        vol_to_oi=3.5,
        is_sweep=True,
        execution_venue="At Ask"
    )
    print(json.dumps(bntx_result, indent=2))
