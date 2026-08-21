from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})

    print("Navigating to https://app.skylit.ai/sign-in...")
    page.goto("https://app.skylit.ai/sign-in", wait_until="networkidle")
    time.sleep(3)

    print("URL after navigation:", page.url)
    print("Page Title:", page.title())

    page.screenshot(path="/tmp/skylit_signin_elements.png")

    inputs = page.query_selector_all("input")
    print(f"\nFound {len(inputs)} input fields:")
    for inp in inputs:
        print("Input field:", inp.get_attribute("type"), "| name:", inp.get_attribute("name"), "| placeholder:", inp.get_attribute("placeholder"), "| id:", inp.get_attribute("id"), "| class:", inp.get_attribute("class"))

    buttons = page.query_selector_all("button, a")
    print(f"\nFound {len(buttons)} buttons/links:")
    for b in buttons:
        try:
            txt = b.inner_text().strip().replace("\n", " ")
            if txt and len(txt) < 50:
                print("Text:", txt, "| Href:", b.get_attribute("href"), "| Type:", b.get_attribute("type"))
        except Exception:
            pass

    browser.close()
