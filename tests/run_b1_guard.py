"""B1: exact external coordinator copy, unchanged offline audit guard."""
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sandbox = Path(tempfile.mkdtemp(prefix='b1-TEST-')).resolve()
(sandbox/'profile/scripts').mkdir(parents=True)
(sandbox/'home').mkdir()
source = Path('/Users/admin/.hermes/scripts/flowseeker_unified_ingestion.py')
body = source.read_bytes()
(sandbox/'profile/scripts'/source.name).write_bytes(body)
env = dict(HOME=str(sandbox/'home'), HERMES_HOME=str(sandbox/'profile'), TMPDIR=str(sandbox), PATH='/usr/bin:/bin', TZ='UTC', LANG='C.UTF-8', PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', ASTRA_SANDBOX=str(sandbox))
result = subprocess.run([str(ROOT/'venv/bin/python'), '-I', '-B', str(ROOT/'tests/stage2_card_guard.py'), '--child', '--tests', 'test_b1_intraday,test_stage2_transport,test_stage2_integration_transport'], cwd=sandbox, env=env, capture_output=True, text=True, timeout=180)
print(result.stdout + result.stderr)
print(json.dumps(dict(evidence=str(sandbox), coordinator_sha256=hashlib.sha256(body).hexdigest(), exit_code=result.returncode)))
raise SystemExit(result.returncode)
