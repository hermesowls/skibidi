"""TEST-only generated prices; maintained schedules are not market observations."""
import copy
import unittest
from datetime import datetime, timedelta, timezone
from plugins.analyst_trader.kian_technicals import analyze


def fixture(end='2026-11-27', timeframe='1h'):
    import exchange_calendars as xc
    schedule = xc.get_calendar('XNYS', start='2024-01-01', end='2027-12-31').schedule
    times = []
    for _, row in schedule.loc['2024-01-01':end].iterrows():
        opening, closing = row['open'].to_pydatetime(), row['close'].to_pydatetime()
        t = opening + timedelta(hours=1) if timeframe == '1h' else closing
        while t < closing:
            times.append(t); t += timedelta(hours=1)
        times.append(closing)
    return dict(source='TEST-observed-bars', ticker='TEST', timeframe=timeframe,
                evidence_id='TEST-calendar', asof=times[-1].isoformat(), max_age_seconds=3600,
                expected_interval_seconds=3600 if timeframe=='1h' else 86400,
                bars=[dict(completed_at=t.isoformat(), completed=True, open=100., high=101.,
                           low=99., close=100., volume=10) for t in times[-210:]])


class CalendarCallers(unittest.TestCase):
    def test_hourly_actual_caller_accepts_session_closes(self):
        for end in ('2026-11-27','2026-03-09','2026-09-08'):
            f=fixture(end)
            result=analyze(f,'TEST',f['asof'])
            self.assertEqual(result['status'],'AVAILABLE', result)
            self.assertEqual(result['calendar']['exchange'],'XNYS')
            self.assertEqual(result['calendar']['adapter_version'],'XNYS-REGULAR-v1')
        self.assertEqual(fixture()['bars'][-1]['completed_at'],'2026-11-27T18:00:00+00:00')

    def test_daily_and_closed_market_no_filler(self):
        f=fixture(timeframe='1d')
        f['asof']='2026-11-29T18:00:00Z'
        self.assertEqual(analyze(f,'TEST',f['asof'])['status'],'AVAILABLE')
        for kind in ('gap','latest_missing','inprogress','duplicate','stale','off_session','future','coverage'):
            x=copy.deepcopy(f)
            if kind=='gap': x['bars'].pop(30)
            if kind=='latest_missing': x['bars'].pop()
            if kind=='inprogress': x['bars'][-1]['completed']=False
            if kind=='duplicate': x['bars'][-1]=x['bars'][-2]
            if kind=='stale': x['asof']='2026-11-30T21:00:00Z'
            if kind=='off_session': x['bars'][-1]['completed_at']='2026-11-28T18:00:00Z'
            if kind=='future': x['bars'][-1]['completed_at']='2026-11-30T21:00:00Z'
            if kind=='coverage': x['asof']='2028-01-01T00:00:00Z'
            self.assertEqual(analyze(x,'TEST',x['asof'])['status'],'UNKNOWN',kind)
        f=fixture(); f['asof']='2026-11-30T15:00:00Z'
        self.assertEqual(analyze(f,'TEST',f['asof'])['status'],'AVAILABLE')
        f['asof']='2026-11-30T15:30:00Z'
        self.assertEqual(analyze(f,'TEST',f['asof'])['status'],'UNKNOWN')

    def test_oi_requires_observed_update_and_immediate_session(self):
        from plugins.analyst_trader.learning_evidence import qualified_oi, aware_time
        r=oi_row(); at=aware_time('2026-11-30T16:00:00Z')
        self.assertEqual(qualified_oi(r,at),(10,20))
        for kind in ('missing_update','preopen','late_update','skipped','wrong_open','wrong_contract','future'):
            x=copy.deepcopy(r); e=x['quant_metrics_json']['oi_evidence']
            if kind=='missing_update': e['next'].pop('observed_at')
            if kind=='preopen': e['next']['observed_at']='2026-11-30T14:29:00Z'
            if kind=='late_update': e['next']['observed_at']='2026-11-30T15:31:00Z'
            if kind=='skipped': e['next_session']=e['next']['session']='2026-12-01'; e['next_open_at']='2026-12-01T14:30:00Z'
            if kind=='wrong_open': e['next_open_at']='2026-11-30T00:00:00Z'
            if kind=='wrong_contract': e['contract']['strike']=101
            if kind=='future': e['next']['available_at']='2026-11-30T17:00:00Z'
            self.assertIsNone(qualified_oi(x,at),kind)
        # Skip one session while all timestamps otherwise satisfy availability.
        x=copy.deepcopy(r); e=x['quant_metrics_json']['oi_evidence']
        e['next_session']=e['next']['session']='2026-12-01'
        e['next_open_at']=e['next']['observed_at']='2026-12-01T14:30:00Z'
        e['next']['available_at']='2026-12-01T15:00:00Z'
        self.assertIsNone(qualified_oi(x,aware_time('2026-12-01T16:00:00Z')))
        self.assertEqual(qualified_oi(x,aware_time('2026-12-01T16:00:00Z'),context='TEST_LEGACY'),(10,20))
        # Actual next open changes across DST; a supplied arbitrary open cannot pass.
        x=copy.deepcopy(r); e=x['quant_metrics_json']['oi_evidence']
        x['trade_timestamp']='2026-03-06T16:00:00Z'
        e['session']=e['initial']['session']='2026-03-06'
        e['initial']['observed_at']=e['initial']['available_at']='2026-03-06T14:30:00Z'
        e['next_session']=e['next']['session']='2026-03-09'
        e['next_open_at']=e['next']['observed_at']=e['next']['available_at']='2026-03-09T13:30:00Z'
        self.assertEqual(qualified_oi(x,aware_time('2026-03-09T14:00:00Z')),(10,20))

    def test_fixed_interval_requires_explicit_test_context(self):
        from test_step5_kian_technicals import candles
        f=candles()
        self.assertEqual(analyze(f,'TEST',f['asof'])['status'],'UNKNOWN')
        self.assertEqual(analyze(f,'TEST',f['asof'],context='TEST_FIXED_INTERVAL')['status'],'AVAILABLE')
        f['context']='TEST_FIXED_INTERVAL'
        self.assertEqual(analyze(f,'TEST',f['asof'])['status'],'UNKNOWN')


def oi_row():
    contract=dict(ticker='TEST',strike=100,call_put='C',expiration='2026-12-18')
    return dict(contract, flow_id='TEST-oi',trade_timestamp='2026-11-27T16:00:00Z',initial_oi=10,next_day_oi=20,
                quant_metrics_json={'oi_evidence':dict(flow_id='TEST-oi',source='TEST-provider',contract=contract,
                session='2026-11-27',next_session='2026-11-30',session_timezone='America/New_York',
                session_evidence_id='TEST-calendar',next_open_at='2026-11-30T14:30:00Z',
                initial=dict(value=10,session='2026-11-27',available_at='2026-11-27T15:00:00Z',observed_at='2026-11-27T14:30:00Z',evidence_id='TEST-initial'),
                next=dict(value=20,session='2026-11-30',available_at='2026-11-30T15:30:00Z',observed_at='2026-11-30T15:00:00Z',evidence_id='TEST-next'))})
