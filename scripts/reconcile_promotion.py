"""Scoped candidate publication. No transport, git, service or package operations."""
import ast
import hashlib
import os
from pathlib import Path
import tempfile


def no_links(path):
    path = Path(path).absolute()
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError('Symlink in promotion path: ' + str(part))
    return path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def allowed_path(path):
    path = no_links(path)
    if any(p in ('.git', 'web_dist') or p == '.env' or p.startswith('.env.') for p in path.parts) or path.suffix in ('.db', '.sqlite', '.sqlite3'):
        raise ValueError('Protected candidate path')
    return path


def validate_syntax(stage, items):
    """Syntax only, not test-suite/release qualification; never execute candidates."""
    for item in items:
        candidate = stage / item['kind'] / item['rel_path']
        if candidate.suffix == '.py':
            ast.parse(candidate.read_bytes(), filename=str(candidate))
        else:
            raise ValueError('Non-Python promotion requires an explicit offline validator')
    return {'all_passed': True, 'scope': 'python_syntax_only', 'files': len(items)}


def checked_items(pipeline, candidates):
    source = no_links(pipeline.source_dir)
    roots = {'repo': no_links(pipeline.checkout_root)}
    roots['scripts'] = no_links(pipeline.runtime_root)
    seen = set()
    items = []
    for item in candidates:
        kind = item['kind']
        rel = Path(item['rel_path'])
        if kind not in roots or rel.is_absolute() or '..' in rel.parts:
            raise ValueError('Invalid candidate scope')
        target_rel = Path(*rel.parts[1:]) if kind == 'scripts' and rel.parts[0] == 'scripts' else rel
        dest = allowed_path(item['dest_path'])
        src = allowed_path(item['src_path'])
        if dest != roots[kind] / target_rel or not src.is_relative_to(source):
            raise ValueError('Candidate escapes declared scope')
        if dest in seen:
            raise ValueError('Duplicate destination')
        seen.add(dest)
        if any(p in ('.git', '.env', 'web_dist') for p in target_rel.parts) or dest.suffix in ('.db', '.sqlite', '.sqlite3'):
            raise ValueError('Protected destination')
        data = src.read_bytes()
        before = dest.read_bytes() if dest.exists() else None
        if sha(data) != item['src_hash'] or (sha(before) if before is not None else '') != item['dest_hash']:
            raise ValueError('Candidate changed since discovery')
        changed = data != before
        if changed != (item['status'] != 'UNCHANGED'):
            raise ValueError('Incorrect candidate status')
        if changed:
            items.append((item, src, dest, data, before))
    return items


def replace_bytes(path, data):
    """Atomic replacement of one regular file, retaining its permission bits."""
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    fd, name = tempfile.mkstemp(prefix='.reconcile-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def promote(pipeline, candidates, *, approved_files=(), validator=None):
    items = checked_items(pipeline, candidates)
    for item, *_ in items:
        print(f"PROPOSE {item['kind']}:{item['rel_path']} {item['src_hash']}")
    if pipeline.dry_run:
        return len(items)
    requested = {i['kind'] + ':' + i['rel_path'] for i, *_ in items}
    if requested != set(approved_files):
        raise PermissionError('Exact per-file approval required before promotion')
    if not items:
        return 0
    # The validator receives only the frozen candidate, not the destination.
    with tempfile.TemporaryDirectory(prefix='reconcile-candidate-') as tmp:
        stage = Path(tmp)
        for item, _, _, data, _ in items:
            p = stage / item['kind'] / item['rel_path']
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        result = (validator or validate_syntax)(stage, [dict(i) for i, *_ in items])
        if not isinstance(result, dict) or result.get('all_passed') is not True:
            raise ValueError('Candidate validation failed')
        for item, _, _, data, _ in items:
            if (stage / item['kind'] / item['rel_path']).read_bytes() != data:
                raise ValueError('Validator mutated candidate')
    # Recheck all source/destination bytes after validation, before first mutation.
    checked_items(pipeline, candidates)
    applied = []
    directories = []
    try:
        for item, _, dest, data, before in items:
            no_links(dest)
            if (dest.read_bytes() if dest.exists() else None) != before:
                raise ValueError('Destination changed during promotion')
            missing = []
            parent = dest.parent
            while not parent.exists():
                missing.append(parent)
                parent = parent.parent
            for parent in reversed(missing):
                parent.mkdir()
                directories.append(parent)
            applied.append((dest, data, before))
            replace_bytes(dest, data)
            if dest.read_bytes() != data:
                raise OSError('Post-promotion hash mismatch')
    except BaseException:
        conflicts = []
        for dest, data, before in reversed(applied):
            no_links(dest)
            current = dest.read_bytes() if dest.exists() else None
            if current == before:
                continue
            if current != data:
                conflicts.append(str(dest))
                continue  # never overwrite an unexplained competing edit
            if before is None:
                dest.unlink()
            else:
                replace_bytes(dest, before)
        for parent in reversed(directories):
            try:
                parent.rmdir()
            except OSError:
                pass  # preserve unrelated concurrent files
        if conflicts:
            raise RuntimeError('Rollback refused competing destination edits: ' + ', '.join(conflicts))
        raise
    pipeline.last_validation = result
    return len(items)
