import urllib.request, json, os

key = os.getenv("UNUSUAL_WHALES_API_KEY", "179ee2b3-3f79-4f10-b5fe-2aa3d82d36ce")
headers = {
    "Authorization": f"Bearer {key}",
    "Accept": "application/json",
    "User-Agent": "HermesAgent/1.0"
}

def fetch_uw_option_price(ticker: str, strike: float, direction: str) -> float:
    url = f"https://api.unusualwhales.com/api/stock/{ticker.upper()}/option-contracts"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            contracts = data.get("data", [])
            opt_type = "C" if direction.lower().startswith("c") or direction.lower() == "long" else "P"
            strike_target = float(strike)

            # 1. Exact match on strike and option type
            for c in contracts:
                sym = c.get("option_symbol") or ""
                if len(sym) > 10:
                    c_type = "C" if "C" in sym[6:12] else "P"
                    # Parse strike from OCC symbol (last 8 digits / 1000.0)
                    try:
                        c_strike = float(sym[-8:]) / 1000.0
                        if abs(c_strike - strike_target) < 0.01 and c_type == opt_type:
                            lp = c.get("last_price")
                            if lp is not None:
                                return float(lp)
                    except Exception:
                        pass
    except Exception as e:
        print(f"Error fetching UW for {ticker}: {e}")
    return None

test_positions = [
    ("RARE", 50.0, "call", 2.00),
    ("RKLB", 100.0, "call", 3.80),
    ("RGTI", 20.0, "call", 2.15),
    ("FCX",  75.0, "call", 3.00),
    ("VNET", 12.0, "call", 0.95),
    ("ORCL", 200.0, "call", 2.84)
]

print("UNUSUAL WHALES OPTION CONTRACT PRICE LOOKUP (STRIKE MATCH):\n")
for ticker, strike, direction, entry in test_positions:
    price = fetch_uw_option_price(ticker, strike, direction)
    if price is not None:
        roi = ((price - entry) / entry) * 100.0
        contract_cost = entry * 100.0
        contract_value = price * 100.0
        print(f"✓ {ticker:<5} {strike}C | Entry Prem: ${entry:.2f} (${contract_cost:.2f}/con) | UW Live Prem: ${price:.2f} (${contract_value:.2f}/con) | ROI: {roi:+.1f}%")
    else:
        print(f"x {ticker:<5} {strike}C | UW Price Not Found")
