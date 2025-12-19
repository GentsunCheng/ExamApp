import os
import pathlib
import sqlite3
from datetime import datetime
from crypto_util import encrypt_probe, verify_probe

DB_DIR = os.path.join(str(pathlib.Path.home()), '.exam_system')
ADMIN_DB_PATH = os.path.join(DB_DIR, 'admin.db')
USERS_DB_PATH = os.path.join(DB_DIR, 'users.db')
EXAMS_DB_PATH = os.path.join(DB_DIR, 'exams.db')
SCORES_DB_PATH = os.path.join(DB_DIR, 'scores.db')
CONFIG_DB_PATH = os.path.join(DB_DIR, 'config.db')
PROGRESS_DB_PATH = os.path.join(DB_DIR, 'progress.db')
DB_PATH = EXAMS_DB_PATH

def ensure_db():
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(ADMIN_DB_PATH)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS admins (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT, active INTEGER DEFAULT 1, created_at TEXT, full_name TEXT)')
    conn.commit()
    conn.close()
    conn = sqlite3.connect(USERS_DB_PATH)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT, role TEXT, active INTEGER DEFAULT 1, created_at TEXT, full_name TEXT)')
    conn.commit()
    conn.close()
    conn = sqlite3.connect(EXAMS_DB_PATH)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS exams (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, description TEXT, pass_ratio REAL, time_limit_minutes INTEGER, end_date TEXT, created_at TEXT, random_pick_count INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS questions (id INTEGER PRIMARY KEY AUTOINCREMENT, exam_id INTEGER, type TEXT, text TEXT, options TEXT, correct_answers TEXT, score REAL, pool TEXT)')
    conn.commit()
    conn.close()
    conn = sqlite3.connect(SCORES_DB_PATH)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS attempts (id INTEGER PRIMARY KEY AUTOINCREMENT, uuid TEXT UNIQUE, user_id INTEGER, exam_id INTEGER, started_at TEXT, submitted_at TEXT, score REAL, passed INTEGER, total_score REAL, checksum TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS attempt_answers (id INTEGER PRIMARY KEY AUTOINCREMENT, attempt_uuid TEXT, question_id INTEGER, selected TEXT)')
    conn.commit()
    conn.close()
    conn = sqlite3.connect(CONFIG_DB_PATH)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT UNIQUE, value TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS sync_targets (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, ip TEXT, username TEXT, remote_path TEXT, ssh_password TEXT)')
    conn.commit()
    conn.close()
    conn = sqlite3.connect(PROGRESS_DB_PATH)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS progress_modules (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, created_at TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS progress_tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, module_id INTEGER, title TEXT, description TEXT, sort_order INTEGER DEFAULT 0, created_at TEXT, UNIQUE(module_id, title))')
    c.execute('CREATE TABLE IF NOT EXISTS user_task_progress (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, task_id INTEGER, status INTEGER DEFAULT 0, updated_at TEXT, updated_by TEXT, UNIQUE(user_id, task_id))')
    try:
        c.execute('CREATE INDEX IF NOT EXISTS idx_progress_tasks_module ON progress_tasks (module_id, sort_order, id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_user_task_progress_user ON user_task_progress (user_id, task_id)')
    except Exception:
        pass
    conn.commit()
    conn.close()

def get_admin_conn():
    ensure_db()
    return sqlite3.connect(ADMIN_DB_PATH)

def get_user_conn():
    ensure_db()
    return sqlite3.connect(USERS_DB_PATH)

def get_exam_conn():
    ensure_db()
    return sqlite3.connect(EXAMS_DB_PATH)

def get_score_conn():
    ensure_db()
    return sqlite3.connect(SCORES_DB_PATH)

def get_config_conn():
    ensure_db()
    return sqlite3.connect(CONFIG_DB_PATH)

def get_progress_conn():
    ensure_db()
    return sqlite3.connect(PROGRESS_DB_PATH)

def now_iso():
    return datetime.now().isoformat()

def get_setting(key):
    conn = sqlite3.connect(CONFIG_DB_PATH)
    c = conn.cursor()
    c.execute('SELECT value FROM settings WHERE key=?', (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def set_setting(key, value):
    conn = sqlite3.connect(CONFIG_DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM settings WHERE key=?', (key,))
    c.execute('INSERT INTO settings (key, value) VALUES (?,?)', (key, value))
    conn.commit()
    conn.close()

def ensure_key_probe():
    try:
        v = get_setting('key_probe')
        if v is None:
            set_setting('key_probe', encrypt_probe())
    except Exception:
        pass

def verify_db_encryption_key():
    try:
        v = get_setting('key_probe')
        if v is None:
            return True
        return bool(verify_probe(v))
    except Exception:
        return False
