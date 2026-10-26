import hashlib
import os
import struct
import unittest
from unittest.mock import patch
import windows_dpapi as dpapi


class DPAPIValidationTests(unittest.TestCase):
    def test_invalid_inputs_rejected_before_native_api(self):
        with patch.object(dpapi, '_crypt') as native:
            for function, limit in ((dpapi.protect, dpapi.MAX_DATA),
                                    (dpapi.unprotect, dpapi.MAX_BLOB)):
                for value in (None, '', bytearray(b'x'), b'', b'x' * (limit + 1)):
                    with self.subTest(function=function.__name__, kind=type(value).__name__):
                        with self.assertRaises(ValueError):
                            function(value)
            native.assert_not_called()

    @unittest.skipIf(os.name == 'nt', 'unsupported-platform check')
    def test_non_windows_fails_closed(self):
        for function in (dpapi.protect, dpapi.unprotect):
            with self.assertRaises(OSError):
                function(b'synthetic')

    def test_corrupt_envelope_rejected_even_if_native_reports_success(self):
        data = b'PUBLIC SYNTHETIC FIXTURE'
        good = dpapi._MAGIC + struct.pack('!I', len(data)) + hashlib.sha256(data).digest() + data
        with patch.object(dpapi, '_crypt', return_value=good):
            self.assertEqual(dpapi.unprotect(b'synthetic-blob'), data)
        for frame in (b'', b'x' + good[1:], good[:-1], good + b'x',
                      good[:len(dpapi._MAGIC)] + b'\0\0\0\0' + good[len(dpapi._MAGIC) + 4:]):
            with patch.object(dpapi, '_crypt', return_value=frame):
                with self.assertRaises(ValueError):
                    dpapi.unprotect(b'synthetic-blob')


@unittest.skipUnless(os.name == 'nt', 'requires real Windows DPAPI')
class WindowsDPAPITests(unittest.TestCase):
    def test_current_user_roundtrip(self):
        for data in (b'PUBLIC SYNTHETIC FIXTURE', b'x' * dpapi.MAX_DATA):
            blob = dpapi.protect(data)
            self.assertLessEqual(len(blob), dpapi.MAX_BLOB)
            self.assertNotEqual(blob, data)
            self.assertEqual(dpapi.unprotect(blob), data)

    def test_corrupt_or_truncated_blob_rejected(self):
        blob = dpapi.protect(b'PUBLIC SYNTHETIC FIXTURE')
        changed = bytearray(blob)
        changed[-1] ^= 1
        for candidate in (b'not a DPAPI blob', blob[:16], bytes(changed)):
            with self.assertRaises((OSError, ValueError)):
                dpapi.unprotect(candidate)

    def test_wrong_domain_entropy_rejected(self):
        blob = dpapi.protect(b'PUBLIC SYNTHETIC FIXTURE')
        with patch.object(dpapi, '_ENTROPY', b'wrong-synthetic-domain'):
            with self.assertRaises((OSError, ValueError)):
                dpapi.unprotect(blob)


if __name__ == '__main__':
    unittest.main()
