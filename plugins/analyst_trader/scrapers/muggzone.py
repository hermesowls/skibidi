"""Muggzone Options Analyst Scraper.

Handles Muggzone's TP updates: CMG Calls up 24%, All 3TPs Hit for 100%, Second TP Hit on NVDA puts.
"""

import re
from typing import Any, Dict, List, Optional
from plugins.analyst_trader.scrapers.base import BaseAnalystScraper


class MuggzoneScraper(BaseAnalystScraper):
    def __init__(self) -> None:
        super().__init__("Muggzone Options")

    def extract_candidates(self, message: Dict[str, Any], context_history: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        content = message.get("content", "")
        if not content:
            return []

        candidates = []
        # Pattern 1: CMG Calls up 24% @everyone
        m1 = re.search(
            r"(?P<ticker>[A-Z]{1,5})\s+(?P<type>calls|puts)\s+(?:up|down)?\s*(?P<roi>\d+)%",
            content,
            re.IGNORECASE
        )
        if m1:
            try:
                roi = float(m1.group("roi"))
            except Exception:
                roi = 0.0

            candidates.append({
                "action": "TRIM",
                "ticker": m1.group("ticker").upper(),
                "asset_type": "option",
                "direction": "call" if m1.group("type").lower().startswith("call") else "put",
                "pct_roi": roi,
                "trim_ratio": 0.5,
                "source_text": content,
                "analyst_name": "Muggzone Options"
            })
            return candidates

        # Pattern 2: Second TP Hit on NVDA puts
        m2 = re.search(
            r"(?:TP|TARGET)\s*(?:HIT|REACHED)?\s+ON\s+(?P<ticker>[A-Z]{1,5})\s+(?P<type>calls|puts)",
            content,
            re.IGNORECASE
        )
        if m2:
            candidates.append({
                "action": "TRIM",
                "ticker": m2.group("ticker").upper(),
                "asset_type": "option",
                "direction": "call" if m2.group("type").lower().startswith("call") else "put",
                "trim_ratio": 0.5,
                "source_text": content,
                "analyst_name": "Muggzone Options"
            })

        return candidates
