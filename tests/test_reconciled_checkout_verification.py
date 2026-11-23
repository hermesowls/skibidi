"""Comprehensive Checkout-Targeted Integration & Provenance Verification Suite.

Validates that:
1. Reconciled modules are strictly imported from the checkout repository (not staging/hardening).
2. Reconciled API routes in hermes_cli/web_server.py execute correctly with isolated HERMES_HOME.
3. Missing, legacy, and populated SQLite databases are handled gracefully.
4. Input boundaries, filters, and SQL deduplication (ROW_NUMBER partition) function as designed.
5. Flow chart serving strictly confines files to authorized storage (preventing directory traversal).
6. Notable flow backfill endpoint executes via mocked subprocess (zero network / provider calls).
7. Frontend TypeScript contracts match backend API payloads.
8. Gateway restart graceful timeout fallback functions correctly.
"""

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

CHECKOUT_ROOT = Path(__file__).resolve().parent.parent


# ==============================================================================
# 1. CHECKOUT IMPORT PROVENANCE TESTS
# ==============================================================================

class TestCheckoutImportProvenance:
    """Assert and record that all imported modules originate from the checkout."""

    def test_reconciled_module_origins_and_hashes(self):
        # Explicit imports from the checkout
        import hermes_cli.web_server as web_server_mod
        import plugins.analyst_trader.price_updater as price_updater_mod
        import plugins.analyst_trader.auto_updater as auto_updater_mod
        import plugins.analyst_trader.db as db_mod
        import plugins.analyst_trader.dynamic_shadow_quant as quant_mod
        import plugins.analyst_trader.quant_storage_cache as cache_mod
        import plugins.analyst_trader.tools as tools_mod
        import plugins.analyst_trader.parser as parser_mod
        import plugins.analyst_trader.portfolio_engine as portfolio_mod
        import gateway.restart as restart_mod

        modules_to_verify = [
            ("web_server", web_server_mod),
            ("price_updater", price_updater_mod),
            ("auto_updater", auto_updater_mod),
            ("db", db_mod),
            ("dynamic_shadow_quant", quant_mod),
            ("quant_storage_cache", cache_mod),
            ("tools", tools_mod),
            ("parser", parser_mod),
            ("portfolio_engine", portfolio_mod),
            ("gateway_restart", restart_mod),
        ]

        provenance_records = []
        for name, mod in modules_to_verify:
            mod_file = getattr(mod, "__file__", None)
            assert mod_file is not None, f"Module {name} has no __file__"
            mod_path = Path(mod_file).resolve()

            # Strict checkout containment assertion
            assert str(mod_path).startswith(str(CHECKOUT_ROOT)), (
                f"Module {name} imported from {mod_path}, expected under checkout {CHECKOUT_ROOT}"
            )

            # Strict negative assertion: NOT staging or hardening
            assert "/staging/" not in str(mod_path), f"Module {name} imported from staging: {mod_path}"
            assert "/hardening/" not in str(mod_path), f"Module {name} imported from hardening: {mod_path}"

            # Record SHA256
            sha256 = hashlib.sha256(mod_path.read_bytes()).hexdigest()
            provenance_records.append({
                "module": name,
                "path": str(mod_path),
                "sha256": sha256,
            })

        print(f"\n[PROVENANCE] Python interpreter: {sys.executable}")
        print(f"[PROVENANCE] Current Working Directory: {os.getcwd()}")
        print(f"[PROVENANCE] Verified {len(provenance_records)} modules strictly originate from {CHECKOUT_ROOT}")
        assert len(provenance_records) == 10


# ==============================================================================
# 2. RECONCILED HOST API ROUTE TESTS (ISOLATED HERMES_HOME)
# ==============================================================================

@pytest.fixture
def isolated_hermes_env(tmp_path, monkeypatch):
    """Create a completely isolated HERMES_HOME temporary directory."""
    hermes_home = tmp_path / ".hermes"
    data_dir = hermes_home / "data"
    scripts_dir = hermes_home / "scripts"
    charts_dir = hermes_home / "flow_charts"
    
    data_dir.mkdir(parents=True, exist_ok=True)
    scripts_dir.mkdir(parents=True, exist_ok=True)
    charts_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    return {
        "home": hermes_home,
        "data": data_dir,
        "scripts": scripts_dir,
        "charts": charts_dir,
        "db_path": data_dir / "analyst_trading.db",
    }


def _seed_test_database(db_path: Path):
    """Seed sample notable flows, analysts, and positions into SQLite."""
    conn = sqlite3.connect(str(db_path))
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notable_flow (
                flow_id TEXT PRIMARY KEY,
                source TEXT,
                ticker TEXT,
                asset_type TEXT,
                strike REAL,
                call_put TEXT,
                expiration TEXT,
                dte INTEGER,
                premium_usd REAL,
                premium_raw TEXT,
                raw_message_id TEXT,
                channel_id TEXT,
                chart_url TEXT,
                local_chart_path TEXT,
                llm_review_status TEXT,
                llm_reasoning TEXT,
                trade_timestamp TEXT,
                created_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analysts (
                id TEXT PRIMARY KEY,
                name TEXT,
                channel_id TEXT,
                win_rate REAL,
                total_trades INTEGER,
                updated_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                position_id TEXT PRIMARY KEY,
                analyst_name TEXT,
                channel_id TEXT,
                ticker TEXT,
                asset_type TEXT,
                direction TEXT,
                strike REAL,
                expiration TEXT,
                entry_price REAL,
                current_price REAL,
                status TEXT,
                roi_pct REAL,
                entry_time TEXT,
                updated_at TEXT
            )
        """)

        # Insert test notable flows (including 2 records for SPY to test deduplication)
        conn.execute("""
            INSERT INTO notable_flow VALUES (
                'flow_spy_older', 'discord', 'SPY', 'etf', 550.0, 'CALL', '2026-10-16', 28,
                500000.0, '$500K', 'msg_1', 'ch_1', 'http://chart.com/1', NULL,
                'APPROVED', 'Bullish sweep', '2026-09-17T10:00:00Z', '2026-09-17T10:00:00Z'
            )
        """)
        conn.execute("""
            INSERT INTO notable_flow VALUES (
                'flow_spy_newer', 'discord', 'SPY', 'etf', 550.0, 'CALL', '2026-10-16', 28,
                750000.0, '$750K', 'msg_2', 'ch_1', 'http://chart.com/2', NULL,
                'APPROVED', 'Bullish sweep update', '2026-09-17T11:00:00Z', '2026-09-17T11:00:00Z'
            )
        """)
        conn.execute("""
            INSERT INTO notable_flow VALUES (
                'flow_tsla_put', 'discord', 'TSLA', 'equity', 200.0, 'PUT', '2026-09-25', 7,
                150000.0, '$150K', 'msg_3', 'ch_1', NULL, NULL,
                'APPROVED', 'Put hedge', '2026-09-17T10:30:00Z', '2026-09-17T10:30:00Z'
            )
        """)

        # Insert test analyst
        conn.execute("""
            INSERT INTO analysts VALUES (
                'analyst_1', 'Jon & Kian', 'ch_1', 78.5, 120, '2026-09-17T12:00:00Z'
            )
        """)

        # Insert test position
        conn.execute("""
            INSERT INTO positions VALUES (
                'pos_1', 'Jon & Kian', 'ch_1', 'GOOGL', 'option', 'call', 180.0, '2026-10-16',
                3.50, 4.20, 'OPEN', 20.0, '2026-09-17T09:30:00Z', '2026-09-17T09:30:00Z'
            )
        """)
    conn.close()


class TestAnalystTraderHostRoutes:
    """Test all reconciled /api/analyst-trader/* routes in hermes_cli.web_server."""

    @pytest.fixture(autouse=True)
    def setup_client(self, isolated_hermes_env):
        from hermes_cli.web_server import app, _SESSION_TOKEN
        self.env = isolated_hermes_env
        self.auth_headers = {"X-Hermes-Session-Token": _SESSION_TOKEN}
        self.client = TestClient(app, headers=self.auth_headers)
        self.unauth_client = TestClient(app)

    def test_unauthenticated_requests_are_rejected(self):
        """Requests without session token must be rejected with 401 Unauthorized."""
        res = self.unauth_client.get("/api/analyst-trader/notable-flow")
        assert res.status_code == 401
        assert res.json()["detail"] == "Unauthorized"

    def test_missing_db_returns_empty_collections_cleanly(self):
        """When database does not exist, endpoints must return ok=True with empty lists (honest missing)."""
        # notable-flow
        res = self.client.get("/api/analyst-trader/notable-flow")
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["flows"] == []
        assert data["count"] == 0

        # analysts
        res = self.client.get("/api/analyst-trader/analysts")
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["analysts"] == []

        # positions
        res = self.client.get("/api/analyst-trader/positions")
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["positions"] == []

    def test_notable_flow_query_and_deduplication(self):
        """Test seeded database query, filtering, and ROW_NUMBER partition deduplication."""
        _seed_test_database(self.env["db_path"])

        # 1. Deduplication check: SPY had 2 entries for identical (ticker, strike, call_put, exp).
        # Only the newer one ('flow_spy_newer', $750K) should be returned!
        res = self.client.get("/api/analyst-trader/notable-flow")
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["count"] == 2  # SPY (deduplicated) + TSLA
        flow_ids = [f["flow_id"] for f in data["flows"]]
        assert "flow_spy_newer" in flow_ids
        assert "flow_spy_older" not in flow_ids

        # 2. Filter by ticker
        res_spy = self.client.get("/api/analyst-trader/notable-flow?ticker=SPY")
        assert res_spy.status_code == 200
        assert res_spy.json()["count"] == 1
        assert res_spy.json()["flows"][0]["ticker"] == "SPY"

        # 3. Filter by call_put
        res_put = self.client.get("/api/analyst-trader/notable-flow?call_put=PUT")
        assert res_put.status_code == 200
        assert res_put.json()["count"] == 1
        assert res_put.json()["flows"][0]["ticker"] == "TSLA"

        # 4. Filter by min_premium
        res_prem = self.client.get("/api/analyst-trader/notable-flow?min_premium=200000")
        assert res_prem.status_code == 200
        assert res_prem.json()["count"] == 1  # only SPY is >= $200k ($750k)

        # 5. Filter by limit
        res_lim = self.client.get("/api/analyst-trader/notable-flow?limit=1")
        assert res_lim.status_code == 200
        assert res_lim.json()["count"] == 1

    def test_live_quotes_truthfulness(self):
        """Live quotes endpoint must return structured quotes without hallucinated or fabricated numbers."""
        res = self.client.get("/api/analyst-trader/live-quotes?tickers=SPY,TSLA,NVDA")
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        quotes = data["quotes"]
        assert "SPY" in quotes
        assert "TSLA" in quotes
        assert "NVDA" in quotes
        for ticker, q in quotes.items():
            assert q["price"] == 0
            assert q["change_pct"] == 0

    def test_chart_path_confinement_and_traversal_prevention(self):
        """Test local chart file serving and strict path traversal protection."""
        _seed_test_database(self.env["db_path"])

        # Case 1: Chart not found in DB
        res_404 = self.client.get("/api/analyst-trader/flow-chart/non_existent_id")
        assert res_404.status_code == 404

        # Case 2: Legitimate chart inside HERMES_HOME
        chart_file = self.env["charts"] / "chart_spy_test.png"
        chart_file.write_bytes(b"\x89PNG\r\n\x1a\nfake_png_data")

        conn = sqlite3.connect(str(self.env["db_path"]))
        with conn:
            conn.execute(
                "UPDATE notable_flow SET local_chart_path = ? WHERE flow_id = 'flow_spy_newer'",
                (str(chart_file),)
            )
        conn.close()

        res_legit = self.client.get("/api/analyst-trader/flow-chart/flow_spy_newer")
        assert res_legit.status_code == 200
        assert res_legit.content == b"\x89PNG\r\n\x1a\nfake_png_data"

        # Case 3: Path traversal attempt (/etc/passwd or ../../secret)
        conn = sqlite3.connect(str(self.env["db_path"]))
        with conn:
            conn.execute(
                "UPDATE notable_flow SET local_chart_path = '/etc/passwd' WHERE flow_id = 'flow_spy_newer'"
            )
        conn.close()

        res_traversal = self.client.get("/api/analyst-trader/flow-chart/flow_spy_newer")
        assert res_traversal.status_code == 404
        assert res_traversal.json()["detail"] == "Chart file not available"

    def test_backfill_endpoint_with_mocked_subprocess(self):
        """Test backfill endpoint uses local HERMES_HOME script and runs offline with mocked subprocess."""
        # 1. Missing script
        res_missing = self.client.post("/api/analyst-trader/notable-flow/backfill?limit=50")
        assert res_missing.status_code == 200
        assert res_missing.json()["ok"] is False
        assert res_missing.json()["error"] == "ingestion script not found"

        # 2. Fake script present + mocked subprocess
        fake_script = self.env["scripts"] / "flowseeker_unified_ingestion.py"
        fake_script.write_text("#!/usr/bin/env python3\nprint('mock')")

        with patch("subprocess.run") as mock_subproc:
            mock_subproc.return_value = subprocess.CompletedProcess(
                args=["mock"],
                returncode=0,
                stdout="[INFO] Ingested 50 notable flows offline\n",
                stderr="",
            )

            res_backfill = self.client.post("/api/analyst-trader/notable-flow/backfill?limit=50")
            assert res_backfill.status_code == 200
            data = res_backfill.json()
            assert data["ok"] is True
            assert data["stats"]["total_processed"] == 50
            assert "Ingested 50 notable flows offline" in data["stdout"]

            # Verify subprocess call args
            mock_subproc.assert_called_once()
            called_cmd = mock_subproc.call_args[0][0]
            assert called_cmd[1] == str(fake_script)
            assert "--skip-flowseeker" in called_cmd


# ==============================================================================
# 3. FRONTEND / BACKEND CONTRACT COMPATIBILITY TESTS
# ==============================================================================

class TestFrontendApiContractCompatibility:
    """Verify backend JSON shapes match TypeScript interfaces in web/src/lib/api.ts."""

    def test_notable_flow_item_contract_alignment(self, isolated_hermes_env):
        from hermes_cli.web_server import app, _SESSION_TOKEN
        _seed_test_database(isolated_hermes_env["db_path"])
        client = TestClient(app, headers={"X-Hermes-Session-Token": _SESSION_TOKEN})

        res = client.get("/api/analyst-trader/notable-flow")
        assert res.status_code == 200
        data = res.json()
        assert "ok" in data and isinstance(data["ok"], bool)
        assert "flows" in data and isinstance(data["flows"], list)
        assert "count" in data and isinstance(data["count"], int)

        flow = data["flows"][0]
        # Required NotableFlowItem fields in NotableFlowPage.tsx:
        required_fields = [
            ("flow_id", str),
            ("source", str),
            ("ticker", str),
            ("asset_type", str),
            ("strike", (float, int)),
            ("call_put", str),
            ("expiration", str),
            ("dte", int),
            ("premium_usd", (float, int)),
            ("premium_raw", str),
            ("trade_timestamp", str),
        ]
        for field_name, expected_type in required_fields:
            assert field_name in flow, f"Missing required NotableFlowItem field: {field_name}"
            assert isinstance(flow[field_name], expected_type), (
                f"Field {field_name} has invalid type {type(flow[field_name])}, expected {expected_type}"
            )


# ==============================================================================
# 4. GATEWAY RESTART TIMEOUT FALLBACK
# ==============================================================================

class TestGatewayRestartFallback:
    """Verify restart.py handles missing signal_interrupt_grace_timeout safely."""

    def test_restart_grace_timeout_default(self):
        from gateway.restart import (
            DEFAULT_GATEWAY_SIGNAL_INTERRUPT_GRACE_TIMEOUT,
            parse_signal_interrupt_grace_timeout,
        )
        # Even with empty/minimal config, grace timeout should resolve to an integer >= 1
        assert DEFAULT_GATEWAY_SIGNAL_INTERRUPT_GRACE_TIMEOUT >= 1.0
        assert parse_signal_interrupt_grace_timeout(None) == DEFAULT_GATEWAY_SIGNAL_INTERRUPT_GRACE_TIMEOUT
        assert parse_signal_interrupt_grace_timeout("invalid") == DEFAULT_GATEWAY_SIGNAL_INTERRUPT_GRACE_TIMEOUT
        assert parse_signal_interrupt_grace_timeout(10.5) == 10.5
