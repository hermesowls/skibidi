"""Daily-only adapter: reuse bounded streaming and rejection handling."""
import base64
import json
import math
import re
import runpy
import sys
from pathlib import Path
from datetime import date, datetime, timezone

_shared = runpy.run_path(str(Path(__file__).with_name('realdata_intraday_worker.py')))

def validate_request(path, params, timeout):
    if not isinstance(path,str) or not re.fullmatch(r'/api/stock/[A-Z][A-Z0-9]{0,5}/ohlc/1d',path):
        raise ValueError('Daily-only route required')
    if not isinstance(params,dict) or set(params)!={'timeframe','end_date','limit'} or params['timeframe']!='1Y' or type(params['limit']) is not int or params['limit'] not in (500,2500):
        raise ValueError('Fixed one-year daily request required')
    day=params['end_date']
    if not isinstance(day,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',day) or date.fromisoformat(day)>datetime.now(timezone.utc).date():
        raise ValueError('Invalid daily date')
    if type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0<timeout<=30:
        raise ValueError('Invalid deadline')

def main():
    try:
        req=json.loads(sys.stdin.buffer.read(4097))
        result=_shared['bounded_fetch'](req['token'],req['path'],req['params'],req['timeout'],validator=validate_request)
        result['raw_body']=base64.b64encode(result['raw_body']).decode()
        sys.stdout.write(json.dumps(result,allow_nan=False))
        return 0
    except Exception:
        sys.stderr.write('Bounded daily worker failed; no retry\n')
        return 1

if __name__=='__main__': raise SystemExit(main())
