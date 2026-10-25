#!/usr/bin/env python3
"""Explicit synthetic inference smoke test; requires reviewed local Linux files."""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import resource
import secrets
import socket
import stat
import subprocess
import sys
import tempfile
import time

MODEL_SHA = 'ed5fa30c487b282ec156c29062f1222e5c20875a944ac98289dbd242e947f747'
SERVER_SHA = 'e48cc61e37e1ed15649f8c39789df5eb03d2e549df1f2c0b1835a26378a72b41'


def digest(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(descriptor, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > 200_000_000:
            raise ValueError('not a bounded regular file')
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (90, 90))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def run(server, model):
    server, model = server.resolve(strict=True), model.resolve(strict=True)
    if digest(server) != SERVER_SHA or digest(model) != MODEL_SHA:
        raise ValueError('unreviewed files')
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    # Local port races remain possible. This uses only synthetic data and an ephemeral key.
    key = secrets.token_hex(32)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='portable-inference-') as directory:
        home = Path(directory)
        keyfile = home / 'key'
        keyfile.write_text(key, encoding='ascii')
        keyfile.chmod(0o600)
        env = {'HOME': directory, 'TMPDIR': directory, 'PATH': '/usr/bin:/bin',
               'LANG': 'C.UTF-8', 'OMP_NUM_THREADS': '2'}
        command = [str(server), '-m', str(model), '--host', '127.0.0.1',
                   '--port', str(port), '--offline', '--no-webui',
                   '--api-key-file', str(keyfile), '--alias', 'local-smoke',
                   '-t', '2', '-tb', '2', '-c', '1024', '-b', '128',
                   '-ub', '128', '-np', '1', '-ngl', '0', '-n', '256']
        process = subprocess.Popen(command, env=env, cwd=directory,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, preexec_fn=limits)
        try:
            deadline = started + 30
            while True:
                if process.poll() is not None:
                    raise RuntimeError('server exited')
                connection = http.client.HTTPConnection('127.0.0.1', port, timeout=1)
                try:
                    connection.request('GET', '/health')
                    ready = connection.getresponse().status == 200
                except OSError:
                    ready = False
                finally:
                    connection.close()
                if ready:
                    break
                if time.monotonic() >= deadline:
                    raise TimeoutError('startup')
                time.sleep(0.1)
            client_env = {**env, 'AGENT_LOCAL_PROCESSING_CONFIRMED': '1',
                          'AGENT_API_KEY': key}
            result = subprocess.run(
                [sys.executable, str(Path(__file__).with_name('client.py').resolve()),
                 '--base-url', f'http://127.0.0.1:{port}/v1', '--model', 'local-smoke', '--request'],
                input=b'What is two plus two? Answer briefly.', capture_output=True,
                env=client_env, cwd=directory, timeout=25, check=True)
            answer = json.loads(result.stdout)
            if process.poll() is not None or not isinstance(answer.get('content'), str) or not answer['content'].strip():
                raise ValueError('invalid inference result')
            return {'real_inference': True, 'synthetic_prompt_only': True,
                    'agent_quality_validated': False,
                    'elapsed_seconds': round(time.monotonic() - started, 3),
                    'model_sha256': MODEL_SHA, 'server_sha256': SERVER_SHA,
                    'client_result': answer}
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server', type=Path, required=True)
    parser.add_argument('--model', type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.server, args.model), ensure_ascii=True))
    except Exception:
        print(json.dumps({'error': 'local_inference_smoke_failed'}))
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
