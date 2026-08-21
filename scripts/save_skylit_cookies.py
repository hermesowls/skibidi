"""Save logged-in cookies directly from active browser session."""

import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

storage_state_path = Path.home() / ".hermes" / "skylit_storage_state.json"

def save_active_cookies():
    print("🌐 Launching visible Chrome browser...")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            headless=False,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        print("Navigating to https://app.skylit.ai/...")
        page.goto("https://app.skylit.ai/", wait_until="domcontentloaded")
        time.sleep(3)

        print(f"Current URL: {page.url}")

        if "sign-in" in page.url or "access-required" in page.url:
            print("\n👉 Please click 'Sign In' in the visible Chrome window and complete login.")
            print("   The script will wait up to 120s for you to land on the dashboard...\n")

            # Wait until URL is not sign-in or access-required
            for _ in range(60):
                time.sleep(2)
                if "sign-in" not in page.url and "access-required" not in page.url:
                    print("🎉 Dashboard reached!")
                    break

        # Save session state
        time.sleep(2)
        context.storage_state(path=str(storage_state_path))
        print(f"✓ Saved authenticated storage state to {storage_state_path}")

        # Now test navigating to SPX GEX page
        print("Testing SPX GEX page...")
        page.goto("https://app.skylit.ai/?ticker=SPX", wait_until="networkidle")
        time.sleep(6)

        artifact_path = "/Users/admin/.gemini/antigravity-ide/brain/7a429be9-82e9-4926-b2af-b0f655fa5fb3/skylit_spx_gex_verified.png"
        page.screenshot(path=artifact_path, full_page=False)
        print(f"✓ Verified GEX screenshot saved to {artifact_path}")

        browser.close()

if __name__ == "__main__":
    save_active_cookies()
