"""Recorded operational cards, actual producers/dispatcher and authenticated read API."""
import json
import os
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
import test_step5_kian_repair as producer
from plugins.analyst_trader import research_profiles as profiles
from plugins.analyst_trader.alert_delivery import actionable_cards, AlertOutbox
from plugins.analyst_trader.db import AnalystDatabase


class OperationalCards(unittest.TestCase):
    def factory(self, db, now):
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None): return now
        with patch.object(profiles, 'datetime', Clock):
            return profiles.create(db, 'Original TEST')

    def test_queued_edit_clone_restart_preserves_serialized_cards(self):
        saved = {}
        def queued(db, result, publication, opts, now):
            candidate = result['research_candidate']
            self.assertIn('max_otm_fraction', candidate)
            self.assertIsNone(candidate['max_otm_fraction'])
            self.assertEqual(candidate['profile_name'], 'Original TEST')
            self.assertEqual(candidate['origin'], 'user_chosen_research')
            self.assertEqual(candidate['filter_provenance'],profiles.select(db,candidate['policy_version'])['profile']['filter_provenance'])
            def stored():
                with db._get_connection() as c:
                    return (c.execute('SELECT identity_json FROM alert_messages ORDER BY alert_id').fetchall(),
                            c.execute('SELECT card,payload FROM alert_units ORDER BY alert_id,card').fetchall())
            before = [[tuple(r) for r in rows] for rows in stored()]
            self.assertIn('Profile: Original TEST', before[1][0][1])
            self.assertIn('OTM cap: Unlimited', before[1][0][1])
            with db._get_connection() as c:
                self.assertEqual(c.execute("SELECT state FROM alert_units WHERE card='risk'").fetchone()[0], 'retryable')
            edited=profiles.create(db,'Edited capped',{'max_otm_fraction':.1},base_version=candidate['policy_version'])
            clone=profiles.create(db,'Clone',base_version=candidate['policy_version'])
            self.assertEqual(profiles.select(db,edited['version_id']),edited)
            reopened=AnalystDatabase(db.db_path)
            sends=[]
            outbox=AlertOutbox(reopened.db_path,clock=lambda:(now+timedelta(seconds=30)).timestamp())
            self.assertEqual(outbox.resume(dict(publication,publishing_authorized=False),opts['delivery_destinations'],lambda u:sends.append(u))['status'],'denied')
            self.assertEqual(sends,[])
            # Existing explicit authorization, not profile configuration, permits delivery.
            status=outbox.resume(publication,opts['delivery_destinations'],lambda u:(sends.append(u) or dict(state='succeeded',receipt='TEST-resume')))
            self.assertEqual(status['status'],'complete')
            self.assertEqual(len(sends),1)
            self.assertEqual(sends[0]['payload'],json.loads(dict(before[1])['risk']))
            self.assertEqual([[tuple(r) for r in rows] for rows in stored()],before)
            with db._get_connection() as c:
                self.assertEqual(c.execute('SELECT COUNT(*) FROM portfolio_holdings').fetchone()[0],0)
                self.assertEqual(c.execute('SELECT COUNT(*) FROM alert_messages').fetchone()[0],1)
            self.assertFalse(candidate['execution_authorized'])
            saved.update(candidate=candidate,first=profiles.select(db,candidate['policy_version']),edited=edited,clone=clone)
            return True
        def history(db, results):
            from hermes_cli import web_server as server
            from starlette.testclient import TestClient
            with patch.object(server,'_analyst_db_path',return_value=db.db_path):
                client=TestClient(server.app)
                url='/api/analyst-trader/notable-flow?limit=500'
                self.assertEqual(client.get(url).status_code,401)
                response=client.get(url,headers={'X-Hermes-Session-Token':server._SESSION_TOKEN})
                self.assertEqual(response.status_code,200)
                body=response.json()
                cards=body['flows'][0]['research_candidates']
                self.assertEqual(len(cards),2)
                self.assertTrue(all(c['profile_name']=='Original TEST' for c in cards))
                self.assertIn(saved['candidate'],cards)
                saved['history']=body
                if os.environ.get('ASTRA_SANDBOX'):
                    (Path(os.environ['ASTRA_SANDBOX'])/'operational-cards.json').write_text(json.dumps(saved))
        # Existing helper also resumes; our successful resume makes its second attempt a no-op.
        # Use unknown for helper expectation? Instead only edit in callback, actual helper resumes below.
        # Dedicated resume above is tested; helper sees no retryable unit after it.
        producer.ProducerContext().run_producers(True,expiry='2026-10-02',change={'spot_price':50.},
            selected_profile_factory=self.factory,delivery_mode='retryable',queued_probe=queued,candidate_probe=history)

    def test_rejected_and_unknown_recorded_rendering(self):
        def probe(db, results):
            for result in results:
                result = result['recommendation']
                card=actionable_cards(result)['open']['content']
                self.assertIn('Reasons: size:rejected',card)
                self.assertIn('Profile: Original TEST',card)
                legacy=dict(result,research_candidate=dict(result['research_candidate']))
                for field in ('profile_name','otm_fraction','max_otm_fraction','origin'):
                    legacy['research_candidate'].pop(field,None)
                text=actionable_cards(legacy)['open']['content']
                self.assertIn('Profile: Unknown',text)
                self.assertIn('OTM cap: Unknown',text)
        producer.ProducerContext().run_producers(True,publish=False,expiry='2026-10-02',change={'size':499},
            expected='REJECTED',selected_profile_factory=self.factory,candidate_probe=probe)
