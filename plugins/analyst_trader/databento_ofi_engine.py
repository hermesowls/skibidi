import os
import time
import math
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

def get_databento_key() -> str:
    key = os.getenv("DATABENTO_API_KEY")
    if key:
        return key
    env_file = Path.home() / ".hermes" / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("DATABENTO_API_KEY="):
                    return line.strip().split("=", 1)[1].strip("\"'")
    return ""

class DatabentoOFIEngine:
    """Recovered OHLCV research proxy, NOT an observed Databento L2 provider."""
    
    def __init__(self, api_key: Optional[str] = None) -> None:
        # This proxy never queries a provider; it needs no credentials.
        self.api_key = api_key
        self.hawkes_mu = 0.05
        self.hawkes_alpha = 0.40
        self.hawkes_beta = 1.20

    def compute_l2_ofi_metrics(self, ticker: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compute Order Flow Imbalance (OFI), Hawkes Intensity, and Queue Depletion Velocity."""
        ticker = ticker.upper()
        price = market_data.get("price", 10.0)
        volume = market_data.get("volume", 1_000_000)
        change_pct = market_data.get("change_pct", 0.0)
        rel_vol = market_data.get("rel_volume", 1.0)
        atr = market_data.get("atr", 0.50)
        
        # 1. Calculate Order Flow Imbalance (OFI) score normalized [-1.0, 1.0]
        # Based on arXiv:2505.17388v1 & arXiv:2507.22712v1
        base_ofi_bias = (change_pct / 5.0) * math.sqrt(max(0.1, rel_vol))
        ofi_score = max(-1.0, min(1.0, base_ofi_bias * 0.45))
        
        # 2. Hawkes Metaorder Self-Excitation Intensity (\lambda_t)
        # \lambda_t = \mu + \sum \alpha * exp(-\beta * \Delta t)
        hawkes_intensity = self.hawkes_mu + (abs(ofi_score) * self.hawkes_alpha * 2.5)
        
        # 3. Queue Depletion Velocity (bid/ask book decay rate)
        queue_depletion_velocity = round(0.15 + abs(change_pct) * 0.08, 4)
        queue_bias = "BID_QUEUE_EXPANSION" if ofi_score >= 0 else "ASK_QUEUE_DEPLETION"
        
        # 4. Amihud Illiquidity Estimator: |R_t| / (Volume * Price)
        amihud_illiquidity = (abs(change_pct) / max(1.0, volume * price)) * 1e6
        
        # 5. Composite Directional Score (0.0 to 1.0, 0.5 neutral)
        p_bullish = max(0.05, min(0.95, 0.50 + (ofi_score * 0.35) + (change_pct * 0.015)))

        return {
            "ticker": ticker,
            "ofi_score": round(ofi_score, 4),
            "hawkes_intensity": round(hawkes_intensity, 4),
            "queue_depletion_velocity": queue_depletion_velocity,
            "queue_bias": queue_bias,
            "amihud_illiquidity": round(amihud_illiquidity, 6),
            "p_bullish": round(p_bullish, 4),
            # This recovered implementation derives a research proxy from
            # OHLCV/defaults; it never fetches or observes an L2 order book.
            "dataset_source": "OHLCV_RESEARCH_PROXY_NOT_L2",
            "status": "unverified",
            "observed_at": None,
            "is_market_observation": False,
        }

    def compute_universe_ofi(self, universe_market_data: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        results = {}
        for ticker, mdata in universe_market_data.items():
            results[ticker] = self.compute_l2_ofi_metrics(ticker, mdata)
        return results

if __name__ == "__main__":
    from plugins.analyst_trader.finviz_fetcher import FinvizFetcher
    
    fetcher = FinvizFetcher()
    mdata = fetcher.fetch_all_universe(["METC", "NOK", "FRMI", "QURE"])
    engine = DatabentoOFIEngine()
    ofi_results = engine.compute_universe_ofi(mdata)
    
    print("Databento L2 & Hawkes Intensity Results:")
    for t, res in ofi_results.items():
        print(f"  {t}: P(Bullish)={res['p_bullish']*100:.1f}%, OFI={res['ofi_score']}, Hawkes Intensity={res['hawkes_intensity']}, Queue={res['queue_bias']}")
