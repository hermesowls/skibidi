#!/usr/bin/env python3
"""
flow_card_generator.py - OWLs Flagship HTML/CSS + Playwright Chromium Card Renderer.
- Subtitle: "NOTABLE FLOW" under OWLs header logo.
- Score Panel: "INSTITUTIONAL CONVICTION" score + Agent Confluence Reasoning block
  (synthesizing technical, social/sentiment, and macro confluence checks).
- Bottom Metrics: 3 equal columns (ENTRY, STOCK, STOCK MOVE) - STATUS removed.
"""

import os
import sys
import json
from datetime import datetime
import urllib.request
from playwright.sync_api import sync_playwright

TRADING_SCRIPTS_DIR = os.path.abspath(os.path.dirname(__file__))
if TRADING_SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, TRADING_SCRIPTS_DIR)


def generate_owls_card_html(
    ticker: str = "NVDA",
    strike: str = "$220",
    type_: str = "PUT",
    expiration: str = "2026-07-31",
    score: float = 8.7,
    score_label: str = "INSTITUTIONAL CONVICTION",
    reasoning: str = "Heavy $287K Put sweep supported by 78% Ask-side urgency, price holding above 200-SMA, and favorable macro VIX regime.",
    technical_check: str = "Price > 200-SMA (Bullish Trend)",
    sentiment_check: str = "78% Ask Buy Accumulation",
    macro_check: str = "VIX 14.2 (Risk-On Regime)",
    premium: str = "$287,529",
    entry: str = "$10.65",
    size: str = "270",
    quality: str = "High Quality",
    flow: str = "Institutional Flow",
    stock: str = "$205.88",
    stock_move: str = "-2.08%"
) -> str:
    """Generate HTML/CSS template with exact user-defined visual specifications."""

    is_put = "PUT" in type_.upper()
    badge_bg = "linear-gradient(135deg, #6D70FF, #9C66F4)" if is_put else "linear-gradient(135deg, #16CFC8, #4778FF)"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  }}

  body {{
    width: 1600px;
    height: 900px;
    background: #EEF5FF;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }}

  .canvas-card {{
    width: 1504px;
    height: 804px;
    border-radius: 36px;
    padding: 40px 48px;
    position: relative;
    background:
      radial-gradient(circle at 12% 10%, rgba(111,232,255,.32), transparent 27%),
      radial-gradient(circle at 88% 8%, rgba(185,145,255,.30), transparent 32%),
      radial-gradient(circle at 68% 90%, rgba(159,224,255,.22), transparent 31%),
      linear-gradient(135deg, #F9FCFF 0%, #EEF5FF 48%, #F5F0FF 100%);
    border: 1px solid rgba(255,255,255,.90);
    box-shadow:
      0 30px 80px rgba(35,55,95,.16),
      inset 0 1px 0 rgba(255,255,255,.95);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }}

  /* GLASS PANEL STYLE */
  .glass-panel {{
    background: linear-gradient(135deg, rgba(255,255,255,.62), rgba(255,255,255,.28));
    backdrop-filter: blur(26px) saturate(135%);
    -webkit-backdrop-filter: blur(26px) saturate(135%);
    border: 1px solid rgba(255,255,255,.74);
    box-shadow:
      0 10px 30px rgba(49,72,115,.08),
      inset 0 1px 0 rgba(255,255,255,.85);
    border-radius: 24px;
    position: relative;
    overflow: hidden;
  }}

  .glass-panel::after {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: linear-gradient(120deg, rgba(255,255,255,.32), transparent 25%, transparent 70%, rgba(133,114,255,.10));
    pointer-events: none;
  }}

  /* TOP SECTION: 12-COLUMN LAYOUT */
  .top-section {{
    display: grid;
    grid-template-columns: repeat(12, 1fr);
    gap: 32px;
    height: 380px;
  }}

  .hero-left {{
    grid-column: span 6;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }}

  /* OWLS HEADER */
  .owls-header {{
    display: flex;
    align-items: center;
    gap: 16px;
  }}

  .owls-logo {{
    width: 54px;
    height: 54px;
    border-radius: 16px;
    background: linear-gradient(135deg, #7865F8, #4778FF);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #FFFFFF;
    font-size: 26px;
    box-shadow: 0 8px 20px rgba(120,101,248,.25);
  }}

  .owls-title-box {{
    display: flex;
    flex-direction: column;
  }}

  .owls-title {{
    font-size: 34px;
    font-weight: 700;
    color: #102345;
    line-height: 1;
  }}

  .owls-subtitle {{
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 4px;
    color: #73839B;
    margin-top: 6px;
  }}

  /* HERO MAIN */
  .hero-main {{
    margin-top: 24px;
  }}

  .ticker-symbol {{
    font-size: 100px;
    font-weight: 700;
    letter-spacing: -5px;
    color: #102345;
    line-height: 0.95;
  }}

  .trade-row {{
    display: flex;
    align-items: center;
    gap: 16px;
    margin-top: 12px;
  }}

  .trade-text {{
    font-size: 38px;
    font-weight: 700;
    color: #102345;
  }}

  .type-badge {{
    height: 36px;
    padding: 0 18px;
    border-radius: 18px;
    background: {badge_bg};
    color: #FFFFFF;
    font-size: 14px;
    font-weight: 700;
    display: inline-flex;
    align-items: center;
    letter-spacing: 1px;
  }}

  .expiration-text {{
    font-size: 18px;
    color: #60718E;
    margin-top: 12px;
    font-weight: 500;
  }}

  /* SCORE PANEL & CONFLUENCE BOX */
  .score-panel {{
    grid-column: span 6;
    padding: 28px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    position: relative;
  }}

  .decorative-curve {{
    position: absolute;
    top: 40px; right: 20px;
    width: 180px; height: 90px;
    opacity: 0.30;
    pointer-events: none;
  }}

  .score-header {{
    font-size: 13px;
    font-weight: 600;
    color: #73839B;
    letter-spacing: 1.5px;
  }}

  .score-display {{
    display: flex;
    align-items: baseline;
    margin-top: 4px;
  }}

  .score-val {{
    font-size: 88px;
    font-weight: 650;
    letter-spacing: -4px;
    color: #102345;
    line-height: 0.9;
  }}

  .score-den {{
    font-size: 26px;
    color: #60718E;
    margin-left: 8px;
    font-weight: 500;
  }}

  /* AGENT CONFLUENCE REASONING BOX */
  .confluence-box {{
    background: rgba(255,255,255,.45);
    border: 1px solid rgba(255,255,255,.75);
    border-radius: 16px;
    padding: 14px 18px;
    margin-top: 12px;
    z-index: 2;
  }}

  .confluence-title {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.5px;
    color: #4778FF;
    margin-bottom: 6px;
  }}

  .confluence-text {{
    font-size: 13px;
    font-weight: 500;
    color: #102345;
    line-height: 1.4;
  }}

  .checks-row {{
    display: flex;
    gap: 12px;
    margin-top: 8px;
    font-size: 11px;
    font-weight: 600;
    color: #60718E;
  }}

  .check-item {{
    display: flex;
    align-items: center;
    gap: 4px;
    background: rgba(255,255,255,.60);
    padding: 4px 8px;
    border-radius: 8px;
    border: 1px solid rgba(255,255,255,.80);
  }}

  .badges-container {{
    display: flex;
    gap: 12px;
    margin-top: 12px;
    z-index: 2;
  }}

  .badge-row {{
    flex: 1;
    background: rgba(255,255,255,.35);
    border: 1px solid rgba(255,255,255,.65);
    border-radius: 12px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    font-size: 13px;
    font-weight: 600;
    color: #102345;
  }}

  .badge-icon-cyan {{ color: #16CFC8; }}
  .badge-icon-blue {{ color: #4778FF; }}

  /* PRIMARY METRICS PANEL */
  .primary-metrics {{
    height: 140px;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    align-items: center;
    padding: 0 48px;
  }}

  .metric-col {{
    display: flex;
    align-items: center;
    gap: 20px;
  }}

  .metric-icon-circle {{
    width: 54px;
    height: 54px;
    border-radius: 18px;
    background: rgba(255,255,255,.50);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 22px;
    border: 1px solid rgba(255,255,255,.80);
  }}

  .metric-content {{
    display: flex;
    flex-direction: column;
  }}

  .metric-label {{
    font-size: 13px;
    font-weight: 600;
    color: #73839B;
    letter-spacing: 1px;
  }}

  .metric-value {{
    font-size: 28px;
    font-weight: 650;
    color: #102345;
    margin-top: 4px;
  }}

  .col-divider {{
    width: 1px;
    height: 70px;
    background: rgba(16,35,69,.10);
    justify-self: center;
  }}

  /* BOTTOM METRICS PANEL (3 EQUAL COLUMNS) */
  .bottom-metrics {{
    height: 120px;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    align-items: center;
    padding: 0 48px;
  }}

  .bottom-col {{
    display: flex;
    flex-direction: column;
    justify-content: center;
  }}

  .bottom-label {{
    font-size: 13px;
    font-weight: 600;
    color: #73839B;
    letter-spacing: 1px;
  }}

  .bottom-value {{
    font-size: 24px;
    font-weight: 650;
    color: #102345;
    margin-top: 4px;
  }}

  .value-negative {{ color: #F04D6B; }}
  .value-positive {{ color: #00A984; }}

</style>
</head>
<body>

<div class="canvas-card">

  <!-- TOP SECTION -->
  <div class="top-section">
    <!-- LEFT HERO -->
    <div class="hero-left">
      <!-- OWLS HEADER -->
      <div class="owls-header">
        <div class="owls-logo">🦉</div>
        <div class="owls-title-box">
          <div class="owls-title">OWLs</div>
          <div class="owls-subtitle">NOTABLE FLOW</div>
        </div>
      </div>

      <!-- MAIN HERO -->
      <div class="hero-main">
        <div class="ticker-symbol">${ticker.upper()}</div>
        <div class="trade-row">
          <div class="trade-text">{strike} {type_.upper()}</div>
          <div class="type-badge">{type_.upper()} FLOW</div>
        </div>
        <div class="expiration-text">Expiration {expiration}</div>
      </div>
    </div>

    <!-- SCORE PANEL & AGENT REASONING -->
    <div class="glass-panel score-panel">
      <!-- DECORATIVE CURVE -->
      <svg class="decorative-curve" viewBox="0 0 220 110" fill="none">
        <path d="M10 80 Q 60 20, 110 60 T 210 10" stroke="url(#curveGrad)" stroke-width="4" stroke-linecap="round"/>
        <defs>
          <linearGradient id="curveGrad" x1="0" y1="0" x2="220" y2="0" gradientUnits="userSpaceOnUse">
            <stop stop-color="#4778FF"/>
            <stop offset="1" stop-color="#7865F8"/>
          </linearGradient>
        </defs>
      </svg>

      <div>
        <div class="score-header">{score_label.upper()}</div>
        <div class="score-display">
          <div class="score-val">{score:.1f}</div>
          <div class="score-den">/10</div>
        </div>
      </div>

      <!-- AGENT CONFLUENCE REASONING BOX -->
      <div class="confluence-box">
        <div class="confluence-title">🤖 AGENT CONFLUENCE ANALYSIS</div>
        <div class="confluence-text">{reasoning}</div>
        <div class="checks-row">
          <div class="check-item">📈 {technical_check}</div>
          <div class="check-item">💬 {sentiment_check}</div>
          <div class="check-item">🏛️ {macro_check}</div>
        </div>
      </div>

      <div class="badges-container">
        <div class="badge-row">
          <span class="badge-icon-cyan">◇</span> {quality}
        </div>
        <div class="badge-row">
          <span class="badge-icon-blue">★</span> {flow}
        </div>
      </div>
    </div>
  </div>

  <!-- PRIMARY METRICS -->
  <div class="glass-panel primary-metrics">
    <div class="metric-col">
      <div class="metric-icon-circle">💲</div>
      <div class="metric-content">
        <div class="metric-label">PREMIUM</div>
        <div class="metric-value">{premium}</div>
      </div>
    </div>

    <div class="col-divider"></div>

    <div class="metric-col">
      <div class="metric-icon-circle">🎯</div>
      <div class="metric-content">
        <div class="metric-label">ENTRY</div>
        <div class="metric-value">{entry}</div>
      </div>
    </div>

    <div class="col-divider"></div>

    <div class="metric-col">
      <div class="metric-icon-circle">👥</div>
      <div class="metric-content">
        <div class="metric-label">SIZE</div>
        <div class="metric-value">{size}</div>
      </div>
    </div>
  </div>

  <!-- BOTTOM METRICS (3 EQUAL COLUMNS) -->
  <div class="glass-panel bottom-metrics">
    <div class="bottom-col">
      <div class="bottom-label">ENTRY</div>
      <div class="bottom-value">{entry}</div>
    </div>

    <div class="bottom-col">
      <div class="bottom-label">STOCK</div>
      <div class="bottom-value">{stock}</div>
    </div>

    <div class="bottom-col">
      <div class="bottom-label">STOCK MOVE</div>
      <div class="bottom-value {'value-negative' if '-' in stock_move else 'value-positive'}">{stock_move}</div>
    </div>
  </div>

</div>

</body>
</html>"""
    return html_content


def render_owls_card_chromium(
    ticker: str = "NVDA",
    strike: str = "$220",
    type_: str = "PUT",
    expiration: str = "2026-07-31",
    score: float = 8.7,
    score_label: str = "INSTITUTIONAL CONVICTION",
    reasoning: str = "Heavy $287K Put sweep supported by 78% Ask-side urgency, price holding above 200-SMA, and favorable macro VIX regime.",
    technical_check: str = "Price > 200-SMA",
    sentiment_check: str = "78% Ask Buy Vol",
    macro_check: str = "VIX 14.2 Risk-On",
    premium: str = "$287,529",
    entry: str = "$10.65",
    size: str = "270",
    quality: str = "High Quality",
    flow: str = "Institutional Flow",
    stock: str = "$205.88",
    stock_move: str = "-2.08%",
    output_path: str = "/tmp/owls_option4_exact_sample.png"
) -> str:
    """Render HTML/CSS via Playwright Headless Chromium to 1600x900 PNG."""

    html_code = generate_owls_card_html(
        ticker=ticker, strike=strike, type_=type_, expiration=expiration,
        score=score, score_label=score_label, reasoning=reasoning,
        technical_check=technical_check, sentiment_check=sentiment_check, macro_check=macro_check,
        premium=premium, entry=entry, size=size, quality=quality, flow=flow, stock=stock, stock_move=stock_move
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 900}, device_scale_factor=2)
        page.set_content(html_code)
        page.wait_for_timeout(300)
        page.screenshot(path=output_path, full_page=True)
        browser.close()

    return output_path


def send_to_discord(img_path: str, ticker: str, payload_data: dict, webhook_url: str = None) -> bool:
    """Post OWLs Card Image + Discord Rich Embed to Discord Webhook."""
    if not webhook_url:
        webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "")

    if not webhook_url:
        print(f"ℹ️ DISCORD_WEBHOOK_URL not set in env; saved card locally at {img_path}")
        return False

    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    
    embed_payload = {
        "embeds": [{
            "title": f"OWLs Flow Tracker - {ticker.upper()}",
            "color": 57637,
            "fields": [
                {"name": "Institutional Conviction", "value": f"**{payload_data.get('score', 8.7)}/10**", "inline": False},
                {"name": "Agent Confluence Analysis", "value": f"`{payload_data.get('reasoning', 'High conviction institutional flow sweep')}`", "inline": False}
            ],
            "image": {"url": "attachment://owls_flow_card.png"},
            "footer": {"text": "Powered by Hermes Agent • OWLs Options Flow Intelligence"},
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }]
    }

    body = []
    # Add payload_json part
    body.append(f"--{boundary}".encode("utf-8"))
    body.append(b'Content-Disposition: form-data; name="payload_json"')
    body.append(b"Content-Type: application/json\r\n")
    body.append(json.dumps(embed_payload).encode("utf-8"))

    # Add file part
    if os.path.exists(img_path):
        body.append(f"--{boundary}".encode("utf-8"))
        body.append(b'Content-Disposition: form-data; name="file"; filename="owls_flow_card.png"')
        body.append(b"Content-Type: image/png\r\n")
        with open(img_path, "rb") as f:
            body.append(f.read())

    body.append(f"--{boundary}--\r\n".encode("utf-8"))
    data = b"\r\n".join(body)

    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        }
    )

    try:
        with urllib.request.urlopen(req) as resp:
            print(f"✅ Posted OWLs Flow Card for ${ticker} to Discord successfully!")
            return True
    except Exception as e:
        print(f"Discord dispatch note: {e}")
        return False


def main():
    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else "NVDA"
    print(f"🎨 Rendering OWLs Option 4 Card for ${ticker}...")
    
    out_file = render_owls_card_chromium(
        ticker=ticker,
        strike="$220",
        type_="PUT",
        expiration="2026-07-31",
        score=8.7,
        score_label="INSTITUTIONAL CONVICTION",
        reasoning=f"Heavy Put sweep on ${ticker} supported by 78% Ask-side urgency, price holding above 200-SMA, and favorable macro VIX regime.",
        technical_check="Price > 200-SMA",
        sentiment_check="78% Ask Buy Vol",
        macro_check="VIX 14.2 Risk-On",
        premium="$287,529",
        entry="$10.65",
        size="270",
        quality="High Quality",
        flow="Institutional Flow",
        stock="$205.88",
        stock_move="-2.08%",
        output_path=f"/tmp/owls_card_{ticker}.png"
    )
    print(f"✅ Card rendered cleanly: {out_file}")
    send_to_discord(out_file, ticker, {"score": 8.7, "reasoning": "Heavy Put sweep with Ask-side accumulation"})


if __name__ == "__main__":
    main()
