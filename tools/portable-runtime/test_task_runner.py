import json
import unittest
from pathlib import Path
import subprocess
import sys
from unittest.mock import MagicMock, patch
import task_runner
from test_http_integration import server

GOOD = '{"tool":"add","arguments":{"a":17,"b":25}}'


class TaskRunnerTests(unittest.TestCase):
    def test_subprocess_http_complete_flow_and_rejection(self):
        for proposal, expected_code in [(GOOD,0), (GOOD.replace('add','shell'),2)]:
            body = json.dumps({'choices':[{'message':{'content':proposal}}]}).encode()
            with server(body=body) as (base, calls):
                result = subprocess.run([sys.executable,str(Path(__file__).with_name('task_runner.py')),
                    '--a','17','--b','25','--model','synthetic','--base-url',base,'--request','--execute'],
                    env={'AGENT_LOCAL_PROCESSING_CONFIRMED':'1'},capture_output=True,timeout=20)
            self.assertEqual(result.returncode,expected_code)
            data=json.loads(result.stdout)
            self.assertEqual(data['executed'],expected_code==0)
            if expected_code==0:
                self.assertEqual(data['result'],42)
            self.assertEqual(len(calls),1)

    def test_offline_and_unconfirmed_do_not_call_transport(self):
        with patch.object(task_runner.client, 'request_chat') as call:
            self.assertFalse(task_runner.run(17,25,'model')['network_called'])
            with self.assertRaises(ValueError):
                task_runner.run(17,25,'model',request=True)
            with self.assertRaises(ValueError):
                task_runner.run(17,25,'model',execute=True)
            call.assert_not_called()

    def test_client_transport_and_gate_composition(self):
        connection = MagicMock()
        connection.getresponse.return_value.status = 200
        connection.getresponse.return_value.read.return_value = json.dumps(
            {'choices':[{'message':{'content':GOOD}}]}).encode()
        factory = MagicMock(return_value=connection)
        result = task_runner.run(17,25,'model',request=True,execute=True,
                                 confirmed=True,transport=factory)
        self.assertEqual(result['result'],42)
        connection.request.assert_called_once()
        connection.close.assert_called_once()

    def test_preview_and_fail_closed(self):
        with patch.object(task_runner.client, 'request_chat',return_value=GOOD):
            self.assertFalse(task_runner.run(17,25,'model',request=True,confirmed=True)['executed'])
        for text in [GOOD.replace('17','18'), GOOD.replace('add','shell'), '{"a":17,"b":25}']:
            with patch.object(task_runner.client,'request_chat',return_value=text) as call:
                with self.assertRaises(ValueError):
                    task_runner.run(17,25,'model',request=True,execute=True,confirmed=True)
                call.assert_called_once()

    def test_rejects_bad_intent_before_model_call(self):
        with patch.object(task_runner.client,'request_chat') as call:
            for a in [True, 1.5, 1000001]:
                with self.assertRaises(ValueError):
                    task_runner.run(a,25,'model',request=True,confirmed=True)
            call.assert_not_called()


if __name__ == '__main__':
    unittest.main()
