"""Live Stock and Option Contract Mark-to-Market Price Updater using Unusual Whales API."""

import json
import math
import logging
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, time as dtime
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from plugins.analyst_trader.db import AnalystDatabase

logger = logging.getLogger(__name__)

PACIFIC_TZ = ZoneInfo("America/Los_Angeles")

US_MARKET_HOLIDAYS_2026 = {
    "2026-01-01",  # New Year's Day
    "2026-01-19",  # MLK Jr. Day
    "2026-02-16",  # Washington's Birthday (Presidents Day)
    "2026-04-03",  # Good Friday
    "2026-05-25",  # Memorial Day
    "2026-06-19",  # Juneteenth
    "2026-07-03",  # Independence Day (Observed)
    "2026-09-07",  # Labor Day
    "2026-11-26",  # Thanksgiving Day
    "2026-12-25",  # Christmas Day
}


class UnusualWhalesPriceUpdater:
    """Updates live option contract and stock mark-to-market prices using Unusual Whales API."""

    def __init__(self, db: Optional[AnalystDatabase] = None, *, offline: bool = False) -> None:
        if offline and db is None:
            raise ValueError('Offline updater requires an explicit database')
        self.db = db or AnalystDatabase()
        self.offline = offline
        self.api_key = '' if offline else os.getenv("UNUSUAL_WHALES_API_KEY", "")
        if not offline and not self.api_key:
            from hermes_constants import get_hermes_home
            env_paths = [get_hermes_home() / '.env']
            for p in env_paths:
                if p.exists():
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            for line in f:
                                if line.startswith("UNUSUAL_WHALES_API_KEY="):
                                    self.api_key = line.strip().split("=", 1)[1].strip("\"'")
                                    if self.api_key:
                                        os.environ["UNUSUAL_WHALES_API_KEY"] = self.api_key
                                        break
                    except Exception:
                        pass
                if self.api_key:
                    break

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "User-Agent": "HermesAgent/1.0"
        }

    def is_pricing_window_active(self, dt: Optional[datetime] = None) -> bool:
        """
        Returns True if current time is within trading pricing window:
        05:00 to 15:00 Pacific Time, Monday through Friday, excluding market holidays.
        """
        now_pt = dt.astimezone(PACIFIC_TZ) if dt else datetime.now(PACIFIC_TZ)
        if now_pt.weekday() >= 5:
            return False
        date_str = now_pt.strftime("%Y-%m-%d")
        if date_str in US_MARKET_HOLIDAYS_2026:
            return False
        t = now_pt.time()
        return dtime(5, 0) <= t <= dtime(15, 0)

    def fetch_unusual_whales_contracts_for_ticker(self, ticker: str) -> List[Dict[str, Any]]:
        """Fetch all option contracts for a ticker from Unusual Whales API."""
        if self.offline or not self.api_key:
            return []
        url = f"https://api.unusualwhales.com/api/stock/{ticker.upper()}/option-contracts"
        req = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                return data.get("data", [])
        except urllib.error.HTTPError as e:
            if e.code == 429:
                logger.warning("Unusual Whales 429 Too Many Requests on ticker %s. Daily/minute quota exhausted.", ticker)
            else:
                logger.debug("Failed Unusual Whales option lookup for %s: HTTP %s", ticker, e.code)
            return []
        except Exception as e:
            logger.debug("Failed Unusual Whales option lookup for %s: %s", ticker, e)
            return []

    def find_contract_price(
        self,
        contracts: List[Dict[str, Any]],
        ticker: str,
        strike: float,
        direction: str,
        expiration: Optional[str] = None
    ) -> Optional[float]:
        """Match the full OCC identity. A last trade is a mark, not an executable bid.

        Legacy month/day-only expirations remain unknown; never guess the year or
        fall back to another expiry. Fresh quote admission belongs to execution.
        """
        import re
        from decimal import Decimal, InvalidOperation
        if direction not in ('call', 'put', 'C', 'P') or isinstance(strike, bool):
            return None
        if not isinstance(expiration, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', expiration):
            return None
        try:
            expiry = datetime.strptime(expiration, '%Y-%m-%d')
            strike_units = Decimal(str(strike)) * 1000
            if not strike_units.is_finite() or not 0 < strike_units <= 99999999 or strike_units != strike_units.to_integral_value():
                return None
        except (ValueError, TypeError, InvalidOperation):
            return None
        right = 'C' if direction in ('call', 'C') else 'P'
        for contract in contracts:
            symbol = contract.get('option_symbol')
            if not isinstance(symbol, str):
                continue
            match = re.fullmatch(r'([A-Z][A-Z0-9.]{0,5}) *(\d{6})([CP])(\d{8})', symbol)
            if not match or (match[1], match[2], match[3], int(match[4])) != (ticker, expiry.strftime('%y%m%d'), right, int(strike_units)):
                continue
            price = contract.get('last_price')
            if price is None or isinstance(price, bool):
                continue
            try:
                price = float(price)
            except (TypeError, ValueError, OverflowError):
                continue
            if math.isfinite(price) and 0 < price <= 1000000:
                return price
        return None

    def fetch_unusual_whales_option_price(
        self,
        ticker: str,
        strike: float,
        direction: str,
        expiration: Optional[str] = None
    ) -> Optional[float]:
        """Fetch latest option contract last price from Unusual Whales API (single contract lookup)."""
        contracts = self.fetch_unusual_whales_contracts_for_ticker(ticker)
        return self.find_contract_price(contracts, ticker, strike, direction, expiration)

    def fetch_alpaca_stock_price(self, ticker: str) -> Optional[float]:
        """Fetch latest stock price snapshot from Alpaca as fallback for equity positions."""
        if self.offline:
            return None
        alpaca_key = os.getenv("ALPACA_API_KEY", "")
        alpaca_sec = os.getenv("ALPACA_SECRET_KEY", "")
        if not alpaca_key:
            return None
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

    def update_open_positions_mark_to_market(self, force: bool = False) -> Dict[str, Any]:
        """Query open positions, fetch live contract or stock prices, and update SQLite.

        Restricted to 05:00-15:00 Pacific Time on weekdays unless force=True.
        Deduplicates Unusual Whales API calls by ticker so each unique ticker is only fetched once per cycle.
        """
        now_iso = datetime.now().isoformat()
        if not force and not self.is_pricing_window_active():
            logger.debug("Mark-to-market pricing window inactive (outside 05:00-15:00 PST Mon-Fri); skipping quote update.")
            return {
                "status": "skipped",
                "reason": "outside_market_hours",
                "positions_updated": 0,
                "timestamp": now_iso
            }

        conn = self.db._get_connection()
        open_positions = self.db.list_positions(status="OPEN")
        updated_count = 0
        contracts_cache: Dict[str, List[Dict[str, Any]]] = {}

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
                    if ticker not in contracts_cache:
                        contracts_cache[ticker] = self.fetch_unusual_whales_contracts_for_ticker(ticker)
                    live_price = self.find_contract_price(
                        contracts_cache[ticker],
                        ticker,
                        float(strike),
                        direction,
                        exp
                    )

                # Strictly stock only if equity
                if live_price is None and asset_type == "equity":
                    live_price = self.fetch_alpaca_stock_price(ticker)

                if live_price is None or isinstance(live_price, bool) or not math.isfinite(live_price) or not 0 < live_price <= 1000000:
                    continue

                # ROI % calculation based on contract entry vs live contract price
                if asset_type == 'option' or direction in ("call", "long"):
                    roi_pct = ((live_price - entry_p) / entry_p) * 100.0 if entry_p > 0 else 0.0
                else:
                    roi_pct = ((entry_p - live_price) / entry_p) * 100.0 if entry_p > 0 else 0.0

                if not math.isfinite(roi_pct):
                    continue
                conn.execute("""
                    UPDATE positions SET
                        current_price = ?,
                        roi_pct = ?,
                        last_price_updated_at = ?,
                        updated_at = ?
                    WHERE position_id = ?
                """, (round(live_price, 2), round(roi_pct, 2), now_iso, now_iso, pos_id))
                updated_count += 1

        logger.info(
            "Unusual Whales mark-to-market updated %d open positions (queried %d unique tickers) at %s",
            updated_count,
            len(contracts_cache),
            now_iso
        )
        return {
            "status": "success",
            "positions_updated": updated_count,
            "tickers_queried": len(contracts_cache),
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
