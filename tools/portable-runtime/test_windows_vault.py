"""Synthetic vault tests; native integration requires Windows and TEST_CUSTODY."""
import contextlib
import io
import os
from pathlib import Path
import tempfile
import subprocess
import stat
from types import SimpleNamespace
import unittest
from unittest.mock import patch, MagicMock

from cryptography.fernet import Fernet
from encrypted_memory import EncryptedMemory
import windows_vault as vault

PASSWORD = 'PUBLIC-SYNTHETIC-VAULT-PASSWORD'


def exercise(root, testcase):
    state = root/'original'
    vault.initialize(state, PASSWORD)
    testcase.assertEqual(vault.check_vault(state)['receipts'],0)
    keys = vault.load_keys(state)
    memory = EncryptedMemory(state/'memory.db',keys['memory'].encode())
    try: memory.append('synthetic',17,25,42)
    finally: memory.close()
    source_bytes = (state/'memory.db').read_bytes()
    archive = state/'next.fernet'
    testcase.assertTrue(vault.backup(state,archive)['verified'])
    recovered = root/'recovered'
    vault.recover(state/'recovery.7z',archive,recovered,PASSWORD)
    testcase.assertEqual(vault.check_vault(recovered)['receipts'],1)
    restored_keys = vault.load_keys(recovered)
    memory = EncryptedMemory(recovered/'memory.db',restored_keys['memory'].encode())
    try: testcase.assertEqual(memory.get('synthetic')['result'],42)
    finally: memory.close()
    with testcase.assertRaises(Exception):
        vault.recover(state/'recovery.7z',archive,root/'wrong-password','WRONG-SYNTHETIC-VAULT-PASSWORD')
    testcase.assertFalse((root/'wrong-password').exists())
    before = {p.name:p.read_bytes() for p in recovered.iterdir() if p.is_file()}
    with testcase.assertRaises(FileExistsError):
        vault.recover(state/'recovery.7z',archive,recovered,PASSWORD)
    testcase.assertEqual(before,{p.name:p.read_bytes() for p in recovered.iterdir() if p.is_file()})
    with testcase.assertRaises(FileExistsError):vault.backup(state,archive)
    testcase.assertEqual((state/'memory.db').read_bytes(),source_bytes)
    for name in ('keys.dpapi','recovery.7z','initial.fernet','next.fernet'):
        content = (state/name).read_bytes()
        for secret in (PASSWORD,*keys.values()):testcase.assertNotIn(secret.encode(),content)
    bad_archive = root/'bad.fernet'
    bad_archive.write_bytes(archive.read_bytes()[:-20])
    with testcase.assertRaises(Exception):
        vault.recover(state/'recovery.7z',bad_archive,root/'bad-restore',PASSWORD)
    testcase.assertFalse((root/'bad-restore'/'READY').exists())
    testcase.assertFalse((root/'bad-restore'/'keys.dpapi').exists())
    (state/'keys.dpapi').write_bytes(b'invalid synthetic data')
    with testcase.assertRaises(Exception):vault.check_vault(state)


class VaultLogicTests(unittest.TestCase):
    def test_reparse_parent_rejected_before_inspecting_leaf(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)/'synthetic-junction'
            leaf = parent/'never-inspect.db'
            inspected = []
            def inspect(path):
                inspected.append(path)
                return SimpleNamespace(st_mode=stat.S_IFDIR,
                    st_file_attributes=0x400 if path == parent else 0)
            kernel = MagicMock()
            kernel.GetDriveTypeW.return_value = 3
            with patch.object(vault.sys,'platform','win32'), \
                 patch.object(vault.ctypes,'WinDLL',return_value=kernel,create=True), \
                 patch.object(Path,'lstat',inspect):
                with self.assertRaises(ValueError):vault.local_path(leaf)
            self.assertEqual(inspected,list(reversed(leaf.absolute().parents)))
            self.assertNotIn(leaf,inspected)

    def test_acl_subprocess_uses_fixed_code_and_minimal_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(vault.sys,'platform','win32'), \
                 patch.object(vault,'system_directory',return_value=Path(tmp)/'System32'), \
                 patch.object(vault,'local_path',side_effect=lambda p,**kw:Path(p).absolute()), \
                 patch.dict(os.environ,{'SystemRoot':tmp,'PRIVATE_API_KEY':'synthetic-not-forwarded'}), \
                 patch.object(vault.subprocess,'run',return_value=subprocess.CompletedProcess([],0,b'PRIVATE',b'')) as run:
                self.assertEqual(vault.check_directory(tmp),Path(tmp).absolute())
                args,kwargs = run.call_args
                self.assertNotIn('PRIVATE_API_KEY',kwargs['env'])
                self.assertEqual(kwargs['env']['MEU_AGENTE_ACL_PATH'],str(Path(tmp).absolute()))
                self.assertIn('-EncodedCommand',args[0])
                self.assertNotIn(str(Path(tmp).absolute()),args[0])
                run.return_value = subprocess.CompletedProcess([],2,b'REJECTED',b'')
                with self.assertRaises(ValueError):vault.check_directory(tmp)

    def test_workflow_with_simulated_os_protector(self):
        # This tests composition only, NOT DPAPI or Windows ACL enforcement.
        protector = Fernet(Fernet.generate_key())
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(vault,'check_directory',side_effect=lambda p:Path(p).absolute()), \
                 patch.object(vault,'local_path',side_effect=lambda p,**kw:Path(p).absolute()), \
                 patch.object(vault.windows_dpapi,'protect',side_effect=protector.encrypt), \
                 patch.object(vault.windows_dpapi,'unprotect',side_effect=protector.decrypt):
                exercise(Path(tmp),self)

    def test_permission_failure_prevents_persistent_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)/'state'
            with patch.object(vault,'check_directory',side_effect=ValueError('denied')), \
                 patch.object(vault.windows_dpapi,'protect') as protect:
                with self.assertRaises(ValueError):vault.initialize(target,PASSWORD)
                protect.assert_not_called()
            self.assertFalse(target.exists())

    def test_password_requires_tty_and_confirmation(self):
        with patch.object(vault.sys.stdin,'isatty',return_value=False), \
             patch.object(vault.getpass,'getpass') as prompt:
            with self.assertRaises(ValueError):vault.ask_password()
            prompt.assert_not_called()
        with patch.object(vault.sys.stdin,'isatty',return_value=True), \
             patch.object(vault.getpass,'getpass',side_effect=[PASSWORD,'different']):
            with self.assertRaises(ValueError):vault.ask_password(confirm=True)
        with patch.object(vault.sys.stdin,'isatty',return_value=True), \
             patch.object(vault.getpass,'getpass',side_effect=vault.getpass.GetPassWarning('no echo protection')):
            with self.assertRaises(vault.getpass.GetPassWarning):vault.ask_password()

    def test_cli_does_not_echo_sensitive_errors(self):
        output = io.StringIO()
        with patch.object(vault.sys,'platform','win32'), \
             patch.object(vault,'check_vault',side_effect=ValueError(PASSWORD)), \
             contextlib.redirect_stdout(output):
            self.assertEqual(vault.main(['check','--directory','synthetic']),2)
        self.assertNotIn(PASSWORD,output.getvalue())
        self.assertIn('vault_operation_failed',output.getvalue())


@unittest.skipUnless(os.name == 'nt','requires Windows, native DPAPI and private custody directory')
class WindowsVaultIntegrationTests(unittest.TestCase):
    def test_real_windows_acl_dpapi_backup_and_recovery(self):
        custody = os.environ.get('TEST_CUSTODY')
        if not custody:self.fail('Set TEST_CUSTODY to the existing private test directory.')
        parent = vault.check_directory(custody)
        with tempfile.TemporaryDirectory(prefix='synthetic-vault-',dir=parent) as tmp:
            exercise(Path(tmp),self)


if __name__ == '__main__':unittest.main()
