#!/usr/bin/env python3
"""
fetch_equity_data.py
Fetch current equity/etf/fx prices and prior close via Finviz Elite API (primary) or Yahoo Finance v8 API (fallback).
Usage: python3 fetch_equity_data.py 'AAPL' 'MSFT' '^GSPC'
Outputs JSON with price, prev_close, change, and pct_change for each ticker.
"""
import json
import sys
import urllib.request
import os

try:
    import finviz_client
except ImportError:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    import finviz_client


def fetch_from_yahoo(ticker: str) -> dict:
    """Fallback fetcher using Yahoo Finance v8 chart API."""
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

        return {
            'price': current,
            'prev': prev,
            'change': round(change, 2) if change is not None else None,
            'pct_change': pct_change,
            'data_source': 'Yahoo Finance'
        }
    except Exception as e:
        return {'error': str(e)}


def fetch_equity_data(tickers):
    out = {}

    # Attempt batch fetch via Finviz Elite
    finviz_results = {}
    if finviz_client.get_finviz_api_url():
        try:
            fq_list = finviz_client.fetch_quotes(tickers)
            for fq in fq_list:
                sym = fq.get("symbol", "").upper()
                if not sym:
                    continue
                try:
                    price_val = float(fq["price"].replace(",", "")) if fq.get("price") else None
                except (ValueError, TypeError):
                    price_val = None

                pct_str = fq.get("change_pct", "").replace("%", "")
                try:
                    pct_val = float(pct_str)
                except (ValueError, TypeError):
                    pct_val = None

                finviz_results[sym] = {
                    'price': price_val,
                    'prev': None,
                    'change': None,
                    'pct_change': pct_val,
                    'data_source': 'Finviz Elite'
                }
        except Exception:
            pass

    for ticker in tickers:
        sym = ticker.upper().strip()
        if sym in finviz_results:
            out[ticker] = finviz_results[sym]
        else:
            out[ticker] = fetch_from_yahoo(ticker)

    return out


if __name__ == '__main__':
    tickers = sys.argv[1:]
    if not tickers:
        print('Usage: python3 fetch_equity_data.py <ticker1> <ticker2> ...')
        sys.exit(1)
    print(json.dumps(fetch_equity_data(tickers), indent=2))
