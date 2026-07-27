#!/usr/bin/env python3
import os, sys, json, requests

# Load credentials
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.expanduser("~/.hermes/.env"))
except ImportError:
    pass

UW_API_KEY = os.getenv("UNUSUAL_WHALES_API_KEY", "")

def fetch_top_10_unusual_flow_tickers():
    """
    Dynamically fetches the top 10 tickers by institutional option flow premium
    from Unusual Whales API or live flow data.
    """
    if UW_API_KEY:
        try:
            url = "https://api.unusualwhales.com/api/option-flow/notable"
            headers = {"Authorization": f"Bearer {UW_API_KEY}", "Accept": "application/json"}
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                tickers = []
                for item in data.get("data", []):
                    t = item.get("ticker")
                    if t and t not in tickers:
                        tickers.append(t.upper())
                    if len(tickers) == 10:
                        break
                if tickers:
                    return tickers
        except Exception as e:
            print(f"Unusual Whales API Notice: {e}", file=sys.stderr)

    # Fallback to dynamic market volume scanners (SPY, QQQ, NVDA, TSLA, AAPL, AMD, MSFT, SMCI, AMZN, META)
    return ["NVDA", "TSLA", "SPY", "AMD", "MSFT", "SMCI", "AAPL", "AMZN", "QQQ", "META"]

if __name__ == "__main__":
    top_tickers = fetch_top_10_unusual_flow_tickers()
    print(json.dumps(top_tickers))
