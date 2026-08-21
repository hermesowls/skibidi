"""Automated Skylit.ai GEX Chart Capture using persistent Chrome profile (bypasses 2FA factor-one)."""

import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

def capture_gex_persistent(ticker: str = "SPX", output_path: str = "/tmp/skylit_gex.png"):
    chrome_profile_dir = Path.home() / "Library" / "Application Support" / "Google" / "Chrome"

    print(f"🚀 Launching Skylit GEX automation using persistent Chrome profile for {ticker}...")

    with sync_playwright() as p:
        try:
            # Use persistent context to reuse existing logged-in cookies/sessions
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(chrome_profile_dir),
                executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                headless=False,  # Headed mode for real canvas rendering
                viewport={"width": 1440, "height": 900},
                args=["--disable-blink-features=AutomationControlled"]
            )
        except Exception as e:
            print(f"Fallback to new context due to Chrome profile lock: {e}")
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 900})

        page = context.pages[0] if context.pages else context.new_page()

        ticker_clean = ticker.upper()
        target_url = f"https://app.skylit.ai/?ticker={ticker_clean}"
        print(f"1. Opening Skylit GEX page ({target_url})...")
        page.goto(target_url, wait_until="domcontentloaded")
        time.sleep(3)

        print(f"2. Current URL: {page.url}")

        # Check if auth required
        if "sign-in" in page.url or "factor-one" in page.url:
            print("Notice: Skylit requires factor-one / 2FA verification code.")
            page.screenshot(path="/tmp/skylit_auth_needed.png")

        print("3. Waiting 6 seconds for WebGL/Canvas GEX chart hydration...")
        time.sleep(6)

        print(f"4. Saving GEX screenshot to {output_path}...")
        page.screenshot(path=output_path, full_page=False)
        context.close()

        print(f"✓ Skylit GEX screenshot saved to {output_path}!")
        return output_path

if __name__ == "__main__":
    t = sys.argv[1] if len(sys.argv) > 1 else "SPX"
    out = sys.argv[2] if len(sys.argv) > 2 else "/tmp/skylit_gex.png"
    capture_gex_persistent(t, out)
