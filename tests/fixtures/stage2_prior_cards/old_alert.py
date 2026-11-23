"""Required alert units in the producer SQLite database. No scheduler or secret lookup.

A send intent is durable before transport. Lost acknowledgements are unknown, never
silently replayed. SQLite transactions never span transport calls.
"""
import json
import math
import sqlite3
import time
import uuid
from contextlib import contextmanager
from typing import Any


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


class AlertOutbox:
    def __init__(self, path, *, clock=time.time):
        self.path = str(path)
        self.clock = clock
        with self.transaction() as c:
            c.executescript('''
                CREATE TABLE IF NOT EXISTS alert_messages (
                    alert_id TEXT NOT NULL, revision INTEGER NOT NULL,
                    identity_json TEXT NOT NULL, created_at REAL NOT NULL,
                    PRIMARY KEY(alert_id,revision));
                CREATE TABLE IF NOT EXISTS alert_units (
                    alert_id TEXT NOT NULL, revision INTEGER NOT NULL,
                    platform TEXT NOT NULL, destination TEXT NOT NULL, card TEXT NOT NULL,
                    payload TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'pending',
                    attempts INTEGER NOT NULL DEFAULT 0, next_retry REAL NOT NULL DEFAULT 0,
                    claim TEXT, lease_until REAL, send_intent REAL, receipt TEXT,
                    last_error TEXT, updated_at REAL NOT NULL,
                    PRIMARY KEY(alert_id,revision,platform,destination,card));
                CREATE TABLE IF NOT EXISTS alert_resolutions (
                    resolution_id INTEGER PRIMARY KEY, unit_key TEXT NOT NULL,
                    authorization_json TEXT NOT NULL, created_at REAL NOT NULL);
            ''')

    @contextmanager
    def transaction(self):
        c = sqlite3.connect(self.path, timeout=5)
        c.row_factory = sqlite3.Row
        try:
            c.execute('BEGIN IMMEDIATE')
            yield c
            c.commit()
        except BaseException:
            c.rollback()
            raise
        finally:
            c.close()

    def enqueue(self, recommendation, publication, destinations, cards):
        if not isinstance(publication, dict) or publication.get('publishing_authorized') is not True:
            return {'status': 'denied', 'reason': 'Explicit publishing authorization required', 'units': []}
        a = publication.get('alert_id')
        v = publication.get('revision')
        for key in ('alert_id','policy_version','flow_id'):
            value = publication.get(key)
            if not isinstance(value,str) or not value.strip() or value!=value.strip() or len(value)>256:
                raise ValueError('Invalid publication '+key)
        if 'flow_id' in recommendation and recommendation['flow_id']!=publication['flow_id']:
            raise ValueError('Publication/source identity mismatch')
        if (not isinstance(a, str) or not a.strip() or a != a.strip()
                or type(v) is not int or v < 1 or not publication.get('policy_version')
                or not publication.get('flow_id')):
            raise ValueError('Invalid publication identity/policy')
        if not destinations:
            return {'status': 'blocked', 'reason': 'No required destinations configured', 'units': []}
        if not cards or len(cards) > 10 or len(destinations) > 50:
            raise ValueError('Invalid delivery scope')
        if len(set(destinations)) != len(destinations):
            raise ValueError('Duplicate destinations')
        for platform, destination in destinations:
            if platform not in ('discord', 'telegram') or not isinstance(destination, str) or not destination:
                raise ValueError('Invalid destination')
        identity = canonical(dict(recommendation=recommendation, publication=publication,
                                  destinations=sorted(destinations), cards=cards))
        now = self.clock()
        with self.transaction() as c:
            old = c.execute('SELECT identity_json FROM alert_messages WHERE alert_id=? AND revision=?', (a,v)).fetchone()
            if old:
                if old[0] != identity:
                    raise ValueError('ALERT_ID_CONFLICT: use an explicitly authorized revision')
            else:
                if v > 1 and (not publication.get('revision_reason') or not c.execute(
                        'SELECT 1 FROM alert_messages WHERE alert_id=? AND revision=?', (a,v-1)).fetchone()):
                    raise ValueError('Explicit sequential correction revision and reason required')
                source = c.execute('SELECT * FROM notable_flow WHERE flow_id=?', (publication['flow_id'],)).fetchone()
                if (source is None or source['is_quarantined'] not in (None,0)
                        or source['final_outcome'] != 'MONITORING'
                        or any(source[k] != recommendation.get(k) for k in ('ticker','strike','call_put','expiration'))):
                    raise ValueError('SOURCE_NOT_ELIGIBLE')
                if c.execute('SELECT 1 FROM flow_candidate_analytics WHERE flow_id=? AND COALESCE(is_quarantined,0)!=0', (publication['flow_id'],)).fetchone():
                    raise ValueError('SOURCE_NOT_ELIGIBLE: linked quarantine')
                c.execute('INSERT INTO alert_messages VALUES(?,?,?,?)', (a,v,identity,now))
                for platform, destination in destinations:
                    for card, payload in cards.items():
                        c.execute('''INSERT INTO alert_units(alert_id,revision,platform,destination,card,payload,updated_at)
                                     VALUES(?,?,?,?,?,?,?)''', (a,v,platform,destination,card,canonical(payload),now))
        return self.summary(a,v)

    def resume(self, publication, destinations, transport, *, limit=100):
        """Delivery-only replay of persisted identity with explicit same policy/config.

        No recommendation regeneration, inference, execution, or new units. The
        existing drain rechecks source/quarantine immediately before send intent.
        """
        if not isinstance(publication, dict) or publication.get('publishing_authorized') is not True:
            return dict(status='denied', reason='Explicit publishing authorization required', units=[])
        with self.transaction() as c:
            row = c.execute('SELECT identity_json FROM alert_messages WHERE alert_id=? AND revision=?',
                            (publication.get('alert_id'), publication.get('revision'))).fetchone()
            if row is None:
                return dict(status='blocked', reason='No persisted publication', units=[])
            identity = json.loads(row[0])
            if (canonical(publication) != canonical(identity['publication'])
                    or canonical(sorted(destinations)) != canonical(identity['destinations'])):
                raise ValueError('ALERT_ID_CONFLICT: resume requires persisted policy/source/config')
        return dict(self.drain(publication['alert_id'], publication['revision'], transport, limit=limit),
                    capability='text_only', media_delivered=False)

    def resolve(self, key, authorization):
        """Trusted operator boundary, never called automatically.

        Only an unknown unit may be resolved. Confirmed-unsent is an explicit
        attestation, not a timeout inference. Abandon is the safe default when
        evidence cannot disambiguate. No generic force-resend operation exists.
        """
        if (len(key)!=5 or not isinstance(authorization,dict)
                or authorization.get('authorized') is not True
                or authorization.get('workers_quiesced') is not True
                or authorization.get('scope')!=list(key)
                or any(not isinstance(authorization.get(k),str) or not authorization[k].strip()
                       for k in ('operator','policy_version','reason'))):
            raise ValueError('Explicit scoped operator authorization required')
        decision = authorization.get('decision')
        states = {'confirmed_delivered':'succeeded','confirmed_unsent':'retryable','abandon':'permanent'}
        if decision not in states or (decision=='confirmed_delivered' and not authorization.get('receipt')):
            raise ValueError('Invalid resolution/evidence')
        with self.transaction() as c:
            row = c.execute('SELECT rowid,* FROM alert_units WHERE alert_id=? AND revision=? AND platform=? AND destination=? AND card=?',key).fetchone()
            if row is None or row['state']!='unknown':
                raise ValueError('Resolution requires unknown unit')
            if decision=='confirmed_unsent' and row['attempts']>=3:
                raise ValueError('Retry budget exhausted; abandon or confirm receipt')
            c.execute('INSERT INTO alert_resolutions(unit_key,authorization_json,created_at) VALUES(?,?,?)',
                      (canonical(key),canonical(authorization),self.clock()))
            c.execute('UPDATE alert_units SET state=?,receipt=?,last_error=?,next_retry=?,updated_at=?,claim=NULL WHERE rowid=?',
                      (states[decision],authorization.get('receipt'), 'Operator: '+authorization['reason'],self.clock(),self.clock(),row['rowid']))
        return self.summary(key[0],key[1])

    def summary(self, a, v) -> dict[str, Any]:
        with self.transaction() as c:
            units = [dict(r) for r in c.execute('SELECT * FROM alert_units WHERE alert_id=? AND revision=? ORDER BY platform,destination,card',(a,v))]
        states = [u['state'] for u in units]
        ambiguous_inflight = any(u['state']=='inflight' and u['send_intent'] is not None for u in units)
        status = ('blocked' if not states else 'complete' if all(s=='succeeded' for s in states)
                  else 'uncertain' if 'unknown' in states or ambiguous_inflight else 'partial' if 'succeeded' in states
                  else 'failed' if all(s=='permanent' for s in states) else 'pending')
        return dict(alert_id=a, revision=v, status=status, units=units)

    def drain(self, a, v, transport, *, limit=100):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError('Batch must be 1..100')
        for _ in range(limit):
            now = self.clock()
            with self.transaction() as c:
                # A claimed but not yet intended send is definitely unsent. Once
                # intent commits, lease expiry cannot establish non-delivery.
                c.execute('''UPDATE alert_units SET state=CASE WHEN send_intent IS NULL THEN 'retryable' ELSE 'unknown' END,
                             last_error='Lease expired; reconcile send intent', claim=NULL, updated_at=?
                             WHERE alert_id=? AND revision=? AND state='inflight' AND lease_until<=?''',(now,a,v,now))
                row = c.execute('''SELECT rowid,* FROM alert_units WHERE alert_id=? AND revision=?
                                  AND state IN ('pending','retryable') AND next_retry<=? ORDER BY platform,destination,card LIMIT 1''',(a,v,now)).fetchone()
                if row is None:
                    break
                token = uuid.uuid4().hex
                c.execute("UPDATE alert_units SET state='inflight',claim=?,lease_until=?,send_intent=NULL,updated_at=? WHERE rowid=?",(token,now+60,now,row['rowid']))
            with self.transaction() as c:
                identity = json.loads(c.execute('SELECT identity_json FROM alert_messages WHERE alert_id=? AND revision=?',(a,v)).fetchone()[0])
                flow_id = identity['publication']['flow_id']
                source = c.execute('SELECT * FROM notable_flow WHERE flow_id=?',(flow_id,)).fetchone()
                eligible = (source is not None and source['is_quarantined'] in (None,0)
                            and source['final_outcome']=='MONITORING'
                            and all(source[k]==identity['recommendation'].get(k) for k in ('ticker','strike','call_put','expiration'))
                            and not c.execute('SELECT 1 FROM flow_candidate_analytics WHERE flow_id=? AND COALESCE(is_quarantined,0)!=0',(flow_id,)).fetchone())
                candidate = identity['recommendation'].get('research_candidate')
                if eligible and source is not None and candidate is not None:
                    from .learning_store import digest, source_snapshot
                    raw = c.execute('SELECT * FROM raw_messages WHERE message_id=?',(source['raw_message_id'],)).fetchone()
                    try:
                        eligible = (candidate['source_id']==flow_id
                            and digest(source_snapshot(source))==candidate['source_hash']
                            and raw is not None and digest(dict(raw))==candidate['raw_source_hash'])
                    except (KeyError,TypeError,ValueError):
                        eligible = False
                if not eligible:
                    c.execute("UPDATE alert_units SET state='permanent',last_error='SOURCE_NOT_ELIGIBLE',claim=NULL,updated_at=? WHERE rowid=? AND claim=? AND state='inflight'",(now,row['rowid'],token))
                    continue
                changed = c.execute('''UPDATE alert_units SET send_intent=?,attempts=attempts+1,updated_at=?
                                       WHERE rowid=? AND claim=? AND state='inflight' AND lease_until>?''',(now,now,row['rowid'],token,now)).rowcount
            if not changed:
                continue
            unit = dict(row)
            unit['payload'] = json.loads(unit['payload'])
            try:
                result = transport(unit) if transport else dict(state='permanent', error='Provider not configured')
            except Exception as exc:
                result = dict(state='unknown', error=type(exc).__name__)
            state = result.get('state') if isinstance(result,dict) else 'unknown'
            receipt = result.get('receipt') if isinstance(result,dict) else None
            error = result.get('error') if isinstance(result,dict) else 'Invalid transport result'
            if state not in ('succeeded','retryable','permanent','unknown') or (state=='succeeded' and not receipt):
                state, error = 'unknown', 'Unconfirmed provider response'
            attempts = row['attempts']+1
            delay = 5 * 2 ** (attempts-1)
            if state=='retryable':
                raw = result.get('retry_after', 0)
                if isinstance(raw,(int,float)) and not isinstance(raw,bool) and math.isfinite(raw) and raw>=0:
                    delay = max(delay,raw)
                else:
                    state, error = 'unknown', 'Invalid Retry-After'
                if attempts>=3:
                    state, error = 'permanent', 'Retry budget exhausted: '+str(error)
            try:
                with self.transaction() as c:
                    c.execute('''UPDATE alert_units SET state=?,receipt=?,last_error=?,next_retry=?,updated_at=?,claim=NULL
                                 WHERE rowid=? AND claim=? AND state='inflight' ''',
                              (state,str(receipt) if receipt else None,error,self.clock()+delay,self.clock(),row['rowid'],token))
            except sqlite3.Error:
                # Persisted intent is already a durable uncertainty marker. Stop
                # this batch; never convert a lost receipt into an unsent retry.
                break
        return self.summary(a,v)


class ProviderTransport:
    """Explicit credentials only; one HTTP request, no hidden retry or idempotency.

    Discord and Telegram send endpoints do not supply a general exactly-once
    contract. Timeout, malformed ACK and 5xx remain unknown rather than replaying.
    """
    def __init__(self, *, discord_token='', telegram_token='', request=None, clock=time.time):
        self.tokens = {'discord': discord_token, 'telegram': telegram_token}
        self.request = request or self._request
        self.clock = clock

    @staticmethod
    def _request(url, payload, headers, timeout):
        import urllib.request
        import urllib.error
        # Explicitly disable redirect following: a POST must not be transformed or
        # credentials forwarded to another host. No environment proxy discovery.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        req = urllib.request.Request(url, data=canonical(payload).encode(), headers=headers, method='POST')
        try:
            response = opener.open(req, timeout=timeout)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            raw = response.read(1024*1024)
            try:
                data = json.loads(raw)
            except (ValueError, UnicodeError):
                data = None
            return response.code, dict(response.headers), data

    def __call__(self, unit):
        from urllib.parse import quote
        platform, destination = unit['platform'], unit['destination']
        token = self.tokens.get(platform)
        if not token:
            return dict(state='permanent', error='Provider not configured')
        headers = {'Content-Type':'application/json'}
        if platform=='discord':
            url = 'https://discord.com/api/v10/channels/'+quote(destination,safe='')+'/messages'
            headers['Authorization'] = 'Bot '+token
            payload = dict(unit['payload'], allowed_mentions={'parse':[]})
        elif platform=='telegram':
            url = 'https://api.telegram.org/bot'+quote(token,safe=':')+'/sendMessage'
            payload = dict(chat_id=destination, text=unit['payload']['content'], link_preview_options={'is_disabled':True})
        else:
            return dict(state='permanent', error='Unsupported provider')
        try:
            status, response_headers, data = self.request(url,payload,headers,10)
        except Exception as exc:
            return dict(state='unknown', error='Transport '+type(exc).__name__)
        data = data if isinstance(data,dict) else {}
        code = data.get('error_code') if platform=='telegram' and data.get('ok') is False else status
        if code==429:
            raw = data.get('parameters',{}).get('retry_after') if platform=='telegram' else data.get('retry_after')
            raw = raw if raw is not None else next((v for k,v in response_headers.items() if k.lower()=='retry-after'),None)
            try:
                try:
                    delay = float(str(raw))
                except (TypeError, ValueError):
                    from email.utils import parsedate_to_datetime
                    delay = max(0,parsedate_to_datetime(str(raw)).timestamp()-self.clock())
                if not math.isfinite(delay) or delay < 0:
                    raise ValueError('Invalid delay')
                if delay > 86400:
                    return dict(state='permanent',error='Retry-After exceeds one-day policy')
                return dict(state='retryable',error='Provider rate limited',retry_after=delay)
            except (TypeError,ValueError,OverflowError):
                return dict(state='unknown',error='Unusable rate limit response')
        if type(code) is int and 400 <= code < 500 and code not in (408,425):
            return dict(state='permanent',error='Provider rejection '+str(code))
        if status in (200,201):
            if platform=='discord' and isinstance(data.get('id'),str) and data['id'].isdigit() and str(data.get('channel_id'))==destination and 'code' not in data:
                return dict(state='succeeded',receipt=data['id'])
            if platform=='telegram' and data.get('ok') is True:
                result = data.get('result')
                if (isinstance(result,dict) and type(result.get('message_id')) is int and result['message_id']>0
                        and str(result.get('chat',{}).get('id'))==destination):
                    return dict(state='succeeded',receipt=str(result['message_id']))
        return dict(state='unknown',error='Unconfirmed provider response '+str(status))


def actionable_cards(rec):
    """Two immutable, readable cards; no asynchronous untracked image patch."""
    thesis = str(rec.get('clean_thesis') or 'No thesis supplied')
    candidate=rec.get('research_candidate')
    if candidate is not None:
        evidence=candidate['evidence']
        thesis = (f"TEST/offline research candidate; not a confirmed setup.\n"
                  f"Baseline: {candidate['baseline_status']} | Enhanced: {candidate['enhanced_status']}\n"
                  f"Source: {candidate['source_id']} | Decision: {candidate['decision_id']}\n"
                  f"Policy: {candidate['policy_version']} | Hash: {candidate['policy_hash']}\n"
                  f"Novelty: {candidate['novelty']} | DTE: {candidate['dte']} ({candidate['calendar_zone']})\n"
                  f"Single-print premium: {evidence.get('premium_usd')} | Size: {evidence.get('size')}\n"
                  f"Aggregate contract volume: {evidence.get('volume')} | Open Interest: {evidence.get('open_interest')}\n"
                  f"Reported side: {candidate.get('reported_side','unknown')}; verified buy: unknown\n"
                  f"Unknowns: {', '.join(candidate['enhancement_unknowns'])}\n"
                  'Targets/stops below are heuristic plans, not observed outcomes or permission to trade.')
    sizing = '\n'.join(f'{k}: {v}' for k,v in rec.get('sizing_rules',{}).items())
    return {
        'open': {'content': f"OWLFRED OPEN\n{rec['ticker']} {rec['strike']} {rec['call_put']} {rec['expiration']}\nEntry target: {rec['entry_price']}\nThesis: {thesis}"},
        'risk': {'content': f"OWLFRED RISK MANAGEMENT\n{rec['ticker']}\nTP1: {rec['tp1_price']} | TP2: {rec['tp2_price']}\nStop: {rec['stop_loss_price']}\n{sizing}\nResearch alert; publication is not trade execution authorization."},
    }
