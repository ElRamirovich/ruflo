#!/usr/bin/env python3
"""Offline portability inventory. Does not launch tools or inspect credentials."""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

TOOLS = ("git", "node", "npm", "docker", "ollama")
REQUIRED = (
    "package.json",
    "independent-backup/backup.py",
    "tools/freellmapi/launcher.py",
)


def inventory(root, environ=None, which=None):
    env = os.environ if environ is None else environ
    locate = shutil.which if which is None else which
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("root must be an existing non-symlink directory")
    # Do not open files, traverse directories, resolve links, query Docker,
    # execute Git, load .env, or contact a model/registry/cloud service.
    files = {}
    for relative in REQUIRED:
        path = root
        linked = False
        for part in Path(relative).parts:
            path = path / part
            if path.is_symlink():
                linked = True
                break
        files[relative] = "symlink_review" if linked else (
            "present" if path.is_file() else "missing"
        )
    git_marker = root / ".git"
    report = {
        "schema_version": 1,
        "mode": "offline_metadata_only",
        "python_supported": sys.version_info >= (3, 10),
        "environment": "codespaces" if env.get("CODESPACES") == "true" else "other",
        "git_metadata_marker_present": git_marker.exists() or git_marker.is_symlink(),
        "tools_on_path": {name: bool(locate(name)) for name in TOOLS},
        "project_files": files,
        "next_steps": [],
        "limitations": [
            "Tool presence does not prove version, health, permissions or compatibility.",
            "No credentials, model access, billing, backups or restoration were verified.",
            "No source tree or service data was copied; no migration was performed.",
            "A Git marker does not prove complete history, ownership or repository association.",
            "Cloud runtimes and external models remain external dependencies.",
        ],
    }
    if any(value != "present" for value in files.values()):
        report["next_steps"].append("Review missing/linked project components before transfer.")
    if not report["tools_on_path"]["node"]:
        report["next_steps"].append("Provide a compatible Node runtime for the application.")
    if not report["tools_on_path"]["git"]:
        report["next_steps"].append("Provide Git to preserve and validate repository history.")
    if report["environment"] == "codespaces":
        report["next_steps"].append("Prepare and test another runtime before retiring Codespaces.")
    report["next_steps"].append(
        "Validate backups, service data and secret provisioning separately before migration."
    )
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).absolute().parents[2])
    args = parser.parse_args(argv)
    try:
        report = inventory(args.root)
    except (ValueError, OSError):
        print(json.dumps({"error": "project_root_unavailable"}))
        return 2
    print(json.dumps(report, indent=2))
    # Exit 0 means inventory completed, NOT that migration is safe or complete.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
