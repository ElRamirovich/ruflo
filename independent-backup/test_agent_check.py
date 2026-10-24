"""Privacy and read-only boundaries of offline agent diagnostics."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('agent_check', Path(__file__).with_name('agent-check.py'))
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class AgentCheckTests(unittest.TestCase):
    def test_reports_presence_without_disclosing_secrets_or_agent_identifiers(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            secret = 'private-value-never-printed-by-diagnostics'
            config = root / 'claude-flow.config.json'
            config.write_text(json.dumps({'agents': {'providers': [
                {'name': 'google', 'enabled': True, 'apiKey': secret, 'model': 'private-model-id'}]}}))
            registry = root / '.claude-flow/agents/store.json'
            registry.parent.mkdir(parents=True)
            registry.write_text(json.dumps({'agents': {'private-agent-id':
                {'provider': 'google', 'status': 'busy'}}}))
            with patch.dict(os.environ, {'GOOGLE_API_KEY': secret, 'RUFLO_PROVIDER': 'google'}):
                report = check.diagnose(root)
            rendered = json.dumps(report)
            self.assertNotIn(secret, rendered)
            self.assertNotIn('private-model-id', rendered)
            self.assertNotIn('private-agent-id', rendered)
            self.assertTrue(report['google_key_present_in_environment'])
            self.assertTrue(report['google_key_present_in_config'])
            self.assertTrue(report['provider_environment_is_google'])
            self.assertEqual(report['google_agent_records_marked_busy'], 1)
            self.assertFalse(report['live_agent_confirmed'])

    def test_diagnostic_does_not_create_state_or_load_dotenv(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dotenv = root / '.env'
            dotenv.write_text('GOOGLE_API_KEY=do-not-load\n')
            before = sorted(p.relative_to(root).as_posix() for p in root.rglob('*'))
            with patch.dict(os.environ, {}, clear=True):
                report = check.diagnose(root)
            self.assertFalse(report['google_key_present_in_environment'])
            self.assertFalse(report['project_config_present'])
            self.assertEqual(before, sorted(p.relative_to(root).as_posix() for p in root.rglob('*')))

    def test_malformed_config_does_not_echo_content(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'claude-flow.config.json').write_text('private-secret-not-valid-json')
            report = check.diagnose(root)
            self.assertFalse(report['project_config_parse_ok'])
            self.assertNotIn('private-secret-not-valid-json', json.dumps(report))


    def test_explicit_env_config_is_not_read(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dotenv = root / '.env'
            dotenv.write_text(json.dumps({'agents': {'providers': [
                {'name': 'google', 'apiKey': 'must-not-be-loaded'}]}}))
            with patch.dict(os.environ, {'CLAUDE_FLOW_CONFIG': str(dotenv)}):
                report = check.diagnose(root)
            self.assertFalse(report['project_config_parse_ok'])
            self.assertFalse(report['google_key_present_in_config'])


if __name__ == '__main__':
    unittest.main()
