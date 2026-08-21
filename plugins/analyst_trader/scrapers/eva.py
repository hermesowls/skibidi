"""Eva Panda Analyst Scraper.

Handles Eva's embed formats ("Open", "Update:"), BTO QQQ 750C @ 0.54, GEX/VEX notes, and lotto plays.
"""

import re
from typing import Any, Dict, List, Optional
from plugins.analyst_trader.scrapers.base import BaseAnalystScraper


class EvaScraper(BaseAnalystScraper):
    def __init__(self) -> None:
        super().__init__("Eva")

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
        # Pattern: BTO QQQ 08/21/2026 750C @ 0.54 (lotto)
        bto_matches = re.finditer(
            r"(?:BTO|BUY)\s+(?P<ticker>[A-Z]{1,5})\s+(?P<exp>\d{1,2}/\d{1,2}(?:/\d{2,4})?)\s+(?P<strike>\d+(?:\.\d+)?)(?P<type>C|P|CALL|PUT)\s*(?:@|at|\$)?\s*(?P<price>\d+(?:\.\d+)?)",
            text,
            re.IGNORECASE
        )
        for m in bto_matches:
            try:
                price = float(m.group("price"))
            except Exception:
                price = 1.0

            candidates.append({
                "action": "ENTRY",
                "ticker": m.group("ticker").upper(),
                "asset_type": "option",
                "direction": "call" if m.group("type").upper().startswith("C") else "put",
                "strike": float(m.group("strike")),
                "expiration": m.group("exp"),
                "price": price,
                "weight": 1.0,
                "source_text": text,
                "analyst_name": "Eva"
            })

        # Pattern: Trim / Close updates in description or context
        if "CLOSED" in text.upper() or "STC" in text.upper() or "TRIM" in text.upper() or "FULLY OUT" in text.upper():
            ticker_match = re.search(r"\b([A-Z]{2,5})\b", text)
            if ticker_match:
                act = "EXIT" if any(w in text.upper() for w in ["CLOSED", "FULLY OUT", "ALL OUT"]) else "TRIM"
                candidates.append({
                    "action": act,
                    "ticker": ticker_match.group(1).upper(),
                    "asset_type": "option",
                    "direction": "call",
                    "trim_ratio": 1.0 if act == "EXIT" else 0.5,
                    "source_text": text,
                    "analyst_name": "Eva"
                })

        return candidates
