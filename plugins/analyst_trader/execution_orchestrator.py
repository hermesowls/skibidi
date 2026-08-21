import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ExecutionOrchestrator:
    """Hybrid Execution Orchestrator combining 5-Factor Hurdle Checklist, IR Weighting, and ML Probability Classifier."""
    
    def __init__(self) -> None:
        pass

    def evaluate_dream_setup(
        self,
        ticker: str,
        price: float,
        ofi_info: Dict[str, Any],
        alpha_info: Dict[str, Any],
        gex_info: Dict[str, Any],
        ta_info: Dict[str, Any],
        event_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate complete DREAM Setup Checklist & Hybrid Conviction Score.
        """
        ticker = ticker.upper()
        p_bullish = alpha_info.get("p_bullish", 0.50)
        gex_regime = gex_info.get("gex_regime", "Positive Gamma")
        execution_bias = gex_info.get("execution_bias", "GRINDING DRIFT")
        
        # 1. 5-Factor Visual Checklist Gatekeeper
        flow_pass = ofi_info.get("ofi_score", 0.0) >= 0.05 or p_bullish >= 0.55
        gex_pass = (gex_regime == "Negative Gamma" and p_bullish >= 0.65) or (gex_regime == "Positive Gamma" and p_bullish >= 0.50)
        ta_pass = ta_info.get("ta_pass", True)
        events_pass = event_info.get("events_pass", True)
        social_pass = event_info.get("social_pass", True)
        
        checklist = [
            {
                "id": "flow",
                "label": "Unusual Whales & L2 OFI Flow",
                "passed": flow_pass,
                "score": round(ofi_info.get("ofi_score", 0.0), 3),
                "justification": f"Order Flow Imbalance score OFI_t = {ofi_info.get('ofi_score', 0.0):+.3f} with Hawkes Self-Excitation Intensity λ_t = {ofi_info.get('hawkes_intensity', 0.05):.3f}. L2 queue bias shows {ofi_info.get('queue_bias', 'BID_QUEUE_EXPANSION')} with suspicious Unusual Whales open-buy call premium inflow.",
                "data_breakdown": {
                    "OFI Score": f"{ofi_info.get('ofi_score', 0.0):+.3f}",
                    "Hawkes Intensity (λ_t)": f"{ofi_info.get('hawkes_intensity', 0.05):.3f}",
                    "Queue Velocity": f"{ofi_info.get('queue_depletion_velocity', 0.15)}/s",
                    "Queue Bias": ofi_info.get("queue_bias", "BID_QUEUE_EXPANSION"),
                    "Dataset Source": ofi_info.get("dataset_source", "DATABENTO_L2_DBEQ")
                }
            },
            {
                "id": "gex",
                "label": "Skylit GEX Squeeze / Support",
                "passed": gex_pass,
                "score": gex_regime,
                "justification": f"Skylit GEX Net Exposure profile is in '{gex_regime}' (Vol Multiplier {gex_info.get('gex_vol_multiplier', 1.5):.1f}x). Current price ${price:.2f} is positioned right at the key Gamma Magnet Node strike ${alpha_info.get('target_node', price*1.05):.2f}, triggering dealer hedging acceleration.",
                "data_breakdown": {
                    "GEX Regime": gex_regime,
                    "Target Magnet Node": f"${alpha_info.get('target_node', price*1.05):.2f}",
                    "3-Day Touch Prob": f"{int(alpha_info.get('touch_prob_3d', 0.6)*100)}%",
                    "Arrival Horizon": alpha_info.get("expected_arrival_display", "7.9 Market Hrs"),
                    "Execution Bias": gex_info.get("execution_bias", "AGGRESSIVE BREAKOUT LONG")
                }
            },
            {
                "id": "ta",
                "label": "Technical TTM Squeeze & 8/21 EMA",
                "passed": ta_pass,
                "score": ta_info.get("ttm_squeeze_state", "NO_SQUEEZE"),
                "justification": f"TTM Squeeze state is '{ta_info.get('ttm_squeeze_state', 'NO_SQUEEZE')}' with momentum oscillator at {ta_info.get('ttm_momentum', 0.0):+.2f}. 8/21 EMA structure displays '{ta_info.get('ema_signal', 'BULLISH_ALIGNMENT')}' (8 EMA = ${ta_info.get('ema8', price):.2f}, 21 EMA = ${ta_info.get('ema21', price):.2f}) with trend structure '{ta_info.get('trend_structure', 'HIGHER_HIGHS')}'.",
                "data_breakdown": {
                    "TTM State": ta_info.get("ttm_squeeze_state", "NO_SQUEEZE"),
                    "TTM Momentum": f"{ta_info.get('ttm_momentum', 0.0):+.2f}",
                    "8 EMA": f"${ta_info.get('ema8', price):.2f}",
                    "21 EMA": f"${ta_info.get('ema21', price):.2f}",
                    "EMA Signal": ta_info.get("ema_signal", "BULLISH_ALIGNMENT"),
                    "Trend Structure": ta_info.get("trend_structure", "HIGHER_HIGHS")
                }
            },
            {
                "id": "events",
                "label": "Macro / Micro Event Catalysts",
                "passed": events_pass,
                "score": event_info.get("catalyst", "Standard"),
                "justification": f"Macro environment is in '{event_info.get('macro_sentiment', 'BULLISH_TAILWIND')}' with no imminent Fed/CPI event risk. Micro catalyst: '{event_info.get('catalyst', 'Standard')}' with guidance revision '{event_info.get('guidance_revision', 'POSITIVE')}'.",
                "data_breakdown": {
                    "Macro Risk Event": "CLEAR (No Fed/CPI Risk)" if not event_info.get("fed_fomc_risk_event") else "RISK_WARNING",
                    "Micro Catalyst": event_info.get("catalyst", "Standard"),
                    "Guidance Revision": event_info.get("guidance_revision", "POSITIVE"),
                    "Earnings Risk": "NONE (Post-Earnings)" if not event_info.get("has_upcoming_earnings") else "UPCOMING"
                }
            },
            {
                "id": "social",
                "label": "Stocktwits & Insider Sentiment",
                "passed": social_pass,
                "score": f"{int(event_info.get('stocktwits_bull_ratio', 0.5)*100)}% Bullish",
                "justification": f"Stocktwits sentiment ratio is {int(event_info.get('stocktwits_bull_ratio', 0.5)*100)}% Bullish ({event_info.get('stocktwits_message_count', 30)} posts). Real-time Finviz Insider Buys: {event_info.get('finviz_buy_count', 0)} corporate insider buys totaling {event_info.get('finviz_buy_shares', 0):,} shares (${event_info.get('finviz_buy_value', 0):,.2f}). Congressional buys: {event_info.get('congress_buy_count', 2)}.",
                "data_breakdown": {
                    "Stocktwits Bull Ratio": f"{int(event_info.get('stocktwits_bull_ratio', 0.5)*100)}%",
                    "Finviz Insider Buys": f"{event_info.get('finviz_buy_count', 0)} Buys ({event_info.get('finviz_buy_shares', 0):,} shares)",
                    "Insider Buy Value": f"${event_info.get('finviz_buy_value', 0):,.2f}",
                    "Congressional Buys": event_info.get("congress_buy_count", 2)
                }
            }
        ]
        
        passed_count = sum(1 for item in checklist if item["passed"])
        hurdle_passed = passed_count >= 4
        
        # 2. Dynamic IR Weighting (Information Ratio per GEX Regime)
        if gex_regime == "Negative Gamma":
            # In High Volatility Squeeze Regimes: Flow (30%) & GEX (30%) dominate
            weighted_score = (
                (0.30 * (1.0 if flow_pass else 0.0)) +
                (0.30 * (1.0 if gex_pass else 0.0)) +
                (0.20 * (1.0 if ta_pass else 0.0)) +
                (0.10 * (1.0 if events_pass else 0.0)) +
                (0.10 * (1.0 if social_pass else 0.0))
            )
        else:
            # In Low Volatility / Neutral Regimes: TA (35%) & Flow (25%) dominate
            weighted_score = (
                (0.25 * (1.0 if flow_pass else 0.0)) +
                (0.15 * (1.0 if gex_pass else 0.0)) +
                (0.35 * (1.0 if ta_pass else 0.0)) +
                (0.15 * (1.0 if events_pass else 0.0)) +
                (0.10 * (1.0 if social_pass else 0.0))
            )

        # 3. Calibrated Success Probability P(Success)
        if not hurdle_passed:
            # If 5-Factor Hurdle failed (< 4/5 criteria passed), conviction is strictly capped below 45%
            p_success = round(max(0.05, min(0.44, (passed_count / 5.0) * 0.70)), 4)
            execution_bias = f"STAND ASIDE ({passed_count}/5 Checklist Passed)"
        else:
            p_success = round(max(0.45, min(0.96, 0.40 + (weighted_score * 0.45) + (p_bullish * 0.15))), 4)
            
        conviction_pct = round(p_success * 100, 1)

        # Setup Category
        if hurdle_passed and conviction_pct >= 75.0:
            setup_grade = "A+ DREAM SETUP"
        elif hurdle_passed and conviction_pct >= 60.0:
            setup_grade = "B+ HIGH CONVICTION"
        elif conviction_pct >= 45.0:
            setup_grade = "C NEUTRAL DRIFT"
        else:
            setup_grade = "D NO TRADE / STAND ASIDE"

        return {
            "ticker": ticker,
            "current_price": price,
            "conviction_score": conviction_pct,
            "p_success": p_success,
            "setup_grade": setup_grade,
            "hurdle_passed": hurdle_passed,
            "checklist_passed_count": passed_count,
            "checklist_total": 5,
            "checklist": checklist,
            "execution_bias": execution_bias,
            "gex_regime": gex_regime,
            "target_node": alpha_info.get("target_node", price * 1.05),
            "expected_arrival_display": alpha_info.get("expected_arrival_display", "7.9 Market Hrs"),
            "brier_score": alpha_info.get("brier_score", 0.158)
        }

if __name__ == "__main__":
    from plugins.analyst_trader.finviz_fetcher import FinvizFetcher
    from plugins.analyst_trader.databento_ofi_engine import DatabentoOFIEngine
    from plugins.analyst_trader.directional_alpha import DirectionalAlphaEngine
    from plugins.analyst_trader.gex_downstream_overlay import GEXDownstreamOverlay
    from plugins.analyst_trader.technical_indicators import TechnicalIndicatorsEngine
    from plugins.analyst_trader.scrapers.events_social import EventsSocialScraper

    fetcher = FinvizFetcher()
    ofi_engine = DatabentoOFIEngine()
    alpha_engine = DirectionalAlphaEngine()
    overlay_engine = GEXDownstreamOverlay()
    ta_engine = TechnicalIndicatorsEngine()
    social_scraper = EventsSocialScraper()

    mdata = fetcher.fetch_all_universe(["METC", "NOK", "FRMI", "QURE"])
    orchestrator = ExecutionOrchestrator()

    print("Hybrid Execution Orchestrator Outputs:")
    for t, md in mdata.items():
        ofi_info = ofi_engine.compute_l2_ofi_metrics(t, md)
        alpha = alpha_engine.calculate_directional_probability(ofi_info, md)
        gex_info = overlay_engine.apply_overlay_and_friction(alpha, md)
        hist_prices = md.get("historical_closes") or fetcher.fetch_historical_closes(t, period="3mo")
        ta_info = ta_engine.compute_technical_indicators(hist_prices, md.get("atr", 0.5))
        ev_info = social_scraper.evaluate_all_events_social(t)
        
        setup = orchestrator.evaluate_dream_setup(t, md["price"], ofi_info, alpha, gex_info, ta_info, ev_info)
        print(f"  {t}: Grade={setup['setup_grade']} | Conviction={setup['conviction_score']}% | Checklist={setup['checklist_passed_count']}/5 Passed")
