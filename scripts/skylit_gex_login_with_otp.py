"""Skylit Authentication & Session Storage Manager."""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

env_path = Path.home() / ".hermes" / ".env"
if not env_path.exists():
    env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

email = os.getenv("SKYLIT_EMAIL", "saidikian@gmail.com")
password = os.getenv("SKYLIT_PASSWORD", "SkyKian12!")
storage_state_path = Path.home() / ".hermes" / "skylit_storage_state.json"

def get_authenticated_context(p):
    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"]
    )

    if storage_state_path.exists():
        print(f"Loading existing session from {storage_state_path}...")
        context = browser.new_context(
            storage_state=str(storage_state_path),
            viewport={"width": 1440, "height": 900}
        )
        page = context.new_page()
        page.goto("https://app.skylit.ai/", wait_until="networkidle")
        time.sleep(2)
        if "sign-in" not in page.url and "access-required" not in page.url:
            print("✓ Session valid!")
            return browser, context, page

    print("Session expired or missing. Initializing fresh login...")
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()

    page.goto("https://app.skylit.ai/sign-in", wait_until="networkidle")
    time.sleep(2)

    print(f"1. Entering email ({email})...")
    page.wait_for_selector("#identifier-field", timeout=10000)
    page.fill("#identifier-field", email)
    page.press("#identifier-field", "Enter")
    time.sleep(3)

    print("2. Entering password...")
    page.wait_for_selector("#password-field", timeout=10000)
    page.fill("#password-field", password)
    page.press("#password-field", "Enter")
    time.sleep(4)

    print(f"3. Page URL after password: {page.url}")

    if "factor-one" in page.url or "code" in page.content().lower():
        print("\n⚠️ Skylit (Clerk) requires a 2FA OTP verification code sent to your email/authenticator!")
        otp_code = input("Enter the 6-digit verification code: ").strip()

        # Fill code input
        code_input = page.query_selector("input[name='code'], input[type='text'], input[id*='code']")
        if code_input:
            code_input.fill(otp_code)
            page.press("input[name='code'], input[type='text'], input[id*='code']", "Enter")
            time.sleep(4)

    print(f"4. Authenticated URL: {page.url}")
    context.storage_state(path=str(storage_state_path))
    print(f"✓ Session saved to {storage_state_path}")
    return browser, context, page

def capture_gex(ticker: str = "SPX", output_path: str = "/tmp/skylit_gex.png"):
    from playwright.sync_api import sync_playwright

    print(f"🚀 Capturing Skylit GEX chart for {ticker}...")
    with sync_playwright() as p:
        browser, context, page = get_authenticated_context(p)

        ticker_clean = ticker.upper()
        target_url = f"https://app.skylit.ai/?ticker={ticker_clean}"
        print(f"Navigating to {target_url}...")
        page.goto(target_url, wait_until="networkidle")

        print("Waiting for GEX Canvas / WebGL chart hydration...")
        time.sleep(6)

        page.screenshot(path=output_path, full_page=False)
        print(f"✓ Saved GEX screenshot to {output_path}")

        browser.close()
        return output_path

if __name__ == "__main__":
    t = sys.argv[1] if len(sys.argv) > 1 else "SPX"
    out = sys.argv[2] if len(sys.argv) > 2 else "/tmp/skylit_gex.png"
    capture_gex(t, out)
