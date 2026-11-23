#!/usr/bin/env python3
"""Repeatable bounded Step5 blocker probe; NOT the complete acceptance runner.

Uses installed checkout Python only. No inherited credentials, listening socket,
installation, product Git, or operational actions. Output is a new temp directory.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    if '--child' not in sys.argv:
        sandbox = Path(tempfile.mkdtemp(prefix='astra-step5-offline-'))
        for name in ('home', 'profile'):
            (sandbox / name).mkdir()
        env = dict(HOME=str(sandbox/'home'), HERMES_HOME=str(sandbox/'profile'),
                   TMPDIR=str(sandbox), PATH='/usr/bin:/bin', TZ='UTC', LANG='C.UTF-8',
                   PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
                   DISCORD_BOT_TOKEN='TEST_OFFLINE_NOT_AUTHORIZATION', ASTRA_SANDBOX=str(sandbox))
        command = [str(ROOT/'venv/bin/python'), '-I', '-B', str(Path(__file__).resolve()), '--child']
        if '--require-publication' in sys.argv:
            command.append('--require-publication')
        if '--tests' in sys.argv:
            command.extend(['--tests', sys.argv[sys.argv.index('--tests') + 1]])
        result = subprocess.run(command, cwd=sandbox, env=env, capture_output=True, text=True, timeout=180)
        (sandbox/'probe.log').write_text(result.stdout + result.stderr)
        print(result.stdout)
        print('evidence=' + str(sandbox))
        print('exit_code=' + str(result.returncode))
        return result.returncode

    import traceback
    import unittest
    sandbox = Path(os.environ['ASTRA_SANDBOX']).resolve()
    denials, probes = [], []
    def inside(p):
        return p == sandbox or sandbox in p.parents
    def audit(event, args):
        reason = None
        if event.startswith('socket.'):
            if event == 'socket.__new__':
                return
            if event == 'socket.bind' and args[1] == ('::1', 0) and any('urllib3/util/connection.py' in f.filename for f in traceback.extract_stack()):
                probes.append(event)
                raise PermissionError('blocked dependency IPv6 probe')
            reason = 'network:' + event
        if event in ('subprocess.Popen', 'os.system', 'os.fork', 'os.posix_spawn', 'os.exec', 'os.kill'):
            reason = 'process:' + event
        if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
            p = Path(os.fsdecode(args[0])).resolve()
            writing = isinstance(args[2], int) and args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
            if writing and not inside(p) and str(p) != '/dev/null':
                reason = 'write:' + str(p)
            private = (p.name == '.env' or p.name.startswith('.env.') or p.suffix in ('.db', '.sqlite', '.sqlite3') or '/.hermes/' in str(p) or str(p).startswith('/Volumes/'))
            if private and not inside(p):
                reason = 'private:' + str(p)
        if event == 'sqlite3.connect':
            value = str(args[0]).removeprefix('file:').split('?')[0]
            if value != ':memory:' and not inside(Path(value).resolve()):
                reason = 'db:' + value
        if event in ('os.mkdir','os.remove','os.rmdir','os.rename','os.link','os.symlink','os.chmod','os.truncate'):
            for arg in args[:2] if event in ('os.rename','os.link','os.symlink') else args[:1]:
                if isinstance(arg,(str,bytes,os.PathLike)) and not inside(Path(os.fsdecode(arg)).resolve()):
                    reason = 'mutation:' + str(arg)
        if reason:
            denials.append(reason)
            raise PermissionError(reason)
    sys.addaudithook(audit)
    # Synthetic audit events: no actual socket, private read, DB or outside write.
    for event, args in [('socket.connect', (None, ('TEST.invalid', 443))),
                        ('open', ('/TEST-outside', 'w', os.O_WRONLY)),
                        ('open', ('/TEST/.hermes/TEST-not-real.env', 'r', 0)),
                        ('sqlite3.connect', ('/TEST-private.sqlite',))]:
        before = len(denials)
        try:
            sys.audit(event, *args)
        except PermissionError:
            pass
        assert len(denials) == before + 1, 'swallowed attempt must remain detectable'
    selftests = list(denials)
    denials.clear()
    sys.path[:0] = [str(ROOT), str(ROOT/'skills/financial/autonomous-trader/scripts'), str(ROOT/'tests')]
    names = sys.argv[sys.argv.index('--tests') + 1].split(',') if '--tests' in sys.argv else ['test_stage2_card_compatibility.Review', 'test_stage2_card_robustness.Extra', 'test_stage2_operational_cards.OperationalCards', 'test_step5_kian_repair.ProducerContext.test_changed_source_cannot_resume_research_delivery', 'test_step5_kian_repair.ProducerContext.test_publication_denial_is_independent_of_research_evaluation', 'test_step5_kian_repair.ProducerContext.test_actual_producer_delivery_restart_and_uncertain_no_resend']
    suite = unittest.defaultTestLoader.loadTestsFromNames(names)
    def flatten(value):
        for item in value:
            if isinstance(item, unittest.TestSuite):
                yield from flatten(item)
            else:
                yield item
    unique = {test.id(): test for test in flatten(suite)}
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(unique.values()))
    origins = {}
    for name, module in tuple(sys.modules.items()):
        value = getattr(module, '__file__', None)
        if value and Path(value).is_file() and Path(value).is_relative_to(ROOT) and '/venv/' not in value:
            origins[name] = dict(path=value, sha256=hashlib.sha256(Path(value).read_bytes()).hexdigest())
    def parent_id(test):
        return getattr(test, 'test_case', test).id()
    failed_ids = {parent_id(t) for t, _ in result.failures}
    error_ids = {parent_id(t) for t, _ in result.errors}
    skipped_ids = {parent_id(t) for t, _ in result.skipped}
    summary = dict(selected=list(unique), executed=result.testsRun, failed=len(failed_ids),
                   errors=len(error_ids), skipped=len(skipped_ids),
                   failure_events=len(result.failures), error_events=len(result.errors),
                   passed=result.testsRun-len(failed_ids | error_ids | skipped_ids),
                   audit_denials=denials, denied_dependency_probes=probes,
                   synthetic_guard_selftests=selftests, import_origins=origins,
                   scope='focused card regression; independent acceptance pending')
    (sandbox/'summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps({k:v for k,v in summary.items() if k != 'import_origins'}, sort_keys=True))
    return 0 if result.wasSuccessful() and not denials else 1


if __name__ == '__main__':
    sys.exit(main())
