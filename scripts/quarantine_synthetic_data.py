#!/usr/bin/env python3
"""Provenance-scoped quarantine. Default is read-only; never infer from prices.

Unidentified legacy synthetic outcomes require reviewed evidence, not an automatic
strike/MFE heuristic. This tool does not connect to a provider or discover a DB.
"""
import argparse
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Optional

TABLE_KEYS = {'notable_flow': 'flow_id', 'flow_candidate_analytics': 'analytics_id'}
# Exact identifiers AND source timestamps from the removed hardcoded scanner.
KNOWN_SCANNER_FIXTURES = {
    'flow_flowseeker_NVDA_20261016_230C': ('skylit_flowseeker', '2026-08-24T19:42:00.000000+00:00'),
    'flow_flowseeker_AAPL_20261120_325C': ('skylit_flowseeker', '2026-08-24T19:35:10.000000+00:00'),
    'flow_flowseeker_SMH_20270115_580C': ('skylit_flowseeker', '2026-08-24T19:15:00.000000+00:00'),
    'flow_uw_TSLA_20260918_340P': ('unusual_whales', '2026-08-24T19:28:30.000000+00:00'),
    'flow_uw_PLTR_20261016_190C': ('unusual_whales', '2026-08-24T19:22:15.000000+00:00'),
}
FLAGS = ('is_quarantined', 'quarantine_reason', 'quarantine_batch_id')


def _tables(conn):
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _candidates(conn):
    tables = _tables(conn)
    rows = {t: [dict(r) for r in conn.execute(f'SELECT * FROM {t}')] if t in tables else [] for t in TABLE_KEYS}
    selected = {}
    flows = set()
    for row in rows['notable_flow']:
        expected = KNOWN_SCANNER_FIXTURES.get(row['flow_id'])
        if expected and (row.get('source'), row.get('trade_timestamp')) == expected and not row.get('raw_message_id'):
            flows.add(row['flow_id'])
            selected[('notable_flow', row['flow_id'])] = (row, 'removed-hardcoded-scanner:' + row['flow_id'])
    # Explicit provenance marker, not a numeric excursion/contract coincidence.
    for row in rows['flow_candidate_analytics']:
        try:
            evidence = json.loads(row.get('correlations_json') or '{}')
        except (TypeError, ValueError):
            continue
        if isinstance(evidence, dict) and evidence.get('evidence_kind') == 'synthetic' and evidence.get('evidence_id'):
            selected[('flow_candidate_analytics', row['analytics_id'])] = (row, 'synthetic-evidence:' + str(evidence['evidence_id']))
            flows.add(row.get('flow_id'))
    for table, items in rows.items():
        for row in items:
            if row.get('flow_id') in flows:
                selected.setdefault((table, row[TABLE_KEYS[table]]), (row, 'linked-quarantined-evidence:' + str(row.get('flow_id'))))
    return {key: value for key, value in selected.items() if not value[0].get('is_quarantined')}


def quarantine_data(db_path: Path, apply: bool = False, revert: bool = False,
                    batch_id: Optional[str] = None) -> dict:
    """Apply/revert an audited batch; dry-run never creates schema or databases."""
    if revert and not batch_id:
        raise ValueError('Revert requires an explicit recorded batch_id')
    if not revert and batch_id:
        raise ValueError('batch_id is only accepted for a scoped revert')
    path = Path(db_path).resolve(strict=True)
    conn = sqlite3.connect(path.as_uri() + ('?mode=rw' if apply else '?mode=ro'), uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        if not apply:
            conn.execute('PRAGMA query_only=ON')
        else:
            conn.execute('BEGIN IMMEDIATE')
        if revert:
            if 'quarantine_batches' not in _tables(conn) or not conn.execute('SELECT 1 FROM quarantine_batches WHERE batch_id=?', (batch_id,)).fetchone():
                raise ValueError('Unknown audited batch_id')
            entries = list(conn.execute("SELECT * FROM quarantine_audit WHERE batch_id=? AND action='APPLY'", (batch_id,)))
            restored = 0
            for entry in entries:
                table, key = entry['table_name'], entry['record_id']
                if table not in TABLE_KEYS:
                    raise ValueError('Invalid audited table')
                if conn.execute("SELECT 1 FROM quarantine_audit WHERE batch_id=? AND table_name=? AND record_id=? AND action='REVERT'", (batch_id, table, key)).fetchone():
                    continue
                row = conn.execute(f'SELECT * FROM {table} WHERE {TABLE_KEYS[table]}=?', (key,)).fetchone()
                if row is None or row['is_quarantined'] != 1 or row['quarantine_batch_id'] != batch_id:
                    raise ValueError('Quarantine state changed; refusing to overwrite another owner')
                restored += 1
                if apply:
                    before = json.loads(entry['before_json'])
                    conn.execute(f'UPDATE {table} SET is_quarantined=?, quarantine_reason=?, quarantine_batch_id=? WHERE {TABLE_KEYS[table]}=?', (*[before.get(f) for f in FLAGS], key))
                    conn.execute("INSERT INTO quarantine_audit(batch_id,action,table_name,record_id,before_json,evidence_id) VALUES (?, 'REVERT', ?, ?, ?, ?)", (batch_id, table, key, json.dumps(dict(row), sort_keys=True), entry['evidence_id']))
            if apply:
                conn.commit()
            return {'action': 'reverted' if apply else 'dry_run_revert', 'batch_id': batch_id, 'records_to_restore': restored, 'status': 'success'}
        selected = _candidates(conn)
        counts = {t: sum(key[0] == t for key in selected) for t in TABLE_KEYS}
        if not apply:
            return {'action': 'dry_run_quarantine', **{t+'_to_quarantine': n for t, n in counts.items()},
                    'evidence': [{'table': t, 'record_id': key, 'reason': value[1]} for (t, key), value in selected.items()],
                    'limitation': 'Unmarked legacy synthetic observations require manual provenance review'}
        for table in TABLE_KEYS:
            if table not in _tables(conn):
                continue
            columns = {r[1] for r in conn.execute(f'PRAGMA table_info({table})')}
            for name, kind in zip(FLAGS, ('INTEGER', 'TEXT', 'TEXT')):
                if name not in columns:
                    conn.execute(f'ALTER TABLE {table} ADD COLUMN {name} {kind}')
        conn.execute('CREATE TABLE IF NOT EXISTS quarantine_batches(batch_id TEXT PRIMARY KEY, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')
        conn.execute('''CREATE TABLE IF NOT EXISTS quarantine_audit(
            audit_id INTEGER PRIMARY KEY, batch_id TEXT NOT NULL, action TEXT NOT NULL,
            table_name TEXT NOT NULL, record_id TEXT NOT NULL, before_json TEXT NOT NULL,
            evidence_id TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(batch_id, action, table_name, record_id))''')
        for action in ('UPDATE', 'DELETE'):
            conn.execute(f"CREATE TRIGGER IF NOT EXISTS quarantine_audit_no_{action.lower()} BEFORE {action} ON quarantine_audit BEGIN SELECT RAISE(ABORT, 'append-only quarantine audit'); END")
        batch = 'batch_' + uuid.uuid4().hex
        conn.execute('INSERT INTO quarantine_batches(batch_id) VALUES (?)', (batch,))
        for (table, key), (row, reason) in selected.items():
            conn.execute("INSERT INTO quarantine_audit(batch_id,action,table_name,record_id,before_json,evidence_id) VALUES (?, 'APPLY', ?, ?, ?, ?)", (batch, table, key, json.dumps(row, sort_keys=True), reason))
            conn.execute(f'UPDATE {table} SET is_quarantined=1, quarantine_reason=?, quarantine_batch_id=? WHERE {TABLE_KEYS[table]}=?', (reason, batch, key))
        conn.commit()
        return {'action': 'quarantined', 'batch_id': batch, **{t+'_quarantined': n for t, n in counts.items()}, 'status': 'success'}
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db-path', type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--apply', action='store_true')
    mode.add_argument('--dry-run', action='store_true')
    parser.add_argument('--revert', action='store_true')
    parser.add_argument('--batch-id')
    args = parser.parse_args()
    print(json.dumps(quarantine_data(args.db_path, apply=args.apply, revert=args.revert, batch_id=args.batch_id), indent=2))


if __name__ == '__main__':
    main()
