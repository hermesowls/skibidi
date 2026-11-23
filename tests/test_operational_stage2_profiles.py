"""Offline real-producer profile regressions; no operational activation."""
import unittest
from test_step5_kian_repair import ProducerContext


def policy():
    return dict(schema_version=2, mode='paper_test', origin='user_chosen_research',
        approval='TEST_OFFLINE_ONLY', min_premium=50000, min_size=500,
        dte_min=1, dte_max=14, otm_required=True, max_otm_fraction=None,
        max_age_seconds=120, calendar_zone='America/New_York',
        complex_handling='reject', ask_handling='report_only',
        premium_definition='single_print_usd', size_definition='single_print_contracts',
        volume_definition='aggregate_contract_session')


class PersistedProfiles(unittest.TestCase):
    def test_authenticated_profile_api_roundtrip(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from starlette.testclient import TestClient
        from hermes_cli import web_server as server
        with tempfile.TemporaryDirectory() as tmp, patch.object(server,'_analyst_db_path',return_value=Path(tmp)/'TEST.sqlite'):
            client=TestClient(server.app)
            url='/api/analyst-trader/research-profiles'
            self.assertEqual(client.post(url,json={'name':'Default TEST'}).status_code,401)
            headers={'X-Hermes-Session-Token':server._SESSION_TOKEN}
            response=client.post(url,json={'name':'Default TEST'},headers=headers)
            self.assertEqual(response.status_code,200,response.text)
            first=response.json()
            edited=client.post(url,json={'name':'Default TEST','base_version':first['version_id'],
                'changes':{'max_otm_fraction':.1}},headers=headers)
            self.assertEqual(edited.status_code,200,edited.text)
            clone=client.post(url,json={'name':'Clone','base_version':first['version_id']},headers=headers)
            self.assertEqual(clone.status_code,200)
            self.assertEqual(len(client.get(url,headers=headers).json()['profiles']),3)
            self.assertEqual(client.get(url,params={'version_id':first['version_id']},headers=headers).json(),first)
            self.assertEqual(client.post(url,json={'name':'No authority','authorized':True},headers=headers).status_code,400)
            import os, json
            if os.environ.get('ASTRA_SANDBOX'):
                (Path(os.environ['ASTRA_SANDBOX'])/'profiles-api.json').write_text(json.dumps(dict(
                    first=first, edited=edited.json(), clone=clone.json(),
                    listed=client.get(url,headers=headers).json())))

    def test_malformed_api_values_are_client_errors(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from starlette.testclient import TestClient
        from hermes_cli import web_server as server
        with tempfile.TemporaryDirectory() as tmp, patch.object(server,'_analyst_db_path',return_value=Path(tmp)/'TEST.sqlite'):
            client=TestClient(server.app, raise_server_exceptions=False)
            headers={'X-Hermes-Session-Token':server._SESSION_TOKEN}
            url='/api/analyst-trader/research-profiles'
            for key, value in [('base_version',{}),('base_version',[]),('base_version',1),('base_version',False),('base_version',''),('changes',[]),('changes',False),('changes',None)]:
                with self.subTest(key=key,value=value):
                    response=client.post(url,json={'name':'Bad',key:value},headers=headers)
                    self.assertEqual(response.status_code,400,response.text)
            self.assertEqual(client.get(url,headers=headers).json()['profiles'],[])

    def test_named_create_edit_clone_select_persisted_immutable(self):
        import tempfile
        from pathlib import Path
        from plugins.analyst_trader.db import AnalystDatabase
        from plugins.analyst_trader import research_profiles as profiles
        with tempfile.TemporaryDirectory() as tmp:
            db=AnalystDatabase(Path(tmp)/'TEST.sqlite')
            first=profiles.create(db, 'Default TEST')
            self.assertEqual(first['profile']['kian_research'],policy())
            edited=profiles.create(db, 'Default TEST', {'max_otm_fraction':.1}, base_version=first['version_id'])
            clone=profiles.create(db, 'Deep OTM', base_version=first['version_id'])
            reopened=AnalystDatabase(db.db_path)
            self.assertEqual(len(profiles.list_profiles(reopened)),3)
            self.assertEqual(profiles.select(reopened, first['version_id']),first)
            self.assertNotEqual(edited['version_id'],first['version_id'])
            self.assertNotEqual(clone['version_id'],first['version_id'])
            self.assertIsNone(profiles.select(reopened, first['version_id'])['profile']['kian_research']['max_otm_fraction'])
            with self.assertRaises(ValueError):
                profiles.create(db,'Bad', {'paper_lifecycle':{'approval':'TEST_OFFLINE_ONLY'}})
            with self.assertRaises(ValueError):
                profiles.create(db,'Bad', {'mode':'live'})


class NullablePolicy(unittest.TestCase):
    def run_case(self, p, **kwargs):
        ProducerContext().run_producers(True, research_policy=p, publish=False,
            expiry='2026-10-02', **kwargs)

    def test_default_uncapped_deep_otm_real_producers(self):
        def probe(db, results):
            for result in results:
                candidate = result['research_candidate']
                self.assertGreater(candidate['otm_fraction'], .1)
                self.assertFalse(candidate['execution_authorized'])
                self.assertFalse(candidate['verified_buy'])
        self.run_case(policy(), change={'spot_price':50.}, candidate_probe=probe)

    def test_finite_cap_same_observations_rejected(self):
        self.run_case(dict(policy(),max_otm_fraction=.1), change={'spot_price':50.},expected='REJECTED')

    def test_named_selection_real_producers_and_edit_preserves_decisions(self):
        from unittest.mock import patch
        from datetime import datetime
        from plugins.analyst_trader import research_profiles as profiles
        def factory(db, now):
            class Clock(datetime):
                @classmethod
                def now(cls, tz=None): return now
            with patch.object(profiles,'datetime',Clock):
                return profiles.create(db,'Default TEST')
        def probe(db, results):
            from plugins.analyst_trader.learning_store import replay_decision
            for result in results:
                decision=result['learning_decision']
                self.assertEqual(result['research_candidate']['profile_name'],'Default TEST')
                before=replay_decision(db,decision['decision_id'])
                profiles.create(db,'Edited',{'max_otm_fraction':.1},base_version=decision['profile_version'])
                self.assertEqual(replay_decision(db,decision['decision_id']),before)
                self.assertIsNone(profiles.select(db,decision['profile_version'])['profile']['kian_research']['max_otm_fraction'])
        ProducerContext().run_producers(True,publish=False,expiry='2026-10-02',
            change={'spot_price':50.},selected_profile_factory=factory,candidate_probe=probe)

    def test_default_threshold_failures_and_unknowns(self):
        for change, expected in [({'size':499},'REJECTED'),({'volume':0},'REJECTED'),
            ({'open_interest':None},'INCOMPLETE'),({'size':0},'INCOMPLETE'),
            ({'complex_trade':True},'REJECTED')]:
            with self.subTest(change=change): self.run_case(policy(),change=change,expected=expected)
        self.run_case(dict(policy(),min_premium=1000001),expected='REJECTED')
        self.run_case(dict(policy(),dte_max=1),expected='REJECTED')

    def test_put_otm_direction(self):
        self.run_case(policy(),option_side='P',change={'spot_price':150.})
        self.run_case(policy(),option_side='P',change={'spot_price':100.},expected='REJECTED')

    def test_invalid_spot_early_abstention(self):
        for spot in (0, None, float('nan'), float('inf')):
            with self.subTest(spot=spot):
                self.run_case(policy(),change={'spot_price':spot},expected='EARLY_ABSTENTION')

    def test_invalid_policies(self):
        from plugins.analyst_trader.kian_research import validate_policy
        from plugins.analyst_trader.learning_store import digest
        for key, value in [('max_otm_fraction',0),('max_otm_fraction',float('inf')),
                           ('min_size',True),('dte_min',1.5),('min_premium','50000'),
                           ('otm_required','yes'),('invented',1),('min_premium',float('nan'))]:
            p=dict(policy(), **{key:value})
            with self.subTest(key=key,value=value), self.assertRaises((ValueError,TypeError)):
                h=digest(p)
                validate_policy(dict(classification='stated_policy',source_mode='paper_test',
                    profile={'kian_research':p,'kian_policy_hash':h}),h)
        p=policy(); del p['max_otm_fraction']
        h=digest(p)
        with self.assertRaises(ValueError):
            validate_policy(dict(classification='stated_policy',source_mode='paper_test',
                profile={'kian_research':p,'kian_policy_hash':h}),h)
