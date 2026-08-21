import urllib.request, json

key = '179ee2b3-3f79-4f10-b5fe-2aa3d82d36ce'
headers = {
    'Authorization': f'Bearer {key}',
    'Accept': 'application/json',
    'User-Agent': 'HermesAgent/1.0'
}

tickers = ['RARE', 'RKLB', 'RGTI', 'ORCL', 'PLTR', 'VNET', 'FCX']

print("UNUSUAL WHALES OPTION CONTRACTS API TEST:\n")
for t in tickers:
    url = f'https://api.unusualwhales.com/api/stock/{t}/option-contracts'
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            contracts = data.get('data', [])
            print(f"✓ Unusual Whales returned {len(contracts)} option contracts for {t}:")
            # Search for matching sample
            for c in contracts[:3]:
                opt_sym = c.get("option_symbol")
                last_p = c.get("last_price")
                ask_p = c.get("ask")
                bid_p = c.get("bid")
                print(f"    - Contract: {opt_sym} | Last: ${last_p} | Bid: ${bid_p} | Ask: ${ask_p}")
    except Exception as e:
        print(f"x Error for {t}: {e}")
