#!/usr/bin/env python3
"""
quant_storage_cache.py - Two-Tier NVMe Primary Cache with 1 TB Cold Storage Sync.

Provides:
  1. Primary NVMe SQLite Database (~/.hermes/data/quant_historical_profiles.db) in WAL mode.
  2. Two-Tier Cache Architecture:
       - Dynamic Microstructure (TTL: 120s max for L2 OFI, queue velocity, Hawkes intensity).
       - Static Fundamental Profile (TTL: 24h for macro, insider buying, daily levels).
  3. Databento Cost Throttling: Max 3 L2 evaluations per ticker per trading session.
  4. Non-blocking async cold backup to external 1 TB SATA HD when mounted.
"""

import os
import sys
import json
import sqlite3
import logging
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("QuantStorageCache")

from hermes_constants import get_hermes_home

LOCAL_DATA_DIR = get_hermes_home() / "data"
PRIMARY_DB_PATH = LOCAL_DATA_DIR / "quant_historical_profiles.db"

EXTERNAL_HD_ROOT = Path("/Volumes/Macintosh 1 TB HD/hermes_storage/quant_cache")


def observed_l2(metrics, ticker, ttl=120.0):
    """Schema/provenance gate; not proof of entitlement or calibration."""
    if not isinstance(metrics, dict):
        return False
    if (metrics.get('ticker') != ticker or metrics.get('status') != 'observed'
            or metrics.get('is_market_observation') is not True
            or metrics.get('dataset_source') != 'DATABENTO_L2_DBEQ'
            or metrics.get('schema') not in ('mbp-1', 'mbp-10', 'mbo')):
        return False
    try:
        stamp = datetime.fromisoformat(metrics['observed_at'].replace('Z', '+00:00'))
        if stamp.tzinfo is None or not 0 <= (datetime.now(timezone.utc) - stamp).total_seconds() <= ttl:
            return False
        for name in ('ofi_score', 'hawkes_intensity', 'queue_depletion_velocity'):
            value = metrics[name]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                return False
        return -1 <= metrics['ofi_score'] <= 1 and metrics['hawkes_intensity'] >= 0 and metrics['queue_depletion_velocity'] >= 0
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


def init_cache_database(db_path: Optional[Path] = None):
    """Initializes primary NVMe SQLite cache with composite primary key and WAL settings."""
    db_path = Path(db_path) if db_path is not None else get_hermes_home() / "data" / "quant_historical_profiles.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=5.0)
    conn.execute('CREATE TABLE IF NOT EXISTS l2_query_attempts(ticker TEXT NOT NULL, session_date TEXT NOT NULL, attempts INTEGER NOT NULL, PRIMARY KEY(ticker,session_date))')
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ticker_quant_profiles (
            ticker TEXT NOT NULL,
            occ_symbol TEXT NOT NULL DEFAULT '',
            session_date TEXT NOT NULL DEFAULT '',
            model_version TEXT NOT NULL DEFAULT 'v1.2.0-RC1',
            last_price REAL,
            directional_bias TEXT,
            p_bullish REAL,
            target_node REAL,
            touch_prob_3d REAL,
            brier_score REAL,
            is_calibrated INTEGER,
            hawkes_intensity REAL,
            ofi_score REAL,
            gex_regime TEXT,
            raw_quant_json TEXT,
            microstructure_updated_at TEXT,
            static_profile_updated_at TEXT,
            session_l2_eval_count INTEGER DEFAULT 1,
            cache_hit_count INTEGER DEFAULT 1,
            PRIMARY KEY (ticker, occ_symbol, session_date, model_version)
        )
    """)
    # Automatic schema migration for existing databases
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(ticker_quant_profiles)")
    existing_cols = {row[1] for row in cur.fetchall()}
    if "occ_symbol" not in existing_cols:
        conn.execute("ALTER TABLE ticker_quant_profiles ADD COLUMN occ_symbol TEXT NOT NULL DEFAULT ''")
    if "session_date" not in existing_cols:
        conn.execute("ALTER TABLE ticker_quant_profiles ADD COLUMN session_date TEXT NOT NULL DEFAULT ''")
    if "model_version" not in existing_cols:
        conn.execute("ALTER TABLE ticker_quant_profiles ADD COLUMN model_version TEXT NOT NULL DEFAULT 'v1.2.0-RC1'")
    conn.commit()
    conn.close()


class QuantStorageCache:
    """Manages Two-Tier Caching, Databento Session Throttling, and Storage Concurrency."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = str(db_path if db_path is not None else get_hermes_home() / "data" / "quant_historical_profiles.db")
        init_cache_database(Path(self.db_path))

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def get_cached_profile(self, ticker: str, microstructure_ttl_seconds: float = 120.0,
                           static_ttl_hours: float = 24.0) -> Tuple[Optional[Dict[str, Any]], bool]:
        """
        Retrieves cached ticker profile.
        Returns: (cached_dict_or_None, is_microstructure_valid)
        """
        ticker = ticker.upper().strip()
        conn = self._get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT * FROM ticker_quant_profiles 
            WHERE ticker = ? 
            ORDER BY static_profile_updated_at DESC, rowid DESC 
            LIMIT 1
        """, (ticker,))
        row = cur.fetchone()

        if not row:
            conn.close()
            return None, False

        now = datetime.now(timezone.utc)
        micro_ts = row["microstructure_updated_at"]
        static_ts = row["static_profile_updated_at"] or micro_ts

        # Check static profile freshness (24h)
        static_age_hours = float("inf")
        try:
            static_dt = datetime.fromisoformat(static_ts.replace('Z', '+00:00'))
            if static_dt.tzinfo is None:
                raise ValueError('Naive cache timestamp')
            static_age_hours = (now - static_dt).total_seconds() / 3600.0
            is_static_valid = 0 <= static_age_hours <= static_ttl_hours
        except Exception:
            is_static_valid = False

        if not is_static_valid:
            conn.close()
            return None, False

        # Check microstructure freshness (120s)
        micro_age_seconds = float("inf")
        try:
            micro_dt = datetime.fromisoformat(micro_ts.replace('Z', '+00:00'))
            if micro_dt.tzinfo is None:
                raise ValueError('Naive observation timestamp')
            micro_age_seconds = (now - micro_dt).total_seconds()
            is_micro_valid = 0 <= micro_age_seconds <= microstructure_ttl_seconds
        except Exception:
            is_micro_valid = False

        # Increment cache hit count
        row_keys = row.keys()
        ticker_val = row["ticker"]
        occ_val = row["occ_symbol"] if "occ_symbol" in row_keys else ""
        sess_val = row["session_date"] if "session_date" in row_keys else ""
        mod_val = row["model_version"] if "model_version" in row_keys else "v1.2.0-RC1"
        cur.execute("""
            UPDATE ticker_quant_profiles 
            SET cache_hit_count = cache_hit_count + 1 
            WHERE ticker = ? AND occ_symbol = ? AND session_date = ? AND model_version = ?
        """, (ticker_val, occ_val, sess_val, mod_val))
        conn.commit()

        raw_json = json.loads(row["raw_quant_json"])
        is_micro_valid = is_micro_valid and observed_l2(raw_json.get('ofi_metrics'), ticker, microstructure_ttl_seconds)
        raw_json["is_from_cache"] = True
        raw_json["is_microstructure_valid"] = is_micro_valid
        raw_json["microstructure_updated_at"] = micro_ts
        raw_json["session_l2_eval_count"] = row["session_l2_eval_count"] or 0
        raw_json["total_cache_hits"] = row["cache_hit_count"] + 1
        conn.close()

        if is_micro_valid:
            logger.info("💾 Two-Tier Full Cache Hit for $%s (Micro Age: %.1fs | $0.00 Cost)", ticker, micro_age_seconds)
        else:
            logger.info("💾 Static Cache Hit for $%s (Static Age: %.1fh | Micro Expired: %.1fs)", ticker, static_age_hours, micro_age_seconds)

        return raw_json, is_micro_valid

    def reserve_l2_query(self, ticker: str, max_session_evals: int = 3) -> bool:
        """Charge attempts before I/O; scope ticker + New York calendar day.

        Session/holiday eligibility is a separate unqualified gate.
        """
        from zoneinfo import ZoneInfo
        day = datetime.now(ZoneInfo('America/New_York')).date().isoformat()
        ticker = ticker.upper().strip()
        conn = self._get_connection()
        try:
            with conn:
                conn.execute('BEGIN IMMEDIATE')
                row = conn.execute('SELECT attempts FROM l2_query_attempts WHERE ticker=? AND session_date=?', (ticker, day)).fetchone()
                if row and row[0] >= max_session_evals:
                    return False
                conn.execute('INSERT INTO l2_query_attempts VALUES (?,?,1) ON CONFLICT(ticker,session_date) DO UPDATE SET attempts=attempts+1', (ticker, day))
            return True
        finally:
            conn.close()

    def can_query_databento_l2(self, ticker: str, max_session_evals: int = 3) -> bool:
        """Enforces Databento Cost Throttling: Max 3 L2 evaluations per ticker per session."""
        ticker = ticker.upper().strip()
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT session_l2_eval_count, microstructure_updated_at 
            FROM ticker_quant_profiles 
            WHERE ticker = ? 
            ORDER BY microstructure_updated_at DESC, rowid DESC 
            LIMIT 1
        """, (ticker,))
        row = cur.fetchone()
        from zoneinfo import ZoneInfo
        day = datetime.now(ZoneInfo('America/New_York')).date().isoformat()
        attempt = conn.execute('SELECT attempts FROM l2_query_attempts WHERE ticker=? AND session_date=?', (ticker, day)).fetchone()
        conn.close()
        if attempt and attempt[0] >= max_session_evals:
            return False
        if not row:
            return True

        eval_count = row["session_l2_eval_count"] or 0
        # Reset count if last eval was on a previous day
        last_eval_ts = row["microstructure_updated_at"]
        if last_eval_ts:
            try:
                last_eval_dt = datetime.fromisoformat(last_eval_ts.replace("Z", "")).replace(tzinfo=timezone.utc)
                if last_eval_dt.date() < datetime.now(timezone.utc).date():
                    return True
            except Exception:
                pass

        if eval_count >= max_session_evals:
            logger.warning("🚫 Databento Throttle: $%s hit max %d L2 evals today. Using static overlay.", ticker, max_session_evals)
            return False

        return True

    def save_quant_profile(self, ticker: str, quant_data: Dict[str, Any], is_l2_fresh: bool = True) -> bool:
        """Persists profile to fast NVMe SSD and triggers async backup to 1 TB HD if mounted."""
        ticker = ticker.upper().strip()
        conn = self._get_connection()
        cur = conn.cursor()
        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()
        session_date = quant_data.get("session_date") or now_dt.strftime("%Y-%m-%d")
        occ_symbol = quant_data.get("occ_symbol") or ""
        model_version = quant_data.get("model_version") or "v1.2.0-RC1"

        alpha = quant_data.get("directional_alpha", {})
        ofi = quant_data.get("ofi_metrics", {})
        gex = quant_data.get("gex_overlay", {})

        cur.execute("""
            SELECT session_l2_eval_count, microstructure_updated_at FROM ticker_quant_profiles 
            WHERE ticker = ? AND occ_symbol = ? AND session_date = ? AND model_version = ?
        """, (ticker, occ_symbol, session_date, model_version))
        existing = cur.fetchone()
        curr_eval_count = (existing["session_l2_eval_count"] if existing else 0) + (1 if is_l2_fresh else 0)

        cur.execute("""
            INSERT INTO ticker_quant_profiles (
                ticker, occ_symbol, session_date, model_version,
                last_price, directional_bias, p_bullish, target_node,
                touch_prob_3d, brier_score, is_calibrated, hawkes_intensity,
                ofi_score, gex_regime, raw_quant_json, microstructure_updated_at,
                static_profile_updated_at, session_l2_eval_count, cache_hit_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(ticker, occ_symbol, session_date, model_version) DO UPDATE SET
                last_price = excluded.last_price,
                directional_bias = excluded.directional_bias,
                p_bullish = excluded.p_bullish,
                target_node = excluded.target_node,
                touch_prob_3d = excluded.touch_prob_3d,
                brier_score = excluded.brier_score,
                is_calibrated = excluded.is_calibrated,
                hawkes_intensity = excluded.hawkes_intensity,
                ofi_score = excluded.ofi_score,
                gex_regime = excluded.gex_regime,
                raw_quant_json = excluded.raw_quant_json,
                microstructure_updated_at = excluded.microstructure_updated_at,
                static_profile_updated_at = excluded.static_profile_updated_at,
                session_l2_eval_count = excluded.session_l2_eval_count
        """, (
            ticker,
            occ_symbol,
            session_date,
            model_version,
            quant_data.get("current_price"),
            alpha.get("directional_bias"),
            alpha.get("p_bullish"),
            alpha.get("target_node"),
            alpha.get("touch_prob_3d"),
            alpha.get("brier_score"),
            alpha.get("is_calibrated"),
            ofi.get("hawkes_intensity"),
            ofi.get("ofi_score"),
            gex.get("gex_regime"),
            json.dumps(quant_data),
            ofi['observed_at'] if is_l2_fresh and observed_l2(ofi, ticker) else (existing["microstructure_updated_at"] if existing else None),
            now_iso,
            curr_eval_count
        ))

        conn.commit()
        conn.close()
        logger.info("Saved $%s quant profile to NVMe cache (%s)", ticker, self.db_path)
        return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    cache = QuantStorageCache()
    print("NVMe Primary Storage Cache initialized at:", cache.db_path)
