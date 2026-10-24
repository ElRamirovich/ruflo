"""Isolated integration tests: no network, API keys, or project dependencies."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

spec = importlib.util.spec_from_file_location('backup', Path(__file__).with_name('backup.py'))
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'repo'
        self.root.mkdir()
        self.out = self.base / 'backups'
        self.git('init', '-q')
        self.git('config', 'user.name', 'Backup Test')
        self.git('config', 'user.email', 'test@example.invalid')
        (self.root / 'code.txt').write_text('original')
        self.git('add', '.')
        self.git('-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'fixture')

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True,
                              capture_output=True).stdout

    def test_roundtrip_dirty_untracked_history_and_modes(self):
        (self.root / 'code.txt').write_text('edited')
        script = self.root / 'run.sh'
        script.write_text('#!/bin/sh\nexit 0\n')
        script.chmod(0o755)
        archive = backup.create(self.root, self.out)
        manifest = backup.verify(archive)
        self.assertTrue(manifest['history'])
        target = self.base / 'restored'
        backup.restore(archive, target, self.root)
        self.assertEqual((target / 'code.txt').read_text(), 'edited')
        self.assertEqual(script.read_bytes(), (target / 'run.sh').read_bytes())
        self.assertTrue((target / 'run.sh').stat().st_mode & 0o100)
        self.assertEqual(archive.stat().st_mode & 0o777, 0o600)
        cloned = self.base / 'history-clone'
        subprocess.run(['git', 'clone', '-q', str(target / '.backup-history.bundle'), str(cloned)],
                       check=True, capture_output=True)
        self.assertEqual((cloned / 'code.txt').read_text(), 'original')

    def test_sensitive_sqlite_links_ignored_and_deleted(self):
        (self.root / '.env').write_text('PRIVATE=never-copy')
        (self.root / 'data.bin').write_bytes(b'SQLite format 3\0stuff')
        (self.root / 'secret.txt').write_bytes(b'-----BEGIN ' + b'PRIVATE KEY-----' + b'\n' + b'A' * 64)
        (self.root / 'link').symlink_to(self.root / 'code.txt')
        (self.root / '.gitignore').write_text('ignored.txt\n')
        (self.root / 'ignored.txt').write_text('private')
        (self.root / 'code.txt').unlink()
        archive = backup.create(self.root, self.out)
        m = backup.verify(archive)
        included = {x['name'] for x in m['files']}
        for name in ['.env', 'data.bin', 'secret.txt', 'link', 'ignored.txt', 'code.txt']:
            self.assertNotIn('files/' + name, included)
        self.assertIn('ignored.txt', m['ignored_paths_not_backed_up'])
        self.assertIn({'path': 'code.txt', 'reason': 'tracked-deletion'}, m['excluded'])

    def test_sensitive_history_fails_closed(self):
        (self.root / '.env').write_text('SECRET=example')
        self.git('add', '.env')
        self.git('-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'sensitive fixture')
        with self.assertRaisesRegex(ValueError, 'Sensitive filename'):
            backup.create(self.root, self.out)
        self.assertFalse(list(self.out.glob('*.zip')))
        self.assertFalse(backup.verify(backup.create(self.root, self.out, True))['history'])

    def test_no_restore_over_existing_or_source(self):
        archive = backup.create(self.root, self.out)
        target = self.base / 'existing'
        target.mkdir()
        with self.assertRaises(FileExistsError):
            backup.restore(archive, target, self.root)
        with self.assertRaises(ValueError):
            backup.restore(archive, self.root / 'restore', self.root)
        self.assertEqual((self.root / 'code.txt').read_text(), 'original')

    def test_output_inside_source_rejected(self):
        with self.assertRaises(ValueError):
            backup.create(self.root, self.root / 'backups')

    def test_restore_symlink_parent_rejected(self):
        archive = backup.create(self.root, self.out)
        (self.base / 'link').symlink_to(self.base, target_is_directory=True)
        with self.assertRaises(ValueError):
            backup.restore(archive, self.base / 'link' / 'restored', self.root)

    def make_archive(self, names, entries=None):
        path = self.base / 'malicious.zip'
        with zipfile.ZipFile(path, 'w') as z:
            for name, data in names:
                z.writestr(name, data)
            if entries is not None:
                z.writestr('manifest.json', json.dumps({'schema': 1, 'files': entries,
                                                       'history': False, 'head': 'a' * 40}))
        return path

    def test_traversal_and_absolute_paths(self):
        for name in ['../escape', '/absolute', 'files/../escape', 'files\\evil', 'files/C:evil']:
            with self.subTest(name=name):
                a = self.make_archive([(name, b'bad')], [])
                with self.assertRaises(ValueError):
                    backup.restore(a, self.base / 'restored', self.root)
                self.assertFalse((self.base / 'restored').exists())

    def test_corrupt_sha_missing_and_extra(self):
        e = {'name': 'files/a', 'size': 3, 'sha256': hashlib.sha256(b'yes').hexdigest()}
        for names in [[('files/a', b'bad')], [], [('files/a', b'yes'), ('extra', b'x')]]:
            a = self.make_archive(names, [e])
            with self.assertRaises((ValueError, KeyError)):
                backup.verify(a)

    def test_symlink_archive_member_rejected(self):
        a = self.base / 'symlink.zip'
        with zipfile.ZipFile(a, 'w') as z:
            info = zipfile.ZipInfo('files/link')
            info.external_attr = 0o120777 << 16
            z.writestr(info, '../outside')
            z.writestr('manifest.json', '{}')
        with self.assertRaises(ValueError):
            backup.verify(a)

    def test_source_mutation_does_not_publish(self):
        original = backup.read_regular
        count = 0
        def changing(path):
            nonlocal count
            result = original(path)
            if path.name == 'code.txt':
                count += 1
                if count == 1:
                    path.write_text('changed during backup')
            return result
        with patch.object(backup, 'read_regular', side_effect=changing):
            with self.assertRaisesRegex(ValueError, 'Source changed'):
                backup.create(self.root, self.out, True)
        self.assertFalse(list(self.out.glob('*.zip')))

    def test_duplicates_and_file_directory_collision(self):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            a = self.make_archive([('files/a', b'x'), ('files/a', b'x')], [])
        with self.assertRaises(ValueError):
            backup.verify(a)
        entries = [{'name': n, 'size': 1, 'sha256': hashlib.sha256(b'x').hexdigest()}
                   for n in ['files/a', 'files/a/b']]
        a = self.make_archive([(e['name'], b'x') for e in entries], entries)
        with self.assertRaises(ValueError):
            backup.verify(a)


    def test_env_example_audited_and_preserved(self):
        (self.root / '.env.example').write_text('API_KEY=replace-me')
        self.git('add', '.env.example')
        self.git('-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'example')
        a = backup.create(self.root, self.out)
        m = backup.verify(a)
        self.assertIn('files/.env.example', {x['name'] for x in m['files']})

    def test_deleted_source_reappears_during_backup(self):
        (self.root / 'code.txt').unlink()
        (self.root / 'z-last.txt').write_text('last')
        original = backup.read_regular
        def recreating(path):
            data = original(path)
            if path.name == 'z-last.txt':
                (self.root / 'code.txt').write_text('reappeared')
            return data
        with patch.object(backup, 'read_regular', side_effect=recreating):
            with self.assertRaisesRegex(ValueError, 'reappeared'):
                backup.create(self.root, self.out, True)
        self.assertFalse(list(self.out.glob('*.zip')))

    def test_mode_change_rejected(self):
        original = backup.read_regular
        def changing(path):
            result = original(path)
            if path.name == 'code.txt':
                path.chmod(0o700 if result[1] != 0o700 else 0o600)
            return result
        with patch.object(backup, 'read_regular', side_effect=changing):
            with self.assertRaisesRegex(ValueError, 'Source changed'):
                backup.create(self.root, self.out, True)
        self.assertFalse(list(self.out.glob('*.zip')))

    def test_head_change_rejected(self):
        original = backup.read_regular
        changed = False
        def changing(path):
            nonlocal changed
            result = original(path)
            if not changed:
                changed = True
                self.git('-c', 'core.hooksPath=/dev/null', 'commit', '--allow-empty', '-qm', 'new head')
            return result
        with patch.object(backup, 'read_regular', side_effect=changing):
            with self.assertRaisesRegex(ValueError, 'Git refs changed'):
                backup.create(self.root, self.out, True)
        self.assertFalse(list(self.out.glob('*.zip')))

    def test_false_history_claim_rejected(self):
        a = self.base / 'false-history.zip'
        with zipfile.ZipFile(a, 'w') as z:
            z.writestr('manifest.json', json.dumps({'schema': 1, 'files': [],
                                                   'history': True, 'head': 'a' * 40}))
        with self.assertRaisesRegex(ValueError, 'History flag'):
            backup.verify(a)

    def test_mapped_restore_collision_rejected_before_creation(self):
        a = self.base / 'collision.zip'
        names = ['files/.backup-history.bundle', 'history.bundle']
        entries = [{'name': n, 'size': 1, 'sha256': hashlib.sha256(b'x').hexdigest()}
                   for n in names]
        with zipfile.ZipFile(a, 'w') as z:
            for name in names:
                z.writestr(name, b'x')
            z.writestr('manifest.json', json.dumps({'schema': 1, 'files': entries,
                                                   'history': True, 'head': 'a' * 40}))
        with self.assertRaisesRegex(ValueError, 'destination collision'):
            backup.restore(a, self.base / 'restored', self.root)
        self.assertFalse((self.base / 'restored').exists())


    def test_marker_literal_is_not_a_private_key(self):
        marker = b'-----BEGIN ' + b'PRIVATE KEY-----'
        self.assertFalse(backup.sensitive(b"x = b'" + marker + b"'\n"))
        self.assertTrue(backup.sensitive(marker + b'\n' + b'A' * 64))
        self.assertTrue(backup.sensitive(marker + b'\\n' + b'A' * 64))
        self.assertTrue(backup.sensitive(json.dumps((marker + b'\r\n' + b'A' * 64).decode()).encode()))
        self.assertTrue(backup.sensitive(b'-----BEGIN EC ' + b'PRIVATE KEY-----\n' + b'A' * 64))

    def test_audit_names_and_reasons_never_secret_values(self):
        secret = 'ghp_' + 'a' * 36
        (self.root / 'secret.txt').write_text(secret)
        self.git('add', 'secret.txt')
        self.git('-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'fixture')
        report = backup.audit_history(self.root)
        output = json.dumps(report)
        self.assertNotIn(secret, output)
        finding = next(x for x in report['findings'] if x['path'] == 'secret.txt')
        self.assertIn('github-token', finding['reasons'])
        self.assertEqual(len(finding['object']), 40)
        self.assertTrue(report['complete'])
        with self.assertRaisesRegex(ValueError, 'object='):
            backup.create(self.root, self.out)

    def test_audit_limit_and_clean_history(self):
        report = backup.audit_history(self.root)
        self.assertTrue(report['complete'])
        self.assertEqual(report['findings'], [])
        for i in range(2):
            (self.root / ('secret' + str(i))).write_text('ghp_' + str(i) * 36)
        self.git('add', '.')
        self.git('-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'fixtures')
        limited = backup.audit_history(self.root, limit=1)
        self.assertEqual(len(limited['findings']), 1)
        self.assertFalse(limited['complete'])

    def test_source_with_marker_can_be_backed_up_with_history(self):
        marker = '-----BEGIN ' + 'PRIVATE KEY-----'
        (self.root / 'fixture.py').write_text('example = ' + repr(marker) + '\n')
        self.git('add', 'fixture.py')
        self.git('-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'literal marker')
        self.assertTrue(backup.verify(backup.create(self.root, self.out))['history'])


if __name__ == '__main__':
    unittest.main()
