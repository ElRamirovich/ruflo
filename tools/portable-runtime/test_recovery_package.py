import unittest
from cryptography.fernet import Fernet
from recovery_package import pack,unpack


class RecoveryPackageTests(unittest.TestCase):
    def test_password_roundtrip_and_rejections(self):
        keys={name:Fernet.generate_key().decode() for name in ('memory','backup')}
        password='SYNTHETIC-ONLY-PASSWORD-2026'
        data=pack(keys,password)
        self.assertEqual(unpack(data,password),keys)
        for key in keys.values():self.assertNotIn(key.encode(),data)
        for candidate in [data,data[:-20]]:
            with self.assertRaises(Exception):unpack(candidate,'WRONG-SYNTHETIC-PASSWORD')
        with self.assertRaises(Exception):unpack(data[:-20],password)
        with self.assertRaises(ValueError):pack(keys,'short')
        with self.assertRaises(ValueError):pack({'memory':keys['memory'],'backup':keys['memory']},password)


if __name__=='__main__':unittest.main()
