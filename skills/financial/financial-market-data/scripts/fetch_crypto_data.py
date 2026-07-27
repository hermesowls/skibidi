#!/usr/bin/env python3
"""
fetch_crypto_data.py
Fetch current crypto prices and 24h change from CoinGecko v3 API.
Usage: python3 fetch_crypto_data.py 'bitcoin,ethereum,solana'
Outputs JSON with price and change_24h for each coin.
"""
import urllib.request
import json
import sys


def fetch_crypto_data(ids):
    out = {}
    for coin_id in ids:
        try:
            req = urllib.request.Request(
                f'https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true',
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
            info = data.get(coin_id, {})
            out[coin_id] = {
                'price': info.get('usd'),
                'change_24h': info.get('usd_24h_change')
            }
        except Exception as e:
            out[coin_id] = {'error': str(e)}
    return out

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python3 fetch_crypto_data.py <coin_id1,coin_id2,...>')
        sys.exit(1)
    ids = sys.argv[1].split(',')
    print(json.dumps(fetch_crypto_data(ids), indent=2))
