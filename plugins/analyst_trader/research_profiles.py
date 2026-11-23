"""Named immutable TEST research screens, never publication/execution permission.

Selection is an explicit version passed by a caller, not mutable process state.
Persistence reuses learning_versions and its immutable SQLite triggers.
"""
from datetime import datetime, timezone
from uuid import uuid4
from .learning_store import digest
from .kian_research import validate_policy

EDITABLE = frozenset(('min_premium','min_size','dte_min','dte_max','otm_required',
    'max_otm_fraction','complex_handling','ask_handling'))


def default_policy():
    return dict(schema_version=2, mode='paper_test', origin='user_chosen_research',
        approval='TEST_OFFLINE_ONLY', min_premium=50000, min_size=500,
        dte_min=1, dte_max=14, otm_required=True, max_otm_fraction=None,
        max_age_seconds=120, calendar_zone='America/New_York',
        complex_handling='reject', ask_handling='report_only',
        premium_definition='single_print_usd', size_definition='single_print_contracts',
        volume_definition='aggregate_contract_session')


def select(db, version_id):
    """Resolve exact immutable version; this does not start a scan."""
    if not isinstance(version_id, str) or not version_id.strip() or len(version_id) > 200:
        raise ValueError('Invalid profile version')
    version = db.get_learning_version(version_id)
    if not version['profile'].get('research_profile_name'):
        raise ValueError('Not a named research profile')
    validate_policy(version, version['profile']['kian_policy_hash'])
    return version


def list_profiles(db):
    with db._get_connection() as conn:
        ids = [row[0] for row in conn.execute('SELECT version_id FROM learning_versions ORDER BY rowid DESC')]
    versions = [db.get_learning_version(version_id) for version_id in ids]
    return [v for v in versions if v['profile'].get('research_profile_name')]


def preview(db_path, payload):
    """Read exact persisted policy; evaluate one declared TEST observation in memory.

    Not historical replay: the hypothetical observation clock is independent of
    when the user saved the policy. No raw rows/decisions/cohorts are persisted.
    """
    import sqlite3
    from pathlib import Path
    from .learning_store import get_version, canonical
    from .kian_research import screen_research
    from .learning_evidence import aware_time

    if not isinstance(payload, dict) or set(payload) != {'version_id', 'evidence'}:
        raise ValueError('Only exact version and declared TEST evidence accepted')
    e = payload['evidence']
    allowed = {'ticker','strike','call_put','expiration','contract_symbol','observed_at',
        'spot_observed_at','spot_price','premium_usd','size','volume','open_interest',
        'complex_trade','reported_side','premium_definition','size_definition','volume_definition'}
    if not isinstance(e, dict) or e.keys() - allowed:
        raise ValueError('Invalid TEST evidence fields')
    # Reject nesting, oversized strings and non-finite JSON before canonical hashing.
    if any(v is not None and type(v) not in (str, int, float, bool) for v in e.values()):
        raise ValueError('TEST evidence must contain scalar observations')
    if len(canonical(e)) > 4096:
        raise ValueError('TEST evidence too large')
    at = aware_time(e.get('observed_at')).isoformat()

    class ReadOnlyVersions:
        def _get_connection(self):
            conn = sqlite3.connect(Path(db_path).resolve().as_uri() + '?mode=ro', uri=True)
            conn.row_factory = sqlite3.Row
            return conn
        def get_learning_version(self, version_id):
            return get_version(self, version_id)

    profile = select(ReadOnlyVersions(), payload['version_id'])
    raw = dict(kind='declared_TEST_evidence', evidence=e)
    source_id = 'TEST-preview:' + digest(raw)
    e = dict(e, source='declared_TEST_evidence', source_id=source_id, evidence_id=source_id)
    source = dict(e)
    decision = dict(profile_version=profile['version_id'], decision_at=at,
        source_id=source_id, source_snapshot_hash=digest(source), raw_source_hash=digest(raw),
        inputs={'spot_price': e.get('spot_price')})
    decision_hash = digest(decision)
    decision['decision_id'] = 'TEST-preview:' + decision_hash
    result = screen_research(profile, decision,
        dict(policy_hash=profile['profile']['kian_policy_hash'], evidence=e), source)
    return dict(result, preview_only=True, lineage_kind='declared_TEST_not_operational',
        decision_hash=decision_hash, max_otm_fraction=profile['profile']['kian_research']['max_otm_fraction'],
        profile_name=profile['profile']['research_profile_name'],
        filter_provenance=profile['profile'].get('filter_provenance'),
        notice='Hypothetical TEST evidence only; not a live scan, trade signal or execution permission')


def create(db, name, changes=None, *, base_version=None):
    """Create, clone or edit into a new version, preserving all prior references."""
    if not isinstance(name, str) or not name.strip() or len(name) > 100:
        raise ValueError('Profile name must be 1..100 characters')
    if changes is None:
        changes = {}
    if not isinstance(changes, dict) or changes.keys() - EDITABLE:
        raise ValueError('Unsupported research filter; configuration is not authority')
    p = dict(select(db, base_version)['profile']['kian_research']) if base_version else default_policy()
    p.update(changes)
    at = datetime.now(timezone.utc).isoformat()
    snapshot = dict(version_id='research:'+uuid4().hex, schema_version=1,
        code_identity='operational-stage2-research-v2', config_identity=digest(p),
        training_cutoff=at, created_at=at, source_mode='paper_test', evidence_ids=[],
        uncertainty=['TEST research configuration only; no demonstrated edge or execution permission'],
        classification='stated_policy', profile=dict(rules={}, kian_research=p,
            kian_policy_hash=digest(p), research_profile_name=name.strip(),
            base_version=base_version, filter_provenance={
                'premium_size_volume':'recovered local single-print screen',
                'dte_otm':'user approved TEST default; explicit user edits versioned'}))
    validate_policy(snapshot, digest(p))
    version_id = db.save_learning_version(snapshot)
    return select(db, version_id)
