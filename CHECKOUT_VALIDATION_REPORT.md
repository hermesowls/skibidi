# Reconciled Checkout Automated Pipeline Report

**Timestamp**: 2026-09-17 22:30:10  
**Source Directory**: `/private/tmp/broken_handoff`  
**Target Checkout**: `/Users/admin/repos/hermes-agent`  
**Python Interpreter**: `/Users/admin/repos/hermes-agent/venv/bin/python3`  
**Overall Status**: 🔴 VALIDATION FAILED  

## 1. Synchronized Files

| Status | Relative Path | Source SHA256 | Destination SHA256 |
| :--- | :--- | :--- | :--- |
| **NEW** | `plugins/analyst_trader/broken_syntax.py` | `696f17b0367a...` | `...` |

## 2. Validation Test Results

| Step | Target | Result |
| :--- | :--- | :--- |
| **Syntax Compilation** | `plugins/analyst_trader/*.py` | FAIL |
| **Integration Tests** | `tests/test_reconciled_checkout_verification.py` | PASS (9/9) |
| **Type Checking** | Pyright (Diagnostics Enabled) | PASS (0 errors) |
| **Frontend Types** | `web/` (`tsc --noEmit`) | PASS (0 errors) |
| **Code Linter** | Ruff | PASS |

## 3. Safety Invariants Maintained

- **Crons**: Preserved in paused state (`~/.hermes/cron/jobs.json`).
- **Live Providers**: Zero real Unusual Whales or broker requests made.
- **Untracked / Dirty Files**: Preserved without destructive overwrite.