import os
import sys
import subprocess
from database import DB_DIR, ADMIN_DB_PATH, USERS_DB_PATH, EXAMS_DB_PATH, SCORES_DB_PATH, CONFIG_DB_PATH, PROGRESS_DB_PATH
import tempfile
import shutil


FILENAME = None
if sys.platform.startswith("win"):
    FILENAME = "sshpass_win.exe"
elif sys.platform.startswith("linux"):
    FILENAME = "sshpass_linux"
elif sys.platform.startswith("darwin"):
    FILENAME = "sshpass_darwin"
else:
    raise Exception("Unsupported platform")

def get_resource_base():
    """
    返回资源目录的实际路径
    - 开发环境: ./resources
    - PyInstaller: sys._MEIPASS/resources
    - Nuitka macOS app bundle: main.app/Contents/MacOS/resources
    """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "resources")
    print(sys.executable)
    exe_dir = os.path.dirname(sys.executable)
    resources_dir = os.path.join(exe_dir, "resources")
    if os.path.exists(resources_dir):
        return resources_dir

    return os.path.abspath("resources")


def load_binary():
    """
    返回 sshpass 二进制文件路径，并设置可执行权限
    """
    base = get_resource_base()
    bin_path = os.path.join(base, FILENAME)
    if not os.path.exists(bin_path):
        raise FileNotFoundError(f"Cannot find binary: {bin_path}")
    os.chmod(bin_path, 0o755)
    return bin_path


SSHPASS_PATH = load_binary()
if os.path.exists(SSHPASS_PATH):
    print(f"Found sshpass binary: {SSHPASS_PATH}")
else:
    print(f"Error: sshpass binary not found at {SSHPASS_PATH}")

def _run_ssh(ip, username, remote_cmd, ssh_password=None):
    if ssh_password:
        cmd = [SSHPASS_PATH, '-p', ssh_password, 'ssh', '-o', 'StrictHostKeyChecking=no', f'{username}@{ip}', remote_cmd]
    else:
        cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', f'{username}@{ip}', remote_cmd]
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
    remote_dir = _expand_remote_tilde(remote_dir, ip, username, ssh_password)
    local_files = [SCORES_DB_PATH, EXAMS_DB_PATH, USERS_DB_PATH, CONFIG_DB_PATH, PROGRESS_DB_PATH]
    if include_admin:
        local_files.append(ADMIN_DB_PATH)
    else:
        if ssh_password:
            cmd = [SSHPASS_PATH, '-p', ssh_password, 'ssh'] + [f'{username}@{ip}'] + [
                'rm', '-f', _remote_join(remote_dir, os.path.basename(ADMIN_DB_PATH))]
        else:
            cmd = ['ssh', f'{username}@{ip}',
             'rm', '-f', _remote_join(remote_dir, os.path.basename(ADMIN_DB_PATH))]
        subprocess.run(cmd, check=True)
    code_mk, out_mk, err_mk = _ensure_remote_dir(ip, username, remote_dir, ssh_password)
    if code_mk != 0:
        return code_mk, out_mk, f"Failed to create remote directory '{remote_dir}': {err_mk}"
    # Compose rsync command
    if ssh_password:
        cmd = [SSHPASS_PATH, '-p', ssh_password, 'rsync', '-avz', '-e', 'ssh -o StrictHostKeyChecking=no'] + local_files + [f'{username}@{ip}:{remote_dir}/']
    else:
        cmd = ['rsync', '-avz', '-e', 'ssh -o StrictHostKeyChecking=no'] + local_files + [f'{username}@{ip}:{remote_dir}/']
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr

def rsync_pull_scores(ip, username, remote_dir, local_dir, ssh_password=None):
    """Pull scores.db from remote directory to local_dir using rsync"""
    os.makedirs(local_dir, exist_ok=True)
    remote_dir = _expand_remote_tilde(remote_dir, ip, username, ssh_password)
    remote_scores = _remote_join(remote_dir, 'scores.db')
    exists = _check_remote_file_exists(ip, username, remote_scores, ssh_password)
    if not exists:
        return 1, '', f'Remote file not found: {remote_scores}'
    if ssh_password:
        cmd = [SSHPASS_PATH, '-p', ssh_password, 'rsync', '-avz', '-e', 'ssh -o StrictHostKeyChecking=no', f'{username}@{ip}:{remote_scores}', local_dir]
    else:
        cmd = ['rsync', '-avz', '-e', 'ssh -o StrictHostKeyChecking=no', f'{username}@{ip}:{remote_scores}', local_dir]
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr
