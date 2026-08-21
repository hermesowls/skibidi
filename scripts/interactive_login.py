"""Interactive Skylit Login - Waits until user is 100% logged in on dashboard."""

import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

storage_state_path = Path.home() / ".hermes" / "skylit_storage_state.json"

def run_interactive_login():
    print("🌐 Opening visible Chrome for Skylit login...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            headless=False,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        print("Navigating to https://app.skylit.ai/sign-in...")
        page.goto("https://app.skylit.ai/sign-in", wait_until="domcontentloaded")

        print("\n" + "="*60)
        print("👉 PLEASE CLICK 'SIGN IN', ENTER YOUR EMAIL & PASSWORD, AND LOG IN.")
        print("   Keep this window open until you see the actual Skylit dashboard / GEX charts.")
        print("="*60 + "\n")

        # Keep browser open & poll until authenticated dashboard element is visible
        logged_in = False
        for i in range(120): # Wait up to 6 minutes
            time.sleep(3)
            url = page.url
            content = page.content().lower()

            # Check if user reached authenticated dashboard (no sign-in form & no access-required)
            if ("sign-in" not in url and "access-required" not in url and "factor-one" not in url) and ("logout" in content or "dashboard" in url or "search" in content or "gex" in content):
                print(f"\n🎉 LOGGED-IN DASHBOARD DETECTED! (URL: {url})")
                time.sleep(3)
                context.storage_state(path=str(storage_state_path))
                print(f"✓ Saved authenticated session state to {storage_state_path}")

                # Test capturing SPX GEX
                print("Testing SPX GEX page capture...")
                page.goto("https://app.skylit.ai/?ticker=SPX", wait_until="networkidle")
                time.sleep(6)

                artifact_path = "/Users/admin/.gemini/antigravity-ide/brain/7a429be9-82e9-4926-b2af-b0f655fa5fb3/skylit_spx_gex_verified.png"
                page.screenshot(path=artifact_path, full_page=False)
                print(f"✓ Verified SPX GEX chart screenshot saved to {artifact_path}")
                logged_in = True
                break

        if not logged_in:
            print("Notice: Still on login page or timed out.")

        browser.close()

if __name__ == "__main__":
    run_interactive_login()
