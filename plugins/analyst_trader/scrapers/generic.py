"""Generic Fallback Analyst Scraper.

Handles remaining analyst channels using standard regex option rules.
"""

import re
from typing import Any, Dict, List, Optional
from plugins.analyst_trader.scrapers.base import BaseAnalystScraper


class GenericScraper(BaseAnalystScraper):
    def __init__(self, analyst_name: str = "Analyst") -> None:
        super().__init__(analyst_name)

    def extract_candidates(self, message: Dict[str, Any], context_history: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        content = message.get("content", "")
        embeds = message.get("embeds", []) or []

        title = ""
        desc = ""
        for emb in embeds:
            if isinstance(emb, dict):
                title = (emb.get("title") or "").strip()
                desc = (emb.get("description") or "").strip()
                break

        text = desc if desc else content
        if not text:
            return []

        candidates = []
        combined_upper = (title + " " + text).upper()

        if "OPEN" in title.upper() or "BTO" in combined_upper or "BUY" in combined_upper:
            m = re.search(
                r"\b(?P<ticker>[A-Z]{1,5})\s+(?P<strike>\d+(?:\.\d+)?)(?P<type>C|P|CALL|PUT)\s+(?P<exp>\d{1,2}/\d{1,2}(?:/\d{2,4})?)",
                text,
                re.IGNORECASE
            )
            if m:
                candidates.append({
                    "action": "ENTRY",
                    "ticker": m.group("ticker").upper(),
                    "asset_type": "option",
                    "direction": "call" if m.group("type").upper().startswith("C") else "put",
                    "strike": float(m.group("strike")),
                    "expiration": m.group("exp"),
                    "price": 1.0,
                    "weight": 1.0,
                    "source_text": text,
                    "analyst_name": self.analyst_name
                })

        return candidates
