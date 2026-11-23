import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class RiskManagementAgent:
    """Risk Management Agent computing ATR & Gamma Support Stop Losses, Take Profits, and Drawdown Caps."""
    
    def __init__(self, portfolio_equity: float = 100_000.0, max_risk_pct: float = 0.015) -> None:
        self.portfolio_equity = portfolio_equity
        self.max_risk_pct = max_risk_pct # 1.5% max account equity risk per trade

    def calculate_risk_parameters(
        self,
        ticker: str,
        current_price: float,
        target_node: float,
        directional_bias: str = "Bullish",
        atr: float = 0.50,
        gex_regime: str = "Negative Gamma"
    ) -> Dict[str, Any]:
        """
        Calculate dynamic Stop-Loss (SL), Take-Profit targets (TP1 & TP2), Risk/Reward ratio,
        and max position size based on portfolio equity risk cap.
        """
        ticker = ticker.upper()
        atr = max(0.10, atr)
        
        is_bullish = "Bullish" in directional_bias or directional_bias == "AGGRESSIVE BREAKOUT LONG"
        
        # 1. Dynamic Stop Loss (ATR + Key Support/Resistance Level)
        atr_stop_buffer = atr * 1.50
        if is_bullish:
            raw_sl = current_price - atr_stop_buffer
            # Protect against rounding too close to current price
            stop_loss = round(min(raw_sl, current_price * 0.965), 2)
            take_profit_1 = round(target_node, 2)
            take_profit_2 = round(current_price + (current_price - stop_loss) * 2.5, 2)
        else:
            raw_sl = current_price + atr_stop_buffer
            stop_loss = round(max(raw_sl, current_price * 1.035), 2)
            take_profit_1 = round(target_node, 2)
            take_profit_2 = round(current_price - (stop_loss - current_price) * 2.5, 2)
            
        # 2. Risk / Reward Calculation
        risk_per_share = abs(current_price - stop_loss)
        reward_per_share = abs(take_profit_1 - current_price)
        rr_ratio = round(reward_per_share / max(0.01, risk_per_share), 2)
        
        # 3. Account Portfolio Risk Sizing
        max_dollar_risk = self.portfolio_equity * self.max_risk_pct
        max_shares = int(max_dollar_risk / max(0.01, risk_per_share))
        max_equity_allocation = round(max_shares * current_price, 2)

        # 4. Trailing Stop Activation Level
        trailing_stop_activation = round(current_price + (reward_per_share * 0.50) if is_bullish else current_price - (reward_per_share * 0.50), 2)
        
        return {
            "ticker": ticker,
            "current_price": current_price,
            "directional_bias": directional_bias,
            "stop_loss": stop_loss,
            "take_profit_1": take_profit_1,
            "take_profit_2": take_profit_2,
            "risk_per_share": round(risk_per_share, 2),
            "reward_per_share": round(reward_per_share, 2),
            "rr_ratio": rr_ratio,
            "max_dollar_risk": round(max_dollar_risk, 2),
            "max_allowed_shares": max_shares,
            "max_equity_allocation": max_equity_allocation,
            "trailing_stop_activation": trailing_stop_activation,
            "portfolio_equity": self.portfolio_equity,
            "risk_cap_pct": self.max_risk_pct * 100
        }

if __name__ == "__main__":
    agent = RiskManagementAgent()
    res = agent.calculate_risk_parameters("METC", current_price=11.19, target_node=11.90, directional_bias="Bullish", atr=0.45)
    print("Risk Management Output for METC:", res)
