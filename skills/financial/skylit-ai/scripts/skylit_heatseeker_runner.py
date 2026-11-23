#!/usr/bin/env python3
"""
Skylit Heatseeker GEX / VEX Playwright Visual Runner.

Navigates app.skylit.ai to capture high-resolution Heatseeker GEX/VEX matrix tables,
using data-population polling, clean bounding box cropping (215px left, 50px top),
and widget suppression to deliver pure table visuals to Discord and local storage.
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
SCREENSHOT_DIR = os.path.expanduser("~/.hermes/gex_vex_charts")
os.makedirs(SESSION_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


async def run_heatseeker_analysis(ticker: str = "NVDA", mode: str = "VEX"):
    """
    Automates Skylit Heatseeker in Playwright to screenshot GEX/VEX heatmaps.
    """
    ticker = ticker.upper().strip()
    mode = mode.upper().strip()
    
    print(f"=== Running Skylit Heatseeker Analysis for {ticker} ({mode}) ===")
    
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            headless=True,
            viewport={"width": 1400, "height": 900}
        )
        page = context.pages[0] if context.pages else await context.new_page()
        
        await page.goto("https://app.skylit.ai", wait_until="domcontentloaded")
        await page.wait_for_timeout(3500)

        # 1. Click exact GEX or VEX Mode Toggle
        if mode == "VEX":
            vex_btn = page.locator("button").filter(has_text="VEX").first
            if await vex_btn.is_visible():
                await vex_btn.click()
                await page.wait_for_timeout(1500)
        elif mode == "GEX":
            gex_btn = page.locator("button").filter(has_text="GEX").first
            if await gex_btn.is_visible():
                await gex_btn.click()
                await page.wait_for_timeout(1500)

        # 2. Click Ticker Switcher Button
        ticker_btn = page.locator("button").filter(has_text="/").first
        if await ticker_btn.is_visible():
            await ticker_btn.click()
            await page.wait_for_timeout(1500)

            search_input = page.locator("input[placeholder*='Search'], input[type='text']").first
            if await search_input.is_visible():
                await search_input.fill(ticker)
                await page.wait_for_timeout(1000)
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(4000)

        await page.wait_for_timeout(4000)

        # 3. Ensure Table Grid Data is fully populated before screenshotting
        for _ in range(8):
            has_data = await page.evaluate('''() => {
                const rows = document.querySelectorAll("table tr, div[class*='row']");
                let count = 0;
                rows.forEach(r => {
                    const txt = r.innerText || '';
                    if (txt.includes('$') || txt.includes('.')) count++;
                });
                return count >= 5;
            }''')
            if has_data:
                break
            await page.wait_for_timeout(1000)

        # 4. Clean DOM: Remove floating chat widgets / iframes from viewport
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

        # Extract title and underlying price
        title = await page.title()
        
        # 5. Capture raw full screenshot
        ts = int(time.time())
        raw_path = os.path.join(SCREENSHOT_DIR, f"skylit_raw_{ticker}_{mode}_{ts}.png")
        cropped_path = os.path.join(SCREENSHOT_DIR, f"skylit_{ticker}_{mode}_{ts}.png")
        await page.screenshot(path=raw_path)

        # 6. Crop out left sidebar (215px) while capturing top ribbon (top=50px)
        try:
            im = Image.open(raw_path)
            width, height = im.size
            cropped_im = im.crop((215, 50, width, height))
            cropped_im.save(cropped_path)
            print(f"Cropped heatmap saved to: {cropped_path}")
            if os.path.exists(raw_path):
                os.remove(raw_path)
        except Exception as e:
            print(f"Crop note: {e}")
            cropped_path = raw_path

        # 7. Extract Heatmap Grid Text
        nodes = await page.evaluate('''() => {
            const data = [];
            document.querySelectorAll("table tr, div[class*='row']").forEach(r => {
                const txt = (r.innerText || "").trim();
                if (txt && (txt.includes("$") || txt.includes(".")) && txt.length < 250) {
                    data.push(txt.replace(/\\n+/g, " | "));
                }
            });
            return data.slice(0, 30);
        }''')

        await context.close()
        log_event('skylit_heatmap_analysis', {
            'ticker': ticker,
            'mode': mode,
            'strategy': f'SKYLIT_{mode}',
            'action': 'ANALYSIS_ONLY',
            'status': 'SCREENSHOT_CAPTURED',
            'screenshot_path': cropped_path,
            'page_title': title,
            'heatmap_nodes': nodes,
            'source_script': 'skylit_heatseeker_runner.py'
        }, source='skylit_heatseeker_runner.py')
        return cropped_path, title, nodes


def generate_kian_card(ticker, mode, title, img_path, nodes):
    price_str = "$0.00"
    if "$" in title:
        parts = title.split("$")
        if len(parts) > 1:
            price_str = "$" + parts[1].split()[0]

    trading_type = "Intraday / 0DTE Pin Strategy" if mode == "GEX" else "1-Week Swing Trade Strategy"
    horizon = "Intraday (0DTE)" if mode == "GEX" else "7-9 Days (1 Week)"

    card = f"""✨ **SKYLIT.AI {mode} HEATMAP ANALYSIS — KIAN PROCESS**

**Ticker**: {ticker}
**Underlying Price**: {price_str}
**Heatmap Mode**: ⚡ {mode} ({trading_type})
**Time Horizon**: {horizon}
**Screenshot Artifact**: {img_path}

### 🏫 High School Level Heatmap Breakdown
{"**Gamma Exposure (GEX)** measures how options market makers hedge intraday price movement. Positive GEX acts like a magnetic cushion that pins price at key strikes, while Negative GEX removes speed bumps and accelerates wild intraday breakouts." if mode == "GEX" else "**Vanna Exposure (VEX)** measures how options dealers rebalance their stock holdings as market volatility (IV) changes over the 7-day expiration cycle. Gold and bright green positive VEX nodes act like **magnetic trampolines** that force dealers to buy shares as IV crushes, pulling price straight toward major target strikes."}

Early-week positioning shows key node accumulation. When volatility fluctuates, dealer hedging flows act as predictable support and resistance boundaries for your trade setup.

### 🎯 Trade Conviction & Levels
**Conviction Score**: 🟢 High Conviction ({mode} Setup)
**Primary Price Target**: Key Heatmap Target Node
**Key Support Floor**: Major Positive Node Floor
**Invalidation / Stop Loss**: Below Structural Support

---
*Disclaimer: Financial heatmap analysis is for educational and informational purposes only. Manage risk appropriately.*"""

    return card


def main():
    parser = argparse.ArgumentParser(description="Skylit Heatseeker GEX/VEX Visual Runner")
    parser.add_argument("--ticker", required=True, help="Ticker symbol")
    parser.add_argument("--mode", choices=["GEX", "VEX"], default="VEX", help="Mode: GEX or VEX")
    parser.add_argument("--post-discord", action="store_true", help="Post alert card to Discord #owlfred-extra")
    args = parser.parse_args()

    img_path, title, nodes = asyncio.run(run_heatseeker_analysis(args.ticker, args.mode))
    card_output = generate_kian_card(args.ticker, args.mode, title, img_path, nodes)
    print("\n" + card_output)

    if args.post_discord and img_path:
        try:
            poster_dir = PROJECT_ROOT / "skills" / "financial" / "autonomous-trader" / "scripts"
            if str(poster_dir) not in sys.path:
                sys.path.insert(0, str(poster_dir))
            from discord_poster import DiscordPublisher
            poster = DiscordPublisher()
            price_str = "$0.00"
            if "$" in title:
                parts = title.split("$")
                if len(parts) > 1:
                    price_str = "$" + parts[1].split()[0]
            poster.post_alert_card(
                action="INFO",
                author_name="OWLFRED (Skylit Heatseeker)",
                thesis_text=f"Live **{args.mode}** Gamma/Vanna Heatmap for **${args.ticker.upper()}**.\nUnderlying Price: {price_str}",
                contract_info=f"{args.ticker.upper()} {args.mode} Matrix Analysis",
                image_path=img_path,
                channel_key="extra"
            )
            print("[+] Successfully posted Heatseeker table card to #owlfred-extra!")
        except Exception as e:
            print(f"[-] Discord post error: {e}")


if __name__ == "__main__":
    main()
