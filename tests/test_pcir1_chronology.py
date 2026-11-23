"""PCIR-1: TEST native HTTP boundary and saved-context admission invariants."""
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from plugins.analyst_trader import research_watchlist as rw

RECEIPT = '2026-09-24T17:00:00Z'
GRANT = dict(authorized=True, evidence_cohort='TEST')
CFG = {'sources': {'discord_notable_flow': {'enabled': True, 'channels': {'456': 'TEST'}}}}

class Chronology(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('pcir1_coordinator', Path(os.environ['HERMES_HOME'])/'scripts/flowseeker_unified_ingestion.py')
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)

    def exercise(self, message_time, edit=None, receipt=RECEIPT, valid=False):
        for native in (False, True):
            with self.subTest(native=native), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                seed = root/'seed.json'
                seed.write_text(json.dumps({'records': [dict(mode='TEST', provider_event_id='TEST', received_at='2026-09-24T16:00:00Z', evidence={'contract_symbol':'AAOI260925C00100000'}, raw={})]}))
                db = root/'TEST/watchlist.sqlite'
                rw.seed(db, seed)
                msg = dict(id='123', channel_id='456', timestamp=message_time, edited_timestamp=edit, author={'id':'789'}, content='GEX AAOI please swing', embeds=[])
                raw = json.dumps([msg]).encode()
                artifact = root/'discord.json'
                artifact.write_bytes(raw)
                class Response:
                    def __enter__(self): return self
                    def __exit__(self, *args): pass
                    def read(self, n): return raw[:n]
                def run():
                    if native:
                        return self.mod.run_research_discord_page(root=root, grant=GRANT, cfg=CFG, limit=1)
                    return self.mod.run_research_context(root=root, grant=GRANT, source='discord', artifact=artifact, received_at=receipt)
                with patch.object(self.mod, 'urlopen', return_value=Response()) as send, patch.object(self.mod, 'now_utc', return_value=receipt), patch.dict(os.environ, {'DISCORD_BOT_TOKEN':'TEST'}):
                    for _ in range(2):
                        if valid:
                            run()
                        else:
                            with self.assertRaises(ValueError): run()
                    self.assertEqual(send.call_count, 1 if native else 0)
                tracked = rw.read_watchlist(db)
                self.assertEqual(tracked['context_count'], 1 if valid else 0)
                self.assertEqual(tracked['snapshot_count'], 0)
                self.assertEqual(tracked['observation_count'], 1)
                self.assertEqual(tracked['pending_contracts'], ['AAOI260925C00100000'])
                if valid:
                    self.assertEqual(tracked['contexts'][0]['request_ticket']['status'], 'RESEARCH_REQUEST_RECORDED')
                    self.assertEqual(tracked['contexts'][0]['freshness'], 'HISTORICAL_CONTEXT_NOT_ACTIONABLE')
                elif native:
                    directory = db.parent/'discord-native-page'
                    self.assertEqual((directory/'raw.json').read_bytes(), raw)
                    state = json.loads((directory/'result.json').read_text())
                    self.assertEqual(state['status'], 'QUARANTINED_INVALID_OR_UNKNOWN_CONTEXT')
                    self.assertEqual(state['coverage'], 'NONE_QUARANTINED')

    def test_versions_and_atomic_page_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            seed = root/'seed.json'
            seed.write_text(json.dumps({'records': [dict(mode='TEST', provider_event_id='TEST', received_at='2026-09-24T16:00:00Z', evidence={'contract_symbol':'AAOI260925C00100000'}, raw={})]}))
            db = root/'TEST/watchlist.sqlite'
            rw.seed(db, seed)
            artifact = root/'discord.json'
            message = dict(id='123', channel_id='456', timestamp='2026-09-24T16:00:00Z', author={'id':'789'}, content='GEX AAOI please swing')
            def run(rows):
                artifact.write_text(json.dumps(rows))
                return self.mod.run_research_context(root=root, grant=GRANT, source='discord', artifact=artifact, received_at=RECEIPT)
            revised = dict(message, edited_timestamp='2026-09-24T16:30:00Z', content='GEX AAOI please swing revised')
            for rows in ([message], [revised], [message, revised], [revised]): run(rows)
            self.assertEqual(rw.read_watchlist(db)['context_count'], 2)
            before = db.read_bytes()
            with self.assertRaises(ValueError):
                run([dict(message, id='999'), dict(message, id='888', edited_timestamp='2026-09-25T17:00:00Z')])
            self.assertEqual(db.read_bytes(), before)
            self.assertEqual(rw.read_watchlist(db)['context_count'], 2)

    def test_future_message(self): self.exercise('2026-09-25T16:00:00Z')
    def test_future_edit(self): self.exercise('2026-09-24T16:00:00Z', '2026-09-25T16:00:00Z')
    def test_edit_before_message(self): self.exercise('2026-09-24T16:00:00Z', '2026-09-24T15:59:00Z')
    def test_offset_equal_instants(self): self.exercise('2026-09-24T13:00:00-04:00', '2026-09-24T18:00:00+01:00', valid=True)
    def test_valid_edit(self): self.exercise('2026-09-24T16:00:00Z', '2026-09-24T16:30:00Z', valid=True)
    def test_valid_unedited(self): self.exercise('2026-09-24T16:00:00Z', valid=True)
    def test_invalid_receipt(self):
        for receipt in ('bad', '2026-09-24T17:00:00', None, 123):
            with self.subTest(receipt=receipt): self.exercise('2026-09-24T16:00:00Z', receipt=receipt)
    def test_unknown_message(self):
        for value in (None, 'bad', '2026-09-24T16:00:00', 123):
            with self.subTest(value=value): self.exercise(value)
    def test_invalid_edit(self):
        for value in ('bad', '2026-09-24T16:30:00', 123):
            with self.subTest(value=value): self.exercise('2026-09-24T16:00:00Z', value)
