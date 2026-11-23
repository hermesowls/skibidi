import math
import numpy as np
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class TechnicalIndicatorsEngine:
    """Quantitative Technical Analysis Engine for TTM Squeeze, EMA Crossovers, and Trend Slopes."""
    
    def __init__(self, minimum_bars: int = 200) -> None:
        self.minimum_bars = max(200, minimum_bars)

    def compute_technical_indicators(
        self,
        prices: List[float],
        atr: float | None = None,
        rel_volume: float | None = None,
        intraday_volume: int | None = None
    ) -> Dict[str, Any]:
        """
        Compute Complete EMA Stack (8, 21, 50, 100, 200), TTM Squeeze, and Trend Alignment.
        Requires historical price series (up to 260 bars for true 200 EMA).
        """
        if not prices or len(prices) < self.minimum_bars:
            return self._fallback_indicators(prices, atr)
            
        series = np.array(prices, dtype=float)
        if not np.all(np.isfinite(series)) or np.any(series <= 0):
            return self._fallback_indicators([], atr)
        current_price = series[-1]
        n_bars = len(series)
        
        # 1. Calculate Full EMA Stack: 8, 21, 50, 100, 200
        ema8_arr = self._calc_ema(series, 8)
        ema21_arr = self._calc_ema(series, 21)
        ema50_arr = self._calc_ema(series, 50)
        ema100_arr = self._calc_ema(series, 100)
        ema200_arr = self._calc_ema(series, 200)
        
        ema8_val = float(ema8_arr[-1])
        ema21_val = float(ema21_arr[-1])
        ema50_val = float(ema50_arr[-1])
        ema100_val = float(ema100_arr[-1])
        ema200_val = float(ema200_arr[-1])
        
        ema8_prev = float(ema8_arr[-2]) if len(ema8_arr) > 1 else ema8_val
        ema21_prev = float(ema21_arr[-2]) if len(ema21_arr) > 1 else ema21_val
        
        # 8/21 Fast Crossover Signal
        is_bullish_cross = (ema8_prev <= ema21_prev) and (ema8_val > ema21_val)
        is_bearish_cross = (ema8_prev >= ema21_prev) and (ema8_val < ema21_val)
        
        # Complete EMA Stack Classification
        is_full_bullish_stack = (current_price > ema8_val > ema21_val > ema50_val > ema100_val > ema200_val)
        is_bullish_pullback = (current_price >= ema21_val and ema21_val > ema50_val and current_price > ema200_val)
        is_full_bearish_stack = (current_price < ema8_val < ema21_val < ema50_val < ema100_val < ema200_val)
        is_bearish_pullback = (current_price <= ema21_val and ema21_val < ema50_val and current_price < ema200_val)
        
        if is_full_bullish_stack:
            stack_state = "FULL_BULLISH_STACK"
            trend_score = 95
        elif is_bullish_cross:
            stack_state = "BULLISH_8_21_CROSS"
            trend_score = 88
        elif is_bullish_pullback:
            stack_state = "BULLISH_TREND_PULLBACK"
            trend_score = 80
        elif is_full_bearish_stack:
            stack_state = "FULL_BEARISH_STACK"
            trend_score = 10
        elif is_bearish_cross:
            stack_state = "BEARISH_8_21_CROSS"
            trend_score = 20
        elif is_bearish_pullback:
            stack_state = "BEARISH_TREND_PULLBACK"
            trend_score = 30
        elif current_price > ema200_val:
            stack_state = "ABOVE_200_EMA_CONSOLIDATING"
            trend_score = 65
        else:
            stack_state = "BELOW_200_EMA_CONSOLIDATING"
            trend_score = 40

        # 2. TTM Squeeze Calculation
        window = min(20, len(series))
        recent = series[-window:]
        sma20 = float(np.mean(recent))
        std20 = float(np.std(recent))
        
        bb_upper = sma20 + (2.0 * std20)
        bb_lower = sma20 - (2.0 * std20)
        atr_known = atr is not None and math.isfinite(atr) and atr > 0
        kc_upper = sma20 + (1.5 * atr) if atr_known and atr is not None else float('nan')
        kc_lower = sma20 - (1.5 * atr) if atr_known and atr is not None else float('nan')
        
        ttm_squeeze_active = (bb_upper < kc_upper) and (bb_lower > kc_lower)
        ttm_squeeze_fired = (bb_upper >= kc_upper) or (bb_lower <= kc_lower)
        
        momentum_val = round((current_price - sma20), 3)
        if not atr_known:
            squeeze_state = "UNKNOWN"
        elif ttm_squeeze_active:
            squeeze_state = "SQUEEZE_ACTIVE_COMPRESSION"
        elif ttm_squeeze_fired and momentum_val > 0:
            squeeze_state = "SQUEEZE_FIRED_BULLISH"
        elif ttm_squeeze_fired and momentum_val < 0:
            squeeze_state = "SQUEEZE_FIRED_BEARISH"
        else:
            squeeze_state = "NO_SQUEEZE"

        # 3. Volume & RVOL Confirmation
        rvol_val = float(rel_volume) if rel_volume is not None and math.isfinite(rel_volume) and rel_volume >= 0 else None
        rvol_elevated = rvol_val >= 1.5 if rvol_val is not None else None
        rvol_extreme = rvol_val >= 2.5 if rvol_val is not None else None
        volume_confirmed = bool(rvol_elevated or intraday_volume > 1_000_000) if intraday_volume is not None and rvol_val is not None else None

        # 4. Overall Technical Pass
        ta_bullish_pass = bool((ema8_val >= ema21_val or is_bullish_cross) and (current_price >= ema50_val or momentum_val > 0))
        ta_bearish_pass = bool((ema8_val <= ema21_val or is_bearish_cross) and (current_price <= ema50_val or momentum_val < 0))

        return {
            "current_price": round(float(current_price), 2),
            "ema8": round(ema8_val, 2),
            "ema21": round(ema21_val, 2),
            "ema50": round(ema50_val, 2),
            "ema100": round(ema100_val, 2),
            "ema200": round(ema200_val, 2),
            "ema_stack_state": stack_state,
            "trend_score": trend_score,
            "is_above_200_ema": bool(current_price > ema200_val),
            "is_full_bullish_stack": bool(is_full_bullish_stack),
            "ttm_squeeze_state": str(squeeze_state),
            "ttm_squeeze_active": bool(ttm_squeeze_active) if atr_known else None,
            "ttm_momentum": float(momentum_val),
            "rel_volume": round(rvol_val, 2) if rvol_val is not None else None,
            "volume_confirmed": volume_confirmed,
            "rvol_extreme": rvol_extreme,
            "ta_bullish_pass": ta_bullish_pass,
            "ta_bearish_pass": ta_bearish_pass,
            "ta_pass": ta_bullish_pass
        }

    def _calc_ema(self, series: np.ndarray, period: int) -> np.ndarray:
        period = max(1, period)
        multiplier = 2.0 / (period + 1.0)
        ema = np.zeros_like(series)
        ema[0] = series[0]
        for i in range(1, len(series)):
            ema[i] = (series[i] - ema[i - 1]) * multiplier + ema[i - 1]
        return ema

    def _fallback_indicators(self, prices: List[float], atr: float | None) -> Dict[str, Any]:
        result: Dict[str, Any] = dict.fromkeys(('current_price','ema8','ema21','ema50','ema100','ema200',
            'trend_score','is_above_200_ema','is_full_bullish_stack','ttm_squeeze_active',
            'ttm_momentum','rel_volume','volume_confirmed','rvol_extreme',
            'ta_bullish_pass','ta_bearish_pass','ta_pass'))
        result.update(ema_stack_state='UNKNOWN', ttm_squeeze_state='UNKNOWN',
                      uncertainty='insufficient_or_invalid_observed_bars')
        return result

if __name__ == "__main__":
    engine = TechnicalIndicatorsEngine()
    test_prices = [10.0, 10.1, 10.2, 10.15, 10.3, 10.4, 10.5, 10.6, 10.75, 10.9, 11.19]
    res = engine.compute_technical_indicators(test_prices, atr=0.35)
    print("Technical Indicators Output:", res)
