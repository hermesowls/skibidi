"""Clean Rebuild & Backfill Script for Analyst Trading Database."""

import json
import logging
import os
import sqlite3, sys
from pathlib import Path

# Load env variables
env_path = Path.home() / ".hermes" / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

from tools.discord_tool import _list_guilds, _list_channels, _get_bot_token, _fetch_messages, DiscordAPIError
from plugins.analyst_trader.db import AnalystDatabase, get_db_path
from plugins.analyst_trader.parser import DiscordBackfillEngine
from plugins.analyst_trader.price_updater import UnusualWhalesPriceUpdater

db_path = get_db_path()
print(f"Rebuilding database at: {db_path}")

# Drop existing database file and WAL logs for a 100% fresh clean slate
for ext in ["", "-wal", "-shm"]:
    p = Path(str(db_path) + ext)
    if p.exists():
        try:
            p.unlink()
        except Exception:
            pass
print("✓ Purged old database file.")

db = AnalystDatabase(db_path)
engine = DiscordBackfillEngine(db)
token = _get_bot_token()

if not token:
    print("❌ No DISCORD_BOT_TOKEN found!")
    sys.exit(1)

guilds_raw = _list_guilds(token)
g_data = json.loads(guilds_raw)
g_id = g_data['guilds'][0]['id']
chans_raw = _list_channels(token, g_id)
c_data = json.loads(chans_raw)

analyst_channels = []
for group in c_data.get('channel_groups', []):
    cat = group.get('category')
    cat_name = cat['name'] if cat else ''
    if 'alert' in cat_name.lower() or '0dte' in cat_name.lower():
        for ch in group.get('channels', []):
            if ch['type'] == 'text':
                analyst_channels.append(ch)

print(f"Discovered {len(analyst_channels)} analyst channels to ingest.")

total_messages = 0
total_positions = 0

for ch in analyst_channels:
    ch_id = ch['id']
    ch_name = ch['name']
    
    try:
        raw = _fetch_messages(token, ch_id, limit=50)
        data = json.loads(raw)
        msgs = data.get('messages', [])
        msgs = list(reversed(msgs))  # Process in chronological order (oldest first)
        db.register_analyst(ch_id, ch_name)
        print(f"  ✓ Ingested {len(msgs)} messages from #{ch_name}")
        for m in msgs:
            pos = engine.process_raw_alert(
                message_id=m['id'],
                channel_id=ch_id,
                channel_name=ch_name,
                analyst_name=ch_name,
                author_id=m['author']['id'],
                content=m.get('content', ''),
                embeds=m.get('embeds'),
                timestamp=m.get('timestamp')
            )
            total_messages += 1
            if pos:
                total_positions += 1
    except DiscordAPIError as err:
        print(f"  x Skipped #{ch_name} (Missing Access)")

print(f"\n✓ Backfill complete: {total_messages} messages, {total_positions} positions extracted.")

# Now run live Option Contract Mark-to-Market Price Updater via Unusual Whales
print("\nFetching live Option Contract & Stock Mark-to-Market prices via Unusual Whales API...")
updater = UnusualWhalesPriceUpdater(db)
res = updater.update_open_positions_mark_to_market()
print(f"✓ Mark-to-Market complete: {res['positions_updated']} positions updated at {res['last_price_updated_at']}.")
