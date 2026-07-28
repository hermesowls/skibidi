#!/usr/bin/env python3
import os, sys, json, requests

# Load credentials
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.expanduser("~/.hermes/.env"))
except ImportError:
    pass

UW_API_KEY = os.getenv("UNUSUAL_WHALES_API_KEY", "").strip()

def fetch_top_10_unusual_flow_tickers():
    """
    Dynamically fetches the top 10 tickers by institutional option flow premium
    from Unusual Whales API. If API key is missing or invalid, logs a clear warning.
    """
    if UW_API_KEY:
        try:
            url = "https://api.unusualwhales.com/api/option-trades/flow"
            headers = {"Authorization": f"Bearer {UW_API_KEY}", "Accept": "application/json"}
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                tickers = []
                flow_list = data.get("data", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                for item in flow_list:
                    t = item.get("ticker") or item.get("symbol")
                    if t and t not in tickers:
                        tickers.append(t.upper())
                    if len(tickers) == 10:
                        break
                if tickers:
                    return tickers
            else:
                print(f"⚠️ Unusual Whales API HTTP {res.status_code}. Key may be compromised, invalid, or expired.", file=sys.stderr)
        except Exception as e:
            print(f"⚠️ Unusual Whales API Error: {e}", file=sys.stderr)
    else:
        print("⚠️ UNUSUAL_WHALES_API_KEY missing in ~/.hermes/.env — using fallback tickers.", file=sys.stderr)

    # Fallback tickers used ONLY when API key is missing or invalid
    return ["NVDA", "TSLA", "SPY", "AMD", "MSFT", "SMCI", "AAPL", "AMZN", "QQQ", "META"]

if __name__ == "__main__":
    top_tickers = fetch_top_10_unusual_flow_tickers()
    print(json.dumps(top_tickers))
