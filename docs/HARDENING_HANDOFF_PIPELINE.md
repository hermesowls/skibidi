# Hermes Hardening & Architecture Automated CI/CD Pipeline

This document defines the mutual contract, automated CI/CD pipeline, and system service between external Hermes agents performing hardening/architectural work and the active development workspace (`/Users/admin/repos/hermes-agent`).

---

## 1. Agreed Handoff Contract & Directory Layout

External Hermes agents dropping hardening or architectural improvements must output files to one of two locations:

1. **Canonical Handoff Directory** (Default):  
   `~/.hermes/hardening/handoff/`

2. **Timestamped Directory with Symlink**:  
   `~/.hermes/hardening/<YYYYMMDD_HHMMSS>/`  
   with symlink: `~/.hermes/hardening/latest -> <timestamp_dir>`

### Standard Drop Layout
```text
~/.hermes/hardening/handoff/
├── HANDOFF.md              # Context, change summary, agent metadata
├── repo/                   # Target files for the active checkout (/Users/admin/repos/hermes-agent)
│   ├── plugins/
│   ├── hermes_cli/
│   ├── web/
│   └── tests/
└── scripts/                # Standalone runtime scripts for ~/.hermes/scripts/
```

---

## 2. Mutual Pipeline Commands

Both the user and agents can trigger, inspect, and manage the pipeline using the mutual script:

```bash
# 1. Preview changes without modifying files (Dry Run)
./scripts/reconcile --dry-run

# 2. Synchronize and run comprehensive checkout-targeted validation
./scripts/reconcile

# 3. Synchronize, validate, and auto-commit on green
./scripts/reconcile --auto-commit

# 4. Synchronize from an explicit historical drop
./scripts/reconcile --source ~/.hermes/hardening/20260914_230002

# 5. Run in continuous watcher mode with auto-commit
./scripts/reconcile --watch --auto-commit

# 6. Background Service Management (macOS launchd)
./scripts/reconcile --install-service     # Installs & starts background daemon
./scripts/reconcile --service-status      # Inspects running status and logs
./scripts/reconcile --uninstall-service   # Stops & removes background daemon
```

---

## 3. Automated 5-Tier Validation Gate

Every synchronization runs a 5-tier checkout-targeted offline test suite. Changes are only certified green when all 5 tiers pass:

1. **Bytecode Compilation**: `python3 -m compileall -q` across all modules in `plugins/analyst_trader/` and all modified repository files to detect syntax regressions.
2. **Checkout Integration Pytest Suite**: `tests/test_reconciled_checkout_verification.py`
   - Real module provenance verification (asserts imports originate strictly from the active checkout).
   - Starlette host route integration under isolated `HERMES_HOME`.
   - Security perimeter checks (401 token authentication gate, chart directory traversal containment).
   - Ingestion deduplication SQL logic.
   - Offline mocked backfill (zero live API calls).
   - Frontend TypeScript contract alignment (`NotableFlowItem`).
3. **Static Type Checking**: Pyright with diagnostics explicitly enabled (`0` type errors allowed).
4. **Frontend TypeScript Check**: `cd web && npx tsc --noEmit` (`0` type errors allowed).
5. **Code Quality Linting**: `ruff check` across modified Python modules.

---

## 4. Key Architectural Safeguards

### Auto-Commit on Green (Smart Branch Protection)
- When all 5 validation tiers pass and `--auto-commit` is active:
  - If currently on `main`, the pipeline automatically creates an isolated branch `hardening/auto-<YYYYMMDD_HHMMSS>` to protect `main`.
  - If on a feature or reconciliation branch (e.g. `reconcile/hardening-pilot-reconciliation`), it commits directly.
  - Commits include a structured message detailing the test breakdown and list of synchronized files.

### Atomic Rollback & Failure Quarantine
- If ANY of the 5 validation checks fail:
  - The pipeline immediately rolls back the checkout: restores modified files from `.pre_sync_backup/` and deletes new files.
  - The active workspace remains 100% clean and undamaged.
  - The failing drop details and error logs are quarantined into `~/.hermes/hardening/quarantine/<timestamp>/FAILURE_LOG.md`.

### Multi-Channel Notifications (Discord Excluded)
- On build completion, notifications are dispatched to:
  1. **macOS Notification Center**: Native desktop banner via `osascript` with sound (`Glass` on success, `Basso` on failure).
  2. **Telegram**: Formatted status message to `TELEGRAM_ALLOWED_USERS` via `TELEGRAM_BOT_TOKEN`.
  - *Note: Discord notifications are explicitly excluded.*

### Settle-Time Debouncing
- The background watcher checks filesystem modification settle times (2s debounce) before triggering, ensuring multi-file drops are completely written before sync begins.

---

## 5. Machine-Readable & Human-Readable Reports

After every reconciliation run, the pipeline writes:
- **Human-Readable Report**: [`CHECKOUT_VALIDATION_REPORT.md`](file:///Users/admin/repos/hermes-agent/CHECKOUT_VALIDATION_REPORT.md) in the checkout root.
- **Machine-Readable Status**: `~/.hermes/hardening/latest_validation.json` containing:
  ```json
  {
    "timestamp": "2026-09-17 22:27:38",
    "source_dir": "/Users/admin/.hermes/hardening/handoff",
    "target_checkout": "/Users/admin/repos/hermes-agent",
    "all_passed": true,
    "results": {
      "py_compile": { "pass": true },
      "pytest": { "pass": true },
      "pyright": { "pass": true },
      "tsc": { "pass": true },
      "ruff": { "pass": true }
    },
    "synchronized_files": [...]
  }
  ```

---

## 6. Safety Invariants & Protections

- **Crons Kept Paused**: All crons in `~/.hermes/cron/jobs.json` remain paused (`enabled: false`).
- **Zero Live Calls**: No live provider API requests (Unusual Whales, Databento, Alpaca) are triggered.
- **Pre-Sync Safety Backup**: Any modified file in the destination checkout is automatically backed up to `.pre_sync_backup/<timestamp>/` before being overwritten.
- **No Diagnostic Suppression**: Dropped configurations with `preset = "off"` or removing type checking are blocked.
- **VCS & Cache Hygiene**: `.git`, `__pycache__`, `.pytest_cache`, and `node_modules` are strictly excluded from file syncing.
