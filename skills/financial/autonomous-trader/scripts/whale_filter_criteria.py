#!/usr/bin/env python3
"""
whale_filter_criteria.py - Institutional Whale Ingestion Filter & Qualification Engine.

Combines quantitative order flow signals, Technical EMA(8, 21, 50, 100, 200) stacks,
GEX/VEX regimes, intraday volume/RVOL, and SQLite multi-whale cluster memory
to determine which institutional sweeps represent high-conviction alpha.
"""

import os
import sys
import json
import sqlite3
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from plugins.analyst_trader.db import get_db_path
from plugins.analyst_trader.finviz_fetcher import FinvizFetcher
from plugins.analyst_trader.technical_indicators import TechnicalIndicatorsEngine
from plugins.analyst_trader.gex_downstream_overlay import GEXDownstreamOverlay
from plugins.analyst_trader.strategy_logger import log_event

logger = logging.getLogger("whale_filter_criteria")

MEGA_CAP_OR_ETF_TICKERS = {
    "SPY", "QQQ", "IWM", "DIA", "SMH", "XLE", "XLF", "XLK", "XBI", "GLD", "SLV", "TLT",
    "NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "GOOG", "AMD", "AVGO", "NFLX"
}


class WhaleFilterEngine:
    """Evaluates institutional whale criteria, technical EMA confluence, GEX regimes, and repeat accumulation."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(get_db_path())
        self.fetcher = FinvizFetcher()
        self.tech_engine = TechnicalIndicatorsEngine()
        self.overlay_engine = GEXDownstreamOverlay()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def check_multi_whale_cluster_memory(
        self,
        ticker: str,
        lookback_hours: int = 48
    ) -> Tuple[int, float, List[Dict[str, Any]]]:
        """
        Query SQLite notable_flow for repeat institutional accumulation on this ticker.
        Returns: (repeat_count, total_cluster_premium_usd, recent_cluster_flows)
        """
        ticker_up = ticker.upper().strip()
        try:
            conn = self._get_connection()
            since_time = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).isoformat()
            cur = conn.execute("""
                SELECT flow_id, strike, call_put, expiration, premium_usd, vol_to_oi_ratio, is_sweep, trade_timestamp
                FROM notable_flow
                WHERE ticker = ? AND trade_timestamp >= ? AND premium_usd >= 150000.0
                  AND COALESCE(notable_flow.is_quarantined,0) = 0
                  AND NOT EXISTS (SELECT 1 FROM flow_candidate_analytics a
                      WHERE a.flow_id=notable_flow.flow_id AND COALESCE(a.is_quarantined,0) != 0)
                ORDER BY trade_timestamp DESC
                LIMIT 10
            """, (ticker_up, since_time))
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()

            total_prem = sum(float(r.get("premium_usd") or 0.0) for r in rows)
            return len(rows), total_prem, rows
        except Exception as e:
            logger.debug("Multi-whale cluster memory check skipped: %s", e)
            return 0, 0.0, []

    def evaluate_whale_candidate(
        self,
        ticker: str,
        strike: float,
        call_put: str,
        expiration: str,
        dte: int,
        premium_usd: float,
        spot_price: Optional[float] = None,
        entry_price: Optional[float] = None,
        vol_to_oi: Optional[float] = None,
        is_sweep: bool = False,
        execution_venue: str = "AT ASK",
        asset_type: str = "equity",
        gex_regime: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive institutional whale filter evaluating:
          1. Premium threshold and tier qualification
          2. Urgency and Vol/OI ratio (opening vs closing)
          3. Technical EMA stack (8, 21, 50, 100, 200) & 200 EMA trap detection
          4. Intraday Volume & RVOL surge confirmation
          5. GEX / VEX market structure overlay
          6. Multi-whale cluster memory
        """
        ticker_up = ticker.upper().strip()
        contract_type = "C" if "C" in call_put.upper() else "P"
        is_call = contract_type == "C"
        is_mega_etf = ticker_up in MEGA_CAP_OR_ETF_TICKERS or asset_type.lower() == "etf"

        confluence_tags: List[str] = []
        score = 0.0

        # 1. Tier Allocation & Minimum Premium Threshold
        if is_mega_etf:
            whale_tier = "Tier 1: Mega-Cap / ETF Whale Block"
            min_premium = 500_000.0
            if premium_usd >= 3_000_000.0: score += 30.0
            elif premium_usd >= 1_000_000.0: score += 25.0
            elif premium_usd >= 500_000.0: score += 20.0
            else: score += (premium_usd / 500_000.0) * 15.0
        elif dte >= 90 and premium_usd >= 250_000.0:
            whale_tier = "Tier 3: LEAP Whale Accumulation"
            min_premium = 250_000.0
            if premium_usd >= 1_000_000.0: score += 30.0
            elif premium_usd >= 500_000.0: score += 25.0
            else: score += 20.0
        else:
            whale_tier = "Tier 2: Mid-Cap Asymmetric Whale"
            min_premium = 200_000.0
            if premium_usd >= 1_000_000.0: score += 30.0
            elif premium_usd >= 500_000.0: score += 25.0
            elif premium_usd >= 200_000.0: score += 20.0
            else: score += (premium_usd / 200_000.0) * 15.0

        confluence_tags.append(f"${premium_usd/1e6:.1f}M PREM" if premium_usd >= 1e6 else f"${premium_usd/1e3:.0f}K PREM")

        # 2. Vol / OI Aggression Ratio (Max 25 pts)
        eff_vol_oi = vol_to_oi
        if eff_vol_oi is None:
            confluence_tags.append('VOL/OI UNKNOWN')
        elif eff_vol_oi >= 5.0:
            score += 25.0
            confluence_tags.append(f"EXTREME VOL/OI {eff_vol_oi:.1f}x")
        elif eff_vol_oi >= 2.5:
            score += 20.0
            confluence_tags.append(f"VOL/OI {eff_vol_oi:.1f}x")
        elif eff_vol_oi >= 1.5:
            score += 15.0
        else:
            score += 8.0

        # 3. Execution Venue & Sweep (Max 15 pts)
        venue_up = execution_venue.upper()
        if is_sweep:
            score += 15.0
            confluence_tags.append("MULTI-EXCHANGE SWEEP")
        elif "ASK" in venue_up or "ABOVE MID" in venue_up:
            score += 12.0
            confluence_tags.append("AT ASK")
        else:
            score += 6.0

        # 4. Expiration Runway (Max 15 pts)
        if 20 <= dte <= 60:
            score += 15.0
            confluence_tags.append(f"{dte}D SWEET SPOT")
        elif 14 <= dte < 20:
            score += 10.0
        elif 60 < dte <= 120:
            score += 12.0
        elif dte > 120:
            score += 8.0
        else:
            score += 4.0  # < 14 DTE penalty for short runway

        # 5. Technical EMA Stack Confluence (EMA 8, 21, 50, 100, 200)
        market_metrics = {}
        technical_data = {}
        try:
            market_metrics = self.fetcher.fetch_ticker_metrics(ticker_up)
            closes = market_metrics.get("historical_closes") or []
            atr_val = market_metrics.get("atr")
            rel_vol = market_metrics.get("rel_volume")
            vol_intraday = market_metrics.get("volume")

            technical_data = self.tech_engine.compute_technical_indicators(
                closes, atr=atr_val, rel_volume=rel_vol, intraday_volume=vol_intraday
            )
            if not spot_price or spot_price <= 0:
                spot_price = market_metrics.get("price") or technical_data.get("current_price")
        except Exception as err:
            logger.debug("Technical metrics lookup warning for %s: %s", ticker_up, err)

        if technical_data:
            stack_state = technical_data.get("ema_stack_state", "")
            is_above_200 = technical_data.get("is_above_200_ema")
            volume_confirmed = technical_data.get("volume_confirmed", False)
            ttm_fired = "FIRED" in technical_data.get("ttm_squeeze_state", "")

            if is_call:
                if stack_state == "FULL_BULLISH_STACK":
                    score += 10.0
                    confluence_tags.append("FULL EMA BULL STACK")
                elif "BULLISH" in stack_state:
                    score += 6.0
                    confluence_tags.append("BULLISH EMA CROSS")
                # 200 EMA Penalty: Calls trapped below 200 EMA
                if is_above_200 is False:
                    score -= 12.0
                    confluence_tags.append("TRAPPED BELOW 200 EMA")
            else:  # Put
                if stack_state == "FULL_BEARISH_STACK":
                    score += 10.0
                    confluence_tags.append("FULL EMA BEAR STACK")
                elif "BEARISH" in stack_state:
                    score += 6.0
                if is_above_200:
                    score -= 10.0
                    confluence_tags.append("CALL TREND OPPOSITION")
                else:
                    score += 6.0

            if volume_confirmed:
                score += 5.0
                confluence_tags.append(f"RVOL {technical_data.get('rel_volume', 1.0):.1f}x")

            if ttm_fired:
                score += 5.0
                confluence_tags.append("TTM SQUEEZE")

        # 6. GEX / VEX Regime Overlay
        if gex_regime:
            if "NEGATIVE GAMMA" in gex_regime.upper():
                score += 6.0
                confluence_tags.append("NEG GEX SQUEEZE")
            elif "POSITIVE GAMMA" in gex_regime.upper():
                confluence_tags.append("POS GEX BUFFER")

        # 7. Multi-Whale Cluster Memory Check
        repeat_count, cluster_prem, recent_flows = self.check_multi_whale_cluster_memory(ticker_up, lookback_hours=48)
        if repeat_count >= 2:
            score += 15.0
            confluence_tags.append(f"MULTI-WHALE CLUSTER ({repeat_count} prints / ${cluster_prem/1e6:.1f}M)")

        # Cap score between 0 and 100
        final_score = round(max(0.0, min(100.0, score)), 1)
        is_qualified = (final_score >= 75.0) and (premium_usd >= min_premium)

        # Strategy Name Determination
        if final_score >= 88.0:
            strategy_name = "A+_DREAM_SETUP"
        elif "NEG GEX SQUEEZE" in confluence_tags:
            strategy_name = "GEX_GAMMA_SQUEEZE"
        elif "FULL EMA BULL STACK" in confluence_tags or "BULLISH EMA CROSS" in confluence_tags:
            strategy_name = "EMA_STACK_BREAKOUT"
        else:
            strategy_name = "INSTITUTIONAL_WHALE_SWEEP"

        return {
            "ticker": ticker_up,
            "strike": strike,
            "call_put": contract_type,
            "expiration": expiration,
            "dte": dte,
            "premium_usd": premium_usd,
            "spot_price": spot_price,
            "flow_score": final_score,
            "is_qualified_whale": is_qualified,
            "whale_tier": whale_tier,
            "strategy_name": strategy_name,
            "confluence_tags": confluence_tags,
            "technical_data": technical_data,
            "multi_whale_cluster_count": repeat_count,
            "cluster_premium_usd": cluster_prem,
            "min_premium_required": min_premium,
        }


if __name__ == "__main__":
    engine = WhaleFilterEngine()
    eval_res = engine.evaluate_whale_candidate(
        ticker="NVDA",
        strike=230.0,
        call_put="C",
        expiration="2026-10-16",
        dte=28,
        premium_usd=4_200_000.0,
        vol_to_oi=3.8,
        is_sweep=True,
        gex_regime="Negative Gamma"
    )
    print("Whale Evaluation Result for NVDA:")
    print(json.dumps(eval_res, indent=2, default=str))
