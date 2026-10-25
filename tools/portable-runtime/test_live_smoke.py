import subprocess
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import live_smoke


class LiveSmokeSafetyTests(unittest.TestCase):
    def test_fifo_rejected_without_blocking(self):
        with tempfile.TemporaryDirectory() as directory:
            fifo = Path(directory) / 'fifo'
            os.mkfifo(fifo)
            with self.assertRaises(ValueError):
                live_smoke.digest(fifo)

    def test_wrong_hash_never_starts_process(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'wrong'
            file.write_bytes(b'not a model or executable')
            with patch.object(live_smoke.subprocess, 'Popen') as start:
                with self.assertRaises(ValueError):
                    live_smoke.run(file, file)
                start.assert_not_called()

    def test_client_timeout_reaps_server(self):
        process = MagicMock()
        process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired('server', 5), 0]
        connection = MagicMock()
        connection.getresponse.return_value.status = 200
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'fixture'
            file.write_bytes(b'fixture')
            with patch.object(live_smoke, 'digest', side_effect=[live_smoke.SERVER_SHA, live_smoke.MODEL_SHA]), \
                 patch.object(live_smoke.subprocess, 'Popen', return_value=process), \
                 patch.object(live_smoke.http.client, 'HTTPConnection', return_value=connection), \
                 patch.object(live_smoke.subprocess, 'run', side_effect=subprocess.TimeoutExpired('client', 25)):
                with self.assertRaises(subprocess.TimeoutExpired):
                    live_smoke.run(file, file)
        process.terminate.assert_called_once()
        process.kill.assert_called_once()
        self.assertEqual(process.wait.call_count, 2)
        connection.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
