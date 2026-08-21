"""Automated Skylit.ai GEX Chart Screenshot Capture Engine using saved session state."""

import os
import sys
import time
from pathlib import Path

storage_state_path = Path.home() / ".hermes" / "skylit_storage_state.json"

def capture_gex(ticker: str = "SPX", output_path: str = "/tmp/skylit_gex.png"):
    from playwright.sync_api import sync_playwright

    ticker_clean = ticker.upper()
    print(f"🚀 Capturing Skylit GEX chart for {ticker_clean}...")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )

        if storage_state_path.exists():
            print(f"Loading authenticated session state from {storage_state_path}...")
            context = browser.new_context(
                storage_state=str(storage_state_path),
                viewport={"width": 1440, "height": 900},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            )
        else:
            print("Warning: No storage state found. Launching fresh context...")
            context = browser.new_context(viewport={"width": 1440, "height": 900})

        page = context.new_page()

        target_url = f"https://app.skylit.ai/?ticker={ticker_clean}"
        print(f"1. Navigating to {target_url}...")
        page.goto(target_url, wait_until="domcontentloaded")
        time.sleep(3)

        print(f"2. Current URL: {page.url}")

        # Check if auth required
        if "sign-in" in page.url or "access-required" in page.url:
            print("⚠️ Session expired or access required.")
            page.screenshot(path=output_path)
            browser.close()
            return output_path

        # Step 5: Hydration Wait for Canvas / WebGL GEX Chart
        print("3. Waiting 6 seconds for WebGL/Canvas GEX chart hydration...")
        time.sleep(6)

        # Step 6: Take crisp screenshot
        print(f"4. Saving GEX screenshot to {output_path}...")
        page.screenshot(path=output_path, full_page=False)

        # Copy to artifacts directory
        artifact_path = f"/Users/admin/.gemini/antigravity-ide/brain/7a429be9-82e9-4926-b2af-b0f655fa5fb3/skylit_{ticker_clean.lower()}_gex.png"
        page.screenshot(path=artifact_path, full_page=False)

        browser.close()

        print(f"✓ Skylit GEX screenshot successfully saved to {artifact_path}!")
        return artifact_path

if __name__ == "__main__":
    ticker_arg = sys.argv[1] if len(sys.argv) > 1 else "SPX"
    out_arg = sys.argv[2] if len(sys.argv) > 2 else "/tmp/skylit_gex.png"
    capture_gex(ticker_arg, out_arg)
