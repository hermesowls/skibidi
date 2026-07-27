---
name: paper-trader
description: Stock & Options paper trading automation via Alpaca Paper API, market intelligence via OpenBB Platform, and time-series forecasting via Kronos.
---

# Paper Trading & OpenBB Market Intelligence Skill

Use this skill whenever requested via **Telegram**, **Discord**, **iMessage**, **CLI**, or **TUI** to run stock/options paper trades, check paper portfolio balance, fetch OpenBB market quotes, or run Kronos model predictions.

---

## ⚡ Key Capabilities

1. **Alpaca Paper Trading**: Place paper stock & option orders, view active positions, and track cash/buying power.
2. **OpenBB Platform**: Fetch equity quotes, option chains, financial statements, and macro indicators.
3. **Kronos Time-Series Forecasting**: Run tokenized candlestick predictive models housed in `~/.hermes/repos/Kronos`.

---

## ⛔ FORMATTING LAWS (TELEGRAM, DISCORD & iMESSAGE)

> [!CAUTION]
> 1. **BAN ON BULLET POINTS (`•`, `-`, `*`)**: Format all output lines with bold label prefixes: `**Portfolio Value**: $100,000.00`.
> 2. **BAN ON `<sub>` HTML TAGS**: Use clean markdown italics for disclaimers.

---

## 🛠️ Execution Commands

```bash
# Check Paper Trading Account Balance & Open Positions
python3 skills/financial/paper-trader/scripts/alpaca_paper.py status

# Fetch OpenBB Stock Quote
python3 skills/financial/paper-trader/scripts/alpaca_paper.py quote --symbol NVDA
```

---

## 🔑 Setup Credentials

Get free paper trading API keys at [Alpaca Markets](https://app.alpaca.markets/signup) and add them to `~/.hermes/.env`:

```env
ALPACA_API_KEY=your_alpaca_paper_api_key
ALPACA_SECRET_KEY=your_alpaca_paper_secret_key
ALPACA_PAPER=true
```
