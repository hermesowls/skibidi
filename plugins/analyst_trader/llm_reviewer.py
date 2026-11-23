"""Hybrid LLM Reviewer Agent for Discord Trade Signals.

Reviews candidate trade alerts extracted by per-analyst scrapers alongside conversation context threads
using structured LLM JSON prompting (Codex / GPT-5.5 / OpenAI fallback).
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
import requests  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

REVIEWER_SYSTEM_PROMPT = """You are a Senior Quantitative Trading Analyst & Verification System for OWLS Capital.
Your job is to review raw Discord messages and analyst conversation threads, and verify whether a valid trade signal occurred.

CRITICAL OWLS TRADING NOTATION RULES:
1. "$X/con" or "$X/contract" or "X/con" (e.g. "$45/con", "$100/con", "45/con"):
   When an analyst posts a trim alert mentioning "$X/con" or "X/con", it represents a PROFIT GAIN of +$X per option contract (+$X/100 premium per share).
   You MUST calculate exit_price = entry_price + (X / 100.0).
   Example: If entry_price is 6.91 and text says "can trim some SPY puts for $45/con", exit_price is 6.91 + 0.45 = 7.36.
   If text says "$100/con", exit_price is 6.91 + 1.00 = 7.91.
2. Verify if this is a genuine trade alert (BTO, STC, Trim, Take Profit, Scale, Close, or Stop Out). Ignore general commentary, market opinions, macro chatter, or unrelated conversation.
3. Assign a confidence_score between 0.00 and 1.00 (e.g. 0.95 for clear BTO/STC/Trim alerts, 0.40 for ambiguous chatter).
4. Return ONLY valid JSON matching this exact schema:

{
  "valid_signal": true,
  "confidence_score": 0.95,
  "action": "TRIM",
  "ticker": "QQQ",
  "asset_type": "option",
  "direction": "call",
  "strike": 750.0,
  "expiration": "2026-08-21",
  "entry_price": 0.54,
  "exit_price": 0.95,
  "pct_roi": 75.9,
  "trim_ratio": 0.5,
  "reasoning": "Explicit Trim/Take Profit alert taking 50% profits at 0.95 (+75.9%)."
}
"""


class LLMTradeReviewer:
    """Hybrid LLM Trade Reviewer Agent powered by active Hermes Agent configuration."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, base_url: Optional[str] = None) -> None:
        cfg = {}
        try:
            from hermes_cli.config import load_config
            cfg = load_config()
        except Exception:
            pass

        raw_model = model or cfg.get("model") or os.getenv("HERMES_MODEL") or "openai/gpt-4o-mini"
        if isinstance(raw_model, dict):
            raw_model = raw_model.get("name") or "openai/gpt-4o-mini"
        self.model = str(raw_model)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("CODEX_API_KEY") or cfg.get("api_key", "")
        
        if not self.api_key:
            try:
                from agent.credential_pool import load_pool
                for p_id in ("openai-codex", "openrouter", "openai", "nous"):
                    pool = load_pool(p_id)
                    if pool and pool.has_credentials():
                        entry = pool.peek()
                        if entry:
                            tok = getattr(entry, "access_token", "") or getattr(entry, "runtime_api_key", "")
                            if tok and len(str(tok).strip()) > 4:
                                self.api_key = str(tok).strip()
                                break
            except Exception:
                pass

        raw_base = base_url or cfg.get("base_url") or os.getenv("OPENAI_BASE_URL")
        if not raw_base:
            provider = (cfg.get("provider") or "").lower()
            if provider == "openrouter" or "openrouter" in self.model.lower():
                raw_base = "https://openrouter.ai/api/v1"
            else:
                raw_base = "https://api.openai.com/v1"
        self.base_url = raw_base.rstrip("/")

    def review_candidate(
        self,
        candidate: Dict[str, Any],
        context_messages: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Review candidate signal using LLM JSON verification with rule-based fallback."""
        source_text = candidate.get("source_text", "")
        analyst_name = candidate.get("analyst_name", "Analyst")

        # Rule-based fast score pre-check: high quality regex matches get auto-scored high confidence
        if candidate.get("ticker") and candidate.get("action") and candidate.get("strike"):
            fallback_score = 0.92
        elif candidate.get("ticker") and candidate.get("action"):
            fallback_score = 0.85
        else:
            fallback_score = 0.50

        # Attempt LLM Verification Call if API Key / Endpoint is available
        if self.api_key:
            try:
                context_str = ""
                if context_messages:
                    ctx_lines = [f"[{m.get('timestamp')}] {m.get('author', 'User')}: {m.get('content', '')}" for m in context_messages[-5:]]
                    context_str = "\n".join(ctx_lines)

                prompt = f"""Analyst: {analyst_name}
Candidate Signal: {json.dumps(candidate)}
Recent Conversation Context:
{context_str}

Evaluate and return JSON verification:"""

                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": REVIEWER_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1
                }
                endpoint = f"{self.base_url}/chat/completions"
                resp = requests.post(endpoint, headers=headers, json=payload, timeout=5)
                if resp.status_code == 200:
                    res_json = resp.json()
                    content_out = res_json["choices"][0]["message"]["content"]

                    # Extract JSON object from output
                    json_match = re.search(r"\{.*\}", content_out, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group(0))
                        return {
                            **candidate,
                            "valid_signal": parsed.get("valid_signal", True),
                            "confidence_score": float(parsed.get("confidence_score", fallback_score)),
                            "reasoning": parsed.get("reasoning", "Verified by LLM Reviewer Agent"),
                            "verification_status": "VERIFIED" if float(parsed.get("confidence_score", 0)) >= 0.80 else "NEEDS_REVIEW"
                        }
            except Exception as e:
                logger.debug("LLM API review fallback (%s); using rule-based scoring.", e)

        # Fallback response
        return {
            **candidate,
            "valid_signal": True if fallback_score >= 0.80 else False,
            "confidence_score": fallback_score,
            "reasoning": "Rule-based structural validation (high confidence format)",
            "verification_status": "VERIFIED" if fallback_score >= 0.80 else "NEEDS_REVIEW"
        }

    def audit_raw_message_against_tracker(
        self,
        raw_msg: Dict[str, Any],
        tracked_positions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Audit a single raw Discord analyst message against recorded database positions."""
        from plugins.analyst_trader.parser import extract_trim_ratio, TICKER_BLACKLIST

        msg_id = str(raw_msg.get("message_id") or raw_msg.get("id") or "")
        analyst_name = raw_msg.get("analyst_name", "Jon & Kian")
        content = raw_msg.get("content", "") or ""
        embeds = raw_msg.get("embeds_json") or raw_msg.get("embeds", [])
        if isinstance(embeds, str):
            try:
                embeds = json.loads(embeds)
            except Exception:
                embeds = []

        title = ""
        desc = ""
        if embeds:
            for emb in embeds:
                if isinstance(emb, dict):
                    title = (emb.get("title") or "").strip()
                    desc = (emb.get("description") or "").strip()
                    break

        combined_text = (title + " " + desc + " " + content).strip()
        combined_upper = combined_text.upper()

        # Check if text contains trade keywords
        trade_kw = any(w in combined_upper for w in ["BTO", "STC", "BUY", "SELL", "OPEN:", "CLOSE:", "UPDATE:", "TRIM", "TRIMMED", "CLOSED", "FULLY OUT", "ALL OUT", "RUNNER", "TAKING PROFITS", "SL HIT", "STOPPED OUT"])
        if not trade_kw:
            return {
                "message_id": msg_id,
                "analyst_name": analyst_name,
                "discrepancy_type": "MATCHED_ACCURATE",
                "confidence_score": 0.99,
                "reasoning": "Non-trade message (commentary/chat). No trade alert.",
                "original_data": None,
                "corrected_data": None
            }

        # Dynamic Ticker Search: search for tracked position tickers or uppercase candidate ticker
        found_ticker = None
        for p in tracked_positions:
            p_tk = p.get("ticker", "")
            if p_tk and re.search(r"\b" + p_tk + r"\b", combined_upper):
                found_ticker = p_tk
                break

        if not found_ticker:
            words = combined_upper.split()
            for w in words:
                w_clean = w.strip("!.,:()$").upper()
                if 2 <= len(w_clean) <= 5 and w_clean.isalpha() and w_clean not in TICKER_BLACKLIST:
                    found_ticker = w_clean
                    break

        # Find existing position in DB
        matching_pos = None
        if found_ticker:
            for p in tracked_positions:
                if p.get("ticker") == found_ticker and p.get("status") in ("OPEN", "TRIMMED"):
                    matching_pos = p
                    break

        # Determine LLM/Rule semantic action
        has_exit_kw = any(k in combined_text.lower() for k in ["rest", "fully out", "all out", "sold all", "closed", "stopped out", "sl hit", "100%"])
        has_trim_kw = any(k in combined_text.lower() for k in ["some", "more", "trim", "trimmed", "part", "half", "6/10", "take some", "taking profits", "tp", "scaled", "runner"])
        is_open = "OPEN:" in combined_upper or "BTO" in combined_upper or "BUY" in combined_upper

        if is_open:
            intended_action = "ENTRY"
        elif has_exit_kw:
            intended_action = "EXIT"
        elif has_trim_kw:
            intended_action = "TRIM"
        elif "CLOSE:" in combined_upper or "STC" in combined_upper:
            intended_action = "EXIT" if any(k in combined_text.lower() for k in ["fully", "all", "out", "rest"]) else "TRIM"
        else:
            intended_action = "TRIM"

        # Price & ROI extraction
        text_for_price = re.sub(r"\b\d+(?:\.\d+)?%\s*", "", combined_text)
        p_match = re.search(r"(?:@|at|\$)\s*\$?(?P<price>\d+\.\d+)|(?P<price2>\d+\.\d+)\b", text_for_price)
        exit_p = None
        if p_match:
            raw_p = p_match.group("price") or p_match.group("price2")
            try:
                exit_p = float(raw_p) if raw_p else None
            except Exception:
                exit_p = None

        trim_ratio = extract_trim_ratio(combined_text)

        # Compare against matched position
        if not matching_pos and found_ticker and intended_action == "ENTRY":
            return {
                "message_id": msg_id,
                "analyst_name": analyst_name,
                "ticker": found_ticker,
                "discrepancy_type": "MISSED_SIGNAL",
                "confidence_score": 0.92,
                "reasoning": f"Analyst posted ENTRY alert for {found_ticker} that was missed by tracker.",
                "original_data": None,
                "corrected_data": {
                    "action": "ENTRY",
                    "ticker": found_ticker,
                    "price": exit_p or 1.0,
                    "asset_type": "option",
                    "direction": "call"
                }
            }

        if matching_pos:
            current_status = matching_pos.get("status")
            if intended_action == "EXIT" and current_status in ("OPEN", "TRIMMED"):
                return {
                    "message_id": msg_id,
                    "analyst_name": analyst_name,
                    "ticker": found_ticker,
                    "discrepancy_type": "ACTION_MISMATCH",
                    "confidence_score": 0.92,
                    "reasoning": f"Analyst announced full exit on {found_ticker}, but position was marked {current_status}.",
                    "original_data": matching_pos,
                    "corrected_data": {
                        "action": "EXIT",
                        "ticker": found_ticker,
                        "price": exit_p or matching_pos.get("exit_price") or matching_pos.get("entry_price"),
                        "status": "CLOSED",
                        "trim_ratio": 1.0
                    }
                }

            if intended_action == "TRIM" and current_status == "OPEN":
                return {
                    "message_id": msg_id,
                    "analyst_name": analyst_name,
                    "ticker": found_ticker,
                    "discrepancy_type": "ACTION_MISMATCH",
                    "confidence_score": 0.90,
                    "reasoning": f"Analyst announced trim on {found_ticker}, updating position to TRIMMED.",
                    "original_data": matching_pos,
                    "corrected_data": {
                        "action": "TRIM",
                        "ticker": found_ticker,
                        "price": exit_p or matching_pos.get("entry_price"),
                        "status": "TRIMMED",
                        "trim_ratio": trim_ratio
                    }
                }

        return {
            "message_id": msg_id,
            "analyst_name": analyst_name,
            "ticker": found_ticker,
            "discrepancy_type": "MATCHED_ACCURATE",
            "confidence_score": 0.95,
            "reasoning": "Parsed event accurately reflects analyst alert.",
            "original_data": matching_pos,
            "corrected_data": None
        }

    def audit_channel_batch(
        self,
        analyst_name: str,
        db: Any,
        limit: int = 50,
        auto_reconcile: bool = True
    ) -> Dict[str, Any]:
        """Audit a batch of raw channel messages against analyst_trading.db positions."""
        conn = db._get_connection()
        cur = conn.execute("SELECT * FROM raw_messages WHERE analyst_name = ? ORDER BY created_at DESC LIMIT ?", (analyst_name, limit))
        raw_msgs = [dict(r) for r in cur.fetchall()]

        tracked_positions = db.list_positions(analyst_name=analyst_name)

        audits_processed = []
        reconciliations_executed = []

        for raw_msg in raw_msgs:
            audit_res = self.audit_raw_message_against_tracker(raw_msg, tracked_positions)
            msg_id = str(raw_msg.get("message_id"))
            audit_id = f"aud_{msg_id}"

            # Save audit record in SQLite DB
            audit_record = db.save_reviewer_audit(
                audit_id=audit_id,
                message_id=msg_id,
                analyst_name=analyst_name,
                ticker=audit_res.get("ticker"),
                discrepancy_type=audit_res.get("discrepancy_type", "MATCHED_ACCURATE"),
                original_data=audit_res.get("original_data"),
                corrected_data=audit_res.get("corrected_data"),
                confidence_score=audit_res.get("confidence_score", 0.90),
                reasoning=audit_res.get("reasoning", ""),
                status="NEEDS_REVIEW" if audit_res.get("discrepancy_type") != "MATCHED_ACCURATE" else "VERIFIED"
            )
            audits_processed.append(audit_record)

            # Auto-reconcile high confidence discrepancies
            if auto_reconcile and audit_res.get("discrepancy_type") != "MATCHED_ACCURATE" and audit_res.get("confidence_score", 0) >= 0.85:
                rec_res = db.reconcile_position_from_audit(audit_id)
                reconciliations_executed.append(rec_res)

        return {
            "analyst_name": analyst_name,
            "total_audited": len(raw_msgs),
            "discrepancies_found": len([a for a in audits_processed if a.get("discrepancy_type") != "MATCHED_ACCURATE"]),
            "reconciliations_executed": len(reconciliations_executed),
            "audits": audits_processed,
            "reconciliations": reconciliations_executed
        }

