#!/usr/bin/env python3
import os, sys, json

JOURNAL_PATH = os.path.expanduser("~/.hermes/paper_trading_journal.json")
PORTFOLIOS_PATH = os.path.expanduser("~/.hermes/strategy_portfolios_db.json")
OUTPUT_PATH = os.path.expanduser("/Users/admin/repos/hermes-agent/web/public/graph_data.json")

# Dynamic Supply Chain Mapping Database
SUPPLY_CHAIN_MAP = {
    "NVDA": {"suppliers": ["TSMC", "ASML"], "sympathy": ["SMCI", "AMD", "AVGO"]},
    "TSLA": {"suppliers": ["ALB", "PANW"], "sympathy": ["RIVN", "LCID"]},
    "AAPL": {"suppliers": ["TSMC", "SWKS", "QCOM"], "sympathy": ["MSFT"]},
    "MSFT": {"suppliers": ["NVDA", "AMD"], "sympathy": ["GOOGL", "AMZN"]},
    "AMD":  {"suppliers": ["TSMC", "ASML"], "sympathy": ["NVDA", "INTC"]},
    "SPY":  {"suppliers": ["AAPL", "NVDA", "MSFT"], "sympathy": ["QQQ", "IWM"]},
    "QQQ":  {"suppliers": ["NVDA", "AAPL", "MSFT"], "sympathy": ["SPY"]},
}

def load_json(path, default_val):
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return default_val

def build_neural_graph():
    journal = load_json(JOURNAL_PATH, {"trades": [], "active_positions": {}})
    portfolios = load_json(PORTFOLIOS_PATH, {})

    # Extract all unique tickers active in journal or open positions
    active_tickers = set()
    for tr in journal.get("trades", []):
        t = tr.get("ticker")
        if t:
            active_tickers.add(t.upper())
    for pos_key in journal.get("active_positions", {}).keys():
        t = pos_key.split("_")[0]
        if t:
            active_tickers.add(t.upper())

    # Fallback to broad market tickers if journal is empty
    if not active_tickers:
        active_tickers = {"SPY", "QQQ"}

    nodes = []
    links = []
    added_node_ids = set()

    # Core Signal Nodes
    signal_nodes = [
        {"id": "Skylit_GEX", "name": "Skylit GEX Heatmap", "community": "Signals", "val": 15, "color": "#f59e0b"},
        {"id": "Skylit_VEX", "name": "Skylit VEX Volatility", "community": "Signals", "val": 15, "color": "#f59e0b"},
        {"id": "UW_Flow", "name": "Unusual Whales Flow", "community": "Signals", "val": 15, "color": "#8b5cf6"},
        {"id": "GEX_0DTE", "name": "GEX 0DTE Scalp Portfolio", "community": "Portfolios", "val": 22, "color": "#ef4444"},
        {"id": "VEX_SWING", "name": "VEX Swing Portfolio", "community": "Portfolios", "val": 22, "color": "#10b981"},
    ]
    for s in signal_nodes:
        nodes.append(s)
        added_node_ids.add(s["id"])

    # Dynamically build Ticker & Supply Chain nodes
    ticker_count = 0
    supplier_count = 0
    sympathy_count = 0

    for ticker in active_tickers:
        if ticker not in added_node_ids:
            nodes.append({"id": ticker, "name": ticker, "community": "Tickers", "val": 18, "color": "#4f46e5"})
            added_node_ids.add(ticker)
            ticker_count += 1

        # Link ticker to Signals
        links.append({"source": ticker, "target": "Skylit_GEX"})
        links.append({"source": ticker, "target": "Skylit_VEX"})
        links.append({"source": ticker, "target": "UW_Flow"})

        # Dynamically link suppliers & sympathy
        meta = SUPPLY_CHAIN_MAP.get(ticker, {})
        for sup in meta.get("suppliers", []):
            if sup not in added_node_ids:
                nodes.append({"id": sup, "name": sup, "community": "Suppliers", "val": 11, "color": "#06b6d4"})
                added_node_ids.add(sup)
                supplier_count += 1
            links.append({"source": ticker, "target": sup})

        for sym in meta.get("sympathy", []):
            if sym not in added_node_ids:
                nodes.append({"id": sym, "name": sym, "community": "Sympathy", "val": 11, "color": "#ec4899"})
                added_node_ids.add(sym)
                sympathy_count += 1
            links.append({"source": ticker, "target": sym})

    # Add dynamic trade history nodes
    trade_count = len(journal.get("trades", []))
    for i, tr in enumerate(journal.get("trades", [])):
        t_id = f"Trade_{tr.get('ticker','SYS')}_{i+1}"
        target_ticker = tr.get("ticker", "SPY").upper()
        if target_ticker not in added_node_ids:
            nodes.append({"id": target_ticker, "name": target_ticker, "community": "Tickers", "val": 16, "color": "#4f46e5"})
            added_node_ids.add(target_ticker)

        nodes.append({
            "id": t_id,
            "name": f"{target_ticker} ({tr.get('mode')})",
            "community": "Active Trades",
            "val": 10,
            "color": "#10b981" if "WIN" in tr.get("status", "") else "#e11d48"
        })
        links.append({"source": t_id, "target": target_ticker})
        if tr.get("mode") == "GEX":
            links.append({"source": t_id, "target": "GEX_0DTE"})
        else:
            links.append({"source": t_id, "target": "VEX_SWING"})

    graph_payload = {
        "nodes": nodes,
        "links": links,
        "communities": [
            {"name": "Tickers", "color": "#4f46e5", "count": ticker_count},
            {"name": "Signals", "color": "#f59e0b", "count": 3},
            {"name": "Portfolios", "color": "#10b981", "count": 2},
            {"name": "Suppliers", "color": "#06b6d4", "count": supplier_count},
            {"name": "Sympathy", "color": "#ec4899", "count": sympathy_count},
            {"name": "Active Trades", "color": "#e11d48", "count": trade_count},
        ]
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(graph_payload, f, indent=2)

    print(f"Generated dynamic neural graph at {OUTPUT_PATH} ({len(nodes)} nodes, {len(links)} links).")

if __name__ == "__main__":
    build_neural_graph()
