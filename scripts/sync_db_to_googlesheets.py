#!/usr/bin/env python3
"""
Sync all SQLite database tables to Google Sheets via Composio.
Primary Spreadsheet: "Hermes Alpha & Analyst Trading Engine (Live DB)"
"""

import os
import sys
import json
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

SPREADSHEET_ID_FILE = os.path.expanduser("~/.hermes/google_sheets_sync.json")
DEFAULT_SPREADSHEET_ID = "1kIIaibuqiIp8nBP1LCRmfqm9d03YrLQ7eYVhtzf7NcY"
COMPOSIO_BIN = os.path.expanduser("~/.composio/composio")

ANALYST_DB = os.path.expanduser("~/.hermes/analyst_trading.db")
STRATEGY_DB = os.path.expanduser("~/.hermes/strategy_incubator.db")

def run_composio_tool(slug, payload, timeout=30):
    cmd = [COMPOSIO_BIN, "execute", slug, "-d", json.dumps(payload)]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if res.returncode != 0:
        print(f"[-] Composio error executing {slug}: {res.stderr}")
        return None
    try:
        return json.loads(res.stdout)
    except Exception:
        return None

def get_or_create_spreadsheet():
    spreadsheet_id = DEFAULT_SPREADSHEET_ID
    if os.path.exists(SPREADSHEET_ID_FILE):
        try:
            with open(SPREADSHEET_ID_FILE, "r") as f:
                data = json.load(f)
                spreadsheet_id = data.get("spreadsheet_id", DEFAULT_SPREADSHEET_ID)
        except Exception:
            pass
    return spreadsheet_id

def get_sheet_names(spreadsheet_id):
    res = run_composio_tool("GOOGLESHEETS_GET_SHEET_NAMES", {"spreadsheet_id": spreadsheet_id})
    if res and res.get("successful") and res.get("data"):
        data = res["data"]
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("sheet_names", []) or data.get("sheets", [])
    return ["Sheet1"]

def ensure_tabs_exist(spreadsheet_id, required_tabs, existing_tabs):
    for tab in required_tabs:
        if tab not in existing_tabs and tab != "Sheet1":
            print(f"[*] Creating tab '{tab}' in Google Sheets...")
            run_composio_tool("GOOGLESHEETS_ADD_SHEET", {
                "spreadsheet_id": spreadsheet_id,
                "title": tab
            })

def query_table_data(db_path, table_name, max_rows=1000):
    if not os.path.exists(db_path):
        return [], []
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f'PRAGMA table_info("{table_name}")')
    cols = [c[1] for c in cursor.fetchall()]
    cursor.execute(f'SELECT * FROM "{table_name}" ORDER BY rowid DESC LIMIT {max_rows}')
    rows = cursor.fetchall()
    conn.close()
    
    # Format rows cleanly (convert None to "", json/dicts/timestamps to string)
    formatted_rows = []
    for r in rows:
        formatted_rows.append([str(v) if v is not None else "" for v in r])
    return cols, formatted_rows

def sync_table_to_tab(spreadsheet_id, tab_name, headers, rows):
    if not headers:
        return
    values = [headers] + rows
    num_cols = len(headers)
    num_rows = len(values)
    
    def col_to_letter(col_idx):
        result = ""
        while col_idx > 0:
            col_idx, remainder = divmod(col_idx - 1, 26)
            result = chr(65 + remainder) + result
        return result

    end_col = col_to_letter(num_cols)
    cell_range = f"'{tab_name}'!A1:{end_col}{num_rows}"
    
    print(f"[*] Uploading {len(rows)} rows to '{tab_name}' ({cell_range})...")
    payload = {
        "spreadsheet_id": spreadsheet_id,
        "range": cell_range,
        "value_input_option": "USER_ENTERED",
        "values": values
    }
    res = run_composio_tool("GOOGLESHEETS_VALUES_UPDATE", payload, timeout=45)
    if res and res.get("successful"):
        print(f"    [+] Successfully synced {len(rows)} rows to '{tab_name}'")
    else:
        print(f"    [-] Failed to sync '{tab_name}': {res}")

def main():
    print("\n=======================================================")
    print(" 🚀 HERMES AGENT — GOOGLE SHEETS LIVE DB SYNC")
    print("=======================================================\n")
    
    spreadsheet_id = get_or_create_spreadsheet()
    sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
    print(f"Target Sheet URL:\n{sheet_url}\n")
    
    # Check existing tabs
    existing_tabs = get_sheet_names(spreadsheet_id)
    print(f"Existing tabs: {existing_tabs}")
    
    tables_to_sync = [
        ("Analysts", ANALYST_DB, "analysts"),
        ("Positions", ANALYST_DB, "positions"),
        ("Trade_Events", ANALYST_DB, "trade_events"),
        ("Portfolios", ANALYST_DB, "portfolios"),
        ("Notable_Flow", ANALYST_DB, "notable_flow"),
        ("Reviewer_Audits", ANALYST_DB, "reviewer_audits"),
        ("Sub_Portfolios", STRATEGY_DB, "sub_portfolios"),
        ("Experimental_Trades", STRATEGY_DB, "experimental_trades"),
    ]
    
    required_tabs = [t[0] for t in tables_to_sync]
    ensure_tabs_exist(spreadsheet_id, required_tabs, existing_tabs)
    
    # Sync each table
    for tab_name, db_path, table_name in tables_to_sync:
        if not os.path.exists(db_path):
            print(f"[-] Database {db_path} not found, skipping {table_name}.")
            continue
        headers, rows = query_table_data(db_path, table_name, max_rows=1000)
        if headers:
            sync_table_to_tab(spreadsheet_id, tab_name, headers, rows)
        else:
            print(f"[-] No data found in {table_name}")

    # Save metadata
    with open(SPREADSHEET_ID_FILE, "w") as f:
        json.dump({
            "spreadsheet_id": spreadsheet_id,
            "url": sheet_url,
            "last_synced_at": datetime.now().isoformat(),
            "tables_synced": required_tabs
        }, f, indent=2)

    print("\n✅ Sync Complete! Open your Google Sheet here:")
    print(f"👉 {sheet_url}\n")

if __name__ == "__main__":
    main()
