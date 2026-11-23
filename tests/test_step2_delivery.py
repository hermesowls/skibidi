"""Offline TEST producer-to-SQLite-to-transport acceptance. No provider access."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from typing import Any

import autonomous_risk_manager as arm
from plugins.analyst_trader.db import AnalystDatabase


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'TEST.sqlite'
        self.db = AnalystDatabase(self.path)
        self.now = [1000.0]
        self.rec = dict(ticker='TEST', strike=100, call_put='C', expiration='2026-10-16',
                        entry_price=2, tp1_price=2.5, tp2_price=3, stop_loss_price=1.5,
                        flow_id='TEST-flow', contract_symbol='TEST261016C00100000')
        self.db.save_notable_flow(dict(self.rec, source='TEST-observed', premium_usd=1000000,
                                     entry_contract_price=2, flow_score=90))
        self.auth = dict(publishing_authorized=True, alert_id='TEST-alert', revision=1,
                         policy_version='TEST-policy', flow_id='TEST-flow')
        self.destinations = [('discord', 'TEST-channel'), ('telegram', 'TEST-chat')]
        self.calls = []

    def manager(self, transport) -> Any:
        # Only external enrichment constructors are replaced. Actual producer,
        # formatter, admission, SQLite state, claims and retries execute unchanged.
        with patch('autonomous_risk_manager.DiscordPublisher'), \
             patch('plugins.analyst_trader.dynamic_shadow_quant.DynamicShadowQuantEngine'), \
             patch('llm_deep_dive_analyzer.LLMDeepDiveAnalyzer'):
            return arm.AutonomousRiskManager(str(self.path), delivery_transport=transport,
                delivery_destinations=self.destinations, delivery_clock=lambda: self.now[0])

    def transport(self, unit):
        self.calls.append((unit['platform'], unit['card']))
        if unit['platform'] == 'telegram' and self.now[0] == 1000:
            return dict(state='retryable', error='TEST definite rejection', retry_after=10)
        return dict(state='succeeded', receipt='TEST-receipt-' + str(len(self.calls)))

    def test_evaluator_propagates_publication_separately_from_execution(self):
        m = self.manager(self.transport)
        m.quant_engine.evaluate_ticker_complete_quant.return_value = {'is_a_plus_dream_setup': True}
        m.deep_dive_analyzer.analyze_candidate_deep_dive.return_value = {}
        args: dict[str, Any] = dict(ticker='TEST', strike=100, call_put='C', expiration='2026-10-16', dte=27,
                    premium_usd=1000000, entry_price=2, spot_price=100)
        result = m.evaluate_candidate_end_to_end(**args, publication=self.auth)
        self.assertEqual(result['alert_delivery']['status'], 'partial')
        self.assertIs(result['alert_published'], False)
        self.assertIsNone(result['paper_trade'])
        self.assertEqual(len(self.calls), 4)
        denied = m.evaluate_candidate_end_to_end(**args)
        self.assertEqual(denied['alert_delivery']['status'], 'denied')
        self.assertIs(denied['alert_published'], False)
        self.assertEqual(len(self.calls), 4)
        self.now[0] += 60
        restarted = self.manager(self.transport)
        restarted.quant_engine.evaluate_ticker_complete_quant.return_value = {'is_a_plus_dream_setup': True}
        restarted.deep_dive_analyzer.analyze_candidate_deep_dive.return_value = {}
        complete = restarted.evaluate_candidate_end_to_end(**args, publication=self.auth)
        self.assertEqual(complete['alert_delivery']['status'],'complete')
        self.assertIs(complete['alert_published'],True)
        self.assertIsNone(complete['paper_trade'])
        self.assertEqual(len(self.calls),6)
        restarted.evaluate_candidate_end_to_end(**args, publication=self.auth)
        self.assertEqual(len(self.calls),6)
        print('TEST_EVALUATOR_TRACER: partial -> restart -> complete; Discord=2 Telegram=4; zero repeat after receipt')

    def test_conflicts_revisions_and_admission(self):
        m = self.manager(self.transport)
        self.assertEqual(m.publish_actionable_alert(self.rec)['status'], 'denied')
        self.assertEqual(m.publish_actionable_alert(self.rec, publication=dict(self.auth, publishing_authorized=1))['status'], 'denied')
        m.delivery_destinations = ()
        self.assertEqual(m.publish_actionable_alert(self.rec, publication=self.auth)['status'], 'blocked')
        m.delivery_destinations = self.destinations
        m.publish_actionable_alert(self.rec, publication=self.auth)
        with self.assertRaisesRegex(ValueError, 'CONFLICT'):
            m.publish_actionable_alert(dict(self.rec, entry_price=9), publication=self.auth)
        with self.assertRaisesRegex(ValueError, 'revision'):
            m.publish_actionable_alert(self.rec, publication=dict(self.auth, revision=2))
        with self.db._get_connection() as c:
            c.execute("UPDATE notable_flow SET is_quarantined=1 WHERE flow_id='TEST-flow'")
            c.commit()
        self.now[0] += 60
        before = len(self.calls)
        result = m.publish_actionable_alert(self.rec, publication=self.auth)
        self.assertEqual(len(self.calls), before)
        self.assertTrue(all(u['state'] in ('succeeded','permanent') for u in result['units']))
        with self.assertRaisesRegex(ValueError, 'SOURCE_NOT_ELIGIBLE'):
            m.publish_actionable_alert(self.rec, publication=dict(self.auth, alert_id='TEST-quarantine'))

    def test_unknown_requires_scoped_audited_resolution(self):
        from plugins.analyst_trader.alert_delivery import AlertOutbox
        m = self.manager(lambda unit: (_ for _ in ()).throw(TimeoutError('TEST timeout')))
        result = m.publish_actionable_alert(self.rec, publication=self.auth)
        self.assertEqual(result['status'], 'uncertain')
        self.assertTrue(all(u['state']=='unknown' for u in result['units']))
        box = AlertOutbox(self.path, clock=lambda: self.now[0])
        key = ('TEST-alert',1,'discord','TEST-channel','open')
        resolution = dict(operator='TEST-operator', policy_version='TEST-resolution-v1',
                          reason='TEST provider transcript checked', authorized=True, workers_quiesced=True,
                          scope=list(key), decision='confirmed_delivered', receipt='TEST-reconciled')
        with self.assertRaises(ValueError):
            box.resolve(key, dict(resolution, authorized=False))
        with self.assertRaises(ValueError):
            box.resolve(key, dict(resolution, workers_quiesced=False))
        box.resolve(key, resolution)
        with self.assertRaises(ValueError):
            box.resolve(key, resolution)
        with self.db._get_connection() as c:
            audit = c.execute('SELECT * FROM alert_resolutions').fetchall()
        self.assertEqual(len(audit),1)
        self.assertEqual(box.summary('TEST-alert',1)['units'][0]['receipt'], 'TEST-reconciled')

    def test_crash_boundaries_and_receipt_commit_failure(self):
        from plugins.analyst_trader.alert_delivery import AlertOutbox, actionable_cards
        box = AlertOutbox(self.path, clock=lambda: self.now[0])
        box.enqueue(self.rec, self.auth, self.destinations, actionable_cards(self.rec))
        # SQLite fault after claim, before intent: real state transition, not mock.
        with self.db._get_connection() as c:
            c.execute("CREATE TRIGGER TEST_before_intent BEFORE UPDATE OF send_intent ON alert_units WHEN NEW.send_intent IS NOT NULL BEGIN SELECT RAISE(ABORT,'TEST crash before send'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            box.drain('TEST-alert',1,self.transport,limit=1)
        self.assertEqual(self.calls,[])
        self.assertEqual(box.summary('TEST-alert',1)['units'][0]['state'],'inflight')
        with self.db._get_connection() as c:
            c.execute('DROP TRIGGER TEST_before_intent')
        self.now[0] += 61
        # Provider accepted but SQLite rejects the receipt update.
        with self.db._get_connection() as c:
            c.execute("CREATE TRIGGER TEST_receipt BEFORE UPDATE OF receipt ON alert_units WHEN NEW.receipt IS NOT NULL BEGIN SELECT RAISE(ABORT,'TEST lost receipt commit'); END")
        result = box.drain('TEST-alert',1,self.transport,limit=1)
        self.assertEqual(result['status'],'uncertain')
        self.assertEqual(len(self.calls),1)
        with self.db._get_connection() as c:
            c.execute('DROP TRIGGER TEST_receipt')
        self.now[0] += 61
        box = AlertOutbox(self.path, clock=lambda: self.now[0])
        result = box.drain('TEST-alert',1,self.transport)
        self.assertEqual(result['units'][0]['state'],'unknown')
        self.assertEqual(self.calls.count(('discord','open')),1)
        self.assertEqual(result['status'],'uncertain')
        before = len(self.calls)
        box.drain('TEST-alert',1,self.transport)
        self.assertEqual(len(self.calls),before)

    def test_real_transport_offline_envelopes(self):
        from plugins.analyst_trader.alert_delivery import ProviderTransport
        requests = []
        replies = [(200,{}, {'id':'123','channel_id':'TEST-channel'}),
                   (200,{}, {'ok':False,'error_code':400}),
                   (429,{'Retry-After':'17'}, {'retry_after':17}),
                   (200,{}, {'ok':True,'result':{'message_id':123,'chat':{'id':'TEST-chat'}}}),
                   (200,{}, {'message':'error','code':500}),
                   (503,{}, {'message':'backend unavailable'})]
        def request(url,payload,headers,timeout):
            requests.append((url,payload,headers,timeout))
            return replies.pop(0)
        transport = ProviderTransport(discord_token='TEST',telegram_token='TEST', request=request)
        unit = dict(platform='discord',destination='TEST-channel',payload={'content':'TEST ONLY'})
        self.assertEqual(transport(unit)['state'],'succeeded')
        unit['platform']='telegram'; unit['destination']='TEST-chat'
        self.assertEqual(transport(unit)['state'],'permanent')
        self.assertEqual(transport(unit)['retry_after'],17)
        self.assertEqual(transport(unit)['receipt'],'123')
        unit['platform']='discord'; unit['destination']='TEST-channel'
        self.assertEqual(transport(unit)['state'],'unknown')
        self.assertEqual(transport(unit)['state'],'unknown')
        self.assertEqual(len(requests),6)
        self.assertTrue(all(r[3]==10 for r in requests))
        self.assertEqual(ProviderTransport()(unit)['state'],'permanent')

    def test_legacy_public_telegram_cannot_bypass_durable_units(self):
        m = self.manager(self.transport)
        self.assertEqual(m.publish_telegram_alert(self.rec, publication=None)['status'], 'denied')
        result = m.publish_telegram_alert(self.rec, publication=self.auth)
        self.assertEqual(result['status'],'pending')
        self.assertEqual(len(result['units']),2)
        self.assertTrue(all(u['platform']=='telegram' for u in result['units']))
        self.assertEqual(len(self.calls),2)
        self.now[0] += 60
        self.assertEqual(m.publish_telegram_alert(self.rec, publication=self.auth)['status'],'complete')
        self.assertEqual(len(self.calls),4)
        self.assertEqual(m.publish_position_exit_alert('TEST','TEST-contract','TP1',25,2.5,2,'Trim', publication=None)['status'],'denied')
        with self.assertRaisesRegex(ValueError, 'OCC identity mismatch'):
            m.publish_position_exit_alert('TEST','TEST-contract','TP1',25,2.5,2,'Trim',
                publication=dict(self.auth, alert_id='TEST-position'), source_recommendation=self.rec)
        self.assertEqual(len(self.calls),4)
        result = m.publish_position_exit_alert('TEST',self.rec['contract_symbol'],'TP1',25,2.5,2,'Trim',
                    publication=dict(self.auth, alert_id='TEST-position'), source_recommendation=self.rec)
        self.assertEqual(result['status'],'complete')
        self.assertEqual(len(result['units']),2)

    def test_offline_constructor_does_not_discover_provider_secrets(self):
        with patch('autonomous_risk_manager.DiscordPublisher') as provider, \
             patch('plugins.analyst_trader.dynamic_shadow_quant.DynamicShadowQuantEngine'), \
             patch('llm_deep_dive_analyzer.LLMDeepDiveAnalyzer'):
            m = arm.AutonomousRiskManager(str(self.path))
        provider.assert_not_called()
        self.assertEqual(m.publish_actionable_alert(self.rec, publication=self.auth)['status'],'blocked')

    def test_contention_and_expired_send_intent_never_resends(self):
        import threading
        from plugins.analyst_trader.alert_delivery import AlertOutbox, actionable_cards
        box = AlertOutbox(self.path, clock=lambda: self.now[0])
        box.enqueue(self.rec, self.auth, self.destinations, actionable_cards(self.rec))
        entered, release = threading.Event(), threading.Event()
        errors = []
        def blocked(unit):
            self.calls.append((unit['platform'],unit['card']))
            # A separate SQLite write succeeds while transport is in progress.
            with sqlite3.connect(self.path,timeout=.1) as c:
                c.execute('CREATE TABLE IF NOT EXISTS TEST_no_lock(value TEXT)')
            entered.set()
            if not release.wait(5): raise AssertionError('TEST release timed out')
            return dict(state='succeeded',receipt='TEST-late-receipt')
        def worker():
            try: box.drain('TEST-alert',1,blocked,limit=1)
            except BaseException as exc: errors.append(exc)
        t = threading.Thread(target=worker)
        t.start()
        try:
            self.assertTrue(entered.wait(5))
            other = AlertOutbox(self.path, clock=lambda: self.now[0])
            other.drain('TEST-alert',1,self.transport)
            self.assertEqual(self.calls.count(('discord','open')),1)
            self.now[0] += 61
            result = other.drain('TEST-alert',1,self.transport)
            self.assertEqual(result['units'][0]['state'],'unknown')
            self.assertEqual(self.calls.count(('discord','open')),1)
        finally:
            release.set(); t.join(5)
        self.assertFalse(t.is_alive()); self.assertEqual(errors,[])
        self.assertEqual(box.summary('TEST-alert',1)['units'][0]['state'],'unknown')
        self.assertIsNone(box.summary('TEST-alert',1)['units'][0]['receipt'])

    def test_during_response_crash_restarts_unknown(self):
        from plugins.analyst_trader.alert_delivery import AlertOutbox, actionable_cards
        class Crash(BaseException): pass
        box = AlertOutbox(self.path, clock=lambda: self.now[0])
        box.enqueue(self.rec, self.auth, self.destinations, actionable_cards(self.rec))
        def crash(unit):
            self.calls.append((unit['platform'],unit['card']))
            raise Crash('TEST process dies during response')
        with self.assertRaises(Crash): box.drain('TEST-alert',1,crash,limit=1)
        self.now[0] += 61
        box = AlertOutbox(self.path, clock=lambda: self.now[0])
        result = box.drain('TEST-alert',1,self.transport)
        self.assertEqual(result['units'][0]['state'],'unknown')
        self.assertEqual(self.calls.count(('discord','open')),1)

    def test_atomic_enqueue_and_no_delivered_on_enqueue(self):
        from plugins.analyst_trader.alert_delivery import AlertOutbox, actionable_cards
        box = AlertOutbox(self.path, clock=lambda: self.now[0])
        with self.db._get_connection() as c:
            c.execute("CREATE TRIGGER TEST_enqueue BEFORE INSERT ON alert_units WHEN NEW.card='risk' BEGIN SELECT RAISE(ABORT,'TEST atomic enqueue'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            box.enqueue(self.rec,self.auth,self.destinations,actionable_cards(self.rec))
        with self.db._get_connection() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM alert_units').fetchone()[0],0)
            self.assertEqual(c.execute('SELECT count(*) FROM alert_messages').fetchone()[0],0)
            c.execute('DROP TRIGGER TEST_enqueue')
        result = box.enqueue(self.rec,self.auth,self.destinations,actionable_cards(self.rec))
        self.assertEqual(result['status'],'pending')
        self.assertTrue(all(u['attempts']==0 and u['receipt'] is None for u in result['units']))
        self.assertEqual(self.calls,[])

    def test_batch_retry_budget_and_partial_card_permanent_failure(self):
        from plugins.analyst_trader.alert_delivery import AlertOutbox, actionable_cards
        box = AlertOutbox(self.path, clock=lambda: self.now[0])
        box.enqueue(self.rec,self.auth,self.destinations,actionable_cards(self.rec))
        def transport(unit):
            self.calls.append((unit['platform'],unit['card']))
            if unit['card']=='risk': return dict(state='permanent',error='TEST forbidden')
            if unit['platform']=='telegram': return dict(state='retryable',error='TEST 429',retry_after=17)
            return dict(state='succeeded',receipt='TEST-ack')
        result = box.drain('TEST-alert',1,transport,limit=1)
        self.assertEqual(len(self.calls),1)
        self.assertEqual(result['status'],'partial')
        for limit in (0,101,True):
            with self.assertRaises(ValueError): box.drain('TEST-alert',1,transport,limit=limit)
        box.drain('TEST-alert',1,transport)
        self.assertEqual(len(self.calls),4)
        box.drain('TEST-alert',1,transport)
        self.assertEqual(len(self.calls),4)
        self.now[0] += 17
        box.drain('TEST-alert',1,transport)
        self.assertEqual(len(self.calls),5)
        self.now[0] += 17
        result = box.drain('TEST-alert',1,transport)
        self.assertEqual(len(self.calls),6)
        self.now[0] += 10000
        box.drain('TEST-alert',1,transport)
        self.assertEqual(len(self.calls),6)
        self.assertEqual(result['status'],'partial')
        self.assertEqual([u['attempts'] for u in result['units']],[1,1,3,1])

    def test_revisions_and_operator_resolution_atomicity(self):
        from plugins.analyst_trader.alert_delivery import AlertOutbox
        m = self.manager(lambda unit: dict(state='unknown',error='TEST lost ACK'))
        m.publish_actionable_alert(self.rec,publication=self.auth)
        box = AlertOutbox(self.path,clock=lambda:self.now[0])
        key=('TEST-alert',1,'discord','TEST-channel','open')
        auth=dict(authorized=True,workers_quiesced=True,scope=list(key),operator='TEST',policy_version='TEST',reason='TEST verified no message',decision='confirmed_unsent')
        with self.assertRaises(ValueError): box.resolve(key,dict(auth,scope=['wrong']))
        with self.db._get_connection() as c:
            c.execute("CREATE TRIGGER TEST_resolution BEFORE INSERT ON alert_resolutions BEGIN SELECT RAISE(ABORT,'TEST audit failure'); END")
        with self.assertRaises(sqlite3.IntegrityError): box.resolve(key,auth)
        self.assertEqual(box.summary('TEST-alert',1)['units'][0]['state'],'unknown')
        with self.db._get_connection() as c: c.execute('DROP TRIGGER TEST_resolution')
        box.resolve(key,auth)
        self.assertEqual(box.summary('TEST-alert',1)['units'][0]['state'],'retryable')
        revision=dict(self.auth,revision=2,revision_reason='TEST intentional correction')
        result=m.publish_actionable_alert(dict(self.rec,tp1_price=2.6),publication=revision)
        self.assertEqual(result['revision'],2)
        self.assertEqual(box.summary('TEST-alert',1)['units'][0]['state'],'retryable')

    def test_http_wrapper_and_rate_limit_date_parsing(self):
        from plugins.analyst_trader.alert_delivery import ProviderTransport
        from io import BytesIO
        from email.message import Message
        from urllib.error import HTTPError
        class Response(BytesIO):
            code = 200
            headers = {'Content-Type':'application/json'}
        response = Response(b'{"id":"123","channel_id":"TEST-channel"}')
        with patch('urllib.request.build_opener') as build:
            build.return_value.open.return_value = response
            t = ProviderTransport(discord_token='TEST')
            unit=dict(platform='discord',destination='TEST-channel',payload={'content':'TEST'})
            self.assertEqual(t(unit)['state'],'succeeded')
            request = build.return_value.open.call_args.args[0]
            self.assertEqual(request.method,'POST')
            self.assertEqual(json.loads(request.data)['allowed_mentions'],{'parse':[]})
            self.assertTrue(response.closed)
            headers=Message(); headers['Retry-After']='Thu, 01 Jan 1970 00:17:00 GMT'
            build.return_value.open.side_effect = HTTPError('https://TEST.invalid',429,'TEST',headers,BytesIO(b'{}'))
            t.clock=lambda:1000
            self.assertEqual(t(unit)['retry_after'],20)
        for response in [(200,{},True),(200,{}, {'id':'123','channel_id':'WRONG'}),
                         (200,{}, {'ok':True,'result':{'message_id':True}}),
                         (429,{},{}),(408,{},{}),(302,{}, {})]:
            with self.subTest(response=response):
                t=ProviderTransport(discord_token='TEST',request=lambda *args:response)
                self.assertEqual(t(unit)['state'],'unknown')

    def test_missing_provider_and_ineligible_evidence(self):
        m = self.manager(None)
        result=m.publish_actionable_alert(self.rec,publication=self.auth)
        self.assertEqual(result['status'],'failed')
        self.assertTrue(all(u['state']=='permanent' and not u['receipt'] for u in result['units']))
        self.assertEqual(self.calls,[])
        for value in (1,2,-1):
            with self.subTest(quarantine=value):
                with self.db._get_connection() as c:
                    c.execute('UPDATE notable_flow SET is_quarantined=? WHERE flow_id=?',(value,'TEST-flow')); c.commit()
                with self.assertRaisesRegex(ValueError,'SOURCE_NOT_ELIGIBLE'):
                    m.publish_actionable_alert(self.rec,publication=dict(self.auth,alert_id='TEST-new'))
        with self.db._get_connection() as c:
            c.execute('UPDATE notable_flow SET is_quarantined=0,final_outcome=NULL WHERE flow_id=?',('TEST-flow',)); c.commit()
        with self.assertRaisesRegex(ValueError,'SOURCE_NOT_ELIGIBLE'):
            m.publish_actionable_alert(self.rec,publication=dict(self.auth,alert_id='TEST-null'))
        with self.db._get_connection() as c:
            c.execute("UPDATE notable_flow SET final_outcome='MONITORING' WHERE flow_id=?",('TEST-flow',)); c.commit()
        self.db.save_flow_candidate_analytics(dict(analytics_id='TEST-linked',flow_id='TEST-flow',ticker='TEST',is_quarantined=1))
        # The production upsert intentionally does not accept quarantine changes.
        with self.db._get_connection() as c:
            c.execute("UPDATE flow_candidate_analytics SET is_quarantined=1 WHERE analytics_id='TEST-linked'"); c.commit()
        with self.assertRaisesRegex(ValueError,'SOURCE_NOT_ELIGIBLE'):
            m.publish_actionable_alert(self.rec,publication=dict(self.auth,alert_id='TEST-linked'))

    def test_card_content_preserves_thesis_and_sizing(self):
        from plugins.analyst_trader.alert_delivery import actionable_cards
        cards=actionable_cards(dict(self.rec,clean_thesis='TEST observed thesis',
                                    sizing_rules={'micro_account':'TEST 1 contract'}))
        self.assertIn('TEST observed thesis',cards['open']['content'])
        self.assertIn('TEST 1 contract',cards['risk']['content'])

    def test_publication_identity_cannot_disagree_with_source(self):
        m=self.manager(self.transport)
        for auth in (dict(self.auth,policy_version=True),dict(self.auth,policy_version=' '),
                     dict(self.auth,flow_id=' ')):
            with self.subTest(auth=auth), self.assertRaises(ValueError):
                m.publish_actionable_alert(self.rec,publication=auth)
        with self.assertRaises(ValueError):
            m.publish_actionable_alert(dict(self.rec,flow_id='TEST-other-flow'),publication=self.auth)
        self.assertEqual(self.calls,[])

    def test_producer_partial_retry_restart(self):
        m = self.manager(self.transport)
        result = m.publish_actionable_alert(self.rec, publication=self.auth, use_graphic_card=False)
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(len(result['units']), 4)
        self.assertEqual(sum(u['state']=='succeeded' for u in result['units']), 2)
        self.assertEqual(len(self.calls), 4)
        self.now[0] += 60
        m = self.manager(self.transport)
        result = m.publish_actionable_alert(self.rec, publication=self.auth, use_graphic_card=False)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(len(self.calls), 6)
        self.assertTrue(all(u['receipt'] for u in result['units']))
        self.assertEqual(m.publish_actionable_alert(self.rec, publication=self.auth, use_graphic_card=False), result)
        self.assertEqual(len(self.calls), 6)
        print('TEST_TRACER', json.dumps(dict(status=result['status'], calls=self.calls,
              units=[{k:u[k] for k in ('platform','destination','card','state','attempts','receipt')} for u in result['units']]), sort_keys=True))
