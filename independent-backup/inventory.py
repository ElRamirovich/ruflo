#!/usr/bin/env python3
"""Inventário somente leitura do backup independente."""
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "independent-backup" / "inventory-report.json"

EXCLUDED_DIRS = {
    ".git", "node_modules", "independent-backup",
    "coverage", ".cache", "__pycache__", ".turbo"
}
SECRET_NAMES = {
    ".env", ".env.local", ".env.development",
    ".env.production", ".env.test", "id_rsa", "id_ed25519"
}
SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx")
TEMP_SUFFIXES = (".pyc", ".log", ".tmp", ".temp", ".tsbuildinfo")
DB_SUFFIXES = (
    ".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm",
    ".sqlite-wal", ".sqlite-shm"
)

def git_paths(*args):
    try:
        result = subprocess.run(
            ["git", *args, "-z"], cwd=ROOT, check=True,
            capture_output=True
        )
        return {
            item.decode("utf-8", "surrogateescape")
            for item in result.stdout.split(b"\0") if item
        }
    except subprocess.CalledProcessError:
        return set()

tracked = git_paths("ls-files")
untracked = git_paths("ls-files", "--others", "--exclude-standard")
ignored = git_paths("ls-files", "--others", "--ignored", "--exclude-standard")

def classify(rel, is_tracked):
    path = Path(rel)
    name = path.name.lower()
    parts = set(path.parts)

    # Não excluir conteúdo versionado só por estar em dist/build.
    if "node_modules" in parts:
        return "excluded_dependency_review"
    if name in SECRET_NAMES or (
        name.startswith(".env.") and not name.endswith(".example")
    ) or name.endswith(SECRET_SUFFIXES):
        return "excluded_sensitive_name_review"
    if name.endswith(DB_SUFFIXES):
        return "excluded_database_review"
    if name.endswith(TEMP_SUFFIXES):
        return "excluded_temporary"
    if not is_tracked and any(
        part in {"dist", "build", "coverage", ".cache", "__pycache__", ".turbo"}
        for part in parts
    ):
        return "excluded_regenerable_review"
    return "candidate"

records, errors = [], []
totals = {}

for current, dirs, files in os.walk(ROOT, followlinks=False):
    base = Path(current)
    # Registra links simbólicos de diretório sem seguir seus destinos.
    for directory in list(dirs):
        link = base / directory
        if directory in EXCLUDED_DIRS:
            dirs.remove(directory)
        elif link.is_symlink():
            rel = link.relative_to(ROOT).as_posix()
            records.append({
                "path": rel,
                "category": "symlink",
                "target": os.readlink(link),
                "git_status": "tracked" if rel in tracked else "other",
                "size": 0
            })
            dirs.remove(directory)

    for name in files:
        path = base / name
        rel = path.relative_to(ROOT).as_posix()

        if rel == "independent-backup/inventory-report.json":
            continue

        try:
            if path.is_symlink():
                records.append({
                    "path": rel, "category": "symlink",
                    "target": os.readlink(path), "size": 0
                })
                continue
            if not path.is_file():
                continue

            size = path.stat().st_size
            is_tracked = rel in tracked
            category = classify(rel, is_tracked)

            if is_tracked:
                status = "tracked"
            elif rel in ignored:
                status = "ignored"
            elif rel in untracked:
                status = "untracked"
            else:
                status = "other"

            record = {
                "path": rel, "category": category,
                "git_status": status, "size": size
            }

            if category == "candidate":
                digest = hashlib.sha256()
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(chunk)
                record["sha256"] = digest.hexdigest()

            records.append(record)
            totals[category] = totals.get(category, 0) + size

        except OSError as exc:
            errors.append({"path": rel, "error": type(exc).__name__})

report = {
    "schema_version": 2,
    "created_utc": datetime.now(timezone.utc).isoformat(),
    "mode": "read-only inventory; no backup created",
    "file_count": len(records),
    "totals_bytes_by_category": totals,
    "errors_count": len(errors),
    "files": sorted(records, key=lambda item: item["path"]),
    "errors": errors
}
OUT.write_text(
    json.dumps(report, indent=2, ensure_ascii=True) + "\n",
    encoding="utf-8"
)

print("Inventário atualizado; nenhum backup foi criado.")
print(f"Entradas listadas: {len(records)}")
print(f"Erros de leitura: {len(errors)}")
for category, size in sorted(totals.items()):
    count = sum(1 for item in records if item["category"] == category)
    print(f"{category}: {count} arquivos, {size / 1024**2:.2f} MiB")
print(f"Relatório: {OUT.relative_to(ROOT)}")
