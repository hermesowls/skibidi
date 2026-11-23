import unittest,json,os,copy
from pathlib import Path
from unittest.mock import patch
import test_step5_kian_repair as producer
from test_stage2_operational_cards import OperationalCards
from test_stage2_card_compatibility import oldmodule
from plugins.analyst_trader import alert_delivery as alerts,kian_research as current

class Extra(unittest.TestCase):
 def test_saturation_and_fresh_metadata(self):
  def probe(db,results):
   from hermes_cli import web_server as server
   from starlette.testclient import TestClient
   rec=results[0]['recommendation']; original=rec['research_candidate']
   with db._get_connection() as c:
    base=dict(c.execute('SELECT * FROM notable_flow LIMIT 1').fetchone())
    c.execute('DELETE FROM kian_research_candidates'); c.execute('DELETE FROM notable_flow')
    for s in range(12):
     sid=f'source-{s:02}'; row=dict(base,flow_id=sid,ticker=f'TEST{s}',strike=100+s)
     c.execute('INSERT INTO notable_flow ('+','.join(row)+') VALUES ('+','.join('?' for _ in row)+')',tuple(row.values()))
     for i in range(15):
      ident=f'{sid}-decision-{i:02}'; payload=dict(original,source_id=sid,decision_id=ident)
      if i==0: value='not-json'
      elif i==1: value='[]'
      elif i==2: value=json.dumps(dict(payload,source_id='other'))
      elif i==3: value=json.dumps(dict(payload,decision_id='other'))
      else:
       if i==4: payload.update(profile_name={},baseline_reasons=[{}],enhancement_unknowns={'bad':1},max_otm_fraction=True)
       if i==5: payload['max_otm_fraction']=None
       value=json.dumps(payload)
      c.execute('INSERT INTO kian_research_candidates VALUES (?,?,?)',(ident,sid,value))
    c.execute('INSERT INTO kian_research_candidates VALUES (?,?,?)',('hidden','not-visible',json.dumps(dict(original,source_id='not-visible',decision_id='hidden'))))
   calls=[]; real=server._sqlite_rows
   def observe(path,query,params):
    rows=real(path,query,params)
    if 'history_rank' in query: calls.append(dict(query=query,params=list(params),rows=len(rows)))
    return rows
   def snapshot():
    with db._get_connection() as c: return [tuple(r) for r in c.execute('SELECT * FROM kian_research_candidates ORDER BY decision_id')]
   before=snapshot()
   with patch.object(server,'_analyst_db_path',return_value=db.db_path),patch.object(server,'_sqlite_rows',side_effect=observe):
    client=TestClient(server.app); headers={'X-Hermes-Session-Token':server._SESSION_TOKEN}
    body=client.get('/api/analyst-trader/notable-flow?limit=100',headers=headers).json()
    again=client.get('/api/analyst-trader/notable-flow?limit=100',headers=headers).json()
    self.assertEqual(body,again); self.assertEqual(len(body['flows']),12)
    for row in body['flows']:
     idx=int(row['flow_id'][-2:]); h=row['research_history']; scanned=10 if idx<10 else 0
     self.assertEqual(h,dict(scope='visible source only',total=15,shown=6 if scanned else 0,omitted=15-scanned,invalid=4 if scanned else 0,truncated=True,per_source_limit=10,total_limit=100))
     self.assertEqual(h['total'],h['shown']+h['invalid']+h['omitted'])
     self.assertTrue(all(x['source_id']==row['flow_id'] for x in row['research_candidates']))
     self.assertEqual([x['decision_id'] for x in row['research_candidates']],sorted(x['decision_id'] for x in row['research_candidates']))
     if scanned:
      bad=row['research_candidates'][0]; self.assertEqual(bad['baseline_reasons'],['Unknown']); self.assertNotIn('max_otm_fraction',bad)
      self.assertIsNone(row['research_candidates'][1]['max_otm_fraction'])
    subset=client.get('/api/analyst-trader/notable-flow?ticker=TEST11',headers=headers).json()
    self.assertEqual(len(subset['flows']),1); self.assertEqual(subset['flows'][0]['research_history']['shown'],6)
   self.assertEqual([x['rows'] for x in calls],[100,100,10]); self.assertTrue(all(x['params'][-2:]==[10,100] for x in calls))
   self.assertEqual(snapshot(),before)
   for reasons in ({'bad':1},[{}],7,'bad',None):
    text=alerts.actionable_cards(dict(rec,research_candidate=dict(original,baseline_reasons=reasons,enhancement_unknowns=reasons,profile_name={})))['open']['content']
    self.assertIn('Reasons: Unknown',text); self.assertIn('Unknowns: Unknown',text)
   Path(os.environ['ASTRA_SANDBOX'],'saturation.json').write_text(json.dumps(dict(body=body,sql=calls,totals={k:sum(r['research_history'][k] for r in body['flows']) for k in ('total','shown','omitted','invalid')})))
  producer.ProducerContext().run_producers(True,publish=False,expiry='2026-10-02',selected_profile_factory=OperationalCards().factory,candidate_probe=probe)

 def test_legacy_authorization_identity(self):
  old=oldmodule('extra_old','old_research.py'); oldalert=oldmodule('extra_alert','old_alert.py'); real=current.evaluate_research; cards=alerts.actionable_cards
  for named in (False,True):
   def queued(db,result,pub,opts,now):
    with db._get_connection() as c:
     identity=c.execute('SELECT identity_json FROM alert_messages WHERE alert_id=?',(pub['alert_id'],)).fetchone()[0]
    data=json.loads(identity); rec=result['recommendation']; pub=data['publication']; box=alerts.AlertOutbox(db.db_path,clock=lambda:now.timestamp())
    def snapshot():
     with db._get_connection() as c:return {t:[tuple(r) for r in c.execute('SELECT * FROM '+t)] for t in ('alert_messages','alert_units','kian_research_candidates','learning_decisions')}
    before=snapshot()
    with patch.object(alerts,'actionable_cards',cards):
     box.enqueue(rec,pub,opts['delivery_destinations'],cards(rec))
     self.assertEqual(box.enqueue(rec,dict(pub,publishing_authorized=False),opts['delivery_destinations'],cards(rec))['status'],'denied')
     mutations=[]
     for key,value in [('entry_price',3),('flow_id','other')]: mutations.append((dict(rec,**{key:value}),pub,opts['delivery_destinations']))
     for key,value in [('policy_version','other'),('flow_id','other'),('revision_reason','changed')]: mutations.append((rec,dict(pub,**{key:value}),opts['delivery_destinations']))
     mutations.append((rec,pub,[('discord','changed')]))
     for key,value in [('profile_name','tampered'),('max_otm_fraction',None),('filter_provenance',{}),('source_hash','changed'),('policy_hash','changed')]: mutations.append((dict(rec,research_candidate=dict(rec['research_candidate'],**{key:value})),pub,opts['delivery_destinations']))
     for r,p,d in mutations:
      with self.assertRaises(ValueError): box.enqueue(r,p,d,cards(r))
     wrong=copy.deepcopy(cards(rec));wrong['open']['content']+='changed'
     with self.assertRaises(ValueError):box.enqueue(rec,pub,opts['delivery_destinations'],wrong)
    self.assertEqual(snapshot(),before)
    return False
   with patch.object(current,'evaluate_research',old.evaluate_research),patch.object(alerts,'actionable_cards',oldalert.actionable_cards):
    producer.ProducerContext().run_producers(True,expiry='2026-10-02',delivery_mode='retryable',queued_probe=queued,selected_profile_factory=OperationalCards().factory if named else None)

 def test_missing_metadata_renderer_no_crash(self):
  def probe(db,results):
   rec=results[0]['recommendation']; candidate=dict(rec['research_candidate']); candidate.pop('dte')
   text=alerts.actionable_cards(dict(rec,research_candidate=candidate))['open']['content']
   self.assertIn('DTE: Unknown',text)
   for value in (None, True, {}, [], '9', 1.5, float('nan'), float('inf'), 10**400):
    malformed=dict(candidate,dte=value); before=copy.deepcopy(malformed)
    text=alerts.actionable_cards(dict(rec,research_candidate=malformed))['open']['content']
    self.assertIn('DTE: Unknown',text)
    self.assertEqual(repr(malformed),repr(before))
   # Every other directly indexed candidate display field already has a safe default.
   for field in ('baseline_status','enhanced_status','source_id','decision_id','policy_version',
                 'policy_hash','novelty','calendar_zone','enhancement_unknowns','evidence'):
    malformed=dict(rec['research_candidate']); malformed.pop(field)
    self.assertIn('Unknown',alerts.actionable_cards(dict(rec,research_candidate=malformed))['open']['content'])
   self.assertIn(f"DTE: {rec['research_candidate']['dte']}",alerts.actionable_cards(rec)['open']['content'])
  producer.ProducerContext().run_producers(True,publish=False,expiry='2026-10-02',selected_profile_factory=OperationalCards().factory,candidate_probe=probe)


 def test_extreme_numeric_saved_api_is_unknown(self):
  def probe(db,results):
   from hermes_cli import web_server as server
   from starlette.testclient import TestClient
   original=results[0]['recommendation']['research_candidate']; malformed=dict(original,decision_id='bad-number',max_otm_fraction=10**400)
   with db._get_connection() as c: c.execute('INSERT INTO kian_research_candidates VALUES (?,?,?)',('bad-number',original['source_id'],json.dumps(malformed)))
   with patch.object(server,'_analyst_db_path',return_value=db.db_path):
    client=TestClient(server.app)
    response=client.get('/api/analyst-trader/notable-flow',headers={'X-Hermes-Session-Token':server._SESSION_TOKEN})
    self.assertEqual(response.status_code,200)
    cards=response.json()['flows'][0]['research_candidates']; bad=next(x for x in cards if x['decision_id']=='bad-number')
    self.assertNotIn('max_otm_fraction',bad); self.assertIn(original,cards)
   for value in (10**400, -(10**400), 10**308, 1e308, float('inf'), float('nan'), True, {}, '0.1'):
    for field in ('max_otm_fraction','otm_fraction'):
     candidate=dict(original,**{field:value}); before=copy.deepcopy(candidate)
     text=alerts.actionable_cards(dict(results[0]['recommendation'],research_candidate=candidate))['open']['content']
     self.assertIn(('OTM cap' if field=='max_otm_fraction' else 'OTM distance')+': Unknown',text)
     self.assertEqual(repr(candidate),repr(before))
   for value,expected in ((None,'Unlimited'),(.1,'10%')):
    text=alerts.actionable_cards(dict(results[0]['recommendation'],research_candidate=dict(original,max_otm_fraction=value)))['open']['content']
    self.assertIn('OTM cap: '+expected,text)
   missing=dict(original);missing.pop('max_otm_fraction')
   self.assertIn('OTM cap: Unknown',alerts.actionable_cards(dict(results[0]['recommendation'],research_candidate=missing))['open']['content'])
   with db._get_connection() as c:
    self.assertEqual(json.loads(c.execute('SELECT payload_json FROM kian_research_candidates WHERE decision_id=?',('bad-number',)).fetchone()[0]),malformed)
  producer.ProducerContext().run_producers(True,publish=False,expiry='2026-10-02',selected_profile_factory=OperationalCards().factory,candidate_probe=probe)
