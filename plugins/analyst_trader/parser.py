"""Signal Parser, Discord Backfill Engine, and Typo Rectification for Owls Analyst Alerts."""

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from plugins.analyst_trader.db import AnalystDatabase

logger = logging.getLogger(__name__)

# Ticker Blacklist
TICKER_BLACKLIST = {
    "STC", "BTO", "STO", "BTC", "BUY", "SELL", "OPEN", "CLOSE", "UPDATE", "MESSAGE",
    "INFO", "BOT", "HERO", "LOTTO", "PM", "AM", "ABOVE", "INTO", "EXP", "TO", "A",
    "LLC", "INC", "THE", "AND", "FOR", "WITH", "THAT", "THIS", "SOME", "TODAY",
    "NOW", "NEW", "ATH", "HOD", "LOD", "FREE", "RUNNER", "RUNNERS", "OR", "AT",
    "SOLD", "CAN", "FULLY", "OUT", "TAKE", "JUST", "GOOD", "GET", "LOOK", "HAVE",
    "ANOTHER", "MORE", "LESS", "HALF", "PROFIT", "PROFITS", "SOME", "FEW", "PAID",
    "TRIM", "TRIMMED", "SL", "TP", "TP1", "TP2", "TP3", "STOP", "STOPPED", "SCALED", "SCALE"
}

OPTION_REGEX = re.compile(
    r"(?P<ticker>[A-Z]{1,5})\s+"
    r"(?P<strike>\$?\d+(?:\.\d+)?)\s*"
    r"(?P<type>C|P|CALL|PUT)\b"
    r"(?:\s*(?:exp(?:iring)?\s*)?(?P<exp>\d{1,2}/\d{1,2}(?:/\d{2,4})?))?",
    re.IGNORECASE
)

# Price Extractor (ignoring numbers followed by %)
PRICE_REGEX = re.compile(
    r"(?:@|at|price|premium|exp\s+at|\$)\s*\$?(?P<price>\d*\.?\d+)"
    r"|(?P<price2>\d*\.?\d+)\s*(?:premium|prem|contract|con)\b",
    re.IGNORECASE
)


def resolve_expiration_typo(exp_str: Optional[str]) -> Optional[str]:
    """Auto-rectify non-standard date typos (e.g. 09/21 typo -> 09/18 standard Friday)."""
    if not exp_str:
        return None
    try:
        parts = [p.strip() for p in exp_str.split("/") if p.strip()]
        if len(parts) >= 2:
            m = int(parts[0])
            d = int(parts[1])
            y = int(parts[2]) % 100 if len(parts) >= 3 else 26

            if m == 9 and d == 21:
                return "09/18"
            return f"{m:02d}/{d:02d}"
    except Exception:
        pass
    return exp_str


def extract_trim_ratio(text: str) -> float:
    """Extract qualitative or explicit trim ratio from message text (percentages, fractions, keywords)."""
    combined = text.lower()

    # Check for explicit percentage (e.g. 50%, 75%, 30%, 100%)
    pct_match = re.search(r"(\d+(?:\.\d+)?)%\s*(?:trimmed|trim|sold|out|off|closed)?", combined)
    if pct_match:
        try:
            val = float(pct_match.group(1))
            if 0 < val <= 100:
                return val / 100.0
        except Exception:
            pass

    # Check for explicit fraction (e.g. 6/10 = 0.60, 1/2 = 0.50, 3/4 = 0.75)
    frac_match = re.search(r"(\d+)/(\d+)", combined)
    if frac_match:
        try:
            n = float(frac_match.group(1))
            d = float(frac_match.group(2))
            if d > 0 and n <= d:
                return n / d
        except Exception:
            pass

    # Qualitative keyword checks
    if any(k in combined for k in ["fully out", "all out", "sold all", "closed rest", "out rest", "100%", "closed"]):
        return 1.0
    if any(k in combined for k in ["runner", "runners", "leave runner", "free runner", "leaving runner"]):
        return 0.85
    if any(k in combined for k in ["half", "1/2", "50%"]):
        return 0.50
    if any(k in combined for k in ["most", "75%", "3/4"]):
        return 0.75
    if any(k in combined for k in ["third", "1/3"]):
        return 0.33
    if any(k in combined for k in ["quarter", "1/4", "25%"]):
        return 0.25

    # Standard default trim ratio (50% trim of open tranche if unspecified)
    return 0.50


class TradeSignalParser:
    """Parses Owls analyst embeds and text alerts with percentage ROI and typo handling."""

    @staticmethod
    def parse_eva(text: str, title: str, author: str) -> Optional[Dict[str, Any]]:
        """Parse Eva's embed format: BTO QQQ 08/21/2026 750C @ 0.54 or CLOSE/TRIM updates."""
        if not text:
            return None
        combined = (title + " " + text).upper()
        if "OPEN" in title or "BTO" in text.upper():
            m = re.search(
                r"(?:BTO|BUY)\s+(?P<ticker>[A-Z]{1,5})\s+(?P<exp>\d{1,2}/\d{1,2}(?:/\d{2,4})?)\s+(?P<strike>\d+(?:\.\d+)?)(?P<type>C|P|CALL|PUT)\s*(?:@|at|\$)?\s*(?P<price>\d+(?:\.\d+)?)",
                text,
                re.IGNORECASE
            )
            if m:
                ticker = m.group("ticker").upper()
                if ticker in TICKER_BLACKLIST:
                    return None
                try:
                    price = float(m.group("price"))
                except Exception:
                    price = 1.0
                return {
                    "action": "ENTRY",
                    "ticker": ticker,
                    "asset_type": "option",
                    "direction": "call" if m.group("type").upper().startswith("C") else "put",
                    "strike": float(m.group("strike")),
                    "expiration": resolve_expiration_typo(m.group("exp")),
                    "price": price,
                    "weight": 1.0,
                    "author": author or "Eva",
                    "raw_text": text
                }
        elif "CLOSE" in title or "TRIM" in title or "STC" in combined:
            m = re.search(
                r"(?:STC|CLOSE|TRIM|SOLD)\s+(?P<ticker>[A-Z]{1,5})\s*(?:(?P<strike>\d+(?:\.\d+)?)(?P<type>C|P|CALL|PUT)?)?\s*(?:@|at|\$)?\s*(?P<price>\d+(?:\.\d+)?)",
                text,
                re.IGNORECASE
            )
            if m:
                ticker = m.group("ticker").upper()
                if ticker not in TICKER_BLACKLIST:
                    act = "EXIT" if any(k in combined for k in ["FULLY OUT", "ALL OUT", "CLOSE", "CLOSED"]) else "TRIM"
                    try:
                        price = float(m.group("price")) if m.group("price") else None
                    except Exception:
                        price = None
                    return {
                        "action": act,
                        "ticker": ticker,
                        "asset_type": "option",
                        "direction": "call" if m.group("type") and m.group("type").upper().startswith("C") else "call",
                        "strike": float(m.group("strike")) if m.group("strike") else None,
                        "expiration": None,
                        "price": price,
                        "trim_ratio": extract_trim_ratio(text),
                        "weight": 1.0,
                        "author": author or "Eva",
                        "raw_text": text
                    }
        return None

    @staticmethod
    def parse_ab(text: str, author: str) -> Optional[Dict[str, Any]]:
        """Parse AB's format: $BIDU 9/18 130c 3.15 or $CVNA 8/21 70c 100% - closed"""
        if not text:
            return None
        # Check closed / trimmed list entries first
        m_c = re.search(
            r"\$?(?P<ticker>[A-Z]{1,5})\s+(?P<exp>\d{1,2}/\d{1,2})?\s*(?P<strike>\d+(?:\.\d+)?)(?P<type>c|p|call|put)?\s+(?P<roi>\d+)%\s*-\s*(?P<action>closed|trimmed)",
            text,
            re.IGNORECASE
        )
        if m_c:
            act = "EXIT" if m_c.group("action").lower() == "closed" else "TRIM"
            try:
                roi = float(m_c.group("roi"))
            except Exception:
                roi = 0.0
            return {
                "action": act,
                "ticker": m_c.group("ticker").upper(),
                "asset_type": "option",
                "direction": "call" if (m_c.group("type") or "c").lower().startswith("c") else "put",
                "strike": float(m_c.group("strike")) if m_c.group("strike") else None,
                "expiration": resolve_expiration_typo(m_c.group("exp")) if m_c.group("exp") else None,
                "price": None,
                "pct_roi": roi,
                "trim_ratio": 1.0 if act == "EXIT" else extract_trim_ratio(text),
                "weight": 1.0,
                "author": author or "AB",
                "raw_text": text
            }

        # Check entry plays
        m_e = re.search(
            r"\$?(?P<ticker>[A-Z]{1,5})\s+(?P<exp>\d{1,2}/\d{1,2})\s+(?P<strike>\d+(?:\.\d+)?)(?P<type>c|p|call|put)\s+(?P<price>\d+(?:\.\d+)?)",
            text,
            re.IGNORECASE
        )
        if m_e:
            ticker = m_e.group("ticker").upper()
            if ticker in TICKER_BLACKLIST:
                return None
            try:
                price = float(m_e.group("price"))
            except Exception:
                price = 1.0
            return {
                "action": "ENTRY",
                "ticker": ticker,
                "asset_type": "option",
                "direction": "call" if m_e.group("type").lower().startswith("c") else "put",
                "strike": float(m_e.group("strike")),
                "expiration": resolve_expiration_typo(m_e.group("exp")),
                "price": price,
                "weight": 1.0,
                "author": author or "AB",
                "raw_text": text
            }
        return None

    @staticmethod
    def parse_muggzone(text: str, author: str) -> Optional[Dict[str, Any]]:
        """Parse Muggzone's TP updates: CMG Calls up 24%, Second TP Hit on NVDA puts"""
        if not text:
            return None
        m = re.search(
            r"(?P<ticker>[A-Z]{1,5})\s+(?P<type>calls|puts)?\s*(?:up|down)?\s*(?P<roi>\d+)%",
            text,
            re.IGNORECASE
        )
        if m:
            ticker = m.group("ticker").upper()
            if ticker in TICKER_BLACKLIST:
                return None
            try:
                roi = float(m.group("roi"))
            except Exception:
                roi = 0.0
            act = "EXIT" if "fully out" in text.lower() or "closed" in text.lower() else "TRIM"
            return {
                "action": act,
                "ticker": ticker,
                "asset_type": "option",
                "direction": "call" if (m.group("type") or "calls").lower().startswith("call") else "put",
                "strike": None,
                "expiration": None,
                "price": None,
                "pct_roi": roi,
                "trim_ratio": extract_trim_ratio(text),
                "weight": 1.0,
                "author": author or "Muggzone Options",
                "raw_text": text
            }
        return None

    @classmethod
    def parse_message(cls, content: str, embeds: Optional[List[Dict[str, Any]]] = None, analyst_name: str = "") -> Optional[Dict[str, Any]]:
        """Parse raw content and embeds using modular analyst parsers."""
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

        # 0. Try Jon & Kian dedicated scraper
        if any(k in analyst_name.lower() for k in ["jon", "kian", "cactusjack"]):
            from plugins.analyst_trader.scrapers.jon_kian import JonKianScraper
            jk_scraper = JonKianScraper()
            msg_obj = {"content": content, "embeds": embeds, "author": author, "title": title, "description": desc}
            candidates = jk_scraper.extract_candidates(msg_obj)
            if candidates:
                cand = candidates[0]
                sub_a = cand.get("analyst_name", "Jon")
                return {
                    "action": cand["action"],
                    "ticker": cand["ticker"],
                    "asset_type": cand.get("asset_type", "option"),
                    "direction": cand.get("direction", "call"),
                    "strike": cand.get("strike"),
                    "expiration": cand.get("expiration"),
                    "price": cand.get("price"),
                    "pct_roi": cand.get("pct_roi"),
                    "trim_ratio": cand.get("trim_ratio", extract_trim_ratio(text_to_parse)),
                    "weight": 1.0,
                    "author": sub_a,
                    "sub_analyst": sub_a,
                    "raw_text": text_to_parse
                }

        # 1. Try Eva parser for embeds
        if "eva" in analyst_name.lower() or "open" in title.lower() or "bto" in text_to_parse.lower():
            eva_res = cls.parse_eva(text_to_parse, title, author)
            if eva_res:
                return eva_res

        # 2. Try AB parser for lists and alerts
        if "ab" in analyst_name.lower() or "$" in text_to_parse:
            ab_res = cls.parse_ab(text_to_parse, author)
            if ab_res:
                return ab_res

        # 3. Try Muggzone TP parser
        if "muggzone" in analyst_name.lower() or "tp" in text_to_parse.lower() or "%" in text_to_parse:
            mugg_res = cls.parse_muggzone(text_to_parse, author)
            if mugg_res:
                return mugg_res

        # 4. Fallback Generic Parser
        combined_upper = (title + " " + text_to_parse).upper()

        pct_roi = None
        pct_match = re.search(r"(\d+(?:\.\d+)?)%", text_to_parse)
        if pct_match:
            try:
                pct_roi = float(pct_match.group(1))
            except Exception:
                pct_roi = None

        text_for_price = re.sub(r"\b\d+(?:\.\d+)?%\s*", "", text_to_parse)

        if "OPEN:" in title or "OPEN:" in combined_upper or "BTO" in combined_upper or "BUY" in combined_upper:
            action = "ENTRY"
        elif "CLOSE:" in title or "CLOSE:" in combined_upper or "STC" in combined_upper or "SOLD" in combined_upper or "TRIM" in combined_upper or "TAKING PROFITS" in combined_upper or "OUT" in combined_upper or "SL HIT" in combined_upper or "STOP" in combined_upper:
            action = "EXIT" if any(k in combined_upper for k in ["FULLY OUT", "ALL OUT", "SOLD ALL", "CLOSED", "CLOSED REST", "OUT REST", "STOPPED OUT", "SL HIT", "FULLY CLOSED"]) else "TRIM"
        else:
            return None

        m = OPTION_REGEX.search(text_to_parse)
        if m and action == "ENTRY":
            ticker = m.group("ticker").upper()
            if ticker in TICKER_BLACKLIST:
                return None

            strike = float(m.group("strike").replace("$", ""))
            opt_type = "call" if m.group("type").upper().startswith("C") else "put"
            raw_exp = m.group("exp")
            exp = resolve_expiration_typo(raw_exp)

            text_for_price = text_to_parse.replace(m.group(0), "")
            p_match = PRICE_REGEX.search(text_for_price)
            if p_match:
                raw_p = p_match.group("price") or p_match.group("price2")
                try:
                    price = float(raw_p) if raw_p else 1.0
                except Exception:
                    price = 1.0
            else:
                price = 1.0

            return {
                "action": action,
                "ticker": ticker,
                "asset_type": "option",
                "direction": opt_type,
                "strike": strike,
                "expiration": exp,
                "price": price,
                "weight": 1.0,
                "author": author,
                "raw_text": text_to_parse
            }

        if action in ("TRIM", "EXIT"):
            words = text_to_parse.split()
            found_ticker = None
            for w in words:
                w_clean = w.strip("!.,:()$").upper()
                if 2 <= len(w_clean) <= 5 and w_clean.isalpha() and w_clean not in TICKER_BLACKLIST:
                    found_ticker = w_clean
                    break

            if found_ticker:
                p_match = PRICE_REGEX.search(text_for_price)
                if p_match:
                    raw_p = p_match.group("price") or p_match.group("price2")
                    try:
                        price = float(raw_p) if raw_p else None
                    except Exception:
                        price = None
                else:
                    price = None

                trim_ratio = extract_trim_ratio(text_to_parse)

                return {
                    "action": action,
                    "ticker": found_ticker,
                    "asset_type": "option",
                    "direction": "call",
                    "strike": None,
                    "expiration": None,
                    "price": price,
                    "pct_roi": pct_roi,
                    "trim_ratio": trim_ratio,
                    "weight": 1.0,
                    "author": author,
                    "raw_text": text_to_parse
                }

        return None


class DiscordBackfillEngine:
    """Fetches full Discord channel message history and processes alerts into SQLite."""

    def __init__(self, db: Optional[AnalystDatabase] = None) -> None:
        self.db = db or AnalystDatabase()
        self.parser = TradeSignalParser()

    def process_raw_alert(self, message_id: str, channel_id: str, channel_name: str,
                          analyst_name: str, author_id: str, content: str,
                          embeds: Optional[List[Dict[str, Any]]] = None,
                          timestamp: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Store raw message and process trade signal into database."""
        inserted = self.db.save_raw_message(
            message_id=message_id,
            channel_id=channel_id,
            channel_name=channel_name,
            analyst_name=analyst_name,
            author_id=author_id,
            content=content,
            embeds=embeds,
            timestamp=timestamp
        )

        # Skip position creation for aggregator channels (e.g. all-alerts) to avoid repeat positions
        if "all-alerts" in channel_name.lower() or "all alerts" in analyst_name.lower() or "all-alerts" in analyst_name.lower():
            self.db.mark_message_processed(message_id)
            return None

        signal = self.parser.parse_message(content, embeds, analyst_name=analyst_name)
        if not signal:
            self.db.mark_message_processed(message_id)
            return None

        effective_analyst = signal.get("sub_analyst") or signal.get("author") or analyst_name
        if "cactusjack" in effective_analyst.lower() or "cactusjackgaming212" in effective_analyst.lower():
            effective_analyst = "Kian"
        if effective_analyst not in ("Jon", "Kian") and ("jon" in analyst_name.lower() or "kian" in analyst_name.lower()):
            effective_analyst = "Jon"

        ticker = signal["ticker"]
        action = signal["action"]
        price = signal.get("price")
        pct_roi = signal.get("pct_roi")
        trim_ratio = signal.get("trim_ratio", 0.5)

        if action == "ENTRY":
            pos_id = f"pos_{effective_analyst}_{ticker}_{message_id[:8]}"
            pos = self.db.create_position(
                position_id=pos_id,
                analyst_name=effective_analyst,
                channel_id=channel_id,
                ticker=ticker,
                asset_type=signal["asset_type"],
                direction=signal["direction"],
                contracts_or_shares=1.0,  # Always start at 1.0 (100% position size)
                entry_price=price or 1.0,
                strike=signal.get("strike"),
                expiration=signal.get("expiration"),
                entry_time=timestamp,
                entry_message_id=message_id,
                notes=signal["raw_text"][:200]
            )
            self.db.log_trade_event(pos_id, effective_analyst, message_id, "ENTRY", ticker, price or 1.0, signal, timestamp)
            self.db.mark_message_processed(message_id)
            return pos

        elif action in ("TRIM", "EXIT"):
            existing = self.db.find_open_position(effective_analyst, ticker, signal.get("strike"), signal.get("expiration"))
            if not existing and effective_analyst in ("Jon", "Kian"):
                existing = self.db.find_open_position("Jon & Kian", ticker, signal.get("strike"), signal.get("expiration"))
            if not existing and effective_analyst in ("Jon", "Kian"):
                other = "Kian" if effective_analyst == "Jon" else "Jon"
                existing = self.db.find_open_position(other, ticker, signal.get("strike"), signal.get("expiration"))

            if existing:
                pos_id = existing["position_id"]
                entry_p = float(existing["entry_price"]) if existing.get("entry_price") else 1.0

                # Exit price & ROI calculation
                if price is not None:
                    exit_price = price
                elif pct_roi is not None:
                    exit_price = round(entry_p * (1.0 + pct_roi / 100.0), 2)
                else:
                    exit_price = float(existing.get("current_price") or entry_p)

                # Maintain max exit price / max ROI across progressive trims
                current_exit_p = float(existing.get("exit_price") or 0.0)
                if current_exit_p > exit_price:
                    exit_price = current_exit_p

                new_status = "CLOSED" if action == "EXIT" or trim_ratio >= 0.85 else "TRIMMED"

                updated_pos = self.db.update_position_trim_or_close(
                    position_id=pos_id,
                    exit_price=exit_price,
                    status=new_status,
                    trim_ratio=trim_ratio,
                    exit_message_id=message_id,
                    exit_time=timestamp
                )
                self.db.log_trade_event(pos_id, effective_analyst, message_id, action, ticker, exit_price, signal, timestamp)
                self.db.mark_message_processed(message_id)
                return updated_pos

        self.db.mark_message_processed(message_id)
        return None

