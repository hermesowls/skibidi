"""AB Trades Analyst Scraper.

Handles AB's format: $BIDU 9/18 130c 3.15, $CVNA 8/21 70c 100% - closed, and # Unrealized / # Realized lists.
"""

import re
from typing import Any, Dict, List, Optional
from plugins.analyst_trader.scrapers.base import BaseAnalystScraper


class ABScraper(BaseAnalystScraper):
    def __init__(self) -> None:
        super().__init__("AB")

    def extract_candidates(self, message: Dict[str, Any], context_history: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        content = message.get("content", "")
        if not content:
            return []

        candidates = []

        # Line-by-line processing for AB multi-line portfolio dumps
        lines = content.splitlines()
        for line in lines:
            line_str = line.strip()
            if not line_str or line_str.startswith("#"):
                continue

            # Check closed / realized lines first
            # e.g., $CVNA 8/21 70c 100% - closed
            m_c = re.search(
                r"\$?(?P<ticker>[A-Z]{1,5})\s+(?P<exp>\d{1,2}/\d{1,2})?\s*(?P<strike>\d+(?:\.\d+)?)(?P<type>c|p|call|put)?\s+(?P<roi>\d+)%\s*-\s*(?P<action>closed|trimmed)",
                line_str,
                re.IGNORECASE
            )
            if m_c:
                act = "EXIT" if m_c.group("action").lower() == "closed" else "TRIM"
                try:
                    roi = float(m_c.group("roi"))
                except Exception:
                    roi = 0.0

                candidates.append({
                    "action": act,
                    "ticker": m_c.group("ticker").upper(),
                    "asset_type": "option",
                    "direction": "call" if (m_c.group("type") or "c").lower().startswith("c") else "put",
                    "strike": float(m_c.group("strike")) if m_c.group("strike") else None,
                    "expiration": m_c.group("exp"),
                    "pct_roi": roi,
                    "trim_ratio": 1.0 if act == "EXIT" else 0.5,
                    "source_text": line_str,
                    "analyst_name": "AB"
                })
                continue

            # Check entry plays
            # e.g., $BIDU 9/18 130c 3.15 (-80%)
            m_e = re.search(
                r"\$?(?P<ticker>[A-Z]{1,5})\s+(?P<exp>\d{1,2}/\d{1,2})\s+(?P<strike>\d+(?:\.\d+)?)(?P<type>c|p|call|put)\s+(?P<price>\d+(?:\.\d+)?)",
                line_str,
                re.IGNORECASE
            )
            if m_e:
                try:
                    price = float(m_e.group("price"))
                except Exception:
                    price = 1.0

                candidates.append({
                    "action": "ENTRY",
                    "ticker": m_e.group("ticker").upper(),
                    "asset_type": "option",
                    "direction": "call" if m_e.group("type").lower().startswith("c") else "put",
                    "strike": float(m_e.group("strike")),
                    "expiration": m_e.group("exp"),
                    "price": price,
                    "weight": 1.0,
                    "source_text": line_str,
                    "analyst_name": "AB"
                })

        return candidates
