"""Isolated single-request worker. Never imported for credential discovery.

HTTPX inactivity timeouts are NOT a total deadline. The parent kills this worker
on the overall deadline, covering DNS, slow streams and blocked client code.
"""
import json
import math
import sys
import re
from decimal import Decimal
from datetime import datetime, timezone

BODY_CAP = 1048576
URL = 'https://api.unusualwhales.com/api/option-trades'


def validate_params(params):
    """Closed REST allowlist, shared by parent and isolated worker.

    Legacy unfiltered bounded calls remain supported; targeted calls require
    the complete economic filter set. No cursors, pagination or max OTM API.
    """
    base = {'limit', 'include_agg_trades'}
    filters = {'min_premium', 'min_size', 'volume_greater_oi', 'min_dte', 'max_dte'}
    if (not isinstance(params, dict) or set(params) not in
            (base, base | filters, base | filters | {'is_otm'}) or
            any(type(v) is not str or len(v) > 128 for v in params.values())):
        raise ValueError('Invalid bounded request params')
    def integer(key, minimum, maximum=None):
        value = params[key]
        if not re.fullmatch(r'[0-9]+', value) or int(value) < minimum or (maximum is not None and int(value) > maximum):
            raise ValueError('Invalid bounded request params')
    integer('limit', 1, 100)
    if params['include_agg_trades'] != 'false':
        raise ValueError('Invalid bounded request params')
    if 'min_premium' in params:
        if (not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?', params['min_premium']) or
                Decimal(params['min_premium']) <= 0 or params['volume_greater_oi'] != 'true' or
                ('is_otm' in params and params['is_otm'] != 'true')):
            raise ValueError('Invalid bounded request params')
        integer('min_size', 1, 2**63-1)
        integer('min_dte', 0)
        integer('max_dte', 0)
        if int(params['min_dte']) > int(params['max_dte']):
            raise ValueError('Invalid bounded request params')


def fetch(token, limit, timeout, *, client=None, params=None):
    import httpx
    if (type(limit) is not int or not 1 <= limit <= 100 or
            type(timeout) not in (int, float) or not math.isfinite(timeout) or
            not 0 < timeout <= 30 or not isinstance(token, str) or
            not token or len(token) > 2048 or '\n' in token or '\r' in token):
        raise ValueError('Invalid bounded request')
    params = {'limit':str(limit), 'include_agg_trades':'false'} if params is None else params
    validate_params(params)
    if int(params['limit']) != limit:
        raise ValueError('Invalid bounded request limit mismatch')
    synthetic = client is not None
    def request(c):
        with c.stream('GET', URL, params=params,
                headers={'Authorization': 'Bearer ' + token, 'Accept-Encoding': 'identity'},
                timeout=httpx.Timeout(timeout, connect=min(timeout, 5)),
                follow_redirects=False) as response:
            if response.status_code != 200:
                raise ValueError('UW request failed; no retry: ' + str(response.status_code))
            if response.headers.get('content-encoding', 'identity').lower() != 'identity':
                raise ValueError('Compressed response forbidden')
            length = response.headers.get('content-length')
            if length is not None and (not length.isdecimal() or int(length) > BODY_CAP):
                raise ValueError('Response body exceeds bounds')
            data = bytearray()
            for chunk in response.iter_raw(chunk_size=16384):
                if len(data) + len(chunk) > BODY_CAP:
                    raise ValueError('Response body exceeds bounds')
                data.extend(chunk)
            body = json.loads(data)
            return dict(status=200, source='TEST_FIXTURE' if synthetic else 'UW_LIVE',
                        received_at=datetime.now(timezone.utc).isoformat(), body=body)
    if synthetic:
        return request(client)
    # No proxies/netrc/env, redirects, cache, retry adapter or fallback.
    with httpx.Client(trust_env=False, transport=httpx.HTTPTransport(retries=0, trust_env=False)) as c:
        return request(c)


def main():
    try:
        request = json.loads(sys.stdin.buffer.read(4097))
        result = fetch(request['token'], request['limit'], request['timeout'], params=request.get('params'))
        sys.stdout.write(json.dumps(result, allow_nan=False, separators=(',', ':')))
        return 0
    except Exception:
        # Never reflect credentials, headers, URLs or response bodies to stderr.
        sys.stderr.write('Bounded UW worker failed; no retry\n')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
