"""Whole archive recovery in a fresh process. Synthetic keys and data only."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from cryptography.fernet import Fernet
from encrypted_memory import EncryptedMemory
from sealed_backup import seal

CHILD = '''import json,sys
from sealed_backup import unseal
from encrypted_memory import EncryptedMemory
try:
    keys=json.loads(sys.stdin.buffer.read(1024))
    unseal(sys.argv[1],sys.argv[2],keys['memory'].encode(),keys['backup'].encode())
    m=EncryptedMemory(sys.argv[2],keys['memory'].encode())
    try: ok=m.get('synthetic')['result']==42
    finally: m.close()
    if not ok: raise ValueError('recovery mismatch')
    print(json.dumps({'recovered':True}))
except Exception:
    print(json.dumps({'recovered':False}))
    sys.exit(2)
'''


class RecoveryProcessTests(unittest.TestCase):
    def test_fresh_process_success_missing_wrong_keys_and_truncation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.db';archive=root/'archive.fernet'
            memory_key,backup_key=Fernet.generate_key(),Fernet.generate_key()
            m=EncryptedMemory(source,memory_key,create=True)
            try:m.append('synthetic',17,25,42)
            finally:m.close()
            seal(source,archive,memory_key,backup_key)
            # Parent source remains untouched; the child is only given archive path.
            keys={'memory':memory_key.decode(),'backup':backup_key.decode()}
            cases=[(keys,True),({'backup':keys['backup']},False),
                   ({'memory':keys['memory']},False),
                   ({**keys,'memory':Fernet.generate_key().decode()},False),
                   ({**keys,'backup':Fernet.generate_key().decode()},False)]
            for index,(candidate,expected) in enumerate(cases):
                target=root/('restore-'+str(index)+'.db')
                env={}
                if 'SYSTEMROOT' in os.environ:env['SYSTEMROOT']=os.environ['SYSTEMROOT']
                r=subprocess.run([sys.executable,'-c',CHILD,str(archive),str(target)],
                    input=json.dumps(candidate).encode(),capture_output=True,timeout=15,
                    cwd=Path(__file__).parent,env=env)
                self.assertEqual(r.returncode,0 if expected else 2)
                self.assertEqual(json.loads(r.stdout),{'recovered':expected})
                self.assertEqual(target.exists(),expected)
                for secret in (memory_key,backup_key):self.assertNotIn(secret,r.stdout+r.stderr)
            archive.write_bytes(archive.read_bytes()[:-16])
            target=root/'truncated.db'
            r=subprocess.run([sys.executable,'-c',CHILD,str(archive),str(target)],
                input=json.dumps(keys).encode(),capture_output=True,timeout=15,
                cwd=Path(__file__).parent,env={})
            self.assertEqual(r.returncode,2)
            self.assertFalse(target.exists())
            self.assertTrue(source.exists())


if __name__=='__main__':unittest.main()
