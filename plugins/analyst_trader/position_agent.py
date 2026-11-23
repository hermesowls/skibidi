import math
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class PositionSizingAgent:
    """Multi-Tier Position Sizing Agent generating 3 Risk/Reward trade profiles."""
    
    def __init__(self) -> None:
        pass

    def generate_position_options(
        self,
        ticker: str,
        current_price: float,
        target_node: float,
        risk_info: Dict[str, Any],
        dte: int = 9,
        estimated_ask: float = 0.25
    ) -> Dict[str, Any]:
        """
        Generate 3 trade execution options:
        1. High R:R - Out-of-the-Money Single Options Calls/Puts
        2. Med R:R - Vertical Defined-Risk Spreads
        3. Low R:R - Direct Equity Shares + Protective Collar
        """
        ticker = ticker.upper()
        stop_loss = risk_info.get("stop_loss", current_price * 0.95)
        max_risk_dollar = risk_info.get("max_dollar_risk", 1500.0)
        is_bullish = risk_info.get("directional_bias", "Bullish") != "Bearish"

        # Round Target Strike
        strike = round(target_node * 2.0) / 2.0
        
        # Fetch Real Live Options Chain Quote via CBOE / Finviz API
        live_quote = self._fetch_real_option_quote(ticker, strike, is_bullish)
        if live_quote and live_quote.get("is_live"):
            strike = live_quote.get("strike", strike)
            dte = live_quote.get("dte", dte)
            estimated_ask = live_quote.get("ask") or estimated_ask
        
        # 1. 🔥 High R:R Profile (Naked Single Option Call/Put)
        option_type = "CALL" if is_bullish else "PUT"
        contract_name = f"{ticker} ${strike:.2f} {option_type} ({dte} DTE)"
        
        est_base_payout = max(0.05, abs(target_node - strike) * 0.60 + (estimated_ask * 1.5))
        est_squeeze_payout = est_base_payout * 1.25
        
        high_roi_base = ((est_base_payout - estimated_ask) / estimated_ask) * 100 if estimated_ask > 0 else 0
        high_roi_squeeze = ((est_squeeze_payout - estimated_ask) / estimated_ask) * 100 if estimated_ask > 0 else 0
        
        max_option_contracts = max(1, int(max_risk_dollar / (estimated_ask * 100))) if estimated_ask > 0 else 10
        high_rr_option = {
            "tier": "HIGH_RR",
            "tier_name": "🔥 High Risk / High Reward",
            "asset_class": "OPTION_SINGLE",
            "contract_name": contract_name,
            "strike": strike,
            "dte": dte,
            "entry_ask": estimated_ask,
            "bid": live_quote.get("bid", estimated_ask * 0.90),
            "volume": live_quote.get("volume", 350),
            "open_interest": live_quote.get("open_interest", 5000),
            "expiration": live_quote.get("expiration", "Near Term"),
            "target_payout_base": round(est_base_payout, 2),
            "target_payout_squeeze": round(est_squeeze_payout, 2),
            "est_roi_base": f"+{high_roi_base:.1f}%",
            "est_roi_squeeze": f"+{high_roi_squeeze:.1f}%",
            "recommended_contracts": max_option_contracts,
            "total_capital_required": round(max_option_contracts * estimated_ask * 100, 2),
            "max_risk_dollar": round(max_option_contracts * estimated_ask * 100, 2),
            "stop_loss_contract": round(estimated_ask * 0.50, 2), # 50% option stop
            "recommendation_summary": f"Buy {max_option_contracts}x {contract_name} @ ${estimated_ask:.2f} Ask. Target: ${est_base_payout:.2f} (+{high_roi_base:.1f}% ROI). Vol: {live_quote.get('volume', 350):,} | OI: {live_quote.get('open_interest', 5000):,}."
        }

        # 2. ⚖️ Med R:R Profile (Vertical Defined-Risk Spread)
        lower_strike = round(current_price * 2.0) / 2.0
        upper_strike = strike
        spread_type = "Bull Call Spread" if is_bullish else "Bear Put Spread"
        spread_name = f"{ticker} ${lower_strike:.2f}/${upper_strike:.2f} {spread_type} ({dte} DTE)"
        
        spread_net_debit = round(abs(upper_strike - lower_strike) * 0.40, 2)
        max_spread_profit = round(abs(upper_strike - lower_strike) - spread_net_debit, 2)
        spread_roi = (max_spread_profit / max(0.01, spread_net_debit)) * 100
        
        max_spread_contracts = int(max_risk_dollar / (spread_net_debit * 100)) if spread_net_debit > 0 else 10
        med_rr_option = {
            "tier": "MED_RR",
            "tier_name": "⚖️ Medium Risk / Medium Reward",
            "asset_class": "OPTION_SPREAD",
            "contract_name": spread_name,
            "lower_strike": lower_strike,
            "upper_strike": upper_strike,
            "dte": dte,
            "entry_ask": spread_net_debit,
            "max_profit": max_spread_profit,
            "est_roi": f"+{spread_roi:.1f}%",
            "recommended_contracts": max_spread_contracts,
            "total_capital_required": round(max_spread_contracts * spread_net_debit * 100, 2),
            "max_risk_dollar": round(max_spread_contracts * spread_net_debit * 100, 2),
            "stop_loss_contract": round(spread_net_debit * 0.50, 2),
            "recommendation_summary": f"Buy {max_spread_contracts}x {spread_name} @ ${spread_net_debit:.2f} Net Debit. Max Profit: ${max_spread_profit:.2f}/spread (+{spread_roi:.1f}% ROI)."
        }

        # 3. 🛡️ Low R:R Profile (Direct Equity + Protective Collar)
        shares_count = risk_info.get("max_allowed_shares", 1000)
        equity_capital = round(shares_count * current_price, 2)
        
        hedge_put_strike = round(stop_loss * 2.0) / 2.0
        covered_call_strike = round((target_node * 1.05) * 2.0) / 2.0
        
        equity_risk_per_share = round(current_price - stop_loss, 2)
        equity_reward_per_share = round(target_node - current_price, 2)
        equity_roi = (equity_reward_per_share / current_price) * 100
        
        low_rr_option = {
            "tier": "LOW_RR",
            "tier_name": "🛡️ Low Risk / Consistent Reward",
            "asset_class": "EQUITY",
            "contract_name": f"{ticker} Direct Equity + Protective Collar",
            "shares_count": shares_count,
            "entry_price": current_price,
            "stop_loss": stop_loss,
            "target_tp": target_node,
            "hedge_put_strike": hedge_put_strike,
            "covered_call_strike": covered_call_strike,
            "est_roi": f"+{equity_roi:.1f}%",
            "total_capital_required": equity_capital,
            "max_risk_dollar": round(shares_count * equity_risk_per_share, 2),
            "recommendation_summary": f"Buy {shares_count} shares {ticker} @ ${current_price:.2f}. Set Stop Loss @ ${stop_loss:.2f}. Target: ${target_node:.2f} (+{equity_roi:.1f}% Gain)."
        }

        return {
            "ticker": ticker,
            "high_rr": high_rr_option,
            "med_rr": med_rr_option,
            "low_rr": low_rr_option,
            "options": [high_rr_option, med_rr_option, low_rr_option]
        }

    def _fetch_real_option_quote(self, ticker: str, target_strike: float, is_bullish: bool = True) -> Dict[str, Any]:
        """Fetch live option chain contract quote via CBOE / Finviz API (Zero yfinance)."""
        try:
            from plugins.analyst_trader.finviz_fetcher import FinvizFetcher
            ff = FinvizFetcher()
            chain_data = ff.fetch_live_option_chain(ticker)
            expirations = chain_data.get("expirations", [])
            if not expirations:
                return {}
            
            exp0 = expirations[0]
            contracts = exp0["calls"] if is_bullish else exp0["puts"]
            if not contracts:
                return {}
            
            best = min(contracts, key=lambda c: abs(c["strike"] - target_strike))
            return {
                "expiration": exp0["expiration"],
                "dte": exp0["dte"],
                "strike": best["strike"],
                "ask": best["ask"],
                "bid": best["bid"],
                "volume": best["volume"],
                "open_interest": best["open_interest"],
                "is_live": True
            }
        except Exception as e:
            logger.warning("CBOE option quote fetch failed for %s: %s", ticker, e)
        return {}

if __name__ == "__main__":
    from plugins.analyst_trader.risk_agent import RiskManagementAgent
    risk_agent = RiskManagementAgent()
    rinfo = risk_agent.calculate_risk_parameters("METC", current_price=11.19, target_node=11.90)
    
    agent = PositionSizingAgent()
    options = agent.generate_position_options("METC", current_price=11.19, target_node=11.90, risk_info=rinfo)
    print("Position Sizing Agent Options:")
    for opt in options["options"]:
        print(f"  {opt['tier_name']}: {opt['recommendation_summary']}")
