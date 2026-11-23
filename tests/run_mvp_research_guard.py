"""Offline runner: exact coordinator bytes copied before unchanged audit guard."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sandbox = Path(tempfile.mkdtemp(prefix='mvp-research-TEST-')).resolve()
profile = sandbox / 'profile'
(profile / 'scripts').mkdir(parents=True)
(sandbox / 'home').mkdir()
source = Path('/Users/admin/.hermes/scripts/flowseeker_unified_ingestion.py')
body = source.read_bytes()
(profile / 'scripts' / source.name).write_bytes(body)
public_source = Path('/Users/admin/.hermes/scripts/notable_flow_public_snapshot.py')
(profile / 'scripts' / public_source.name).write_bytes(public_source.read_bytes())
env = dict(HOME=str(sandbox/'home'), HERMES_HOME=str(profile), TMPDIR=str(sandbox),
    PATH='/usr/bin:/bin', TZ='UTC', LANG='C.UTF-8', PYTHONDONTWRITEBYTECODE='1',
    PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', ASTRA_SANDBOX=str(sandbox))
result = subprocess.run([str(ROOT/'venv/bin/python'), '-I', '-B',
    str(ROOT/'tests/stage2_card_guard.py'), '--child', '--tests',
    'test_finviz_operator,test_finviz_recovery,test_finviz_quotes,test_mvp_research,test_stage2_realdata,test_stage2_uw_schema,test_stage3_targeted_request,test_pcir1_chronology,test_daily_transport,test_b1_intraday,test_request_lifecycle,test_outcome_learning,test_research_cli,test_underlying_auto,test_stage2_calendar,test_step5_kian_technicals'],
    cwd=sandbox, env=env, capture_output=True, text=True, timeout=180)
(sandbox/'probe.log').write_text(result.stdout + result.stderr)
print(result.stdout + result.stderr)
print(json.dumps(dict(evidence=str(sandbox), coordinator_sha256=hashlib.sha256(body).hexdigest(), exit_code=result.returncode)))
raise SystemExit(result.returncode)
