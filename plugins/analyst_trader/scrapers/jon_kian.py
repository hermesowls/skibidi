"""Jon & Kian Analyst Scraper.

Handles Jon & Kian format: BTO RARE 50C 11/20exp 2 premium, STC RARE 50C at 2.40,
OPEN/CLOSE/Update embed cards, sub-analyst distinction (Jon vs Kian), and trim vs close logic.
"""

import re
from typing import Any, Dict, List, Optional
from plugins.analyst_trader.scrapers.base import BaseAnalystScraper

TICKER_BLACKLIST = {
    "STC", "BTO", "STO", "BTC", "BUY", "SELL", "OPEN", "CLOSE", "UPDATE", "MESSAGE",
    "INFO", "BOT", "HERO", "LOTTO", "PM", "AM", "ABOVE", "INTO", "EXP", "TO", "A",
    "LLC", "INC", "THE", "AND", "FOR", "WITH", "THAT", "THIS", "SOME", "TODAY",
    "NOW", "NEW", "ATH", "HOD", "LOD", "FREE", "RUNNER", "RUNNERS", "OR", "AT",
    "SOLD", "CAN", "FULLY", "OUT", "TAKE", "JUST", "GOOD", "GET", "LOOK", "HAVE",
    "ANOTHER", "MORE", "LESS", "HALF", "PROFIT", "PROFITS", "FEW", "PAID", "OPEX",
    "CPI", "EARNINGS", "DISCORD", "OWLS", "ON", "IN", "BE", "UP", "IS", "IT", "IF",
    "MY", "SO", "BY", "NO", "OF", "DO", "GO", "HE", "WE", "US", "ME", "AS", "AN",
    "OK", "OH", "AH", "HA", "HERE", "GAINS", "OVER", "MOST", "REST", "FULL", "TAKING",
    "FUCK", "SAKE", "HUGE", "KIAN", "JON", "TRADES", "WILL", "WOULD", "COULD", "SHOULD",
    "DONT", "DOESNT", "DIDNT", "WAIT", "WAITING", "ALERT", "ALERTS", "BIT", "BUT",
    "YOU", "YOUR", "HIS", "HER", "THEIR", "THEM", "THEY", "WHAT", "WHEN", "WHERE",
    "WHY", "HOW", "LIKE", "EVEN", "WELL", "ALSO", "BACK", "GREAT", "NICE", "CHOP",
    "WORK", "WORKING", "SWING", "SWINGS", "CALL", "CALLS", "PUT", "PUTS", "EXPIRE",
    "EXPIRING", "PREM", "PREMIUM", "CONTRACT", "CONTRACTS", "NODE", "SUPPORT",
    "RESISTANCE", "DAILY", "WEEKLY", "MARKET", "DOWNSIDE", "UPSIDE", "RISK", "HEDGE",
    "INSURANCE", "CHANCE", "WORTHLESS", "FLOW", "ONLINE", "SELL"
}

TYPO_MAP = {
    "ATXI": "AXTI",
    "VBNTX": "BNTX",
    "DFXT": "DFXT",
}


def resolve_sub_analyst(message: Dict[str, Any], text_to_parse: str) -> str:
    """Determine whether message is from Jon or Kian."""
    embeds = message.get("embeds", [])
    author_id = str(message.get("author_id") or message.get("author", ""))

    if embeds:
        for emb in embeds:
            if isinstance(emb, dict):
                author_info = emb.get("author", {})
                author_name = author_info.get("name", "") if isinstance(author_info, dict) else str(author_info)
                if "Jon" in author_name or "RegardedTrader" in author_name:
                    return "Jon"
                if "Kian" in author_name or "KianTrades" in author_name:
                    return "Kian"

    if author_id == "523089010592055296":
        return "Jon"

    text_lower = text_to_parse.lower()
    if "kian" in text_lower:
        return "Kian"
    if "jon" in text_lower:
        return "Jon"

    return "Jon"


class JonKianScraper(BaseAnalystScraper):
    def __init__(self) -> None:
        super().__init__("Jon & Kian")

    def extract_candidates(self, message: Dict[str, Any], context_history: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        content = message.get("content", "") or ""
        embeds = message.get("embeds", []) or []

        title = ""
        desc = ""
        if embeds:
            for emb in embeds:
                if isinstance(emb, dict):
                    title = (emb.get("title") or "").strip()
                    desc = (emb.get("description") or "").strip()
                    break

        text_to_parse = desc if desc else content
        if not text_to_parse:
            return []

        sub_analyst = resolve_sub_analyst(message, title + " " + text_to_parse)
        title_upper = title.upper()
        text_upper = text_to_parse.upper()
        combined_upper = title_upper + " " + text_upper

        candidates = []

        # 1. ENTRY Parsing (OPEN: embed card or BTO text)
        if "OPEN:" in title_upper or "BTO" in text_upper or "BUY" in text_upper:
            m_bto = re.search(
                r"(?:BTO|BUY|OPEN:?\s*)?\s*\$?(?P<ticker>[A-Z]{1,5})\s+(?P<strike>\d+(?:\.\d+)?)\s*(?P<type>C|P|CALL|PUT)\s+(?:at\s+)?(?P<exp>\d{1,2}/\d{1,2}(?:/\d{2,4}|exp)?)\b\s*(?:(?:at|@|premium)\s*)?\$?(?P<price>\d+(?:\.\d+)?)?",
                text_to_parse,
                re.IGNORECASE
            )
            if m_bto:
                ticker = m_bto.group("ticker").upper()
                ticker = TYPO_MAP.get(ticker, ticker)
                if ticker not in TICKER_BLACKLIST:
                    try:
                        price = float(m_bto.group("price")) if m_bto.group("price") else 1.0
                    except Exception:
                        price = 1.0

                    exp_raw = (m_bto.group("exp") or "").lower().replace("exp", "").strip()
                    candidates.append({
                        "action": "ENTRY",
                        "ticker": ticker,
                        "asset_type": "option",
                        "direction": "call" if m_bto.group("type").upper().startswith("C") else "put",
                        "strike": float(m_bto.group("strike")),
                        "expiration": exp_raw,
                        "price": price,
                        "weight": 1.0,
                        "source_text": text_to_parse,
                        "analyst_name": sub_analyst
                    })
                    return candidates

        # 2. CLOSE / TRIM / UPDATE Card Parsing
        is_close_card = "CLOSE:" in title_upper
        is_update_card = "UPDATE:" in title_upper or "UPDATE" in title_upper
        is_close_text = any(w in text_upper for w in ["STC", "SOLD", "TRIM", "CLOSED", "FULLY OUT", "ALL OUT", "TAKE SOME", "TAKE PROFIT"])

        if is_close_card or is_update_card or is_close_text:
            # Extract percentage ROI if present
            pct_roi = None
            pct_match = re.search(r"(\d+(?:\.\d+)?)%", text_to_parse)
            if pct_match:
                try:
                    pct_roi = float(pct_match.group(1))
                except Exception:
                    pct_roi = None

            # Extract exit price if present
            exit_price = None
            p_match = re.search(r"(?:@|at|\$)\s*\$?(?P<price>\d+\.\d+)|(?P<price2>\d+\.\d+)\b", text_to_parse)
            if p_match:
                raw_p = p_match.group("price") or p_match.group("price2")
                try:
                    exit_price = float(raw_p) if raw_p else None
                except Exception:
                    exit_price = None

            # Action Determination: TRIM vs EXIT (Close)
            text_lower = text_to_parse.lower()
            has_trim_kw = any(k in text_lower for k in ["some", "more", "trim", "trimmed", "part", "half", "6/10", "1/2", "3/4", "take some"])
            has_exit_kw = any(k in text_lower for k in ["rest", "fully out", "all out", "sold all", "all closed"])

            if has_exit_kw:
                act = "EXIT"
            elif has_trim_kw or "some" in text_lower or "more" in text_lower:
                act = "TRIM"
            elif is_close_card and not has_trim_kw:
                act = "EXIT"
            else:
                act = "TRIM"

            # Determine trim ratio
            frac_match = re.search(r"(\d+)/(\d+)", text_lower)
            if frac_match:
                try:
                    n, d = float(frac_match.group(1)), float(frac_match.group(2))
                    trim_ratio = n / d if d > 0 and n <= d else 0.5
                except Exception:
                    trim_ratio = 0.5
            elif "runner" in text_lower:
                trim_ratio = 0.85
            elif act == "EXIT":
                trim_ratio = 1.0
            else:
                trim_ratio = 0.5

            # Tickers known in Jon & Kian portfolio
            known_tickers = ["AXTI", "HPE", "FRO", "SPY", "BNTX", "MRVL", "CAKE", "INTC", "RIOT", "MS", "RGTI", "RKLB", "FCX", "AAPL", "VIX", "CORZ", "VNET", "RARE", "IREN", "DFXT", "QURE"]
            found_tickers = []

            # First match any known active tickers present in text
            for kt in known_tickers:
                if re.search(r"\b" + kt + r"\b", text_upper):
                    if kt not in found_tickers:
                        found_tickers.append(kt)

            # Fallback to word extraction if no known ticker found
            if not found_tickers:
                words = [w.strip("!.,:()$@#").upper() for w in text_to_parse.split()]
                for w in words:
                    w_clean = TYPO_MAP.get(w, w)
                    if 2 <= len(w_clean) <= 5 and w_clean.isalpha() and w_clean not in TICKER_BLACKLIST:
                        if w_clean not in found_tickers:
                            found_tickers.append(w_clean)

            # Generate candidate for each found ticker
            for ticker in found_tickers:
                candidates.append({
                    "action": act,
                    "ticker": ticker,
                    "asset_type": "option",
                    "direction": "call",
                    "price": exit_price,
                    "pct_roi": pct_roi,
                    "trim_ratio": trim_ratio,
                    "weight": 1.0,
                    "source_text": text_to_parse,
                    "analyst_name": sub_analyst
                })

        return candidates


