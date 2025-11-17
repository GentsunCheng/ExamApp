import os
import pathlib
import sqlite3
from datetime import datetime

DB_DIR = os.path.join(str(pathlib.Path.home()), '.exam_system')
DB_PATH = os.path.join(DB_DIR, 'exam.db')

def ensure_db():
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT, role TEXT, active INTEGER DEFAULT 1, created_at TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS exams (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, description TEXT, pass_ratio REAL, time_limit_minutes INTEGER, end_date TEXT, created_at TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS questions (id INTEGER PRIMARY KEY AUTOINCREMENT, exam_id INTEGER, type TEXT, text TEXT, options TEXT, correct_answers TEXT, score REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS attempts (id INTEGER PRIMARY KEY AUTOINCREMENT, uuid TEXT UNIQUE, user_id INTEGER, exam_id INTEGER, started_at TEXT, submitted_at TEXT, score REAL, passed INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS attempt_answers (id INTEGER PRIMARY KEY AUTOINCREMENT, attempt_uuid TEXT, question_id INTEGER, selected TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT UNIQUE, value TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS sync_targets (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, ip TEXT, username TEXT, remote_path TEXT)')
    
    # Add ssh_password column if it doesn't exist
    try:
        c.execute('SELECT ssh_password FROM sync_targets LIMIT 1')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE sync_targets ADD COLUMN ssh_password TEXT')
    
    conn.commit()
    # Add full_name column to users if it doesn't exist
    try:
        c = sqlite3.connect(DB_PATH).cursor()
        c.execute('SELECT full_name FROM users LIMIT 1')
    except sqlite3.OperationalError:
        conn = sqlite3.connect(DB_PATH)
        conn.execute('ALTER TABLE users ADD COLUMN full_name TEXT')
        conn.commit()
        conn.close()
    conn.close()

def get_conn():
    ensure_db()
    return sqlite3.connect(DB_PATH)

def now_iso():
    return datetime.utcnow().isoformat()
