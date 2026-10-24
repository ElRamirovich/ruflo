"""Private setup and Docker isolation; no Docker/network calls in tests."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, patch

spec = importlib.util.spec_from_file_location('gateway_setup', Path(__file__).with_name('setup_gateway.py'))
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class SetupTests(unittest.TestCase):
    def test_private_key_file_is_created_once_and_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            path = setup.prepare_env(Path(temp) / 'config')
            before = path.read_bytes()
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertIn(b'ENCRYPTION_KEY=', before)
            self.assertEqual(path, setup.prepare_env(path.parent))
            self.assertEqual(before, path.read_bytes())

    def test_rejects_links_and_public_or_foreign_config(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'link').symlink_to(root, target_is_directory=True)
            with self.assertRaises(ValueError):
                setup.prepare_env(root / 'link' / 'config')
            config = root / 'config'
            path = setup.prepare_env(config)
            path.chmod(0o644)
            with self.assertRaises(ValueError):
                setup.prepare_env(config)
            path.chmod(0o600)
            path.write_text('PRIVATE=foreign-data\n')
            with self.assertRaises(ValueError):
                setup.prepare_env(config)

    def test_existing_container_is_never_replaced(self):
        with patch.object(setup.shutil, 'which', return_value='/docker'), \
                patch.object(setup, 'docker', return_value=MagicMock(returncode=0)) as docker, \
                patch.object(setup, 'prepare_env') as env, self.assertRaises(ValueError):
            setup.start()
        env.assert_not_called()
        self.assertFalse(any(call.args[0] in {'run', 'rm', 'stop', 'restart'} for call in docker.call_args_list))

    def test_docker_run_has_only_local_port_no_socket_no_secret_arguments(self):
        def docker(*args, **kwargs):
            absent = args[0] == 'container' or args[:2] == ('volume', 'inspect')
            return subprocess.CompletedProcess(args, 1 if absent else 0, '', '')
        sock = MagicMock()
        sock.__enter__.return_value.connect_ex.return_value = 1
        with tempfile.TemporaryDirectory() as temp, patch.object(setup.shutil, 'which', return_value='/docker'), \
                patch.object(setup, 'docker', side_effect=docker) as calls, patch.object(setup.socket, 'socket', return_value=sock):
            result = setup.start(Path(temp) / 'config')
            run = next(c.args for c in calls.call_args_list if c.args[0] == 'run')
            self.assertIn('127.0.0.1:3001:3001', run)
            self.assertIn('--restart=no', run)
            self.assertIn('--pull=never', run)
            self.assertIn('node', run)
            self.assertIn('--cap-drop=ALL', run)
            self.assertFalse(any('docker.sock' in arg for arg in run))
            self.assertFalse(any('ENCRYPTION_KEY=' in arg for arg in run))
            self.assertFalse(result['inference_performed'])
            self.assertTrue(result['docker_loopback_binding'])
            self.assertFalse(result['codespaces_port_visibility_verified'])

    def test_existing_data_volume_is_not_rekeyed_or_started(self):
        def docker(*args, **kwargs):
            return subprocess.CompletedProcess(args, 1 if args[0] == 'container' else 0, '', '')
        with patch.object(setup.shutil, 'which', return_value='/docker'), \
                patch.object(setup, 'docker', side_effect=docker) as calls, \
                patch.object(setup, 'prepare_env') as env, self.assertRaisesRegex(ValueError, 'volume already exists'):
            setup.start()
        env.assert_not_called()
        self.assertFalse(any(c.args[0] in {'run', 'rm', 'stop', 'restart'} for c in calls.call_args_list))


if __name__ == '__main__':
    unittest.main()
