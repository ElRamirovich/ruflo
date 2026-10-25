import tempfile
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch
from task_memory import TaskMemory
from recorded_task import run_recorded

GOOD='{"tool":"add","arguments":{"a":17,"b":25}}'


class RecordedTaskTests(unittest.TestCase):
    def test_execution_persists_and_duplicate_does_not_call_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'memory.db'
            m=TaskMemory(path,create=True)
            try:
                with patch('task_runner.client.request_chat',return_value=GOOD) as call:
                    r=run_recorded(m,'task1',17,25,'model',request=True,execute=True,confirmed=True)
                    self.assertTrue(r['memory_saved'])
                    with self.assertRaises(ValueError):
                        run_recorded(m,'task1',17,25,'model',request=True,execute=True,confirmed=True)
                    call.assert_called_once()
            finally:m.close()
            m=TaskMemory(path)
            try:self.assertEqual(m.get('task1')['result'],42)
            finally:m.close()

    def test_offline_preview_and_invalid_proposal_do_not_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=TaskMemory(Path(tmp)/'memory.db',create=True)
            try:
                self.assertFalse(run_recorded(m,'task1',17,25,'model')['memory_saved'])
                with patch('task_runner.client.request_chat',return_value=GOOD):
                    self.assertFalse(run_recorded(m,'task1',17,25,'model',request=True,confirmed=True)['memory_saved'])
                with patch('task_runner.client.request_chat',return_value=GOOD.replace('add','shell')):
                    with self.assertRaises(ValueError):
                        run_recorded(m,'task1',17,25,'model',request=True,execute=True,confirmed=True)
                self.assertIsNone(m.get('task1'))
            finally:m.close()

    def test_write_failure_keeps_execution_status_and_never_retries(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=TaskMemory(Path(tmp)/'memory.db',create=True)
            try:
                with patch('task_runner.client.request_chat',return_value=GOOD) as call, \
                     patch.object(m,'append',side_effect=sqlite3.OperationalError('PRIVATE ERROR')) as write:
                    r=run_recorded(m,'task1',17,25,'model',request=True,execute=True,confirmed=True)
                    self.assertTrue(r['executed'])
                    self.assertFalse(r['memory_saved'])
                    self.assertEqual(r['memory_status'],'write_failed_no_retry')
                    self.assertNotIn('PRIVATE',str(r))
                    call.assert_called_once();write.assert_called_once()
            finally:m.close()


if __name__=='__main__':unittest.main()
