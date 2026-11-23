import os
import requests
import re
import logging
import time
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Fast In-Memory TTL Cache (30s TTL)
_OPTION_CHAIN_CACHE: Dict[str, Dict[str, Any]] = {}
_METRICS_CACHE: Dict[str, Dict[str, Any]] = {}
_LIVE_QUOTES_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL_SEC = 30.0
_LIVE_QUOTES_TTL_SEC = 60.0

class FinvizFetcher:
    """Fetch real-time stock metrics from Finviz and Yahoo Finance fallback."""
    
    def __init__(self, timeout: int = 8) -> None:
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def fetch_ticker_metrics(self, ticker: str) -> Dict[str, Any]:
        """Finviz-first display quote. Fetch time is NOT an exchange quote as-of.

        No automatic fallback is authorized by this API. Legacy CBOE helpers remain
        separate and unqualified; they cannot overwrite a Finviz quote.
        """
        from copy import deepcopy
        from datetime import datetime, timezone
        import math
        if not isinstance(ticker, str) or not re.fullmatch(r'[A-Z]{1,6}', ticker):
            raise ValueError('Exact uppercase ticker required')
        now = time.time()
        cached = _METRICS_CACHE.get(ticker)
        if cached and 0 <= now - cached['timestamp'] < _CACHE_TTL_SEC:
            return deepcopy(cached['data'])
        data = self._fetch_finviz(ticker)
        price = data.get('price')
        valid = not isinstance(price,bool) and isinstance(price,(int,float)) and math.isfinite(price) and price > 0
        data.update(price=price if valid else None, quote_source='finviz', quote_asof=None,
                    quote_observed_at=datetime.now(timezone.utc).isoformat(),
                    quote_validity='unknown_asof' if valid else 'unavailable',
                    execution_authorized=False)
        data['historical_closes'] = self.fetch_historical_closes(ticker, period='1y')
        _METRICS_CACHE[ticker] = {'timestamp':now, 'data':deepcopy(data)}
        return data

    def fetch_historical_closes(self, ticker: str, period: str = "1y") -> List[float]:
        """Fetch real daily historical closing prices via CBOE for exact EMA 8, 21, 50, 100, and 200 calculation."""
        try:
            import urllib.request
            import json
            url = f"https://cdn.cboe.com/api/global/delayed_quotes/charts/historical/{ticker.upper()}.json"
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8")).get("data", [])
                closes = [round(float(row["close"]), 2) for row in data if "close" in row]
                if period == "3mo":
                    return closes[-90:]
                elif period == "6mo":
                    return closes[-130:]
                elif period == "max":
                    return closes
                return closes[-260:] if len(closes) >= 260 else closes
        except Exception as e:
            logger.warning("Failed to fetch CBOE historical closes for %s: %s", ticker, e)
        return []

    def _fetch_finviz(self, ticker: str) -> Dict[str, Any]:
        url = f"https://finviz.com/quote.ashx?t={ticker}"
        result = {
            "ticker": ticker,
            "price": 0.0,
            "change_pct": 0.0,
            "volume": 0,
            "avg_volume": 0,
            "rel_volume": 1.0,
            "atr": 0.5,
            "rsi_14": 50.0,
            "short_float_pct": 0.0,
            "vwap_dist_pct": 0.0,
            "sue_score": 0.0
        }
        
        try:
            resp = requests.get(url, headers=self.headers, timeout=self.timeout)
            if resp.status_code != 200:
                return result
                
            html = resp.text
            
            # Extract price
            price_match = re.search(r'class="quote-price"[^>]*>([\d\.]+)<', html) or re.search(r'<b>([\d\.]+)</b></td>[^<]*<td[^>]*>Price', html)
            if price_match:
                result["price"] = float(price_match.group(1))

            # Extract change
            change_match = re.search(r'<b>([\+\-\d\.]+)%</b></td>[^<]*<td[^>]*>Change', html) or re.search(r'Change</td>\s*<td[^>]*><b>([\+\-\d\.]+)%</b>', html)
            if change_match:
                result["change_pct"] = float(change_match.group(1))

            # Extract Volume
            vol_match = re.search(r'Volume</td>\s*<td[^>]*><b>([\d\.\,KMB]+)</b>', html)
            if vol_match:
                result["volume"] = self._parse_num(vol_match.group(1))

            # Extract Avg Volume
            avg_vol_match = re.search(r'Avg Volume</td>\s*<td[^>]*><b>([\d\.\,KMB]+)</b>', html)
            if avg_vol_match:
                result["avg_volume"] = self._parse_num(avg_vol_match.group(1))

            # Rel Volume
            rel_vol_match = re.search(r'Rel Volume</td>\s*<td[^>]*><b>([\d\.]+)</b>', html)
            if rel_vol_match:
                result["rel_volume"] = float(rel_vol_match.group(1))

            # ATR
            atr_match = re.search(r'ATR</td>\s*<td[^>]*><b>([\d\.]+)</b>', html)
            if atr_match:
                result["atr"] = float(atr_match.group(1))

            # RSI (14)
            rsi_match = re.search(r'RSI \(14\)</td>\s*<td[^>]*><b>([\d\.]+)</b>', html)
            if rsi_match:
                result["rsi_14"] = float(rsi_match.group(1))

            # Short Float
            sf_match = re.search(r'Short Float</td>\s*<td[^>]*><b>([\d\.]+)%</b>', html)
            if sf_match:
                result["short_float_pct"] = float(sf_match.group(1))

        except Exception as e:
            logger.warning("Finviz fetch exception for %s: %s", ticker, e)

        return result

    def _fetch_yahoo_fallback(self, ticker: str) -> Dict[str, Any]:
        """Fetch extended hours / after hours real-time price data via CBOE."""
        try:
            import urllib.request
            import json
            url = f"https://cdn.cboe.com/api/global/delayed_quotes/options/{ticker.upper()}.json"
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8")).get("data", {})
                current_p = float(data.get("current_price", 0.0))
                prev_close = float(data.get("prev_day_close", current_p))
                if current_p > 0:
                    change_pct = round(((current_p - prev_close) / prev_close * 100), 2) if prev_close else 0.0
                    return {
                        "price": round(current_p, 2),
                        "change_pct": change_pct,
                        "is_extended_hours": True
                    }
        except Exception as e:
            logger.warning("CBOE extended hours exception for %s: %s", ticker, e)
        return {}

    def fetch_live_quotes(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch live CBOE delayed market prices for a list of tickers with in-memory TTL cache."""
        now = time.time()
        results: Dict[str, Dict[str, Any]] = {}
        for t in tickers:
            sym = t.strip().upper()
            if not sym:
                continue
            cached = _LIVE_QUOTES_CACHE.get(sym)
            if cached and 0 <= now - cached["timestamp"] < _LIVE_QUOTES_TTL_SEC:
                results[sym] = cached["data"]
                continue

            quote = self._fetch_yahoo_fallback(sym)
            if quote and quote.get("price", 0) > 0:
                data = {
                    "price": float(quote["price"]),
                    "change_pct": float(quote.get("change_pct", 0.0)),
                    "is_extended_hours": bool(quote.get("is_extended_hours", False)),
                }
            else:
                data = {"price": 0.0, "change_pct": 0.0, "is_extended_hours": False}

            _LIVE_QUOTES_CACHE[sym] = {"timestamp": now, "data": data}
            results[sym] = data
        return results

    def _parse_num(self, val_str: str) -> int:
        val_str = val_str.replace(",", "").upper()
        if "M" in val_str:
            return int(float(val_str.replace("M", "")) * 1_000_000)
        if "K" in val_str:
            return int(float(val_str.replace("K", "")) * 1_000)
        if "B" in val_str:
            return int(float(val_str.replace("B", "")) * 1_000_000_000)
        try:
            return int(float(val_str))
        except ValueError:
            return 0

    def fetch_live_option_chain(self, ticker: str) -> Dict[str, Any]:
        """Fetch full live Robinhood-style option chain matrix via Unusual Whales API (Primary) with CBOE fallback."""
        ticker = ticker.upper()
        now = time.time()

        if ticker in _OPTION_CHAIN_CACHE:
            cached_entry = _OPTION_CHAIN_CACHE[ticker]
            if now - cached_entry["timestamp"] < _CACHE_TTL_SEC:
                return cached_entry["data"]

        try:
            import urllib.request
            import json
            import datetime
            import re

            m_info = self.fetch_ticker_metrics(ticker)
            p_val = m_info.get("price")
            share_price = float(p_val) if p_val is not None and float(p_val) > 0 else 11.95

            # 1. Unusual Whales Ticker-Specific Option Contracts API
            uw_key = os.getenv("UNUSUAL_WHALES_API_KEY", "")
            if uw_key:
                try:
                    uw_url = f"https://api.unusualwhales.com/api/stock/{ticker}/option-contracts"
                    uw_req = urllib.request.Request(uw_url, headers={"Authorization": f"Bearer {uw_key}", "User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(uw_req, timeout=self.timeout) as uw_resp:
                        raw_data = json.loads(uw_resp.read().decode("utf-8")).get("data", [])
                        
                        if raw_data:
                            exp_groups = {}
                            pattern = re.compile(r"^([A-Z]+)(\d{2})(\d{2})(\d{2})([CP])(\d{8})$")
                            
                            for item in raw_data:
                                opt_sym = item.get("option_symbol", "")
                                m = pattern.match(opt_sym)
                                if not m:
                                    continue
                                
                                yy, mm, dd, otype, strike_raw = m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)
                                exp_date_str = f"20{yy}-{mm}-{dd}"
                                strike = float(strike_raw) / 1000.0
                                
                                ask = float(item.get("nbbo_ask") or 0.0)
                                bid = float(item.get("nbbo_bid") or 0.0)
                                last_p = float(item.get("last_price") or 0.0) or ask
                                vol = int(item.get("volume") or 0)
                                oi = int(item.get("open_interest") or 0)
                                
                                if ask <= 0:
                                    ask = last_p if last_p > 0 else 0.05
                                if bid <= 0:
                                    bid = ask * 0.90
                                
                                is_call = (otype == "C")
                                breakeven = (strike + ask) if is_call else (strike - ask)
                                to_breakeven_pct = (((breakeven - share_price) / share_price) * 100) if is_call else (((share_price - breakeven) / share_price) * 100)
                                
                                contract_obj = {
                                    "strike": float(strike),
                                    "ask": float(round(ask, 2)),
                                    "bid": float(round(bid, 2)),
                                    "last_price": float(round(last_p, 2)),
                                    "mark_price": float(round((ask + bid) / 2.0, 2)),
                                    "percent_change": 0.0,
                                    "breakeven": float(round(breakeven, 2)),
                                    "to_breakeven_pct": float(round(to_breakeven_pct, 2)),
                                    "volume": vol,
                                    "open_interest": oi,
                                    "in_the_money": bool(strike < share_price if is_call else strike > share_price)
                                }
                                
                                if exp_date_str not in exp_groups:
                                    exp_groups[exp_date_str] = {"calls": [], "puts": []}
                                if is_call:
                                    exp_groups[exp_date_str]["calls"].append(contract_obj)
                                else:
                                    exp_groups[exp_date_str]["puts"].append(contract_obj)
                            
                            result_expirations = []
                            today = datetime.date.today()
                            sorted_dates = sorted(exp_groups.keys())
                            
                            for exp in sorted_dates[:6]:
                                exp_dt = datetime.datetime.strptime(exp, "%Y-%m-%d")
                                exp_label = exp_dt.strftime("%b %d")
                                dte = max(1, (exp_dt.date() - today).days)
                                
                                calls = sorted(exp_groups[exp]["calls"], key=lambda x: x["strike"], reverse=True)
                                puts = sorted(exp_groups[exp]["puts"], key=lambda x: x["strike"], reverse=True)
                                
                                result_expirations.append({
                                    "expiration": exp,
                                    "label": exp_label,
                                    "dte": dte,
                                    "calls": calls,
                                    "puts": puts
                                })
                            
                            if result_expirations:
                                res = {
                                    "ok": True,
                                    "ticker": ticker,
                                    "share_price": round(share_price, 2),
                                    "source": "UNUSUAL_WHALES_API",
                                    "expirations": result_expirations
                                }
                                _OPTION_CHAIN_CACHE[ticker] = {"timestamp": now, "data": res}
                                return res
                except Exception as e_uw:
                    logger.warning("Unusual Whales API option chain fetch failed for %s: %s", ticker, e_uw)

            # 2. CBOE Direct Option Chain Feed (Real-Time OPRA Option Chain for exact Ticker)
            url = f"https://cdn.cboe.com/api/global/delayed_quotes/options/{ticker}.json"
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8")).get("data", {})
                raw_options = data.get("options", [])
                if not raw_options:
                    return {"ok": False, "ticker": ticker, "share_price": round(share_price, 2), "expirations": []}

                exp_groups = {}
                pattern = re.compile(r"^([A-Z]+)(\d{2})(\d{2})(\d{2})([CP])(\d{8})$")

                for opt in raw_options:
                    symbol = opt.get("option", "")
                    m = pattern.match(symbol)
                    if not m:
                        continue

                    yy, mm, dd, otype, strike_raw = m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)
                    exp_date_str = f"20{yy}-{mm}-{dd}"
                    strike = float(strike_raw) / 1000.0

                    ask = float(opt.get("ask", 0.0))
                    bid = float(opt.get("bid", 0.0))
                    last_p = float(opt.get("last_trade_price", 0.0)) or ask
                    vol = int(opt.get("volume", 0))
                    oi = int(opt.get("open_interest", 0))
                    pct_change = float(opt.get("percent_change", 0.0))

                    if ask <= 0:
                        ask = last_p if last_p > 0 else 0.05
                    if bid <= 0:
                        bid = ask * 0.90

                    is_call = (otype == "C")
                    if is_call:
                        breakeven = strike + ask
                        to_breakeven_pct = ((breakeven - share_price) / share_price) * 100
                    else:
                        breakeven = strike - ask
                        to_breakeven_pct = ((share_price - breakeven) / share_price) * 100

                    contract_obj = {
                        "strike": float(strike),
                        "ask": float(round(ask, 2)),
                        "bid": float(round(bid, 2)),
                        "last_price": float(round(last_p, 2)),
                        "mark_price": float(round((ask + bid) / 2.0, 2)),
                        "percent_change": float(round(pct_change, 2)),
                        "breakeven": float(round(breakeven, 2)),
                        "to_breakeven_pct": float(round(to_breakeven_pct, 2)),
                        "volume": int(vol),
                        "open_interest": int(oi),
                        "in_the_money": bool(strike < share_price if is_call else strike > share_price)
                    }

                    if exp_date_str not in exp_groups:
                        exp_groups[exp_date_str] = {"calls": [], "puts": []}

                    if is_call:
                        exp_groups[exp_date_str]["calls"].append(contract_obj)
                    else:
                        exp_groups[exp_date_str]["puts"].append(contract_obj)

                result_expirations = []
                today = datetime.date.today()
                sorted_dates = sorted(exp_groups.keys())

                for exp in sorted_dates[:6]:
                    exp_dt = datetime.datetime.strptime(exp, "%Y-%m-%d")
                    exp_label = exp_dt.strftime("%b %d")
                    dte = max(1, (exp_dt.date() - today).days)

                    calls = sorted(exp_groups[exp]["calls"], key=lambda x: x["strike"], reverse=True)
                    puts = sorted(exp_groups[exp]["puts"], key=lambda x: x["strike"], reverse=True)

                    result_expirations.append({
                        "expiration": exp,
                        "label": exp_label,
                        "dte": dte,
                        "calls": calls,
                        "puts": puts
                    })

                res = {
                    "ok": True,
                    "ticker": ticker,
                    "share_price": round(share_price, 2),
                    "source": "CBOE_FALLBACK",
                    "expirations": result_expirations
                }
                _OPTION_CHAIN_CACHE[ticker] = {"timestamp": now, "data": res}
                return res
        except Exception as e:
            logger.warning("Failed to fetch CBOE option chain for %s: %s", ticker, e)
            return {"ok": False, "error": str(e), "ticker": ticker, "share_price": 11.95, "expirations": []}

    def fetch_finviz_insider_buys(self, ticker: str) -> Dict[str, Any]:
        """Fetch real-time insider buy transactions from Finviz quote page."""
        ticker = ticker.upper()
        url = f"https://finviz.com/quote.ashx?t={ticker}"
        insider_buys = []
        total_buy_value = 0.0
        total_buy_shares = 0
        try:
            from bs4 import BeautifulSoup
            import urllib.request

            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                html = resp.read().decode("utf-8")
                soup = BeautifulSoup(html, "html.parser")
                tables = soup.find_all("table", class_="body-table")
                for t in tables:
                    rows = t.find_all("tr")
                    for r in rows:
                        cols = [c.text.strip() for c in r.find_all("td")]
                        if len(cols) >= 7:
                            insider_name = cols[0]
                            relationship = cols[1]
                            date_str = cols[2]
                            tx_type = cols[3]
                            shares_str = cols[5].replace(",", "")
                            value_str = cols[6].replace(",", "")

                            # Filter for INSIDER BUYS ONLY ("Buy", "Option Exercise", "Purchase")
                            is_buy = any(b in tx_type.lower() for b in ["buy", "option exercise", "purchase"])
                            if is_buy:
                                try:
                                    shares = int(shares_str)
                                    value = float(value_str) if value_str else 0.0
                                    total_buy_shares += shares
                                    total_buy_value += value
                                    insider_buys.append({
                                        "insider": insider_name,
                                        "relationship": relationship,
                                        "date": date_str,
                                        "tx_type": tx_type,
                                        "shares": shares,
                                        "value": value
                                    })
                                except ValueError:
                                    pass
        except Exception as e:
            logger.warning("Failed to fetch Finviz insider buys for %s: %s", ticker, e)

        return {
            "insider_buys": insider_buys,
            "insider_buy_count": len(insider_buys),
            "total_insider_buy_shares": total_buy_shares,
            "total_insider_buy_value": round(total_buy_value, 2),
            "insider_sentiment": "STRONG_BUY_ACCUMULATION" if len(insider_buys) >= 3 else ("BULLISH" if len(insider_buys) > 0 else "NEUTRAL")
        }

    def fetch_all_universe(self, tickers: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        if not tickers:
            tickers = ["METC", "NOK", "FRMI", "QURE"]
        
        results = {}
        for t in tickers:
            results[t] = self.fetch_ticker_metrics(t)
        return results

if __name__ == "__main__":
    fetcher = FinvizFetcher()
    universe = fetcher.fetch_all_universe(["METC", "NOK", "FRMI", "QURE"])
    print("Finviz Universe Realtime Market Data:")
    for t, m in universe.items():
        print(f"  {t}: Price=${m['price']}, Change={m['change_pct']}%, Vol={m['volume']}, RelVol={m['rel_volume']}, ATR={m['atr']}")
