"""Embed-Title Trade Signal Parser for Owls Analyst Alerts."""

import json
import re
from typing import Any, Dict, List, Optional

# Ticker Blacklist
TICKER_BLACKLIST = {
    "STC", "BTO", "STO", "BTC", "BUY", "SELL", "OPEN", "CLOSE", "UPDATE", "MESSAGE",
    "INFO", "BOT", "HERO", "LOTTO", "PM", "AM", "ABOVE", "INTO", "EXP", "TO", "A",
    "LLC", "INC", "THE", "AND", "FOR", "WITH", "THAT", "THIS", "SOME", "TODAY",
    "NOW", "NEW", "ATH", "HOD", "LOD", "FREE", "RUNNER", "RUNNERS", "OR", "AT",
    "SOLD", "CAN", "FULLY", "OUT", "TAKE", "JUST", "GOOD", "GET", "LOOK", "HAVE",
    "ANOTHER", "MORE", "LESS", "HALF", "PROFIT", "PROFITS", "SOME", "FEW", "PAID"
}

OPTION_REGEX = re.compile(
    r"(?P<ticker>[A-Z]{1,5})\s+"
    r"(?P<strike>\$?\d+(?:\.\d+)?)\s*"
    r"(?P<type>C|P|CALL|PUT)\b"
    r"(?:\s*(?:exp(?:iring)?\s*)?(?P<exp>\d{1,2}/\d{1,2}(?:/\d{2,4})?))?",
    re.IGNORECASE
)

# Improved Price Extractor for .95, 2 premium, @ 2.15, $3.80, etc.
PRICE_REGEX = re.compile(
    r"(?:@|at|price|premium|exp\s+at|\$)\s*\$?(?P<price>\d*\.?\d+)"
    r"|(?P<price2>\d*\.?\d+)\s*(?:premium|prem|contract|con)\b",
    re.IGNORECASE
)


def parse_owls_alert(content: str, embeds: Optional[List[Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
    """Parse Owls analyst embeds using explicit OPEN: vs CLOSE: title headers."""
    title = ""
    desc = ""
    author = ""

    if embeds:
        for emb in embeds:
            if isinstance(emb, dict):
                title = (emb.get("title") or "").upper().strip()
                desc = emb.get("description") or ""
                author = emb.get("author") or ""
                break

    text_to_parse = desc if desc else content
    combined_upper = (title + " " + text_to_parse).upper()

    # Check action type
    if "OPEN:" in title or "OPEN:" in combined_upper:
        action = "ENTRY"
    elif "CLOSE:" in title or "CLOSE:" in combined_upper or "STC" in combined_upper or "SOLD" in combined_upper:
        action = "EXIT" if "FULLY OUT" in combined_upper or "ALL OUT" in combined_upper or "SOLD ALL" in combined_upper else "TRIM"
    else:
        # Skip Update: or general chat commentary
        return None

    # Parse Option Alert
    m = OPTION_REGEX.search(text_to_parse)
    if m:
        ticker = m.group("ticker").upper()
        if ticker in TICKER_BLACKLIST:
            return None

        strike = float(m.group("strike"))
        opt_type = "call" if m.group("type").upper().startswith("C") else "put"
        exp = m.group("exp")

        # Price Extraction
        p_match = PRICE_REGEX.search(text_to_parse)
        if p_match:
            raw_p = p_match.group("price") or p_match.group("price2")
            try:
                price = float(raw_p) if raw_p else 1.0
            except Exception:
                price = 1.0
        else:
            price = 1.0

        # Qualitative Sizing Weight
        text_lower = text_to_parse.lower()
        weight = 1.0
        if any(w in text_lower for w in ["lotto", "sized for 0", "0 or hero", "small size"]):
            weight = 0.25
        elif any(w in text_lower for w in ["heavy", "full size", "high conviction"]):
            weight = 1.75

        return {
            "action": action,
            "ticker": ticker,
            "asset_type": "option",
            "direction": opt_type,
            "strike": strike,
            "expiration": exp,
            "price": price,
            "weight": weight,
            "author": author,
            "raw_text": text_to_parse
        }

    return None
