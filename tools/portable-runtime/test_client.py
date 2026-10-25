import contextlib
import io
import json
import unittest
from unittest.mock import patch
import client


class Response:
    status = 200
    body = b'{"choices":[{"message":{"content":"synthetic ok"}}]}'
    def read(self, limit):
        self.limit = limit
        return self.body[:limit]


class Connection:
    def __init__(self, *args, **kwargs):
        self.args, self.kwargs, self.calls, self.closed = args, kwargs, [], False
        self.response = Response()
    def request(self, *args, **kwargs):
        self.calls.append((args, kwargs))
    def getresponse(self):
        return self.response
    def close(self):
        self.closed = True


class Tests(unittest.TestCase):
    def test_strict_literal_endpoints(self):
        self.assertEqual(client.endpoint('http://127.0.0.1:11434/v1'), ('http', '127.0.0.1', 11434))
        self.assertEqual(client.endpoint('https://[::1]/v1'), ('https', '::1', 443))
        for url in ['http://localhost/v1', 'http://example.com/v1', 'http://127.0.0.1:0/v1',
                    'http://x@127.0.0.1/v1', 'http://127.0.0.1/v1?', 'http://127.0.0.1/v1#',
                    'http://127.0.0.1:99999/v1', 'http://127.0.0.1/v1/','http://127.0.0.1:/v1']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                client.endpoint(url)

    def test_offline_does_not_open_network_or_stdin(self):
        out = io.StringIO()
        with patch('client.http.client.HTTPConnection', side_effect=AssertionError), patch('client.sys.stdin', None), contextlib.redirect_stdout(out):
            self.assertEqual(client.main(['--model', 'test']), 0)
        self.assertFalse(json.loads(out.getvalue())['network_called'])

    def test_confirmation_rejects_before_reading_prompt(self):
        with patch.dict('client.os.environ', {}, clear=True), patch('client.sys.stdin', None), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(client.main(['--model', 'test', '--request']), 2)

    def test_exact_bounded_request_and_close(self):
        conn = Connection('127.0.0.1', 1234)
        factory = unittest.mock.Mock(return_value=conn)
        text = client.request_chat('http://127.0.0.1:1234/v1', 'test:small', 'synthetic', 'SENTINEL', factory)
        self.assertEqual(text, 'synthetic ok')
        factory.assert_called_once_with('127.0.0.1', 1234, timeout=15)
        args, kwargs = conn.calls[0]
        self.assertEqual(args, ('POST', '/v1/chat/completions'))
        self.assertEqual(kwargs['headers']['Authorization'], 'Bearer SENTINEL')
        body = json.loads(kwargs['body'])
        self.assertFalse(body['stream'])
        self.assertNotIn('tools', body)
        self.assertEqual(conn.response.limit, 65537)
        self.assertTrue(conn.closed)

    def test_rejected_server_data_never_retry_and_closes(self):
        for status, body in [(302, b'secret'), (429, b'secret'), (200, b'x'*65537),
                             (200,b'{"choices":[]}'),(200,b'{}'),(200,b'[]'),
                             (200,b'{"choices":[{"message":{"content":null,"tool_calls":[]}}]}'),
                             (200,b'{"choices":[{"message":{"content":"  "}}]}')]:
            conn = Connection(); conn.response.status = status; conn.response.body = body
            with self.subTest(status=status, length=len(body)), self.assertRaises((ValueError,KeyError,IndexError,TypeError)):
                client.request_chat('http://127.0.0.1/v1','test','synthetic',factory=lambda *a,**k:conn)
            self.assertTrue(conn.closed)
            self.assertEqual(len(conn.calls), 1)

    def test_utf8_byte_limits_and_header_injection(self):
        for prompt, token in [('é'*4097,''), ('synthetic','key\r\nInjected: yes')]:
            factory = unittest.mock.Mock(side_effect=AssertionError('network must remain unopened'))
            with self.assertRaises(ValueError):
                client.request_chat('http://127.0.0.1/v1','test',prompt,token,factory)
            factory.assert_not_called()

    def test_main_redacts_server_errors(self):
        out=io.StringIO()
        stdin=io.TextIOWrapper(io.BytesIO(b'SECRET PROMPT'))
        with patch.dict('client.os.environ',{'AGENT_LOCAL_PROCESSING_CONFIRMED':'1','AGENT_API_KEY':'SECRET KEY'},clear=True), patch('client.sys.stdin',stdin), patch('client.request_chat',side_effect=ValueError('SECRET RESPONSE')),contextlib.redirect_stdout(out):
            self.assertEqual(client.main(['--model','test','--request']),2)
        self.assertNotIn('SECRET',out.getvalue())

    def test_deep_json_is_rejected_without_raw_error(self):
        conn = Connection()
        conn.response.body = b'[' * 2000 + b'0' + b']' * 2000
        out = io.StringIO()
        stdin = io.TextIOWrapper(io.BytesIO(b'synthetic'))
        with patch.dict('client.os.environ',{'AGENT_LOCAL_PROCESSING_CONFIRMED':'1'},clear=True), patch('client.sys.stdin',stdin), patch('client.http.client.HTTPConnection',return_value=conn), contextlib.redirect_stdout(out):
            self.assertEqual(client.main(['--model','test','--request']),2)
        self.assertEqual(json.loads(out.getvalue())['error'], 'request_or_configuration_rejected')
        self.assertTrue(conn.closed)


if __name__ == '__main__':
    unittest.main()
