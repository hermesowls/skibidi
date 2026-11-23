"""Public research CLI: isolated TEST, never provider observations."""
import json
import tempfile
import unittest
from pathlib import Path
from plugins.analyst_trader import realdata_cli as cli, research_watchlist as rw

class ResearchCLI(unittest.TestCase):
    def test_offline_discovery_followup_context_lifecycle_outcome_reader(self):
        from datetime import datetime, timezone
        from plugins.analyst_trader.db import AnalystDatabase
        from plugins.analyst_trader import research_profiles
        from test_stage2_uw_schema import trade
        import os
        with tempfile.TemporaryDirectory(dir=os.environ['HERMES_HOME']) as tmp:
            root=Path(tmp).resolve(); profile_db=root/'profiles.sqlite'
            from unittest.mock import patch
            class Clock(datetime):
                @classmethod
                def now(cls, tz=None): return cls(2026,9,24,15,0,tzinfo=timezone.utc)
            store=AnalystDatabase(profile_db)
            with patch.object(research_profiles,'datetime',Clock):
                profile=research_profiles.create(store,'TEST E2E')
            with store._get_connection() as c: c.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            args=['--root',str(root),'--cohort','TEST','--authorize-research']
            def save(name, data):
                path=root/name; path.write_text(json.dumps(data)); return str(path)
            response=save('discovery.json',dict(status=200,source='TEST_FIXTURE',received_at='2026-09-24T16:00:00Z',body={'data':[trade(datetime(2026,9,24,15,50,tzinfo=timezone.utc))]}))
            result=cli.main(['research','cycle',*args,'--request-budget','1','--test-response',response,'--profile-db',str(profile_db),'--profile-version',profile['version_id'],'--now','2026-09-24T16:00:00Z'])
            self.assertEqual(result['watchlist']['observation_count'],1)
            contract=result['watchlist']['contracts'][0]
            follow=save('follow.json',dict(source='TEST_FIXTURE',evidence_cohort='TEST',status=200,received_at='2026-09-24T17:00:00Z',body={'data':[dict(start_time='2026-09-24T16:01:00Z',close=2),dict(start_time='2026-09-24T16:02:00Z',close=3)]}))
            context=save('discord.json',[dict(id='123',channel_id='456',timestamp='2026-09-24T16:00:00Z',author={'id':'TEST'},content='GEX AAOI please')])
            result=cli.main(['research','cycle',*args,'--request-budget','1','--test-followup',follow,'--date','2026-09-24','--now','2026-09-24T17:00:00Z','--context-json',context,'--received-at','2026-09-24T17:00:00Z'])
            self.assertEqual(result['watchlist']['snapshot_count'],1)
            update=dict(update_id='TEST-analysis',ticket_id='discord:456:123',setup_id='TEST-swing',state='analyzed',actor={'id':'TEST','kind':'researcher'},occurred_at='2026-09-24T17:01:00Z',received_at='2026-09-24T17:02:00Z',timeframe='swing',note='TEST only',evidence_ids=[result['watchlist']['contexts'][0]['id']])
            cli.main(['research','update-request',*args,'--update-json',save('update.json',update)])
            cli.main(['research','configure-horizons',*args,'--version','TEST-e2e-v1','--minutes','1','--metric','close','--received-at','2026-09-24T17:00:00Z'])
            final=cli.main(['research','status',*args])['watchlist']
            self.assertEqual(final['research_requests'][0]['state'],'analyzed')
            self.assertEqual(final['outcome_research']['candidates'][0]['outcomes'][0]['mark_return_pct'],50)
            self.assertEqual(final['mode'],'TEST')
            self.assertFalse((root/'REAL_DATA_RESEARCH').exists())


    def test_legacy_migration_preserves_bytes_and_claims(self):
        import os, base64
        for status in ('CONSUMED', 'SEND_OUTCOME_UNKNOWN', 'FAILED_NO_RETRY', 'RATE_LIMITED'):
            with tempfile.TemporaryDirectory(dir=os.environ['HERMES_HOME']) as tmp:
                root=Path(tmp); dest=root/'TEST'; dest.mkdir()
                path=dest/'uw-cycle-state.json'
                legacy=dict(authorization={'root':str(root),'cohort':'TEST'}, attempts=1, status=status, stopped=True)
                raw=json.dumps(legacy, indent=3).encode(); path.write_bytes(raw)
                args=['migrate-ledger','--root',str(root),'--cohort','TEST','--authorize-research']
                result=cli.research_main(args)
                self.assertEqual(result['status'],'MIGRATED')
                state=json.loads(path.read_text())
                self.assertEqual(base64.b64decode(state['legacy']['original_base64']),raw)
                self.assertEqual(state['runs'][state['legacy']['run_id']],legacy)
                self.assertTrue(state['provider_stop'])
                before=path.read_bytes()
                self.assertEqual(cli.research_main(args)['status'],'ALREADY_MIGRATED')
                self.assertEqual(path.read_bytes(),before)

    def test_reviewed_release_deadline_replay_conflict_and_lock(self):
        import os, fcntl
        from datetime import datetime, timezone, timedelta
        with tempfile.TemporaryDirectory(dir=os.environ['HERMES_HOME']) as tmp:
            root=Path(tmp); dest=root/'TEST'; dest.mkdir(); path=dest/'uw-cycle-state.json'
            now=datetime.now(timezone.utc)
            state=dict(runs={'TEST-old':dict(authorization={},attempts=1,claims=[{'status':'RATE_LIMITED'}])},
                provider_stop=dict(run_id='TEST-old',retry_after='3600',observed_at=now.isoformat()))
            path.write_text(json.dumps(state)); before=path.read_bytes()
            common=['--root',str(root),'--cohort','TEST','--authorize-research']
            status=cli.research_main(['recovery-status',*common])
            args=['release-rate-limit',*common,'--run-id','TEST-old','--receipt-reference',status['receipt_reference'],
                '--release-id','TEST-release','--reason','TEST operator reviewed quota','--operator-decision','allow-new-cycle']
            with self.assertRaisesRegex(ValueError,'deadline'):
                cli.research_main(args)
            self.assertEqual(path.read_bytes(),before)
            state['provider_stop']['observed_at']=(now-timedelta(hours=2)).isoformat()
            path.write_text(json.dumps(state)); status=cli.research_main(['recovery-status',*common])
            args[args.index('--receipt-reference')+1]=status['receipt_reference']
            with path.with_suffix('.lock').open('a') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with self.assertRaises(BlockingIOError): cli.research_main(args)
            out=cli.research_main(args); self.assertEqual(out['status'],'RELEASED')
            after=path.read_bytes(); saved=json.loads(after)
            self.assertEqual(saved['runs'],state['runs'])
            self.assertEqual(saved['releases']['TEST-release']['stop'],state['provider_stop'])
            self.assertEqual(cli.research_main(args)['status'],'RELEASE_REPLAY')
            self.assertEqual(path.read_bytes(),after)
            with self.assertRaisesRegex(ValueError,'conflict'):
                cli.research_main([*args,'--reason','different'])

    def test_legacy_absent_incompatible_and_unknown_release(self):
        import os
        with tempfile.TemporaryDirectory(dir=os.environ['HERMES_HOME']) as tmp:
            root=Path(tmp); common=['--root',str(root),'--cohort','TEST','--authorize-research']
            self.assertEqual(cli.research_main(['migrate-ledger',*common])['status'],'NO_LEGACY_LEDGER')
            self.assertFalse((root/'TEST').exists())
            dest=root/'TEST'; dest.mkdir(); path=dest/'uw-cycle-state.json'
            path.write_text('{"alien":true}'); before=path.read_bytes()
            with self.assertRaises(ValueError): cli.research_main(['migrate-ledger',*common])
            self.assertEqual(path.read_bytes(),before)
            path.write_text(json.dumps(dict(runs={},provider_stop={'run_id':'TEST-unknown'})))
            ref=cli.research_main(['recovery-status',*common])['receipt_reference']
            args=['release-rate-limit',*common,'--run-id','TEST-unknown','--receipt-reference',ref,'--release-id','TEST-release','--reason','TEST manual decision']
            with self.assertRaises(ValueError): cli.research_main(args)
            self.assertEqual(cli.research_main([*args,'--operator-decision','allow-new-cycle'])['status'],'RELEASED')

    def test_repeat_concurrent_claim(self):
        self._live_cases(['concurrent'])

    def test_repeat_archive_recovery(self):
        self._live_cases(['recovery'])

    def test_repeat_followup_429(self):
        self._live_cases(['followup429'])

    def test_repeat_two_runs_and_binding(self):
        self._live_cases([None])

    def test_repeat_ambiguous_consumed(self):
        self._live_cases(['ambiguous'])

    def test_live_selection_process_boundary_cap_and_replay(self):
        self._live_cases([None, '429', 'ambiguous'])

    def _live_cases(self, failures):
        import os, base64
        from datetime import datetime, timezone, timedelta
        from plugins.analyst_trader.db import AnalystDatabase
        from plugins.analyst_trader import research_profiles
        from test_stage2_uw_schema import trade
        for failure in failures:
            with self.subTest(failure=failure), tempfile.TemporaryDirectory(dir=os.environ['HERMES_HOME']) as tmp:
                root=Path(tmp).resolve(); source=root/'profiles.sqlite'
                store=AnalystDatabase(source); profile=research_profiles.create(store,'TEST boundary')
                with store._get_connection() as c: c.execute('PRAGMA wal_checkpoint(TRUNCATE)')
                now=datetime.now(timezone.utc); sends=[]
                case=self
                class Child:
                    stdin=stdout=None
                    returncode=0
                    def __init__(self, argv): self.worker=argv[-1]
                    def communicate(self,payload,timeout):
                        request=json.loads(payload); sends.append((self.worker,request))
                        if failure=='concurrent':
                            with case.assertRaises(BlockingIOError):
                                cli.research_main([*args[:-1],'TEST-competing'],process_factory=factory)
                        if failure=='ambiguous': raise OSError('TEST ambiguous send')
                        receipt=datetime.now(timezone.utc).isoformat()
                        if 'intraday' in self.worker:
                            response=dict(status=429 if failure=='followup429' else 200,source='UW_LIVE',received_at=receipt,raw_body=base64.b64encode(b'{"data":[]}').decode())
                        else:
                            response=dict(status=429 if failure=='429' else 200,source='UW_LIVE',received_at=receipt,body={'data':[trade(now-timedelta(seconds=1))]})
                        return json.dumps(response).encode(),None
                    def kill(self): pass
                    def wait(self,timeout): pass
                factory=lambda argv,**kw: Child(argv)
                args=['cycle','--root',str(root),'--cohort','TEST','--authorize-research','--uw-live','--request-budget','2','--stages','discovery','followup','--profile-db',str(source),'--profile-version',profile['version_id'],'--date',now.date().isoformat(),'--window-start',(now-timedelta(seconds=1)).isoformat(),'--window-end',(now+timedelta(seconds=90)).isoformat()]
                args += ['--run-id','TEST-first']
                if failure=='recovery':
                    from unittest.mock import patch
                    with patch.object(rw,'seed',side_effect=RuntimeError('TEST archive before seed')):
                        result=cli.research_main(args,process_factory=factory)
                        with self.assertRaises(RuntimeError):
                            cli.research_main([*args[:-1],'TEST-unresolved'],process_factory=factory)
                    self.assertEqual(len(sends),1)
                else:
                    result=cli.research_main(args,process_factory=factory)
                expected=1 if failure in ('429','ambiguous','recovery') else 2
                self.assertEqual(result['requests'],expected)
                self.assertEqual(len(sends),result['requests'])
                self.assertEqual(cli.research_main(args,process_factory=factory)['requests'],0)
                self.assertEqual(len(sends),expected)
                self.assertFalse((root/'REAL_DATA_RESEARCH').exists())
                if not failure:
                    self.assertEqual(result['watchlist']['mode'],'TEST')
                    self.assertIn('intraday',sends[1][0])
                    self.assertEqual(sends[0][1]['params']['limit'],'20')
                with self.assertRaisesRegex(ValueError, 'conflict'):
                    cli.research_main([*args,'--max-rows','19'],process_factory=factory)
                next_args=[*args[:-1],'TEST-second']
                second=cli.research_main(next_args,process_factory=factory)
                if failure in ('429','followup429'):
                    self.assertEqual(second['requests'],0)
                else:
                    self.assertGreater(second['requests'],0)
                state=json.loads((root/'TEST/uw-cycle-state.json').read_text())
                self.assertEqual(state['runs']['TEST-first']['attempts'],expected)
                if not failure:
                    self.assertEqual(second['watchlist']['observation_count'],1)
                if failure in ('429','followup429'):
                    common=['--root',str(root),'--cohort','TEST','--authorize-research']
                    blocked=cli.research_main(['recovery-status',*common])
                    release=['release-rate-limit',*common,'--run-id',blocked['stop']['run_id'],
                        '--receipt-reference',blocked['receipt_reference'],'--release-id','TEST-reviewed',
                        '--reason','TEST explicit unknown quota decision','--operator-decision','allow-new-cycle']
                    cli.research_main(release)
                    prior=dict(state['runs'])
                    if failure == 'followup429':
                        import time
                        time.sleep(1.05)  # Preserve the existing one-second interval.
                    third=cli.research_main([*args[:-1],'TEST-after-review'],process_factory=factory)
                    self.assertGreater(third['requests'],0)
                    retained=json.loads((root/'TEST/uw-cycle-state.json').read_text())
                    self.assertEqual({k:retained['runs'][k] for k in prior},prior)
                    # Replaying an old release must not clear the new stop.
                    cli.research_main(release)
                    self.assertTrue(json.loads((root/'TEST/uw-cycle-state.json').read_text())['provider_stop'])
                self.assertEqual(cli.research_main(next_args,process_factory=factory)['requests'],0)

    def test_bounded_live_selector_zero_and_fail_closed(self):
        import os
        with tempfile.TemporaryDirectory(dir=os.environ['HERMES_HOME']) as tmp:
            root=Path(tmp)/'untouched'
            args=['cycle','--root',str(root),'--cohort','REAL_DATA_RESEARCH','--authorize-research','--uw-live']
            self.assertEqual(cli.research_main([*args,'--request-budget','0'])['requests'],0)
            with self.assertRaises(ValueError):
                cli.research_main([*args,'--request-budget','1'])
            self.assertFalse(root.exists())

    def test_status_cycle_and_versioned_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()
            common=['--root',str(root),'--cohort','TEST']
            self.assertTrue(callable(getattr(cli,'research_main',None)), 'Missing public research CLI')
            out=cli.research_main(['status',*common])
            self.assertEqual(out['status'],'NOT_INITIALIZED')
            self.assertFalse((root/'TEST').exists())
            source=root/'seed.json'
            source.write_text(json.dumps({'records':[dict(mode='TEST',provider_event_id='TEST',received_at='2026-09-24T16:00:00Z',evidence={'contract_symbol':'AAOI260925C00100000'},raw={})]}))
            db=root/'TEST/watchlist.sqlite'; rw.seed(db,source)
            before=db.read_bytes()
            out=cli.research_main(['cycle',*common,'--authorize-research','--request-budget','0'])
            self.assertEqual(out['sources']['discord'],'DISCONNECTED')
            self.assertEqual(out['requests'],0)
            self.assertEqual(db.read_bytes(),before)
            result=cli.research_main(['configure-horizons',*common,'--authorize-research','--version','TEST-v1','--minutes','1','3','--metric','close','--received-at','2026-09-24T17:00:00Z'])
            self.assertEqual(result['mode'],'TEST')
            self.assertEqual(result['outcome_research']['candidates'][0]['outcomes'][0]['status'],'PENDING')
            with self.assertRaises(ValueError):
                cli.research_main(['cycle',*common,'--authorize-research','--request-budget','1'])
