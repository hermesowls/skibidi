"""Authenticated backend recordings for mounted real api.ts transport replay."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class TransportRecordings(unittest.TestCase):
    def test_export_authenticated_requests(self):
        from hermes_cli import web_server as server
        from starlette.testclient import TestClient
        with tempfile.TemporaryDirectory() as tmp, patch.object(server, '_analyst_db_path', return_value=Path(tmp)/'TEST.sqlite'):
            client = TestClient(server.app)
            url = '/api/analyst-trader/research-profiles'
            headers = {'X-Hermes-Session-Token': server._SESSION_TOKEN}
            recordings = []
            def request(method, suffix='', body=None, authenticated=True):
                response = client.request(method, url+suffix, json=body, headers=headers if authenticated else {})
                recordings.append(dict(method=method, url=url+suffix, body=body, status=response.status_code, response=response.json()))
                return response
            self.assertEqual(request('GET', authenticated=False).status_code, 401)
            request('GET')
            fields = dict(min_premium=50000,min_size=500,dte_min=1,dte_max=14,otm_required=True,max_otm_fraction=None)
            first = request('POST', body=dict(name='Default TEST',changes=fields)).json()
            from urllib.parse import quote
            def select(version): return request('GET','?version_id='+quote(version,safe='')).json()
            select(first['version_id']); request('GET'); select(first['version_id'])
            from test_stage2_preview import EVIDENCE
            preview = request('POST','/preview',body=dict(version_id=first['version_id'],evidence=EVIDENCE)).json()
            self.assertEqual(preview['baseline_status'],'QUALIFIED')
            edited = request('POST', body=dict(name='Renamed capped',changes=dict(fields,max_otm_fraction=.1),base_version=first['version_id'])).json()
            select(edited['version_id']); request('GET')
            capped = request('POST','/preview',body=dict(version_id=edited['version_id'],evidence=EVIDENCE)).json()
            self.assertEqual(capped['baseline_status'],'REJECTED')
            select(first['version_id'])
            clone = request('POST',body=dict(name='Clone',changes={},base_version=first['version_id'])).json()
            select(clone['version_id']); request('GET')
            error = request('POST',body=dict(name='Bad',changes=dict(fields,max_otm_fraction=0),base_version=clone['version_id']))
            self.assertEqual(error.status_code,400)
            self.assertIsNone(first['profile']['kian_research']['max_otm_fraction'])
            self.assertEqual(select(first['version_id']),first)
            if os.environ.get('ASTRA_SANDBOX'):
                Path(os.environ['ASTRA_SANDBOX'],'profiles-transport.json').write_text(json.dumps(dict(recordings=recordings,first=first,edited=edited,clone=clone)))
