"""Consistent SQLite snapshots, including committed WAL pages; no private data."""
from contextlib import closing
import importlib.util
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest

import backup

spec = importlib.util.spec_from_file_location('sqlite_snapshot', Path(__file__).with_name('sqlite-snapshot.py'))
snap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snap)


class SQLiteSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'repo'
        self.root.mkdir()
        self.out = self.base / 'backups'
        for args in [('init', '-q'), ('config', 'user.name', 'Test'),
                     ('config', 'user.email', 'test@example.invalid'),
                     ('-c', 'core.hooksPath=/dev/null', 'commit', '--allow-empty', '-qm', 'fixture')]:
            subprocess.run(['git', '-C', str(self.root), *args], check=True, capture_output=True)

    def make_db(self, name='memory.db', value='local data'):
        path = self.root / name
        with closing(sqlite3.connect(path)) as conn:
            conn.execute('CREATE TABLE memory (value TEXT)')
            conn.execute('INSERT INTO memory VALUES (?)', (value,))
            conn.commit()
        return path

    def test_snapshot_restore_and_source_unchanged(self):
        path = self.make_db()
        before = path.read_bytes()
        archive = snap.snapshot(self.root, self.out, ['memory.db'])
        manifest = backup.verify(archive)
        self.assertEqual(manifest['kind'], 'explicit-sqlite-snapshots')
        self.assertEqual(manifest['files'][0]['sqlite_integrity'], 'ok')
        target = self.base / 'restore'
        backup.restore(archive, target, self.root)
        with closing(sqlite3.connect((target / 'memory.db').as_uri() + '?mode=ro', uri=True)) as conn:
            self.assertEqual(conn.execute('PRAGMA integrity_check').fetchall(), [('ok',)])
            self.assertEqual(conn.execute('SELECT value FROM memory').fetchone(), ('local data',))
        self.assertEqual(before, path.read_bytes())
        self.assertEqual(archive.stat().st_mode & 0o777, 0o600)

    def test_committed_wal_rows_are_included_without_uncommitted_rows(self):
        path = self.make_db()
        with closing(sqlite3.connect(path)) as writer:
            writer.execute('PRAGMA journal_mode=WAL')
            writer.execute('PRAGMA wal_autocheckpoint=0')
            writer.execute('INSERT INTO memory VALUES (?)', ('committed wal',))
            writer.commit()
            writer.execute('INSERT INTO memory VALUES (?)', ('not committed',))
            archive = snap.snapshot(self.root, self.out, ['memory.db'])
            writer.rollback()
        target = self.base / 'restore'
        backup.restore(archive, target, self.root)
        with closing(sqlite3.connect(target / 'memory.db')) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM memory').fetchone(), (2,))

    def test_corrupt_database_is_not_published(self):
        (self.root / 'bad.db').write_bytes(b'not a database')
        with self.assertRaises(sqlite3.DatabaseError):
            snap.snapshot(self.root, self.out, ['bad.db'])
        self.assertFalse(list(self.out.glob('*.zip')))

    def test_detected_secret_is_not_published(self):
        self.make_db(value='ghp_' + 'x' * 36)
        with self.assertRaisesRegex(ValueError, 'credential'):
            snap.snapshot(self.root, self.out, ['memory.db'])
        self.assertFalse(list(self.out.glob('*.zip')))

    def test_paths_links_duplicates_and_output_are_rejected(self):
        path = self.make_db()
        (self.root / 'link.db').symlink_to(path)
        for names, output in [(['../outside.db'], self.out), (['link.db'], self.out),
                              (['memory.db', 'memory.db'], self.out), (['missing.db'], self.out),
                              (['memory.db'], self.root / 'copies')]:
            with self.subTest(names=names, output=output):
                with self.assertRaises(ValueError):
                    snap.snapshot(self.root, output, names)

    def test_multiple_databases_and_repeated_runs_are_retained(self):
        self.make_db()
        self.make_db('other.db')
        a = snap.snapshot(self.root, self.out, ['memory.db', 'other.db'])
        b = snap.snapshot(self.root, self.out, ['memory.db', 'other.db'])
        self.assertNotEqual(a, b)
        self.assertTrue(a.exists())
        self.assertEqual(len(backup.verify(b)['files']), 2)


if __name__ == '__main__':
    unittest.main()
