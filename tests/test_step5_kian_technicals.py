"""Deterministic TEST candles, no downloaded history or proprietary TTM claim."""
import importlib.util
import unittest
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from typing import Any


def candles() -> dict[str, Any]:
    at=datetime(2026,9,22,20,tzinfo=timezone.utc)
    return dict(source='TEST-completed-hourly',ticker='TEST',timeframe='1h',asof=at.isoformat(),
        max_age_seconds=3600,expected_interval_seconds=3600,evidence_id='TEST-bars',
        bars=[dict(completed_at=(at-timedelta(hours=201-i)).isoformat(),completed=True,
                   open=100.,high=101.,low=99.,close=100.,volume=1000) for i in range(201)])


class TechnicalEvidence(unittest.TestCase):
    def engine(self):
        self.assertIsNotNone(importlib.util.find_spec('plugins.analyst_trader.kian_technicals'),
                             'Missing pure provenance-validated candle surface')
        from plugins.analyst_trader.kian_technicals import analyze, ema
        from functools import partial
        return partial(analyze, context='TEST_FIXED_INTERVAL'),ema

    def test_ema_reference_and_compression_not_direction(self):
        analyze,ema=self.engine()
        # SMA seed over three bars; alpha=1/2. Independently calculated fractions.
        self.assertEqual(ema([1.,2.,3.,4.,2.],3),[None,None,2.,3.,2.5])
        x=[float(i) for i in range(1,205)]
        for period in (8,21,50,100,200):
            alpha=Fraction(2,period+1)
            reference=sum(Fraction(v) for v in x[:period])/period
            for value in x[period:]: reference=alpha*Fraction(value)+(1-alpha)*reference
            self.assertAlmostEqual(ema(x,period)[-1],float(reference),places=10)
        fixture=candles()
        result=analyze(fixture,'TEST',fixture['asof'])
        self.assertEqual(result['status'],'AVAILABLE')
        self.assertTrue(result['squeeze_on'])
        self.assertFalse(result['release'])
        self.assertEqual(result['direction'],'CONFLICT')
        self.assertEqual(result['momentum'],0)
        self.assertIsNone(result['probability'])

    def test_invalid_future_gappy_expired_or_short_is_unknown(self):
        analyze,_=self.engine()
        for kind in ('future','gap','duplicate','invalid','incomplete','short','stale','ticker'):
            with self.subTest(kind=kind):
                f=candles()
                if kind=='future': f['bars'][-1]['completed_at']='2099-01-01T00:00:00Z'
                if kind=='gap': f['bars'].pop(100)
                if kind=='duplicate': f['bars'][-1]['completed_at']=f['bars'][-2]['completed_at']
                if kind=='invalid': f['bars'][-1]['close']=float('nan')
                if kind=='incomplete': f['bars'][-1]['completed']=False
                if kind=='short': f['bars']=f['bars'][-40:]
                if kind=='stale': f['asof']='2026-10-01T20:00:00Z'
                if kind=='ticker': f['ticker']='OTHER'
                self.assertEqual(analyze(f,'TEST',f['asof'])['status'],'UNKNOWN')

    def test_momentum_fading_both_signs_with_independent_rational_oracle(self):
        analyze,_=self.engine()
        # Fixed Donchian midpoint=100. LR20 endpoint weights are calculated
        # analytically, not by calling production EMA/endpoint helpers.
        for sign in (1,-1):
            for last, fading in ((0,True),(20,False)):
                with self.subTest(sign=sign,last=last):
                    f=candles()
                    deviations=[Fraction(0)]*199+[Fraction(sign*20),Fraction(sign*last)]
                    for bar,d in zip(f['bars'],deviations):
                        bar.update(high=121.,low=79.,close=float(100+d))
                    detrended=[deviations[i]-sum(deviations[i-19:i+1])/40 for i in range(19,201)]
                    weights=[Fraction(1,20)+Fraction(2*i-19,2)*Fraction(19,2)/665 for i in range(20)]
                    expected=sum(w*d for w,d in zip(weights,detrended[-20:]))
                    prior=sum(w*d for w,d in zip(weights,detrended[-21:-1]))
                    r=analyze(f,'TEST',f['asof'])
                    self.assertEqual(r['status'],'AVAILABLE')
                    self.assertAlmostEqual(r['momentum'],float(expected),places=10)
                    self.assertAlmostEqual(r['momentum_slope'],float(expected-prior),places=10)
                    self.assertEqual(r['fading'],fading)
                    self.assertEqual(r['momentum_direction'],'BULLISH' if sign==1 else 'BEARISH')
        flat=candles();r=analyze(flat,'TEST',flat['asof'])
        self.assertEqual((r['momentum'],r['momentum_slope'],r['fading']),(0,0,False))

    def test_ema_hold_reclaim_loss_and_equality_boundaries(self):
        analyze,_=self.engine()
        cases=((110,110,'HOLD_ABOVE'),(90,90,'HOLD_BELOW'),
               (90,110,'RECLAIM'),(110,90,'LOSS'),(100,100,'AT_EMA'),
               (100,110,'RECLAIM'),(100,90,'LOSS'))
        for previous,current,state in cases:
            with self.subTest(previous=previous,current=current):
                f=candles()
                for bar,close in zip(f['bars'][-2:],(previous,current)):
                    bar.update(high=121.,low=79.,close=close)
                r=analyze(f,'TEST',f['asof'])
                for period in (8,21):
                    self.assertEqual(r['ema_price_state'][str(period)],state)
                    alpha=Fraction(2,period+1)
                    previous_ema=100+alpha*(previous-100)
                    expected=previous_ema+alpha*(current-previous_ema)
                    self.assertAlmostEqual(r['ema'][str(period)],float(expected),places=10)
        # Land exactly on each EMA from either side (not merely flat bars).
        for period,previous,current in ((8,109,102),(8,91,98),(21,111,101),(21,89,99)):
            with self.subTest(period=period,previous=previous):
                f=candles()
                for bar,close in zip(f['bars'][-2:],(previous,current)):
                    bar.update(high=121.,low=79.,close=close)
                r=analyze(f,'TEST',f['asof'])
                self.assertEqual(r['ema'][str(period)],current)
                self.assertEqual(r['ema_price_state'][str(period)],'AT_EMA')

    def test_release_separates_bull_bear_and_fading(self):
        analyze,_=self.engine()
        for sign in (1,-1):
            f=candles()
            f['bars'][-1].update(open=100.,close=100.+sign*20,high=121.,low=79.)
            r=analyze(f,'TEST',f['asof'])
            self.assertTrue(r['release'])
            self.assertEqual(r['momentum_direction'],'BULLISH' if sign==1 else 'BEARISH')
            self.assertGreater(sign*r['momentum'],0)
