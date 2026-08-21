"""Capture Skylit GEX chart using active logged in session."""

import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

storage_state_path = Path.home() / ".hermes" / "skylit_storage_state.json"

def capture_now(ticker: str = "SPX", output_path: str = "/tmp/skylit_gex_live.png"):
    chrome_profile_dir = Path.home() / "Library" / "Application Support" / "Google" / "Chrome"

    print(f"🚀 Capturing live Skylit GEX chart for {ticker}...")

    with sync_playwright() as p:
        # Launch using Chrome profile or persistent context
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(chrome_profile_dir),
                executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                headless=False,
                viewport={"width": 1440, "height": 900},
                args=["--disable-blink-features=AutomationControlled"]
            )
        except Exception:
            # Fallback if profile is locked
            if storage_state_path.exists():
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    storage_state=str(storage_state_path),
                    viewport={"width": 1440, "height": 900}
                )
            else:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(viewport={"width": 1440, "height": 900})

        page = context.pages[0] if context.pages else context.new_page()

        ticker_clean = ticker.upper()
        target_url = f"https://app.skylit.ai/?ticker={ticker_clean}"
        print(f"1. Navigating to {target_url}...")
        page.goto(target_url, wait_until="domcontentloaded")
        time.sleep(3)

        print(f"2. Current URL: {page.url}")

        # Save session state if logged in
        if "sign-in" not in page.url and "access-required" not in page.url:
            context.storage_state(path=str(storage_state_path))
            print(f"✓ Saved authenticated session state to {storage_state_path}")

        print("3. Waiting 6 seconds for WebGL/Canvas GEX chart hydration...")
        time.sleep(6)

        print(f"4. Saving GEX screenshot to {output_path}...")
        page.screenshot(path=output_path, full_page=False)

        # Copy to artifacts directory
        artifact_path = f"/Users/admin/.gemini/antigravity-ide/brain/7a429be9-82e9-4926-b2af-b0f655fa5fb3/skylit_{ticker_clean.lower()}_gex.png"
        page.screenshot(path=artifact_path, full_page=False)

        context.close()
        print(f"✓ Skylit GEX screenshot successfully saved to {artifact_path}!")
        return artifact_path

if __name__ == "__main__":
    t = sys.argv[1] if len(sys.argv) > 1 else "SPX"
    out = sys.argv[2] if len(sys.argv) > 2 else "/tmp/skylit_gex_live.png"
    capture_now(t, out)
