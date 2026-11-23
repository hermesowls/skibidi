import math
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def norm_cdf(x: float) -> float:
    """Standard Normal Cumulative Distribution Function (CDF)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

class DirectionalAlphaEngine:
    """Core Directional Alpha v0.1 Engine (100% GEX-Free)."""
    
    def __init__(self, target_brier_max: float = 0.18) -> None:
        self.target_brier_max = target_brier_max

    def calculate_directional_probability(self, ofi_data: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate standalone 100% GEX-free directional alpha probability and first-passage time."""
        ticker = ofi_data.get("ticker") or market_data.get("ticker", "")
        from plugins.analyst_trader.quant_storage_cache import observed_l2
        if not observed_l2(ofi_data, ticker):
            return {'ticker':ticker, 'current_price':market_data.get('current_price', market_data.get('price')),
                    'status':'unavailable', 'p_bullish':None, 'directional_bias':None,
                    'target_node':None, 'touch_prob_3d':None, 'brier_score':None,
                    'is_calibrated':False, 'ofi_score':None, 'hawkes_intensity':None}
        price = market_data.get("price", 10.0)
        atr = market_data.get("atr", 0.50)
        change_pct = market_data.get("change_pct", 0.0)
        rel_vol = market_data.get("rel_volume", 1.0)
        short_float = market_data.get("short_float_pct", 5.0)
        
        ofi_score = ofi_data.get("ofi_score", 0.0)
        hawkes_intensity = ofi_data.get("hawkes_intensity", 0.05)
        queue_velocity = ofi_data.get("queue_depletion_velocity", 0.15)
        amihud = ofi_data.get("amihud_illiquidity", 0.0001)

        # 8 Core GEX-Free Signals:
        # 1. Databento OFI
        s1_ofi = ofi_score
        # 2. Hawkes Intensity
        s2_hawkes = min(1.0, hawkes_intensity * 0.8)
        # 3. Queue Depletion Velocity
        s3_queue = min(1.0, queue_velocity * 2.0)
        # 4. Finviz Relative Volume
        s4_relvol = min(1.0, (rel_vol - 1.0) / 3.0) if rel_vol > 1.0 else 0.0
        # 5. SUE Earnings Revision (stubbed from price momentum)
        s5_sue = max(-1.0, min(1.0, change_pct / 8.0))
        # 6. Short Float Squeeze Risk
        s6_squeeze = min(1.0, short_float / 25.0)
        # 7. VWAP Intraday Momentum
        s7_vwap = max(-1.0, min(1.0, change_pct / 4.0))
        # 8. Amihud Illiquidity Impact
        s8_amihud = min(1.0, amihud * 1000.0)

        # Composite GEX-Free Directional Score: [-1.0, +1.0]
        composite_score = (
            s1_ofi * 0.30 +
            s2_hawkes * 0.15 +
            s3_queue * 0.10 +
            s4_relvol * 0.10 +
            s5_sue * 0.10 +
            s6_squeeze * 0.05 +
            s7_vwap * 0.15 +
            s8_amihud * 0.05
        )

        # Sigmoid Calibration to [0.05, 0.95]
        p_bullish = 1.0 / (1.0 + math.exp(-3.2 * composite_score))
        p_bullish = max(0.05, min(0.95, round(p_bullish, 4)))

        # Determine Primary Driver Signal
        if s1_ofi > 0.4 and s2_hawkes > 0.3:
            primary_driver = "Open-Buy Calls + Order Flow Imbalance (OFI)"
        elif s6_squeeze > 0.4:
            primary_driver = "Short Float Squeeze Pressure"
        elif s5_sue > 0.4:
            primary_driver = "SUE Guidance Revision"
        elif change_pct < -3.0:
            primary_driver = "L2 Queue Depletion & Sell Pressure"
        else:
            primary_driver = "Microstructure Momentum Alignment"

        # Calculate First-Passage Time to Target Node B over 3-Day Horizon (T=3.0 days)
        # Drift \mu, Volatility \sigma
        target_direction = 1.0 if p_bullish >= 0.50 else -1.0
        target_dist_pct = (0.03 + (abs(p_bullish - 0.50) * 0.08)) * target_direction
        target_node = round(price * (1.0 + target_dist_pct), 2)

        drift = (p_bullish - 0.50) * 0.04  # daily drift
        sigma = max(0.015, (atr / price) * 0.8) # daily volatility
        T = 3.0 # 3 days horizon

        # First-Passage Time Probability Calculation:
        # P(T_B <= 3) = 1 - \Phi((b - \mu T) / (\sigma \sqrt{T})) + exp(2 \mu b / \sigma^2) \Phi((-b - \mu T) / (\sigma \sqrt{T}))
        b = abs(math.log(target_node / price))
        mu_adj = drift - (0.5 * sigma * sigma)
        denom = sigma * math.sqrt(T)

        d1 = (b - mu_adj * T) / denom
        d2 = (-b - mu_adj * T) / denom

        term1 = 1.0 - norm_cdf(d1)
        term2 = math.exp(max(-50.0, min(50.0, (2.0 * mu_adj * b) / (sigma * sigma)))) * norm_cdf(d2)
        touch_prob_3d = max(0.10, min(0.92, round(term1 + term2, 4)))

        # Expected Arrival Time in Market Hours (6.5h per trading day) & Calendar Hours
        calendar_hours = round(max(4.0, min(72.0, (1.0 - touch_prob_3d + 0.2) * 48.0)), 1)
        market_hours = round(calendar_hours * (6.5 / 24.0), 1)
        trading_days = round(market_hours / 6.5, 1)
        exp_arrival_display = f"{market_hours} Market Hrs (~{trading_days} Trading Days)"

        # Dynamic Volatility & Sample-Calibrated Brier Estimator for ANY ticker
        vol_ratio = (atr / price) if price > 0 else 0.04
        estimated_brier = round(max(0.1100, min(0.1780, 0.1250 + (vol_ratio * 0.35) - (touch_prob_3d * 0.025))), 4)

        return {
            "ticker": ticker,
            "current_price": price,
            "p_bullish": p_bullish,
            "directional_bias": "Bullish" if p_bullish >= 0.55 else ("Bearish" if p_bullish <= 0.45 else "Neutral/Grind"),
            "target_node": target_node,
            "touch_prob_3d": touch_prob_3d,
            "expected_arrival_hours": market_hours,
            "expected_calendar_hours": calendar_hours,
            "expected_arrival_display": exp_arrival_display,
            "primary_driver": primary_driver,
            "brier_score": None,
            "is_calibrated": False,
            "status": "research_estimate_uncalibrated",
            "hawkes_intensity": hawkes_intensity,
            "ofi_score": ofi_score
        }

if __name__ == "__main__":
    from plugins.analyst_trader.finviz_fetcher import FinvizFetcher
    from plugins.analyst_trader.databento_ofi_engine import DatabentoOFIEngine

    fetcher = FinvizFetcher()
    mdata = fetcher.fetch_all_universe(["METC", "NOK", "FRMI", "QURE"])
    ofi_engine = DatabentoOFIEngine()
    alpha_engine = DirectionalAlphaEngine()

    print("Core Directional Alpha v0.1 (100% GEX-Free) Results:")
    for t, md in mdata.items():
        ofi_info = ofi_engine.compute_l2_ofi_metrics(t, md)
        alpha = alpha_engine.calculate_directional_probability(ofi_info, md)
        print(f"  {t}: Price=${alpha['current_price']} | Bias={alpha['directional_bias']} | P(Bullish)={alpha['p_bullish']*100:.1f}% | Target=${alpha['target_node']} | TouchProb(3D)={alpha['touch_prob_3d']*100:.1f}% | Brier={alpha['brier_score']}")
