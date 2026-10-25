"""Experimental portable 7z key package; synthetic use pending deployment review."""
import io
import json
import base64
import py7zr
from py7zr.io import BytesIOFactory
from cryptography.fernet import Fernet

LIMIT = 65536


def validate(keys):
    if type(keys) is not dict or set(keys) != {'memory','backup'}:
        raise ValueError('invalid keys')
    for key in keys.values():
        if type(key) is not str or len(key)!=44:raise ValueError('invalid key')
        Fernet(key.encode('ascii'))
    if base64.urlsafe_b64decode(keys['memory']) == base64.urlsafe_b64decode(keys['backup']):
        raise ValueError('keys must differ')
    return keys


def check(password):
    if py7zr.__version__ != '1.1.4':raise ValueError('unreviewed library version')
    if type(password) is not str or not 20 <= len(password) <= 256:
        raise ValueError('password length')


def pack(keys, password):
    check(password);validate(keys)
    output=io.BytesIO()
    with py7zr.SevenZipFile(output,'w',password=password,header_encryption=True) as archive:
        archive.writestr(json.dumps(keys).encode(),'recovery.json')
    data=output.getvalue()
    if len(data)>LIMIT:raise ValueError('package limit')
    if unpack(data,password)!=keys:raise ValueError('verification failed')
    return data


def unpack(data, password):
    check(password)
    if type(data) is not bytes or len(data)>LIMIT:raise ValueError('package limit')
    factory=BytesIOFactory(limit=4096)
    with py7zr.SevenZipFile(io.BytesIO(data),'r',password=password,max_extract_size=4096) as archive:
        if archive.getnames()!=['recovery.json']:raise ValueError('unexpected member')
        member=archive.list()[0]
        if not member.is_file or member.is_directory or member.is_symlink or member.uncompressed>4096:
            raise ValueError('invalid member type or size')
        if any(f.is_junction or f.is_symlink for f in archive.files):
            raise ValueError('links rejected')
        archive.extractall(factory=factory)
    content=factory.get('recovery.json').read()
    if len(content)>4096:raise ValueError('content limit')
    def unique(pairs):
        obj={}
        for key,value in pairs:
            if key in obj:raise ValueError('duplicate key')
            obj[key]=value
        return obj
    return validate(json.loads(content,object_pairs_hook=unique))
