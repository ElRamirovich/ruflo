#!/usr/bin/env python3
"""Offline diagnostics only: no inference, network, installs, or state writes."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
MAX_READ = 4 * 1024 * 1024


def read_small(path):
    if path.name.lower().startswith('.env') or path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_READ:
        raise ValueError('unsupported diagnostic file')
    return path.read_text(encoding='utf-8')


def object_file(path):
    try:
        value = json.loads(read_small(path))
        return (value, True) if isinstance(value, dict) else ({}, False)
    except (OSError, ValueError, UnicodeError):
        return {}, False


def google_marker(path):
    try:
        source = read_small(path)
        return 'Google Gemini was selected' in source and 'generativelanguage.googleapis.com' in source
    except (OSError, ValueError, UnicodeError):
        return False


def process_candidates(root):
    """Candidate process count only; do not expose argv, environments, or tokens."""
    proc = Path('/proc')
    if not proc.is_dir():
        return None
    count = 0
    try:
        processes = list(proc.iterdir())
    except OSError:
        return None
    for p in processes:
        if not p.name.isdecimal() or int(p.name) == os.getpid():
            continue
        try:
            parts = (p / 'cmdline').read_bytes().split(b'\0')
            args = [os.fsdecode(x) for x in parts if x]
            if not args:
                continue
            binary = Path(args[0]).name
            if binary not in {'node', 'nodejs', 'ruflo', 'claude-flow'}:
                continue
            # A process must reference this checkout and a CLI entry, not merely
            # a shell command string containing the project's name.
            local_cli = any(str(root) in arg and Path(arg).name in
                            {'cli.js', 'mcp-server.js', 'index.js', 'ruflo', 'claude-flow'}
                            for arg in args[1:4])
            if local_cli:
                count += 1
        except (OSError, ValueError):
            continue
    return count


def diagnose(root):
    root = root.resolve()
    cli = root / 'v3/@claude-flow/cli'
    source = cli / 'src/mcp-tools/agent-execute-core.ts'
    built = cli / 'dist/src/mcp-tools/agent-execute-core.js'
    entry = cli / 'dist/src/index.js'
    key_env = any(bool(os.environ.get(k, '').strip()) for k in ('GOOGLE_API_KEY', 'GEMINI_API_KEY'))
    config_paths = [root / 'claude-flow.config.json', root / '.claude-flow/config.json']
    if os.environ.get('CLAUDE_FLOW_CONFIG'):
        config_paths.append(Path(os.environ['CLAUDE_FLOW_CONFIG']))
    config_exists, config_ok, providers = False, False, []
    for path in config_paths:
        if path.exists():
            config_exists = True
            config, config_ok = object_file(path)
            agents = config.get('agents', {})
            providers = config.get('agents.providers', agents.get('providers', []) if isinstance(agents, dict) else [])
            break
    google_configs = [p for p in providers if isinstance(p, dict) and p.get('name') == 'google'
                      and p.get('enabled') is not False] if isinstance(providers, list) else []
    config_key = any(isinstance(p.get('apiKey'), str) and bool(p['apiKey'].strip()) for p in google_configs)
    registry_path = root / '.claude-flow/agents/store.json'
    registry, registry_ok = object_file(registry_path)
    records = registry.get('agents', {})
    records = list(records.values()) if isinstance(records, dict) else []
    google_agents = [a for a in records if isinstance(a, dict) and a.get('provider') == 'google']
    node = shutil.which('node')
    node_version = None
    if node:
        try:
            result = subprocess.run([node, '--version'], capture_output=True, text=True,
                                    timeout=5, check=True)
            version = result.stdout.strip()
            if version.startswith('v') and all(c.isdigit() or c == '.' for c in version[1:]):
                node_version = version
        except (OSError, subprocess.SubprocessError):
            pass
    return {
        'mode': 'offline read-only diagnostics; no external requests or inference',
        'source_google_dispatch_present': google_marker(source),
        'built_cli_entry_present': entry.is_file(),
        'built_google_dispatch_present': google_marker(built),
        'node_available': node is not None,
        'node_version': node_version,
        'google_key_present_in_environment': key_env,
        'provider_environment_is_google': os.environ.get('RUFLO_PROVIDER', '').strip().lower() == 'google',
        'project_config_present': config_exists,
        'project_config_parse_ok': config_ok,
        'enabled_google_provider_in_config': bool(google_configs),
        'google_key_present_in_config': config_key,
        'google_model_explicitly_configured': bool(os.environ.get('GOOGLE_DEFAULT_MODEL', '').strip()) or
            any(bool(p.get('model')) for p in google_configs),
        'project_agent_registry_present': registry_path.is_file(),
        'project_agent_registry_parse_ok': registry_ok,
        'google_agent_records': len(google_agents),
        'google_agent_records_marked_busy': sum(a.get('status') == 'busy' for a in google_agents),
        'local_cli_process_candidates': process_candidates(root),
        'live_agent_confirmed': False,
        'limitations': [
            'Credential presence does not prove validity or a free billing tier.',
            'Dotenv files and OS credential stores are not read by this diagnostic.',
            'Source support does not prove the installed CLI build contains the change.',
            'Registry busy states and matching processes do not prove inference or useful work.',
            'External/global CLI processes and other workspaces may not be detected.',
            'Model availability and a live Gemini request were not tested.',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(diagnose(args.root), indent=2, ensure_ascii=True))


if __name__ == '__main__':
    main()
