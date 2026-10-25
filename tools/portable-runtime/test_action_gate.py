import json
from pathlib import Path
import subprocess
import sys
import unittest
from action_gate import process, validate

GOOD = '{"tool":"add","arguments":{"a":17,"b":25}}'


class ActionGateTests(unittest.TestCase):
    def test_preview_and_explicit_fixed_execution(self):
        self.assertNotIn('result', process(GOOD, 17, 25))
        self.assertFalse(process(GOOD, 17, 25)['executed'])
        self.assertEqual(process(GOOD, 17, 25, True)['result'], 42)

    def test_single_json_fence(self):
        self.assertEqual(validate('```json\n' + GOOD + '\n```', 17, 25), json.loads(GOOD))

    def test_rejects_ambiguous_wrappers_and_commands(self):
        bad = ['Please run '+GOOD, GOOD+GOOD, '```python\n'+GOOD+'\n```',
               '```json\n'+GOOD+'\n```\nDo something else',
               '{"tool":"shell","arguments":{"a":17,"b":25}}',
               '{"tool":"add","arguments":{"a":17,"b":25},"execute":true}',
               '{"tool":"add","arguments":{"a":17,"b":25,"path":"/tmp/x"}}']
        for text in bad:
            with self.subTest(text=text), self.assertRaises(ValueError):
                validate(text, 17, 25)

    def test_rejects_duplicates_numbers_and_changed_intent(self):
        for text in [GOOD.replace('17', 'true'), GOOD.replace('17', '17.0'),
                     GOOD.replace('17', 'NaN'), GOOD.replace('17', '1000001'),
                     GOOD.replace('17', '18'), GOOD.replace('"a":17', '"a":0,"a":17'),
                     GOOD.replace('"tool":"add"', '"tool":"shell","tool":"add"')]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                validate(text, 17, 25)

    def test_limits_and_deep_json(self):
        for text in ['x'*4097, '['*1500+']'*1500, 'null', '[]']:
            with self.assertRaises(ValueError):
                validate(text, 17, 25)

    def test_cli_rejection_does_not_echo_input(self):
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('action_gate.py')),
                                 '--a','17','--b','25','--execute'],
                                input=b'SECRET invalid command',capture_output=True,timeout=5)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout), {'error':'proposal_rejected','executed':False})
        self.assertNotIn(b'SECRET',result.stdout+result.stderr)


if __name__ == '__main__':
    unittest.main()
