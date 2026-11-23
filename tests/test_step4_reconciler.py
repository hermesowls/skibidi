import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
from scripts import reconcile_hardening as r


class ReconcilerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.source = self.root / 'drop'
        (self.source / 'repo').mkdir(parents=True)
        (self.source / 'repo' / 'example.py').write_text('value = 2\n')
        self.dest = self.root / 'checkout'
        self.root_patch = patch.object(r, 'CHECKOUT_ROOT', self.dest)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def test_dry_run_entrypoint_has_no_writes_validation_notifications_or_processes(self):
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with patch.object(r.subprocess, 'run') as child, patch.object(r.Notifier, 'dispatch') as notify, patch.object(r.ReconcilePipeline, 'run_validation_suite', return_value={'all_passed': True}) as validate, patch('sys.argv', ['reconcile', '--source', str(self.source), '--dry-run']), contextlib.redirect_stdout(io.StringIO()):
            try:
                r.main()
            except SystemExit as exc:
                self.assertEqual(exc.code, 0)
            self.assertFalse(validate.called, 'dry-run must not validate or acquire packages')
            self.assertFalse(child.called)
            self.assertFalse(notify.called)
        after = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        self.assertFalse(self.dest.exists())

    def test_invalid_candidate_does_not_change_destination(self):
        self.dest.mkdir()
        (self.dest / 'example.py').write_text('value = 1\n')
        (self.source / 'repo' / 'example.py').write_text('def invalid(:\n')
        p = r.ReconcilePipeline(self.source)
        candidates = p.collect_sync_candidates()
        with self.assertRaises((ValueError, PermissionError, SyntaxError)):
            p.apply_sync(candidates, approved_files=['repo:example.py'])
        self.assertEqual((self.dest / 'example.py').read_text(), 'value = 1\n')

    def test_autocommit_refuses_without_touching_index(self):
        import os
        import subprocess
        self.dest.mkdir()
        env = dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null',
                   GIT_CONFIG_SYSTEM='/dev/null', GIT_TERMINAL_PROMPT='0')
        prefix = ['/usr/bin/git', '-c', 'core.hooksPath=/dev/null']
        # Guard allows precisely these two commands only under the disposable root.
        subprocess.run(prefix+['init', '--quiet', '--template='], cwd=self.dest, env=env, check=True, capture_output=True)
        (self.dest/'unrelated.txt').write_text('TEST unrelated staged work')
        subprocess.run(prefix+['add', '--', 'unrelated.txt'], cwd=self.dest, env=env, check=True, capture_output=True)
        index = self.dest/'.git/index'
        before = index.read_bytes()
        self.assertTrue(before.startswith(b'DIRC'))
        p = r.ReconcilePipeline(self.source)
        with patch.object(r.subprocess, 'run', return_value=Mock(returncode=0, stdout='fixture', stderr='')) as child:
            with self.assertRaises((ValueError, PermissionError)):
                p.git_commit_on_green(p.collect_sync_candidates(), {'all_passed': True})
            child.assert_not_called()
        self.assertEqual(index.read_bytes(), before)
        self.assertEqual((self.dest/'unrelated.txt').read_text(), 'TEST unrelated staged work')

    def test_success_validates_frozen_tree_before_promotion(self):
        self.dest.mkdir()
        (self.dest / 'unrelated.txt').write_text('leave me')
        pipeline = r.ReconcilePipeline(self.source)
        calls = []
        def validate(stage, items):
            self.assertFalse((self.dest / 'example.py').exists())
            self.assertEqual((stage / 'repo/example.py').read_text(), 'value = 2\n')
            calls.append(stage)
            return {'all_passed': True, 'scope': 'fixture'}
        self.assertEqual(pipeline.apply_sync(pipeline.collect_sync_candidates(), approved_files=['repo:example.py'], validator=validate), 1)
        self.assertEqual(len(calls), 1)
        self.assertFalse(calls[0].exists())
        self.assertEqual((self.dest / 'example.py').read_text(), 'value = 2\n')
        self.assertEqual((self.dest / 'unrelated.txt').read_text(), 'leave me')

    def test_rejected_validator_leaves_absent_destination_absent(self):
        p = r.ReconcilePipeline(self.source)
        with self.assertRaises(ValueError):
            p.apply_sync(p.collect_sync_candidates(), approved_files=['repo:example.py'], validator=lambda *_: {'all_passed': False})
        self.assertFalse(self.dest.exists())

    def test_late_replace_failure_rolls_back_files_and_new_directories(self):
        from scripts import reconcile_promotion as promotion
        (self.source / 'repo' / 'nested').mkdir()
        (self.source / 'repo' / 'nested/second.py').write_text('value = 3\n')
        self.dest.mkdir()
        (self.dest / 'example.py').write_text('value = 1\n')
        (self.dest / 'unrelated.txt').write_text('unchanged')
        p = r.ReconcilePipeline(self.source)
        candidates = sorted(p.collect_sync_candidates(), key=lambda c: c['rel_path'])
        original = promotion.replace_bytes
        def fault(path, data):
            if path.name == 'second.py':
                raise OSError('injected late failure')
            return original(path, data)
        with patch.object(promotion, 'replace_bytes', side_effect=fault), self.assertRaises(OSError):
            p.apply_sync(candidates, approved_files=['repo:example.py', 'repo:nested/second.py'])
        self.assertEqual((self.dest / 'example.py').read_text(), 'value = 1\n')
        self.assertFalse((self.dest / 'nested').exists())
        self.assertEqual((self.dest / 'unrelated.txt').read_text(), 'unchanged')

    def test_discovery_rejects_symlink_and_private_candidates_before_read(self):
        outside = self.root/'private.txt'
        outside.write_text('TEST secret sentinel')
        link = self.source/'repo/link.py'
        link.symlink_to(outside)
        p = r.ReconcilePipeline(self.source, dry_run=True)
        with self.assertRaises(ValueError):
            p.collect_sync_candidates()
        link.unlink()
        secret = self.source/'repo/private.db'
        secret.write_text('TEST database sentinel')
        with self.assertRaises(ValueError):
            p.collect_sync_candidates()

    def test_source_or_destination_revision_rejects(self):
        p = r.ReconcilePipeline(self.source)
        c = p.collect_sync_candidates()
        (self.source / 'repo/example.py').write_text('value = 99\n')
        with self.assertRaises(ValueError):
            p.apply_sync(c, approved_files=['repo:example.py'])
        self.assertFalse(self.dest.exists())

    def test_traversal_and_symlink_reject(self):
        p = r.ReconcilePipeline(self.source)
        c = p.collect_sync_candidates()
        c[0]['rel_path'] = '../escape.py'
        with self.assertRaises(ValueError):
            p.apply_sync(c, approved_files=['repo:../escape.py'])
        self.dest.mkdir()
        outside = self.root / 'outside.py'
        outside.write_text('untouched')
        (self.dest / 'example.py').symlink_to(outside)
        with self.assertRaises(ValueError):
            p.apply_sync(p.collect_sync_candidates(), approved_files=['repo:example.py'])
        self.assertEqual(outside.read_text(), 'untouched')

    def test_deprecated_entrypoints_refuse_before_any_side_effect(self):
        pipeline = r.ReconcilePipeline(self.source, dry_run=True)
        candidates = pipeline.collect_sync_candidates()
        self.dest.mkdir()
        (self.dest / '.git').mkdir()
        index = self.dest / '.git/index'
        index.write_bytes(b'TEST unrelated staged index sentinel')
        before = {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with patch.object(r.subprocess, 'run') as child, patch.object(r.Notifier, 'dispatch') as notify:
            for action in (lambda: pipeline.run_validation_suite(candidates),
                           lambda: pipeline.generate_report(candidates, {'all_passed': True}),
                           lambda: pipeline.rollback_sync(candidates, {}),
                           lambda: r.watch_for_handoffs(),
                           lambda: pipeline.git_commit_on_green(candidates, {'all_passed': True})):
                with self.assertRaises(PermissionError):
                    action()
            child.assert_not_called()
            notify.assert_not_called()
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_default_preview_and_approved_apply_entrypoint(self):
        with patch.object(r.Notifier, 'dispatch') as notify, patch.object(r.subprocess, 'run') as child:
            with patch('sys.argv', ['reconcile', '--source', str(self.source)]):
                r.main()
            self.assertFalse(self.dest.exists())
            with patch('sys.argv', ['reconcile', '--source', str(self.source), '--apply', '--approve-file', 'repo:example.py']):
                r.main()
            self.assertEqual((self.dest/'example.py').read_text(), 'value = 2\n')
            notify.assert_not_called()
            child.assert_not_called()

    def test_validator_exception_leaves_destination_unchanged(self):
        p = r.ReconcilePipeline(self.source)
        def fail(*_):
            raise RuntimeError('validator error')
        with self.assertRaises(RuntimeError):
            p.apply_sync(p.collect_sync_candidates(), approved_files=['repo:example.py'], validator=fail)
        self.assertFalse(self.dest.exists())

