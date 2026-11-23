import unittest, importlib.util, json, os, hashlib
from pathlib import Path
from unittest.mock import patch
import test_step5_kian_repair as producer
from test_stage2_operational_cards import OperationalCards
from plugins.analyst_trader import kian_research as current, alert_delivery as alerts
from plugins.analyst_trader.db import AnalystDatabase
E=Path(__file__).parent / 'fixtures' / 'stage2_prior_cards'
def oldmodule(name,file):
    if not os.environ.get('ASTRA_SANDBOX'):
        raise RuntimeError('Run genuine prior fixtures only with tests/stage2_card_guard.py')
    expected=json.loads((E/'provenance.json').read_text())['sha256'][file]
    assert hashlib.sha256((E/file).read_bytes()).hexdigest() == expected, 'Prior fixture hash mismatch'
    spec=importlib.util.spec_from_file_location('plugins.analyst_trader.'+name,E/file)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class Review(unittest.TestCase):
    def test_legacy_real_producer_reevaluation(self):
        old=oldmodule('review_old_research','old_research.py')
        oldalert=oldmodule('review_old_alert','old_alert.py')
        real=current.evaluate_research
        findings=[]
        for named in (False,True):
            def queued(db,result,publication,opts,now):
                from owlfred_engine import eval_ticker
                cand=result['research_candidate']; decision=result['learning_decision']
                self.assertNotIn('max_otm_fraction',cand)
                def snapshot():
                    with db._get_connection() as c:
                        return {t:[tuple(r) for r in c.execute('SELECT * FROM '+t).fetchall()] for t in ('kian_research_candidates','alert_messages','alert_units','learning_decisions')}
                before=snapshot()
                ctx={k:decision[k] for k in ('decision_id','source_id','profile_version','decision_at','inputs')}
                request=dict(authorized=True,mode='paper_test',policy_hash=cand['policy_hash'],evidence=cand['evidence'])
                error=None
                with patch.object(current,'evaluate_research',real),patch.object(alerts,'actionable_cards',newcards):
                    try:
                        eval_ticker('TEST',db_path=str(db.db_path),flow_id=cand['source_id'],publication=publication,learning_context=ctx,research_context=request,**opts)
                    except ValueError as exc: error=str(exc)
                with patch.object(current,'evaluate_research',real):
                    for field,value in (('profile_name','MUTATED'),('max_otm_fraction',.123),('source_hash','bad'),('policy_hash','bad')):
                        mutated=dict(cand,**{field:value})
                        from plugins.analyst_trader.learning_store import canonical
                        with db._get_connection() as c:
                            c.execute('UPDATE kian_research_candidates SET payload_json=? WHERE decision_id=?',(canonical(mutated),cand['decision_id']))
                        with self.assertRaises(ValueError): real(db,decision,request,now)
                        with db._get_connection() as c:
                            c.execute('UPDATE kian_research_candidates SET payload_json=? WHERE decision_id=?',(canonical(cand),cand['decision_id']))
                    for field,value in (('size',501),('premium_usd',123),('source_id','different')):
                        with self.assertRaises(ValueError): real(db,decision,dict(request,evidence=dict(cand['evidence'],**{field:value})),now)
                    with self.assertRaises(ValueError): real(db,decision,dict(request,policy_hash='bad'),now)
                self.assertEqual(snapshot(),before)
                findings.append(dict(named=named,error=error,bytes_unchanged=True,old_keys=sorted(cand)))
                # Positive compatibility invariant; stored queue bytes must remain unchanged.
                self.assertIsNone(error)
                return False
            newcards=alerts.actionable_cards
            with patch.object(current,'evaluate_research',old.evaluate_research),patch.object(alerts,'actionable_cards',oldalert.actionable_cards):
                producer.ProducerContext().run_producers(True,expiry='2026-10-02',delivery_mode='retryable',queued_probe=queued,selected_profile_factory=OperationalCards().factory if named else None)
        (Path(os.environ['ASTRA_SANDBOX'])/'legacy-reproduction.json').write_text(json.dumps(findings,indent=2))


    def test_malformed_saved_history(self):
        def probe(db,results):
            from hermes_cli import web_server as server
            from starlette.testclient import TestClient
            rec=results[0]['recommendation']; original=rec['research_candidate']; source=original['source_id']
            with db._get_connection() as c:
                bad=dict(original,decision_id='bad',profile_name={'bad':'object'},baseline_reasons='bad')
                c.execute('INSERT INTO kian_research_candidates VALUES (?,?,?)',('bad',source,json.dumps(bad)))
                c.execute('INSERT INTO kian_research_candidates VALUES (?,?,?)',('mismatch',source,json.dumps(original)))
            with patch.object(server,'_analyst_db_path',return_value=db.db_path):
                client=TestClient(server.app); url='/api/analyst-trader/notable-flow?limit=1'
                self.assertEqual(client.get(url).status_code,401)
                body=client.get(url,headers={'X-Hermes-Session-Token':server._SESSION_TOKEN}).json()
                cards=body['flows'][0]['research_candidates']
                self.assertEqual(len(cards),3)
                rendered=next(x for x in cards if x['decision_id']=='bad')
                self.assertEqual(rendered['profile_name'],'Unknown')
                self.assertEqual(rendered['baseline_reasons'],['Unknown'])
                self.assertIn(original,cards)
                (Path(os.environ['ASTRA_SANDBOX'])/'malformed-history.json').write_text(json.dumps(body))
            for value in ('bad',[{}],7):
                text=alerts.actionable_cards(dict(rec,research_candidate=dict(original,profile_name={},baseline_reasons=value,enhancement_unknowns=value)))['open']['content']
                self.assertIn('Reasons: Unknown',text); self.assertIn('Profile: Unknown',text);self.assertIn('Unknowns: Unknown',text)
        producer.ProducerContext().run_producers(True,publish=False,expiry='2026-10-02',change={'size':499},expected='REJECTED',selected_profile_factory=OperationalCards().factory,candidate_probe=probe)

    def test_bounded_history(self):
        def probe(db,results):
            from hermes_cli import web_server as server
            from starlette.testclient import TestClient
            original=results[0]['recommendation']['research_candidate']; source=original['source_id']
            with db._get_connection() as c:
                for i in range(40):
                    ident=f'bounded-{i:03}'
                    c.execute('INSERT INTO kian_research_candidates VALUES (?,?,?)',(ident,source,json.dumps(dict(original,decision_id=ident))))
            with patch.object(server,'_analyst_db_path',return_value=db.db_path):
                client=TestClient(server.app)
                body=client.get('/api/analyst-trader/notable-flow?limit=1',headers={'X-Hermes-Session-Token':server._SESSION_TOKEN}).json()
                row=body['flows'][0]
                self.assertEqual(len(row['research_candidates']),10)
                self.assertEqual(row['research_history']['total'],42)
                self.assertEqual(row['research_history']['omitted'],32)
                self.assertEqual(row['research_history']['scope'],'visible source only')
                self.assertEqual([x['decision_id'] for x in row['research_candidates']],sorted(x['decision_id'] for x in row['research_candidates']))
                (Path(os.environ['ASTRA_SANDBOX'])/'bounded-history.json').write_text(json.dumps(body))
        producer.ProducerContext().run_producers(True,publish=False,expiry='2026-10-02',selected_profile_factory=OperationalCards().factory,candidate_probe=probe)
