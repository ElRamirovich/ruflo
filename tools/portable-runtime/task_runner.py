#!/usr/bin/env python3
"""One bounded addition task. Offline unless explicitly requested."""
import argparse
import http.client
import json
import os
import re
import sys
import action_gate
import client


def run(a, b, model, base_url='http://127.0.0.1:11434/v1', request=False,
        execute=False, token='', confirmed=False, transport=None):
    action_gate.integer(a)
    action_gate.integer(b)
    if any(type(flag) is not bool for flag in (request, execute, confirmed)):
        raise ValueError('invalid flag')
    client.endpoint(base_url)
    if not isinstance(model, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}', model):
        raise ValueError('invalid model')
    if execute and not request:
        raise ValueError('execution requires request')
    if not request:
        return {'mode': 'offline', 'network_called': False, 'executed': False}
    if not confirmed:
        raise ValueError('local processing must be reviewed')
    schema = {'tool': 'add', 'arguments': {'a': a, 'b': b}}
    prompt = 'Return exactly this JSON object, without explanation or additional fields: ' + json.dumps(schema)
    response = client.request_chat(base_url, model, prompt, token, factory=transport)
    return action_gate.process(response, a, b, execute)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--a', type=int, required=True)
    p.add_argument('--b', type=int, required=True)
    p.add_argument('--model', required=True)
    p.add_argument('--base-url', default='http://127.0.0.1:11434/v1')
    p.add_argument('--request', action='store_true')
    p.add_argument('--execute', action='store_true')
    a = p.parse_args(argv)
    try:
        result = run(a.a, a.b, a.model, a.base_url, a.request, a.execute,
                     os.environ.get('AGENT_API_KEY', '') if a.request else '',
                     os.environ.get('AGENT_LOCAL_PROCESSING_CONFIRMED') == '1' if a.request else False)
        print(json.dumps(result))
        return 0
    except (ValueError, TypeError, OSError, http.client.HTTPException,
            KeyError, IndexError, RecursionError):
        print(json.dumps({'error': 'task_rejected', 'executed': False}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
