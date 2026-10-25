import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from key_custody import generate, load
from encrypted_memory import EncryptedMemory
from sealed_backup import seal, unseal


class KeyCustodyTests(unittest.TestCase):
    def test_equivalent_key_encoding_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)/'keys';generate(directory)
            key=(directory/'memory.key').read_bytes()
            alphabet=b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
            alternative=key[:-2]+bytes([alphabet[alphabet.index(key[-2])+1]])+key[-1:]
            Fernet(alternative)
            (directory/'backup.key').write_bytes(alternative)
            with self.assertRaises(ValueError):load(directory)

    def test_files_reopen_and_recovery_without_secret_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);directory=root/'keys';generate(directory)
            memory_key,backup_key=load(directory)
            self.assertNotEqual(memory_key,backup_key)
            result=subprocess.run([sys.executable,str(Path(__file__).with_name('key_custody.py')),
                'check','--directory',str(directory)],capture_output=True,timeout=5,env={})
            self.assertEqual(result.returncode,0)
            self.assertTrue(json.loads(result.stdout)['key_files_valid'])
            for key in (memory_key,backup_key):self.assertNotIn(key,result.stdout+result.stderr)
            source,archive,restore=root/'source',root/'archive',root/'restore'
            m=EncryptedMemory(source,memory_key,create=True)
            m.append('synthetic',1,2,3);m.close()
            seal(source,archive,memory_key,backup_key)
            unseal(archive,restore,*load(directory))
            with self.assertRaises(FileExistsError):generate(directory)
            self.assertEqual(load(directory),(memory_key,backup_key))

    def test_permissions_links_and_missing_key_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)/'keys';generate(directory)
            file=directory/'memory.key';original=file.read_bytes()
            file.chmod(0o644)
            with self.assertRaises(ValueError):load(directory)
            file.chmod(0o600)
            file.unlink();file.symlink_to(directory/'backup.key')
            with self.assertRaises(OSError):load(directory)
            file.unlink()
            with self.assertRaises(OSError):load(directory)
            file.write_bytes(original);file.chmod(0o600)
            directory.chmod(0o755)
            with self.assertRaises(ValueError):load(directory)
            directory.chmod(0o700)


if __name__=='__main__':unittest.main()
