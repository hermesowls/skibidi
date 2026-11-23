"""Persistent raw research observations, separate from trading and source DBs.

No network calls, migrations of trading data, or execution authority. A contract
is a grouping key, never a replacement for distinct provider events/versions.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3


def canonical_root(home=None):
    """Versioned non-secret research selection shared by writers and readers."""
    if home is None:
        from hermes_constants import get_hermes_home
        home = get_hermes_home()
    config = json.loads((Path(home) / 'research/config.json').read_text())
    if set(config) != {'version', 'root'} or config['version'] != 1:
        raise ValueError('Unsupported research configuration')
    root = Path(config['root'])
    if not root.is_absolute() or any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError('Canonical research root must be absolute and non-symlink')
    return root


def canonical_path(home=None):
    return canonical_root(home) / 'REAL_DATA_RESEARCH/watchlist.sqlite'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def timestamp(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('Timezone required')
    return dt


def validate_contract(symbol):
    if not isinstance(symbol, str) or not re.fullmatch(r'[A-Z][A-Z0-9]{0,5}[0-9]{6}[CP][0-9]{8}', symbol):
        raise ValueError('Invalid literal OCC contract')
    datetime.strptime(symbol[-15:-9], '%y%m%d')
    return symbol


@contextmanager
def connection(path, *, write=False):
    path = Path(path)
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Symlink database not permitted')
    if path.exists() and path.stat().st_nlink != 1:
        raise ValueError('Hardlinked database not permitted')
    wal = path.with_name(path.name + '-wal')
    if wal.exists() and wal.stat().st_size:
        raise ValueError('Stable standalone research database required')
    if not path.exists():
        if not write:
            raise FileNotFoundError(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb'):
            pass
        path.chmod(0o600)
        with sqlite3.connect(path) as c:
            c.execute('CREATE TABLE watchlist_identity (kind TEXT NOT NULL)')
            c.execute("INSERT INTO watchlist_identity VALUES ('research-watchlist-v1')")
            c.execute('CREATE TABLE observations (event_id TEXT, raw_hash TEXT, contract TEXT, executed_at TEXT, first_seen_at TEXT, source_hash TEXT, source_path TEXT, record_json TEXT, PRIMARY KEY(event_id, raw_hash))')
            c.execute('CREATE TABLE snapshots (id TEXT PRIMARY KEY, contract TEXT, received_at TEXT, endpoint TEXT, raw_hash TEXT, raw_body BLOB, summary_json TEXT)')
    c = sqlite3.connect(path.resolve().as_uri() + ('?mode=rw' if write else '?mode=ro&immutable=1'), uri=True)
    c.row_factory = sqlite3.Row
    try:
        tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view','trigger')")}
        if tables != {'watchlist_identity','observations','snapshots'} or [r[0] for r in c.execute('SELECT kind FROM watchlist_identity')] != ['research-watchlist-v1']:
            raise ValueError('Not a dedicated research watchlist database')
        if not write:
            c.execute('PRAGMA query_only=ON')
        with c:
            yield c
    finally:
        c.close()


def seed(db, source):
    source = Path(source)
    if Path(db).resolve() == source.resolve():
        raise ValueError('Source must remain separate')
    body = source.read_bytes()
    rows = json.loads(body)['records']
    prepared = []
    expected = Path(db).parent.name
    modes = {row.get('mode', 'REAL_DATA_RESEARCH') for row in rows}
    if expected in ('TEST', 'REAL_DATA_RESEARCH') and modes - {expected}:
        raise ValueError('Evidence cohort does not match destination cohort')
    if Path(db).exists():
        existing = read_watchlist(db)
        if existing['observation_count'] and modes - {existing['mode']}:
            raise ValueError('Cannot mix evidence cohorts')
    for row in rows:
        contract = validate_contract(row['evidence']['contract_symbol'])
        seen = row['received_at']
        timestamp(seen)
        raw = json.dumps(row['raw'], sort_keys=True, separators=(',', ':')).encode()
        prepared.append((row['provider_event_id'], digest(raw), contract,
            row['raw'].get('executed_at'), seen, digest(body), str(source.resolve()),
            json.dumps(row, sort_keys=True)))
    with connection(db, write=True) as c:
        c.executemany('INSERT OR IGNORE INTO observations VALUES (?,?,?,?,?,?,?,?)', prepared)
    return read_watchlist(db)


def store_snapshot(db, contract, raw_body, *, received_at, evidence_cohort='REAL_DATA_RESEARCH'):
    validate_contract(contract)
    tracked = read_watchlist(db)
    if evidence_cohort not in ('TEST', 'REAL_DATA_RESEARCH') or tracked['mode'] != evidence_cohort:
        raise ValueError('Snapshot evidence cohort mismatch')
    receipt = timestamp(received_at)
    data = json.loads(raw_body)['data']
    if not isinstance(data, list):
        raise ValueError('Expected minute bars')
    with connection(db, write=True) as c:
        seen = [timestamp(r[0]) for r in c.execute('SELECT first_seen_at FROM observations WHERE contract=?', (contract,))]
        if not seen:
            raise ValueError('Contract not seeded')
        # Latest first-seen is conservative for every linked print.
        cutoff = max(seen)
        valid = []
        unknown = 0
        for bar in data:
            if bar.get('option_symbol') is not None and bar['option_symbol'] != contract:
                raise ValueError('Response contract mismatch')
            try:
                t = timestamp(bar['start_time'])
            except (KeyError, ValueError, TypeError):
                unknown += 1
                continue
            if t > receipt:
                unknown += 1
                continue
            valid.append((t, bar['start_time']))
        asof = max(valid)[1] if valid else None
        raw_hash = digest(raw_body)
        sid = digest((contract + received_at + raw_hash).encode())
        summary = dict(id=sid, contract=contract, received_at=received_at,
            endpoint=f'/api/option-contract/{contract}/intraday', raw_hash=raw_hash,
            as_of=asof, age_seconds_at_receipt=(receipt-timestamp(asof)).total_seconds() if asof else None,
            first_seen_cutoff=cutoff.isoformat(), total_bars=len(data), unknown_time_bars=unknown,
            post_first_seen_bars=sum(t > cutoff for t, _ in valid),
            pre_first_seen_bars=sum(t <= cutoff for t, _ in valid),
            interpretation='Minute aggregates, not fills or confirmed buys',
            contract_identity=('RESPONSE_ECHO' if data and all(b.get('option_symbol') == contract for b in data) else 'REQUEST_PATH_ONLY_NO_RESPONSE_ECHO'),
            coverage='ONE_CONTRACT_PILOT', freshness='AS_OF_RECORDED_NOT_LIVE')
        c.execute('INSERT OR IGNORE INTO snapshots VALUES (?,?,?,?,?,?,?)',
            (sid, contract, received_at, summary['endpoint'], raw_hash, raw_body, json.dumps(summary)))
    return read_watchlist(db)


def store_context(db, raw_body, summaries, *, received_at, evidence_cohort):
    """Reuse immutable snapshot storage; context never admits/deletes UW candidates."""
    timestamp(received_at)
    tracked = read_watchlist(db)
    if evidence_cohort not in ('TEST', 'REAL_DATA_RESEARCH') or tracked['mode'] != evidence_cohort:
        raise ValueError('Context evidence cohort mismatch')
    prepared = []
    for summary in summaries:
        summary = dict(summary, contract=None, evidence_cohort=evidence_cohort,
            freshness='HISTORICAL_CONTEXT_NOT_ACTIONABLE', execution_authorized=False,
            publication_authorized=False, received_at=received_at, raw_hash=digest(raw_body))
        sid = digest(json.dumps([evidence_cohort, summary['source'], summary.get('channel_id'), summary.get('external_id'), summary.get('message_version', digest(raw_body))], sort_keys=True).encode())
        summary['id'] = sid
        prepared.append((sid, None, received_at, 'research-context/' + summary['source'],
            digest(raw_body), raw_body, json.dumps(summary, sort_keys=True, allow_nan=False)))
    with connection(db, write=True) as c:
        c.executemany('INSERT OR IGNORE INTO snapshots VALUES (?,?,?,?,?,?,?)', prepared)
    return read_watchlist(db)


def research_requests(contexts, updates):
    """Read-only setups over immutable native requests and attributed events."""
    originals = {}
    # Input is durable insertion order: backfills cannot replace first admission.
    for context in contexts:
        ticket = context.get('request_ticket')
        if ticket:
            originals.setdefault(ticket['id'], context)
    result = []
    for ticket_id, original in originals.items():
        ticket = original['request_ticket']
        events = [u for u in updates if u['ticket_id'] == ticket_id]
        for setup in sorted({u['setup_id'] for u in events}) or [None]:
            history = sorted((u for u in events if u['setup_id'] == setup), key=lambda u: u['sequence'])
            latest = history[-1] if history else {}
            result.append(dict(ticket_id=ticket_id, setup_id=setup, ticker=ticket['ticker'],
                requester=ticket['requester'], requester_identity=ticket['requester_identity'],
                original_context=original, updates=history,
                state=latest.get('state', 'pending-timeframe' if ticket['timeframe']=='UNKNOWN' else 'requested'),
                timeframe=latest.get('timeframe', ticket['timeframe']),
                execution_authorized=False, publication_authorized=False))
    return result


def append_request_update(db, update, *, evidence_cohort):
    """Append only, serialized with replay checking; never orders or scheduling.

    Actor attribution is a caller-supplied claim, not verified Kian identity.
    Monitoring requires a recorded explicit operating-plan approval reference;
    this does not activate a collector or authorize expenditure.
    """
    required = {'update_id','ticket_id','setup_id','state','actor','occurred_at',
                'received_at','timeframe','note','evidence_ids'}
    if not isinstance(update, dict) or not required <= set(update) or set(update)-required-{'monitoring_plan','analysis'}:
        raise ValueError('Closed research update schema required')
    for key in required - {'actor','evidence_ids'}:
        if not isinstance(update[key], str) or not update[key].strip():
            raise ValueError('Explicit nonempty update fields required')
    actor = update['actor']
    if not isinstance(actor, dict) or set(actor) != {'id','kind'} or not all(isinstance(v,str) and v.strip() for v in actor.values()):
        raise ValueError('Explicit actor attribution required')
    if 'analysis' in update:
        analysis = update['analysis']
        if (not isinstance(analysis,dict) or set(analysis) != {'thesis','trigger','invalidation','targets','expiry_context'}
                or not all(isinstance(analysis[k],str) and analysis[k].strip() for k in ('thesis','trigger','invalidation','expiry_context'))
                or not isinstance(analysis['targets'],list) or not all(isinstance(v,str) and v.strip() for v in analysis['targets'])):
            raise ValueError('Explicit attributed analysis fields required')
    occurred, received = timestamp(update['occurred_at']), timestamp(update['received_at'])
    if occurred > received:
        raise ValueError('Event cannot postdate receipt')
    raw = json.dumps(update, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    tracked = read_watchlist(db)
    if evidence_cohort not in ('TEST','REAL_DATA_RESEARCH') or tracked['mode'] != evidence_cohort:
        raise ValueError('Research update cohort mismatch')
    sid = digest(json.dumps(['research-request-update', evidence_cohort, update['update_id']]).encode())
    with connection(db, write=True) as c:
        c.execute('BEGIN IMMEDIATE')
        prior = c.execute('SELECT raw_body FROM snapshots WHERE id=?', (sid,)).fetchone()
        if prior:
            if bytes(prior[0]) != raw:
                raise ValueError('Research update idempotency conflict')
        else:
            rows = [dict(r) for r in c.execute('SELECT * FROM snapshots ORDER BY rowid')]
            contexts = [json.loads(r['summary_json']) for r in rows if r['endpoint'].startswith('research-context/')]
            events = [json.loads(r['summary_json']) for r in rows if r['endpoint']=='research-request-update']
            requests = research_requests(contexts, events)
            matches = [r for r in requests if r['ticket_id']==update['ticket_id']]
            if not matches:
                raise ValueError('Existing native request required')
            original = matches[0]['original_context']
            history = [e for e in events if e['ticket_id']==update['ticket_id'] and e['setup_id']==update['setup_id']]
            history.sort(key=lambda e:e['sequence'])
            previous = history[-1] if history else None
            state = previous['state'] if previous else ('pending-timeframe' if original['request_ticket']['timeframe']=='UNKNOWN' else 'requested')
            allowed = {'pending-timeframe':{'pending-timeframe','analyzed','closed'},
                       'requested':{'analyzed','closed'}, 'analyzed':{'analyzed','monitoring','closed'},
                       'monitoring':{'monitoring','analyzed','closed'}, 'closed':set()}
            if update['state'] not in allowed[state]:
                raise ValueError('Invalid research state transition')
            if occurred < timestamp(original['received_at']) or (previous and (occurred < timestamp(previous['occurred_at']) or received < timestamp(previous['received_at']))):
                raise ValueError('Research chronology reversed')
            if update['state'] in ('analyzed','monitoring') and update['timeframe'].strip().upper() in ('UNKNOWN','PENDING','NONE'):
                raise ValueError('Explicit timeframe required')
            if previous and previous['state'] in ('analyzed','monitoring') and update['timeframe'] != previous['timeframe']:
                raise ValueError('Different timeframe requires separate setup')
            evidence = update['evidence_ids']
            available = {r['id'] for r in rows if r['endpoint'] != 'research-request-update' and timestamp(r['received_at']) <= occurred}
            if not isinstance(evidence,list) or not all(isinstance(e,str) and e in available for e in evidence):
                raise ValueError('Existing point-in-time evidence required')
            if update['state'] in ('analyzed','monitoring') and not evidence:
                raise ValueError('Analysis evidence required')
            if update['state']=='monitoring':
                plan = update.get('monitoring_plan')
                if not isinstance(plan,dict) or set(plan) != {'approved_by','approval_ref','budget_ref','cadence','closure_rule'} or not all(isinstance(v,str) and v.strip() and v.upper()!='UNKNOWN' for v in plan.values()):
                    raise ValueError('Explicit approved monitoring plan required')
            summary = dict(update, id=sid, sequence=len(history)+1, evidence_cohort=evidence_cohort,
                           interpretation='ATTRIBUTED_RESEARCH_NOT_VERIFIED_OBSERVATION',
                           execution_authorized=False, publication_authorized=False)
            c.execute('INSERT INTO snapshots VALUES (?,?,?,?,?,?,?)', (sid,None,update['received_at'],
                      'research-request-update',digest(raw),raw,json.dumps(summary,sort_keys=True)))
    return read_watchlist(db)


def store_underlying_daily(db, ticker, raw_body, *, received_at, end_date, evidence_cohort):
    """Documented UW daily date/OHLC schema; calendar-derived completion, not provider time.

    Receipt-time descriptive context only: never a historical discovery feature.
    Raw daily bars have no provider observation timestamp; leave it unknown.
    """
    from .session_calendar import calendar, check_coverage
    from .execution_contract import number
    from .kian_technicals import analyze
    receipt = timestamp(received_at)
    check_coverage(receipt)
    if not isinstance(ticker, str) or not re.fullmatch(r'[A-Z][A-Z0-9]{0,5}', ticker):
        raise ValueError('Literal underlying ticker required')
    if not isinstance(end_date, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', end_date):
        raise ValueError('Literal end date required')
    datetime.strptime(end_date, '%Y-%m-%d')
    tracked = read_watchlist(db)
    if evidence_cohort not in ('TEST','REAL_DATA_RESEARCH') or tracked['mode'] != evidence_cohort:
        raise ValueError('Underlying cohort mismatch')
    if ticker not in {s[:-15] for s in tracked['contracts']}:
        raise ValueError('Underlying outside captured cohort')
    if not isinstance(raw_body, bytes) or len(raw_body) > 2_000_000:
        raise ValueError('Bounded raw bytes required')
    data = json.loads(raw_body)['data']
    if not isinstance(data, list) or len(data) > 2500:
        raise ValueError('Bounded daily rows required')
    bars=[]; seen=set(); excluded=0; excluded_extended=0
    for row in data:
        if (not isinstance(row, dict) or any(k in row for k in ('option_symbol','start_time','end_time'))
                or row.get('ticker', ticker) != ticker):
            raise ValueError('Not underlying OHLC')
        # Actual daily responses contain separate pre/regular/post rows per date.
        # Never combine sessions or invent OHLC. Preserve all rows in raw BLOB.
        if row.get('market_time') in ('pr','po'):
            excluded_extended += 1
            continue
        if row.get('market_time') not in (None,'r'):
            raise ValueError('Unknown daily market session')
        day=row.get('date')
        if not isinstance(day,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',day) or day in seen or day > end_date:
            raise ValueError('Invalid/duplicate daily date')
        seen.add(day)
        schedule=calendar().schedule.loc[day:day]
        if len(schedule) != 1:
            raise ValueError('Not an XNYS session')
        completion=schedule.iloc[0]['close'].to_pydatetime()
        from .uw_option_trades import decimal_field
        values={k:float(decimal_field(row,k,required=True)) for k in ('open','high','low','close')}
        values['volume']=number(row['volume'],'volume',zero=True)
        if not values['low'] <= min(values['open'],values['close']) <= max(values['open'],values['close']) <= values['high']:
            raise ValueError('Invalid daily OHLC')
        if completion > receipt:
            excluded += 1
            continue
        bars.append(dict(values,completed=True,completed_at=completion.isoformat(),provider_date=day))
    bars.sort(key=lambda b:timestamp(b['completed_at']))
    raw_hash=digest(raw_body)
    endpoint=f'/api/stock/{ticker}/ohlc/1d'
    sid=digest(json.dumps([ticker,received_at,end_date,raw_hash,evidence_cohort]).encode())
    candles=dict(ticker=ticker,source='UW_UNDERLYING_DAILY',evidence_id=sid,timeframe='1d',expected_interval_seconds=86400,
        max_age_seconds=1,asof=received_at,bars=bars)
    ta=analyze(candles,ticker,received_at)
    if ta['status'] != 'AVAILABLE':
        ta.update(status='INSUFFICIENT_DATA',ema=None,ttm=None)
    summary=dict(ta,id=sid,ticker=ticker,endpoint=endpoint,raw_hash=raw_hash,
        received_at=received_at,decision_at=received_at,provider_observed_at=None,
        provider='UW', source='UW_UNDERLYING_DAILY', delay_status='DAILY_NOT_REALTIME',
        market_session='REGULAR', quote_status='UNAVAILABLE',
        stale_status='CALENDAR_CURRENT_AT_RECEIPT' if ta['status']=='AVAILABLE' else 'INSUFFICIENT_OR_STALE',
        event_dates=[b['provider_date'] for b in bars],last_completed_at=bars[-1]['completed_at'] if bars else None,
        underlying_completed_bars=len(bars),raw_bars=len(data),excluded_incomplete_bars=excluded,
        excluded_extended_session_bars=excluded_extended,session_selection='REGULAR_ONLY_WHEN_PROVIDER_TAGGED',
        research_timeframe='DAILY',research_policy_version='UW-DAILY-DESCRIPTIVE-v1',
        timeframe_approval='PROVISIONAL_DESCRIPTIVE_ONLY',evidence_cohort=evidence_cohort,
        completion_provenance='XNYS_CALENDAR_DERIVED_NOT_PROVIDER_TIMESTAMP',
        use='RECEIPT_TIME_CONTEXT_NOT_DISCOVERY_TIME_SIGNAL',execution_authorized=False,publication_authorized=False)
    with connection(db,write=True) as c:
        c.execute('INSERT OR IGNORE INTO snapshots VALUES (?,?,?,?,?,?,?)',
            (sid,None,received_at,endpoint,raw_hash,raw_body,json.dumps(summary,sort_keys=True,allow_nan=False)))
    return read_watchlist(db)


def store_cboe_capture(db, ticker, raw_body, *, received_at, end_date, evidence_cohort):
    """Archive observed CBOE schema without inventing session/adjustment semantics.

    No CBOE payload currently qualifies for KIAN admission. Clock-only timestamp
    is not an aware provider observation time; all raw rows remain preserved.
    """
    from .realdata_cboe_worker import validate_request
    validate_request(ticker, 10)
    timestamp(received_at)
    datetime.strptime(end_date, '%Y-%m-%d')
    view = read_watchlist(db)
    if view['mode'] != evidence_cohort or ticker not in {s[:-15] for s in view['contracts']}:
        raise ValueError('CBOE capture outside cohort')
    if not isinstance(raw_body, bytes) or len(raw_body) > 1048576:
        raise ValueError('Bounded raw capture required')
    reasons=['REGULAR_SESSION_UNVERIFIED','ADJUSTMENT_UNKNOWN','PROVIDER_OBSERVATION_TIME_UNKNOWN']
    dates=[]; invalid=0; count=0; schema='UNKNOWN'
    try:
        payload=json.loads(raw_body)
        rows=payload['data']
        if not isinstance(rows,list) or len(rows)>20000:
            raise ValueError('Invalid data array')
        count=len(rows)
        if payload.get('symbol') != ticker:
            reasons.append('SYMBOL_MISMATCH_OR_MISSING')
        for row in rows:
            day=row['date']; datetime.strptime(day,'%Y-%m-%d'); dates.append(day)
            values=[row[k] for k in ('open','high','low','close','volume')]
            import math
            if any(type(v) not in (float,int) or not math.isfinite(v) for v in values):
                invalid+=1; continue
            o,h,l,c,v=values
            if not 0 < l <= min(o,c) <= max(o,c) <= h or v < 0:
                invalid+=1
        schema='CBOE_DATE_OHLCV_OBSERVED_V1'
    except (ValueError,TypeError,KeyError):
        reasons.append('MALFORMED_OR_UNSUPPORTED_SCHEMA')
    if invalid: reasons.append('INVALID_OHLCV_ROWS')
    if len(dates)!=len(set(dates)): reasons.append('DUPLICATE_DATES')
    raw_hash=digest(raw_body)
    sid=digest(json.dumps(['CBOE',ticker,received_at,end_date,raw_hash,evidence_cohort]).encode())
    summary=dict(id=sid,ticker=ticker,provider='CBOE',source='CBOE_HISTORY',
        status='CAPTURED_UNQUALIFIED',reason=';'.join(reasons),schema=schema,
        raw_hash=raw_hash,received_at=received_at,requested_end_date=end_date,
        provider_observed_at=None,market_session='UNKNOWN',adjustment_status='UNKNOWN',
        delay_status='UNKNOWN',stale_status='UNQUALIFIED',ema=None,ttm=None,
        raw_bars=count,invalid_ohlcv_rows=invalid,unique_dates=len(set(dates)),
        first_date=min(dates) if dates else None,last_date=max(dates) if dates else None,
        underlying_completed_bars=0,excluded_incomplete_bars=0,
        coverage_status='NOT_ADMITTED_SESSION_SEMANTICS_UNKNOWN',
        evidence_cohort=evidence_cohort,baseline_rejection=False,
        execution_authorized=False,publication_authorized=False)
    with connection(db,write=True) as c:
        c.execute('INSERT OR IGNORE INTO snapshots VALUES (?,?,?,?,?,?,?)',
            (sid,None,received_at,'research-underlying/cboe-history',raw_hash,raw_body,json.dumps(summary,sort_keys=True)))
    return summary


def configure_outcomes(db, config, *, received_at, evidence_cohort):
    """Persist explicit research measurement settings, never collector activation."""
    from .learning_evidence import validate_outcome_config
    validate_outcome_config(config, [received_at])
    current = read_watchlist(db)
    if evidence_cohort not in ('TEST', 'REAL_DATA_RESEARCH') or current['mode'] != evidence_cohort:
        raise ValueError('Outcome configuration cohort mismatch')
    anchors = [r['first_seen_at'] for r in current['observations']]
    with connection(db) as c:
        for row in c.execute("SELECT raw_body FROM snapshots WHERE endpoint LIKE '/api/option-contract/%/intraday'"):
            anchors.extend(b['start_time'] for b in json.loads(row[0])['data'])
    validate_outcome_config(config, anchors)
    raw = json.dumps(config, sort_keys=True, allow_nan=False).encode()
    sid = digest((evidence_cohort + config['version']).encode())
    summary = dict(id=sid, config=config, received_at=received_at, evidence_cohort=evidence_cohort,
        approval='CALLER_CONFIGURATION_NOT_OPERATING_APPROVAL', activation=False)
    with connection(db, write=True) as c:
        c.execute('BEGIN IMMEDIATE')
        existing = c.execute('SELECT raw_body FROM snapshots WHERE id=?', (sid,)).fetchone()
        if existing and bytes(existing[0]) != raw:
            raise ValueError('Outcome version is immutable; choose a new version')
        c.execute('INSERT OR IGNORE INTO snapshots VALUES (?,?,?,?,?,?,?)',
            (sid, None, received_at, 'research-outcome-config', digest(raw), raw, json.dumps(summary, sort_keys=True)))
    return read_watchlist(db)


def read_watchlist(db, *, outcome_as_of=None):
    with connection(db) as c:
        observations = [dict(r) for r in c.execute('SELECT * FROM observations ORDER BY contract,event_id,raw_hash')]
        stored = [dict(r) for r in c.execute('SELECT * FROM snapshots ORDER BY rowid')]
        snapshots, contexts, underlying, request_updates = [], [], [], []
        quotes = []
        outcome_configs, outcome_sources = [], []
        from .learning_evidence import observed_mark_path
        for row in stored:
            summary = json.loads(row['summary_json'])
            if row['endpoint'] == 'research-quotes/finviz':
                quotes.append(summary)
                continue
            if row['endpoint'] == 'research-outcome-config':
                outcome_configs.append(summary)
                continue
            if row['endpoint'] == 'research-request-update':
                request_updates.append(summary)
                continue
            if row['endpoint'] == 'research-underlying/cboe-history' or (row['endpoint'].startswith('/api/stock/') and row['endpoint'].endswith('/ohlc/1d')):
                underlying.append(summary)
                continue
            if row['endpoint'].startswith('research-context/'):
                contexts.append(summary)
                continue
            # Recompute conservative availability from current linked events.
            # A newly discovered print must not inherit an older print's path;
            # keep the original stored cutoff unchanged as historical provenance.
            cutoff = max((r['first_seen_at'] for r in observations if r['contract'] == row['contract']), key=timestamp)
            summary['observed_mark_path'] = observed_mark_path(json.loads(row['raw_body'])['data'],
                first_seen=cutoff, received_at=row['received_at'])
            snapshots.append(summary)
            outcome_sources.append(dict(summary, bars=json.loads(row['raw_body'])['data']))
    for row in observations:
        row['record'] = json.loads(row.pop('record_json'))
    contracts = sorted({r['contract'] for r in observations})
    covered = {s['contract'] for s in snapshots}
    cohorts = {r['record'].get('mode', 'REAL_DATA_RESEARCH') for r in observations}
    mode = next(iter(cohorts)) if len(cohorts) == 1 else ('MIXED_RESEARCH' if cohorts else 'EMPTY_RESEARCH')
    # Availability is a read-only projection, never a baseline admission gate.
    availability = {
        source: dict(context_status='SAVED_CONTEXT_ONLY' if any(x.get('source') == source for x in contexts) else 'UNAVAILABLE',
                     access_status='UNKNOWN', http_status=None, live_verified=False,
                     numeric_gex='UNKNOWN', baseline_rejection=False)
        for source in ('discord', 'skylit')
    }
    availability['finviz'] = dict(context_status='UNAVAILABLE', access_status='ADAPTER_UNQUALIFIED',
        provider='finviz', role='UNDERLYING_TA_AND_QUOTES_ONLY', provider_observed_at=None,
        received_at=None, delay_status='UNKNOWN', market_session='UNKNOWN', stale_status='UNAVAILABLE',
        live_verified=False, baseline_rejection=False)
    if quotes:
        latest=max(quotes,key=lambda q: timestamp(q['received_at']))
        availability['finviz'].update(context_status='SAVED_QUOTES_ONLY',access_status='SAVED_QUOTES_ONLY',
            received_at=latest['received_at'],stale_status='UNKNOWN',historical_ta_status='BLOCKED_OHLC_SCHEMA_UNVERIFIED')
    # Only the exact bounded, non-linked local receipt is eligible. Never expose
    # free-form provider errors, paths, credentials or native message contents.
    receipt = Path(db).parent / 'discord-native-page' / 'result.json'
    try:
        if (not receipt.parent.is_symlink() and not receipt.is_symlink()
                and receipt.is_file() and receipt.stat().st_nlink == 1):
            with receipt.open('rb') as stream:
                raw = stream.read(4097)
            saved = json.loads(raw) if len(raw) <= 4096 else {}
            if isinstance(saved, dict) and saved.get('status') == 'HTTP_BLOCKED' and type(saved.get('http_status')) is int and 400 <= saved['http_status'] <= 599:
                availability['discord'].update(access_status='HTTP_BLOCKED', http_status=saved['http_status'])
    except (OSError, ValueError):
        pass  # Missing/corrupt status evidence stays UNKNOWN, not a candidate loss.
    from .learning_evidence import baseline_learning_summary, research_outcomes
    # This canonical schema currently stores option intraday and source context,
    # not qualified underlying OHLC. Do not run EMA/TTM on contract prices or
    # pretend provider spot fields supply a completed underlying candle history.
    technicals = dict(status='INSUFFICIENT_DATA', version='KIAN-TA-v1',
        ema_periods=[8,21,50,100,200], ttm_variant='TTM-style BB20x2 KC20x1.5 SMA-TR LR20',
        underlying_completed_bars=0, ema=None, ttm=None,
        reason='No qualified completed underlying OHLC stored in canonical research; option marks are not underlying candles',
        timeframe='UNKNOWN', timeframe_approval='PENDING', probability=None)
    if underlying:
        technicals['reason'] = 'Per-snapshot receipt-time daily context is in underlying_technicals; no cohort-wide or discovery-time TA qualification'
    return dict(mode=mode, source_availability=availability,
        quote_snapshots=quotes, quote_snapshot_count=len(quotes),
        outcome_research=dict(research_outcomes(observations, outcome_sources, outcome_configs, as_of=outcome_as_of), evidence_cohort=mode),
        research_requests=research_requests(contexts, request_updates),
        research_update_count=len(request_updates),
        underlying_technicals=underlying, underlying_snapshot_count=len(underlying),
        technicals=technicals, learning_summary=baseline_learning_summary(observations, snapshots),
        observation_count=len(observations),
        contract_count=len(contracts), snapshot_count=len(snapshots),
        contracts=contracts, pending_contracts=[s for s in contracts if s not in covered],
        observations=observations, snapshots=snapshots, contexts=contexts, context_count=len(contexts),
        execution_authorized=False, verified_buy=False,
        unknowns=['GEX', 'EMA', 'TTM', 'next-session OI', 'fills', 'elapsed outcomes'])
