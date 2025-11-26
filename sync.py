import os
import sys
import subprocess
from database import DB_PATH
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


def is_dev():
    return not hasattr(sys, "_MEIPASS")

def extract_resources():
    bundle_path = os.path.join(sys._MEIPASS, "resources")
    temp_dir = tempfile.mkdtemp(prefix="examapp_")
    for fname in os.listdir(bundle_path):
        src = os.path.join(bundle_path, fname)
        dst = os.path.join(temp_dir, fname)
        shutil.copy(src, dst)
    return temp_dir


def load_binary():
    if is_dev():
        base = os.path.abspath("resources")
    else:
        base = extract_resources()
    bin_path = os.path.join(base, FILENAME)
    os.chmod(bin_path, 0o755)
    return bin_path


SSHPASS_PATH = load_binary()
if os.path.exists(SSHPASS_PATH):
    print(f"Found sshpass binary: {SSHPASS_PATH}")
else:
    print(f"Error: sshpass binary not found at {SSHPASS_PATH}")
def rsync_push(ip, username, remote_path, ssh_password=None):
    """Push database file to remote device using rsync"""
    # First, create remote directory if it doesn't exist
    remote_dir = os.path.dirname(remote_path)
    
    if ssh_password:
        # Create remote directory using SSH with password
        mkdir_cmd = [SSHPASS_PATH, '-p', ssh_password, 'ssh', '-o', 'StrictHostKeyChecking=no', 
                     f'{username}@{ip}', f'mkdir -p {remote_dir}']
        mkdir_result = subprocess.run(mkdir_cmd, capture_output=True, text=True)
        
        if mkdir_result.returncode != 0:
            return mkdir_result.returncode, mkdir_result.stdout, f"Failed to create remote directory: {mkdir_result.stderr}"
        
        # Use sshpass for password authentication
        cmd = [SSHPASS_PATH, '-p', ssh_password, 'rsync', '-avz', '-e', 'ssh -o StrictHostKeyChecking=no', 
               DB_PATH, f'{username}@{ip}:{remote_path}']
    else:
        # Create remote directory using SSH with key authentication
        mkdir_cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', f'{username}@{ip}', f'mkdir -p {remote_dir}']
        mkdir_result = subprocess.run(mkdir_cmd, capture_output=True, text=True)
        
        if mkdir_result.returncode != 0:
            return mkdir_result.returncode, mkdir_result.stdout, f"Failed to create remote directory: {mkdir_result.stderr}"
        
        # Use key-based authentication
        cmd = ['rsync', '-avz', '-e', 'ssh -o StrictHostKeyChecking=no', 
               DB_PATH, f'{username}@{ip}:{remote_path}']
    
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr

def rsync_pull(ip, username, remote_path, local_dir, ssh_password=None):
    """Pull database file from remote device using rsync"""
    os.makedirs(local_dir, exist_ok=True)
    
    if ssh_password:
        # Check if remote file exists using SSH with password
        check_cmd = [SSHPASS_PATH, '-p', ssh_password, 'ssh', '-o', 'StrictHostKeyChecking=no', 
                     f'{username}@{ip}', f'test -f {remote_path} && echo "exists" || echo "not found"']
        check_result = subprocess.run(check_cmd, capture_output=True, text=True)
        
        if check_result.returncode != 0 or 'not found' in check_result.stdout:
            return 1, '', f'Remote file not found: {remote_path}'
        
        # Use sshpass for password authentication
        cmd = [SSHPASS_PATH, '-p', ssh_password, 'rsync', '-avz', '-e', 'ssh -o StrictHostKeyChecking=no', 
               f'{username}@{ip}:{remote_path}', local_dir]
    else:
        # Check if remote file exists using SSH with key authentication
        check_cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', f'{username}@{ip}', 
                     f'test -f {remote_path} && echo "exists" || echo "not found"']
        check_result = subprocess.run(check_cmd, capture_output=True, text=True)
        
        if check_result.returncode != 0 or 'not found' in check_result.stdout:
            return 1, '', f'Remote file not found: {remote_path}'
        
        # Use key-based authentication
        cmd = ['rsync', '-avz', '-e', 'ssh -o StrictHostKeyChecking=no', 
               f'{username}@{ip}:{remote_path}', local_dir]
    
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr