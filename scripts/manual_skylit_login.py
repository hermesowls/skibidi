"""Interactive Manual Skylit.ai Login Session Saver."""

import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

storage_state_path = Path.home() / ".hermes" / "skylit_storage_state.json"
storage_state_path.parent.mkdir(parents=True, exist_ok=True)

def run_manual_login():
    print("🌐 Launching visible Google Chrome browser for manual Skylit.ai login...")

    with sync_playwright() as p:
        # Launch visible headed Chrome browser
        browser = p.chromium.launch(
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            headless=False,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        print("Navigating to https://app.skylit.ai/sign-in...")
        page.goto("https://app.skylit.ai/sign-in")

        print("\n" + "=" * 60)
        print("👉 PLEASE LOG IN MANUALLY IN THE VISIBLE CHROME WINDOW NOW.")
        print("   The script will automatically detect when you're logged in")
        print("   and save your session to ~/.hermes/skylit_storage_state.json")
        print("=" * 60 + "\n")

        # Monitor until user logs in successfully
        max_wait_seconds = 300
        start_time = time.time()

        while time.time() - start_time < max_wait_seconds:
            curr_url = page.url
            # Check if user reached main app or dashboard
            if "app.skylit.ai" in curr_url and "sign-in" not in curr_url and "access-required" not in curr_url:
                print(f"\n🎉 Successful login detected! Current URL: {curr_url}")
                time.sleep(3)
                context.storage_state(path=str(storage_state_path))
                print(f"✓ Session storage state successfully saved to: {storage_state_path}\n")
                browser.close()
                return True

            time.sleep(2)

        print("\n⌛ Login wait timeout reached (5 minutes). Saving current state...")
        context.storage_state(path=str(storage_state_path))
        browser.close()
        return False

if __name__ == "__main__":
    run_manual_login()
