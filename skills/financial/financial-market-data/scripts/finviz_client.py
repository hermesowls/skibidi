#!/usr/bin/env python3
"""
finviz_client.py - Finviz Elite API client helper for Hermes Agent.
Parses realtime equity quotes, market caps, P/E ratios, technical indicators,
and 8, 21, 50, 100, 200 SMAs. Standard library only.
"""

import csv
import io
import json
import os
import sys
import ssl
import time
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"


def get_finviz_api_url() -> str | None:
    """Retrieve FINVIZ_API_URL from environment or .env file."""
    url = os.environ.get("FINVIZ_API_URL")
    if url:
        return url

    # Candidate locations for .env
    candidates = [
        os.path.expanduser("~/.hermes/.env"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../.env")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.env")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.env")),
    ]
    for env_path in candidates:
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("FINVIZ_API_URL="):
                            val = line.split("=", 1)[1].strip().strip("\"'")
                            if val:
                                os.environ["FINVIZ_API_URL"] = val
                                return val
            except Exception:
                pass
    return None


def parse_csv_stream(csv_text: str) -> list[dict]:
    """Parse CSV text into a list of row dictionaries."""
    if not csv_text or not csv_text.strip():
        return []
    reader = csv.DictReader(io.StringIO(csv_text))
    return [row for row in reader]


def _build_finviz_export_url(base_url: str, view: int = 111, tickers: list[str] | None = None) -> str:
    """Build a Finviz screener export URL preserving auth token and adding ticker filter."""
    parsed = urllib.parse.urlparse(base_url)
    qs = urllib.parse.parse_qs(parsed.query)

    auth = qs.get("auth", [""])[0]
    base_path = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    params = {"v": str(view)}
    if auth:
        params["auth"] = auth
    if tickers:
        clean_tickers = [t.upper().strip() for t in tickers if t.strip()]
        if clean_tickers:
            params["t"] = ",".join(clean_tickers)

    # Preserve any existing filters if not specifying tickers explicitly
    if not tickers and "f" in qs:
        params["f"] = qs["f"][0]

    return f"{base_path}?{urllib.parse.urlencode(params)}"


def _get_ssl_context():
    """Create SSL context with fallback for systems with missing local CA certificates."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        pass
    try:
        ctx = ssl._create_unverified_context()
        return ctx
    except Exception:
        pass
    return ssl.create_default_context()


def fetch_raw_csv(url: str, timeout: int = 10) -> str:
    """Fetch raw CSV payload from URL with SSL fallback."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        context = _get_ssl_context()
        with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
            return resp.read().decode("utf-8", errors="replace")


def _calculate_smas(ticker: str, price_val: float | None, tech_data: dict) -> dict:
    """Calculate exact SMAs for periods 8, 21, 50, 100, and 200."""
    time.sleep(0.1)
    urls = [
        f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1y",
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1y",
    ]
    closes = []
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(CookieJar()),
        urllib.request.HTTPSHandler(context=_get_ssl_context())
    )
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with opener.open(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
                raw_closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
                closes = [c for c in raw_closes if c is not None]
                if len(closes) >= 8:
                    break
        except Exception:
            pass

    smas = {}
    if len(closes) >= 8:
        curr = price_val if price_val is not None else closes[-1]
        for period in [8, 21, 50, 100, 200]:
            if len(closes) >= period:
                avg = sum(closes[-period:]) / period
                pct = ((curr - avg) / avg) * 100
                smas[f"sma{period}"] = f"${avg:.2f} ({pct:+.2f}%)"
            else:
                smas[f"sma{period}"] = None
    else:
        # Fallback to Finviz export values for SMA 50 & 200
        smas = {
            "sma8": None,
            "sma21": None,
            "sma50": tech_data.get("50-Day Simple Moving Average"),
            "sma100": None,
            "sma200": tech_data.get("200-Day Simple Moving Average"),
        }
    return smas


def fetch_quotes(tickers: list[str]) -> list[dict]:
    """
    Fetch comprehensive equity quotes for tickers via Finviz Elite API.
    Combines overview (v=111) and technical (v=171) datasets with 8, 21, 50, 100, 200 SMAs.
    """
    base_url = get_finviz_api_url()
    if not base_url:
        return []

    tickers = [t.upper().strip() for t in tickers if t.strip()]
    if not tickers:
        return []

    # Fetch overview view (v=111)
    overview_url = _build_finviz_export_url(base_url, view=111, tickers=tickers)
    overview_csv = fetch_raw_csv(overview_url)
    overview_rows = parse_csv_stream(overview_csv)

    # Fetch technical view (v=171) for 52w high/low, RSI
    tech_url = _build_finviz_export_url(base_url, view=171, tickers=tickers)
    tech_rows = {}
    try:
        tech_csv = fetch_raw_csv(tech_url)
        for r in parse_csv_stream(tech_csv):
            if r.get("Ticker"):
                tech_rows[r["Ticker"].upper()] = r
    except Exception:
        pass

    results = []
    for r in overview_rows:
        ticker = r.get("Ticker", "").upper()
        if not ticker:
            continue

        tech_data = tech_rows.get(ticker, {})

        # Parse numeric values cleanly
        price_val = None
        try:
            price_val = float(r.get("Price", "").replace(",", ""))
        except (ValueError, TypeError):
            pass

        pe_val = None
        try:
            pe_val = float(r.get("P/E", "").replace(",", ""))
        except (ValueError, TypeError):
            pass

        market_cap_str = r.get("Market Cap", "")
        if market_cap_str and market_cap_str != "-":
            try:
                mc_num = float(market_cap_str)
                if mc_num >= 1e6:
                    market_cap_str = f"{mc_num / 1e6:.2f}T"
                elif mc_num >= 1e3:
                    market_cap_str = f"{mc_num / 1e3:.2f}B"
                else:
                    market_cap_str = f"{mc_num:.2f}M"
            except ValueError:
                pass

        smas = _calculate_smas(ticker, price_val, tech_data)

        item = {
            "symbol": ticker,
            "short_name": r.get("Company"),
            "company": r.get("Company"),
            "sector": r.get("Sector"),
            "industry": r.get("Industry"),
            "country": r.get("Country"),
            "price": f"{price_val:.2f}" if price_val is not None else r.get("Price"),
            "change_pct": r.get("Change"),
            "volume": r.get("Volume"),
            "market_cap": market_cap_str,
            "pe_ratio": f"{pe_val:.2f}" if pe_val is not None else r.get("P/E"),
            "52w_high": tech_data.get("52-Week High"),
            "52w_low": tech_data.get("52-Week Low"),
            "rsi_14": tech_data.get("Relative Strength Index (14)"),
            "sma8": smas.get("sma8"),
            "sma21": smas.get("sma21"),
            "sma50": smas.get("sma50"),
            "sma100": smas.get("sma100"),
            "sma200": smas.get("sma200"),
            "data_source": "Finviz Elite",
        }
        results.append(item)

    return results


def main() -> None:
    tickers = sys.argv[1:]
    if not tickers:
        print("Usage: finviz_client.py <SYMBOL1> [SYMBOL2 ...]")
        sys.exit(1)

    quotes = fetch_quotes(tickers)
    print(json.dumps(quotes, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
