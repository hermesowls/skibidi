"""One documented historical intraday GET; isolated by parent deadline."""
import base64
import json
import math
import re
import sys
from datetime import datetime, date, timezone

BODY_CAP = 1048576

def validate_request(path, params, timeout):
    match = re.fullmatch(r'/api/option-contract/([A-Z][A-Z0-9]{0,5}[0-9]{6}[CP][0-9]{8})/intraday', path)
    if not match or not isinstance(params, dict) or set(params) != {'date'}:
        raise ValueError('Invalid intraday route/params')
    datetime.strptime(match[1][-15:-9], '%y%m%d')
    day = params['date']
    if not isinstance(day, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day) or date.fromisoformat(day) > datetime.now(timezone.utc).date():
        raise ValueError('Invalid intraday date')
    if type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0 < timeout <= 30:
        raise ValueError('Invalid deadline')

def fetch(token, path, params, timeout, *, client=None):
    return bounded_fetch(token, path, params, timeout, validator=validate_request, client=client)

def bounded_fetch(token, path, params, timeout, *, validator, client=None):
    import httpx
    validator(path, params, timeout)
    if not isinstance(token,str) or not token or len(token)>2048 or '\r' in token or '\n' in token:
        raise ValueError('Explicit credential required')
    synthetic = client is not None
    known_rejection = None
    def request(c):
        nonlocal known_rejection
        with c.stream('GET', 'https://api.unusualwhales.com'+path, params=params,
                headers={'Authorization':'Bearer '+token,'Accept-Encoding':'identity'},
                timeout=httpx.Timeout(timeout,connect=min(timeout,5)),follow_redirects=False) as r:
            # HTTP rejection metadata must not depend on consuming its body.
            # In particular, never wait on a 429 body before reporting the stop.
            retry_after = r.headers.get('retry-after')
            if not isinstance(retry_after, str) or not re.fullmatch(
                    r'(?:[0-9]{1,10}|(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), [0-9]{2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) [0-9]{4} [0-9]{2}:[0-9]{2}:[0-9]{2} GMT)', retry_after):
                retry_after = None
            if r.status_code != 200:
                known_rejection = dict(status=r.status_code, raw_body=b'',
                    body_status='NOT_READ_HTTP_ERROR',
                    received_at=datetime.now(timezone.utc).isoformat(),
                    retry_after=retry_after, source='TEST_FIXTURE' if synthetic else 'UW_LIVE',
                    evidence_cohort='TEST' if synthetic else 'REAL_DATA_RESEARCH')
                return known_rejection
            if r.headers.get('content-encoding','identity').lower() != 'identity':
                raise ValueError('Compressed response forbidden')
            length=r.headers.get('content-length')
            if length is not None and (not length.isdecimal() or int(length)>BODY_CAP):
                raise ValueError('Body exceeds bounds')
            raw=bytearray()
            for chunk in r.iter_raw(chunk_size=16384):
                if len(raw)+len(chunk)>BODY_CAP: raise ValueError('Body exceeds bounds')
                raw.extend(chunk)
            return dict(status=r.status_code,raw_body=bytes(raw),received_at=datetime.now(timezone.utc).isoformat(),
                retry_after=retry_after,source='TEST_FIXTURE' if synthetic else 'UW_LIVE',
                evidence_cohort='TEST' if synthetic else 'REAL_DATA_RESEARCH')
    try:
        if synthetic: return request(client)
        with httpx.Client(trust_env=False,transport=httpx.HTTPTransport(retries=0,trust_env=False)) as c:
            return request(c)
    except Exception:
        # A response/client close failure must not erase visible rejection headers.
        if known_rejection is not None:
            return known_rejection
        raise

def main():
    try:
        req=json.loads(sys.stdin.buffer.read(4097))
        result=fetch(req['token'],req['path'],req['params'],req['timeout'])
        result['raw_body']=base64.b64encode(result['raw_body']).decode()
        sys.stdout.write(json.dumps(result,allow_nan=False))
        return 0
    except Exception:
        sys.stderr.write('Bounded intraday worker failed; no retry\n')
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
