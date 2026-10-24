"""Offline integration boundaries: child launch and networking are mocked."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch
import sys

spec = importlib.util.spec_from_file_location('freellm_launcher', Path(__file__).with_name('launcher.py'))
launcher = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = launcher
spec.loader.exec_module(launcher)


class LauncherTests(unittest.TestCase):
    def configured(self):
        return {'FREELLM_API_KEY': 'unified-secret-for-test', 'FREELLM_FREE_ONLY_CONFIRMED': '1',
                'PATH': '/test/bin', 'RUFLO_PROVIDER': 'google',
                'ANTHROPIC_API_KEY': 'paid-anthropic', 'ANTHROPIC_AUTH_TOKEN': 'old-token',
                'GOOGLE_API_KEY': 'paid-google', 'GEMINI_API_KEY': 'paid-gemini',
                'OPENAI_API_KEY': 'paid-openai', 'OPENROUTER_API_KEY': 'paid-router',
                'OLLAMA_API_KEY': 'paid-ollama', 'CLAUDE_CODE_USE_BEDROCK': '1'}

    def test_loopback_and_remote_https_origins(self):
        for value, expected in [('http://127.0.0.1:3001/', True), ('http://localhost:3001', True),
                                ('http://[::1]:3001', True), ('https://gateway.example:443', False)]:
            with self.subTest(value=value):
                result = launcher.validate_origin(value)
                self.assertEqual(result.loopback, expected)
                self.assertFalse(result.url.endswith('/'))

    def test_rejects_credential_query_path_unsafe_and_cleartext_remote_urls(self):
        bad = ['', 'ftp://127.0.0.1', 'http://user:secret@127.0.0.1:3001',
               'http://@127.0.0.1', 'http://127.0.0.1:3001/v1', 'http://127.0.0.1?',
               'http://127.0.0.1#', 'http://public.example:3001', 'http://127.1:3001',
               'http://localhost.evil.test', 'https://bad%2ehost', 'http://127.0.0.1:0',
               'http://127.0.0.1:65536', 'http://127.0.0.1:', 'http://\n127.0.0.1',
               'https://a\\b.test', 'https://bad_host.example', 'https://-bad.example',
               'http://[::1]evil', 'http://localhost:03001']
        for value in bad:
            with self.subTest(value=value), self.assertRaises(ValueError):
                launcher.validate_origin(value)

    def test_default_doctor_and_dry_run_are_offline_and_do_not_disclose_keys(self):
        env = self.configured()
        for args in [[], ['--dry-run', '--', 'node', 'bin/cli.js', 'status']]:
            with self.subTest(args=args), patch.dict(os.environ, env, clear=True), \
                    patch.object(launcher.subprocess, 'run') as run, \
                    patch.object(launcher.http.client, 'HTTPConnection') as connection, \
                    patch.object(launcher.http.client, 'HTTPSConnection') as secure, \
                    contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(launcher.main(args), 0)
                result = json.loads(out.getvalue())
                self.assertTrue(result['launch_guard_satisfied'])
                self.assertFalse(result['model_inference_performed'])
                for value in env.values():
                    if 'secret' in value or value.startswith('paid-'):
                        self.assertNotIn(value, out.getvalue())
                run.assert_not_called(); connection.assert_not_called(); secure.assert_not_called()

    def test_launch_requires_free_only_confirmation_and_key(self):
        origin = launcher.validate_origin(launcher.DEFAULT_ORIGIN)
        for env in [{}, {'FREELLM_API_KEY': 'test-secret'}, {'FREELLM_FREE_ONLY_CONFIRMED': '1'},
                    {'FREELLM_API_KEY': 'test-secret', 'FREELLM_FREE_ONLY_CONFIRMED': 'true'}]:
            with self.subTest(env_keys=list(env)), patch.object(launcher.subprocess, 'run') as run, \
                    self.assertRaises(ValueError):
                launcher.launch(['node', 'bin/cli.js', 'status'], env, origin)
            run.assert_not_called()

    def test_child_routing_and_credentials_are_scoped_and_no_shell_or_fallback(self):
        parent = self.configured()
        before = parent.copy()
        origin = launcher.validate_origin(launcher.DEFAULT_ORIGIN)
        with patch.object(launcher.subprocess, 'run', return_value=MagicMock(returncode=7)) as run:
            self.assertEqual(launcher.launch(['node', 'bin/cli.js', 'status'], parent, origin), 7)
        command = run.call_args.args[0]
        child = run.call_args.kwargs['env']
        self.assertEqual(command, ['node', 'bin/cli.js', 'status'])
        self.assertNotIn(parent['FREELLM_API_KEY'], ' '.join(command))
        self.assertFalse(run.call_args.kwargs['shell'])
        self.assertEqual(child['RUFLO_PROVIDER'], 'anthropic')
        self.assertEqual(child['ANTHROPIC_BASE_URL'], launcher.DEFAULT_ORIGIN)
        self.assertEqual(child['ANTHROPIC_AUTH_TOKEN'], parent['FREELLM_API_KEY'])
        for key in launcher.CONFLICTING_KEYS - {'ANTHROPIC_AUTH_TOKEN'}:
            self.assertNotIn(key, child)
        self.assertEqual(parent, before)
        self.assertEqual(run.call_count, 1)

    def test_explicit_launch_does_not_mutate_process_environment(self):
        parent = self.configured()
        with patch.dict(os.environ, parent, clear=True), patch.object(launcher.subprocess, 'run',
                return_value=MagicMock(returncode=0)), contextlib.redirect_stdout(io.StringIO()):
            before = dict(os.environ)
            self.assertEqual(launcher.main(['--', 'node', 'bin/cli.js', 'status']), 0)
            self.assertEqual(dict(os.environ), before)

    def test_probe_only_local_get_without_keys_body_reads_redirects_or_proxies(self):
        connection = MagicMock()
        response = connection.getresponse.return_value
        response.status = 302
        origin = launcher.validate_origin('http://localhost:3001')
        with patch.object(launcher.http.client, 'HTTPConnection', return_value=connection) as factory:
            report = launcher.probe_local(origin)
        factory.assert_called_once_with('127.0.0.1', 3001, timeout=3)
        connection.request.assert_called_once_with('GET', '/api/ping', headers={'Accept': 'application/json'})
        response.read.assert_not_called()
        connection.close.assert_called_once()
        self.assertFalse(report['healthy'])
        self.assertEqual(report['http_status'], 302)
        self.assertEqual(connection.request.call_count, 1)

    def test_remote_probe_rejected_before_network(self):
        with patch.object(launcher.http.client, 'HTTPSConnection') as connection, self.assertRaises(ValueError):
            launcher.probe_local(launcher.validate_origin('https://gateway.example'))
        connection.assert_not_called()

    def test_unreachable_probe_is_sanitized(self):
        connection = MagicMock()
        connection.request.side_effect = OSError('secret-error-body')
        with patch.object(launcher.http.client, 'HTTPConnection', return_value=connection):
            report = launcher.probe_local(launcher.validate_origin(launcher.DEFAULT_ORIGIN))
        self.assertFalse(report['reachable'])
        self.assertNotIn('secret-error-body', json.dumps(report))

    def test_no_secret_in_argv_or_shell_expansion(self):
        env = self.configured()
        origin = launcher.validate_origin(launcher.DEFAULT_ORIGIN)
        with patch.object(launcher.subprocess, 'run') as run, self.assertRaises(ValueError):
            launcher.launch(['node', '--token=' + env['FREELLM_API_KEY']], env, origin)
        run.assert_not_called()
        with patch.object(launcher.subprocess, 'run', return_value=MagicMock(returncode=0)) as run:
            launcher.launch(['echo', '$(touch /do-not-run)'], env, origin)
        self.assertEqual(run.call_args.args[0][1], '$(touch /do-not-run)')
        self.assertFalse(run.call_args.kwargs['shell'])

    def test_command_requires_explicit_separator(self):
        with patch.dict(os.environ, self.configured(), clear=True), patch.object(launcher.subprocess, 'run') as run, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(launcher.main(['node', 'bin/cli.js']), 2)
            self.assertEqual(launcher.main(['--']), 2)
        run.assert_not_called()

    def test_probe_dry_run_and_launch_are_separate(self):
        for args in [['--probe', '--dry-run'], ['--probe', '--', 'node', 'bin/cli.js']]:
            with patch.object(launcher.subprocess, 'run') as run, patch.object(launcher, 'probe_local') as probe, \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(launcher.main(args), 2)
            run.assert_not_called(); probe.assert_not_called()

    def test_invalid_url_and_child_exception_do_not_echo_credentials(self):
        env = self.configured()
        with patch.dict(os.environ, env, clear=True), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(launcher.main(['--base-url', 'http://user:' + env['FREELLM_API_KEY'] + '@localhost']), 2)
        self.assertNotIn(env['FREELLM_API_KEY'], out.getvalue())
        with patch.dict(os.environ, env, clear=True), contextlib.redirect_stdout(io.StringIO()) as out, \
                patch.object(launcher.subprocess, 'run', side_effect=OSError(env['FREELLM_API_KEY'])):
            self.assertEqual(launcher.main(['--', 'node', 'bin/cli.js']), 2)
        self.assertNotIn(env['FREELLM_API_KEY'], out.getvalue())


if __name__ == '__main__':
    unittest.main()
