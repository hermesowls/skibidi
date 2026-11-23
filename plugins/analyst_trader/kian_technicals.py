"""Pure KIAN-TA-v1: SMA-seeded EMA; explicit TTM-style, not proprietary TTM.

BB(20,SMA,population std,2); KC(20,SMA close,SMA true range,1.5).
Compression: strict BB inside KC. Equality is off. Release: previous on,
current off. Momentum: 20-bar least-squares endpoint of close minus mean
of Donchian midpoint(20) and SMA close(20). No probability or learned edge.
Session completions use a bounded maintained calendar, never imputation.
"""
from typing import Any
from statistics import fmean, pstdev
from .execution_contract import number, identity
from .learning_evidence import aware_time


def ema(values, period):
    if isinstance(period,bool) or not isinstance(period,int) or period<1:
        raise ValueError('Invalid EMA period')
    x=[number(v,'close') for v in values]
    out: list[float | None]=[None]*len(x)
    if len(x)<period: return out
    current=fmean(x[:period]); out[period-1]=current
    for i in range(period,len(x)):
        current+=(x[i]-current)*2/(period+1)
        out[i]=current
    return out


def analyze(candles, ticker, decision_at, *, context='XNYS_REGULAR') -> dict[str, Any]:
    unknown=dict(status='UNKNOWN',version='KIAN-TA-v1',direction='UNKNOWN',probability=None)
    try:
        if context not in ('XNYS_REGULAR', 'TEST_FIXED_INTERVAL'):
            raise ValueError('Unsupported calendar context')
        fixed = context == 'TEST_FIXED_INTERVAL'
        from .session_calendar import completions, provenance
        if not isinstance(candles,dict) or candles.get('ticker')!=ticker:
            raise ValueError('Missing/mismatched candles')
        identity(candles.get('source'),'candle source');identity(candles.get('evidence_id'),'candle evidence')
        period={'1h':3600,'1d':86400}.get(str(candles.get('timeframe')))
        if period is None or candles.get('expected_interval_seconds')!=period:
            raise ValueError('Unsupported/mismatched timeframe')
        at=aware_time(candles['asof']); decision=aware_time(decision_at)
        max_age=number(candles.get('max_age_seconds'),'candle max age')
        if at>decision or (decision-at).total_seconds()>max_age:
            raise ValueError('Stale/future candle snapshot')
        bars=candles['bars']
        if not isinstance(bars,list) or len(bars)<201:
            raise ValueError('EMA slope requires at least 201 completed bars')
        times=[]; closes=[]; highs=[]; lows=[]; ranges=[]
        for b in bars:
            t=aware_time(b['completed_at'])
            if b.get('completed') is not True or t>at or (times and (t<=times[-1] or (fixed and (t-times[-1]).total_seconds()!=period))):
                raise ValueError('Incomplete/future/unsorted/duplicate/gappy candles')
            o,h,l,c=(number(b[k],k) for k in ('open','high','low','close'))
            number(b['volume'],'volume',zero=True)
            if not l<=min(o,c)<=max(o,c)<=h: raise ValueError('Invalid OHLC')
            tr=max(h-l,abs(h-closes[-1]),abs(l-closes[-1])) if closes else h-l
            times.append(t);closes.append(c);highs.append(h);lows.append(l);ranges.append(tr)
        if fixed:
            if (decision-times[-1]).total_seconds()>max_age: raise ValueError('Expired completed bar')
        elif times != completions(times[0], decision, candles['timeframe']):
            raise ValueError('Missing or off-session expected completed bars')
    except (KeyError,TypeError,ValueError,OverflowError,ImportError) as exc:
        return dict(unknown,reason=str(exc))
    # All five series are warmed up; numeric validation makes that invariant explicit.
    arrays={p:[number(v,'warmed EMA') for v in ema(closes,p)[-2:]] for p in (8,21,50,100,200)}
    current={str(p):a[-1] for p,a in arrays.items()}
    slopes={str(p):a[-1]-a[-2] for p,a in arrays.items()}
    stack=[closes[-1]]+list(current.values())
    direction='BULLISH' if all(a>b for a,b in zip(stack,stack[1:])) else 'BEARISH' if all(a<b for a,b in zip(stack,stack[1:])) else 'CONFLICT'
    states={}
    for p in (8,21):
        prev=closes[-2]-arrays[p][-2]; cur=closes[-1]-arrays[p][-1]
        states[str(p)]='RECLAIM' if prev<=0<cur else 'LOSS' if prev>=0>cur else 'HOLD_ABOVE' if prev>0 and cur>0 else 'HOLD_BELOW' if prev<0 and cur<0 else 'AT_EMA'
    def squeeze(i):
        close=closes[i-19:i+1]; mid=fmean(close); width=2*pstdev(close)
        kc=1.5*fmean(ranges[i-19:i+1])
        return width<kc,dict(bb_lower=mid-width,bb_upper=mid+width,kc_lower=mid-kc,kc_upper=mid+kc)
    previous,_=squeeze(len(closes)-2); on,bands=squeeze(len(closes)-1)
    detrended=[]
    for i in range(19,len(closes)):
        midpoint=(max(highs[i-19:i+1])+min(lows[i-19:i+1]))/2
        detrended.append(closes[i]-(midpoint+fmean(closes[i-19:i+1]))/2)
    def endpoint(y):
        avg=fmean(y); center=(len(y)-1)/2
        slope=sum((i-center)*(v-avg) for i,v in enumerate(y))/sum((i-center)**2 for i in range(len(y)))
        return avg+slope*center
    momentum=endpoint(detrended[-20:]); prior=endpoint(detrended[-21:-1])
    return dict(status='AVAILABLE',version='KIAN-TA-v1',variant='TTM-style BB20x2 KC20x1.5 SMA-TR LR20',
        calendar={'adapter_version':'TEST_FIXED_INTERVAL'} if fixed else provenance(),
        source=candles['source'],ticker=ticker,timeframe=candles['timeframe'],asof=candles['asof'],
        evidence_id=candles['evidence_id'],last_completed_at=times[-1].isoformat(),bars=len(bars),
        ema=current,ema_slope=slopes,ema_price_state=states,direction=direction,
        trend50='ABOVE' if closes[-1]>current['50'] else 'BELOW' if closes[-1]<current['50'] else 'AT',
        context100=current['100'],context200=current['200'],squeeze_on=on,squeeze_off=not on,
        release=previous and not on,momentum=momentum,momentum_slope=momentum-prior,
        momentum_direction='BULLISH' if momentum>0 else 'BEARISH' if momentum<0 else 'FLAT',
        fading=abs(momentum)<abs(prior),bands=bands,probability=None)
