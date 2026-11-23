#!/usr/bin/env python3
"""
premarket_oi_auditor.py - Automated Pre-Market 06:15 PST OCC Open Interest Carryover Auditor.

Runs every morning before market open (06:15 PST):
  1. Compares overnight OCC net Open Interest updates against yesterday's flow.
  2. Calculates genuine Open Interest Delta (ΔOI = next_day_oi - initial_oi).
  3. Classifies empirical market distributions:
       - Institutional Accumulation: ΔOI >= 0.50 * Volume
       - Partial Carryover:          0 < ΔOI < 0.50 * Volume
       - Day-Trade Churn / Closure:  ΔOI <= 0
  4. Stores statistical records on NVMe SQLite for Nightly Dreaming & Strategy Lab.
"""

import os
import sys
import sqlite3
import logging
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from plugins.analyst_trader.db import get_db_path
from plugins.analyst_trader.learning_evidence import qualified_oi, aware_time

logger = logging.getLogger("PremarketOIAuditor")


class PremarketOIAuditor:
    """Pre-Market 06:15 PST OCC Open Interest Carryover Verifier."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(get_db_path())

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        return conn

    def run_premarket_oi_audit(self, *, as_of=None) -> Dict[str, Any]:
        """
        Scans all recent notable flow candidates and calculates OCC ΔOI carryover distributions.
        """
        logger.info("Executing Pre-Market 06:15 PST OCC OI Carryover Audit on %s...", self.db_path)
        conn = self._get_connection()
        cur = conn.cursor()
        clock = aware_time(as_of) if as_of else datetime.now(timezone.utc)

        # Query candidates from the last 72 hours (excluding quarantined rows)
        cur.execute("""
            SELECT flow_id, ticker, strike, call_put, expiration, dte, premium_usd,
                   flow_score, intraday_volume, initial_oi, next_day_oi, final_outcome, quant_metrics_json, trade_timestamp
            FROM notable_flow
            WHERE datetime(trade_timestamp) >= datetime(?, '-3 days') AND datetime(trade_timestamp)<=datetime(?)
              AND (is_quarantined = 0 OR is_quarantined IS NULL)
              AND NOT EXISTS (SELECT 1 FROM flow_candidate_analytics a
                  WHERE a.flow_id=notable_flow.flow_id AND COALESCE(a.is_quarantined,0)<>0)
        """, (clock.isoformat(), clock.isoformat()))
        rows = cur.fetchall()

        stats = {
            "total_audited": len(rows),
            "aggregate_large_increase": 0,
            "aggregate_increase": 0,
            "aggregate_nonincrease": 0,
            "unobserved": 0,
            "audit_timestamp": datetime.utcnow().isoformat() + "Z"
        }

        for r in rows:
            f_id = r["flow_id"]
            vol = r["intraday_volume"]
            init_oi = r["initial_oi"]
            next_oi = r["next_day_oi"]

            # Genuine OCC Clearinghouse Net Open Interest:
            # Only compute carryover when real clearinghouse data has been observed.
            # Never manufacture next-day OI with pseudo-random numbers.
            if qualified_oi(dict(r), clock) is not None:
                delta_oi = next_oi - init_oi
                is_carried_over = None  # aggregate OI cannot identify this whale's holding

                # Categorize distribution if volume is observed
                if vol and vol > 0 and delta_oi >= (0.50 * vol):
                    stats["aggregate_large_increase"] += 1
                elif delta_oi > 0:
                    stats["aggregate_increase"] += 1
                else:
                    stats["aggregate_nonincrease"] += 1
            else:
                delta_oi = None
                is_carried_over = None
                stats["unobserved"] += 1

            cur.execute("""
                UPDATE notable_flow
                SET next_day_oi = ?,
                    oi_delta = ?,
                    is_carried_over = ?
                WHERE flow_id = ?
            """, (next_oi, delta_oi, is_carried_over, f_id))

        conn.commit()
        conn.close()

        logger.info("Pre-Market OCC OI Audit Complete: %s", stats)
        return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    auditor = PremarketOIAuditor()
    res = auditor.run_premarket_oi_audit()
    print("\n" + "="*55)
    print("🌅 PRE-MARKET 06:15 PST OCC ΔOI AUDIT REPORT")
    print("="*55)
    print(f"Total Candidates Audited:       {res['total_audited']}")
    print(f"Aggregate large OI increase:    {res['aggregate_large_increase']}")
    print(f"Aggregate OI increase:          {res['aggregate_increase']}")
    print(f"Aggregate OI nonincrease:       {res['aggregate_nonincrease']}")
    print(f"Audit Timestamp:                {res['audit_timestamp']}")
    print("="*55 + "\n")
