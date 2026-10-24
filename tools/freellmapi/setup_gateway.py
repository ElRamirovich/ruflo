#!/usr/bin/env python3
"""Start an optional pinned local gateway, without adding model credentials."""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess

IMAGE = 'ghcr.io/tashfeenahmed/freellmapi@sha256:b4723c688f1d272a8a9e745b649221f6c44f3050c35e20ac31456855e74cf50b'
CONTAINER = 'ruflo-freellmapi'
VOLUME = 'ruflo-freellmapi-data'
CONFIG = Path.home() / '.config' / 'ruflo-freellmapi'


def docker(*args, check=True):
    return subprocess.run(['docker', *args], capture_output=True, text=True,
                          check=check, timeout=45)


def prepare_env(directory):
    directory = Path(os.path.abspath(directory))
    for path in [directory, *directory.parents]:
        if path.is_symlink():
            raise ValueError('Symlink rejected in private configuration path')
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if directory.stat().st_mode & 0o077:
        raise ValueError('Configuration directory must be private (mode 700)')
    path = directory / 'server.env'
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    except FileExistsError:
        if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
            raise ValueError('Existing gateway configuration is not a private regular file')
        data = path.read_text()
        expected = {'ENCRYPTION_KEY', 'PORT', 'NODE_ENV', 'ALLOWED_HOSTS', 'FREELLMAPI_INSTALL_METHOD'}
        fields = dict(line.split('=', 1) for line in data.splitlines() if line)
        if (set(fields) != expected or not re.fullmatch('[0-9a-f]{64}', fields.get('ENCRYPTION_KEY', ''))
                or fields.get('PORT') != '3001' or fields.get('NODE_ENV') != 'production'
                or fields.get('ALLOWED_HOSTS') != 'localhost'
                or fields.get('FREELLMAPI_INSTALL_METHOD') != 'docker'):
            raise ValueError('Existing configuration differs; inspect privately without overwriting it')
        return path
    with os.fdopen(fd, 'w') as stream:
        stream.write('ENCRYPTION_KEY=' + secrets.token_hex(32) + '\nPORT=3001\n'
                     'NODE_ENV=production\nALLOWED_HOSTS=localhost\nFREELLMAPI_INSTALL_METHOD=docker\n')
    return path


def start(directory=CONFIG):
    if not shutil.which('docker'):
        raise ValueError('Docker is required in the development environment')
    docker('info')
    # Never replace, restart or inspect secrets from an existing container.
    existing = docker('container', 'inspect', '--format', '{{.State.Status}}', CONTAINER, check=False)
    if existing.returncode == 0:
        raise ValueError('Named container already exists; no existing container was changed')
    old_volume = docker('volume', 'inspect', '--format', '{{.Name}}', VOLUME, check=False)
    if old_volume.returncode == 0:
        raise ValueError('Named data volume already exists; preserve its original encryption key and review it privately')
    docker('image', 'inspect', '--format', '{{.Id}}', IMAGE)
    with socket.socket() as sock:
        if sock.connect_ex(('127.0.0.1', 3001)) == 0:
            raise ValueError('Loopback port 3001 is already in use')
    env_file = prepare_env(directory)
    docker('volume', 'create', VOLUME)
    docker('run', '-d', '--pull=never', '--name', CONTAINER, '--restart=no', '--user', 'node',
           '--cap-drop=ALL', '--security-opt', 'no-new-privileges:true',
           '--pids-limit', '256', '--memory', '768m', '--cpus', '1',
           '--env-file', str(env_file), '-p', '127.0.0.1:3001:3001',
           '-v', VOLUME + ':/app/server/data', IMAGE)
    return {'container': CONTAINER, 'image': IMAGE, 'origin': 'http://127.0.0.1:3001',
            'started': True, 'inference_performed': False, 'provider_keys_configured': False,
            'administrator_setup_required': True, 'docker_loopback_binding': True,
            'codespaces_port_visibility_verified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start', action='store_true', help='Explicitly start the local Docker service')
    args = parser.parse_args()
    try:
        if args.start:
            print(json.dumps(start(), indent=2))
        else:
            print(json.dumps({'mode': 'offline; no Docker commands or writes',
                              'docker_executable_present': bool(shutil.which('docker')),
                              'image': IMAGE, 'origin': 'http://127.0.0.1:3001',
                              'inference_performed': False}, indent=2))
    except (OSError, ValueError, subprocess.SubprocessError):
        # Do not expose Docker stderr/env-file contents or setup/login codes.
        raise SystemExit('Gateway setup did not complete; inspect local state without printing secrets. Existing data was not deleted.')


if __name__ == '__main__':
    main()
