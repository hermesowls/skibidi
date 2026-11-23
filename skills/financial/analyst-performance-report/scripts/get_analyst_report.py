#!/usr/bin/env python3
"""
Analyst Performance Report CLI helper script for Hermes / Skibidi.
Fetches performance metrics, active positions, and recent trade events from ~/.hermes/analyst_trading.db
and formats clean Telegram / Discord Markdown reports matching the Dashboard metrics exactly.
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_db_connection() -> sqlite3.Connection:
    db_path = Path.home() / ".hermes" / "analyst_trading.db"
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_analyst_stats(analyst_query: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cur = conn.cursor()

    if analyst_query:
        cur.execute(
            "SELECT DISTINCT analyst_name FROM positions WHERE analyst_name LIKE ?",
            (f"%{analyst_query}%",),
        )
    else:
        cur.execute("SELECT DISTINCT analyst_name FROM positions")

    analysts = [r[0] for r in cur.fetchall()]
    reports = []

    for name in analysts:
        cur.execute(
            "SELECT * FROM positions WHERE analyst_name = ?",
            (name,),
        )
        all_positions = [dict(r) for r in cur.fetchall()]
        if not all_positions:
            continue

        open_positions = [p for p in all_positions if p["status"] == "OPEN"]
        trimmed_positions = [p for p in all_positions if p["status"] == "TRIMMED"]
        closed_positions = [p for p in all_positions if p["status"] == "CLOSED"]

        # Dashboard exact win & ROI formulas:
        # closed_evaluated = CLOSED or (TRIMMED with roi_pct > 0)
        closed_eval = [
            p for p in all_positions
            if p["status"] == "CLOSED" or (p["status"] == "TRIMMED" and float(p.get("roi_pct") or 0) > 0)
        ]
        closed_wins = [p for p in closed_eval if float(p.get("roi_pct") or 0) > 0]
        closed_losses = [p for p in closed_eval if float(p.get("roi_pct") or 0) <= 0]

        win_rate = (len(closed_wins) / len(closed_eval) * 100.0) if closed_eval else 0.0
        avg_closed_win_roi = (
            sum(float(p.get("roi_pct") or 0) for p in closed_wins) / len(closed_wins)
            if closed_wins
            else 0.0
        )
        blended_live_mtm = (
            sum(float(p.get("roi_pct") or 0) for p in all_positions) / len(all_positions)
            if all_positions
            else 0.0
        )

        # Recent 5 closed positions
        cur.execute(
            """
            SELECT position_id, ticker, asset_type, direction, strike, expiration, entry_price, exit_price, roi_pct, status, exit_time
            FROM positions
            WHERE analyst_name = ? AND status = 'CLOSED'
            ORDER BY exit_time DESC, updated_at DESC
            LIMIT 5
            """,
            (name,),
        )
        recent_closed = [dict(r) for r in cur.fetchall()]

        active_list = open_positions + trimmed_positions

        reports.append(
            {
                "analyst_name": name,
                "total_positions": len(all_positions),
                "open_count": len(open_positions),
                "trimmed_count": len(trimmed_positions),
                "closed_count": len(closed_positions),
                "closed_wins_count": len(closed_wins),
                "closed_losses_count": len(closed_losses),
                "win_rate": round(win_rate, 1),
                "avg_closed_win_roi": round(avg_closed_win_roi, 1),
                "blended_live_mtm": round(blended_live_mtm, 1),
                "active_positions": active_list,
                "recent_closed": recent_closed,
            }
        )

    return reports


def format_markdown_report(reports: List[Dict[str, Any]]) -> str:
    if not reports:
        return "⚠️ No analyst matching that query was found in the database."

    lines = []
    for r in reports:
        name = r["analyst_name"]
        win_emoji = "🔥" if r["win_rate"] >= 60 else "📊"
        lines.append(f"{win_emoji} **Analyst Performance Card: {name}**")
        lines.append("━━━" * 10)
        lines.append(f"• **Active Positions**: `{r['open_count']} Open` · `{r['trimmed_count']} Trimmed` (`{r['closed_count']} Fully Closed`)")
        lines.append(f"• **Win Rate**: `{r['win_rate']}%` ({r['closed_wins_count']} Wins logged)")
        lines.append(f"• **Avg Closed Win**: `+{r['avg_closed_win_roi']}%`")
        lines.append(f"• **Blended Live MTM**: `{'+' if r['blended_live_mtm'] >= 0 else ''}{r['blended_live_mtm']}%`")
        lines.append("")

        if r["active_positions"]:
            lines.append("🟢 **Active & Runner Positions:**")
            for p in r["active_positions"]:
                strike_str = f" ${p['strike']:.0f}C" if p.get("strike") else ""
                exp_str = f" ({p['expiration']})" if p.get("expiration") else ""
                cur_p = p.get("current_price") or p.get("entry_price") or 0.0
                entry_p = p.get("entry_price") or 0.0
                roi = p.get("roi_pct") or 0.0
                roi_str = f"+{roi:.1f}%" if roi >= 0 else f"{roi:.1f}%"
                status_tag = f" [{p['status']}]" if p['status'] == "TRIMMED" else ""
                lines.append(
                    f"  ▫️ **{p['ticker']}**{strike_str}{exp_str} @ `${entry_p:.2f}` → Current: `${cur_p:.2f}` (`{roi_str}`){status_tag}"
                )
            lines.append("")

        if r["recent_closed"]:
            lines.append("🏁 **Recent Closed Trades:**")
            for p in r["recent_closed"]:
                roi = p.get("roi_pct") or 0.0
                roi_badge = f"🟢 +{roi:.1f}%" if roi >= 0 else f"🔴 {roi:.1f}%"
                lines.append(
                    f"  ▫️ **{p['ticker']}**: Entry `${p['entry_price']:.2f}` → Exit `${p['exit_price']:.2f}` [{roi_badge}]"
                )
            lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Get Analyst Performance Card")
    parser.add_argument("--analyst", type=str, help="Analyst name (e.g. Eva, Kian, AB, Jon)")
    parser.add_argument("--format", type=str, choices=["markdown", "json"], default="markdown")
    args = parser.parse_args()

    reports = fetch_analyst_stats(args.analyst)

    if args.format == "json":
        print(json.dumps(reports, indent=2))
    else:
        print(format_markdown_report(reports))


if __name__ == "__main__":
    main()
