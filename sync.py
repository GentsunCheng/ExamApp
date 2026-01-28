import os
import sys
import subprocess
import socket
from database import (
    DB_DIR, 
    ADMIN_DB_PATH, 
    USERS_DB_PATH, 
    EXAMS_DB_PATH, 
    SCORES_DB_PATH, 
    CONFIG_DB_PATH, 
    PROGRESS_DB_PATH,
    RESOURCE_PATH,
    DB_VERFILE_PATH,
)

from utils import load_binary


FILENAME = None
if sys.platform.startswith("win"):
    FILENAME = "sshpass_win.exe"
elif sys.platform.startswith("linux"):
    FILENAME = "sshpass_linux"
elif sys.platform.startswith("darwin"):
    FILENAME = "sshpass_darwin"
else:
    raise Exception("Unsupported platform")


SSHPASS_PATH = load_binary(filename=FILENAME)
if os.path.exists(SSHPASS_PATH):
    print(f"Found sshpass binary: {SSHPASS_PATH}")
else:
    print(f"Error: sshpass binary not found at {SSHPASS_PATH}")


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        local_ip = s.getsockname()[0]
    except Exception as err_net:
        print(f"{err_net}")
        local_ip = '127.0.0.1'
    finally:
        s.close()
    return local_ip

def _parse_ip_port(ip_str):
    """
    解析 IP 和端口，格式为 ip:port 或 ip
    返回 (ip, port)，默认为 22
    """
    if ':' in ip_str:
        parts = ip_str.split(':')
        if len(parts) == 2:
            return parts[0], parts[1]
    return ip_str, '22'

def _is_port_open(ip, port, timeout=3):
    """
    检查目标 IP 的端口是否可连接
    """
    try:
        with socket.create_connection((ip, int(port)), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

def _run_ssh(ip, username, remote_cmd, ssh_password=None):
    ip_addr, port = _parse_ip_port(ip)
    if ssh_password:
        cmd = [SSHPASS_PATH, '-p', ssh_password, 'ssh', '-p', port, '-o', 'StrictHostKeyChecking=no', f'{username}@{ip_addr}', remote_cmd]
    else:
        cmd = ['ssh', '-p', port, '-o', 'StrictHostKeyChecking=no', f'{username}@{ip_addr}', remote_cmd]
    return subprocess.run(cmd, capture_output=True, text=True)

 
def _get_remote_cwd(ip, username, ssh_password=None):
    try:
        r = _run_ssh(ip, username, 'pwd', ssh_password)
        out = (r.stdout or '').strip()
        if out:
            return out
    except Exception:
        pass
    try:
        r = _run_ssh(ip, username, 'powershell -NoProfile -Command "$pwd.Path"', ssh_password)
        out = (r.stdout or '').strip()
        if out:
            return out
    except Exception:
        pass
    try:
        r = _run_ssh(ip, username, 'cmd /c cd', ssh_password)
        out = (r.stdout or '').strip()
        if out:
            return out
    except Exception:
        pass
    return ''

def _ensure_remote_dir(ip, username, remote_dir, ssh_password=None):
    cmd1 = f"test -d {remote_dir} || mkdir -p {remote_dir}"
    r1 = _run_ssh(ip, username, cmd1, ssh_password)
    if r1.returncode == 0:
        return 0, r1.stdout, r1.stderr
    cmd2 = f"powershell -NoProfile -Command \"if (!(Test-Path -Path '{remote_dir}')) {{ New-Item -ItemType Directory -Path '{remote_dir}' }}\""
    r2 = _run_ssh(ip, username, cmd2, ssh_password)
    return r2.returncode, r2.stdout, r2.stderr

def _check_remote_file_exists(ip, username, remote_path, ssh_password=None):
    cmd1 = f"test -f {remote_path} && echo 'exists' || echo 'not found'"
    r1 = _run_ssh(ip, username, cmd1, ssh_password)
    if r1.returncode == 0 and 'exists' in (r1.stdout or ''):
        return True
    cmd2 = f"powershell -NoProfile -Command \"if (Test-Path -Path '{remote_path}') {{ Write-Output 'exists' }} else {{ Write-Output 'not found' }}\""
    r2 = _run_ssh(ip, username, cmd2, ssh_password)
    return (r2.returncode == 0) and ('exists' in (r2.stdout or ''))

def _expand_remote_tilde(remote_dir, ip, username, ssh_password=None):
    if remote_dir and remote_dir.startswith('~'):
        base = _get_remote_cwd(ip, username, ssh_password) or ''
        if base:
            return base + remote_dir[1:]
    return remote_dir

def _remote_join(remote_dir, *parts):
    sep = '\\' if ('\\' in remote_dir and '/' not in remote_dir) else '/'
    out = remote_dir.rstrip('/\\')
    for p in parts:
        out += sep + str(p).strip('/\\')
    return out

def rsync_push(ip, username, remote_dir, ssh_password=None, include_admin=False):
    """Push selected local databases to remote directory"""
    ip_addr, port = _parse_ip_port(ip)
    if not _is_port_open(ip_addr, port):
        return 1, '', f"Connection failed: {ip_addr}:{port} is unreachable."
    if ip_addr == get_local_ip() or ip_addr == '127.0.0.1':
        return 304, f"Skip local device: {ip_addr}:{port}", ''
    remote_dir = _expand_remote_tilde(remote_dir, ip, username, ssh_password)
    local_files = [SCORES_DB_PATH, EXAMS_DB_PATH, USERS_DB_PATH, CONFIG_DB_PATH, PROGRESS_DB_PATH, RESOURCE_PATH, DB_VERFILE_PATH]
    if include_admin:
        local_files.append(ADMIN_DB_PATH)
    else:
        if ssh_password:
            cmd = [SSHPASS_PATH, '-p', ssh_password, 'ssh', '-p', port] + [f'{username}@{ip_addr}'] + [
                'rm', '-f', _remote_join(remote_dir, os.path.basename(ADMIN_DB_PATH))]
        else:
            cmd = ['ssh', '-p', port, f'{username}@{ip_addr}',
             'rm', '-f', _remote_join(remote_dir, os.path.basename(ADMIN_DB_PATH))]
        subprocess.run(cmd, check=True)
    code_mk, out_mk, err_mk = _ensure_remote_dir(ip, username, remote_dir, ssh_password)
    if code_mk != 0:
        return code_mk, out_mk, f"Failed to create remote directory '{remote_dir}': {err_mk}"
    # Compose rsync command
    ssh_opts = f'ssh -p {port} -o StrictHostKeyChecking=no'
    if ssh_password:
        cmd = [SSHPASS_PATH, '-p', ssh_password, 'rsync', '-avz', '-e', ssh_opts] + local_files + [f'{username}@{ip_addr}:{remote_dir}/']
    else:
        cmd = ['rsync', '-avz', '-e', ssh_opts] + local_files + [f'{username}@{ip_addr}:{remote_dir}/']
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr

def rsync_pull_scores(ip, username, remote_dir, local_dir, ssh_password=None):
    """Pull scores.db from remote directory to local_dir using rsync"""
    ip_addr, port = _parse_ip_port(ip)
    if not _is_port_open(ip_addr, port):
        return 1, '', f"Connection failed: {ip_addr}:{port} is unreachable."
    os.makedirs(local_dir, exist_ok=True)
    remote_dir = _expand_remote_tilde(remote_dir, ip, username, ssh_password)
    remote_scores = _remote_join(remote_dir, 'scores.db')
    exists = _check_remote_file_exists(ip, username, remote_scores, ssh_password)
    if not exists:
        return 1, '', f'Remote file not found: {remote_scores}'
    ssh_opts = f'ssh -p {port} -o StrictHostKeyChecking=no'
    if ssh_password:
        cmd = [SSHPASS_PATH, '-p', ssh_password, 'rsync', '-avz', '-e', ssh_opts, f'{username}@{ip_addr}:{remote_scores}', local_dir]
    else:
        cmd = ['rsync', '-avz', '-e', ssh_opts, f'{username}@{ip_addr}:{remote_scores}', local_dir]
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr
