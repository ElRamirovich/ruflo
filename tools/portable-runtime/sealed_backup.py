"""Experimental whole-file Fernet backups. No keys are generated or saved."""
import os
import base64
from pathlib import Path
import stat
import tempfile
from cryptography.fernet import Fernet
from memory_backup import snapshot, MAX_BYTES, temporary_directory

TOKEN_LIMIT = 24 * 1024 * 1024


def bounded_read(path, limit):
    before = os.lstat(path)
    reparse = getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400)
    if (not stat.S_ISREG(before.st_mode) or before.st_size > limit
            or getattr(before, 'st_file_attributes', 0) & reparse):
        raise ValueError('input rejected')
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0)
    flags |= getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_size > limit
                or (info.st_dev, info.st_ino) != (before.st_dev, before.st_ino)
                or not info.st_ino):
            raise ValueError('input rejected')
        data = stream.read(limit + 1)
        if len(data) > limit:
            raise ValueError('input limit')
        return data


def private_write(path, data):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, 'O_BINARY', 0), 0o600)
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
    with temporary_directory(destination.parent, 'sealed-memory-') as tmp:
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
    with temporary_directory(destination.parent, 'unsealed-memory-') as tmp:
        db = Path(tmp)/'snapshot.db'
        private_write(db, data)
        return snapshot(db, destination, memory_key)
