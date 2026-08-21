---
name: unusual-whales
description: Access Unusual Whales financial API for options flow, dark pool volume, market alerts, insider trading, and unusual options activity using the Kian Process with TradingView Lightweight Charts & 5-minute Whale Contract Flow Drilldown visuals.
---

# Unusual Whales Skill — The Kian Process & Whale Contract Drilldown

Use this skill whenever analyzing options flow, dark pool activity, or stock alerts using the Unusual Whales API or whenever the user asks for options analysis, notable flow, **The Kian Process**, or **Contract Flow Drilldown rendering**.

> [!CRITICAL]
> **STRICT EXECUTION & FORMATTING RULES FOR DISCORD**:
> 1. **BAN ON BULLET POINTS**: DO NOT use bullet characters (`•`, `-`, `*`) anywhere in the top trade region or notes section of the card. Use bold label prefixes line-by-line (e.g. `**Ticker**: NBIS`).
> 2. **BAN ON HTML `<sub>` TAGS**: Discord DOES NOT render HTML `<sub>` tags — they appear as raw text `<sub>`. Format the disclaimer strictly in markdown italics (`*Disclaimer: ...*`).
> 3. **CONSOLIDATED CHART ATTACHMENT MANDATORY**: Every analysis output posted to Discord MUST attach the consolidated chart image `kian_[TICKER]_[STRIKE]_[TYPE].png`. The single interactive HTML link must contain Chart 1 and Chart 2 stacked vertically on the same page. Do not create separate public links for each chart unless explicitly requested.
> 4. **BAN ON LEGACY SCRIPTS**: NEVER reuse or execute cached/legacy python scripts from `/Users/admin/Workspace/agentic-hub/agents/financial/output/scripts/`. Always generate a fresh script using the blueprints below.
> 5. **CHART RENDERING VIA PLAYWRIGHT HTTP**: Ensure the local HTTP server is running (`python3 -m http.server 8000 --directory /tmp &`). Navigate Playwright to `http://localhost:8000/...` (NOT `file://` which blocks CDN script loading). Wait **3000ms** for JS rendering before screenshotting.
6. **INTERACTIVE LINKS MUST BE PUBLIC FOR DISCORD**: Render locally through `http://localhost:8000/...`, then expose `/tmp` with Cloudflare Tunnel (`cloudflared tunnel --url http://localhost:8000`) and replace every `localhost:8000` link in the final card with the current `https://*.trycloudflare.com` base URL. If a Cloudflare tunnel is already running, read its log (for example `/tmp/cf_charts.log`) and reuse the current URL. Do not leave localhost links in Discord-facing output unless Cloudflare fails and the failure is explicitly disclosed.
7. **DISCORD DELIVERY DEFAULT / CLEAN CARD**: When the user asks for Unusual Whales/Kian output and does not specify a destination, deliver/post to Discord Home, not just the originating Telegram chat. For polished Discord cards, avoid Hermes cron delivery framing because cron adds `Cronjob Response...` and stop/manage footer text. Prefer direct Discord/webhook delivery for formal cards; if only cron delivery is available, explicitly disclose that Hermes will add the wrapper/footer.
8. **DYNAMIC API DATA MAPPING**: All numbers, statistics, tickers, strikes, expirations, premiums, volume ratios, sentiment %, and HTML filenames MUST be populated dynamically from live Unusual Whales API responses and yfinance. The numbers/links in the template blueprint are visual examples — NEVER hardcode mock values in execution scripts.
9. **HARDCODE CARD STRUCTURE, NOT DATA**: Keep the Discord output structure as deterministic/hardcoded as possible: fixed section order, fixed labels, fixed formatting, fixed chart/link placement, and fixed disclaimer. Only dynamic API/yfinance values and the final reasoning fields should vary.
10. **LLM REASONING SCOPE**: Use LLM judgment only for critical interpretation fields such as Technical Alignment wording, Conviction Profile nuance, and the final Action Summary. The LLM should synthesize API + chart + Kian signals into beginner-friendly trade setup guidance, not rewrite the whole card.
11. **PATTERN LEARNING LOOP**: As the workflow matures, preserve reusable lessons about what makes trades good/bad as skill updates or compact memory. Capture patterns like ask-side continuation, next-session OI confirmation, contract price holding above intraday average, trend alignment, failed follow-through, and invalidation rules.
12. **DETERMINISTIC DTE + SPOTTED DATE STANDARD**: Always show the whale spotted date separately from DTE. Compute DTE dynamically from the current analysis date/today, not from the whale purchase/spotted date: `(datetime.strptime(expiration_date, "%Y-%m-%d").date() - datetime.now().date()).days`. In Discord cards include `**Whale Spotted Date**`, `**Analysis Date**`, and `**Expiration Date**: YYYY-MM-DD (N DTE from analysis date)`. NEVER guess or hallucinate DTE values or reuse static template numbers.

---

## Notable Flow Mirror Process

When Amar asks for the OWLS/Kian-style `Notable Flow` list, do **not** treat it as a data source or as the same thing as Kian conviction cards. It is a separate generated output process.

Use `/Users/admin/.hermes/scripts/uw_notable_flow_mirror.py` to generate the compact notable-flow list format, e.g. `$TICKER STRIKEC/P M/Dexp $PREMIUM AVG Avg`.

**Purpose**: contract-level notable-flow output similar to Kian's simple list, before full Kian chart/card scoring.

**Default command**:
```bash
/Users/admin/repos/hermes-agent/venv/bin/python /Users/admin/.hermes/scripts/uw_notable_flow_mirror.py --limit 11 --output /tmp/notable_flow_mirror_latest.md
```

**Discord command**:
```bash
/Users/admin/repos/hermes-agent/venv/bin/python /Users/admin/.hermes/scripts/uw_notable_flow_mirror.py --limit 11 --send-discord --output /tmp/notable_flow_mirror_latest.md
```

**Behavior**: aggregates UW contract/trade rows into contract-level notable rows, enriches finalists through `/option-contract/{contract}/historic`, ranks by daily premium/volume, computes DTE from analysis date, and labels novelty as `NEW` or `CARRYOVER` via `~/.hermes/trading_logs/notable_flow_mirror.sqlite`.

**Exit/sell-pressure check**: after running the mirror, use `/Users/admin/.hermes/scripts/uw_notable_flow_exit_check.py` to evaluate whether mirrored whales may have sold or faded. It checks contract intraday/flow/historic endpoints for bid-side dominance, ask-side follow-through, contract price vs avg, and current/previous OI. Same-day bid-side pressure can warn of exit, but true hold/sold confirmation requires next-session OI after market open.

**Exit check command**:
```bash
/Users/admin/repos/hermes-agent/venv/bin/python /Users/admin/.hermes/scripts/uw_notable_flow_exit_check.py
```

**Human-readable Discord rule**: All Discord-facing whale output must use human-readable contract labels first, with raw option symbols only as secondary metadata. Use labels like `Readable Contract: EEM $62 Put expiring Sep 18, 2026 | DTE From Today: 52` and `Raw Contract ID: EEM260918P00062000`. Avoid unexplained abbreviations in primary labels: write `Open Interest` instead of `OI`, `Whale-Day Volume` instead of `Entry Volume`, `Earliest Valid Open Interest Check` instead of `OI Check Window`, and `Position Persistence Score` instead of generic `Conviction` when the score measures holding/persistence rather than trade-entry confidence.

**Separation rule**: Notable Flow Mirror = discovery/output list. Exit Check = sold/fade pressure. Kian Process = conviction card + chart workflow. Whale Monitor = persistence/confirmation tracking. Do not conflate them.

---

## Core Methodology: The Kian Process

Whenever evaluating market flow or scanning tickers, apply **The Kian Process** with progressive filter relaxation:

### Filter Priority (Apply in Order — Relax if No Results)

**Tier 1 (Strict Kian)** — Try these filters first:
- `volume > open_interest` (Vol > OI)
- Premium $\ge$ $50,000
- Contract volume $\ge$ 500
- Trade side: ASK or ABOVE ASK

**Tier 2 (Relaxed Kian)** — If Tier 1 returns 0 results, relax to:
- `volume > open_interest` (Vol > OI) — KEEP this, it's the core signal
- Premium $\ge$ $10,000
- Contract volume $\ge$ 100
- Any trade side (include MID and BID)

**Tier 3 (Top Flow)** — If Tier 2 also returns 0, show the top 3-5 highest-premium trades regardless of filters, with a note: `"No strict Kian candidates today. Showing top flow by premium."`

> **NEVER exit with "No strict Kian candidates found" and show nothing.** Always fall through to the next tier.

---

## Discord Card Template (FOLLOW EXACTLY — NO BULLET POINTS — NO `<sub>` TAGS)

```markdown
🐳 **NBIS — PUT $170.00 2026-08-07**

**Ticker**: NBIS
**Option Type**: PUT
**Trade Side**: ASK-SIDE (BUY CONVICTION)
**Whale Spotted Date**: 2026-07-27
**Analysis Date**: 2026-07-28
**Expiration Date**: 2026-08-07 (10 DTE from analysis date)
**Strike Price**: $170.00
**Contract Price**: $16.10
**Trade Total**: $32,654,020 (20,282 contracts)
**Total Premium at or Greater Than Ask**: $32,654,020
**Volume vs. Open Interest**: 31,171 / 1,564 (Vol > OI: YES)
**Sentiment**: 🔴 BEARISH

### 📈 Notes & Key Details

**Holding Status**: Intraday-only read; true holding requires next-session OI confirmation. Current ask-side premium suggests buyer-side urgency if contracts persist.
**Technical Alignment**: Bearish short-term stack: price 187.77 < 8/21 SMA.
**Conviction Profile**: Strict Kian filter passed; high premium, Vol > OI, ask-side urgency, and API-backed intraday contract flow confirmation.
**Rules / Alert Context**: FloorTradeLargeCap

---

📊 **Charts**

🔗 [Open Interactive NBIS Charts](https://.../kian_NBIS_170_PUT.html)

### 🧭 Action Summary

**Setup Read**: High-conviction bearish flow setup, but not a blind entry.
**Entry Idea**: Wait for price-action confirmation in the trade direction before treating it as actionable.
**Confirmation Needed**: Next-session OI expansion plus contract price holding above its intraday average supports that whales held the position.
**Invalidation / Caution**: Flow weakens if next-session OI does not expand, contract price fades below average, or stock moves against the trade direction.
**Risk Plan**: Short-dated contract with elevated options activity; size smaller, avoid chasing the first spike, and require confirmation.

*Disclaimer: Options flow data & Kian Process metrics are for research purposes only.*
```

---

## Chart 1: Stock Price + SMA Technical Chart

Clean candlestick chart with SMA overlays. **NO volume bars on this chart.**

- **Locked stock chart timeframe**: Use **1-day candles** and lock the visible x-axis to a **1-year range** by default. Do not use intraday candles for the stock SMA chart.
- **Header badges**: Show `1D Candles` and `1Y Range` badges in the stock-chart header so the locked timeframe is obvious.
- **Candlesticks**: Green (#26a69a) up, Red (#ef5350) down.
- **SMA Lines**: 8 (cyan #00bcd4), 21 (gold #ffd54f), 50 (orange #ff9800), 100 (green #4caf50), 200 (magenta #e040fb).
- **SMA legend required**: Show a visible stock-chart legend mapping each SMA timeframe to its color: 8 SMA cyan, 21 SMA gold, 50 SMA orange, 100 SMA green, 200 SMA magenta. Keep line end labels disabled so they do not cover latest data.
- **Background**: #131722, Grid: #1f2434, Text: #d1d4dc.
- **Header bar**: Dark (#1e222d), ticker in blue (#4ba2ff).

---

## Chart 2: Contract Bid/Ask Volume + Contract Price

Chart 2 is the contract intraday flow chart. It replaces the prior dual-pane drilldown. **Chart 3 / put-call net premium chart is removed entirely unless the user explicitly asks to bring it back.**

- **Single combined interactive link**: Put the stock SMA chart and contract chart on the same HTML page, stacked vertically. The final card should include one public Cloudflare link: `🔗 [Open Interactive Kian Charts](https://.../kian_[TICKER]_[STRIKE]_[TYPE].html)`. Keep legacy `tv_*.html` and `drilldown_*.html` compatibility files only if useful, but do not list them as separate links.
- **Naming schema**: Do not show `Chart 1` or `Chart 2` in final chart titles. Use `Stock Simple Moving Average (SMA)` for the stock chart title and `Contract Bid/Ask Volume + Price` for the contract chart title.
- **Stats Row**: `Vol`, `OI`, `Vol/OI`, `Ask Premium`, `Bid Premium`, `Contract Avg`.
- **Volume candles**: Intraday histogram/candles for the selected contract. Teal/green (#26a69a) = ask-side / buys. Red (#ef5350) = bid-side / sells. Bid/sell candles can be negative/below baseline when needed.
- **Left volume y-axis required**: Chart 2 must show the volume scale on the left y-axis so candle size is readable.
- **Right price y-axis required**: Chart 2 must show the contract price scale on the right y-axis.
- **Contract price line**: White line through the middle/right-scale showing the contract price throughout the day.
- **Average line**: Yellow dashed line showing average contract price.
- **Non-intrusive labels**: Disable right-edge series labels/last-value labels for SMA and average/price overlay lines in screenshots. Use legends/header text instead so end-of-year/end-of-day data is not covered.
- **No Chart 3**: Do not render put/call net premium, NCP/NPP, or net sentiment panes by default.
- **Actual API data required for Chart 2**: Do not synthesize intraday candles from aggregate totals. After selecting the Kian contract, fetch and render real Unusual Whales data from:
  - `/api/option-contract/{option_chain}/intraday?date=YYYY-MM-DD` for 1-minute ask/bid volume buckets plus `close` and `avg_price` lines.
  - `/api/option-contract/{option_chain}/flow?date=YYYY-MM-DD&limit=500` for trade tape context and validation.
  - `/api/option-contract/{option_chain}/volume-profile?date=YYYY-MM-DD` for price-level volume context when needed.
  - `/api/option-contract/{option_chain}/historic?limit=30` for prior-day OI/volume context.
  - `/api/stock/{ticker}/option-contracts?expiry=...&option_type=...&vol_greater_oi=true` for chain comparison.
- **Chart 2 mapping**: Use `volume_ask_side` as positive teal ask/buy bars, `volume_bid_side` as negative red bid/sell bars, `close` as the white contract-price line, and `avg_price` as the yellow dashed average line.

---

## Complete Chart Rendering Blueprint (Playwright via HTTP)

```python
import json, subprocess, os
import yfinance as yf
import pandas as pd
from playwright.async_api import async_playwright

CHART_DIR = "/tmp"
HTTP_PORT = 8000

def ensure_http_server():
    """Start local HTTP server if not already running."""
    res = subprocess.run("pgrep -f 'python3 -m http.server 8000'", shell=True, capture_output=True)
    if res.returncode != 0:
        subprocess.Popen(
            ["python3", "-m", "http.server", str(HTTP_PORT), "--directory", CHART_DIR],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        import time; time.sleep(1)

async def render_stock_sma_chart(symbol, period="6mo"):
    """Chart 1: Stock Price + SMA only (NO volume bars)."""
    ensure_http_server()
    df = yf.Ticker(symbol).history(period=period)
    if df.empty:
        return None, None

    df['SMA8']   = df['Close'].rolling(8).mean()
    df['SMA21']  = df['Close'].rolling(21).mean()
    df['SMA50']  = df['Close'].rolling(50).mean()
    df['SMA100'] = df['Close'].rolling(100).mean()
    df['SMA200'] = df['Close'].rolling(200).mean()

    candles = []
    sma_data = {k: [] for k in ['sma8','sma21','sma50','sma100','sma200']}
    sma_cols = {'sma8':'SMA8','sma21':'SMA21','sma50':'SMA50','sma100':'SMA100','sma200':'SMA200'}

    for date, row in df.iterrows():
        t = date.strftime("%Y-%m-%d")
        candles.append({"time":t,"open":round(row['Open'],2),"high":round(row['High'],2),"low":round(row['Low'],2),"close":round(row['Close'],2)})
        for key, col in sma_cols.items():
            if not pd.isna(row[col]):
                sma_data[key].append({"time":t,"value":round(row[col],2)})

    html = f"""<!DOCTYPE html>
<html><head>
<script src="https://unpkg.com/lightweight-charts@4/dist/lightweight-charts.standalone.production.js"></script>
<style>
  body {{ margin:0; background:#131722; font-family:-apple-system,sans-serif; }}
  #hdr {{ padding:12px 20px; font-size:15px; font-weight:700; background:#1e222d; border-bottom:1px solid #2a2e39; color:#d1d4dc; }}
  #hdr span {{ color:#4ba2ff; }}
  #chart {{ width:900px; height:500px; }}
</style>
</head><body>
<div id="hdr"><span>{symbol}</span> — Technical Chart · SMA 8/21/50/100/200</div>
<div id="chart"></div>
<script>
const c=LightweightCharts.createChart(document.getElementById('chart'),{{
  width:900,height:500,
  layout:{{background:{{type:'solid',color:'#131722'}},textColor:'#d1d4dc'}},
  grid:{{vertLines:{{color:'#1f2434'}},horzLines:{{color:'#1f2434'}}}},
  crosshair:{{mode:LightweightCharts.CrosshairMode.Normal}},
  rightPriceScale:{{borderColor:'#2a2e39'}},
  timeScale:{{borderColor:'#2a2e39'}}
}});
const cs=c.addCandlestickSeries({{upColor:'#26a69a',downColor:'#ef5350',wickUpColor:'#26a69a',wickDownColor:'#ef5350'}});
cs.setData({json.dumps(candles)});
const add=(col,name,d)=>{{const s=c.addLineSeries({{color:col,lineWidth:1.5,title:name}});s.setData(d);}};
add('#00bcd4','8 SMA',{json.dumps(sma_data['sma8'])});
add('#ffd54f','21 SMA',{json.dumps(sma_data['sma21'])});
add('#ff9800','50 SMA',{json.dumps(sma_data['sma50'])});
add('#4caf50','100 SMA',{json.dumps(sma_data['sma100'])});
add('#e040fb','200 SMA',{json.dumps(sma_data['sma200'])});
c.timeScale().fitContent();
</script></body></html>"""

    html_path = os.path.join(CHART_DIR, f"tv_{symbol}.html")
    img_path  = os.path.join(CHART_DIR, f"tv_{symbol}.png")
    with open(html_path, "w") as f:
        f.write(html)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width":900,"height":560})
        await page.goto(f"http://localhost:{HTTP_PORT}/tv_{symbol}.html")
        await page.wait_for_timeout(3000)
        await page.screenshot(path=img_path)
        await browser.close()

    return f"http://localhost:{HTTP_PORT}/tv_{symbol}.html", img_path


async def render_contract_drilldown(ticker, strike, option_type, expiry, price, pct_change, flow):
    """Chart 2: Dual-panel Contract Flow Drilldown (Unusual Whales exact UI)."""
    ensure_http_server()

    bid_pct = flow.get('bid_pct', 28)
    ask_pct = flow.get('ask_pct', 72)
    bear_pct = flow.get('bear_pct', 50)
    bull_pct = flow.get('bull_pct', 50)

    html = f"""<!DOCTYPE html>
<html><head>
<script src="https://unpkg.com/lightweight-charts@4/dist/lightweight-charts.standalone.production.js"></script>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#0b0e14; color:#d1d4dc; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; }}
  .top-bar {{ background:#131722; border-bottom:1px solid #2a2e39; padding:10px 16px; display:flex; align-items:center; justify-content:space-between; }}
  .top-bar .contract {{ color:#ef5350; font-weight:700; font-size:14px; }}
  .top-bar .price {{ color:#d1d4dc; font-size:14px; margin-left:8px; }}
  .top-bar .pct {{ color:#ef5350; font-size:13px; margin-left:4px; }}
  .top-bar .tf {{ display:flex; gap:4px; }}
  .top-bar .tf span {{ background:#1e222d; color:#848e9c; padding:4px 10px; border-radius:4px; font-size:11px; }}
  .top-bar .tf span.active {{ background:#2962ff; color:#fff; }}
  .tabs {{ display:flex; background:#131722; border-bottom:1px solid #2a2e39; }}
  .tabs div {{ flex:1; text-align:center; padding:8px; font-size:13px; font-weight:600; color:#848e9c; }}
  .tabs div.active {{ color:#d1d4dc; border-bottom:2px solid #2962ff; }}
  .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:0; height:340px; }}
  .panel {{ background:#131722; border:1px solid #2a2e39; padding:12px 14px; display:flex; flex-direction:column; }}
  .stats {{ font-size:11px; color:#848e9c; line-height:1.6; }}
  .stats b {{ color:#d1d4dc; }}
  .sub-label {{ font-size:10px; color:#555; margin:4px 0 2px; }}
  .ratio-bar {{ height:5px; border-radius:3px; display:flex; overflow:hidden; margin:4px 0; }}
  .ratio-bar .fill {{ height:100%; }}
  .ratio-labels {{ display:flex; justify-content:space-between; font-size:10px; color:#848e9c; }}
  .legend {{ font-size:10px; color:#848e9c; margin:4px 0 6px; display:flex; gap:10px; flex-wrap:wrap; }}
  .legend .dot {{ display:inline-block; width:7px; height:7px; border-radius:50%; margin-right:3px; vertical-align:middle; }}
  .chart-box {{ flex:1; min-height:200px; }}
</style>
</head><body>

<div class="top-bar">
  <div>
    <span class="contract">Contract Drilldown | {ticker} {strike} {option_type} {expiry} · {flow.get('dte','28')} DTE</span>
    <span class="price">| {ticker} ${price}</span>
    <span class="pct">({pct_change})</span>
  </div>
  <div class="tf"><span class="active">1D</span><span>5min ▾</span></div>
</div>

<div class="tabs">
  <div class="active">CONTRACT FLOW</div>
  <div>NET PREMIUM</div>
</div>

<div class="grid">
  <div class="panel">
    <div class="stats">Vol: <b>{flow.get('vol','11,184')}</b> | OI: <b>{flow.get('oi','6,703')}</b> | Avg: <b>${flow.get('avg','3.82')}</b> | Prem: <b>${flow.get('prem','4,269,785')}</b> | OTM: {flow.get('otm','11%')} | Vol/OI: <b>{flow.get('ratio','1.67')}</b> | Multi: {flow.get('multi','25%')}</div>
    <div class="sub-label">Contract Ratio</div>
    <div class="ratio-bar">
      <div class="fill" style="width:{bid_pct}%;background:#ef5350;"></div>
      <div class="fill" style="width:{ask_pct}%;background:#26a69a;"></div>
    </div>
    <div class="ratio-labels"><span>Bid</span><span>Ask {ask_pct}%</span></div>
    <div class="legend">
      <span><span class="dot" style="background:#ef5350;"></span>Bid: {flow.get('bid_count','3,046')}</span>
      <span><span class="dot" style="background:#555;"></span>Mid: {flow.get('mid_count','125')}</span>
      <span><span class="dot" style="background:#26a69a;"></span>Ask: {flow.get('ask_count','7,999')}</span>
    </div>
    <div id="chart-flow" class="chart-box"></div>
  </div>

  <div class="panel">
    <div class="stats">Vol: <b>{flow.get('total_vol','1,036,135')}</b> | Prem: <b>${flow.get('total_prem','361.39M')}</b> | Net: <b>${flow.get('net','19.50K')}</b> | NCP: <b>${flow.get('ncp','878.56K')}</b> | NPP: <b>${flow.get('npp','859.00K')}</b></div>
    <div class="sub-label">Net Sentiment</div>
    <div class="ratio-bar">
      <div class="fill" style="width:{bear_pct}%;background:#ef5350;"></div>
      <div class="fill" style="width:{bull_pct}%;background:#26a69a;"></div>
    </div>
    <div class="ratio-labels"><span>Bearish {bear_pct}%</span><span>Bullish {bull_pct}%</span></div>
    <div class="legend">
      <span><span class="dot" style="background:#26a69a;"></span>Call Bought: ${flow.get('call_bought','92.85M')}</span>
      <span><span class="dot" style="background:#b71c1c;"></span>Call Sold: ${flow.get('call_sold','91.88M')}</span>
      <span><span class="dot" style="background:#ef5350;"></span>Put Bought: ${flow.get('put_bought','45.90M')}</span>
      <span><span class="dot" style="background:#424242;"></span>Put Sold: ${flow.get('put_sold','44.54M')}</span>
    </div>
    <div id="chart-net" class="chart-box"></div>
  </div>
</div>

</body></html>"""

    fname = f"drilldown_{ticker}_{strike}_{option_type}"
    html_path = os.path.join(CHART_DIR, f"{fname}.html")
    img_path  = os.path.join(CHART_DIR, f"drilldown_{ticker}_{strike}_{option_type}.png")
    with open(html_path, "w") as f:
        f.write(html)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width":920,"height":440})
        await page.goto(f"http://localhost:{HTTP_PORT}/{fname}.html")
        await page.wait_for_timeout(3000)
        await page.screenshot(path=img_path)
        await browser.close()

    return f"http://localhost:{HTTP_PORT}/{fname}.html", img_path
```
