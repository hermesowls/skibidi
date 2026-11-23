"""LLM Validation Agent for Analyst Trade Signals (AnalystSignalReviewer)."""

import json
import logging
import os
import urllib.request
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AnalystSignalReviewer:
    """Uses LLM structured output to validate, rectify, and verify analyst Discord signals."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    def review_signal(self, raw_content: str, embeds: Optional[list] = None, regex_parsed: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Validate and rectify a trade signal using LLM semantic reasoning."""
        if not self.api_key:
            # Fallback to regex output if API key is not provided
            return regex_parsed or {"is_trade_signal": False}

        prompt = f"""
System: You are an expert financial analyst trade alert reviewer. Analyze the following Discord message from a stock/options analyst and extract structured JSON trade intent.

Message Content: "{raw_content}"
Embed Data: {json.dumps(embeds) if embeds else "None"}
Regex Initial Estimate: {json.dumps(regex_parsed) if regex_parsed else "None"}

Rules:
1. Determine if this is a legitimate trade signal (is_trade_signal: true/false). Skip general chat, news, market commentary, or greetings.
2. Action MUST be one of: "ENTRY", "TRIM", "EXIT", or "COMMENTARY".
3. Extract exact ticker (e.g. "RARE", "FCX", "RKLB", "VNET", "RGTI").
4. Asset type: "option" or "equity". Direction: "call" or "put" or "long".
5. Strike price (float, e.g. 50.0). Expiration (MM/DD, convert typos like 09/21 to standard Friday 09/18).
6. Price: Extract DOLLAR premium (e.g., 2.00, 3.80, 0.95). If "12%" or "%" is written, it is ROI %, NOT dollar price!
7. Trim ratio: 0.15 for standard trim, 0.60 for 6/10, 0.85 for "free runner" / "leave runner".
8. Confidence score between 0.0 and 1.0.

Return JSON ONLY with keys:
is_trade_signal, action, ticker, asset_type, direction, strike, expiration, price, pct_roi, trim_ratio, confidence_score, reasoning
"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        body = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "response_format": {"type": "json_object"}
        }

        try:
            req = urllib.request.Request(f"{self.base_url}/chat/completions", data=json.dumps(body).encode(), headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                content = data["choices"][0]["message"]["content"]
                return json.loads(content)
        except Exception as e:
            logger.debug("LLM Signal Reviewer fallback due to API error: %s", e)
            return regex_parsed or {"is_trade_signal": False}
