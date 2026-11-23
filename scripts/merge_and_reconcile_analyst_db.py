#!/usr/bin/env python3
"""
merge_and_reconcile_analyst_db.py - Safe, Lossless Reconciliation of Legacy and Canonical Analyst Databases.

Unifies:
  Source (Legacy):    ~/.hermes/analyst_trading.db
  Target (Canonical): ~/.hermes/data/analyst_trading.db

Performs:
  1. Full pre-migration snapshot backups of both databases.
  2. Lossless de-duplicating merge across all tables (raw_messages, analysts, positions, trade_events, notable_flow, etc.).
  3. Integrity verification (PRAGMA integrity_check) on canonical target.
  4. Archives legacy DB to ~/.hermes/data/analyst_trading.db.legacy_backup and replaces root with a protective symlink.
"""

import sys
import os
import shutil
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("db_reconciler")

LEGACY_DB = Path.home() / ".hermes" / "analyst_trading.db"
CANONICAL_DB = Path.home() / ".hermes" / "data" / "analyst_trading.db"


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?", (table_name,))
    return cur.fetchone() is not None


def get_column_names(conn: sqlite3.Connection, table_name: str) -> List[str]:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name})")
    return [r[1] for r in cur.fetchall()]


def reconcile_databases(dry_run: bool = False) -> Dict[str, Any]:
    if not LEGACY_DB.exists():
        logger.error("Legacy database not found at %s", LEGACY_DB)
        return {"ok": False, "error": "Legacy database missing"}

    if not CANONICAL_DB.exists():
        logger.error("Canonical database not found at %s", CANONICAL_DB)
        return {"ok": False, "error": "Canonical database missing"}

    # Check if LEGACY_DB is already a symlink pointing to CANONICAL_DB
    if LEGACY_DB.is_symlink() and LEGACY_DB.resolve() == CANONICAL_DB.resolve():
        logger.info("Legacy DB is already a symlink pointing to canonical DB. Nothing to merge.")
        return {"ok": True, "already_symlinked": True}

    logger.info("=================================================================")
    logger.info("📊 STARTING LOSSLESS ANALYST DATABASE RECONCILIATION")
    logger.info("Source (Legacy):    %s (%d bytes)", LEGACY_DB, LEGACY_DB.stat().st_size)
    logger.info("Target (Canonical): %s (%d bytes)", CANONICAL_DB, CANONICAL_DB.stat().st_size)
    logger.info("Mode: %s", "DRY-RUN (No changes applied)" if dry_run else "LIVE MIGRATION")
    logger.info("=================================================================")

    # 1. Backups
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = CANONICAL_DB.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    canonical_backup = backup_dir / f"canonical_analyst_trading_{timestamp}.db"
    legacy_backup = backup_dir / f"legacy_analyst_trading_{timestamp}.db"

    if not dry_run:
        logger.info("Creating safety backup of canonical DB -> %s", canonical_backup)
        shutil.copy2(CANONICAL_DB, canonical_backup)
        logger.info("Creating safety backup of legacy DB -> %s", legacy_backup)
        shutil.copy2(LEGACY_DB, legacy_backup)

    # 2. Open connections
    src_conn = sqlite3.connect(str(LEGACY_DB))
    src_conn.row_factory = sqlite3.Row
    
    tgt_conn = sqlite3.connect(str(CANONICAL_DB))
    tgt_conn.row_factory = sqlite3.Row
    tgt_conn.execute("PRAGMA foreign_keys = OFF;")
    tgt_conn.execute("PRAGMA journal_mode = WAL;")

    stats: Dict[str, Dict[str, int]] = {}

    try:
        tables_to_merge = [
            "raw_messages",
            "analysts",
            "positions",
            "trade_events",
            "portfolios",
            "portfolio_holdings",
            "analyst_styles",
            "reviewer_audits",
            "notable_flow",
            "flow_candidate_analytics",
        ]

        for table in tables_to_merge:
            if not table_exists(src_conn, table) or not table_exists(tgt_conn, table):
                continue

            src_cols = get_column_names(src_conn, table)
            tgt_cols = get_column_names(tgt_conn, table)
            common_cols = [c for c in src_cols if c in tgt_cols]
            cols_str = ", ".join(common_cols)
            placeholders = ", ".join(["?"] * len(common_cols))

            # Initial counts
            cur_src = src_conn.cursor()
            cur_src.execute(f"SELECT COUNT(*) FROM {table}")
            src_count = cur_src.fetchone()[0]

            cur_tgt = tgt_conn.cursor()
            cur_tgt.execute(f"SELECT COUNT(*) FROM {table}")
            tgt_before = cur_tgt.fetchone()[0]

            inserted_count = 0

            if table == "raw_messages":
                cur_src.execute(f"SELECT {cols_str} FROM raw_messages")
                for row in cur_src.fetchall():
                    if not dry_run:
                        cur_tgt.execute(
                            f"INSERT OR IGNORE INTO raw_messages ({cols_str}) VALUES ({placeholders})",
                            tuple(row)
                        )
                    inserted_count += 1

            elif table == "analysts":
                cur_src.execute(f"SELECT {cols_str} FROM analysts")
                for row in cur_src.fetchall():
                    if not dry_run:
                        cur_tgt.execute(
                            f"INSERT OR IGNORE INTO analysts ({cols_str}) VALUES ({placeholders})",
                            tuple(row)
                        )
                    inserted_count += 1

            elif table == "positions":
                cur_src.execute(f"SELECT {cols_str} FROM positions")
                for row in cur_src.fetchall():
                    if not dry_run:
                        cur_tgt.execute(
                            f"INSERT OR IGNORE INTO positions ({cols_str}) VALUES ({placeholders})",
                            tuple(row)
                        )
                    inserted_count += 1

            elif table == "trade_events":
                # High-speed in-memory set de-duplication: fetch existing (position_id, event_type, timestamp) in target
                cur_tgt.execute("SELECT position_id, event_type, timestamp FROM trade_events")
                existing_events = set(cur_tgt.fetchall())

                event_cols = [c for c in common_cols if c != "event_id"]
                event_cols_str = ", ".join(event_cols)
                event_placeholders = ", ".join(["?"] * len(event_cols))

                cur_src.execute(f"SELECT {', '.join(common_cols)} FROM trade_events")
                batch_to_insert = []
                for row in cur_src.fetchall():
                    row_dict = dict(row)
                    key = (row_dict.get("position_id"), row_dict.get("event_type"), row_dict.get("timestamp"))
                    if key in existing_events:
                        continue
                    existing_events.add(key)
                    batch_to_insert.append(tuple(row_dict[c] for c in event_cols))

                if not dry_run and batch_to_insert:
                    cur_tgt.executemany(
                        f"INSERT INTO trade_events ({event_cols_str}) VALUES ({event_placeholders})",
                        batch_to_insert
                    )
                inserted_count = len(batch_to_insert)

            elif table == "notable_flow":
                cur_src.execute(f"SELECT {cols_str} FROM notable_flow")
                for row in cur_src.fetchall():
                    if not dry_run:
                        cur_tgt.execute(
                            f"INSERT OR IGNORE INTO notable_flow ({cols_str}) VALUES ({placeholders})",
                            tuple(row)
                        )
                    inserted_count += 1

            elif table in ("reviewer_audits", "portfolios", "portfolio_holdings", "analyst_styles", "flow_candidate_analytics"):
                cur_src.execute(f"SELECT {cols_str} FROM {table}")
                for row in cur_src.fetchall():
                    if not dry_run:
                        cur_tgt.execute(
                            f"INSERT OR IGNORE INTO {table} ({cols_str}) VALUES ({placeholders})",
                            tuple(row)
                        )
                    inserted_count += 1

            if not dry_run:
                tgt_conn.commit()
                cur_tgt.execute(f"SELECT COUNT(*) FROM {table}")
                tgt_after = cur_tgt.fetchone()[0]
                delta = tgt_after - tgt_before
            else:
                tgt_after = tgt_before
                delta = 0

            stats[table] = {
                "source_count": src_count,
                "target_before": tgt_before,
                "target_after": tgt_after,
                "new_rows_added": delta,
            }
            logger.info(
                "%-25s | Source: %6d | Target Before: %6d | Target After: %6d | Added: +%d",
                table, src_count, tgt_before, tgt_after, delta
            )

        if not dry_run:
            # 3. Integrity Check
            logger.info("Running PRAGMA integrity_check on reconciled database...")
            chk = tgt_conn.execute("PRAGMA integrity_check").fetchone()
            if chk and chk[0] == "ok":
                logger.info("✅ Database integrity check PASSED.")
            else:
                logger.error("❌ Integrity check returned: %s", chk)
                return {"ok": False, "error": f"Integrity check failed: {chk}"}

    finally:
        src_conn.close()
        tgt_conn.close()

    if not dry_run:
        # 4. Safe archive of legacy database and symlink creation
        legacy_archive_target = CANONICAL_DB.parent / "analyst_trading.db.legacy_backup"
        logger.info("Archiving legacy database to %s", legacy_archive_target)
        if legacy_archive_target.exists():
            legacy_archive_target.unlink()
        shutil.move(str(LEGACY_DB), str(legacy_archive_target))

        logger.info("Creating protective symlink: %s -> %s", LEGACY_DB, CANONICAL_DB)
        LEGACY_DB.symlink_to(CANONICAL_DB)
        logger.info("✅ Symlink established. All legacy paths will now resolve to canonical database.")

    logger.info("=================================================================")
    logger.info("🎉 ANALYST DATABASE RECONCILIATION COMPLETED SUCCESSFULLY")
    logger.info("=================================================================")
    return {"ok": True, "stats": stats}


if __name__ == "__main__":
    is_dry = "--dry-run" in sys.argv
    res = reconcile_databases(dry_run=is_dry)
    if not res.get("ok"):
        sys.exit(1)
