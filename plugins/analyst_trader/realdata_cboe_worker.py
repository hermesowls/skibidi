"""One public legacy CBOE history GET. No redirects, retries or TA admission.

This route is inherited from finviz_fetcher, not a Finviz historical source.
Schema/session/adjustment qualification is deliberately separate from transport.
"""
import base64
import json
import math
import re
import sys
from datetime import datetime, timezone

BODY_CAP = 1048576


def validate_request(ticker, timeout):
    if not isinstance(ticker, str) or not re.fullmatch(r'[A-Z][A-Z0-9]{0,5}', ticker):
        raise ValueError('Literal ticker required')
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 30:
        raise ValueError('Invalid deadline')


def fetch(ticker, timeout):
    import httpx
    validate_request(ticker, timeout)
    url = 'https://cdn-api.cboe.com/api/global/delayed_quotes/charts/historical/' + ticker + '.json'
    rejection = None
    try:
        with httpx.Client(trust_env=False, transport=httpx.HTTPTransport(retries=0, trust_env=False)) as client:
            with client.stream('GET', url, headers={'Accept-Encoding': 'identity'},
                               timeout=httpx.Timeout(timeout, connect=min(timeout, 5)), follow_redirects=False) as response:
                result = dict(status=response.status_code, provider='CBOE', source='CBOE_HISTORY',
                              evidence_cohort='REAL_DATA_RESEARCH', raw_body=b'',
                              received_at=datetime.now(timezone.utc).isoformat(),
                              qualification='UNVERIFIED_SCHEMA_SESSION_ADJUSTMENT',
                              retry_after=None, provider_observed_at=None)
                retry = response.headers.get('retry-after')
                if isinstance(retry, str) and re.fullmatch(r'[0-9]{1,10}', retry):
                    result['retry_after'] = retry
                elif isinstance(retry,str) and len(retry)<=64:
                    from email.utils import parsedate_to_datetime, format_datetime
                    try:
                        parsed=parsedate_to_datetime(retry)
                        if parsed.tzinfo is not None:
                            result['retry_after']=format_datetime(parsed.astimezone(timezone.utc),usegmt=True)
                    except (ValueError,TypeError,OverflowError):
                        pass
                if response.status_code != 200:
                    rejection = dict(result, body_status='NOT_READ_HTTP_ERROR')
                    return rejection
                if response.headers.get('content-encoding', 'identity').lower() != 'identity':
                    raise ValueError('Compressed response forbidden')
                length = response.headers.get('content-length')
                if length is not None and (not length.isdecimal() or int(length) > BODY_CAP):
                    raise ValueError('Body exceeds bounds')
                raw = bytearray()
                for chunk in response.iter_raw(chunk_size=16384):
                    if len(raw) + len(chunk) > BODY_CAP:
                        raise ValueError('Body exceeds bounds')
                    raw.extend(chunk)
                result.update(raw_body=bytes(raw), body_status='RAW_UNQUALIFIED',
                              received_at=datetime.now(timezone.utc).isoformat())
                return result
    except Exception:
        if rejection is not None:
            return rejection
        raise


def main():
    try:
        request = json.loads(sys.stdin.buffer.read(4097))
        if set(request) != {'ticker', 'timeout'}:
            raise ValueError('Closed request required')
        result = fetch(request['ticker'], request['timeout'])
        result['raw_body'] = base64.b64encode(result['raw_body']).decode()
        sys.stdout.write(json.dumps(result, allow_nan=False))
        return 0
    except Exception:
        sys.stderr.write('Bounded CBOE worker failed; no retry\n')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
