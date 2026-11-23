#!/usr/bin/env python3
"""Hermes Hardening & Architecture Reconciler Pipeline.

Automates the handoff, safe synchronization, and checkout-targeted validation
between an external Hermes hardening agent and the active IDE checkout.

Usage:
    # Run sync and test against latest hardening handoff
    ./scripts/reconcile_hardening.py

    # Preview diffs without applying changes
    ./scripts/reconcile_hardening.py --dry-run

    # Target an explicit handoff directory
    ./scripts/reconcile_hardening.py --source ~/.hermes/hardening/20260914_230002

    # Watch mode: auto-reconcile whenever Hermes agent drops a new handoff
    ./scripts/reconcile_hardening.py --watch
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CHECKOUT_ROOT = Path(__file__).resolve().parent.parent


def get_hermes_home() -> Path:
    """Resolve HERMES_HOME from environment or default to ~/.hermes."""
    env_home = os.getenv("HERMES_HOME")
    if env_home:
        return Path(env_home).expanduser().resolve()
    return (Path.home() / ".hermes").resolve()


def load_hermes_env() -> None:
    """Load secrets and tokens from ~/.hermes/.env into os.environ if not already present."""
    env_file = get_hermes_home() / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip("'\"")
        if key not in os.environ:
            os.environ[key] = val


class Notifier:
    """Multi-channel notification dispatcher: macOS desktop + Telegram (Discord excluded)."""

    @staticmethod
    def notify_macos(title: str, message: str, success: bool = True):
        sound = "Glass" if success else "Basso"
        clean_title = title.replace('"', '\\"')
        clean_msg = message.replace('"', '\\"')
        cmd = [
            "osascript",
            "-e",
            f'display notification "{clean_msg}" with title "{clean_title}" sound name "{sound}"',
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=5)
        except Exception:
            pass

    @staticmethod
    def notify_telegram(title: str, message: str, success: bool = True):
        load_hermes_env()
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        allowed_users = os.getenv("TELEGRAM_ALLOWED_USERS", "")
        if not bot_token or not allowed_users:
            return

        import ssl
        try:
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

        icon = "🟢" if success else "🔴"
        text = f"{icon} *{title}*\n\n{message}"
        user_ids = [u.strip() for u in allowed_users.split(",") if u.strip()]

        for uid in user_ids:
            try:
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                payload = json.dumps({
                    "chat_id": uid,
                    "text": text,
                    "parse_mode": "Markdown",
                }).encode("utf-8")
                req = urllib.request.Request(
                    url, data=payload, headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=5, context=ctx):
                    pass
            except Exception as e:
                print(f"Telegram notify notice: {e}")

    @classmethod
    def dispatch(cls, title: str, message: str, success: bool = True):
        cls.notify_macos(title, message, success)
        cls.notify_telegram(title, message, success)
        # Note: Discord is explicitly excluded per user requirement


def find_latest_hardening_source(explicit_source: Optional[str] = None) -> Path:
    """Resolve the handoff directory."""
    if explicit_source:
        p = Path(explicit_source).expanduser().resolve()
        if not p.exists():
            raise FileNotFoundError(f"Specified hardening source does not exist: {p}")
        return p

    hermes_home = get_hermes_home()
    
    # 1. Check standard handoff directory
    standard_handoff = hermes_home / "hardening" / "handoff"
    if standard_handoff.exists() and any(standard_handoff.iterdir()):
        return standard_handoff

    # 2. Check standard latest symlink
    latest_link = hermes_home / "hardening" / "latest"
    if latest_link.exists():
        return latest_link.resolve()

    # 3. Scan for timestamped hardening directories
    hardening_root = hermes_home / "hardening"
    if hardening_root.exists():
        dirs = [d for d in hardening_root.iterdir() if d.is_dir() and d.name != ".pytest_cache"]
        if dirs:
            dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
            return dirs[0].resolve()

    raise FileNotFoundError(f"No hardening handoff found under {hardening_root}")


def compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    if not file_path.exists() or not file_path.is_file():
        return ""
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


class ReconcilePipeline:
    def __init__(self, source_dir: Path, dry_run: bool = False, auto_commit: bool = False):
        self.source_dir = source_dir
        self.dry_run = dry_run
        self.auto_commit = auto_commit
        self.checkout_root = CHECKOUT_ROOT
        self.runtime_root = get_hermes_home() / 'scripts'
        self.last_backup_root: Optional[Path] = None
        self.venv_python = self.checkout_root / "venv" / "bin" / "python3"
        if not self.venv_python.exists():
            self.venv_python = Path(sys.executable)

    def locate_staging_trees(self) -> Tuple[Optional[Path], Optional[Path]]:
        """Find repo and scripts staging subtrees inside the hardening directory."""
        # Standard layout: <source>/staging/repo/ and <source>/staging/scripts/
        # Or direct: <source>/repo/ and <source>/scripts/
        candidates_repo = [
            self.source_dir / "staging" / "repo",
            self.source_dir / "repo",
            self.source_dir / "staging" / "deployment-package" / "src",
        ]
        candidates_scripts = [
            self.source_dir / "staging" / "scripts",
            self.source_dir / "scripts",
        ]

        repo_tree = next((p for p in candidates_repo if p.exists() and p.is_dir()), None)
        scripts_tree = next((p for p in candidates_scripts if p.exists() and p.is_dir()), None)
        return repo_tree, scripts_tree

    IGNORED_NAMES = {
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".DS_Store",
        "node_modules",
        ".ruff_cache",
        ".mypy_cache",
        ".venv",
        "venv",
    }

    def collect_sync_candidates(self) -> List[Dict[str, Any]]:
        """Identify which files need to be synchronized and diff them against checkout."""
        if __package__:
            from scripts.reconcile_promotion import no_links, allowed_path
        else:
            from reconcile_promotion import no_links, allowed_path
        no_links(self.source_dir)
        repo_tree, scripts_tree = self.locate_staging_trees()
        for tree in (repo_tree, scripts_tree):
            if tree:
                no_links(tree)
        candidates = []

        if repo_tree:
            for src_file in repo_tree.rglob("*"):
                if not src_file.is_file():
                    continue
                if any(part in self.IGNORED_NAMES for part in src_file.parts) or src_file.name.endswith(".pyc"):
                    continue
                rel = src_file.relative_to(repo_tree)
                dest = self.checkout_root / rel
                allowed_path(src_file)
                allowed_path(dest)

                # Guard: Do not overwrite pyproject.toml / pyrefly.toml if it alters diagnostics or venv configs
                if rel.name in ("pyproject.toml", "pyrefly.toml"):
                    src_content = src_file.read_text(encoding="utf-8", errors="ignore")
                    if 'preset = "off"' in src_content or "preset = 'off'" in src_content:
                        continue
                    if dest.exists() and "[tool.pyright]" in dest.read_text(encoding="utf-8", errors="ignore"):
                        # Keep checkout's venv configuration intact
                        continue

                src_hash = compute_sha256(src_file)
                dest_hash = compute_sha256(dest)

                status = "UNCHANGED" if src_hash == dest_hash else ("NEW" if not dest.exists() else "MODIFIED")
                candidates.append({
                    "kind": "repo",
                    "rel_path": str(rel),
                    "src_path": src_file,
                    "dest_path": dest,
                    "src_hash": src_hash,
                    "dest_hash": dest_hash,
                    "status": status,
                })

        if scripts_tree:
            hermes_scripts = self.runtime_root
            for src_file in scripts_tree.rglob("*"):
                if not src_file.is_file():
                    continue
                if any(part in self.IGNORED_NAMES for part in src_file.parts) or src_file.name.endswith(".pyc"):
                    continue
                rel = src_file.relative_to(scripts_tree)
                dest = hermes_scripts / rel
                allowed_path(src_file)
                allowed_path(dest)

                src_hash = compute_sha256(src_file)
                dest_hash = compute_sha256(dest)

                status = "UNCHANGED" if src_hash == dest_hash else ("NEW" if not dest.exists() else "MODIFIED")
                candidates.append({
                    "kind": "scripts",
                    "rel_path": f"scripts/{rel}",
                    "src_path": src_file,
                    "dest_path": dest,
                    "src_hash": src_hash,
                    "dest_hash": dest_hash,
                    "status": status,
                })

        return candidates

    def apply_sync(self, candidates: List[Dict[str, Any]], *, approved_files=(), validator=None) -> int:
        """Preview, or validate a disposable candidate before scoped promotion.

        Approval keys are kind:rel_path. No inference from a green exit status,
        no implicit runtime scope, and no git/index operations.
        """
        if __package__:
            from scripts.reconcile_promotion import promote
        else:
            from reconcile_promotion import promote
        return promote(self, candidates, approved_files=approved_files, validator=validator)

    def rollback_sync(self, candidates: List[Dict[str, Any]], test_results: Dict[str, Any]) -> None:
        """Deprecated; scoped promotion owns its exception-safe rollback journal."""
        raise PermissionError('Legacy rollback/quarantine disabled; rollback is internal to scoped promotion')
        print("\n⏪ Rolling back synchronized files to keep checkout clean...")
        for item in candidates:
            if item["status"] == "MODIFIED" and self.last_backup_root and self.last_backup_root.exists():
                backup_file = self.last_backup_root / item["rel_path"]
                if backup_file.exists():
                    shutil.copy2(backup_file, item["dest_path"])
                    print(f"  [RESTORED] {item['rel_path']}")
            elif item["status"] == "NEW" and item["dest_path"].exists():
                item["dest_path"].unlink()
                print(f"  [REMOVED NEW] {item['rel_path']}")

        # Quarantine failing drop
        quarantine_dir = get_hermes_home() / "hardening" / "quarantine" / datetime.now().strftime("%Y%m%d_%H%M%S")
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        try:
            fail_lines = [
                "# Quarantine Report: Validation Failed",
                f"Source: {self.source_dir}",
                f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "\n## Test Failures:\n",
            ]
            for step, res in test_results.items():
                if isinstance(res, dict) and not res.get("pass", False):
                    fail_lines.append(f"### ❌ {step.upper()} Failure:")
                    if res.get("stdout"):
                        fail_lines.append(f"```\n{res['stdout'][-1500:]}\n```")
                    if res.get("stderr"):
                        fail_lines.append(f"```\n{res['stderr'][-1500:]}\n```")

            (quarantine_dir / "FAILURE_LOG.md").write_text("\n".join(fail_lines), encoding="utf-8")
            print(f"📦 Failing drop details quarantined to: {quarantine_dir}")
        except Exception as e:
            print(f"Quarantine log error: {e}")

    def git_commit_on_green(self, candidates: List[Dict[str, Any]], test_results: Dict[str, Any]) -> Optional[str]:
        """Deprecated: never stage, branch, or include unrelated staged work."""
        raise PermissionError('Autocommit is unsupported; independent review and manual commit required')

    def run_validation_suite(self, candidates: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Deprecated; destination-targeted validation is not candidate validation."""
        raise PermissionError('Legacy validation disabled; provide an offline candidate validator to apply_sync')
        results: Dict[str, Any] = {}
        py_exec = str(self.venv_python)

        print("\n🧪 Running Checkout-Targeted Validation Suite...")

        # 1. Byte-compile all Python files in plugins/analyst_trader/ and any modified files
        print("  ▶ 1. Python syntax & bytecode compilation check...")
        compile_targets = ["plugins/analyst_trader"]
        if candidates:
            for c in candidates:
                if c["kind"] == "repo" and c["rel_path"].endswith(".py") and c["status"] != "UNCHANGED":
                    if not c["rel_path"].startswith("plugins/analyst_trader"):
                        compile_targets.append(c["rel_path"])

        cmd_compile = [py_exec, "-m", "compileall", "-q"] + compile_targets
        res_compile = subprocess.run(cmd_compile, cwd=str(self.checkout_root), capture_output=True, text=True)
        results["py_compile"] = {
            "pass": res_compile.returncode == 0,
            "stdout": res_compile.stdout,
            "stderr": res_compile.stderr,
        }
        print(f"     Status: {'✅ PASS' if res_compile.returncode == 0 else '❌ FAIL'}")

        # 2. Reconciled Checkout Pytest Suite
        print("  ▶ 2. Reconciled checkout integration tests (pytest)...")
        cmd_pytest = [
            py_exec, "-m", "pytest",
            "tests/test_reconciled_checkout_verification.py",
            "-v",
        ]
        res_pytest = subprocess.run(cmd_pytest, cwd=str(self.checkout_root), capture_output=True, text=True)
        results["pytest"] = {
            "pass": res_pytest.returncode == 0,
            "stdout": res_pytest.stdout,
            "stderr": res_pytest.stderr,
        }
        print(f"     Status: {'✅ PASS (9/9)' if res_pytest.returncode == 0 else '❌ FAIL'}")

        # 3. Static Type Checking (Pyright with enabled diagnostic configuration)
        print("  ▶ 3. Static type checker (Pyright enabled diagnostics)...")
        cmd_pyright = [
            "npx", "-y", "pyright",
            "tests/test_reconciled_checkout_verification.py",
            "plugins/analyst_trader/price_updater.py",
            "plugins/analyst_trader/tools.py",
            "plugins/analyst_trader/position_tracker_db.py",
            "plugins/analyst_trader/databento_ofi_engine.py",
            "plugins/analyst_trader/quant_storage_cache.py",
        ]
        res_pyright = subprocess.run(cmd_pyright, cwd=str(self.checkout_root), capture_output=True, text=True)
        results["pyright"] = {
            "pass": res_pyright.returncode == 0,
            "stdout": res_pyright.stdout,
            "stderr": res_pyright.stderr,
        }
        print(f"     Status: {'✅ PASS (0 errors)' if res_pyright.returncode == 0 else '❌ FAIL'}")

        # 4. Frontend TypeScript Validation
        print("  ▶ 4. Frontend TypeScript compiler (tsc --noEmit)...")
        cmd_tsc = ["npx", "tsc", "--noEmit"]
        web_dir = self.checkout_root / "web"
        res_tsc = subprocess.run(cmd_tsc, cwd=str(web_dir), capture_output=True, text=True)
        results["tsc"] = {
            "pass": res_tsc.returncode == 0,
            "stdout": res_tsc.stdout,
            "stderr": res_tsc.stderr,
        }
        print(f"     Status: {'✅ PASS (0 errors)' if res_tsc.returncode == 0 else '❌ FAIL'}")

        # 5. Linter Check (Ruff)
        print("  ▶ 5. Code linter (Ruff)...")
        cmd_ruff = [
            py_exec, "-m", "ruff", "check",
            "tests/test_reconciled_checkout_verification.py",
            "plugins/analyst_trader/price_updater.py",
            "plugins/analyst_trader/tools.py",
            "plugins/analyst_trader/position_tracker_db.py",
            "plugins/analyst_trader/databento_ofi_engine.py",
            "plugins/analyst_trader/quant_storage_cache.py",
            "hermes_cli/web_server.py",
        ]
        res_ruff = subprocess.run(cmd_ruff, cwd=str(self.checkout_root), capture_output=True, text=True)
        results["ruff"] = {
            "pass": res_ruff.returncode == 0,
            "stdout": res_ruff.stdout,
            "stderr": res_ruff.stderr,
        }
        print(f"     Status: {'✅ PASS' if res_ruff.returncode == 0 else '❌ FAIL'}")

        all_passed = all(v["pass"] for v in results.values())
        results["all_passed"] = all_passed
        return results

    def generate_report(self, candidates: List[Dict[str, Any]], test_results: Dict[str, Any]) -> Path:
        """Deprecated; historical report claims are not current qualification."""
        raise PermissionError('Legacy report writes disabled; use the explicit scoped CLI result')
        report_path = self.checkout_root / "CHECKOUT_VALIDATION_REPORT.md"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines = [
            "# Reconciled Checkout Automated Pipeline Report",
            f"\n**Timestamp**: {now_str}  ",
            f"**Source Directory**: `{self.source_dir}`  ",
            f"**Target Checkout**: `{self.checkout_root}`  ",
            f"**Python Interpreter**: `{self.venv_python}`  ",
            f"**Overall Status**: {'🟢 ALL CHECKS PASSED' if test_results.get('all_passed') else '🔴 VALIDATION FAILED'}  \n",
            "## 1. Synchronized Files\n",
            "| Status | Relative Path | Source SHA256 | Destination SHA256 |",
            "| :--- | :--- | :--- | :--- |",
        ]

        for item in candidates:
            if item["status"] != "UNCHANGED":
                lines.append(
                    f"| **{item['status']}** | `{item['rel_path']}` | `{item['src_hash'][:12]}...` | `{item['dest_hash'][:12]}...` |"
                )

        lines.extend([
            "\n## 2. Validation Test Results\n",
            "| Step | Target | Result |",
            "| :--- | :--- | :--- |",
            f"| **Syntax Compilation** | `plugins/analyst_trader/*.py` | {'PASS' if test_results.get('py_compile', {}).get('pass') else 'FAIL'} |",
            f"| **Integration Tests** | `tests/test_reconciled_checkout_verification.py` | {'PASS (9/9)' if test_results.get('pytest', {}).get('pass') else 'FAIL'} |",
            f"| **Type Checking** | Pyright (Diagnostics Enabled) | {'PASS (0 errors)' if test_results.get('pyright', {}).get('pass') else 'FAIL'} |",
            f"| **Frontend Types** | `web/` (`tsc --noEmit`) | {'PASS (0 errors)' if test_results.get('tsc', {}).get('pass') else 'FAIL'} |",
            f"| **Code Linter** | Ruff | {'PASS' if test_results.get('ruff', {}).get('pass') else 'FAIL'} |",
            "\n## 3. Safety Invariants Maintained\n",
            "- **Crons**: Preserved in paused state (`~/.hermes/cron/jobs.json`).",
            "- **Live Providers**: Zero real Unusual Whales or broker requests made.",
            "- **Untracked / Dirty Files**: Preserved without destructive overwrite.",
        ])

        report_path.write_text("\n".join(lines), encoding="utf-8")

        # Also write machine-readable JSON status for external agents and CLI tools
        try:
            json_path = get_hermes_home() / "hardening" / "latest_validation.json"
            json_path.parent.mkdir(parents=True, exist_ok=True)
            summary_data = {
                "timestamp": now_str,
                "source_dir": str(self.source_dir),
                "target_checkout": str(self.checkout_root),
                "all_passed": test_results.get("all_passed", False),
                "results": {
                    k: {"pass": v.get("pass", False)}
                    for k, v in test_results.items()
                    if isinstance(v, dict)
                },
                "synchronized_files": [
                    {"status": c["status"], "rel_path": c["rel_path"]}
                    for c in candidates if c["status"] != "UNCHANGED"
                ],
            }
            json_path.write_text(json.dumps(summary_data, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"Warning: could not write JSON status: {e}")

        return report_path


def debounce_wait(source_dir: Path, settle_seconds: int = 2) -> None:
    """Ensure file-writing by an external agent has settled before starting sync."""
    last_count = -1
    last_mtime = -1.0
    for _ in range(10):  # Wait up to 20s max
        files = [f for f in source_dir.rglob("*") if f.is_file()]
        current_count = len(files)
        current_mtime = max((f.stat().st_mtime for f in files), default=0.0)
        if current_count == last_count and current_mtime == last_mtime and current_count > 0:
            break
        last_count = current_count
        last_mtime = current_mtime
        time.sleep(settle_seconds)


def watch_for_handoffs(poll_interval: int = 5, auto_commit: bool = False):
    """Deprecated; unattended sync cannot supply per-candidate approval."""
    raise PermissionError('Watcher disabled; use explicit scoped candidate approval')
    hermes_home = get_hermes_home()
    hardening_root = hermes_home / "hardening"
    handoff_dir = hardening_root / "handoff"
    handoff_dir.mkdir(parents=True, exist_ok=True)

    print(f"👀 Watching {hardening_root} for Hermes Agent drops (poll every {poll_interval}s)...")
    print(f"   Target Checkout: {CHECKOUT_ROOT}")
    print(f"   Auto-Commit on Green: {'ENABLED' if auto_commit else 'DISABLED'}")
    print("Press Ctrl+C to stop.")

    last_seen_mtime = 0.0
    last_seen_source = None

    while True:
        try:
            source_dir = None
            max_mtime = 0.0

            # Priority 1: Check handoff/ directory
            if handoff_dir.exists():
                handoff_files = list(handoff_dir.iterdir())
                if handoff_files:
                    source_dir = handoff_dir
                    max_mtime = max(f.stat().st_mtime for f in handoff_files)

            # Priority 2: Check timestamped directories / latest symlink
            if not source_dir:
                try:
                    source_dir = find_latest_hardening_source()
                    if source_dir.exists():
                        max_mtime = source_dir.stat().st_mtime
                except FileNotFoundError:
                    pass

            if source_dir and (source_dir != last_seen_source or max_mtime > last_seen_mtime):
                print(f"\n🚀 Hardening drop detected: {source_dir} (mtime: {datetime.fromtimestamp(max_mtime).strftime('%H:%M:%S')})")
                print("⏳ Debouncing writes (settle check)...")
                debounce_wait(source_dir, settle_seconds=2)

                pipeline = ReconcilePipeline(source_dir, dry_run=False, auto_commit=auto_commit)
                candidates = pipeline.collect_sync_candidates()
                changed = [c for c in candidates if c["status"] != "UNCHANGED"]

                if changed:
                    print(f"Found {len(changed)} changed files. Applying sync and running validation...")
                    pipeline.apply_sync(candidates)
                    results = pipeline.run_validation_suite(candidates)
                    report_file = pipeline.generate_report(candidates, results)
                    if results.get("all_passed"):
                        status_str = "🟢 PASSED"
                        print(f"[{status_str}] Report updated at {report_file}")
                        commit_hash = None
                        if auto_commit:
                            commit_hash = pipeline.git_commit_on_green(candidates, results)
                        commit_note = f" (commit: {commit_hash})" if commit_hash else ""
                        Notifier.dispatch(
                            "Hermes CI/CD: 🟢 Hardening Integrated",
                            f"Synchronized {len(changed)} files.\nAll 5 test tiers passed.{commit_note}",
                            success=True,
                        )
                    else:
                        status_str = "🔴 FAILED"
                        print(f"[{status_str}] Report updated at {report_file}")
                        pipeline.rollback_sync(candidates, results)
                        Notifier.dispatch(
                            "Hermes CI/CD: 🔴 Validation Failed",
                            "Checks failed. Workspace safely rolled back to pre-sync state.",
                            success=False,
                        )
                else:
                    print("Files are already identical to checkout.")

                last_seen_source = source_dir
                last_seen_mtime = max_mtime

            time.sleep(poll_interval)
        except KeyboardInterrupt:
            print("\nStopped watcher.")
            break
        except Exception as e:
            print(f"Watcher error: {e}")
            time.sleep(poll_interval)


def install_launchd_service() -> None:
    """Install and start the macOS launchd daemon."""
    plist_src = CHECKOUT_ROOT / "scripts" / "ai.hermes.reconciler.plist"
    plist_dest = Path.home() / "Library" / "LaunchAgents" / "ai.hermes.reconciler.plist"

    if not plist_src.exists():
        print(f"❌ Error: plist source not found at {plist_src}")
        sys.exit(1)

    plist_dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["launchctl", "unload", str(plist_dest)], capture_output=True)

    shutil.copy2(plist_src, plist_dest)
    print(f"📋 Installed plist to: {plist_dest}")

    res = subprocess.run(["launchctl", "load", str(plist_dest)], capture_output=True, text=True)
    if res.returncode == 0:
        print("🚀 Service loaded successfully into launchd (ai.hermes.reconciler)!")
        print("   Logs: ~/.hermes/logs/reconciler.log")
        print("   Check status with: ./scripts/reconcile --service-status")
    else:
        print(f"❌ Failed to load service: {res.stderr.strip()}")


def uninstall_launchd_service() -> None:
    """Unload and remove the macOS launchd daemon."""
    plist_dest = Path.home() / "Library" / "LaunchAgents" / "ai.hermes.reconciler.plist"
    if plist_dest.exists():
        subprocess.run(["launchctl", "unload", str(plist_dest)], capture_output=True)
        plist_dest.unlink()
        print("🛑 Service stopped and plist removed.")
    else:
        print("Service is not currently installed.")


def check_service_status() -> None:
    """Check running status of the launchd service and tail recent logs."""
    res = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
    running = False
    pid = "-"
    status_code = "-"
    for line in res.stdout.splitlines():
        if "ai.hermes.reconciler" in line:
            running = True
            parts = line.split()
            if len(parts) >= 2:
                pid = parts[0]
                status_code = parts[1]
            break

    print("=================================================================")
    print("🤖 HERMES RECONCILER SERVICE STATUS (launchd)")
    print("=================================================================")
    if running:
        print(f"State: 🟢 RUNNING (PID: {pid}, ExitCode: {status_code})")
    else:
        print("State: ⚪ NOT RUNNING (or not loaded)")

    log_file = get_hermes_home() / "logs" / "reconciler.log"
    print(f"\nLog file: {log_file}")
    if log_file.exists():
        lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        tail = lines[-20:]
        print("Last 20 log lines:")
        print("-----------------------------------------------------------------")
        for l in tail:
            print(f"  {l}")
    else:
        print("  (No logs written yet)")
    print("=================================================================")


def main():
    parser = argparse.ArgumentParser(description="Automated Hermes Hardening Sync & Verification Pipeline")
    parser.add_argument("--source", type=str, default=None, help="Explicit handoff/staging path")
    parser.add_argument("--dry-run", action="store_true", help="Preview file changes without syncing")
    parser.add_argument("--skip-tests", action="store_true", help="Sync files without running test suite")
    parser.add_argument("--auto-commit", action="store_true", help="Automatically commit changes when all tests pass")
    parser.add_argument("--watch", action="store_true", help="Continuously watch handoff directory and auto-sync")
    parser.add_argument("--install-service", action="store_true", help="Install and start the macOS launchd daemon")
    parser.add_argument("--uninstall-service", action="store_true", help="Uninstall and stop the macOS launchd daemon")
    parser.add_argument("--service-status", action="store_true", help="Check daemon status and tail recent logs")

    parser.add_argument('--apply', action='store_true', help='Apply only explicitly approved files after candidate validation')
    parser.add_argument('--approve-file', action='append', default=[], help='Exact kind:rel_path approval (repeatable)')
    parser.add_argument('--notify', action='store_true', help='Separately permit notifications after successful apply')
    args = parser.parse_args()
    if args.auto_commit:
        parser.error('Autocommit is deprecated; unrelated staged work must remain untouched')
    if args.dry_run and (args.apply or args.notify or args.install_service or args.uninstall_service or args.service_status or args.watch):
        parser.error('--dry-run cannot be combined with operational actions')
    if args.skip_tests:
        parser.error('Skipping pre-promotion validation is unsupported')
    if args.watch:
        parser.error('Unattended promotion is unsupported; use explicit --apply --approve-file')

    if args.install_service:
        install_launchd_service()
        return

    if args.uninstall_service:
        uninstall_launchd_service()
        return

    if args.service_status:
        check_service_status()
        return

    if args.watch:
        watch_for_handoffs(auto_commit=args.auto_commit)
        return

    try:
        source_dir = find_latest_hardening_source(args.source)
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

    preview = not args.apply
    pipeline = ReconcilePipeline(source_dir, dry_run=preview)
    candidates = pipeline.collect_sync_candidates()
    count = pipeline.apply_sync(candidates, approved_files=args.approve_file)
    if preview:
        print(f'Preview only: {count} proposed files; no validation, writes or notifications.')
        return
    print(json.dumps({'promoted_files': count, 'validation': getattr(pipeline, 'last_validation', None),
                      'qualification': 'Scoped candidate checks only; not release qualification'}))
    if args.notify:
        Notifier.dispatch('Scoped reconciliation', f'Promoted {count} approved files. No release qualification.', success=True)


if __name__ == "__main__":
    main()
