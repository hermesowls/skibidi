"""Live Stock and Option Contract Mark-to-Market Price Updater using Unusual Whales API."""

import json
import logging
import os
import time
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional

from plugins.analyst_trader.db import AnalystDatabase

logger = logging.getLogger(__name__)


class UnusualWhalesPriceUpdater:
    """Updates live option contract and stock mark-to-market prices using Unusual Whales API."""

    def __init__(self, db: Optional[AnalystDatabase] = None) -> None:
        self.db = db or AnalystDatabase()
        self.api_key = os.getenv("UNUSUAL_WHALES_API_KEY", "179ee2b3-3f79-4f10-b5fe-2aa3d82d36ce")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "User-Agent": "HermesAgent/1.0"
        }

    def fetch_unusual_whales_option_price(self, ticker: str, strike: float, direction: str, expiration: Optional[str] = None) -> Optional[float]:
        """Fetch latest option contract last price from Unusual Whales API."""
        url = f"https://api.unusualwhales.com/api/stock/{ticker.upper()}/option-contracts"
        req = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                contracts = data.get("data", [])
                opt_type = "C" if direction.lower().startswith("c") or direction.lower() == "long" else "P"
                strike_target = float(strike)

                # 1. Match by exact expiration month/day + strike + option type
                if expiration:
                    parts = [p.strip() for p in expiration.split("/") if p.strip()]
                    if len(parts) >= 2:
                        m_str = f"{int(parts[0]):02d}"
                        d_str = f"{int(parts[1]):02d}"
                        target_exp_sub = f"{m_str}{d_str}"
                        for c in contracts:
                            sym = c.get("option_symbol") or ""
                            if len(sym) >= 15:
                                # OCC format: TICKER (var) YYMMDD (6) C/P (1) STRIKE (8)
                                exp_part = sym[len(ticker):len(ticker)+6] if len(sym) >= len(ticker)+7 else ""
                                if target_exp_sub in exp_part:
                                    c_type = "C" if "C" in sym else "P"
                                    try:
                                        c_strike = float(sym[-8:]) / 1000.0
                                        if abs(c_strike - strike_target) < 0.01 and c_type == opt_type:
                                            lp = c.get("last_price")
                                            if lp is not None:
                                                return float(lp)
                                    except Exception:
                                        pass

                # 2. Fallback match by strike and option type
                for c in contracts:
                    sym = c.get("option_symbol") or ""
                    if len(sym) >= 10:
                        c_type = "C" if "C" in sym else "P"
                        try:
                            c_strike = float(sym[-8:]) / 1000.0
                            if abs(c_strike - strike_target) < 0.01 and c_type == opt_type:
                                lp = c.get("last_price")
                                if lp is not None:
                                    return float(lp)
                        except Exception:
                            pass
        except Exception as e:
            logger.debug("Failed Unusual Whales option lookup for %s: %s", ticker, e)
        return None

    def fetch_alpaca_stock_price(self, ticker: str) -> Optional[float]:
        """Fetch latest stock price snapshot from Alpaca as fallback for equity positions."""
        alpaca_key = os.getenv("ALPACA_API_KEY", "PKCYHR5AL6F3P4M7FYQDD4XW4J")
        alpaca_sec = os.getenv("ALPACA_SECRET_KEY", "Dsrfn4ge73X7Av8MmbFsMF7TVLh9LfQPhkynKLEFuzPn")
        url = f"https://data.alpaca.markets/v2/stocks/{ticker.upper()}/snapshot"
        req = urllib.request.Request(url, headers={
            "APCA-API-KEY-ID": alpaca_key,
            "APCA-API-SECRET-KEY": alpaca_sec,
            "Accept": "application/json"
        })
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                trade = data.get("latestTrade", {})
                return float(trade["p"]) if "p" in trade else None
        except Exception as e:
            logger.debug("Failed stock snapshot for %s: %s", ticker, e)
            return None

    def update_open_positions_mark_to_market(self) -> Dict[str, Any]:
        """Query open positions, fetch live contract or stock prices from Unusual Whales, and update SQLite."""
        conn = self.db._get_connection()
        open_positions = self.db.list_positions(status="OPEN")
        updated_count = 0
        now_iso = datetime.now().isoformat()

        with conn:
            for pos in open_positions:
                pos_id = pos["position_id"]
                ticker = pos["ticker"]
                entry_p = float(pos["entry_price"])
                asset_type = pos["asset_type"]
                direction = pos["direction"]
                strike = pos.get("strike")
                exp = pos.get("expiration")

                live_price = None
                if asset_type == "option" and strike:
                    live_price = self.fetch_unusual_whales_option_price(ticker, float(strike), direction, exp)

                # Strictly stock only if equity
                if live_price is None and asset_type == "equity":
                    live_price = self.fetch_alpaca_stock_price(ticker)

                if live_price is None or live_price <= 0:
                    continue

                # ROI % calculation based on contract entry vs live contract price
                if direction in ("call", "long"):
                    roi_pct = ((live_price - entry_p) / entry_p) * 100.0 if entry_p > 0 else 0.0
                else:
                    roi_pct = ((entry_p - live_price) / entry_p) * 100.0 if entry_p > 0 else 0.0

                conn.execute("""
                    UPDATE positions SET
                        current_price = ?,
                        roi_pct = ?,
                        last_price_updated_at = ?,
                        updated_at = ?
                    WHERE position_id = ?
                """, (round(live_price, 2), round(roi_pct, 2), now_iso, now_iso, pos_id))
                updated_count += 1

        logger.info("Unusual Whales mark-to-market updated %d open positions at %s", updated_count, now_iso)
        return {
            "status": "success",
            "positions_updated": updated_count,
            "last_price_updated_at": now_iso
        }

    def start_5min_updater_loop(self, interval_seconds: int = 300) -> None:
        """Run continuous 5-minute price update loop using Unusual Whales."""
        logger.info("Starting Unusual Whales 5-minute price mark-to-market updater loop...")
        while True:
            try:
                self.update_open_positions_mark_to_market()
            except Exception as e:
                logger.error("Error during price mark-to-market update: %s", e)
            time.sleep(interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    updater = UnusualWhalesPriceUpdater()
    res = updater.update_open_positions_mark_to_market()
    print("Unusual Whales Mark-to-Market Result:", res)
