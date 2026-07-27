---
name: skylit-ai
description: Automate navigation, GEX (0DTE/Intraday) vs VEX (1-Week/Swing) heatmap analysis, high school level market explanations, trade conviction scoring, cropped chart screenshots, and formal Kian-style card formatting for Telegram and Discord.
---

# Skylit.ai Financial Automation & Heatmap Analysis Skill

Use this skill whenever requested via **Telegram**, **Discord**, **CLI**, or **TUI** to run a Skylit heatmap workflow for a specific ticker (e.g. "search NVDA for gex", "skylit vex for AAPL", "run skylit workflow for TSLA").

---

## ⚡ Mode Strategy Rulebook

| Request Trigger | Heatmap Mode | Trading Horizon | Primary Focus |
| :--- | :--- | :--- | :--- |
| **GEX / Intraday / 0DTE** | `⚡ GEX` | Intraday (0DTE) | Intraday pin levels, gamma flips, zero-gamma thresholds, price cushions |
| **VEX / Swing / 1 Week** | `⚡ VEX` | 1 Week (7-9 Days) | 7-day magnetic nodes, dealer IV-crush hedging, 1-week target strikes |

---

## ⛔ CRITICAL DISCORD & TELEGRAM FORMATTING LAWS

> [!CAUTION]
> **STRICT FORMATTING & CROPPING ENFORCEMENT**:
> 1. **AUTOMATED SCREENSHOT CROPPING**: Always crop out top navigation bars, maintenance banners, user login IDs (`Hi, user_...`), and the left navigation column. The attached image must frame ONLY the active heatmap grid + control toolbar (`left=215px, top=110px`).
> 2. **BAN ON BULLET POINTS (`•`, `-`, `*`)**: Never use bullet points in trade cards. Use bold label line-by-line formatting: `**Ticker**: NVDA`.
> 3. **BAN ON `<sub>` HTML TAGS**: Never use raw `<sub>` or `<sup>` HTML tags. Use markdown italics for disclaimers (`*Disclaimer: ...*`).
> 4. **MANDATORY IMAGE ATTACHMENT**: Always attach the cropped heatmap screenshot (`/tmp/skylit_[TICKER]_[MODE]_[TIMESTAMP].png`) alongside the text response.
> 5. **HIGH SCHOOL LEVEL EXPLANATION**: Always explain GEX (cushion/pin) or VEX (volatility magnet/trampoline) in intuitive, high-school-level terms.
> 6. **KIAN PROCESS CARD FORMAT**: Follow the formal Kian-style card template below for all Discord and Telegram responses.

---

## 📋 Kian-Style Formal Card Template (Discord & Telegram)

```markdown
✨ **SKYLIT.AI [MODE] HEATMAP ANALYSIS — KIAN PROCESS**

**Ticker**: [TICKER]
**Underlying Price**: $[PRICE]
**Heatmap Mode**: ⚡ [GEX / VEX] ([INTRADAY_0DTE / SWING_1WEEK])
**Time Horizon**: [INTRADAY / 7-9 DAYS]
**Screenshot Artifact**: [CROPPED_IMAGE_PATH]

### 🏫 High School Level Heatmap Breakdown
[2-3 paragraph plain-english explanation of what dealers are doing, where the magnetic nodes are, and how volatility changes will move price over the requested timeframe.]

### 🎯 Trade Conviction & Levels
**Conviction Score**: 🟢 [High Bullish / Moderate Bearish / Neutral Pin]
**Primary Price Target**: $[TARGET_STRIKE]
**Key Support Floor**: $[SUPPORT_STRIKE]
**Invalidation / Stop Loss**: Below $[STOP_PRICE]

---
*Disclaimer: Financial heatmap analysis is for educational and informational purposes only. Manage risk appropriately.*
```

---

## 🛠️ Execution Engine (`skills/financial/skylit-ai/scripts/skylit_runner.py`)

Run the automation runner for any ticker:

```bash
# For Intraday GEX (0DTE)
python3 skills/financial/skylit-ai/scripts/skylit_runner.py --ticker NVDA --mode GEX

# For 1-Week Swing VEX
python3 skills/financial/skylit-ai/scripts/skylit_runner.py --ticker NVDA --mode VEX
```
