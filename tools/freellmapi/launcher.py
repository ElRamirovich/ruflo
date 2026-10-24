#!/usr/bin/env python3
"""Optional FreeLLMAPI environment launcher; offline doctor is the default."""
import argparse
from dataclasses import dataclass
import http.client
import ipaddress
import json
import os
import re
import subprocess
from urllib.parse import urlsplit

DEFAULT_ORIGIN = 'http://127.0.0.1:3001'
# Remove credentials that could route a child to an unrelated paid provider.
CONFLICTING_KEYS = {
    'ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'CLAUDE_CODE_OAUTH_TOKEN',
    'OPENAI_API_KEY', 'OPENROUTER_API_KEY', 'OLLAMA_API_KEY',
    'GOOGLE_API_KEY', 'GEMINI_API_KEY', 'GOOGLE_APPLICATION_CREDENTIALS',
    'ANTHROPIC_BEDROCK_BASE_URL', 'ANTHROPIC_VERTEX_BASE_URL',
    'CLAUDE_CODE_USE_BEDROCK', 'CLAUDE_CODE_USE_VERTEX', 'CLAUDE_CODE_USE_FOUNDRY',
    'ANTHROPIC_FOUNDRY_API_KEY', 'ANTHROPIC_FOUNDRY_RESOURCE',
}


@dataclass(frozen=True)
class Origin:
    url: str
    scheme: str
    host: str
    port: int
    loopback: bool


def validate_origin(value):
    """Require an origin, not /v1, a credential-bearing URL, or an unsafe URL."""
    if not isinstance(value, str) or not value or any(ord(c) <= 32 or ord(c) >= 127 for c in value):
        raise ValueError('Gateway origin must be a nonempty ASCII URL without whitespace.')
    if any(c in value for c in ('\\', '?', '#', '%')):
        raise ValueError('Gateway origin cannot contain escapes, a query, or a fragment.')
    try:
        parsed = urlsplit(value)
        host, port = parsed.hostname, parsed.port
        if parsed.scheme not in {'http', 'https'} or not host or not parsed.netloc:
            raise ValueError
        if parsed.username is not None or parsed.password is not None:
            raise ValueError
        if parsed.path not in {'', '/'} or parsed.netloc.endswith(':'):
            raise ValueError
        if port is not None and not 1 <= port <= 65535:
            raise ValueError
        try:
            address = ipaddress.ip_address(host)
            local = address.is_loopback
        except ValueError:
            if len(host) > 253 or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label)
                                     for label in host.split('.')):
                raise ValueError
            local = host == 'localhost'
        if not local and parsed.scheme != 'https':
            raise ValueError
    except (ValueError, TypeError):
        raise ValueError('Use an HTTP(S) origin without credentials or paths; nonloopback origins require HTTPS.') from None
    actual_port = port if port is not None else (443 if parsed.scheme == 'https' else 80)
    authority = '[' + host + ']' if ':' in host else host
    if port is not None:
        authority += ':' + str(port)
    if parsed.netloc.lower() != authority:
        raise ValueError('Gateway origin contains an ambiguous host or port.')
    return Origin(parsed.scheme + '://' + authority, parsed.scheme, host, actual_port, local)


def probe_local(origin):
    """One local GET only: no proxy environment, redirects, key, or model request."""
    if not origin.loopback:
        raise ValueError('Health probes are restricted to loopback origins.')
    # Avoid resolving a hostname during a loopback-only probe.
    host = '127.0.0.1' if origin.host == 'localhost' else origin.host
    connection_type = http.client.HTTPSConnection if origin.scheme == 'https' else http.client.HTTPConnection
    conn = connection_type(host, origin.port, timeout=3)
    try:
        conn.request('GET', '/api/ping', headers={'Accept': 'application/json'})
        response = conn.getresponse()
        # Do not log/read the response body, send credentials, or follow redirects.
        status = response.status
        return {'attempted': True, 'reachable': True, 'http_status': status,
                'healthy': 200 <= status < 300}
    except (OSError, http.client.HTTPException):
        return {'attempted': True, 'reachable': False, 'http_status': None, 'healthy': False}
    finally:
        conn.close()


def doctor(env, origin, command=None):
    key_present = bool(env.get('FREELLM_API_KEY', '').strip())
    confirmed = env.get('FREELLM_FREE_ONLY_CONFIRMED') == '1'
    return {
        'mode': 'offline doctor; no inference or configuration writes',
        'gateway_origin': origin.url,
        'gateway_is_loopback': origin.loopback,
        'unified_key_present': key_present,
        'free_only_configuration_confirmed': confirmed,
        'launch_guard_satisfied': key_present and confirmed,
        'command_supplied': bool(command),
        'key_validated': False,
        'gateway_and_provider_credentials_verified': False,
        'model_inference_performed': False,
        'limitations': [
            'Free-tier availability and gateway billing configuration are not verified.',
            'This optional launcher does not change the model in the parent chat.',
            'A child command can override its own configuration; this is not a sandbox.',
        ],
    }


def child_environment(parent, origin):
    if parent.get('FREELLM_FREE_ONLY_CONFIRMED') != '1':
        raise ValueError('Launch blocked: confirm free-only gateway configuration with FREELLM_FREE_ONLY_CONFIRMED=1.')
    key = parent.get('FREELLM_API_KEY', '')
    if not key.strip() or any(ord(c) < 33 or ord(c) == 127 for c in key):
        raise ValueError('Launch blocked: a valid unified FREELLM_API_KEY must be provided through the environment.')
    child = dict(parent)
    for name in CONFLICTING_KEYS:
        child.pop(name, None)
    child['RUFLO_PROVIDER'] = 'anthropic'
    child['ANTHROPIC_BASE_URL'] = origin.url
    child['ANTHROPIC_AUTH_TOKEN'] = key
    return child


def launch(command, parent, origin):
    if not command or any(not isinstance(arg, str) or '\x00' in arg for arg in command):
        raise ValueError('Provide a valid command after --.')
    env = child_environment(parent, origin)
    key = env['ANTHROPIC_AUTH_TOKEN']
    if any(key in arg for arg in command):
        raise ValueError('Do not place credentials in command arguments.')
    # No shell expansion and no keys in argv or launcher logs.
    result = subprocess.run(command, env=env, shell=False, check=False)
    return result.returncode if result.returncode >= 0 else 128 - result.returncode


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default=None, help='Gateway origin only; defaults to FREELLM_BASE_URL or loopback port 3001.')
    parser.add_argument('--probe', action='store_true', help='Explicitly GET local /api/ping; no inference.')
    parser.add_argument('--dry-run', action='store_true', help='Offline report only, even when a command is provided.')
    parser.add_argument('command', nargs=argparse.REMAINDER, help='Optional child command after --.')
    args = parser.parse_args(argv)
    try:
        if args.probe and args.dry_run:
            raise ValueError('--dry-run is offline; do not combine it with --probe.')
        env = dict(os.environ)
        origin = validate_origin(args.base_url or env.get('FREELLM_BASE_URL', DEFAULT_ORIGIN))
        command = args.command
        if command:
            if command[0] != '--':
                raise ValueError('Place the child command after an explicit -- separator.')
            command = command[1:]
            if not command:
                raise ValueError('Provide a command after --.')
        if args.probe and command:
            raise ValueError('Run --probe separately from a child command.')
        if args.probe:
            report = doctor(env, origin)
            report['mode'] = 'explicit local health probe; no inference or configuration writes'
            report['probe'] = probe_local(origin)
            print(json.dumps(report, indent=2))
            return 0 if report['probe']['healthy'] else 1
        if not command or args.dry_run:
            print(json.dumps(doctor(env, origin, command), indent=2))
            return 0
        return launch(command, env, origin)
    except ValueError as exc:
        print('FreeLLMAPI: ' + str(exc))
        return 2
    except (OSError, subprocess.SubprocessError):
        # Exceptions can contain argv, environment-derived URLs, or credentials.
        print('FreeLLMAPI: child command could not start; no fallback was attempted.')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
