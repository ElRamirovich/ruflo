from pathlib import Path
import tempfile
import unittest
from cryptography.fernet import Fernet, InvalidToken
from encrypted_memory import EncryptedMemory
from sealed_backup import seal, unseal


class SealedBackupTests(unittest.TestCase):
    def test_roundtrip_hides_schema_and_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.db';archive=root/'backup';restored=root/'restored.db'
            key,backup_key=Fernet.generate_key(),Fernet.generate_key()
            m=EncryptedMemory(source,key,create=True)
            try:m.append('SYNTHETIC_IDENTIFIER',17,25,42)
            finally:m.close()
            seal(source,archive,key,backup_key)
            content=archive.read_bytes()
            for marker in [b'SQLite format',b'SYNTHETIC_IDENTIFIER',b'crypto_meta']:
                self.assertNotIn(marker,content)
            unseal(archive,restored,key,backup_key)
            m=EncryptedMemory(restored,key)
            try:self.assertEqual(m.get('SYNTHETIC_IDENTIFIER')['result'],42)
            finally:m.close()

    def test_bad_keys_corruption_and_overwrite_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';archive=root/'backup';dest=root/'dest'
            key,backup_key=Fernet.generate_key(),Fernet.generate_key()
            m=EncryptedMemory(source,key,create=True);m.close()
            with self.assertRaises(ValueError):seal(source,archive,key,key)
            self.assertFalse(archive.exists())
            seal(source,archive,key,backup_key)
            for mk,bk in [(key,Fernet.generate_key()),(Fernet.generate_key(),backup_key)]:
                with self.assertRaises(InvalidToken):unseal(archive,dest,mk,bk)
                self.assertFalse(dest.exists())
            original=archive.read_bytes()
            with self.assertRaises(FileExistsError):seal(source,archive,key,backup_key)
            self.assertEqual(archive.read_bytes(),original)
            archive.write_bytes(original[:-8])
            with self.assertRaises(InvalidToken):unseal(archive,dest,key,backup_key)
            self.assertFalse(dest.exists())


if __name__=='__main__':unittest.main()
