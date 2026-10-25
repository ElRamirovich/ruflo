#!/usr/bin/env python3
"""Validate one untrusted addition proposal. No dynamic code or external tools."""
import argparse
import json
import re
import sys

LIMIT = 4096
BOUND = 1_000_000


def integer(value):
    if type(value) is not int or not -BOUND <= value <= BOUND:
        raise ValueError('invalid integer')
    return value


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate key')
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError('nonstandard JSON')


def validate(text, expected_a, expected_b):
    """Expected operands must come from the trusted caller, never the model."""
    integer(expected_a)
    integer(expected_b)
    if type(text) is not str or len(text.encode('utf-8')) > LIMIT:
        raise ValueError('input limit')
    text = text.strip()
    if text.startswith('```'):
        match = re.fullmatch(r'```json\r?\n([^`]+)\r?\n```', text)
        if not match:
            raise ValueError('ambiguous fence')
        text = match.group(1)
    try:
        obj = json.loads(text, object_pairs_hook=unique_object, parse_constant=reject_constant)
    except RecursionError as exc:
        raise ValueError('excessive nesting') from exc
    if type(obj) is not dict or set(obj) != {'tool', 'arguments'} or obj['tool'] != 'add':
        raise ValueError('tool rejected')
    args = obj['arguments']
    if type(args) is not dict or set(args) != {'a', 'b'}:
        raise ValueError('arguments rejected')
    a, b = integer(args['a']), integer(args['b'])
    if (a, b) != (expected_a, expected_b):
        raise ValueError('proposal differs from caller intent')
    return {'tool': 'add', 'arguments': {'a': a, 'b': b}}


def process(text, expected_a, expected_b, execute=False):
    if type(execute) is not bool:
        raise ValueError('invalid execution flag')
    proposal = validate(text, expected_a, expected_b)
    result = {'validated': True, 'executed': execute, 'proposal': proposal}
    if execute:
        # Fixed operation: no eval/exec, shell, imports chosen by model or plugins.
        result['result'] = proposal['arguments']['a'] + proposal['arguments']['b']
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--a', required=True, type=int)
    parser.add_argument('--b', required=True, type=int)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args(argv)
    try:
        integer(args.a)
        integer(args.b)
        raw = sys.stdin.buffer.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raise ValueError('input limit')
        print(json.dumps(process(raw.decode('utf-8'), args.a, args.b, args.execute)))
        return 0
    except (ValueError, TypeError, OSError, RecursionError):
        print(json.dumps({'error': 'proposal_rejected', 'executed': False}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
