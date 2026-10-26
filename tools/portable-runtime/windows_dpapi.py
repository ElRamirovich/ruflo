"""Windows CurrentUser DPAPI for small bytes; no storage, ACL or CLI.

Normally tied to the Windows user/profile and machine, not portable key custody.
Fixed entropy is domain separation, not a secret. Native buffers are cleared;
Python bytes and caller-owned copies cannot be reliably erased by this module.
"""
import ctypes
import hashlib
import hmac
import os
import struct

MAX_DATA = 8192
MAX_BLOB = 16384
_MAGIC = b'PORTABLE-DPAPI\x01'
_ENTROPY = b'portable-agent/recovery/current-user/v1'
_UI_FORBIDDEN = 0x1
_SYSTEM32 = 0x800
_HEADER = len(_MAGIC) + 4 + 32


class _DataBlob(ctypes.Structure):
    _fields_ = [('cbData', ctypes.c_uint32),
                ('pbData', ctypes.POINTER(ctypes.c_ubyte))]


def _validate(data, limit):
    if type(data) is not bytes or not 1 <= len(data) <= limit:
        raise ValueError('invalid DPAPI input')


def _crypt(data, protect_data):
    if os.name != 'nt':
        raise OSError('Windows DPAPI unavailable')
    # Search the system directory only, not the working directory or PATH.
    crypt32 = ctypes.WinDLL('crypt32.dll', use_last_error=True, winmode=_SYSTEM32)
    kernel32 = ctypes.WinDLL('kernel32.dll', use_last_error=True, winmode=_SYSTEM32)
    blob_pointer = ctypes.POINTER(_DataBlob)
    protect_fn = crypt32.CryptProtectData
    protect_fn.argtypes = [blob_pointer, ctypes.c_wchar_p, blob_pointer,
                          ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, blob_pointer]
    protect_fn.restype = ctypes.c_int
    unprotect_fn = crypt32.CryptUnprotectData
    unprotect_fn.argtypes = [blob_pointer, ctypes.POINTER(ctypes.c_wchar_p), blob_pointer,
                            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, blob_pointer]
    unprotect_fn.restype = ctypes.c_int
    free_fn = kernel32.LocalFree
    free_fn.argtypes = [ctypes.c_void_p]
    free_fn.restype = ctypes.c_void_p
    incoming = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    entropy_bytes = (ctypes.c_ubyte * len(_ENTROPY)).from_buffer_copy(_ENTROPY)
    source = _DataBlob(len(data), incoming)
    entropy = _DataBlob(len(_ENTROPY), entropy_bytes)
    output = _DataBlob()
    try:
        fn = protect_fn if protect_data else unprotect_fn
        # No LOCAL_MACHINE flag and no interactive prompt or description output.
        ok = fn(ctypes.byref(source), None, ctypes.byref(entropy), None, None,
                _UI_FORBIDDEN, ctypes.byref(output))
        if not ok:
            raise OSError('DPAPI operation failed')
        limit = MAX_BLOB if protect_data else MAX_DATA + _HEADER
        if not output.pbData or not 1 <= output.cbData <= limit:
            raise ValueError('invalid DPAPI output')
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        ctypes.memset(incoming, 0, len(incoming))
        if output.pbData:
            ctypes.memset(output.pbData, 0, output.cbData)
            free_fn(ctypes.cast(output.pbData, ctypes.c_void_p))


def protect(data: bytes) -> bytes:
    _validate(data, MAX_DATA)
    frame = _MAGIC + struct.pack('!I', len(data)) + hashlib.sha256(data).digest() + data
    return _crypt(frame, True)


def unprotect(blob: bytes) -> bytes:
    _validate(blob, MAX_BLOB)
    frame = _crypt(blob, False)
    if len(frame) < _HEADER or not frame.startswith(_MAGIC):
        raise ValueError('invalid DPAPI envelope')
    length = struct.unpack('!I', frame[len(_MAGIC):len(_MAGIC) + 4])[0]
    expected = frame[len(_MAGIC) + 4:_HEADER]
    data = frame[_HEADER:]
    if (not 1 <= length <= MAX_DATA or len(data) != length
            or not hmac.compare_digest(expected, hashlib.sha256(data).digest())):
        raise ValueError('invalid DPAPI envelope')
    return data
