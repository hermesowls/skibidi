"""Exact configured Elite CSV route; private personal-license quotes only."""
import base64
import json
import math
import sys
from datetime import datetime, timezone
from urllib.parse import urlsplit


def validate(url, timeout):
    try:
        p=urlsplit(url)
        valid=(p.scheme=='https' and p.netloc=='elite.finviz.com' and p.path=='/export/screener'
               and not p.fragment and bool(p.query) and len(url)<=4096
               and not any(ord(c)<33 for c in url))
    except Exception:
        valid=False
    if not valid or type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0<timeout<=30:
        raise ValueError('Invalid bounded Elite configuration')


def fetch(url, timeout):
    import httpx
    validate(url,timeout)
    rejection=None
    try:
        with httpx.Client(trust_env=False,transport=httpx.HTTPTransport(retries=0,trust_env=False)) as client:
            with client.stream('GET',url,headers={'Accept-Encoding':'identity'},follow_redirects=False,
                               timeout=httpx.Timeout(timeout,connect=min(timeout,5))) as response:
                result=dict(status=response.status_code,received_at=datetime.now(timezone.utc).isoformat(),raw_body='',retry_after=None)
                # Capture status before headers/body; cleanup must not erase it.
                if response.status_code!=200: rejection=result
                import re
                retry=getattr(response,'headers',{}).get('retry-after')
                if isinstance(retry,str) and re.fullmatch(r'[0-9]{1,10}',retry):
                    result['retry_after']=retry
                elif isinstance(retry,str) and len(retry)<=64:
                    from email.utils import parsedate_to_datetime,format_datetime
                    try:
                        parsed=parsedate_to_datetime(retry)
                        if parsed.tzinfo is not None:
                            result['retry_after']=format_datetime(parsed.astimezone(timezone.utc),usegmt=True)
                    except (ValueError,TypeError,OverflowError):
                        pass
                if response.status_code!=200:
                    rejection=result
                    return result
                if response.headers.get('content-type','').split(';')[0].strip().lower()!='text/csv':
                    raise ValueError('CSV content type required')
                if response.headers.get('content-encoding','identity').lower()!='identity':
                    raise ValueError('Encoding unsupported')
                body=bytearray()
                for chunk in response.iter_raw(chunk_size=16384):
                    if len(body)+len(chunk)>1048576: raise ValueError('CSV bound exceeded')
                    body.extend(chunk)
                result.update(raw_body=base64.b64encode(body).decode(),received_at=datetime.now(timezone.utc).isoformat())
                return result
    except Exception:
        if rejection is not None: return rejection
        raise ValueError('Elite request failed; no retry') from None


def main():
    try:
        request=json.loads(sys.stdin.buffer.read(8193))
        if set(request)!={'url','timeout'}: raise ValueError('Closed request required')
        sys.stdout.write(json.dumps(fetch(**request),allow_nan=False))
        return 0
    except Exception:
        sys.stderr.write('Elite request failed; no retry\n')
        return 1

if __name__=='__main__':
    raise SystemExit(main())
