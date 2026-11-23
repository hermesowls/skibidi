#!/usr/bin/env python3
"""
Beginner Guidance Onboarding Publisher for #owlfred-beginner-guidance.

Publishes 3 comprehensive, beginner-friendly onboarding cards:
  1. Welcome & Channel Directory
  2. Small Account Risk Management & The "Free-Roll" Rule
  3. Step-by-Step Guide: How to Read and Execute OWLFRED Alerts
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "financial" / "autonomous-trader" / "scripts"))

from discord_poster import DiscordPublisher


def publish_onboarding():
    poster = DiscordPublisher()
    print("Publishing Beginner Guidance series to #owlfred-beginner-guidance...")

    # --- CARD 1: WELCOME & CHANNEL DIRECTORY ---
    c1_thesis = (
        "**Welcome to the Owls Trading Community!** 🦉\n\n"
        "OWLFRED is your institutional options flow and risk management engine. "
        "Here is a quick breakdown of our key channels and how to navigate them:\n\n"
        "🎯 **`#owlfred-alerts`**\n"
        "• High-conviction, actionable trade recommendations.\n"
        "• Comes with exact contract strikes, entry targets, TP1/TP2 goals, and hard stop losses.\n\n"
        "🌊 **`#owlfred-notable-flow`**\n"
        "• Live whale flow on individual stocks (Equities only).\n"
        "• Includes real-time Flowseeker dual-chart volume and delta tape screenshots.\n\n"
        "📊 **`#owlfred-notable-etf-flow`**\n"
        "• Institutional block flow and darkpool accumulation on index ETFs (`SPY`, `QQQ`, `IWM`, `GLD`).\n\n"
        "⚡ **`#owlfred-extra`**\n"
        "• Live GEX/VEX heatmaps, King Node support/resistance walls, and market structure briefings."
    )

    ok1 = poster.post_alert_card(
        action="INFO",
        author_name="OWLFRED ONBOARDING",
        contract_info="📚 **OWLFRED ECOSYSTEM & CHANNEL GUIDE**",
        thesis_text=c1_thesis,
        channel_key="beginner_guidance"
    )
    print("Card 1 Posted:", ok1)
    time.sleep(1.5)

    # --- CARD 2: GOLDEN RULES OF RISK MANAGEMENT ---
    c2_thesis = (
        "**The #1 goal in trading is capital preservation.** Follow these core rules to protect your account:\n\n"
        "🛡️ **1. Account Risk Caps (Never Risk the Whole Account)**\n"
        "• **Micro Accounts (< $1,000):** Maximum risk per trade should be **$30 – $50**.\n"
        "• **Growing Accounts ($1,000 – $5,000):** Maximum risk per trade should be **$100 – $200**.\n"
        "• **Standard Accounts ($5,000+):** Risk **2% – 5%** of total portfolio balance.\n\n"
        "🛑 **2. The -30% Hard Stop Rule**\n"
        "• Every trade alert comes with an explicit stop loss level (-30%).\n"
        "• **Always cut losses when the stop is hit.** Never hope or hold losing options through severe decay.\n\n"
        "🚀 **3. The 'Free-Roll' Rule (Lock in Guaranteed Profits)**\n"
        "• When trading 2+ contracts: Sell 1 contract at **TP1 (+45%)** and immediately move your stop loss on the remaining contract to your **entry price**.\n"
        "• *Result:* You locked in profit on contract 1, and contract 2 is a **100% Risk-Free Runner** with zero downside!\n\n"
        "⚠️ **4. The Affordability Rule**\n"
        "• If a contract costs more than you can afford (e.g. $1,000+ per con), **PASS and wait**.\n"
        "• We alert plenty of high-quality $50 – $150 setups. Never gamble a massive chunk of your account on a single trade."
    )

    ok2 = poster.post_alert_card(
        action="OPEN",
        author_name="OWLFRED RISK MANAGER",
        contract_info="🛡️ **THE GOLDEN RULES OF RISK MANAGEMENT**",
        thesis_text=c2_thesis,
        channel_key="beginner_guidance"
    )
    print("Card 2 Posted:", ok2)
    time.sleep(1.5)

    # --- CARD 3: HOW TO READ & EXECUTE AN ALERT ---
    c3_thesis = (
        "Every official trade alert in **`#owlfred-alerts`** is posted in two clear, paired cards:\n\n"
        "🟢 **Card 1: The Trade Setup (OPEN)**\n"
        "• **Contract:** The exact Ticker, Strike, Call/Put, and Expiration Date (e.g. `BNTX 115C 09/18/2026`).\n"
        "• **Entry Price:** The target price to buy the contract at open.\n"
        "• **Thesis:** Why institutions are accumulating this position (Conviction Score, Volume vs Open Interest, and GEX levels).\n"
        "• **Tape Chart:** High-res screenshot of the institutional tape.\n\n"
        "🔵 **Card 2: Sizing & Targets**\n"
        "• **Account Sizing:** Clear recommendations on how many contracts to buy based on your account size.\n"
        "• **🎯 TP1 (+45%):** Take profit level to trim 50–60% of position and move stop to breakeven.\n"
        "• **🚀 TP2 (+100%+):** Extended target to let runners capture explosive multi-day momentum.\n"
        "• **🛑 Stop Loss (-30%):** Invalidation price where we exit to protect capital.\n\n"
        "💡 *Tip: Set your alerts on your broker right after entering so your profit takes and stop losses trigger automatically!*"
    )

    ok3 = poster.post_alert_card(
        action="INFO",
        author_name="OWLFRED GUIDE",
        contract_info="🚦 **HOW TO READ & EXECUTE AN OWLFRED ALERT**",
        thesis_text=c3_thesis,
        channel_key="beginner_guidance"
    )
    print("Card 3 Posted:", ok3)


if __name__ == "__main__":
    publish_onboarding()
