"""Bounded synthetic encrypted-memory snapshots. Trusted private directories only."""
import os
from pathlib import Path
import sqlite3
import tempfile
import time
from encrypted_memory import EncryptedMemory

MAX_BYTES = 16 * 1024 * 1024
MAX_RECEIPTS = 1000


def snapshot(source, destination, key):
    """Backup or restore into a NEW path; never replaces a file or saves the key."""
    source, destination = Path(source).absolute(), Path(destination).absolute()
    if source.is_symlink() or not source.is_file() or source.stat().st_size > MAX_BYTES:
        raise ValueError('source rejected')
    if os.path.lexists(destination):
        raise FileExistsError('destination exists')
    deadline = time.monotonic() + 10

    def progress(status, remaining, total):
        if total * page_size > MAX_BYTES or time.monotonic() > deadline:
            raise ValueError('snapshot limit')

    # Temp and final path share a filesystem; hard link publishes without overwrite.
    with tempfile.TemporaryDirectory(prefix='memory-snapshot-', dir=destination.parent) as tmp:
        staged = Path(tmp) / 'snapshot.db'
        fd = os.open(staged, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        src = EncryptedMemory(source, key)
        try:
            page_size = src.db.execute('PRAGMA page_size').fetchone()[0]
            dst = sqlite3.connect(staged)
            try:
                src.db.backup(dst, pages=128, progress=progress, sleep=0.01)
            finally:
                dst.close()
        finally:
            src.close()
        if staged.stat().st_size > MAX_BYTES:
            raise ValueError('snapshot too large')
        check = EncryptedMemory(staged, key)
        try:
            if check.db.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise ValueError('integrity failed')
            ids = check.db.execute('SELECT id FROM receipts LIMIT ?', (MAX_RECEIPTS + 1,)).fetchall()
            if len(ids) > MAX_RECEIPTS:
                raise ValueError('receipt limit')
            for (task_id,) in ids:
                check.get(task_id)
        finally:
            check.close()
        # Windows _commit (used by fsync) needs a writable handle.
        # r+b preserves existing snapshot contents; it does not truncate.
        with staged.open('r+b') as stream:
            os.fsync(stream.fileno())
        os.link(staged, destination)
    return {'verified': True, 'receipts': len(ids), 'key_saved': False}
