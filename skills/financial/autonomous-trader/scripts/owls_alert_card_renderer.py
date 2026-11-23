#!/usr/bin/env python3
"""
OWLs Flagship Actionable Trade Alert Card Renderer.

HTML/CSS + Playwright Chromium Card Renderer (Retina 2x Glassmorphism).
Renders the custom OWLs branded visual trade card matching the user's flagship design.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path.home() / ".hermes" / "alert_cards"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_owls_alert_html(
    ticker: str = "BNTX",
    strike: str = "$115",
    type_: str = "CALL",
    expiration: str = "09/18/2026",
    dte: int = 27,
    action: str = "OPEN",
    score: float = 8.5,
    score_label: str = "INSTITUTIONAL CONVICTION",
    score_badge: str = "STRONG",
    reasoning: str = "High-conviction $120K Call sweep with 3.50x Size/OI ratio breaking out above the $100 King Node into positive GEX acceleration.",
    technical_check: str = "Breakout above $100 King Node",
    sentiment_check: str = "Size/OI 3.50x Ask Sweep",
    macro_check: str = "Positive GEX Runway",
    entry: str = "$1.20",
    spot_price: str = "$98.50",
    tp1: str = "$1.55",
    tp1_pct_str: str = "+25%",
    tp2: str = "$2.10",
    tp2_pct_str: str = "+75%",
    sl: str = "$0.84",
    sl_pct_str: str = "-30%",
    max_loss_str: str = "$120/con (100%)",
    premium: str = "$120,000",
    tier_name: str = "Asymmetric Runner",
    micro_sizing: str = "1 Contract (~$120 | Planned Risk: $36)",
    grow_sizing: str = "1 – 2 Contracts (Trim 1 at TP1 to De-Risk 65%)",
    std_sizing: str = "2 – 5 Contracts (Trim 60% at TP1, Trail 40%)"
) -> str:
    """Generates the flagship OWLs glassmorphism HTML/CSS template with dynamic TP & true risk math."""
    is_call = "CALL" in type_.upper() or "C" == type_.upper()
    badge_bg = "linear-gradient(135deg, #16CFC8, #4778FF)" if is_call else "linear-gradient(135deg, #6D70FF, #9C66F4)"
    action_bg = "linear-gradient(135deg, #00FF66, #00B347)" if action.upper() == "OPEN" else "linear-gradient(135deg, #FF2A55, #D90429)"

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
    height: 940px;
    background: #0f172a;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }}

  .canvas-card {{
    width: 1504px;
    height: 860px;
    border-radius: 36px;
    padding: 36px 44px;
    position: relative;
    background:
      radial-gradient(circle at 12% 10%, rgba(111,232,255,.22), transparent 27%),
      radial-gradient(circle at 88% 8%, rgba(185,145,255,.20), transparent 32%),
      radial-gradient(circle at 68% 90%, rgba(0,255,102,.12), transparent 31%),
      linear-gradient(135deg, #1e293b 0%, #0f172a 48%, #1e1b4b 100%);
    border: 1px solid rgba(255,255,255,.15);
    box-shadow:
      0 30px 80px rgba(0,0,0,.60),
      inset 0 1px 0 rgba(255,255,255,.20);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }}

  .glass-panel {{
    background: linear-gradient(135deg, rgba(255,255,255,.08), rgba(255,255,255,.03));
    backdrop-filter: blur(26px) saturate(135%);
    -webkit-backdrop-filter: blur(26px) saturate(135%);
    border: 1px solid rgba(255,255,255,.12);
    box-shadow:
      0 10px 30px rgba(0,0,0,.25),
      inset 0 1px 0 rgba(255,255,255,.15);
    border-radius: 24px;
    position: relative;
    overflow: hidden;
  }}

  /* TOP SECTION */
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

  .owls-header {{
    display: flex;
    align-items: center;
    gap: 16px;
  }}

  .owls-logo {{
    width: 52px;
    height: 52px;
    border-radius: 16px;
    background: linear-gradient(135deg, #7865F8, #4778FF);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #FFFFFF;
    font-size: 26px;
    box-shadow: 0 8px 20px rgba(120,101,248,.35);
  }}

  .owls-title-box {{
    display: flex;
    flex-direction: column;
  }}

  .owls-title {{
    font-size: 36px;
    font-weight: 800;
    color: #FFFFFF;
    line-height: 1;
    display: flex;
    align-items: center;
    gap: 16px;
  }}

  .action-badge {{
    font-size: 22px;
    font-weight: 800;
    padding: 6px 22px;
    border-radius: 14px;
    background: {action_bg};
    color: #000000;
    letter-spacing: 1.5px;
    box-shadow: 0 4px 14px rgba(0,255,102,.40);
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }}

  .owls-subtitle {{
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 4px;
    color: #94a3b8;
    margin-top: 6px;
  }}

  .hero-main {{
    margin-top: 18px;
  }}

  .ticker-symbol {{
    font-size: 92px;
    font-weight: 800;
    letter-spacing: -4px;
    color: #FFFFFF;
    line-height: 0.95;
  }}

  .trade-row {{
    display: flex;
    align-items: center;
    gap: 16px;
    margin-top: 10px;
  }}

  .trade-text {{
    font-size: 36px;
    font-weight: 700;
    color: #38bdf8;
  }}

  .type-badge {{
    height: 34px;
    padding: 0 16px;
    border-radius: 17px;
    background: {badge_bg};
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 700;
    display: inline-flex;
    align-items: center;
    letter-spacing: 1px;
  }}

  .expiration-text {{
    font-size: 18px;
    color: #94a3b8;
    margin-top: 10px;
    font-weight: 500;
  }}

  /* SCORE PANEL */
  .score-panel {{
    grid-column: span 6;
    padding: 24px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }}

  .score-header {{
    font-size: 12px;
    font-weight: 600;
    color: #94a3b8;
    letter-spacing: 1.5px;
    display: flex;
    justify-content: space-between;
  }}

  .score-display {{
    display: flex;
    align-items: baseline;
    margin-top: 2px;
  }}

  .score-val {{
    font-size: 78px;
    font-weight: 800;
    letter-spacing: -3px;
    color: #00FF66;
    line-height: 0.9;
  }}

  .score-den {{
    font-size: 24px;
    color: #64748b;
    margin-left: 8px;
    font-weight: 500;
  }}

  .badge-tag {{
    font-size: 13px;
    font-weight: 800;
    padding: 4px 12px;
    border-radius: 8px;
    background: rgba(0,255,102,.15);
    color: #00FF66;
    border: 1px solid rgba(0,255,102,.3);
  }}

  .confluence-box {{
    background: rgba(0,0,0,.35);
    border: 1px solid rgba(255,255,255,.10);
    border-radius: 16px;
    padding: 12px 16px;
    margin-top: 8px;
  }}

  .confluence-title {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.5px;
    color: #38bdf8;
    margin-bottom: 4px;
  }}

  .confluence-text {{
    font-size: 13px;
    font-weight: 500;
    color: #f1f5f9;
    line-height: 1.35;
  }}

  .checks-row {{
    display: flex;
    gap: 8px;
    margin-top: 8px;
    font-size: 11px;
    font-weight: 600;
    color: #cbd5e1;
  }}

  .check-item {{
    display: flex;
    align-items: center;
    gap: 4px;
    background: rgba(255,255,255,.06);
    padding: 4px 8px;
    border-radius: 6px;
    border: 1px solid rgba(255,255,255,.10);
  }}

  /* TARGETS PANEL (4 EQUAL COLUMNS: ENTRY -> TP1 -> TP2 -> SL) */
  .targets-panel {{
    height: 125px;
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    align-items: center;
    padding: 0 36px;
    gap: 20px;
  }}

  .target-box {{
    display: flex;
    flex-direction: column;
  }}

  .target-lbl {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
  }}

  .target-val {{
    font-size: 26px;
    font-weight: 800;
    margin-top: 4px;
    color: #FFFFFF;
  }}

  .target-sub {{
    font-size: 11px;
    font-weight: 500;
    color: #94a3b8;
    margin-top: 2px;
  }}

  .c-entry {{ color: #38bdf8; }}
  .c-tp1 {{ color: #2dd4bf; }}
  .c-tp2 {{ color: #a78bfa; }}
  .c-sl {{ color: #fb7185; }}

  /* SIZING PANEL */
  .sizing-panel {{
    height: 130px;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    align-items: center;
    padding: 0 36px;
    background: rgba(15,23,42,.6);
  }}

  .sizing-col {{
    display: flex;
    flex-direction: column;
  }}

  .sizing-tier {{
    font-size: 12px;
    font-weight: 700;
    color: #facc15;
    letter-spacing: 1px;
  }}

  .sizing-val {{
    font-size: 16px;
    font-weight: 600;
    color: #FFFFFF;
    margin-top: 4px;
  }}

  .sizing-desc {{
    font-size: 12px;
    color: #94a3b8;
    margin-top: 2px;
  }}

</style>
</head>
<body>

<div class="canvas-card">

  <!-- TOP SECTION -->
  <div class="top-section">
    <div class="hero-left">
      <div class="owls-header">
        <div class="owls-logo">🦉</div>
        <div class="owls-title-box">
          <div class="owls-title">OWLs <span class="action-badge">{action.upper()}</span></div>
          <div class="owls-subtitle">ACTIONABLE TRADE ALERT</div>
        </div>
      </div>

      <div class="hero-main">
        <div class="ticker-symbol">{ticker.upper()}</div>
        <div class="trade-row">
          <div class="trade-text">{strike} {type_.upper()}</div>
          <div class="type-badge">ENTRY {entry}</div>
        </div>
        <div class="expiration-text">Exp: {expiration} ({dte} DTE) • Spot: {spot_price}</div>
      </div>
    </div>

    <!-- SCORE & CONFLUENCE -->
    <div class="glass-panel score-panel">
      <div>
        <div class="score-header">
          <span>{score_label.upper()}</span>
          <span class="badge-tag">{score_badge}</span>
        </div>
        <div class="score-display">
          <div class="score-val">{score:.1f}</div>
          <div class="score-den">/10</div>
        </div>
      </div>

      <div class="confluence-box">
        <div class="confluence-title">🤖 AGENT CONFLUENCE & THESIS</div>
        <div class="confluence-text">{reasoning}</div>
        <div class="checks-row">
          <div class="check-item">📈 {technical_check}</div>
          <div class="check-item">💬 {sentiment_check}</div>
          <div class="check-item">🏛️ {macro_check}</div>
        </div>
      </div>
    </div>
  </div>

  <!-- TARGETS PANEL (4-COLUMN SEQUENCE) -->
  <div class="glass-panel targets-panel">
    <div class="target-box">
      <div class="target-lbl c-entry">🎯 ENTRY TARGET</div>
      <div class="target-val c-entry">{entry}</div>
      <div class="target-sub">Recommended Buy Level</div>
    </div>
    <div class="target-box">
      <div class="target-lbl c-tp1">🎯 TAKE PROFIT 1 ({tp1_pct_str})</div>
      <div class="target-val c-tp1">{tp1}</div>
      <div class="target-sub">De-Risk Capital & Move SL</div>
    </div>
    <div class="target-box">
      <div class="target-lbl c-tp2">🚀 TAKE PROFIT 2 ({tp2_pct_str})</div>
      <div class="target-val c-tp2">{tp2}</div>
      <div class="target-sub">Primary Magnet Node Target</div>
    </div>
    <div class="target-box">
      <div class="target-lbl c-sl">🛑 PLANNED STOP ({sl_pct_str})</div>
      <div class="target-val c-sl">{sl}</div>
      <div class="target-sub">Max Theoretical: {max_loss_str}</div>
    </div>
  </div>

  <!-- SIZING PANEL -->
  <div class="glass-panel sizing-panel">
    <div class="sizing-col">
      <div class="sizing-tier">🛡️ MICRO (< $1,000)</div>
      <div class="sizing-val">{micro_sizing}</div>
      <div class="sizing-desc">Strict contract risk discipline</div>
    </div>
    <div class="sizing-col">
      <div class="sizing-tier">📈 GROWING ($1K – $5K)</div>
      <div class="sizing-val">{grow_sizing}</div>
      <div class="sizing-desc">Scale at TP1 to remove core risk</div>
    </div>
    <div class="sizing-col">
      <div class="sizing-tier">💼 STANDARD ($5K+)</div>
      <div class="sizing-val">{std_sizing}</div>
      <div class="sizing-desc">Scale at TP1/TP2, trail runners</div>
    </div>
  </div>

</div>

</body>
</html>"""
    return html_content


def render_flagship_owls_alert_card(
    ticker: str = "BNTX",
    strike: str = "$115",
    type_: str = "CALL",
    expiration: str = "09/18/2026",
    dte: int = 27,
    action: str = "OPEN",
    score: float = 8.5,
    score_badge: str = "STRONG",
    reasoning: str = "High-conviction $120K Call sweep breaking out above the $100 King Node into positive GEX acceleration.",
    technical_check: str = "Breakout above $100 King Node",
    sentiment_check: str = "Size/OI 3.50x Ask Sweep",
    macro_check: str = "Positive GEX Runway",
    entry: str = "$1.20",
    spot_price: str = "$98.50",
    tp1: str = "$1.55",
    tp1_pct: float = 25.0,
    tp2: str = "$2.10",
    tp2_pct: float = 75.0,
    sl: str = "$0.84",
    sl_pct: float = 30.0,
    premium: str = "$120,000",
    tier_name: str = "Asymmetric Runner",
    output_path: str = None
) -> str:
    """Renders the flagship HTML card using Playwright Chromium with 2x Retina scaling."""
    if not output_path:
        output_path = str(OUTPUT_DIR / f"owls_flagship_{ticker}_{action}_{int(float(entry.replace('$',''))*100)}.png")

    con_cost = int(float(entry.replace("$", "")) * 100)
    stop_risk = int(con_cost * (sl_pct / 100.0))
    max_cap_loss = con_cost
    
    if stop_risk > 50 or con_cost > 200:
        micro_sizing = f"⚠️ PASS (Costs ${con_cost:,} > $200 limit)"
    else:
        micro_sizing = f"1 Contract (~${con_cost} | Planned SL: ${stop_risk})"

    if stop_risk > 250 or con_cost > 1000:
        grow_sizing = "⚠️ PASS (Exceeds 5% risk budget)"
    else:
        grow_sizing = f"1 – 2 Contracts (Trim 1 at TP1 +{tp1_pct:.0f}% to De-Risk 65%)"

    std_sizing = f"2 – 5 Contracts (Trim 60% at TP1, Trail 40%)"

    html_code = generate_owls_alert_html(
        ticker=ticker, strike=strike, type_=type_, expiration=expiration, dte=dte,
        action=action, score=score, score_label="INSTITUTIONAL CONVICTION", score_badge=score_badge,
        reasoning=reasoning, technical_check=technical_check, sentiment_check=sentiment_check, macro_check=macro_check,
        entry=entry, spot_price=spot_price,
        tp1=tp1, tp1_pct_str=f"+{tp1_pct:.0f}%",
        tp2=tp2, tp2_pct_str=f"+{tp2_pct:.0f}%",
        sl=sl, sl_pct_str=f"-{sl_pct:.0f}%",
        max_loss_str=f"${max_cap_loss:.0f}/con (100%)",
        premium=premium, tier_name=tier_name,
        micro_sizing=micro_sizing, grow_sizing=grow_sizing, std_sizing=std_sizing
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 940}, device_scale_factor=2)
        page.set_content(html_code)
        page.wait_for_timeout(300)
        page.screenshot(path=output_path, full_page=True)
        browser.close()

    print(f"[+] Flagship OWLs Alert Card rendered: {output_path}")
    return output_path


if __name__ == "__main__":
    card = render_flagship_owls_alert_card()
    print("Rendered:", card)
