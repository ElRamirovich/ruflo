"""Experimental encrypted receipts; caller supplies key, never stored here."""
import json
import re
from cryptography.fernet import Fernet
from task_memory import TaskMemory


class EncryptedMemory(TaskMemory):
    def __init__(self, path, key, create=False):
        self.cipher = Fernet(key)
        super().__init__(path, create=create)
        try:
            if create:
                with self.db:
                    self.db.execute('CREATE TABLE crypto_meta (token BLOB NOT NULL)')
                    self.db.execute('INSERT INTO crypto_meta VALUES (?)',
                                    (self.cipher.encrypt(b'encrypted-receipts-v1'),))
            rows = self.db.execute('SELECT token FROM crypto_meta').fetchall()
            if len(rows) != 1 or self.cipher.decrypt(rows[0][0]) != b'encrypted-receipts-v1':
                raise ValueError('invalid encrypted database')
        except Exception:
            self.close()
            raise

    @staticmethod
    def check_id(task_id):
        if type(task_id) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', task_id):
            raise ValueError('invalid id')

    def append(self, task_id, a, b, result):
        self.check_id(task_id)
        if any(type(n) is not int or abs(n)>1_000_000 for n in (a,b)) or type(result) is not int or result != a+b:
            raise ValueError('invalid receipt')
        payload = json.dumps({'id':task_id,'tool':'add','a':a,'b':b,'result':result}).encode()
        token = self.cipher.encrypt(payload)
        with self.db:
            self.db.execute('INSERT INTO receipts VALUES (?,?)',(task_id,token))

    def get(self, task_id):
        self.check_id(task_id)
        row = self.db.execute('SELECT payload FROM receipts WHERE id=?',(task_id,)).fetchone()
        if row is None:
            return None
        if not isinstance(row[0], bytes) or len(row[0])>4096:
            raise ValueError('invalid token')
        obj = json.loads(self.cipher.decrypt(row[0]))
        if type(obj) is not dict or set(obj)!={'id','tool','a','b','result'} or obj['id']!=task_id or obj['tool']!='add':
            raise ValueError('invalid context')
        if any(type(obj[n]) is not int or abs(obj[n])>1_000_000 for n in ('a','b')) or type(obj['result']) is not int or obj['result']!=obj['a']+obj['b']:
            raise ValueError('invalid receipt')
        return {k:v for k,v in obj.items() if k!='id'}
