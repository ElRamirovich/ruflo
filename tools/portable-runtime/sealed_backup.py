"""Experimental whole-file Fernet backups. No keys are generated or saved."""
import os
import base64
from pathlib import Path
import stat
import tempfile
from cryptography.fernet import Fernet
from memory_backup import snapshot, MAX_BYTES

TOKEN_LIMIT = 24 * 1024 * 1024


def bounded_read(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise ValueError('input rejected')
        data = stream.read(limit + 1)
        if len(data) > limit:
            raise ValueError('input limit')
        return data


def private_write(path, data):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def cipher_for(memory_key, backup_key):
    # Separate key material for record and archive protection.
    Fernet(memory_key)
    archive_cipher = Fernet(backup_key)
    if base64.urlsafe_b64decode(memory_key) == base64.urlsafe_b64decode(backup_key):
        raise ValueError('separate keys required')
    return archive_cipher


def seal(source, destination, memory_key, backup_key):
    cipher = cipher_for(memory_key, backup_key)
    destination = Path(destination).absolute()
    if os.path.lexists(destination):
        raise FileExistsError('destination exists')
    with tempfile.TemporaryDirectory(prefix='sealed-memory-', dir=destination.parent) as tmp:
        db, archive = Path(tmp)/'snapshot.db', Path(tmp)/'archive.fernet'
        receipt = snapshot(source, db, memory_key)
        data = bounded_read(db, MAX_BYTES)
        token = cipher.encrypt(data)
        private_write(archive, token)
        if cipher.decrypt(bounded_read(archive, TOKEN_LIMIT)) != data:
            raise ValueError('verification failed')
        os.link(archive, destination)
    return {**receipt, 'whole_file_encrypted': True}


def unseal(source, destination, memory_key, backup_key):
    cipher = cipher_for(memory_key, backup_key)
    destination = Path(destination).absolute()
    if os.path.lexists(destination):
        raise FileExistsError('destination exists')
    data = cipher.decrypt(bounded_read(source, TOKEN_LIMIT))
    if len(data) > MAX_BYTES:
        raise ValueError('database limit')
    with tempfile.TemporaryDirectory(prefix='unsealed-memory-', dir=destination.parent) as tmp:
        db = Path(tmp)/'snapshot.db'
        private_write(db, data)
        return snapshot(db, destination, memory_key)
