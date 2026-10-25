"""Real loopback HTTP integration, synthetic responses only; no model inference."""
import contextlib
import http.server
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import unittest

CLIENT = Path(__file__).with_name('client.py')


@contextlib.contextmanager
def server(status=200, body=None):
    requests = []
    payload = body if body is not None else json.dumps({
        'choices': [{'message': {'content': 'synthetic integration ok'}}]
    }).encode()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            # Record redirect-to-GET too, so an unexpected follow cannot hide.
            requests.append({'method': 'GET', 'path': self.path})
            self.send_response(200)
            self.send_header('Content-Length', '0')
            self.end_headers()

        def do_POST(self):
            length = int(self.headers.get('Content-Length', '0'))
            if length > 16384:
                self.send_error(413)
                return
            requests.append({'method': 'POST', 'path': self.path,
                             'authorization': self.headers.get('Authorization'),
                             'body': json.loads(self.rfile.read(length))})
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(payload)))
            if status == 302:
                self.send_header('Location', '/unexpected-redirect')
            self.end_headers()
            try:
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *_):
            pass

    httpd = http.server.HTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield 'http://127.0.0.1:%d/v1' % httpd.server_port, requests
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)
        if thread.is_alive():
            raise RuntimeError('test server did not stop')


def invoke(base):
    # No credentials from the parent are passed to the subprocess.
    env = {'AGENT_LOCAL_PROCESSING_CONFIRMED': '1',
           'AGENT_API_KEY': 'SYNTHETIC-KEY-NOT-A-CREDENTIAL',
           'HTTP_PROXY': 'http://127.0.0.1:1',
           'HTTPS_PROXY': 'http://127.0.0.1:1',
           'ALL_PROXY': 'http://127.0.0.1:1'}
    # Needed by Python subprocesses on Windows; contains no API credentials.
    if 'SYSTEMROOT' in os.environ:
        env['SYSTEMROOT'] = os.environ['SYSTEMROOT']
    return subprocess.run([sys.executable, str(CLIENT), '--base-url', base,
                           '--model', 'synthetic-test-model', '--request'],
                          input=b'PUBLIC SYNTHETIC PROMPT', capture_output=True,
                          env=env, timeout=20)


class HTTPIntegrationTests(unittest.TestCase):
    def test_subprocess_http_roundtrip_without_proxy_or_framework(self):
        with server() as (base, calls):
            result = invoke(base)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['content'], 'synthetic integration ok')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]['path'], '/v1/chat/completions')
        self.assertEqual(calls[0]['authorization'], 'Bearer SYNTHETIC-KEY-NOT-A-CREDENTIAL')
        self.assertEqual(calls[0]['body']['messages'], [
            {'role': 'user', 'content': 'PUBLIC SYNTHETIC PROMPT'}])
        self.assertEqual(result.stderr, b'')

    def test_redirect_and_rate_limit_rejected_without_retry(self):
        for status in (302, 429):
            with self.subTest(status=status), server(status, b'PRIVATE SERVER ERROR') as (base, calls):
                result = invoke(base)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(len(calls), 1)
            self.assertNotIn(b'PRIVATE', result.stdout + result.stderr)
            self.assertNotIn(b'SYNTHETIC-KEY', result.stdout + result.stderr)

    def test_oversized_response_fails_without_publishing_body(self):
        with server(body=b'PRIVATE'+b'x'*65537) as (base, calls):
            result = invoke(base)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(len(calls), 1)
        self.assertNotIn(b'PRIVATE', result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
