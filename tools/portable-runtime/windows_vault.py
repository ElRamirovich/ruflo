"""Windows-only local key custody and recovery for the portable receipt database.

No application network calls, generated shell commands, deletion of existing
user data, or password arguments. Owned temporary test/snapshot files are removed.
Only use recovery archives created by this application, in trusted directories.
"""
import argparse
import base64
import ctypes
import getpass
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import warnings

from cryptography.fernet import Fernet
from encrypted_memory import EncryptedMemory
from memory_backup import snapshot
from recovery_package import pack, unpack, validate
from sealed_backup import bounded_read, private_write, seal, unseal
import windows_dpapi


ACL_SCRIPT = r'''
$ErrorActionPreference = 'Stop'
try {
    $path = $env:MEU_AGENTE_ACL_PATH
    $item = Get-Item -LiteralPath $path -Force
    if (-not $item.PSIsContainer) { throw 'directory required' }
    $acl = Get-Acl -LiteralPath $path
    $sidType = [System.Security.Principal.SecurityIdentifier]
    $user = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    if ($acl.GetOwner($sidType).Value -ne $user) { throw 'owner rejected' }
    $rules = @($acl.GetAccessRules($true, $true, $sidType))
    if ($rules.Count -ne 2) { throw 'rules rejected' }
    $seen = @()
    foreach ($rule in $rules) {
        $sid = $rule.IdentityReference.Value
        if ($sid -notin @($user, 'S-1-5-18') -or $sid -in $seen) { throw 'identity rejected' }
        if ($rule.AccessControlType -ne 'Allow' -or
            $rule.FileSystemRights -ne [System.Security.AccessControl.FileSystemRights]::FullControl -or
            $rule.InheritanceFlags -ne [System.Security.AccessControl.InheritanceFlags]'ContainerInherit,ObjectInherit' -or
            $rule.PropagationFlags -ne [System.Security.AccessControl.PropagationFlags]::None) {
            throw 'rights rejected'
        }
        $seen += $sid
    }
    [Console]::Out.Write('PRIVATE')
    exit 0
} catch {
    [Console]::Out.Write('REJECTED')
    exit 2
}
'''


def system_directory():
    if sys.platform != 'win32':
        raise OSError('Windows required')
    kernel = ctypes.WinDLL('kernel32.dll',use_last_error=True,winmode=0x800)
    function = kernel.GetSystemDirectoryW
    function.argtypes = [ctypes.c_wchar_p,ctypes.c_uint32]
    function.restype = ctypes.c_uint32
    buffer = ctypes.create_unicode_buffer(32768)
    size = function(buffer,len(buffer))
    if not 0 < size < len(buffer):raise OSError('system directory unavailable')
    return Path(buffer.value)


def local_path(value, directory=False):
    if sys.platform != 'win32':raise OSError('Windows required')
    path = Path(value).absolute()
    if str(path).startswith('\\\\'):
        raise ValueError('local path required')
    kernel = ctypes.WinDLL('kernel32.dll',use_last_error=True,winmode=0x800)
    drive_type = kernel.GetDriveTypeW
    drive_type.argtypes = [ctypes.c_wchar_p]
    drive_type.restype = ctypes.c_uint32
    if drive_type(path.anchor) != 3:raise ValueError('fixed local disk required')
    # Check ancestors from the drive root before touching a descendant.
    for component in (*reversed(path.parents),path):
        info = component.lstat()
        is_kind = stat.S_ISDIR(info.st_mode) if directory or component != path else stat.S_ISREG(info.st_mode)
        if not is_kind or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('path rejected')
    return path


def check_directory(directory):
    path = local_path(directory,directory=True)
    system = system_directory()
    executable = system/'WindowsPowerShell/v1.0/powershell.exe'
    env = {'SystemRoot':str(system.parent),
           'WINDIR':str(system.parent),
           'PSModulePath':str(executable.parent/'Modules'),
           'MEU_AGENTE_ACL_PATH':str(path)}
    encoded = base64.b64encode(ACL_SCRIPT.encode('utf-16-le')).decode('ascii')
    result = subprocess.run([str(executable), '-NoLogo', '-NoProfile', '-NonInteractive',
                             '-EncodedCommand', encoded], env=env, cwd=system,
                            capture_output=True, timeout=15)
    if result.returncode != 0 or result.stdout != b'PRIVATE' or result.stderr:
        raise ValueError('private directory check failed')
    return path


def ask_password(confirm=False):
    if not sys.stdin.isatty():
        raise ValueError('interactive terminal required')
    with warnings.catch_warnings():
        warnings.simplefilter('error', getpass.GetPassWarning)
        password = getpass.getpass('Senha de recuperacao (nao aparece): ')
        if not 20 <= len(password) <= 256:
            raise ValueError('password length')
        if confirm and getpass.getpass('Repita a senha: ') != password:
            raise ValueError('password mismatch')
    return password


def new_directory(directory):
    directory = Path(directory).absolute()
    check_directory(directory.parent)
    directory.mkdir(exist_ok=False)
    check_directory(directory)
    return directory


def store_keys(directory, keys):
    data = json.dumps(validate(keys), sort_keys=True).encode('ascii')
    blob = windows_dpapi.protect(data)
    if windows_dpapi.unprotect(blob) != data:
        raise ValueError('local protection failed')
    private_write(directory/'keys.dpapi', blob)
    if windows_dpapi.unprotect(bounded_read(directory/'keys.dpapi', 16384)) != data:
        raise ValueError('stored keys verification failed')


def load_keys(directory):
    directory = check_directory(directory)
    if bounded_read(directory/'READY', 32) != b'portable-vault-v1\n':
        raise ValueError('incomplete vault')
    data = windows_dpapi.unprotect(bounded_read(directory/'keys.dpapi', 16384))
    return validate(json.loads(data))


def initialize(directory, password):
    # Generate the portable package BEFORE making a persistent directory.
    keys = {name:Fernet.generate_key().decode('ascii') for name in ('memory','backup')}
    package = pack(keys, password)
    directory = new_directory(directory)
    store_keys(directory, keys)
    private_write(directory/'recovery.7z', package)
    if unpack(bounded_read(directory/'recovery.7z',65536), password) != keys:
        raise ValueError('stored recovery verification failed')
    memory = EncryptedMemory(directory/'memory.db', keys['memory'].encode(), create=True)
    memory.close()
    seal(directory/'memory.db', directory/'initial.fernet', keys['memory'].encode(), keys['backup'].encode())
    with tempfile.TemporaryDirectory(prefix='verify-', dir=directory) as tmp:
        unseal(directory/'initial.fernet', Path(tmp)/'restored.db', keys['memory'].encode(), keys['backup'].encode())
    private_write(directory/'READY', b'portable-vault-v1\n')
    return directory


def check_vault(directory):
    keys = load_keys(directory)
    directory = Path(directory).absolute()
    with tempfile.TemporaryDirectory(prefix='verify-', dir=directory) as tmp:
        return snapshot(directory/'memory.db',Path(tmp)/'verified.db',keys['memory'].encode())


def backup(directory, destination):
    keys = load_keys(directory)
    destination = Path(destination).absolute()
    check_directory(destination.parent)
    return seal(Path(directory)/'memory.db',destination,keys['memory'].encode(),keys['backup'].encode())


def recover(package, archive, directory, password):
    package = local_path(package)
    archive = local_path(archive)
    package_data = bounded_read(package,65536)
    keys = unpack(package_data,password)
    directory = new_directory(directory)
    # Authenticate and validate the backup before storing recovered keys.
    unseal(archive,directory/'memory.db',keys['memory'].encode(),keys['backup'].encode())
    store_keys(directory,keys)
    private_write(directory/'recovery.7z',package_data)
    private_write(directory/'READY',b'portable-vault-v1\n')
    return directory


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=['init','check','backup','recover'])
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--package',type=Path)
    parser.add_argument('--archive',type=Path)
    args = parser.parse_args(argv)
    try:
        if sys.platform != 'win32':raise ValueError('Windows required')
        if args.operation == 'init':
            if any((args.output,args.package,args.archive)):raise ValueError('unexpected arguments')
            check_directory(args.directory.absolute().parent)
            if os.path.lexists(args.directory):raise FileExistsError('destination exists')
            initialize(args.directory,ask_password(confirm=True))
        elif args.operation == 'recover':
            if not args.package or not args.archive or args.output:raise ValueError('missing arguments')
            check_directory(args.directory.absolute().parent)
            if os.path.lexists(args.directory):raise FileExistsError('destination exists')
            recover(args.package,args.archive,args.directory,ask_password())
        elif args.operation == 'backup':
            if not args.output or args.package or args.archive:raise ValueError('invalid arguments')
            backup(args.directory,args.output)
        else:
            if any((args.output,args.package,args.archive)):raise ValueError('unexpected arguments')
            check_vault(args.directory)
        print(json.dumps({'ok':True,'operation':args.operation,'network_used':False}))
        return 0
    except (Exception, KeyboardInterrupt):
        # Partial new directories are retained for inspection, never overwritten.
        print(json.dumps({'ok':False,'error':'vault_operation_failed','existing_data_overwritten':False}))
        return 2


if __name__ == '__main__':raise SystemExit(main())
