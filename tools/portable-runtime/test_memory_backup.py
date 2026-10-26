import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import memory_backup
from cryptography.fernet import Fernet, InvalidToken
from encrypted_memory import EncryptedMemory
from memory_backup import snapshot


class MemoryBackupTests(unittest.TestCase):
    def test_windows_temporary_child_cleanup_and_collision(self):
        # Exercises the branch, not native ACL inheritance (covered on Windows).
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(memory_backup.sys,'platform','win32'):
                with self.assertRaisesRegex(ValueError,'synthetic failure'):
                    with memory_backup.temporary_directory(root,'test-') as owned:
                        (owned/'fixture').write_text('synthetic')
                        raise ValueError('synthetic failure')
                self.assertFalse(owned.exists())
                existing = root/'test-fixed'
                existing.mkdir()
                (existing/'keep').write_text('preserve')
                with patch.object(memory_backup.uuid,'uuid4',return_value=SimpleNamespace(hex='fixed')):
                    with self.assertRaises(FileExistsError):
                        with memory_backup.temporary_directory(root,'test-'):
                            self.fail('collision accepted')
                self.assertEqual((existing/'keep').read_text(),'preserve')

    def test_backup_restore_and_recovery_in_separate_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.db';backup=root/'backup.db';restored=root/'restored.db'
            key=Fernet.generate_key()
            memory=EncryptedMemory(source,key,create=True)
            try:memory.append('synthetic',17,25,42)
            finally:memory.close()
            self.assertTrue(snapshot(source,backup,key)['verified'])
            code = '''import json,sys
from memory_backup import snapshot
from encrypted_memory import EncryptedMemory
key=sys.stdin.buffer.read(45)
snapshot(sys.argv[1],sys.argv[2],key)
m=EncryptedMemory(sys.argv[2],key)
try: print(json.dumps(m.get('synthetic')))
finally: m.close()
'''
            result=subprocess.run([sys.executable,'-c',code,str(backup),str(restored)],
                input=key,capture_output=True,timeout=15,cwd=Path(__file__).parent)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['result'],42)
            self.assertNotIn(key,result.stdout+result.stderr)
            self.assertNotIn(b'"result"',restored.read_bytes())

    def test_wrong_key_tamper_and_existing_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.db';out=root/'out.db';key=Fernet.generate_key()
            m=EncryptedMemory(source,key,create=True)
            m.append('one',1,2,3);m.close()
            original=source.read_bytes()
            with self.assertRaises(InvalidToken):snapshot(source,out,Fernet.generate_key())
            self.assertFalse(out.exists())
            self.assertEqual(source.read_bytes(),original)
            out.write_bytes(b'preserve')
            with self.assertRaises(FileExistsError):snapshot(source,out,key)
            self.assertEqual(out.read_bytes(),b'preserve')
            out.unlink()
            m=EncryptedMemory(source,key)
            m.db.execute('UPDATE receipts SET payload=?',(b'corrupt',));m.db.commit();m.close()
            with self.assertRaises(InvalidToken):snapshot(source,out,key)
            self.assertFalse(out.exists())


if __name__=='__main__':unittest.main()
