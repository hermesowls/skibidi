#!/usr/bin/env python3
"""Local Test Script for Hybrid LLM Reviewer Agent on Analyst Scrapers.

Audits raw Discord analyst messages against recorded tracker positions in analyst_trading.db,
detects missed or misclassified trade alerts, and executes auto-reconciliation updates.
"""

import sys
import json
import logging
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from plugins.analyst_trader.db import AnalystDatabase
from plugins.analyst_trader.llm_reviewer import LLMTradeReviewer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    analyst_name = sys.argv[1] if len(sys.argv) > 1 else "Jon & Kian"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50

    logger.info("=== Starting LLM Reviewer Agent Audit for Analyst: '%s' ===", analyst_name)

    db = AnalystDatabase()
    reviewer = LLMTradeReviewer()

    # Run batch audit across raw messages for analyst
    results = reviewer.audit_channel_batch(analyst_name=analyst_name, db=db, limit=limit, auto_reconcile=True)

    print("\n================ LLM REVIEWER AUDIT SUMMARY ================")
    print(f"Analyst Name            : {results['analyst_name']}")
    print(f"Total Messages Audited  : {results['total_audited']}")
    print(f"Discrepancies Found     : {results['discrepancies_found']}")
    print(f"Reconciliations Executed: {results['reconciliations_executed']}")

    print("\n---------------- DISCREPANCY AUDIT DETAILS ----------------")
    discrepancies = [a for a in results["audits"] if a.get("discrepancy_type") != "MATCHED_ACCURATE"]
    if not discrepancies:
        print("  ✓ All audited messages match database position tracker events accurately!")
    else:
        for idx, d in enumerate(discrepancies, 1):
            msg_id = d.get("message_id")
            ticker = d.get("ticker", "N/A")
            disc_type = d.get("discrepancy_type")
            conf = d.get("confidence_score")
            reason = d.get("reasoning")
            status = d.get("status")
            print(f"  [{idx}] MsgID: {msg_id} | Ticker: {ticker:<5} | Type: {disc_type:<16} | Conf: {conf:.2f} | Status: {status}")
            print(f"      Reasoning: {reason}")

    print("\n---------------- RECONCILIATIONS EXECUTED ----------------")
    if not results["reconciliations"]:
        print("  ✓ No position corrections were required.")
    else:
        for idx, r in enumerate(results["reconciliations"], 1):
            status = r.get("status")
            aid = r.get("audit_id")
            action = r.get("action_taken")
            print(f"  [{idx}] AuditID: {aid} | Status: {status} | Action: {action}")

    # Verify audits saved in database table
    audits_in_db = db.list_reviewer_audits(analyst_name=analyst_name, limit=10)
    print(f"\n================ DATABASE REVIEWER_AUDITS TABLE ({len(audits_in_db)} recent records) ================")
    for row in audits_in_db[:5]:
        print(f"  [Audit {row.get('audit_id')}] Ticker: {row.get('ticker') or 'N/A':<5} | Type: {row.get('discrepancy_type'):<16} | Conf: {row.get('confidence_score'):.2f} | Status: {row.get('status')}")

    print("\n=== LLM Reviewer Agent Local Test Completed Successfully ===")


if __name__ == "__main__":
    main()
