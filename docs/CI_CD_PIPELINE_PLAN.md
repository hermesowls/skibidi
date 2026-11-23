# Automated Agent CI/CD Pipeline Implementation Plan

This plan details the full implementation of the **3 requested capabilities** (Auto-Commit on Green, Notifications, Background `launchd` Service) along with **5 key architectural improvements** to make the pipeline resilient, production-ready, and non-destructive.

---

## 5 Proposed Architectural Improvements

Before executing the changes, here are the 5 architectural improvements to elevate this pipeline from a basic script to a bulletproof CI/CD engine:

### 1. Automatic Rollback & Quarantine on Failure (Atomic Transactions)
- **Problem**: If the external Hermes agent drops code with a subtle syntax error, failing test, or type regression, copying it into the active checkout leaves your working directory dirty and broken.
- **Improvement**: If any of the 5 validation checks fail, the reconciler will **immediately restore the checkout from `.pre_sync_backup`**, leaving the checkout 100% clean. It then moves the failing drop to `~/.hermes/hardening/quarantine/<timestamp>/` along with `FAILURE_LOG.md` detailing the exact error, preventing broken code from ever contaminating the workspace.

### 2. Settle-Time Debouncing & Atomic Drop Sentinel
- **Problem**: When an external agent writes 20+ files into `~/.hermes/hardening/handoff/`, the file-system watcher could fire on file #1 while files #2–20 are still being written, causing tests to run against an incomplete state.
- **Improvement**: Implement a **3-second settle-time debounce** (all writes must cease for 3s before trigger) AND check for an optional sentinel file `HANDOFF_READY` or completion of `HANDOFF.md`.

### 3. Smart Branch Protection (Branching vs. Direct Commit)
- **Problem**: Blindly committing to `main` can lead to unintended commits on your primary branch.
- **Improvement**:
  - If currently on `main`, the reconciler automatically creates an isolated branch: `hardening/auto-<YYYYMMDD_HHMMSS>`.
  - If currently on a feature or reconciliation branch (e.g. `reconcile/hardening-pilot-reconciliation`), it commits directly to that branch.
  - The commit message includes the validation results table, list of modified files, and attribution.

### 4. Multi-Channel Notification Router
- **Problem**: Terminal output is silent if running in the background.
- **Improvement**: The notification engine routes alerts across 3 tiers (using existing credentials in `~/.hermes/.env`):
  1. **macOS Notification Center** (native desktop banner via `osascript` with sound).
  2. **Discord Webhook** (rich green/red embed to `DISCORD_WEBHOOK_URL` with files changed and test status).
  3. **Telegram Bot** (formatted message to `TELEGRAM_ALLOWED_USERS` via `TELEGRAM_BOT_TOKEN`).

### 5. Built-in `launchd` Service Manager
- **Problem**: Managing background jobs manually with `nohup` or `tmux` is fragile across reboots.
- **Improvement**: Add native CLI commands directly into `./scripts/reconcile`:
  - `./scripts/reconcile --install-service` (installs `~/Library/LaunchAgents/ai.hermes.reconciler.plist` and starts it)
  - `./scripts/reconcile --service-status` (checks daemon PID, memory, and tails `~/.hermes/logs/reconciler.log`)
  - `./scripts/reconcile --uninstall-service` (stops daemon and removes plist cleanly)

---

## User Review & Decisions

> [!IMPORTANT]
> **Branching Decision**:
> When running auto-commit, if the checkout is currently on `main`, the recommended behavior is to create a new branch `hardening/auto-<timestamp>` to protect `main`. If you are on a feature or reconciliation branch (like `reconcile/hardening-pilot-reconciliation`), it commits directly to that branch.
>
> *(A `--force-main` flag will be available if you ever want direct-to-main commits).*

> [!NOTE]
> **Safety Invariants Maintained**:
> - All 14 crons in `~/.hermes/cron/jobs.json` remain paused (`enabled: false`).
> - Zero live provider API requests (mocked offline isolation).
> - All existing untracked/dirty files are backed up to `.pre_sync_backup/` before any sync.

---

## Proposed Code Changes

### Component: Pipeline Engine & Watcher

#### [MODIFY] [reconcile_hardening.py](file:///Users/admin/repos/hermes-agent/scripts/reconcile_hardening.py)
- **Auto-Commit Functionality**:
  - Add `git_commit_on_green(candidates, test_results)`:
    - Checks active branch; if `main`, creates `hardening/auto-<timestamp>`.
    - Stages only the synchronized files (`git add <files>`).
    - Commits with structured message and validation results summary.
- **Atomic Rollback on Failure**:
  - Add `rollback_sync(candidates, backup_dir)`:
    - If `not test_results["all_passed"]`, restores original files from `.pre_sync_backup`.
    - Quarantines the failing drop to `~/.hermes/hardening/quarantine/<timestamp>`.
- **Multi-Channel Notifier**:
  - Add `NotificationRouter`:
    - Reads `DISCORD_WEBHOOK_URL`, `TELEGRAM_BOT_TOKEN`, and `TELEGRAM_ALLOWED_USERS` from `~/.hermes/.env`.
    - Dispatches macOS desktop notification (`osascript`).
    - Dispatches Discord webhook embed (green if passed, red if failed).
    - Dispatches Telegram message if tokens are present.
- **Debounced Watcher**:
  - Add settle-time debouncing (wait 3s for filesystem writes to cease).
- **Service Management**:
  - Add `--install-service`, `--uninstall-service`, `--service-status` to manage `~/Library/LaunchAgents/ai.hermes.reconciler.plist`.

---

### Component: Service Configuration

#### [NEW] [ai.hermes.reconciler.plist](file:///Users/admin/repos/hermes-agent/scripts/ai.hermes.reconciler.plist)
- launchd property list configuring the reconciler watcher:
  - Label: `ai.hermes.reconciler`
  - Program: `/Users/admin/repos/hermes-agent/venv/bin/python3`
  - Arguments: `[..., "scripts/reconcile_hardening.py", "--watch", "--auto-commit"]`
  - Environment: `HERMES_HOME=/Users/admin/.hermes`, `PATH=...`
  - StandardOutPath: `~/.hermes/logs/reconciler.log`
  - StandardErrorPath: `~/.hermes/logs/reconciler.log`
  - RunAtLoad: true, KeepAlive: true

---

### Component: Documentation

#### [MODIFY] [HARDENING_HANDOFF_PIPELINE.md](file:///Users/admin/repos/hermes-agent/docs/HARDENING_HANDOFF_PIPELINE.md)
- Update documentation with the auto-commit, notification triggers, failure quarantine, and launchd management commands.

---

## Verification Plan

### Automated Tests
1. **Dry-Run Mode**:
   ```bash
   ./scripts/reconcile --dry-run
   ```
   Assert zero side-effects and all 5 verification tiers pass.

2. **Synthetic Handoff Test**:
   - Create a synthetic test drop in `~/.hermes/hardening/test_handoff/` with a clean non-breaking improvement.
   - Run `./scripts/reconcile --source ~/.hermes/hardening/test_handoff/ --auto-commit`.
   - Verify:
     - Files synced and backed up in `.pre_sync_backup/`.
     - 5 verification tiers pass.
     - Git commit created with structured log.
     - Notification triggered.
     - Working tree clean.

3. **Failure & Rollback Test**:
   - Introduce a deliberate syntax/type error into a dummy file in the test drop.
   - Run reconciler.
   - Verify:
     - Validation fails.
     - Auto-rollback restores checkout to 100% clean state.
     - Failing files moved to quarantine.
     - Error notification dispatched.

4. **Daemon Lifecycle Verification**:
   - Test `./scripts/reconcile --install-service`
   - Test `./scripts/reconcile --service-status`
   - Test `./scripts/reconcile --uninstall-service`
