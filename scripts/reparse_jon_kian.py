"""Reparse historical raw messages for Jon & Kian analyst channel into analyst_trading.db."""

import logging
import json
import sqlite3
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from plugins.analyst_trader.db import AnalystDatabase, get_db_path
from plugins.analyst_trader.parser import DiscordBackfillEngine
from plugins.analyst_trader.price_updater import UnusualWhalesPriceUpdater

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def reparse_jon_kian_messages():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    logger.info("Starting historical re-parse for Jon & Kian analyst channel...")

    # 1. Register distinct Jon and Kian analysts in DB
    db = AnalystDatabase(db_path)
    ch_id = "1339678887411322960"
    db.register_analyst(ch_id, "jon-and-kian", "Jon")
    db.register_analyst(ch_id + "_kian", "jon-and-kian", "Kian")

    # 2. Clear old positions for Jon & Kian to rebuild cleanly from raw_messages
    with conn:
        conn.execute("DELETE FROM positions WHERE analyst_name IN ('Jon & Kian', 'Jon', 'Kian')")
        conn.execute("DELETE FROM trade_events WHERE analyst_name IN ('Jon & Kian', 'Jon', 'Kian')")

    # 3. Fetch all raw messages for Jon & Kian in chronological order (oldest first)
    cur = conn.execute("""
        SELECT * FROM raw_messages
        WHERE analyst_name LIKE '%Jon%' OR analyst_name LIKE '%Kian%' OR channel_name LIKE '%jon%'
        ORDER BY timestamp ASC
    """)
    messages = [dict(r) for r in cur.fetchall()]
    logger.info("Found %d raw messages for Jon & Kian. Processing...", len(messages))

    engine = DiscordBackfillEngine(db)
    positions_created = 0
    trades_updated = 0

    for msg in messages:
        msg_id = msg["message_id"]
        channel_id = msg["channel_id"]
        channel_name = msg["channel_name"]
        analyst_name = msg["analyst_name"]
        author_id = msg["author_id"]
        content = msg["content"] or ""
        embeds = json.loads(msg["embeds_json"]) if msg["embeds_json"] else []
        timestamp = msg["timestamp"]

        res = engine.process_raw_alert(
            message_id=msg_id,
            channel_id=channel_id,
            channel_name=channel_name,
            analyst_name=analyst_name,
            author_id=author_id,
            content=content,
            embeds=embeds,
            timestamp=timestamp
        )
        if res:
            if res.get("status") == "OPEN":
                positions_created += 1
            else:
                trades_updated += 1

    # 4. Recalculate stats for Jon and Kian
    db.recalculate_analyst_stats("Jon")
    db.recalculate_analyst_stats("Kian")

    # 5. Run Unusual Whales Mark-to-Market for open positions
    try:
        updater = UnusualWhalesPriceUpdater(db)
        updater.update_open_positions_mark_to_market()
    except Exception as e:
        logger.warning("Unusual Whales price update post-reparse failed: %s", e)

    logger.info("Reparse completed! Total Jon & Kian raw messages processed: %d", len(messages))

    # Print summary of updated positions for Jon & Kian
    cur_p = conn.execute("""
        SELECT position_id, analyst_name, ticker, status, realized_pnl, roi_pct, entry_time, exit_time, notes
        FROM positions
        WHERE analyst_name IN ('Jon', 'Kian', 'Jon & Kian')
        ORDER BY entry_time DESC
    """)
    rows = [dict(r) for r in cur_p.fetchall()]
    print(f"\n================ JON & KIAN RE-PARSED POSITIONS ({len(rows)}) ================")
    for r in rows:
        print(f"[{r['entry_time'][:10]}] {r['analyst_name']} {r['ticker']} ({r['status']}) | ROI: {r['roi_pct']:+.1f}% | PnL: ${r['realized_pnl']:.2f}")

if __name__ == "__main__":
    reparse_jon_kian_messages()
