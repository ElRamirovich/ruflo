#!/usr/bin/env python3
"""Explicit SQLite snapshots via the online backup API; no uploads or pruning."""
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import uuid
import zipfile

from backup import ROOT, MAX_FILE, SECRET_PATTERNS, git, read_regular, safe_name, verify


def source_path(root, name):
    safe_name(name)
    path = root / name
    for parent in [path, *path.parents]:
        if parent.is_symlink():
            raise ValueError('Symlink rejected')
    if not path.is_file() or path.suffix.lower() not in {'.db', '.sqlite', '.sqlite3'}:
        raise ValueError('Select an existing SQLite database file')
    if any(p in {'node_modules', 'backups'} for p in Path(name).parts):
        raise ValueError('Dependencies and old backups are not eligible')
    if path.stat().st_size > MAX_FILE:
        raise ValueError('Database too large')
    return path


def snapshot(root, output, databases):
    root, output = root.resolve(), output.resolve()
    if not databases or len(databases) != len(set(databases)):
        raise ValueError('Select unique database paths explicitly')
    if output == root or root in output.parents:
        raise ValueError('Snapshot output must be outside source')
    sources = [(name, source_path(root, name)) for name in databases]
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    result = output / ('sqlite-snapshot-' + uuid.uuid4().hex + '.zip')
    manifest = {'schema': 1, 'head': git(root, 'rev-parse', 'HEAD').decode().strip(),
                'history': False, 'kind': 'explicit-sqlite-snapshots', 'files': [],
                'consistency': 'each database is transactional; not a cross-database snapshot',
                'secret_detection': 'best-effort patterns; not a guarantee of absence'}
    with tempfile.TemporaryDirectory(prefix='.sqlite-staging-', dir=output) as temp:
        os.chmod(temp, 0o700)
        staged = Path(temp) / 'pending.zip'
        with zipfile.ZipFile(staged, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
            for index, (name, source) in enumerate(sources):
                before = source.stat(follow_symlinks=False)
                copy = Path(temp) / (str(index) + '.sqlite3')
                copy.touch(mode=0o600, exist_ok=False)
                started = time.monotonic()
                def progress(status, remaining, total):
                    if time.monotonic() - started > 30:
                        raise ValueError('SQLite snapshot timed out')
                # mode=ro forbids changing SQL data. SQLite may coordinate WAL
                # readers through existing/new shared-memory sidecars.
                with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True, timeout=2)) as reader:
                    reader.execute('PRAGMA query_only=ON')
                    reader.execute('PRAGMA trusted_schema=OFF')
                    with closing(sqlite3.connect(copy, timeout=2)) as writer:
                        reader.backup(writer, pages=256, progress=progress, sleep=0.05)
                        writer.execute('PRAGMA trusted_schema=OFF')
                        check = writer.execute('PRAGMA integrity_check').fetchall()
                        if check != [('ok',)]:
                            raise ValueError('SQLite integrity check failed')
                after = source.stat(follow_symlinks=False)
                if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
                    raise ValueError('Database replaced during snapshot')
                data, _ = read_regular(copy)
                if not data.startswith(b'SQLite format 3\0'):
                    raise ValueError('Not a SQLite database')
                if any(pattern.search(data) for _, pattern in SECRET_PATTERNS):
                    raise ValueError('Potential credential in database; no snapshot published')
                info = zipfile.ZipInfo('files/' + name)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100600 << 16
                archive.writestr(info, data)
                manifest['files'].append({'name': info.filename, 'size': len(data),
                                          'sha256': hashlib.sha256(data).hexdigest(),
                                          'sqlite_integrity': 'ok', 'method': 'sqlite-online-backup'})
            archive.writestr('manifest.json', json.dumps(manifest, indent=2))
        verify(staged)
        os.chmod(staged, 0o600)
        os.link(staged, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--database', action='append', required=True, help='Explicit path relative to repository root')
    args = parser.parse_args()
    try:
        print('Verified local SQLite snapshot:', snapshot(args.root, args.output, args.database))
    except (OSError, ValueError, sqlite3.Error) as exc:
        # Do not print SQLite errors: they may contain values or SQL fragments.
        raise SystemExit('SQLite snapshot failed: ' + type(exc).__name__ +
                         '; no snapshot declared valid. ' + (str(exc) if isinstance(exc, ValueError) else
                         'Check database access and format without printing its contents.'))


if __name__ == '__main__':
    main()
