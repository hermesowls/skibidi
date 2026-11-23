#!/usr/bin/env python3
"""Dedicated macOS OS-process gate. Does not relax stage2_card_guard.
Only the fixed worker or labelled fixture may be launched; no network allowed.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT/'plugins/analyst_trader/realdata_http_worker.py'
FIXTURE = ROOT/'tests/stage2_worker_fixture.py'
SCENARIOS = ('ok', 'overflow', 'status', 'error', 'hang', 'flood', 'output')
DENIALS = []
PROBES = []
OWNED = set()
PERMIT = None


def install_guard(sandbox):
    def inside(p):
        return p == sandbox or sandbox in p.parents
    def audit(event, args):
        reason = None
        if event.startswith('socket.'):
            import traceback
            if event == 'socket.__new__' and any('urllib3/util/connection.py' in f.filename for f in traceback.extract_stack()):
                PROBES.append(event)
                raise PermissionError('blocked dependency IPv6 capability probe before socket creation')
            reason = 'network:' + event
        if event in ('os.system', 'os.fork', 'os.posix_spawn', 'os.exec'):
            reason = 'process:' + event
        if event == 'subprocess.Popen':
            if PERMIT is None or list(args[1]) != PERMIT or args[3] != {}:
                reason = 'process:unapproved-child'
        if event == 'os.kill' and (args[0] not in OWNED or args[1] not in (0, 9)):
            reason = 'process:unowned-signal'
        if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
            p = Path(os.fsdecode(args[0])).resolve()
            writing = isinstance(args[2], int) and args[2] & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)
            if writing and not inside(p) and str(p) != '/dev/null':
                reason = 'outside-write'
            if (p.name.startswith('.env') or p.suffix in ('.db','.sqlite','.sqlite3') or '/.hermes/' in str(p) or str(p).startswith('/Volumes/')) and not inside(p):
                reason = 'private-file'
        if event == 'sqlite3.connect':
            p = str(args[0]).removeprefix('file:').split('?')[0]
            if p != ':memory:' and not inside(Path(p).resolve()): reason = 'private-db'
        if event in ('os.mkdir','os.remove','os.rmdir','os.rename','os.link','os.symlink','os.chmod','os.truncate'):
            for a in args[:2] if event in ('os.rename','os.link','os.symlink') else args[:1]:
                if isinstance(a,(str,bytes,os.PathLike)) and not inside(Path(os.fsdecode(a)).resolve()): reason = 'outside-mutation'
        if reason:
            DENIALS.append(reason)
            raise PermissionError(reason)
    sys.addaudithook(audit)


def spawn(command, **kwargs):
    global PERMIT
    production = [sys.executable, '-I', '-B', str(WORKER)]
    assert command == production or (command[:4] == [sys.executable, '-I', '-B', str(FIXTURE)] and len(command) == 6 and command[4] in SCENARIOS and Path(command[5]).resolve() == Path(os.environ['WORKER_SANDBOX']).resolve())
    assert kwargs == dict(stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env={}, close_fds=True)
    assert PERMIT is None
    PERMIT = command
    try:
        child = subprocess.Popen(command, **kwargs)
        OWNED.add(child.pid)
        return child
    finally:
        PERMIT = None


def main():
    if '--child' not in sys.argv:
        sandbox = Path(tempfile.mkdtemp(prefix='stage2-worker-lifecycle-')).resolve()
        (sandbox/'home').mkdir()
        python = Path(sys.executable).resolve()
        # Default-deny: only runtime/repository reads, sandbox writes, Python exec.
        reads = [ROOT, python.parent.parent, Path('/System'), Path('/usr/lib'), Path('/usr/share'), Path('/private/var/db/timezone'), Path('/private/etc'), Path('/dev'), sandbox]
        profile = '(version 1)\n(deny default)\n(allow process-fork)\n(allow process-exec (literal '+json.dumps(str(python))+'))\n(allow signal (target self) (target children))\n(allow sysctl-read)\n(allow mach-lookup)\n'
        profile += ''.join('(allow file-read* (subpath '+json.dumps(str(p))+'))\n' for p in reads)
        profile += '(allow file-read-metadata)\n(allow file-write* (subpath '+json.dumps(str(sandbox))+') (literal "/dev/null"))\n'
        profile += '(deny network*)\n(deny file-read-data (require-all (regex #"/\\.env($|\\.)" #"/\\.hermes/" #"\\.(db|sqlite|sqlite3)$") (require-not (subpath '+json.dumps(str(sandbox))+'))))\n'
        (sandbox/'sandbox.sb').write_text(profile)
        env = dict(HOME=str(sandbox/'home'), HERMES_HOME=str(sandbox/'home'), TMPDIR=str(sandbox), PATH='/usr/bin:/bin', TZ='UTC', LANG='C.UTF-8', WORKER_SANDBOX=str(sandbox), PYTHONDONTWRITEBYTECODE='1')
        command = ['/usr/bin/sandbox-exec','-f',str(sandbox/'sandbox.sb'),sys.executable,'-I','-B',str(Path(__file__).resolve()),'--child']
        result = subprocess.run(command, cwd=sandbox, env=env, capture_output=True, text=True, timeout=90)
        (sandbox/'probe.log').write_text(result.stdout+result.stderr)
        print(result.stdout+result.stderr)
        print('evidence='+str(sandbox))
        return result.returncode
    sandbox = Path(os.environ['WORKER_SANDBOX']).resolve()
    install_guard(sandbox)
    checks = [('socket.connect',(None,('TEST.invalid',443))), ('open',('/TEST-outside','w',os.O_WRONLY)), ('open',('/TEST/.hermes/private.env','r',0)), ('sqlite3.connect',('/TEST.sqlite',)), ('subprocess.Popen',('/bin/false',['/bin/false'],None,{})), ('os.kill',(999999,9))]
    for event,args in checks:
        before = len(DENIALS)
        try: sys.audit(event,*args)
        except PermissionError: pass
        assert len(DENIALS) == before+1
    selftests = DENIALS[:]; DENIALS.clear()
    sys.path[:0] = [str(ROOT),str(ROOT/'tests')]
    sys.modules['stage2_worker_guard'] = sys.modules[__name__]
    import unittest
    suite = unittest.defaultTestLoader.loadTestsFromName('test_stage2_worker_lifecycle')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    summary = dict(executed=result.testsRun, failures=len(result.failures), errors=len(result.errors), skips=len(result.skipped), audit_denials=DENIALS, denied_dependency_probes=PROBES, synthetic_guard_selftests=selftests, child_pids=sorted(OWNED), scope='TEST fixtures only; not provider proof', hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [WORKER, ROOT/'plugins/analyst_trader/realdata_transport.py', ROOT/'tests/stage2_card_guard.py',Path(__file__), FIXTURE,ROOT/'tests/test_stage2_worker_lifecycle.py']})
    (sandbox/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary))
    return 0 if result.wasSuccessful() and not DENIALS else 1

if __name__ == '__main__':
    raise SystemExit(main())
