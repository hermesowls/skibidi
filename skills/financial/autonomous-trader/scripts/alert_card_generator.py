#!/usr/bin/env python3
"""
Custom Graphical Alert Card Generator for OWLFRED.

Generates high-resolution, institutional-grade dark-mode alert cards (1200x630)
using Pillow with neon accents, visual target ribbons, and account sizing matrices.
"""

import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
OUTPUT_DIR = Path.home() / ".hermes" / "alert_cards"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def create_graphic_alert_card(
    ticker: str,
    strike: float,
    call_put: str,
    expiration: str,
    dte: int,
    entry_price: float,
    spot_price: float,
    tp1_price: float,
    tp2_price: float,
    stop_loss_price: float,
    conviction_score: float,
    score_badge: str,
    action: str = "OPEN",
    tier_name: str = "Tier 2: Asymmetric Runner",
    vol_to_oi: float = 3.5
) -> str:
    """
    Renders a custom graphical alert card and saves as PNG.
    """
    ticker = ticker.upper().strip()
    contract_cp = "C" if "C" in call_put.upper() else "P"
    contract_str = f"{ticker} {strike:g}{contract_cp}"
    
    # 1. Canvas Setup (1200x650)
    w, h = 1200, 650
    img = Image.new("RGB", (w, h), color=(15, 23, 42))  # Deep Slate #0f172a
    draw = ImageDraw.Draw(img)

    # 2. Outer Glowing Accent Border (Neon Green for OPEN)
    border_color = (0, 255, 102) if action.upper() == "OPEN" else (255, 42, 85)
    draw.rounded_rectangle([15, 15, w - 15, h - 15], radius=24, outline=border_color, width=3)

    # 3. Inner Card Panel (Dark Glass #1e293b)
    draw.rounded_rectangle([30, 30, w - 30, h - 30], radius=18, fill=(30, 41, 59))

    # Font Setup (System fallback)
    try:
        font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 38)
        font_ticker = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
        font_sub = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
        font_metric = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 26)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
    except Exception:
        font_title = ImageFont.load_default()
        font_ticker = font_title
        font_sub = font_title
        font_metric = font_title
        font_small = font_title

    # 4. Header Bar
    draw.text((55, 50), "🦉 OWLFRED", fill=(255, 255, 255), font=font_title)
    draw.rounded_rectangle([270, 52, 380, 92], radius=8, fill=(0, 255, 102))
    draw.text((285, 58), action.upper(), fill=(0, 0, 0), font=font_sub)
    draw.text((405, 60), f"|  {tier_name.upper()}  |  CONVICTION: {conviction_score:.0f}/100 {score_badge}", fill=(148, 163, 184), font=font_sub)

    # 5. Main Contract Ribbon
    draw.rounded_rectangle([55, 115, w - 55, 205], radius=14, fill=(15, 23, 42), outline=(51, 65, 85), width=2)
    draw.text((80, 130), contract_str, fill=(0, 255, 102), font=font_ticker)
    draw.text((380, 142), f"EXP: {expiration} ({dte} DTE)", fill=(241, 245, 249), font=font_title)
    draw.text((820, 145), f"ENTRY: ${entry_price:.2f}", fill=(56, 189, 248), font=font_title)

    # 6. Targets & Stop Loss Strip
    # TP1 Box
    draw.rounded_rectangle([55, 225, 400, 325], radius=12, fill=(13, 148, 136), outline=(45, 212, 191), width=2)
    draw.text((75, 240), "🎯 TAKE PROFIT 1 (+45%)", fill=(204, 251, 241), font=font_sub)
    draw.text((75, 272), f"${tp1_price:.2f}", fill=(255, 255, 255), font=font_ticker)
    draw.text((230, 282), "Trim 60% & Move SL", fill=(204, 251, 241), font=font_small)

    # TP2 Box
    draw.rounded_rectangle([425, 225, 770, 325], radius=12, fill=(124, 58, 237), outline=(167, 139, 250), width=2)
    draw.text((445, 240), "🚀 TAKE PROFIT 2 (+120%)", fill=(237, 233, 254), font=font_sub)
    draw.text((445, 272), f"${tp2_price:.2f}", fill=(255, 255, 255), font=font_ticker)
    draw.text((610, 282), "Hold Runner Target", fill=(237, 233, 254), font=font_small)

    # Stop Loss Box
    draw.rounded_rectangle([795, 225, w - 55, 325], radius=12, fill=(159, 18, 57), outline=(244, 63, 94), width=2)
    draw.text((815, 240), "🛑 HARD STOP LOSS (-30%)", fill=(255, 228, 230), font=font_sub)
    draw.text((815, 272), f"${stop_loss_price:.2f}", fill=(255, 255, 255), font=font_ticker)
    draw.text((980, 282), "Strict Invalidation", fill=(255, 228, 230), font=font_small)

    # 7. Beginner-Friendly Account Sizing Matrix Box
    draw.rounded_rectangle([55, 345, w - 55, 560], radius=14, fill=(15, 23, 42), outline=(51, 65, 85), width=2)
    draw.text((80, 360), "🛡️ ACCOUNT SIZING & RISK RULES (MAX 2% – 5% RISK):", fill=(250, 204, 21), font=font_sub)

    con_cost = int(entry_price * 100)
    stop_risk = int(con_cost * 0.30)
    
    if stop_risk > 50 or con_cost > 200:
        micro_txt = f"• Micro (< $1k):  ⚠️ PASS / WAIT (1 con is ${con_cost:,} — too expensive for micro accounts)"
    else:
        micro_txt = f"• Micro (< $1k):  1 Contract (~${con_cost} outlay | Max stop risk: ~${stop_risk})"

    if stop_risk > 250 or con_cost > 1000:
        grow_txt = f"• Growing ($1k–$5k):  ⚠️ PASS (Exceeds safe risk budget for accounts under $5k)"
    else:
        grow_txt = f"• Growing ($1k–$5k):  1 – 2 Contracts  (Sell 1 at TP1, move stop to entry for Risk-Free Runner!)"

    std_txt = f"• Standard ($5k+):    2 – 5 Contracts  (Max loss per contract with SL: ~${stop_risk})"

    draw.text((80, 400), micro_txt, fill=(241, 245, 249), font=font_metric)
    draw.text((80, 445), grow_txt, fill=(56, 189, 248), font=font_metric)
    draw.text((80, 490), std_txt, fill=(148, 163, 184), font=font_metric)

    # 8. Footer
    draw.text((55, 595), "Owls Investments LLC. Informational purposes only. Not financial advice. Bot Version 6.7", fill=(100, 116, 139), font=font_small)

    # 9. Save
    card_path = str(OUTPUT_DIR / f"alert_card_{ticker}_{strike:g}{contract_cp}_{int(entry_price*100)}.png")
    img.save(card_path, quality=95)
    print(f"[+] Graphical Alert Card generated: {card_path}")
    return card_path


if __name__ == "__main__":
    card = create_graphic_alert_card(
        ticker="BNTX",
        strike=115.0,
        call_put="C",
        expiration="09/18/2026",
        dte=27,
        entry_price=1.20,
        spot_price=98.50,
        tp1_price=1.74,
        tp2_price=2.64,
        stop_loss_price=0.84,
        conviction_score=85.0,
        score_badge="STRONG",
        action="OPEN",
        tier_name="Tier 2: Asymmetric Runner"
    )
