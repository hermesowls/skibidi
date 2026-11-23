"""TEST-only full research coordinator -> HTTP boundary -> durable tracking."""
import importlib.util
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from plugins.analyst_trader.db import AnalystDatabase
from plugins.analyst_trader import research_profiles, research_watchlist
from plugins.analyst_trader.realdata_http_worker import fetch
from test_stage2_uw_schema import trade

class UnderlyingDaily(unittest.TestCase):
    def test_rejects_intraday_shape_and_preserves_database(self):
        spec=importlib.util.spec_from_file_location('daily_bad_coordinator',Path(os.environ['HERMES_HOME'])/'scripts/flowseeker_unified_ingestion.py')
        mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve(); source=root/'seed.json'
            source.write_text(json.dumps({'records':[dict(mode='TEST',provider_event_id='TEST-UW',received_at='2026-09-24T16:00:00Z',evidence={'contract_symbol':'SPY260925C00700000'},raw={})]}))
            db=root/'TEST/watchlist.sqlite'; research_watchlist.seed(db,source); before=db.read_bytes()
            row=dict(date='2026-09-24',open='100',high='102',low='99',close='101',volume=100,start_time='2026-09-24T14:00:00Z')
            artifact=root/'raw.json'; artifact.write_text(json.dumps({'data':[row]}))
            with self.assertRaises(ValueError):
                mod.run_research_underlying(root=root,grant=dict(authorized=True,evidence_cohort='TEST'),ticker='SPY',artifact=artifact,received_at='2026-09-24T21:00:00Z',end_date='2026-09-24')
            self.assertEqual(db.read_bytes(),before)

    def test_public_daily_replay_to_canonical_reader(self):
        spec=importlib.util.spec_from_file_location('daily_coordinator',Path(os.environ['HERMES_HOME'])/'scripts/flowseeker_unified_ingestion.py')
        mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        self.assertTrue(callable(getattr(mod,'run_research_underlying',None)))
        from plugins.analyst_trader.session_calendar import calendar
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve(); source=root/'seed.json'
            source.write_text(json.dumps({'records':[dict(mode='TEST',provider_event_id='TEST-UW',received_at='2026-09-24T16:00:00Z',evidence={'contract_symbol':'SPY260925C00700000'},raw={})]}))
            db=root/'TEST/watchlist.sqlite'; research_watchlist.seed(db,source)
            dates=calendar().schedule.loc['2025-09-01':'2026-09-24'].index[-220:]
            rows=[dict(date=d.date().isoformat(),open=str(100+i),high=str(102+i),low=str(99+i),close=str(101+i),volume=100) for i,d in enumerate(dates)]
            artifact=root/'ohlc.json'; artifact.write_text(json.dumps({'data':rows})); raw=artifact.read_bytes()
            def run(): return mod.run_research_underlying(root=root,grant=dict(authorized=True,evidence_cohort='TEST'),ticker='SPY',artifact=artifact,received_at='2026-09-24T21:00:00Z',end_date='2026-09-24')
            out=run(); run()
            ta=out['underlying_technicals'][0]
            self.assertEqual(ta['status'],'AVAILABLE'); self.assertEqual(set(ta['ema']),{'8','21','50','100','200'})
            self.assertEqual(ta['research_timeframe'],'DAILY'); self.assertEqual(ta['timeframe_approval'],'PROVISIONAL_DESCRIPTIVE_ONLY')
            self.assertFalse(ta['execution_authorized']); self.assertEqual(out['underlying_snapshot_count'],1)
            self.assertEqual((out['observation_count'],out['contract_count'],out['snapshot_count'],out['context_count']),(1,1,0,0))
            with research_watchlist.connection(db) as c:
                self.assertEqual(bytes(c.execute('SELECT raw_body FROM snapshots').fetchone()[0]),raw)
            artifact.write_text(json.dumps({'data':rows[-5:]})); out=run()
            short=next(t for t in out['underlying_technicals'] if t['raw_hash']==research_watchlist.digest(artifact.read_bytes()))
            self.assertEqual(short['status'],'INSUFFICIENT_DATA')

class ContextReplay(unittest.TestCase):
    def test_skylit_browser_capture_public_replay(self):
        spec=importlib.util.spec_from_file_location('browser_coordinator',Path(os.environ['HERMES_HOME'])/'scripts/flowseeker_unified_ingestion.py')
        mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve(); source=root/'seed.json'
            source.write_text(json.dumps({'records':[dict(mode='TEST',provider_event_id='TEST-UW',received_at='2026-09-24T16:00:00Z',evidence={'contract_symbol':'SPY260925C00700000'},raw={})]}))
            db=root/'TEST/watchlist.sqlite'; research_watchlist.seed(db,source)
            artifact=root/'browser.json'
            capture=dict(schema='skylit-browser-capture-v1',evidence_cohort='TEST',ticker='SPY',mode='GEX',status='POPULATED',captured_at='2026-09-24T17:00:00Z',displayed_asof='2026-09-24 12:59 ET',expiry_labels=['Sep 25'],screenshot={'path':'/not/fetched.png','sha256':'a'*64},dom_text='SPY GEX Sep 25 700 1.2M',cells=[{'strike':'700','expiry':'Sep 25','display_value':'1.2M'}],uncertainty=['Provider units unverified'])
            artifact.write_text(json.dumps(capture)); raw=artifact.read_bytes()
            def run(): return mod.run_research_context(root=root,grant=dict(authorized=True,evidence_cohort='TEST'),source='skylit',artifact=artifact,received_at='2026-09-24T17:01:00Z')
            run(); run()
            tracked=research_watchlist.read_watchlist(db); context=tracked['contexts'][0]
            self.assertEqual(tracked['context_count'],1)
            self.assertEqual(tracked['snapshot_count'],0)
            self.assertEqual(context['capture']['cells'],capture['cells'])
            self.assertEqual(context['capture']['screenshot'],capture['screenshot'])
            self.assertEqual(context['gex'],'UNKNOWN')
            self.assertEqual(context['interpretation'],'BROWSER_DISPLAY_VALUES_UNVERIFIED_UNITS')
            with research_watchlist.connection(db) as c:
                self.assertEqual(bytes(c.execute('SELECT raw_body FROM snapshots').fetchone()[0]),raw)
            for key,value in [('evidence_cohort','REAL_DATA_RESEARCH'),('ticker','QQQ'),('status','ACCESS_REQUIRED'),('mode','VEX')]:
                bad=dict(capture); bad[key]=value; artifact.write_text(json.dumps(bad))
                with self.assertRaises(ValueError): run()
            self.assertEqual(research_watchlist.read_watchlist(db)['context_count'],1)
            bad=dict(capture,cells=[{'strike':'700','expiry':'Sep 25','display_value':'9.9B'}])
            artifact.write_text(json.dumps(bad))
            with self.assertRaises(ValueError): run()

    def test_native_one_page_request_ticket_and_no_cursor_skip(self):
        from unittest.mock import patch
        spec=importlib.util.spec_from_file_location('native_coordinator',Path(os.environ['HERMES_HOME'])/'scripts/flowseeker_unified_ingestion.py')
        mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        self.assertTrue(callable(getattr(mod,'run_research_discord_page',None)))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve(); source=root/'seed.json'
            source.write_text(json.dumps({'records':[dict(mode='TEST',provider_event_id='TEST-UW',received_at='2026-09-24T16:00:00Z',evidence={'contract_symbol':'AAOI260925C00100000'},raw={})]}))
            db=root/'TEST/watchlist.sqlite'; research_watchlist.seed(db,source)
            msg=dict(id='123456789',channel_id='123',timestamp='2026-08-01T16:00:00Z',author={'id':'42'},content='GEX AAOI please',embeds=[{'description':'original'}],attachments=[{'id':'7'}])
            raw=json.dumps([msg]).encode(); seen=[]
            class Response:
                def __enter__(self): return self
                def __exit__(self,*a): pass
                def read(self,n): return raw[:n]
            def boundary(req,timeout):
                seen.append(req.full_url); return Response()
            cfg={'sources':{'discord_notable_flow':{'enabled':True,'channels':{'123':'notable-flow'}}}}
            with patch.object(mod,'urlopen',boundary), patch.dict(os.environ,{'DISCORD_BOT_TOKEN':'TEST'}):
                out=mod.run_research_discord_page(root=root,grant={'authorized':True,'evidence_cohort':'TEST'},cfg=cfg,limit=1)
                again=mod.run_research_discord_page(root=root,grant={'authorized':True,'evidence_cohort':'TEST'},cfg=cfg,limit=1)
            self.assertEqual(len(seen),1); self.assertEqual(out['requests'],1)
            self.assertEqual(again['requests'],0)
            self.assertIsNone(out['cursor_after']); self.assertEqual(out['coverage'],'INCOMPLETE_NOT_ADVANCED')
            tracked=research_watchlist.read_watchlist(db)
            self.assertEqual(tracked['observation_count'],1); self.assertEqual(tracked['snapshot_count'],0)
            context=tracked['contexts'][0]
            self.assertEqual(context['request_ticket']['ticker'],'AAOI')
            self.assertEqual(context['request_ticket']['timeframe'],'UNKNOWN')
            self.assertEqual(context['request_ticket']['requester'],{'id':'42'})
            self.assertFalse(context['execution_authorized'])
            with research_watchlist.connection(db) as c:
                self.assertEqual(bytes(c.execute('SELECT raw_body FROM snapshots').fetchone()[0]),raw)

    def test_rejected_page_cannot_enter_on_recovery(self):
        from unittest.mock import patch
        spec=importlib.util.spec_from_file_location('reject_coordinator',Path(os.environ['HERMES_HOME'])/'scripts/flowseeker_unified_ingestion.py')
        mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve(); source=root/'seed.json'
            source.write_text(json.dumps({'records':[dict(mode='TEST',provider_event_id='TEST-UW',received_at='2026-09-24T16:00:00Z',evidence={'contract_symbol':'AAOI260925C00100000'},raw={})]}))
            db=root/'TEST/watchlist.sqlite'; research_watchlist.seed(db,source)
            class Response:
                def __enter__(self): return self
                def __exit__(self,*a): pass
                def read(self,n): return b'[{"id":"123", "channel_id":"999", "content":"GEX AAOI please"}]'
            cfg={'sources':{'discord_notable_flow':{'enabled':True,'channels':{'123':'notable-flow'}}}}
            with patch.object(mod,'urlopen',return_value=Response()) as send, patch.dict(os.environ,{'DISCORD_BOT_TOKEN':'TEST'}):
                for _ in range(2):
                    with self.assertRaises(ValueError):
                        mod.run_research_discord_page(root=root,grant={'authorized':True,'evidence_cohort':'TEST'},cfg=cfg)
                self.assertEqual(send.call_count,1)
            self.assertEqual(research_watchlist.read_watchlist(db)['context_count'],0)

    def test_saved_context_is_immutable_non_actionable_and_optional(self):
        spec=importlib.util.spec_from_file_location('context_coordinator',Path(os.environ['HERMES_HOME'])/'scripts/flowseeker_unified_ingestion.py')
        mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        self.assertTrue(callable(getattr(mod,'run_research_context',None)))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve(); source=root/'seed.json'
            source.write_text(json.dumps({'records':[dict(mode='TEST',provider_event_id='TEST-UW',received_at='2026-09-24T16:00:00Z',evidence={'contract_symbol':'AAOI260925C00100000'},raw={})]}))
            db=root/'TEST/watchlist.sqlite'; research_watchlist.seed(db,source)
            artifact=root/'discord.json'
            msg=dict(id='123456789',channel_id='123',timestamp='2026-08-01T16:00:00Z',author={'id':'42','username':'TEST'},content='GEX AAOI please',attachments=[{'id':'7','url':'https://example.invalid/test.png'}],embeds=[])
            artifact.write_text(json.dumps([msg])); before=artifact.read_bytes()
            grant=dict(authorized=True,evidence_cohort='TEST')
            def run(): return mod.run_research_context(root=root,grant=grant,source='discord',artifact=artifact,received_at='2026-09-24T17:00:00Z')
            result=run(); run()
            tracked=research_watchlist.read_watchlist(db)
            self.assertEqual(tracked['observation_count'],1)
            self.assertEqual(tracked['snapshot_count'],0)
            self.assertEqual(tracked['context_count'],1)
            # Overlapping native pages dedupe the unchanged message, not page hash.
            extra=dict(msg,id='987654321',content='ordinary comment')
            artifact.write_text(json.dumps([msg,extra])); run()
            self.assertEqual(research_watchlist.read_watchlist(db)['context_count'],2)
            artifact.write_bytes(before)
            context=tracked['contexts'][0]
            self.assertEqual(context['external_id'],msg['id'])
            self.assertEqual(context['author'],msg['author'])
            self.assertEqual(context['attachments'],msg['attachments'])
            self.assertEqual(context['timeframe'],'UNKNOWN')
            self.assertFalse(context['execution_authorized'])
            self.assertEqual(context['freshness'],'HISTORICAL_CONTEXT_NOT_ACTIONABLE')
            self.assertEqual(artifact.read_bytes(),before)
            with research_watchlist.connection(db) as c:
                self.assertEqual(bytes(c.execute('SELECT raw_body FROM snapshots').fetchone()[0]),before)
            self.assertEqual(result['requests'],0)
            missing=mod.run_research_context(root=root,grant=grant,source='skylit',artifact=None,received_at='2026-09-24T17:00:00Z')
            self.assertEqual(missing['status'],'UNAVAILABLE')
            state_dir=db.parent/'discord-native-page'; state_dir.mkdir()
            (state_dir/'result.json').write_text(json.dumps({'status':'HTTP_BLOCKED','http_status':403}))
            projected=research_watchlist.read_watchlist(db)
            self.assertEqual(projected['observation_count'],1)
            self.assertEqual(projected['source_availability']['discord']['access_status'],'HTTP_BLOCKED')
            self.assertEqual(projected['source_availability']['discord']['http_status'],403)
            self.assertEqual(projected['source_availability']['skylit']['context_status'],'UNAVAILABLE')
            self.assertEqual(projected['source_availability']['skylit']['numeric_gex'],'UNKNOWN')
            self.assertFalse(projected['source_availability']['skylit']['baseline_rejection'])
            (state_dir/'result.json').write_text('not json')
            self.assertEqual(research_watchlist.read_watchlist(db)['source_availability']['discord']['access_status'],'UNKNOWN')
            with self.assertRaises(ValueError):
                mod.run_research_context(root=root,grant=grant,source='discord',artifact=artifact,received_at='2026-09-24T17:00:00Z',max_rows=0)
            # A revised message is a distinct immutable raw version; replay stays idempotent.
            msg['content']='GEX AAOI update'; artifact.write_text(json.dumps([msg])); run(); run()
            self.assertEqual(research_watchlist.read_watchlist(db)['context_count'],3)
            self.assertEqual(research_watchlist.read_watchlist(db)['pending_contracts'],['AAOI260925C00100000'])
            with self.assertRaises((ValueError, FileNotFoundError)):
                mod.run_research_context(root=root,grant=dict(grant,evidence_cohort='REAL_DATA_RESEARCH'),source='discord',artifact=artifact,received_at='2026-09-24T17:00:00Z')
            skylit=root/'skylit.json'
            skylit.write_text(json.dumps({'ts':'2026-08-01T16:00:00Z','sources':{'skylit_flowseeker':{'captures':[{'status':'ok','screenshot':'/not/read.png'}]}}}))
            mod.run_research_context(root=root,grant=grant,source='skylit',artifact=skylit,received_at='2026-09-24T17:00:00Z')
            context=research_watchlist.read_watchlist(db)['contexts'][-1]
            skylit_context=next(x for x in research_watchlist.read_watchlist(db)['contexts'] if x['source']=='skylit')
            self.assertEqual(skylit_context['gex'],'UNKNOWN')
            self.assertEqual(skylit_context['interpretation'],'CAPTURE_METADATA_ONLY_NOT_OBSERVED_GEX')
            self.assertEqual(research_watchlist.read_watchlist(db)['snapshot_count'],0)
            old=db.read_bytes()
            artifact.write_text(json.dumps([dict(msg,id='not-native')]))
            with self.assertRaises(ValueError): run()
            self.assertEqual(db.read_bytes(),old)
            linked=root/'linked.json'; linked.symlink_to(skylit)
            with self.assertRaises(ValueError):
                mod.run_research_context(root=root,grant=grant,source='skylit',artifact=linked,received_at='2026-09-24T17:00:00Z')

class RealIntraday(unittest.TestCase):
    def test_bounded_boundary(self):
        from plugins.analyst_trader import realdata_transport as rt
        self.assertTrue(hasattr(rt, 'BoundedUWIntradayTransport'))
        from plugins.analyst_trader.realdata_intraday_worker import fetch, validate_request
        seen=[]
        class Response:
            status_code=200
            headers={}
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def iter_raw(self,chunk_size): yield b'{"data":[]}'
        class Client:
            def stream(self,method,url,**kw):
                seen.append((method,url,kw)); return Response()
        path='/api/option-contract/AAOI260925C00100000/intraday'
        r=fetch('TEST',path,{'date':'2026-09-24'},30,client=Client())
        self.assertEqual(r['source'],'TEST_FIXTURE')
        self.assertEqual(r['raw_body'],b'{"data":[]}')
        self.assertEqual(len(seen),1)
        Response.status_code=429; Response.headers={'retry-after':'90'}
        limited=fetch('TEST',path,{'date':'2026-09-24'},30,client=Client())
        self.assertEqual((limited['status'],limited['retry_after']),(429,'90'))
        self.assertEqual(len(seen),2)
        self.assertFalse(seen[0][2]['follow_redirects'])
        for p,d,t in [(path,{'date':'2026-02-30'},30),(path+'?x=1',{'date':'2026-09-24'},30),(path,{'date':'2026-09-24','limit':1},30),(path,{'date':'2026-09-24'},True)]:
            with self.assertRaises(ValueError): validate_request(p,d,t)

    def test_real_public_caller_claims_and_failures(self):
        from plugins.analyst_trader.realdata_transport import BoundedUWIntradayTransport
        from unittest.mock import patch
        import base64
        spec=importlib.util.spec_from_file_location('real_followup',Path(os.environ['HERMES_HOME'])/'scripts/flowseeker_unified_ingestion.py')
        mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory(dir=os.environ['HERMES_HOME']) as tmp:
            root=Path(tmp).resolve(); db=root/'REAL_DATA_RESEARCH/watchlist.sqlite'
            source=root/'input.json'
            contracts=['AAOI260925C00100000','BBB260925C00100000']
            source.write_text(json.dumps({'records':[dict(mode='REAL_DATA_RESEARCH',provider_event_id=c,received_at='2026-09-24T16:00:00Z',evidence={'contract_symbol':c},raw={}) for c in contracts]}))
            research_watchlist.seed(db,source)
            transport=BoundedUWIntradayTransport('TEST-NOT-A-REAL-CREDENTIAL')
            grant=dict(authorized=True,evidence_cohort='REAL_DATA_RESEARCH',source='UW_INTRADAY_BOUNDED_V1')
            def run(**kw): return mod.run_research_followup(root=root,grant=grant,transport=transport,date='2026-09-24',now='2026-09-24T17:00:00Z',max_requests=1,min_interval_seconds=0,**kw)
            def response(body,status=200): return dict(status=status,raw_body=base64.b64encode(body).decode(),received_at='2026-09-24T17:00:01Z',source='UW_LIVE',retry_after='120')
            with patch.object(transport,'_execute',return_value=response(b'{"data":[]}')):
                self.assertEqual(run()['requests'],1)
            with patch.object(transport,'_execute',side_effect=TimeoutError('TEST ambiguous')):
                self.assertEqual(run()['requests'],1)
            state=json.loads((db.parent/'followup-state.json').read_text())
            self.assertEqual([c['contract'] for c in state['claims']],contracts)
            self.assertEqual(state['claims'][1]['status'],'TRANSPORT_FAILED_NO_RETRY')
            self.assertNotIn('http_status',state['claims'][1])
            for body in (b'{"data":{}}', b'{"data":[null]}', b'{"data":[{"start_time":"2026-09-23T16:01:00Z","close":"2"}]}', b'{"data":[{"start_time":"2026-09-24T16:01:00Z","option_symbol":"CCC260925C00100000","close":"2"}]}'):
                with patch.object(transport,'_execute',return_value=response(body)):
                    run()
                state=json.loads((db.parent/'followup-state.json').read_text())
                self.assertEqual(state['claims'][-1]['status'],'INVALID_RESPONSE')
            with patch.object(transport,'_execute',return_value=response(b'{}',429)) as call:
                self.assertEqual(run()['status'],'RATE_LIMITED')
                self.assertEqual(run()['requests'],0)
                self.assertEqual(call.call_count,1)
            state=json.loads((db.parent/'followup-state.json').read_text())
            self.assertEqual(state['claims'][-1]['retry_after'],'120')
            self.assertEqual(state['claims'][0]['source'],'UW_LIVE')
            for n in (True,-1,21):
                with self.assertRaises(ValueError): mod.run_research_followup(root=root,grant=grant,transport=transport,date='2026-09-24',max_requests=n)

class Outcomes(unittest.TestCase):
    def test_public_followup_projects_baseline_learning_without_option_ta(self):
        spec=importlib.util.spec_from_file_location('learning_coordinator',Path(os.environ['HERMES_HOME'])/'scripts/flowseeker_unified_ingestion.py')
        mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory(dir=os.environ['HERMES_HOME']) as tmp:
            root=Path(tmp).resolve(); source=root/'seed.json'
            contracts=['AAA260925C00100000','BBB260925C00100000']
            rows=[dict(mode='TEST',provider_event_id=str(i),received_at='2026-09-24T16:00:09Z',evidence={'contract_symbol':c},raw={'executed_at':'2026-09-24T15:59:00Z'},raw_threshold_diagnostics={'failures':[],'unknown':[]},policy_hash='TEST-policy') for i,c in enumerate([contracts[0],contracts[0],contracts[1]])]
            source.write_text(json.dumps({'records':rows})); db=root/'TEST/watchlist.sqlite'
            research_watchlist.seed(db,source); calls=[]
            def transport(endpoint,**kw):
                calls.append(endpoint)
                bars=[dict(start_time='2026-09-24T16:00:00Z',close='999'),dict(start_time='2026-09-24T16:01:00Z',close='2'),dict(start_time='2026-09-24T16:02:00Z',close='3'),dict(start_time='2026-09-24T16:03:00Z',close='999')]
                return dict(status=200,received_at='2026-09-24T16:03:20Z',raw_body=json.dumps({'data':bars}).encode(),evidence_cohort='TEST')
            mod.run_research_followup(root=root,grant=dict(authorized=True,evidence_cohort='TEST',source='TEST_TRANSPORT'),transport=transport,date='2026-09-24',now='2026-09-24T16:03:20Z',max_requests=1,min_interval_seconds=0)
            before=db.read_bytes()
            result=research_watchlist.read_watchlist(db)
            aggregate=result['learning_summary']
            self.assertEqual(len(calls),1)
            self.assertEqual(aggregate['baseline_observation_count'],3)
            self.assertEqual(aggregate['baseline_contract_count'],2)
            self.assertEqual(aggregate['covered_contract_count'],1)
            self.assertEqual(aggregate['covered_observation_count'],2)
            self.assertEqual(aggregate['completed_bars_latest_per_contract'],2)
            self.assertEqual(aggregate['observed_change_pct_mean'],50)
            self.assertEqual(aggregate['horizon_approval'],'PENDING')
            self.assertIsNone(aggregate['trade_pnl'])
            self.assertFalse(aggregate['validated_edge'])
            self.assertEqual(result['technicals']['status'],'INSUFFICIENT_DATA')
            self.assertEqual(result['technicals']['ema_periods'],[8,21,50,100,200])
            self.assertEqual(result['observations'][0]['executed_at'],'2026-09-24T15:59:00Z')
            self.assertEqual(result['observations'][0]['first_seen_at'],'2026-09-24T16:00:09Z')
            self.assertEqual(db.read_bytes(),before)

    def test_latest_receipt_deduplicates_overlap_and_retains_unknown_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve(); source=root/'seed.json'; db=root/'TEST/watchlist.sqlite'
            a,b='AAA260925C00100000','BBB260925C00100000'
            source.write_text(json.dumps({'records':[
                dict(mode='TEST',provider_event_id='eligible',received_at='2026-09-24T16:00:00Z',evidence={'contract_symbol':a},raw={},raw_threshold_diagnostics={'failures':[],'unknown':[]}),
                dict(mode='TEST',provider_event_id='unknown',received_at='2026-09-24T16:00:00Z',evidence={'contract_symbol':b},raw={})]}))
            research_watchlist.seed(db,source)
            def store(prices,receipt):
                raw=json.dumps({'data':[dict(start_time=f'2026-09-24T16:0{i}:00Z',close=p) for i,p in enumerate(prices,1)]}).encode()
                research_watchlist.store_snapshot(db,a,raw,received_at=receipt,evidence_cohort='TEST')
            store([2,3],'2026-09-24T17:00:00Z')
            store([2,3,4],'2026-09-24T13:01:00-04:00')
            result=research_watchlist.read_watchlist(db); summary=result['learning_summary']
            self.assertEqual(result['observation_count'],2)
            self.assertEqual(summary['baseline_observation_count'],1)
            self.assertEqual(summary['eligibility_unknown_or_failed_count'],1)
            self.assertEqual(summary['covered_contract_count'],1)
            self.assertEqual(summary['completed_bars_latest_per_contract'],3)
            self.assertEqual(summary['observed_change_pct_mean'],100)
            self.assertEqual(len(summary['selected_snapshot_ids']),1)
            self.assertEqual(result['snapshot_count'],2)

    def test_later_discovery_cannot_inherit_earlier_snapshot_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve(); source=root/'seed.json'; db=root/'TEST/watchlist.sqlite'
            contract='AAA260925C00100000'
            def seed(event,seen):
                source.write_text(json.dumps({'records':[dict(mode='TEST',provider_event_id=event,received_at=seen,evidence={'contract_symbol':contract},raw={},raw_threshold_diagnostics={'failures':[],'unknown':[]})]}))
                research_watchlist.seed(db,source)
            seed('early','2026-09-24T16:00:00Z')
            raw=json.dumps({'data':[dict(start_time='2026-09-24T16:01:00Z',close=2),dict(start_time='2026-09-24T16:02:00Z',close=3)]}).encode()
            research_watchlist.store_snapshot(db,contract,raw,received_at='2026-09-24T16:03:00Z',evidence_cohort='TEST')
            seed('late','2026-09-24T16:04:00Z')
            result=research_watchlist.read_watchlist(db)
            self.assertEqual(result['learning_summary']['covered_contract_count'],0)
            self.assertEqual(result['learning_summary']['covered_observation_count'],0)
            self.assertEqual(result['learning_summary']['completed_bars_latest_per_contract'],0)
            self.assertEqual(result['snapshots'][0]['first_seen_cutoff'],'2026-09-24T16:00:00+00:00')
            self.assertEqual(result['snapshots'][0]['observed_mark_path']['first_seen_at'],'2026-09-24T16:04:00Z')

    def test_completed_observed_path_not_pnl(self):
        from plugins.analyst_trader import learning_evidence as le
        self.assertTrue(callable(getattr(le, 'observed_mark_path', None)))
        bars = [dict(start_time=f'2026-09-24T16:{m}:00Z', close=p) for m,p in [('35','99'),('36','2'),('38','3'),('39','4')]]
        result = le.observed_mark_path(bars, first_seen='2026-09-24T16:35:09Z', received_at='2026-09-24T16:39:20Z')
        self.assertEqual(result['completed_bars'], 2)
        self.assertEqual(result['basis_price'], 2)
        self.assertEqual(result['observed_change_pct'], 50)
        self.assertEqual(result['coverage'], 'GAPPED_OBSERVED_MARKS')
        self.assertIsNone(result['trade_pnl'])
        self.assertEqual(le.observed_mark_path([], first_seen='2026-09-24T16:35:09Z', received_at='2026-09-24T16:39:20Z')['status'], 'UNKNOWN')

class Followup(unittest.TestCase):
    def test_budget_cursor_recovery_and_stop(self):
        path = Path(os.environ['HERMES_HOME'])/'scripts/flowseeker_unified_ingestion.py'
        spec = importlib.util.spec_from_file_location('followup_coordinator', path)
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        self.assertTrue(callable(getattr(mod, 'run_research_followup', None)))
        root = Path(os.environ['HERMES_HOME']).resolve()/'followup-TEST'
        root.mkdir()
        source = root/'input.json'
        contracts = ['AAA260925C00100000','BBB260925C00100000','CCC260925C00100000']
        source.write_text(json.dumps({'records':[dict(mode='TEST',provider_event_id=c,received_at='2026-09-24T16:00:00Z',evidence={'contract_symbol':c},raw={}) for c in contracts]}))
        db = root/'TEST/watchlist.sqlite'; research_watchlist.seed(db,source)
        with self.assertRaisesRegex(ValueError, 'cohort'):
            research_watchlist.store_snapshot(db, contracts[0], b'{"data":[]}', received_at='2026-09-24T17:00:00Z')
        calls=[]
        def transport(endpoint, *, params, timeout):
            calls.append(endpoint)
            return dict(status=200, received_at='2026-09-24T17:00:00Z', raw_body=json.dumps({'data':[dict(start_time='2026-09-24T16:01:00Z',close='2'),dict(start_time='2026-09-24T16:02:00Z',close='3')]}).encode(), evidence_cohort='TEST')
        grant=dict(authorized=True,evidence_cohort='TEST',source='TEST_TRANSPORT')
        def run(**kw): return mod.run_research_followup(root=root,grant=grant,transport=kw.pop('transport',transport),date='2026-09-24',now='2026-09-24T17:00:00Z',max_requests=1,min_interval_seconds=0,**kw)
        from unittest.mock import patch
        with patch.object(research_watchlist,'store_snapshot',side_effect=RuntimeError('TEST crash')):
            with self.assertRaises(RuntimeError): run()
        result=run()
        self.assertEqual(len(calls),2)
        self.assertIn(contracts[1],calls[1])
        self.assertEqual(research_watchlist.read_watchlist(db)['snapshot_count'],2)
        self.assertEqual(research_watchlist.read_watchlist(db)['snapshots'][0]['observed_mark_path']['status'],'OBSERVED_MARK_PATH')
        def limited(endpoint,**kw):
            calls.append(endpoint)
            return dict(status=429,received_at='2026-09-24T17:00:00Z',raw_body=b'{}',evidence_cohort='TEST',retry_after='60')
        self.assertEqual(run(transport=limited)['status'],'RATE_LIMITED')
        self.assertEqual(run()['requests'],0)
        self.assertEqual(len(calls),3)
        with self.assertRaises(ValueError):
            mod.run_research_followup(root=root,grant=dict(grant,evidence_cohort='REAL_DATA_RESEARCH'),transport=transport,date='2026-09-24')

class Canonical(unittest.TestCase):
    def test_existing_watchlist_regressions(self):
        import test_research_watchlist as tests
        for name in sorted(n for n in dir(tests) if n.startswith('test_')):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                getattr(tests, name)(Path(tmp).resolve())

    def test_configured_reader(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve()
            (home/'research').mkdir()
            (home/'research/config.json').write_text(json.dumps({'version': 1, 'root': str(home/'selected')}))
            self.assertTrue(callable(getattr(research_watchlist, 'canonical_path', None)))
            self.assertEqual(research_watchlist.canonical_path(home), home/'selected/REAL_DATA_RESEARCH/watchlist.sqlite')
            from unittest.mock import patch
            from hermes_cli import web_server
            import asyncio
            sample = home/'sample.json'
            sample.write_text(json.dumps({'records': [dict(provider_event_id='TEST-reader', received_at='2026-09-24T16:00:00Z', evidence={'contract_symbol':'TEST260925C00100000'}, raw={}, mode='TEST')]}))
            with self.assertRaisesRegex(ValueError, 'cohort'):
                research_watchlist.seed(research_watchlist.canonical_path(home), sample)
            self.assertFalse(research_watchlist.canonical_path(home).exists())
            with research_watchlist.connection(research_watchlist.canonical_path(home), write=True):
                pass
            with patch.object(web_server, 'get_hermes_home', return_value=home):
                result = asyncio.run(web_server.api_research_watchlist())
            self.assertEqual(result['observation_count'], 0)
            self.assertEqual(result['technicals']['status'], 'INSUFFICIENT_DATA')
            self.assertEqual(result['learning_summary']['baseline_observation_count'], 0)
            self.assertIsNone(result['learning_summary']['observed_change_pct_mean'])
            self.assertEqual(result['learning_summary']['horizon_approval'], 'PENDING')
            self.assertEqual(result['source_availability']['skylit']['numeric_gex'], 'UNKNOWN')
            self.assertEqual(result['source_availability']['discord']['access_status'], 'UNKNOWN')
            self.assertFalse(result['execution_authorized'])
            exporter_path = Path(os.environ['HERMES_HOME'])/'scripts/notable_flow_public_snapshot.py'
            spec = importlib.util.spec_from_file_location('public_export', exporter_path)
            exporter = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(exporter)
            with patch.object(exporter, 'canonical_path', return_value=research_watchlist.canonical_path(home)), patch.object(exporter, 'ROOT', home/'public'):
                with self.assertRaisesRegex(ValueError, 'real research cohort'):
                    exporter.generate()
            self.assertFalse((home/'public/index.html').exists())

class Integration(unittest.TestCase):
    def test_public_caller_retains_old_distinct_events_and_replay(self):
        path = Path(os.environ['HERMES_HOME'])/'scripts/flowseeker_unified_ingestion.py'
        spec = importlib.util.spec_from_file_location('mvp_coordinator', path)
        coordinator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(coordinator)
        self.assertTrue(callable(getattr(coordinator, 'run_research_once', None)), 'Missing safe public caller')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            source = root/'profiles.sqlite'
            db = AnalystDatabase(source)
            profile = research_profiles.create(db, 'TEST canonical research')
            with db._get_connection() as connection:
                connection.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            before = source.read_bytes()
            raw = trade(datetime.now(timezone.utc)-timedelta(seconds=600))
            rows = [raw, dict(raw, id='TEST-distinct-id'), raw]
            calls = []
            class Response:
                status_code = 200
                headers = {}
                def __enter__(self): return self
                def __exit__(self, *args): pass
                def iter_raw(self, chunk_size): yield json.dumps({'data':rows}).encode()
            class Client:
                def stream(self, method, url, **kw):
                    calls.append(kw['params'])
                    return Response()
            def transport(path, *, params, timeout):
                if len(calls) == 1:
                    recovered = research_watchlist.read_watchlist(root/'canonical/TEST/watchlist.sqlite')
                    self.assertEqual(recovered['observation_count'], 2, 'Recovery must precede next HTTP request')
                return fetch('TEST-NOT-A-CREDENTIAL', int(params['limit']), timeout, params=params, client=Client())
            grant = dict(mode='REAL_DATA_RESEARCH', authorized=True, profile_version=profile['version_id'], evidence_cohort='TEST')
            def invoke():
                return coordinator.run_research_once(root=root/'canonical', profile_source=source,
                    grant=grant, transport=transport, now=None)
            # Unsafe existing destinations must fail before creating any artifacts.
            import sqlite3
            from unittest.mock import patch
            destination = root/'canonical/TEST'
            destination.mkdir(parents=True)
            bad = destination/'watchlist.sqlite'
            with sqlite3.connect(bad) as c:
                c.execute('CREATE TABLE unrelated (x)')
            before_bad = bad.read_bytes()
            with self.assertRaises(ValueError):
                invoke()
            self.assertEqual(bad.read_bytes(), before_bad)
            self.assertEqual(list(destination.iterdir()), [bad])
            bad.unlink()
            for kind in ('symlink', 'hardlink', 'sourcecollision'):
                target = bad if kind != 'sourcecollision' else destination/'research.sqlite'
                if kind == 'symlink': target.symlink_to(source)
                else: os.link(source, target)
                with self.assertRaises(ValueError): invoke()
                self.assertEqual(source.read_bytes(), before)
                self.assertEqual(list(destination.iterdir()), [target])
                target.unlink()
            # A fault between durable archive and seed is recovered on retry.
            with patch.object(research_watchlist, 'seed', side_effect=RuntimeError('TEST crash')):
                with self.assertRaisesRegex(RuntimeError, 'TEST crash'): invoke()
            self.assertTrue(list((destination/'evidence').glob('*.json')))
            self.assertFalse(bad.exists())
            first = invoke()
            archives = {p: p.read_bytes() for p in (root/'canonical'/'TEST'/'evidence').glob('*.json')}
            again = invoke()
            tracked = research_watchlist.read_watchlist(again['watchlist_path'])
            self.assertEqual(tracked['observation_count'], 2)
            self.assertEqual(tracked['contract_count'], 1)
            self.assertEqual(tracked['mode'], 'TEST')
            self.assertEqual(len(calls), 3)
            self.assertFalse((root/'canonical/REAL_DATA_RESEARCH').exists())
            self.assertEqual(calls[0]['min_size'], '500')
            self.assertEqual(calls[0]['min_premium'], '50000')
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(first['tracked_count'], 2)
            self.assertFalse(tracked['execution_authorized'])
            for row in tracked['observations']:
                self.assertEqual(row['record']['mode'], 'TEST')
                self.assertEqual(row['record']['raw_threshold_diagnostics']['failures'], [])
                self.assertTrue(Path(row['source_path']).is_file())
            self.assertEqual(len(archives), 4)
            self.assertEqual({p: p.read_bytes() for p in archives}, archives)
