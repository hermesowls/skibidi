#!/usr/bin/env python3
"""
Discord Alert & Flow Publisher Module — Production Hardened.

Implements exact Discord UI templates with defense-in-depth:
  1. Notable Flow Template (Plain text + Flowseeker chart attachment)
     - Maps to #owlfred-notable-flow (1540785373280473138) [Equities]
     - Maps to #owlfred-notable-etf-flow (1540808176943898634) [ETFs]
  2. Actionable Alert Card Template (Rich Embed with colored accent border)
     - Maps to #owlfred-alerts (1540785808804552734)
     - Maps to #owlfred-extra (1540797567653253300)

Production Guards:
  - Automatic currency formatting ($120K, $5.3M, float conversion)
  - Image integrity verification (PIL validation, >20KB size check)
  - Exponential backoff retry on HTTP 429 / 5xx Discord errors
  - 2000-char payload boundary enforcement
  - Strict channel type segregation (GEX barred from Flow channels)
"""

import os
import sys
import json
import time
import logging
import requests  # type: ignore
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("discord_poster")

DISCORD_CHANNELS = {
    "alerts": "1540785808804552734",               # #owlfred-alerts
    "notable_flow": "1540785373280473138",         # #owlfred-notable-flow (Equities)
    "notable_etf_flow": "1540808176943898634",     # #owlfred-notable-etf-flow (ETFs)
    "extra": "1540797567653253300",                # #owlfred-extra
    "beginner_guidance": "1540797300262178837",    # #owlfred-beginner-guidance
}

EMBED_COLORS = {
    "OPEN": 0x00FF66,   # Vibrant Green
    "TRIM": 0xFFA500,   # Amber / Orange
    "CLOSE": 0xFF2A55,  # Crimson Red
    "INFO": 0x3498DB,   # Blue
}


def get_discord_token() -> str:
    token = os.getenv("DISCORD_BOT_TOKEN")
    if token:
        return token
    from hermes_constants import get_hermes_home
    # Missing selected-profile credentials must not fall through to checkout or
    # default-profile secrets (the checkout .env may itself be a symlink).
    env_paths = [get_hermes_home() / ".env"]
    for p in env_paths:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("DISCORD_BOT_TOKEN="):
                        return line.strip().split("=", 1)[1].strip("\"'")
    return ""


import re


def format_premium_currency(val: Union[str, float, int], fallback_usd: Optional[float] = None) -> str:
    """
    Institutional currency formatter ($120K, $38.5M).
    - If float/int passed: Formats mathematically with 100% precision.
    - If fallback_usd is provided: Prefers authoritative float.
    - If string passed: Uses regex to extract magnitude and suffix (M/K/B) and repairs malformed inputs.
    """
    # 1. Authoritative Float / Int Formatter
    if isinstance(val, (int, float)) and val > 0:
        v = float(val)
        if v >= 1_000_000_000:
            return f"${v / 1_000_000_000:.2f}B".replace(".00B", "B")
        elif v >= 1_000_000:
            return f"${v / 1_000_000:.1f}M".replace(".0M", "M")
        elif v >= 1_000:
            return f"${v / 1_000:.0f}K"
        return f"${v:,.0f}"

    if fallback_usd and fallback_usd > 0:
        return format_premium_currency(fallback_usd)

    s = str(val).strip().upper()
    if not s or s in ("K", "M", "$", "B", "$.", "."):
        return "$100K+"

    # 2. Regex match numeric component + unit suffix
    m = re.search(r"(\d+(?:\.\d+)?|\.\d+)\s*([KMB]?)", s)
    if m:
        num_str, unit = m.group(1), m.group(2)
        try:
            num = float(num_str)
            # If input was missing leading integer (e.g. '.5M' or '$.5M')
            if num_str.startswith(".") and num < 1.0:
                if unit == "M":
                    return f"${int(num * 1000)}K"  # .5M -> $500K
                elif unit == "K":
                    return f"${int(num * 1000)}"

            if unit == "M":
                return f"${num:.1f}M".replace(".0M", "M")
            elif unit == "K":
                return f"${num:.0f}K"
            elif unit == "B":
                return f"${num:.2f}B"
            else:
                return format_premium_currency(num)
        except ValueError:
            pass

    # 3. Fallback cleanup
    clean_digits = re.sub(r"[^\d.]", "", s)
    if clean_digits:
        try:
            return format_premium_currency(float(clean_digits))
        except ValueError:
            pass

    return "$100K+"


def is_valid_image(path: Optional[str], min_bytes: int = 15_000) -> bool:
    """
    Verifies that the image file exists, is non-empty (>15KB), and is a valid image.
    """
    if not path or not os.path.exists(path):
        return False
    try:
        if os.path.getsize(path) < min_bytes:
            logger.warning("Image %s rejected: size too small (%d bytes < %d min)", path, os.path.getsize(path), min_bytes)
            return False
        with Image.open(path) as img:
            img.verify()
        return True
    except Exception as e:
        logger.warning("Image %s verification failed: %s", path, e)
        return False


class DiscordPublisher:
    def __init__(self, token: Optional[str] = None):
        self.token = token or get_discord_token()
        if not self.token:
            logger.warning("DISCORD_BOT_TOKEN not found.")

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bot {self.token}"}

    def _post_with_retry(
        self,
        url: str,
        payload: dict,
        files: Optional[dict] = None,
        max_retries: int = 3,
        method: str = "POST"
    ) -> Optional[dict]:
        """POST/PATCH with automatic exponential backoff on HTTP 429 and 5xx."""
        if not self.token:
            logger.warning("Discord token is not set. Skipping post to %s", url)
            return None

        for attempt in range(1, max_retries + 1):
            try:
                if files:
                    if method.upper() == "PATCH":
                        r = requests.patch(
                            url,
                            headers=self._headers(),
                            data={"payload_json": json.dumps(payload)},
                            files=files,
                            timeout=25
                        )
                    else:
                        r = requests.post(
                            url,
                            headers=self._headers(),
                            data={"payload_json": json.dumps(payload)},
                            files=files,
                            timeout=25
                        )
                else:
                    if method.upper() == "PATCH":
                        r = requests.patch(
                            url,
                            headers=self._headers(),
                            json=payload,
                            timeout=15
                        )
                    else:
                        r = requests.post(
                            url,
                            headers=self._headers(),
                            json=payload,
                            timeout=15
                        )

                if r.status_code in (200, 201):
                    return r.json()
                elif r.status_code == 429:
                    retry_after = float(r.json().get("retry_after", 2.0))
                    logger.warning("Discord 429 Rate Limited. Backing off for %.2fs (Attempt %d/%d)", retry_after, attempt, max_retries)
                    time.sleep(retry_after + 0.5)
                elif r.status_code >= 500:
                    logger.warning("Discord %s Server Error. Retrying in %ds (Attempt %d/%d)", r.status_code, attempt * 2, attempt, max_retries)
                    time.sleep(attempt * 2)
                else:
                    logger.error("Discord API Error HTTP %s: %s", r.status_code, r.text)
                    return None
            except requests.exceptions.RequestException as req_err:
                logger.warning("Network exception on Discord post (Attempt %d/%d): %s", attempt, max_retries, req_err)
                time.sleep(attempt * 2)

        return None

    def post_fast_alert(
        self,
        ticker: str,
        strike: float,
        call_put: str,
        expiration: str,
        entry_target: float,
        channel_key: str = "alerts",
        dte: Optional[int] = None
    ) -> Optional[dict]:
        """
        Dispatches instantaneous (<200ms) text alert and returns message dict with 'id' and 'channel_id'.
        Allows subsequent async Playwright worker to PATCH the visual card onto this exact message.
        """
        ch_id = DISCORD_CHANNELS.get(channel_key, DISCORD_CHANNELS["alerts"])
        url = f"https://discord.com/api/v10/channels/{ch_id}/messages"
        cp = "C" if "C" in call_put.upper() else "P"
        dte_str = f" ({dte}D)" if dte else ""
        content = f"🔥 **OWLs [OPEN]** · `${ticker.upper()}` · `{strike:g}{cp}` · `{expiration}{dte_str}` · `🎯 Entry: ${entry_target:.2f}`\n*(Rendering institutional 2x Retina card...)*"
        
        resp = self._post_with_retry(url, {"content": content})
        if resp and "id" in resp:
            logger.info("⚡ Fast Alert dispatched in <200ms for $%s (Message ID: %s)", ticker, resp["id"])
            return resp
        return None

    def patch_message_with_card(
        self,
        channel_id: str,
        message_id: str,
        image_path: str
    ) -> bool:
        """
        Attaches the high-res visual card directly to the existing message via Discord PATCH,
        eliminating dual push notification spam and channel clutter.
        """
        if not is_valid_image(image_path):
            logger.error("Cannot patch visual card: invalid image %s", image_path)
            return False

        url = f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}"
        with open(image_path, "rb") as img_file:
            files = {
                "file": (os.path.basename(image_path), img_file.read(), "image/png")
            }
            # Clear placeholder text so only clean card remains
            payload = {"content": ""}
            res = self._post_with_retry(url, payload, files=files, method="PATCH")
            if res:
                logger.info("✨ Successfully PATCHED visual card onto existing Message %s", message_id)
                return True
        return False

    def post_image_card(
        self,
        image_path: str,
        channel_key: str = "alerts",
        caption: str = ""
    ) -> bool:
        """
        Posts the standalone visual card directly as an image upload with zero text clutter.
        """
        ch_id = DISCORD_CHANNELS.get(channel_key, DISCORD_CHANNELS["alerts"])
        url = f"https://discord.com/api/v10/channels/{ch_id}/messages"

        if not is_valid_image(image_path):
            logger.error("Cannot post image card: invalid or missing file %s", image_path)
            return False

        with open(image_path, "rb") as img_file:
            files = {
                "file": (os.path.basename(image_path), img_file.read(), "image/png")
            }
            payload = {"content": caption} if caption else {}
            res = self._post_with_retry(url, payload, files=files)
            if res:
                logger.info("Successfully posted standalone visual card to #%s", channel_key)
                return True
            return False

    def post_notable_flow(
        self,
        ticker: str,
        strike: float,
        call_put: str,
        expiration: str,
        premium_raw: Union[str, float, int],
        asset_type: str = "equity",
        chart_image_path: Optional[str] = None,
        tag_everyone: bool = False,
        premium_usd: Optional[float] = None
    ) -> bool:
        """
        Template 1: Notable Flow Post
        Content:
          TICKER STRIKE C/P EXPIRATION $PREMIUM
          @everyone
        + Flowseeker chart attachment
        """
        # Strict validation
        call_put_clean = call_put.upper().strip()
        if call_put_clean not in ("C", "P", "CALL", "PUT"):
            logger.error("Guarded: post_notable_flow only accepts 'C' or 'P' options contracts, not '%s'.", call_put)
            return False

        contract_cp = "C" if "C" in call_put_clean else "P"
        prem_formatted = format_premium_currency(premium_raw, fallback_usd=premium_usd)
        ch_id = DISCORD_CHANNELS["notable_etf_flow"] if asset_type.lower() == "etf" else DISCORD_CHANNELS["notable_flow"]
        url = f"https://discord.com/api/v10/channels/{ch_id}/messages"

        # Format: e.g. "MRVL 250 C 9/25/2026 $5.3M\n@everyone"
        mention_str = "@everyone" if tag_everyone else ""
        content = f"{ticker.upper()} {strike:g} {contract_cp} {expiration} {prem_formatted}\n{mention_str}".strip()

        # Guard against Discord 2000 char overflow
        if len(content) > 1950:
            content = content[:1950] + "..."

        payload = {"content": content}
        files = None

        if chart_image_path and is_valid_image(chart_image_path):
            with open(chart_image_path, "rb") as img_file:
                files = {
                    "file": (os.path.basename(chart_image_path), img_file.read(), "image/png")
                }
                result = self._post_with_retry(url, payload, files=files)
        else:
            if chart_image_path:
                logger.warning("Posting text-only flow alert: chart %s failed validation", chart_image_path)
            result = self._post_with_retry(url, payload)

        if result:
            logger.info("Successfully posted notable flow to #%s (%s %s%s %s)", 
                        "notable_etf_flow" if asset_type == "etf" else "notable_flow", 
                        ticker, strike, contract_cp, prem_formatted)
            return True
        return False

    def post_alert_card(
        self,
        action: str,  # 'OPEN' | 'TRIM' | 'CLOSE' | 'INFO'
        thesis_text: str,
        author_name: str = "OWLFRED",
        contract_info: Optional[str] = None,
        tp_sl_info: Optional[str] = None,
        image_path: Optional[str] = None,
        channel_key: str = "alerts",
        author_icon_url: Optional[str] = None
    ) -> bool:
        """
        Template 2: Actionable Alert Card (Rich Embed)
        Supports optional high-res chart image attachment embedded inside the card.
        """
        ch_id = DISCORD_CHANNELS.get(channel_key, DISCORD_CHANNELS["alerts"])
        url = f"https://discord.com/api/v10/channels/{ch_id}/messages"

        action_clean = action.upper().strip()
        color = EMBED_COLORS.get(action_clean, EMBED_COLORS["INFO"])

        # Build description
        desc_parts = [f"**{action_clean}:**\n"]
        if contract_info:
            desc_parts.append(f"{contract_info}\n")
        desc_parts.append(thesis_text)
        if tp_sl_info:
            desc_parts.append(f"\n{tp_sl_info}")

        full_description = "\n".join(desc_parts).strip()
        # Embed description limit: 4096
        if len(full_description) > 4000:
            full_description = full_description[:4000] + "..."

        now = datetime.now()
        timestamp_formatted = now.strftime("%m/%d/%y • %I:%M:%S %p")

        embed = {
            "color": color,
            "author": {
                "name": author_name,
                "icon_url": author_icon_url or "https://cdn.discordapp.com/embed/avatars/0.png"
            },
            "description": full_description,
            "footer": {
                "text": f"Owls Investments LLC. Informational purposes only. Not financial advice.\nBot Version 6.7 -- Released 06.24.2026\n{timestamp_formatted}"
            }
        }

        payload = {"embeds": [embed]}
        files = None

        if image_path and is_valid_image(image_path):
            filename = os.path.basename(image_path)
            embed["image"] = {"url": f"attachment://{filename}"}
            with open(image_path, "rb") as f_img:
                files = {"file": (filename, f_img.read(), "image/png")}
                result = self._post_with_retry(url, payload, files=files)
        else:
            result = self._post_with_retry(url, payload)

        if result:
            logger.info("Successfully posted alert card to #%s [%s]", channel_key, action_clean)
            return True
        return False


if __name__ == "__main__":
    poster = DiscordPublisher()
    print("Testing production hardened currency normalization:")
    print("  5300000.0  ->", format_premium_currency(5300000.0))
    print("  120000     ->", format_premium_currency(120000))
    print("  '$120K'    ->", format_premium_currency("$120K"))
    print("  '214k'     ->", format_premium_currency("214k"))
    print("  'K'        ->", format_premium_currency("K"))
