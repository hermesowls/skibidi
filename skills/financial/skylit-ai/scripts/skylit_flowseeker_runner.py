#!/usr/bin/env python3
"""
Skylit Flowseeker Visual Whale Flow Runner.

Navigates app.skylit.ai/flow/live and /flow/lookup to spot whale flow accumulation,
capture high-resolution dual-chart tape screenshots, and publish verified notable flow
alerts to Discord (#owlfred-notable-flow or #owlfred-notable-etf-flow).
"""

import os
import sys
import asyncio
import json
import time
import argparse
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Optional strategy logger
try:
    from strategy_logger import log_event
except Exception:
    def log_event(*args, **kwargs): return None

from playwright.async_api import async_playwright

SESSION_DIR = os.path.expanduser("~/.hermes/browser_sessions/skylit_ai")
FLOW_CHARTS_DIR = os.path.expanduser("~/.hermes/flow_charts")
os.makedirs(SESSION_DIR, exist_ok=True)
os.makedirs(FLOW_CHARTS_DIR, exist_ok=True)

ETF_TICKERS = {"SPY", "QQQ", "IWM", "DIA", "SMH", "XLE", "XLF", "XLK", "XBI", "GLD", "SLV", "TLT", "HYG", "LQD", "VIX", "UVXY", "SQQQ", "TQQQ", "SOXL", "SOXS", "EWY", "EEM", "GDX", "IBIT"}


async def capture_flowseeker_chart(
    ticker: str,
    strike: float,
    call_put: str,
    expiration: str,
    premium_raw: str = ""
) -> str:
    """
    Automates Skylit Flowseeker to capture dual-chart flow visual tape.
    """
    ticker = ticker.upper().strip()
    call_put = call_put.upper().strip()
    contract_str = f"{ticker} {strike:g}{call_put} {expiration}"
    print(f"=== Running Skylit Flowseeker Capture for {contract_str} ===")
    
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            headless=True,
            viewport={"width": 1400, "height": 850}
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        
        # Navigate to Flow Lookup
        await page.goto("https://app.skylit.ai/flow/lookup", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        # Search for ticker in Flow Lookup
        search_box = page.locator("input[placeholder*='Search' i], input[type='text']").first
        if await search_box.is_visible():
            await search_box.fill(ticker)
            await page.wait_for_timeout(800)
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(3500)

        # Suppress chat widgets / iframes
        try:
            await page.add_style_tag(content="""
                iframe, [class*='intercom'], [class*='chat'], [class*='widget'], 
                button[aria-label*='chat' i], div[id*='drift'] { 
                    display: none !important; 
                    visibility: hidden !important; 
                }
            """)
        except Exception:
            pass

        # Capture Flow Chart
        ts = int(time.time())
        raw_path = os.path.join(FLOW_CHARTS_DIR, f"flow_raw_{ticker}_{strike:g}{call_put}_{ts}.png")
        cropped_path = os.path.join(FLOW_CHARTS_DIR, f"flow_{ticker}_{strike:g}{call_put}_{ts}.png")
        await page.screenshot(path=raw_path)

        # Clean crop
        try:
            im = Image.open(raw_path)
            w, h = im.size
            cropped_im = im.crop((215, 50, w, h))
            cropped_im.save(cropped_path)
            print(f"[+] Clean Flowseeker chart saved: {cropped_path}")
            if os.path.exists(raw_path):
                os.remove(raw_path)
        except Exception as e:
            print(f"Crop note: {e}")
            cropped_path = raw_path

        await ctx.close()
        return cropped_path


def main():
    parser = argparse.ArgumentParser(description="Skylit Flowseeker Visual Whale Flow Runner")
    parser.add_argument("--ticker", required=True, help="Ticker symbol (e.g. NVDA, SPY, BNTX)")
    parser.add_argument("--strike", type=float, required=True, help="Strike price (e.g. 250)")
    parser.add_argument("--call-put", choices=["C", "P", "c", "p"], required=True, help="Call or Put")
    parser.add_argument("--expiration", required=True, help="Expiration date (e.g. 11/20/2026)")
    parser.add_argument("--premium", default="", help="Raw premium string (e.g. $214K, $5.3M)")
    parser.add_argument("--post-discord", action="store_true", help="Post notable flow alert to Discord")
    args = parser.parse_args()

    chart_path = asyncio.run(capture_flowseeker_chart(
        ticker=args.ticker,
        strike=args.strike,
        call_put=args.call_put,
        expiration=args.expiration,
        premium_raw=args.premium
    ))

    print(f"\nFlowseeker Screenshot Captured: {chart_path}")

    if args.post_discord and chart_path:
        try:
            poster_dir = PROJECT_ROOT / "skills" / "financial" / "autonomous-trader" / "scripts"
            if str(poster_dir) not in sys.path:
                sys.path.insert(0, str(poster_dir))
            from discord_poster import DiscordPublisher
            poster = DiscordPublisher()
            asset_type = "etf" if args.ticker.upper() in ETF_TICKERS else "equity"
            success = poster.post_notable_flow(
                ticker=args.ticker.upper(),
                strike=args.strike,
                call_put=args.call_put.upper(),
                expiration=args.expiration,
                premium_raw=args.premium or "$150K+",
                asset_type=asset_type,
                chart_image_path=chart_path,
                tag_everyone=False
            )
            print(f"[+] Posted Notable Flow to #{'owlfred-notable-etf-flow' if asset_type == 'etf' else 'owlfred-notable-flow'}: {success}")
        except Exception as e:
            print(f"[-] Discord post error: {e}")


if __name__ == "__main__":
    main()
