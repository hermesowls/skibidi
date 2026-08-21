#!/usr/bin/env python3
import os, sys, argparse

# Load .env credentials if present
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.expanduser("~/.hermes/.env"))
except ImportError:
    pass

API_KEY = os.getenv("ALPACA_API_KEY", "")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
PAPER = os.getenv("ALPACA_PAPER", "true").lower() in ("true", "1", "yes")

def get_alpaca_client():
    if not API_KEY or not SECRET_KEY:
        return None
    try:
        from alpaca.trading.client import TradingClient
        return TradingClient(API_KEY, SECRET_KEY, paper=PAPER)
    except Exception as e:
        print(f"Error initializing Alpaca client: {e}")
        return None

def show_account_status():
    client = get_alpaca_client()
    if not client:
        return """📊 **ALPACA PAPER TRADING ACCOUNT REPORT**

**Status**: ⚠️ Credentials Not Configured
**API Key Needed**: Set `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` in `~/.hermes/.env`.

---
*Visit https://app.alpaca.markets/signup to get free paper trading API keys.*"""

    try:
        acc = client.get_account()
        positions = client.get_all_positions()

        pos_lines = []
        for p in positions:
            pos_lines.append(f"**Symbol**: {p.symbol} | **Qty**: {p.qty} | **Market Value**: ${float(p.market_value):,.2f} | **P/L**: ${float(p.unrealized_pl):,.2f}")

        pos_str = "\n".join(pos_lines) if pos_lines else "No open positions."

        report = f"""📊 **ALPACA PAPER TRADING ACCOUNT REPORT**

**Portfolio Value**: ${float(acc.portfolio_value):,.2f}
**Buying Power**: ${float(acc.buying_power):,.2f}
**Cash Balance**: ${float(acc.cash):,.2f}
**Account Status**: 🟢 Active (Paper Mode)

**Open Positions**:
{pos_str}

---
*Executed via Alpaca Paper Trading API.*"""
        return report
    except Exception as e:
        return f"⚠️ Error fetching Alpaca account: {e}"

def openbb_quote(symbol):
    # Check Finviz Elite first
    try:
        finviz_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../financial-market-data/scripts"))
        if finviz_dir not in sys.path:
            sys.path.insert(0, finviz_dir)
        import finviz_client
        if finviz_client.get_finviz_api_url():
            quotes = finviz_client.fetch_quotes([symbol])
            if quotes:
                q = quotes[0]
                return f"📈 **MARKET QUOTE ({symbol.upper()})**\n\n**Last Price**: ${q['price']}\n**Daily Change**: {q['change_pct']}\n**Market Cap**: {q['market_cap']}\n**P/E Ratio**: {q['pe_ratio']}\n\n*Fetched via Finviz Elite Engine.*"
    except Exception:
        pass

    try:
        from openbb import ob
        res = ob.equity.price.quote(symbol)
        df = res.to_df()
        if not df.empty:
            row = df.iloc[0]
            price = row.get("last_price", row.get("close", "N/A"))
            change = row.get("change_percent", "N/A")
            return f"📈 **OPENBB QUOTE ({symbol.upper()})**\n\n**Last Price**: ${price}\n**Change**: {change}%\n\n*Fetched via OpenBB Platform.*"
    except Exception as e:
        pass
    # Fallback to yfinance if openbb provider requires key
    try:
        import yfinance as yf
        t = yf.Ticker(symbol)
        info = t.fast_info
        price = info.last_price
        prev = info.previous_close
        pct = ((price - prev) / prev) * 100
        return f"📈 **MARKET QUOTE ({symbol.upper()})**\n\n**Last Price**: ${price:,.2f}\n**Daily Change**: {pct:+.2f}%\n**Previous Close**: ${prev:,.2f}\n\n*Fetched via OpenBB / YFinance Engine.*"
    except Exception as ex:
        return f"⚠️ Error fetching quote for {symbol}: {ex}"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["status", "quote", "buy", "sell"], default="status", nargs="?")
    parser.add_argument("--symbol", default="NVDA")
    parser.add_argument("--qty", type=float, default=1)
    args = parser.parse_args()

    if args.action == "status":
        print(show_account_status())
    elif args.action == "quote":
        print(openbb_quote(args.symbol))
    else:
        print(f"Action '{args.action}' on {args.symbol} requested.")
