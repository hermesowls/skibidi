"""TEST ONLY subprocess fixture, never provider observations.
Runs production __main__ with only the external HTTP client boundary stubbed.
Hang/flood/output deliberately exercise hostile fixture process behavior, not HTTP.
"""
import json
import os
from pathlib import Path
import runpy
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
scenario, directory = sys.argv[1:]
sandbox = Path(directory).resolve()
sys.path.insert(0, str(ROOT/'tests'))
from stage2_worker_guard import install_guard, DENIALS
install_guard(sandbox)
def diagnostic(kind, value, tb):
    import traceback
    (sandbox/('fixture-error-'+str(os.getpid()))).write_text(''.join(traceback.format_exception(kind,value,tb)))
sys.excepthook = diagnostic
assert set(os.environ) <= {'LC_CTYPE', '__CF_USER_TEXT_ENCODING'}, list(os.environ)
# No inherited HOME, credentials, proxies or config; imports cannot read private files.
import signal
signal.alarm(8)  # Fixture-only orphan fail-safe if the harness itself fails.
(sandbox/('started-'+str(os.getpid()))).write_text(scenario)
if scenario == 'hang':
    time.sleep(60)
    raise SystemExit('fixture watchdog failed')
if scenario == 'flood':
    while True:
        os.write(1, b'F'*65536)
if scenario == 'output':
    sys.stdin.buffer.read()
    sys.stdout.write('x'*(6*1048576+1025))
    raise SystemExit(0)

import httpx
class Response:
    status_code = 429 if scenario == 'status' else 200
    headers = {}
    def __enter__(self): return self
    def __exit__(self,*args):
        (sandbox/('closed-'+str(os.getpid()))).write_text('closed')
    def iter_raw(self, chunk_size):
        assert chunk_size == 16384
        if scenario == 'error': raise RuntimeError('TEST-DUMMY-CREDENTIAL MUST NOT LEAK')
        if scenario == 'overflow':
            for _ in range(65): yield b'x'*16384
        else: yield b'{"data":[{}]}'
class Client:
    def __init__(self, **kwargs): assert kwargs['trust_env'] is False
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def stream(self,*args,**kwargs):
        (sandbox/('params-'+str(os.getpid()))).write_text(json.dumps(kwargs['params']))
        assert kwargs['follow_redirects'] is False
        assert kwargs['headers']['Authorization'] == 'Bearer TEST-DUMMY-CREDENTIAL'
        with (sandbox/('attempts-'+str(os.getpid()))).open('a') as f: f.write('TEST HTTP boundary\n')
        return Response()
def transport(**kwargs):
    assert kwargs == {'retries':0,'trust_env':False}
    return object()
httpx.Client = Client
httpx.HTTPTransport = transport
try:
    with (sandbox/('stderr-'+str(os.getpid()))).open('w') as diagnostics:
        sys.stderr = diagnostics
        runpy.run_path(str(ROOT/'plugins/analyst_trader/realdata_http_worker.py'), run_name='__main__')
finally:
    (sandbox/('denials-'+str(os.getpid()))).write_text(json.dumps(DENIALS))
