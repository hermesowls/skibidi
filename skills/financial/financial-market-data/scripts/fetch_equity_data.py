#!/usr/bin/env python3
"""
fetch_equity_data.py
Fetch current equity/etf/fx prices and prior close from Yahoo Finance v8 chart API.
Usage: python3 fetch_equity_data.py '^GSPC' '^IXIC' '^VIX' '^TNX' 'AAPL'
Outputs JSON with price, prev_close, change, and pct_change for each ticker.
"""
import urllib.request
import json
import sys


def fetch_equity_data(tickers):
    out = {}
    for ticker in tickers:
        try:
            req = urllib.request.Request(
                f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d',
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
            result = data['chart']['result'][0]
            meta = result['meta']
            current = meta.get('regularMarketPrice')
            
            # Fallback chain for previous close: chartPreviousClose > previousClose > last close in array
            prev = meta.get('chartPreviousClose')
            if not prev:
                prev = meta.get('previousClose')
            if not prev:
                closes = result['indicators']['quote'][0].get('close', [])
                if len(closes) >= 2:
                    for c in reversed(closes[:-1]):
                        if c is not None:
                            prev = c
                            break
            
            change = current - prev if current is not None and prev is not None else None
            pct_change = round(change / prev * 100, 2) if change is not None and prev else None
            
            out[ticker] = {
                'price': current,
                'prev': prev,
                'change': change,
                'pct_change': pct_change
            }
        except Exception as e:
            out[ticker] = {'error': str(e)}
    return out

if __name__ == '__main__':
    tickers = sys.argv[1:]
    if not tickers:
        print('Usage: python3 fetch_equity_data.py <ticker1> <ticker2> ...')
        sys.exit(1)
    print(json.dumps(fetch_equity_data(tickers), indent=2))
