"""Parent watchdog for the fixed single-request worker; no implicit credentials.

The request budget includes launch and communication. OS process creation itself
cannot be interrupted portably by Python; after it returns, remaining time is
used. Timeout kills the isolated worker, with at most one extra second for reap.
This is not a hard real-time scheduling guarantee. No synchronous elapsed check
is represented as cancellation of an arbitrary in-process callable.
"""
import json
import math
from pathlib import Path
import subprocess
import sys
import time
from .realdata_http_worker import validate_params


class BoundedUWTransport:
    def __init__(self, token, *, process_factory=None, before_send=None, after_response=None):
        if not isinstance(token, str) or not token or len(token) > 2048 or '\r' in token or '\n' in token:
            raise ValueError('Explicit credential required')
        self._before_send = before_send
        self._after_response = after_response
        self._token = token
        self._process_factory = process_factory or subprocess.Popen
        self._synthetic = process_factory is not None

    def __call__(self, path, *, params, timeout):
        validate_params(params)
        if (path != '/api/option-trades' or
                type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 30):
            raise ValueError('Invalid bounded request')
        payload = json.dumps(dict(token=self._token, limit=int(params['limit']), timeout=timeout, params=params)).encode()
        return self._execute(payload, timeout, 'realdata_http_worker.py')

    def _execute(self, payload, timeout, worker):
        if self._before_send is not None:
            self._before_send()
        started = time.monotonic()
        child = self._process_factory([sys.executable, '-I', '-B',
            str(Path(__file__).with_name(worker))],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            env={}, close_fds=True)
        try:
            out, _ = child.communicate(payload, timeout=max(.001, timeout-(time.monotonic()-started)))
            if time.monotonic()-started > timeout:
                raise subprocess.TimeoutExpired('UW worker', timeout)
        except subprocess.TimeoutExpired:
            child.kill()
            try:
                child.wait(timeout=1)
            except subprocess.TimeoutExpired:
                raise ValueError('Research deadline exceeded; worker reap unconfirmed') from None
            raise ValueError('Research request deadline exceeded; worker killed; no retry') from None
        except BaseException:
            child.kill()
            try:
                child.wait(timeout=1)
            except subprocess.TimeoutExpired:
                raise ValueError('Worker cleanup unconfirmed; no retry') from None
            raise
        finally:
            for stream in ('stdin', 'stdout'):
                pipe = getattr(child, stream, None)
                if pipe is not None:
                    pipe.close()
        if child.returncode != 0:
            raise ValueError('UW worker failed; no retry')
        # Worker raw-body limit bounds output; JSON escaping can expand sixfold.
        if len(out) > 6 * 1048576 + 1024:
            raise ValueError('Worker output exceeds bounds')
        result = json.loads(out)
        if self._after_response is not None:
            self._after_response(result)
        if self._synthetic:
            result['source'] = 'TEST_FIXTURE'
        return result


class BoundedCBOEHistoryTransport(BoundedUWTransport):
    """Public CBOE history; reuse only the process watchdog, never UW routes/auth.

    A successful capture is NOT qualified OHLCV and cannot supply indicators
    until the provider schema, regular-session and adjustment policy are verified.
    """
    def __init__(self, *, process_factory=None, before_send=None, after_response=None):
        self._before_send = before_send
        self._after_response = after_response
        self._process_factory = process_factory or subprocess.Popen
        self._synthetic = process_factory is not None

    def __call__(self, ticker, *, timeout):
        import base64
        from .realdata_cboe_worker import validate_request
        validate_request(ticker, timeout)
        result = self._execute(json.dumps(dict(ticker=ticker, timeout=timeout)).encode(),
                               timeout, 'realdata_cboe_worker.py')
        result['raw_body'] = base64.b64decode(result['raw_body'], validate=True)
        if len(result['raw_body']) > 1048576:
            raise ValueError('CBOE body exceeds bounds')
        result['evidence_cohort'] = 'TEST' if self._synthetic else 'REAL_DATA_RESEARCH'
        return result


class BoundedUWDailyTransport(BoundedUWTransport):
    """Narrow daily adapter; unchanged shared process watchdog."""
    def __call__(self, path, *, params, timeout):
        import base64
        from .realdata_daily_worker import validate_request
        validate_request(path, params, timeout)
        result = self._execute(json.dumps(dict(token=self._token,path=path,params=params,timeout=timeout)).encode(),
            timeout, 'realdata_daily_worker.py')
        result['raw_body'] = base64.b64decode(result['raw_body'], validate=True)
        if len(result['raw_body']) > 1048576:
            raise ValueError('Daily body exceeds bounds')
        result['evidence_cohort'] = 'TEST' if self._synthetic else 'REAL_DATA_RESEARCH'
        return result


class BoundedUWIntradayTransport(BoundedUWTransport):
    """Exact intraday-only route; shared kill/reap watchdog, zero retries."""
    @property
    def identity(self):
        return 'TEST_TRANSPORT' if self._synthetic else 'UW_INTRADAY_BOUNDED_V1'

    def __call__(self, path, *, params, timeout):
        import base64
        from .realdata_intraday_worker import validate_request
        validate_request(path, params, timeout)
        result = self._execute(json.dumps(dict(token=self._token,path=path,params=params,timeout=timeout)).encode(),
            timeout, 'realdata_intraday_worker.py')
        result['raw_body'] = base64.b64decode(result['raw_body'], validate=True)
        result['evidence_cohort'] = 'TEST' if self._synthetic else 'REAL_DATA_RESEARCH'
        return result
