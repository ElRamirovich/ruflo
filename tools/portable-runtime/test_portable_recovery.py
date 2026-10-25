"""Synthetic recovery using only an archive, password package and password."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from cryptography.fernet import Fernet
from encrypted_memory import EncryptedMemory
from recovery_package import pack
from sealed_backup import seal

CHILD = '''import sys
from recovery_package import unpack
from sealed_backup import bounded_read,unseal
from encrypted_memory import EncryptedMemory
try:
    password=sys.stdin.buffer.read(1024).decode()
    keys=unpack(bounded_read(sys.argv[1],65536),password)
    unseal(sys.argv[2],sys.argv[3],keys['memory'].encode(),keys['backup'].encode())
    memory=EncryptedMemory(sys.argv[3],keys['memory'].encode())
    try: valid=memory.get('synthetic')['result']==42
    finally: memory.close()
    if not valid: raise ValueError()
    print('RECOVERED')
except Exception:
    print('REJECTED')
    sys.exit(2)
'''


class PortableRecoveryTests(unittest.TestCase):
    def test_password_only_fresh_process_and_failure_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, archive, package = [root/name for name in ('source.db','backup.fernet','keys.7z')]
            keys = {name:Fernet.generate_key().decode() for name in ('memory','backup')}
            password = 'PUBLIC-SYNTHETIC-PASSWORD-ONLY'
            memory = EncryptedMemory(source,keys['memory'].encode(),create=True)
            try: memory.append('synthetic',17,25,42)
            finally: memory.close()
            seal(source,archive,keys['memory'].encode(),keys['backup'].encode())
            package.write_bytes(pack(keys,password))
            original = source.read_bytes()
            archive_bytes, package_bytes = archive.read_bytes(), package.read_bytes()
            # Only synthetic fixtures; never operates on user data.
            env = {k:os.environ[k] for k in ('SYSTEMROOT','PYTHONPATH') if k in os.environ}
            if 'PYTHONPATH' in env:
                env['PYTHONPATH'] = os.pathsep.join(str(Path(p).resolve()) for p in env['PYTHONPATH'].split(os.pathsep))
            cases = [('valid',password,False,False,0),
                     ('wrong-password','WRONG-SYNTHETIC-PASSWORD-ONLY',False,False,2),
                     ('truncated-package',password,True,False,2),
                     ('truncated-archive',password,False,True,2)]
            for name, supplied, bad_package, bad_archive, code in cases:
                with self.subTest(name=name):
                    package.write_bytes(package_bytes[:-20] if bad_package else package_bytes)
                    archive.write_bytes(archive_bytes[:-20] if bad_archive else archive_bytes)
                    target = root/(name+'.db')
                    result = subprocess.run([sys.executable,'-c',CHILD,str(package),str(archive),str(target)],
                        input=supplied.encode(),capture_output=True,timeout=20,
                        cwd=Path(__file__).parent,env=env)
                    self.assertEqual(result.returncode,code)
                    self.assertEqual(result.stdout.strip(),b'RECOVERED' if code==0 else b'REJECTED')
                    self.assertEqual(result.stderr,b'')
                    self.assertEqual(target.exists(),code==0)
                    for secret in [password,*keys.values()]:
                        self.assertNotIn(secret.encode(),result.stdout+result.stderr)
            self.assertEqual(source.read_bytes(),original)


if __name__ == '__main__': unittest.main()
