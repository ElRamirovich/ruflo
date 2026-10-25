"""Experimental POSIX key files. Trusted parent required; no secret output."""
import argparse
import base64
import json
import os
from pathlib import Path
import stat
from cryptography.fernet import Fernet

NAMES = ('memory.key', 'backup.key')


def private(info, directory=False):
    if info.st_uid != os.geteuid() or info.st_mode & 0o077:
        raise ValueError('insecure ownership or permissions')
    if directory:
        if not stat.S_ISDIR(info.st_mode):raise ValueError('not directory')
    elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError('not private regular file')


def load(directory):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        private(os.fstat(fd), directory=True)
        keys = []
        for name in NAMES:
            child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            with os.fdopen(child, 'rb') as stream:
                private(os.fstat(stream.fileno()))
                key = stream.read(45)
                if len(key) != 44:raise ValueError('invalid key size')
                Fernet(key)
                keys.append(key)
        if base64.urlsafe_b64decode(keys[0]) == base64.urlsafe_b64decode(keys[1]):
            raise ValueError('keys must differ')
        return tuple(keys)
    finally:
        os.close(fd)


def generate(directory):
    # A new directory is mandatory; partial failures are left for manual recovery.
    os.mkdir(directory, mode=0o700)
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        private(os.fstat(fd), directory=True)
        for name in NAMES:
            child = os.open(name, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                            0o600, dir_fd=fd)
            with os.fdopen(child, 'wb') as stream:
                stream.write(Fernet.generate_key())
                stream.flush()
                os.fsync(stream.fileno())
        os.fsync(fd)
    finally:
        os.close(fd)
    load(directory)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation', choices=['generate','check'])
    p.add_argument('--directory',type=Path,required=True)
    args=p.parse_args()
    try:
        if args.operation=='generate':generate(args.directory)
        else:load(args.directory)
        print(json.dumps({'key_files_valid':True,'keys_printed':False}))
        return 0
    except (OSError, ValueError, TypeError):
        print(json.dumps({'error':'key_operation_failed','keys_printed':False}))
        return 2


if __name__=='__main__':raise SystemExit(main())
