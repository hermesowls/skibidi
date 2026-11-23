#!/usr/bin/env python3
"""
llm_deep_dive_analyzer.py - LLM Multi-Dimensional Deep Dive Analysis Engine.

Performs institutional pattern discovery across:
  1. Dual-Sided Skew & Dealer Positioning (Call vs Put skew, Net Delta/Gamma pressure)
  2. Graphify Sympathy & Supply-Chain Correlations (Lagging Movers & Peer Contagion)
  3. Candlestick Patterns, TTM Squeeze, and 8/21 EMA Momentum Alignment
  4. Macro/Micro Regimes & Corporate Insider Buying
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from plugins.analyst_trader.db import get_db_path

logger = logging.getLogger("LLMDeepDiveAnalyzer")


# Sector Peer Baskets for Dynamic Sympathy Resolution
SECTOR_PEER_MAP = {
    "Technology": ["QQQ", "XLK", "SMH", "NVDA", "AAPL"],
    "Financial": ["XLF", "JPM", "BAC", "GS"],
    "Healthcare": ["XLV", "LLY", "UNH", "PFE"],
    "Energy": ["XLE", "XOM", "CVX", "OXY"],
    "Consumer Cyclical": ["XLY", "AMZN", "TSLA", "HD"],
    "Consumer Defensive": ["XLP", "PG", "COST", "KO"],
    "Industrials": ["XLI", "CAT", "GE", "UNP"],
    "Basic Materials": ["XLB", "LIN", "FCX", "NUE"],
    "Communication Services": ["XLC", "META", "GOOGL", "NFLX"],
    "Utilities": ["XLU", "NEE", "SO", "DUK"],
    "Real Estate": ["XLRE", "PLD", "AMT", "CCI"]
}

# Pre-mapped Sympathy & Supply-Chain Knowledge Graph (High-Conviction Overrides)
SECTOR_SYMPATHY_GRAPH = {
    "METC": {
        "sector": "Basic Materials / Metallurgical Coal",
        "peers": ["AMR", "ARCH", "BTU", "NUE", "X"],
        "thesis": "Met coal export demand surge acts as a direct leading indicator for steel manufacturing (NUE, X) and thermal coal peers (BTU, ARCH)."
    },
    "BNTX": {
        "sector": "Healthcare / Biotechnology mRNA",
        "peers": ["MRNA", "PFE", "NVAX", "GILD"],
        "thesis": "mRNA oncology & vaccine pipeline breakthrough creates secondary sympathy momentum in MRNA and commercialization partner PFE."
    },
    "NVDA": {
        "sector": "Technology / AI Accelerators & Datacenter",
        "peers": ["TSM", "SMCI", "AVGO", "ARM", "AMD"],
        "thesis": "Hyperscale datacenter GPU capexe drives immediate lagging sympathy surges in foundry partner TSM, server integrator SMCI, and custom silicon peers."
    },
    "GLD": {
        "sector": "Commodities / Precious Metals",
        "peers": ["GDX", "NEM", "SLV", "GOLD"],
        "thesis": "Sovereign central bank gold accumulation and real-yield compression drives leveraged upside across senior gold miners (GDX, NEM)."
    }
}


def resolve_sector_sympathy(ticker: str, market_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Dynamically resolves sector, industry, and peer basket for any arbitrary ticker."""
    ticker_upper = ticker.upper().strip()
    if ticker_upper in SECTOR_SYMPATHY_GRAPH:
        return SECTOR_SYMPATHY_GRAPH[ticker_upper]

    m_data = market_data or {}
    sector = m_data.get("sector") or "Equities"
    industry = m_data.get("industry") or "General Market"

    matched_peers = ["SPY", "QQQ"]
    for s_key, p_list in SECTOR_PEER_MAP.items():
        if s_key.lower() in sector.lower() or s_key.lower() in industry.lower():
            matched_peers = p_list
            break

    return {
        "sector": f"{sector} / {industry}" if industry != "General Market" else sector,
        "peers": matched_peers,
        "thesis": f"Institutional order flow on ${ticker_upper} creates sympathy correlation across {sector} sector peers ({', '.join(matched_peers[:3])}) and related industry supply chain."
    }


class LLMDeepDiveAnalyzer:
    """Multi-Agent Reasoner conducting deep structural audits for candidate flow."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(get_db_path())

    def analyze_candidate_deep_dive(
        self,
        ticker: str,
        strike: float,
        call_put: str,
        expiration: str,
        dte: int,
        premium_usd: float,
        current_price: float,
        quant_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Executes a 4-dimensional structural analysis for candidate options flow.
        """
        ticker = ticker.upper().strip()
        cp = "CALL" if "C" in call_put.upper() else "PUT"

        # Descriptive supplied evidence only; option right is not tape skew,
        # and neither price nor DTE establishes TA or macro clearance.
        from plugins.analyst_trader.learning_evidence import observed_number
        market_data = quant_result.get('market_data', {})
        ratio = observed_number(market_data.get('call_put_ratio'))
        call_put_ratio = ratio if ratio is not None and ratio >= 0 else None
        is_unhedged = None if call_put_ratio is None else call_put_ratio > 2.5 or call_put_ratio < .40
        skew_verdict = 'Unknown tape skew' if is_unhedged is None else 'Observed skew; hedge intent unverified'
        sympathy_info = resolve_sector_sympathy(ticker, market_data)
        ta = market_data.get('ta_info') or {}
        events = market_data.get('event_info') or {}
        ta_summary = ta.get('summary', 'Technical evidence unavailable')
        macro_summary = events.get('summary', 'Macro/event clearance unavailable')
        # No calibrated synthesis probability has been established by this
        # descriptive formatter. Keep unknown rather than invent a blend.
        synthesis_confidence = None

        return {
            "ticker": ticker,
            "contract": f"{ticker} {strike:g}{'C' if cp == 'CALL' else 'P'}",
            "directional_bias": quant_result.get('directional_alpha', {}).get('directional_bias'),
            "skew_analysis": {
                "call_put_ratio": call_put_ratio,
                "is_unhedged_directional": is_unhedged,
                "verdict": skew_verdict
            },
            "sympathy_network": {
                "sector": sympathy_info["sector"],
                "key_peers": sympathy_info["peers"],
                "thesis": sympathy_info["thesis"],
                "classification": "unvalidated_peer_hypothesis"
            },
            "technical_confluence": {
                "ttm_squeeze": ta.get('ttm_squeeze'),
                "ema_stack": ta.get('ema_stack_state'),
                "summary": ta_summary
            },
            "macro_micro_clearance": {
                "macro_regime": events.get('macro_regime'),
                "binary_event_risk": events.get('binary_event_risk'),
                "summary": macro_summary
            },
            "synthesis_confidence": synthesis_confidence,
            "final_recommendation": (
                "ACTIONABLE_A_PLUS_DREAM_SETUP"
                if quant_result.get("is_a_plus_dream_setup") is True
                else "CONTINUE_SHADOW_MONITORING"
            )
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from plugins.analyst_trader.dynamic_shadow_quant import DynamicShadowQuantEngine

    engine = DynamicShadowQuantEngine()
    q_res = engine.evaluate_ticker_complete_quant("METC")
    
    analyzer = LLMDeepDiveAnalyzer()
    deep_dive = analyzer.analyze_candidate_deep_dive(
        ticker="METC",
        strike=12.0,
        call_put="C",
        expiration="09/18/2026",
        dte=26,
        premium_usd=120000.0,
        current_price=11.80,
        quant_result=q_res
    )
    
    print("\n" + "="*60)
    print(f"🧠 LLM MULTI-DIMENSIONAL DEEP DIVE: {deep_dive['ticker']}")
    print("="*60)
    print(f"Contract:               {deep_dive['contract']}")
    print(f"Directional Bias:       {deep_dive['directional_bias']}")
    print(f"Dual-Sided Skew:        {deep_dive['skew_analysis']['verdict']}")
    print(f"Sympathy Peers:         {', '.join(deep_dive['sympathy_network']['key_peers'])}")
    print(f"Sympathy Thesis:        {deep_dive['sympathy_network']['thesis']}")
    print(f"Technical Confluence:   {deep_dive['technical_confluence']['summary']}")
    print(f"Macro/Micro Clearance:  {deep_dive['macro_micro_clearance']['summary']}")
    print(f"Synthesis Confidence:   {deep_dive['synthesis_confidence']}%")
    print(f"Final Recommendation:   {deep_dive['final_recommendation']}")
    print("="*60 + "\n")
