"""TEST-only public request lifecycle over native context storage."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from plugins.analyst_trader import research_watchlist as rw

GRANT = dict(authorized=True, evidence_cohort='TEST')

class Lifecycle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.db = self.root/'TEST/watchlist.sqlite'
        seed = self.root/'seed.json'
        seed.write_text(json.dumps({'records':[dict(mode='TEST', provider_event_id='TEST', received_at='2026-09-24T16:00:00Z', evidence={'contract_symbol':'AAOI260925C00100000'}, raw={})]}))
        rw.seed(self.db, seed)
        spec = importlib.util.spec_from_file_location('lifecycle_coordinator', Path(os.environ['HERMES_HOME'])/'scripts/flowseeker_unified_ingestion.py')
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)
        self.message = dict(id='123', channel_id='456', timestamp='2026-09-24T16:00:00Z', author={'id':'789'}, content='GEX AAOI please')
        self.import_message(self.message)

    def import_message(self, message):
        artifact = self.root/'discord.json'
        artifact.write_text(json.dumps([message]))
        self.mod.run_research_context(root=self.root, grant=GRANT, source='discord', artifact=artifact, received_at='2026-09-24T17:00:00Z')

    def update(self, **changes):
        event = dict(update_id='TEST-analysis', ticket_id='discord:456:123', setup_id='TEST-swing', state='analyzed', actor={'id':'TEST-analyst', 'kind':'researcher'}, occurred_at='2026-09-24T17:01:00Z', received_at='2026-09-24T17:02:00Z', timeframe='swing', note='TEST descriptive analysis', evidence_ids=[rw.read_watchlist(self.db)['contexts'][0]['id']])
        event.update(changes)
        return self.mod.run_research_request_update(root=self.root, grant=GRANT, update=event)

    def test_durable_analysis_replay_and_original_provenance(self):
        initial = rw.read_watchlist(self.db)
        self.assertEqual(initial['research_requests'][0]['state'], 'pending-timeframe')
        self.update()
        before = self.db.read_bytes()
        self.update()
        self.assertEqual(self.db.read_bytes(), before)
        request = rw.read_watchlist(self.db)['research_requests'][0]
        self.assertEqual(request['state'], 'analyzed')
        self.assertEqual(request['original_context']['raw_text'], self.message['content'])
        self.assertEqual(request['requester'], self.message['author'])
        self.assertEqual(len(request['updates']), 1)
        self.assertFalse(request['execution_authorized'])
        self.assertEqual(rw.read_watchlist(self.db)['snapshot_count'], 0)

    def test_transitions_monitoring_closure_replay(self):
        with self.assertRaises(ValueError): self.update(state='monitoring')
        self.update()
        with self.assertRaises(ValueError): self.update(update_id='TEST-monitor', state='monitoring')
        plan = dict(approved_by='TEST-owner', approval_ref='TEST-approval', budget_ref='TEST-zero-network', cadence='manual', closure_rule='explicit reviewed close')
        self.update(update_id='TEST-monitor', state='monitoring', monitoring_plan=plan)
        self.update(update_id='TEST-close', state='closed', note='TEST research archived; outcome unknown')
        before = self.db.read_bytes()
        self.update(update_id='TEST-close', state='closed', note='TEST research archived; outcome unknown')
        with self.assertRaises(ValueError): self.update(update_id='TEST-reopen')
        self.assertEqual(self.db.read_bytes(), before)
        self.assertEqual([u['state'] for u in rw.read_watchlist(self.db)['research_requests'][0]['updates']], ['analyzed','monitoring','closed'])

    def test_invalid_updates_are_atomic(self):
        for changes in [dict(timeframe='UNKNOWN'), dict(evidence_ids=[]), dict(evidence_ids=['missing']), dict(actor={}), dict(state='ordered'), dict(ticket_id='invented'), dict(occurred_at='2026-09-24T16:59:59Z'), dict(received_at='2026-09-24T17:00:00Z'), dict(occurred_at='2026-09-24T17:00:00'), dict(execution_authorized=True)]:
            with self.subTest(changes=changes):
                before = self.db.read_bytes()
                with self.assertRaises(ValueError): self.update(**changes)
                self.assertEqual(self.db.read_bytes(), before)
        self.update()
        for changes in [dict(note='changed replay'), dict(update_id='TEST-old', occurred_at='2026-09-24T17:00:59Z'), dict(update_id='TEST-horizon', timeframe='intraday')]:
            before = self.db.read_bytes()
            with self.assertRaises(ValueError): self.update(**changes)
            self.assertEqual(self.db.read_bytes(), before)

    def test_different_setups_same_ticker_and_pending_note(self):
        self.update(update_id='TEST-pending', state='pending-timeframe', timeframe='UNKNOWN', evidence_ids=[], note='TEST timeframe question pending; not sent')
        self.update()
        self.update(update_id='TEST-intraday', setup_id='TEST-intraday', timeframe='intraday')
        requests = rw.read_watchlist(self.db)['research_requests']
        self.assertEqual({r['timeframe'] for r in requests}, {'swing','intraday'})
        self.assertEqual({r['ticker'] for r in requests}, {'AAOI'})
        self.assertEqual(len(requests), 2)

    def test_original_survives_edited_replay_and_offset_chronology(self):
        self.update()
        self.import_message(dict(self.message, edited_timestamp='2026-09-24T16:30:00Z', content='GEX AAOI please intraday changed'))
        self.update(update_id='TEST-offset', occurred_at='2026-09-24T13:01:00-04:00', received_at='2026-09-24T18:02:00+01:00')
        req = rw.read_watchlist(self.db)['research_requests'][0]
        self.assertEqual(req['original_context']['raw_text'], self.message['content'])
        self.assertEqual(req['requester'], self.message['author'])
        self.assertEqual(len(req['updates']), 2)

    def test_analysis_fields_preserved(self):
        analysis = dict(thesis='TEST range', trigger='TEST reclaim', invalidation='TEST loss', targets=['TEST level'], expiry_context='UNKNOWN')
        self.update(analysis=analysis)
        req = rw.read_watchlist(self.db)['research_requests'][0]
        self.assertEqual(req['updates'][0]['analysis'], analysis)

    def test_public_api_projects_test_lifecycle(self):
        import asyncio
        from unittest.mock import patch
        from hermes_cli import web_server
        self.update()
        with patch.object(rw, 'canonical_path', return_value=self.db):
            response = asyncio.run(web_server.api_research_watchlist())
        self.assertEqual(response['mode'], 'TEST')
        self.assertEqual(response['research_requests'][0]['state'], 'analyzed')
        self.assertEqual(response['research_update_count'], 1)
        self.assertFalse(response['execution_authorized'])

    def test_grant_and_future_evidence_rejected(self):
        with self.assertRaises(ValueError):
            self.mod.run_research_request_update(root=self.root, grant=dict(authorized=False,evidence_cohort='TEST'), update={})
        artifact = self.root/'future.json'
        artifact.write_text(json.dumps([dict(self.message,id='124')]))
        self.mod.run_research_context(root=self.root, grant=GRANT, source='discord', artifact=artifact, received_at='2026-09-24T17:10:00Z')
        contexts = rw.read_watchlist(self.db)['contexts']
        self.update()
        before = self.db.read_bytes()
        with self.assertRaises(ValueError):
            self.update(update_id='TEST-future', occurred_at='2026-09-24T17:05:00Z', received_at='2026-09-24T17:11:00Z', evidence_ids=[contexts[-1]['id']])
        self.assertEqual(self.db.read_bytes(), before)

    def test_backfilled_version_cannot_replace_original(self):
        self.update()
        artifact = self.root/'backfill.json'
        changed = dict(self.message, author={'id':'TEST-different'}, content='GEX AAOI please intraday')
        artifact.write_text(json.dumps([changed]))
        self.mod.run_research_context(root=self.root, grant=GRANT, source='discord', artifact=artifact, received_at='2026-09-24T16:30:00Z')
        req = rw.read_watchlist(self.db)['research_requests'][0]
        self.assertEqual(req['requester'], self.message['author'])
        self.assertEqual(req['original_context']['raw_text'], self.message['content'])
