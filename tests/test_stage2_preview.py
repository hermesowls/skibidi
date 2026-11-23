"""Actual authenticated preview with disposable persistence; no business mocks."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

EVIDENCE = dict(ticker='TEST', strike=105., call_put='C', expiration='2026-09-30',
    contract_symbol='TEST260930C00105000', observed_at='2026-09-23T15:00:00+00:00',
    spot_observed_at='2026-09-23T15:00:00+00:00', spot_price=50., premium_usd=1000000.,
    size=500, volume=1000, open_interest=0, complex_trade=False, reported_side='ask',
    premium_definition='single_print_usd',size_definition='single_print_contracts',
    volume_definition='aggregate_contract_session')

class Preview(unittest.TestCase):
    def test_selected_versions_pure_preview(self):
        from starlette.testclient import TestClient
        from hermes_cli import web_server as server
        with tempfile.TemporaryDirectory() as tmp, patch.object(server,'_analyst_db_path',return_value=Path(tmp)/'TEST.sqlite'):
            client=TestClient(server.app)
            headers={'X-Hermes-Session-Token':server._SESSION_TOKEN}
            url='/api/analyst-trader/research-profiles'
            first=client.post(url,json={'name':'Original TEST'},headers=headers).json()
            second=client.post(url,json={'name':'Renamed capped','base_version':first['version_id'],'changes':{'max_otm_fraction':.1}},headers=headers).json()
            def dump():
                with sqlite3.connect(Path(tmp)/'TEST.sqlite') as c: return list(c.iterdump())
            before=dump()
            body=dict(version_id=first['version_id'],evidence=EVIDENCE)
            self.assertEqual(client.post(url+'/preview',json=body).status_code,401)
            a=client.post(url+'/preview',json=body,headers=headers)
            self.assertEqual(a.status_code,200,a.text)
            a=a.json()
            b=client.post(url+'/preview',json=dict(body,version_id=second['version_id']),headers=headers).json()
            self.assertEqual(a['baseline_status'],'QUALIFIED')
            self.assertEqual(b['baseline_status'],'REJECTED')
            self.assertIn('otm:rejected',b['baseline_reasons'])
            self.assertEqual(a['profile_name'],'Original TEST')
            self.assertEqual(a['policy_version'],first['version_id'])
            self.assertEqual(a['policy_hash'],first['profile']['kian_policy_hash'])
            self.assertIsNone(a['max_otm_fraction'])
            self.assertGreater(a['otm_fraction'],.1)
            self.assertFalse(a['execution_authorized'])
            self.assertEqual(a['enhanced_status'],'UNKNOWN')
            for change in ({'open_interest':None},{'spot_price':0},{'size':None}):
                response=client.post(url+'/preview',json=dict(body,evidence=dict(EVIDENCE,**change)),headers=headers)
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(response.json()['baseline_status'],'INCOMPLETE')
            for bad in (dict(body,authorized=True),dict(body,evidence=[]),dict(body,version_id='unknown'),dict(body,evidence=dict(EVIDENCE,source='live'))):
                self.assertEqual(client.post(url+'/preview',json=bad,headers=headers).status_code,400)
            self.assertEqual(client.post(url+'/preview',json=body,headers=headers).json(),a)
            for value in ('NaN', 'Infinity'):
                raw=json.dumps(body).replace('50.0',value)
                self.assertEqual(client.post(url+'/preview',content=raw,headers=headers).status_code,400)
            self.assertEqual(client.post(url+'/preview',content='x'*8193,headers=headers).status_code,400)
            from plugins.analyst_trader.learning_store import digest
            self.assertEqual(a['raw_source_hash'],digest(dict(kind='declared_TEST_evidence',evidence=EVIDENCE)))
            self.assertEqual(a['source_hash'],digest(a['evidence']))
            self.assertEqual(a['source_hash'],b['source_hash'])
            self.assertEqual(dump(),before,'Preview must not create or change any operational records')
