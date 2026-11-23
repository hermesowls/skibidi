#!/usr/bin/env python3
"""
Hermes Server Control Center & Status Monitor
Double-clickable interactive operational dashboard for macOS Mac Mini Server.
"""

import os
import sys
import subprocess
import time
from datetime import datetime

# Terminal colors
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
RESET = "\033[0m"

HERMES_DIR = "/Users/admin/repos/hermes-agent"
VENV_PYTHON = "/Users/admin/repos/hermes-agent/venv/bin/python"
HERMES_CLI = [VENV_PYTHON, "-m", "hermes_cli.main"]

def run_cmd(cmd_list, timeout=10):
    try:
        env = os.environ.copy()
        env["HERMES_HOME"] = os.path.expanduser("~/.hermes")
        env["PYTHONPATH"] = HERMES_DIR
        res = subprocess.run(
            cmd_list,
            cwd=HERMES_DIR,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env
        )
        return res.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def clear_screen():
    subprocess.run(["clear"], check=False)

def print_header():
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S PST")
    print(f"{CYAN}{BOLD}╔══════════════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{CYAN}{BOLD}║               🏛️  SKIBIDI — SERVER CONTROL CENTER                   ║{RESET}")
    print(f"{CYAN}{BOLD}║{RESET}  Host: {BOLD}Mac Mini (Production Server){RESET}               {DIM}{now_str}{RESET}   {CYAN}{BOLD}║{RESET}")
    print(f"{CYAN}{BOLD}╚══════════════════════════════════════════════════════════════════════════╝{RESET}\n")

def get_gateway_status():
    status_out = run_cmd(HERMES_CLI + ["gateway", "status"])
    if "is supervised by launchd" in status_out or "running" in status_out.lower():
        # extract PID if possible
        pid = "ACTIVE"
        for line in status_out.splitlines():
            if "PID" in line:
                pid = line.strip()
        return True, pid
    return False, "STOPPED"

def get_cron_summary():
    cron_out = run_cmd(HERMES_CLI + ["cron", "list"])
    active_count = cron_out.count("[active]")
    return active_count, cron_out

def print_dashboard():
    clear_screen()
    print_header()

    # 1. Gateway Status
    is_running, pid_info = get_gateway_status()
    if is_running:
        gw_badge = f"{GREEN}{BOLD}● ONLINE{RESET} ({pid_info})"
    else:
        gw_badge = f"{RED}{BOLD}○ OFFLINE{RESET}"

    print(f"{BOLD}[1] OPERATIONAL STATUS{RESET}")
    print(f"  • {BOLD}Gateway Service (launchd){RESET}: {gw_badge}")
    print(f"  • {BOLD}Active Ingress Platforms{RESET}:  {CYAN}Telegram (Polling){RESET} | {CYAN}Discord (Bot){RESET} | {CYAN}iMessage{RESET}")
    print(f"  • {BOLD}RBAC / Whitelist Mode{RESET}:     {GREEN}ENFORCED (Authorized Users Only){RESET}")
    print()

    # 2. Crons
    active_crons, _ = get_cron_summary()
    print(f"{BOLD}[2] AUTOMATED TRADING & RESEARCH CRONS{RESET}")
    print(f"  • {BOLD}Supervised Active Jobs{RESET}:   {GREEN}{active_crons} Active Pipelines{RESET}")
    print(f"  • {DIM}Key Routines: Premarket (05:45) | Intelligence (06:30) | Kian TA (06:35) | Midday (09:30) | Power Hour (12:00) | Post-Close (13:30){RESET}")
    print()

    # 3. Market Data & Stores
    db_path = os.path.expanduser("~/.hermes/trading_store.db")
    db_status = f"{GREEN}Available{RESET}" if os.path.exists(db_path) else f"{YELLOW}Ready to initialize{RESET}"
    print(f"{BOLD}[3] INTEGRATIONS & DATA STORE{RESET}")
    print(f"  • {BOLD}Market Data Providers{RESET}:   {CYAN}Databento (OFI){RESET} | {CYAN}Finviz Elite{RESET} | {CYAN}Unusual Whales{RESET} | {CYAN}Skylit GEX{RESET}")
    print(f"  • {BOLD}SQLite Trading Store{RESET}:    {db_status}")
    print()

    # 4. Recent Gateway Logs (Last 4 lines)
    log_path = os.path.expanduser("~/.hermes/logs/gateway.log")
    print(f"{BOLD}[4] RECENT GATEWAY LOG ACTIVITY{RESET}")
    if os.path.exists(log_path):
        try:
            lines = open(log_path, "r", encoding="utf-8", errors="replace").readlines()[-4:]
            for line in lines:
                print(f"  {DIM}{line.strip()}{RESET}")
        except Exception:
            print(f"  {DIM}Unable to read log file.{RESET}")
    else:
        print(f"  {DIM}No logs recorded yet.{RESET}")

    print("\n" + "─" * 74)
    print(f"{BOLD}QUICK ACTIONS:{RESET}")
    print(f"  {CYAN}[1]{RESET} Stream Live Logs (`hermes logs -f`)")
    print(f"  {CYAN}[2]{RESET} Restart Gateway Daemon (`hermes gateway restart`)")
    print(f"  {CYAN}[3]{RESET} View Detailed Cron Jobs (`hermes cron list`)")
    print(f"  {CYAN}[4]{RESET} Open Hermes Web Dashboard (`hermes dashboard`)")
    print(f"  {CYAN}[5]{RESET} Trigger Instant Kian TA / Intelligence Briefing")
    print(f"  {CYAN}[6]{RESET} Sync SQLite DB Tables to Google Sheets (Composio)")
    print(f"  {CYAN}[r]{RESET} Refresh Dashboard")
    print(f"  {CYAN}[q]{RESET} Exit")
    print("─" * 74)


def main():
    while True:
        print_dashboard()
        try:
            choice = input(f"\n{BOLD}Select an action [1-6, r, q]: {RESET}").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break

        if choice == "1":
            clear_screen()
            print(f"{CYAN}Streaming logs (Ctrl+C to return to menu)...{RESET}\n")
            try:
                subprocess.run([VENV_PYTHON, "-m", "hermes_cli.main", "logs", "-f"], cwd=HERMES_DIR)
            except KeyboardInterrupt:
                pass
        elif choice == "2":
            print(f"\n{YELLOW}Restarting gateway service...{RESET}")
            out = run_cmd(HERMES_CLI + ["gateway", "restart"])
            print(out)
            time.sleep(2)
        elif choice == "3":
            clear_screen()
            _, cron_out = get_cron_summary()
            print(cron_out)
            input(f"\n{DIM}Press Enter to return to menu...{RESET}")
        elif choice == "4":
            print(f"\n{CYAN}Starting / Opening Web Dashboard on http://127.0.0.1:9119 ...{RESET}")
            subprocess.Popen(HERMES_CLI + ["dashboard"], cwd=HERMES_DIR)
            time.sleep(2)
        elif choice == "5":
            print(f"\n{CYAN}Running Instant Kian Technical Analysis...{RESET}")
            out = run_cmd([VENV_PYTHON, "skills/financial/autonomous-trader/scripts/kian_analysis.py"], timeout=30)
            print(out)
            input(f"\n{DIM}Press Enter to return to menu...{RESET}")
        elif choice == "6":
            clear_screen()
            print(f"\n{CYAN}Syncing SQLite Database Tables to Google Sheets...{RESET}\n")
            subprocess.run([VENV_PYTHON, "-u", "scripts/sync_db_to_googlesheets.py"], cwd=HERMES_DIR)
            input(f"\n{DIM}Press Enter to return to menu...{RESET}")
        elif choice == "r" or choice == "":
            continue
        elif choice == "q":
            print("\nExiting Control Center.")
            break

if __name__ == "__main__":
    main()
