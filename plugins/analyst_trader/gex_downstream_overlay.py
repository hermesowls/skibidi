import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class GEXDownstreamOverlay:
    """Independent Downstream Overlay applying Skylit GEX/VEX positioning and Execution Friction."""
    
    def __init__(self) -> None:
        pass

    def apply_overlay_and_friction(self, alpha_output: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply downstream GEX regime overlay, determine System Execution Bias, and compute execution friction."""
        ticker = alpha_output.get("ticker") or market_data.get("ticker", "")
        if alpha_output.get('status') == 'unavailable':
            return {**alpha_output, 'gex_regime':None, 'gex_vol_multiplier':None,
                    'gex_pass':False, 'execution_bias':'DATA_UNAVAILABLE',
                    'bid_ask_spread':None, 'friction_cost':None, 'friction_adjusted_price':None}
        price = alpha_output.get("current_price", 10.0)
        p_bullish = alpha_output.get("p_bullish", 0.50)
        ofi_score = alpha_output.get("ofi_score", 0.0)
        change_pct = market_data.get("change_pct", 0.0)
        atr = market_data.get("atr", 0.50)

        # 1. Determine Skylit GEX Regime Overlay (Downstream Only)
        # Negative GEX: High volatility / Gamma squeeze multiplier (1.5x)
        # Positive GEX: Low volatility / Gamma buffer multiplier (0.7x)
        if change_pct > 4.0 or ofi_score > 0.4:
            gex_regime = "Negative Gamma"
            gex_multiplier = 1.50
        elif change_pct < -4.0 or ofi_score < -0.4:
            gex_regime = "Negative Gamma"
            gex_multiplier = 1.50
        else:
            gex_regime = "Positive Gamma"
            gex_multiplier = 0.70

        # 2. Determine System Execution Bias
        if p_bullish >= 0.75 and gex_regime == "Negative Gamma":
            execution_bias = "AGGRESSIVE BREAKOUT LONG"
        elif p_bullish >= 0.60:
            execution_bias = "GRINDING DRIFT"
        elif p_bullish <= 0.35:
            execution_bias = "FADE / MEAN-REVERSION"
        else:
            execution_bias = "STAND ASIDE"

        # 3. Execution Friction Application
        # Deduct 50% bid-ask spread + Amihud illiquidity penalty + options execution slippage
        bid_ask_spread = max(0.01, round(price * 0.001, 3))
        half_spread_deduction = 0.50 * bid_ask_spread
        amihud_penalty = round(price * 0.0005, 3)
        options_slippage = round(price * 0.0010, 3)
        
        total_friction_cost = half_spread_deduction + amihud_penalty + options_slippage
        friction_adjusted_price = round(price + (total_friction_cost if p_bullish >= 0.5 else -total_friction_cost), 2)

        return {
            **alpha_output,
            # Momentum-derived regime is not observed Skylit GEX.
            "gex_regime": None,
            "gex_vol_multiplier": None,
            "gex_pass": False,
            "execution_bias": 'RESEARCH_ONLY_UNVERIFIED_GEX',
            "status": 'unverified',
            "bid_ask_spread": bid_ask_spread,
            "friction_cost": round(total_friction_cost, 4),
            "friction_adjusted_price": friction_adjusted_price,
            "architecture_mode": "DECOUPLED_GEX_DOWNSTREAM_OVERLAY"
        }

if __name__ == "__main__":
    from plugins.analyst_trader.finviz_fetcher import FinvizFetcher
    from plugins.analyst_trader.databento_ofi_engine import DatabentoOFIEngine
    from plugins.analyst_trader.directional_alpha import DirectionalAlphaEngine

    fetcher = FinvizFetcher()
    mdata = fetcher.fetch_all_universe(["METC", "NOK", "FRMI", "QURE"])
    ofi_engine = DatabentoOFIEngine()
    alpha_engine = DirectionalAlphaEngine()
    overlay_engine = GEXDownstreamOverlay()

    print("Decoupled System Output (Directional Alpha v0.1 + Downstream GEX Overlay):")
    for t, md in mdata.items():
        ofi_info = ofi_engine.compute_l2_ofi_metrics(t, md)
        alpha = alpha_engine.calculate_directional_probability(ofi_info, md)
        final_state = overlay_engine.apply_overlay_and_friction(alpha, md)
        print(f"  {t}: Price=${final_state['current_price']} | Bias={final_state['execution_bias']} | P(Bullish)={final_state['p_bullish']*100:.1f}% | GEX={final_state['gex_regime']} | Target=${final_state['target_node']} ({final_state['touch_prob_3d']*100:.1f}%, {final_state['expected_arrival_hours']}h) | Friction=${final_state['friction_cost']}")
