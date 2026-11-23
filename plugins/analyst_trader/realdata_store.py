"""Explicit paths only. Source is read-only; destination is research-only."""
from contextlib import contextmanager
from pathlib import Path
import os
import sqlite3
from .learning_store import get_version
from .research_profiles import select


class ReadOnlyProfiles:
    def __init__(self, path):
        self.path = Path(path).resolve(strict=True)
        wal = self.path.with_name(self.path.name + '-wal')
        if wal.exists() and wal.stat().st_size:
            raise ValueError('Provide a stable standalone profile DB snapshot, not active WAL')

    def _get_connection(self):
        # Immutable prevents SQLite sidecar/shm writes. Caller supplies a stable
        # standalone snapshot, not a concurrently changing production database.
        c = sqlite3.connect(self.path.as_uri() + '?mode=ro&immutable=1', uri=True)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA query_only=ON')
        return c

    def get_learning_version(self, version_id):
        return get_version(self, version_id)


class ResearchStore:
    """No AnalystDatabase constructor, production schema, migrations or defaults.

    Paths must live in an operator-controlled directory (not attacker-writable).
    Existing destinations must have our marker and no unrelated schema objects.
    """
    def __init__(self, destination, profile_source, version_id):
        self.source = ReadOnlyProfiles(profile_source)
        self.profile = select(self.source, version_id)
        self.path = Path(destination).absolute()
        if (self.path.resolve() == self.source.path or
                self.path.exists() and os.path.samefile(self.path, self.source.path)):
            raise ValueError('Research destination must be separate from profile source')
        if self.path.is_symlink():
            raise ValueError('Research destination must be separate non-symlink file')
        if not self.path.exists():
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(fd)
            with sqlite3.connect(self.path) as c:
                c.execute('CREATE TABLE research_store_identity (kind TEXT NOT NULL)')
                c.execute("INSERT INTO research_store_identity VALUES ('bounded-research-v1')")
        self._validate()
        self.identity = (self.path.stat().st_dev, self.path.stat().st_ino)

    def _validate(self):
        with sqlite3.connect(self.path.resolve().as_uri()+'?mode=ro', uri=True) as c:
            tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
            if not tables <= {'research_store_identity', 'realdata_research_records'} or 'research_store_identity' not in tables:
                raise ValueError('Destination is not a dedicated research DB')
            if c.execute('SELECT kind FROM research_store_identity').fetchall() != [('bounded-research-v1',)]:
                raise ValueError('Invalid dedicated research DB identity')
            triggers = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
            if not triggers <= {'realdata_research_no_update', 'realdata_research_no_delete'}:
                raise ValueError('Unexpected research DB trigger')

    def get_learning_version(self, version_id):
        if version_id != self.profile['version_id']:
            raise ValueError('Only exact selected profile permitted')
        return self.profile

    @contextmanager
    def _get_connection(self):
        stat = self.path.stat()
        if self.path.is_symlink() or (stat.st_dev, stat.st_ino) != self.identity or os.path.samefile(self.path, self.source.path):
            raise ValueError('Research destination changed or is not separate')
        self._validate()
        c = sqlite3.connect(self.path, timeout=1)
        try:
            with c:
                yield c
        finally:
            c.close()
