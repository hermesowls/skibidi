"""TEST fixtures only; no network or production database."""
import importlib
import json
import ast
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


def test_existing_server_readonly_watchlist_route(tmp_path):
    test_seed_retains_old_unknown_prints_and_is_idempotent(tmp_path)
    source = (Path(__file__).resolve().parents[1]/'hermes_cli/web_server.py').read_text()
    tree = ast.parse(source)
    functions = [n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'api_research_watchlist']
    assert functions, 'Existing server must expose the read-only route'
    home = tmp_path/'home'
    target = home/'research/notable-flow-v1/REAL_DATA_RESEARCH/watchlist.sqlite'
    target.parent.mkdir(parents=True)
    (home/'research/config.json').write_text(json.dumps({'version':1, 'root':str(home/'research/notable-flow-v1')}))
    target.write_bytes((tmp_path/'watchlist.sqlite').read_bytes())
    app = FastAPI()
    scope = dict(app=app, get_hermes_home=lambda:home, HTTPException=HTTPException)
    exec(compile(ast.Module(body=functions,type_ignores=[]), '<actual-server-route>', 'exec'),scope)
    response = TestClient(app).get('/api/analyst-trader/research-watchlist')
    assert response.status_code == 200
    assert response.json()['observation_count'] == 2
    assert response.json()['execution_authorized'] is False
    assert not (home/'data').exists()

from pathlib import Path


def test_seed_retains_old_unknown_prints_and_is_idempotent(tmp_path):
    from plugins.analyst_trader import research_watchlist as w
    sample = tmp_path / 'sample.json'
    rows = [dict(provider_event_id=x, received_at='2026-09-24T16:35:00+00:00',
        evidence={'contract_symbol':'TEST260925C00100000'},
        raw={'executed_at':'2026-09-24T13:30:00Z','is_agg':None}, baseline_status='INCOMPLETE') for x in ['TEST-a','TEST-b']]
    sample.write_text(json.dumps({'records':rows}))
    db = tmp_path / 'watchlist.sqlite'
    w.seed(db, sample)
    w.seed(db, sample)
    result = w.read_watchlist(db)
    assert result['observation_count'] == 2
    assert result['contract_count'] == 1
    assert result['observations'][0]['executed_at'] != result['observations'][0]['first_seen_at']
    assert result['observations'][0]['record']['raw']['is_agg'] is None
    assert result['observations'][0]['record']['baseline_status'] == 'INCOMPLETE'
    assert result['snapshot_count'] == 0


def test_snapshot_excludes_before_first_seen_and_hashes_raw(tmp_path):
    from plugins.analyst_trader import research_watchlist as w
    test_seed_retains_old_unknown_prints_and_is_idempotent(tmp_path)
    db = tmp_path / 'watchlist.sqlite'
    symbol = 'TEST260925C00100000'
    body = json.dumps({'data': [dict(option_symbol=symbol, start_time=t, close='1') for t in
        ['2026-09-24T16:34:00Z','2026-09-24T16:36:00Z']]}).encode()
    w.store_snapshot(db, symbol, body, received_at='2026-09-24T16:38:00Z')
    result = w.read_watchlist(db)
    s = result['snapshots'][0]
    assert s['raw_hash'] == w.digest(body)
    assert s['post_first_seen_bars'] == 1
    assert s['pre_first_seen_bars'] == 1
    assert s['as_of'] == '2026-09-24T16:36:00Z'
    assert s['age_seconds_at_receipt'] == 120
    assert result['pending_contracts'] == []
    with w.connection(db) as c:
        assert c.execute('SELECT raw_body FROM snapshots').fetchone()[0] == body


def test_missing_contract_echo_is_explicit_unknown(tmp_path):
    from plugins.analyst_trader import research_watchlist as w
    test_seed_retains_old_unknown_prints_and_is_idempotent(tmp_path)
    r = w.store_snapshot(tmp_path/'watchlist.sqlite', 'TEST260925C00100000',
        b'{"data":[{"start_time":"2026-09-24T16:36:00Z"}]}', received_at='2026-09-24T16:38:00Z')
    assert r['snapshots'][0]['contract_identity'] == 'REQUEST_PATH_ONLY_NO_RESPONSE_ECHO'

