"""Bounded maintained XNYS regular-session schedule; never market data.

Coverage is intentionally frozen. Extending it or changing the package requires
review. No weekday fallback, network, imputation or provider timestamp inference.
"""
from datetime import timedelta
from functools import lru_cache
from importlib.metadata import version

ADAPTER_VERSION = 'XNYS-REGULAR-v1'
START, END = '2020-01-01', '2027-12-31'


@lru_cache(maxsize=1)
def calendar():
    import exchange_calendars
    return exchange_calendars.get_calendar('XNYS', start=START, end=END)


def provenance():
    return dict(adapter_version=ADAPTER_VERSION, exchange='XNYS',
                library='exchange_calendars', library_version=version('exchange-calendars'),
                coverage_start=START, coverage_end=END, session_scope='regular',
                completion_policy='open-anchored-hourly-short-final-or-daily-close')


def check_coverage(at):
    if not START <= at.date().isoformat() <= END:
        raise ValueError('Outside bounded calendar coverage')


def completions(first, decision, timeframe):
    check_coverage(first); check_coverage(decision)
    if timeframe not in ('1h', '1d') or first > decision:
        raise ValueError('Invalid completion range')
    times = []
    schedule = calendar().schedule.loc[first.date().isoformat():decision.date().isoformat()]
    for _, row in schedule.iterrows():
        opening, closing = row['open'].to_pydatetime(), row['close'].to_pydatetime()
        t = opening + timedelta(hours=1) if timeframe == '1h' else closing
        while t < closing:
            if first <= t <= decision: times.append(t)
            t += timedelta(hours=1)
        if first <= closing <= decision: times.append(closing)
    return times


def next_session(trade_at):
    check_coverage(trade_at)
    from zoneinfo import ZoneInfo
    session = trade_at.astimezone(ZoneInfo('America/New_York')).date().isoformat()
    c = calendar()
    if not c.is_session(session):
        raise ValueError('Trade date is not an XNYS session')
    following = c.next_session(session)
    return session, following.date().isoformat(), c.session_open(following).to_pydatetime()
