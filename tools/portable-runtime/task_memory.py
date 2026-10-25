"""Local synthetic task receipts. Trusted caller only; not encrypted storage."""
import json
import os
import sqlite3
from pathlib import Path


class TaskMemory:
    def __init__(self, path, create=False):
        self.path = Path(path).absolute()
        if create:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
        if self.path.is_symlink() or not self.path.is_file():
            raise ValueError('regular database required')
        self.db = sqlite3.connect(self.path.as_uri() + '?mode=rw', uri=True, timeout=2)
        self.db.execute('PRAGMA trusted_schema=OFF')
        if create:
            with self.db:
                self.db.execute('CREATE TABLE receipts (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')

    def append(self, task_id, a, b, result):
        if type(task_id) is not str or not 1 <= len(task_id) <= 64 or not all(c in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in task_id):
            raise ValueError('invalid id')
        if any(type(n) is not int or abs(n)>1_000_000 for n in (a,b)) or type(result) is not int or result != a+b:
            raise ValueError('invalid receipt')
        payload = json.dumps({'tool':'add','a':a,'b':b,'result':result})
        with self.db:
            self.db.execute('INSERT INTO receipts VALUES (?,?)',(task_id,payload))

    def get(self, task_id):
        if type(task_id) is not str or len(task_id)>64:
            raise ValueError('invalid id')
        row = self.db.execute('SELECT payload FROM receipts WHERE id=?',(task_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def close(self):
        self.db.close()
