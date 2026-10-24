#!/usr/bin/env python3
"""Local, verified backup. Python standard library and Git only; no network calls."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import tempfile
import uuid
import zipfile

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {'.git', 'node_modules', '.cache', '__pycache__', '.turbo', 'coverage'}
REGENERABLE = {'dist', 'build'}
SECRET_NAMES = {'oauth-client.json', 'oauth-token.json', 'credentials.json',
                'credentials', 'id_rsa', 'id_ed25519', '.npmrc', '.netrc', '.pypirc'}
SUFFIXES = ('.pem', '.key', '.p12', '.pfx', '.db', '.sqlite', '.sqlite3',
            '-wal', '-shm', '-journal', '.pyc', '.log', '.tmp', '.tsbuildinfo',
            '.zip', '.tar', '.gz', '.7z', '.bundle')
SECRET = re.compile(rb'-----BEGIN (?:[A-Z ]*PRIVATE KEY)-----|'
                    rb'AIza[0-9A-Za-z_-]{35}|gh[pousr]_[A-Za-z0-9]{30,}|'
                    rb'github_pat_[A-Za-z0-9_]{40,}|AKIA[0-9A-Z]{16}|'
                    rb'ya29\.[A-Za-z0-9_-]{20,}|'
                    rb'"(?:refresh_token|client_secret)"\s*:\s*"[^"\s]{12,}"')
MAX_FILE = 256 * 1024 * 1024
MAX_TOTAL = 50 * 1024**3


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def paths(root, *args):
    return {os.fsdecode(p) for p in git(root, 'ls-files', *args, '-z').split(b'\0') if p}


def excluded(name, tracked=False):
    p = PurePosixPath(name)
    low = p.name.lower()
    if any(part in SKIP_DIRS for part in p.parts):
        return 'dependency/cache/git-directory'
    if not tracked and any(part in REGENERABLE for part in p.parts):
        return 'untracked-build-output'
    example = low.endswith(('.example', '.template'))
    if (low.startswith('.env') and not example) or low in SECRET_NAMES or low.endswith(SUFFIXES):
        return 'sensitive/database/temporary/archive-name'
    if name == 'independent-backup/inventory-report.json':
        return 'generated-inventory'
    return None


def safe_name(name):
    p = PurePosixPath(name)
    if (not name or '\\' in name or '\x00' in name or ':' in name or
            p.is_absolute() or any(x in {'.', '..', ''} for x in name.split('/')) or
            '.git' in p.parts):
        raise ValueError('Unsafe archive path')
    return name


def read_regular(path):
    # Reject links in all parent components, not just the final filename.
    for parent in [path, *path.parents]:
        if parent.is_symlink():
            raise ValueError('Symlink rejected')
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE:
            raise ValueError('Unsupported file type or file too large')
        data = stream.read(MAX_FILE + 1)
        after = os.fstat(stream.fileno())
        signature = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if len(data) > MAX_FILE or signature(before) != signature(after):
            raise ValueError('Source changed while being read')
        if signature(after) != signature(path.stat(follow_symlinks=False)):
            raise ValueError('Source replaced while being read')
        return data, before.st_mode & 0o777


def sensitive(data):
    return bool(SECRET.search(data)) or data.startswith(b'SQLite format 3\0')


def history(root, destination):
    if git(root, 'rev-parse', '--is-shallow-repository').strip() != b'false':
        raise ValueError('Shallow Git history; use a complete repository or --without-history')
    refs = git(root, 'show-ref', '--head')
    # Audit every reachable historical pathname and blob, not only current files.
    objects = git(root, 'rev-list', '--objects', '--all', 'HEAD').splitlines()
    with subprocess.Popen(['git', '-C', str(root), 'cat-file', '--batch'],
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE) as proc:
        try:
            for item in objects:
                sha, _, raw_name = item.partition(b' ')
                if raw_name and excluded(os.fsdecode(raw_name), tracked=True) == 'sensitive/database/temporary/archive-name':
                    # Archives and temporary files in history are valid code history;
                    # credential names, env and private key containers are not.
                    low = PurePosixPath(os.fsdecode(raw_name)).name.lower()
                    if (low.startswith('.env') and not low.endswith(('.example', '.template'))) or low in SECRET_NAMES or low.endswith(('.pem', '.key', '.p12', '.pfx')):
                        raise ValueError('Sensitive filename in Git history; review history or use --without-history')
                proc.stdin.write(sha + b'\n')
                proc.stdin.flush()
                header = proc.stdout.readline().split()
                if len(header) != 3:
                    raise ValueError('Cannot audit Git object')
                size = int(header[2])
                if size > MAX_FILE:
                    raise ValueError('Git object too large for audit')
                data = proc.stdout.read(size)
                if len(data) != size or proc.stdout.read(1) != b'\n':
                    raise ValueError('Incomplete Git object')
                if sensitive(data):
                    raise ValueError('Potential secret/database in Git history; review or use --without-history')
        finally:
            proc.stdin.close()
            proc.terminate()
    git(root, 'bundle', 'create', str(destination), '--all', 'HEAD')
    git(root, 'bundle', 'verify', str(destination))
    if refs != git(root, 'show-ref', '--head'):
        raise ValueError('Git refs changed during backup')


def verify_open(archive):
    infos = archive.infolist()
    if len(infos) > 200000:
        raise ValueError('Too many archive entries')
    names = [safe_name(x.filename) for x in infos]
    if len(names) != len(set(names)) or sum(x.file_size for x in infos) > MAX_TOTAL:
        raise ValueError('Duplicate entries or archive too large')
    for info in infos:
        kind = stat.S_IFMT(info.external_attr >> 16)
        if info.is_dir() or kind not in (0, stat.S_IFREG) or info.file_size > MAX_FILE:
            raise ValueError('Unsupported archive entry')
    manifest = json.loads(archive.read('manifest.json'))
    if manifest.get('schema') != 1 or not isinstance(manifest.get('files'), list):
        raise ValueError('Unsupported manifest')
    if type(manifest.get('history')) is not bool or not re.fullmatch('[0-9a-f]{40,64}', manifest.get('head', '')):
        raise ValueError('Invalid history/source metadata')
    expected = {'manifest.json'}
    for entry in manifest['files']:
        name = safe_name(entry['name'])
        if name in expected or not (name.startswith('files/') or name == 'history.bundle'):
            raise ValueError('Invalid manifest entry')
        expected.add(name)
        data = archive.read(name)
        if len(data) != entry['size'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise ValueError('SHA-256 or size mismatch')
    if expected != set(names):
        raise ValueError('Unmanifested or missing entries')
    if manifest['history'] != ('history.bundle' in expected):
        raise ValueError('History flag does not match archive contents')
    destinations = set()
    for entry in manifest['files']:
        name = entry['name']
        mapped = name[6:] if name.startswith('files/') else '.backup-history.bundle'
        if mapped in destinations:
            raise ValueError('Restore destination collision')
        destinations.add(mapped)
    for name in destinations:
        if any(str(p) in destinations for p in PurePosixPath(name).parents if str(p) != '.'):
            raise ValueError('Restore destination parent collision')
    for name in names:
        if any(str(p) in expected for p in PurePosixPath(name).parents if str(p) != '.'):
            raise ValueError('File/directory path collision')
    return manifest


def verify(path):
    with zipfile.ZipFile(path) as archive:
        return verify_open(archive)


def create(root, output, without_history=False):
    root, output = root.resolve(), output.resolve()
    if output == root or root in output.parents:
        raise ValueError('Backup output must be outside source repository')
    if git(root, 'rev-parse', '--show-toplevel').decode().strip() != str(root):
        raise ValueError('Source must be the Git repository root')
    initial_refs = git(root, 'show-ref', '--head')
    initial_head = git(root, 'rev-parse', 'HEAD').decode().strip()
    tracked = paths(root)
    candidates = tracked | paths(root, '--others', '--exclude-standard')
    ignored = paths(root, '--others', '--ignored', '--exclude-standard')
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    result = output / ('backup-' + uuid.uuid4().hex + '.zip')
    manifest = {'schema': 1, 'head': initial_head,
                'history': not without_history, 'files': [], 'excluded': [],
                'ignored_paths_not_backed_up': sorted(ignored),
                'secret_detection': 'best-effort patterns; not a guarantee of absence'}
    checks = []
    deleted = []
    # Staging is private; a final .zip appears only after successful verification.
    with tempfile.TemporaryDirectory(prefix='.backup-staging-', dir=output) as temp:
        os.chmod(temp, 0o700)
        staged = Path(temp) / 'pending.zip'
        with zipfile.ZipFile(staged, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
            def add(name, data, mode=0o600):
                safe_name(name)
                if len(data) > MAX_FILE:
                    raise ValueError('Archive member too large')
                info = zipfile.ZipInfo(name)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (stat.S_IFREG | mode) << 16
                archive.writestr(info, data)
                manifest['files'].append({'name': name, 'size': len(data),
                                          'sha256': hashlib.sha256(data).hexdigest()})
            for name in sorted(candidates):
                safe_name(name)
                path = root / name
                reason = excluded(name, name in tracked)
                if path.is_symlink() or any(p.is_symlink() for p in path.parents):
                    reason = 'symlink'
                if reason:
                    manifest['excluded'].append({'path': name, 'reason': reason})
                    continue
                if not path.exists() and name in tracked:
                    manifest['excluded'].append({'path': name, 'reason': 'tracked-deletion'})
                    deleted.append(path)
                    continue
                data, mode = read_regular(path)
                if sensitive(data):
                    manifest['excluded'].append({'path': name, 'reason': 'sensitive-content'})
                    continue
                add('files/' + name, data, mode & 0o700)
                checks.append((path, hashlib.sha256(data).digest(), mode))
            if not without_history:
                bundle = Path(temp) / 'history.bundle'
                history(root, bundle)
                data, _ = read_regular(bundle)
                add('history.bundle', data)
            archive.writestr('manifest.json', json.dumps(manifest, ensure_ascii=True, indent=2))
        for path, digest, mode in checks:
            current_data, current_mode = read_regular(path)
            if hashlib.sha256(current_data).digest() != digest or current_mode != mode:
                raise ValueError('Source changed during backup; retry when idle')
        if candidates != paths(root) | paths(root, '--others', '--exclude-standard'):
            raise ValueError('Source file list changed during backup')
        if any(path.exists() or path.is_symlink() for path in deleted):
            raise ValueError('Deleted source file reappeared during backup')
        if initial_refs != git(root, 'show-ref', '--head') or initial_head != git(root, 'rev-parse', 'HEAD').decode().strip():
            raise ValueError('Git refs changed during backup')
        verify(staged)
        os.chmod(staged, 0o600)
        os.link(staged, result)  # exclusive final publication, never overwrites
    return result


def restore(backup, target, source=ROOT):
    # Keep the same open archive for validation and extraction.
    target = Path(os.path.abspath(target))
    for parent in [target, *target.parents]:
        if parent.is_symlink():
            raise ValueError('Symlink in restore destination')
    source = source.resolve()
    if target == source or source in target.parents:
        raise ValueError('Restore destination must be outside source')
    with zipfile.ZipFile(backup) as archive:
        manifest = verify_open(archive)
        target.mkdir(mode=0o700, exist_ok=False)
        for entry in manifest['files']:
            name = entry['name']
            rel = name[6:] if name.startswith('files/') else '.backup-history.bundle'
            path = target / safe_name(rel)
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with path.open('xb') as stream:
                stream.write(archive.read(name))
            mode = archive.getinfo(name).external_attr >> 16
            path.chmod((mode & 0o700) or 0o600)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    c = commands.add_parser('create')
    c.add_argument('--root', type=Path, default=ROOT)
    c.add_argument('--output', type=Path, required=True)
    c.add_argument('--without-history', action='store_true', help='Explicit partial backup: no Git history')
    v = commands.add_parser('verify')
    v.add_argument('archive', type=Path)
    r = commands.add_parser('restore')
    r.add_argument('archive', type=Path)
    r.add_argument('--to', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'create':
            print('Verified local backup:', create(args.root, args.output, args.without_history))
        elif args.command == 'verify':
            m = verify(args.archive)
            print('Integrity verified:', len(m['files']), 'files; history:', m['history'])
        else:
            restore(args.archive, args.to)
            print('Restored into new directory:', args.to)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
        # Git stderr, file contents and secret values are never printed.
        raise SystemExit('Backup failed: ' + type(exc).__name__ + '; no backup declared valid. ' +
                         (str(exc) if isinstance(exc, ValueError) and not isinstance(exc, json.JSONDecodeError) else 'Inspect paths/permissions and repository state.'))


if __name__ == '__main__':
    main()
