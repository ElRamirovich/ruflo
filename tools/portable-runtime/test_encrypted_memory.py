from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from cryptography.fernet import Fernet, InvalidToken
from encrypted_memory import EncryptedMemory
from recorded_task import run_recorded


class EncryptedTests(unittest.TestCase):
    def test_reopen_wrong_key_tamper_and_no_plaintext(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'encrypted.db';key=Fernet.generate_key()
            m=EncryptedMemory(p,key,create=True)
            m.append('one',17,25,42);m.close()
            self.assertNotIn(b'"result"',p.read_bytes())
            with self.assertRaises(InvalidToken):EncryptedMemory(p,Fernet.generate_key())
            m=EncryptedMemory(p,key)
            try:
                self.assertEqual(m.get('one')['result'],42)
                m.db.execute("UPDATE receipts SET payload=? WHERE id='one'",(b'corrupt',));m.db.commit()
                with self.assertRaises(InvalidToken):m.get('one')
            finally:m.close()

    def test_context_swap_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=EncryptedMemory(Path(tmp)/'db',Fernet.generate_key(),create=True)
            try:
                m.append('one',1,2,3)
                m.db.execute("UPDATE receipts SET id='two'");m.db.commit()
                with self.assertRaises(ValueError):m.get('two')
            finally:m.close()

    def test_recorded_execution_uses_encrypted_adapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=EncryptedMemory(Path(tmp)/'db',Fernet.generate_key(),create=True)
            try:
                with patch('task_runner.client.request_chat',return_value='{"tool":"add","arguments":{"a":17,"b":25}}'):
                    r=run_recorded(m,'one',17,25,'synthetic',request=True,execute=True,confirmed=True)
                self.assertTrue(r['memory_saved'])
                self.assertEqual(m.get('one')['result'],42)
            finally:m.close()


if __name__=='__main__':unittest.main()
