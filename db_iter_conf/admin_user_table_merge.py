"""
Description: Merge id from admin to user table
Author: GentsunCheng
"""
import os
import sqlite3
from database import (
    DB_DIR,
    UID_DB_PATH,
    ADMIN_DB_PATH,
    USERS_DB_PATH,
    EXAMS_DB_PATH,
    SCORES_DB_PATH,
    CONFIG_DB_PATH,
    PROGRESS_DB_PATH,
    DB_VERFILE_PATH,
)

# 版本过度标识
VER_TRAIN = {"260128": "260208"}


def migrate_old_db():
    if not os.path.exists(ADMIN_DB_PATH) or not os.path.exists(USERS_DB_PATH):
        return False
    conn = sqlite3.connect(ADMIN_DB_PATH)
    c = conn.cursor()
    try:
        c.execute('BEGIN;')
        c.execute("ALTER TABLE admins RENAME TO admins_old;")
        c.execute('CREATE TABLE IF NOT EXISTS admins '
        '(id INTEGER PRIMARY KEY, '
        'username TEXT UNIQUE, password_hash TEXT, '
        'active INTEGER DEFAULT 1, created_at TEXT, '
        'full_name TEXT, edit_at TEXT DEFAULT NULL, '
        'shadow_delete INTEGER NOT NULL DEFAULT 0);')
        c.execute('INSERT INTO admins (id, username, password_hash, active, '
        'created_at, full_name, edit_at, shadow_delete) '
        'SELECT id, username, password_hash, active, created_at, full_name, '
        'edit_at, shadow_delete FROM admins_old;')
        c.execute('DROP TABLE admins_old;')
        conn.commit()
    except Exception as e:
        print("admins table 迁移失败，已回滚：", e)
        conn.rollback()
    finally:
        conn.close()
    conn = sqlite3.connect(USERS_DB_PATH)
    c = conn.cursor()
    try:
        c.execute('BEGIN;')
        c.execute("ALTER TABLE users RENAME TO users_old;")
        c.execute('CREATE TABLE IF NOT EXISTS users '
                  '(id INTEGER PRIMARY KEY, username TEXT UNIQUE, '
                  'password_hash TEXT, role TEXT, '
                  'active INTEGER DEFAULT 1, created_at TEXT, '
                  'full_name TEXT, edit_at TEXT DEFAULT NULL, '
                  'shadow_delete INTEGER NOT NULL DEFAULT 0);')
        c.execute('INSERT INTO users (id, username, password_hash, role, active, '
                  'created_at, full_name, edit_at, shadow_delete) '
                  'SELECT id, username, password_hash, role, active, created_at, full_name, '
                  'edit_at, shadow_delete FROM users_old;')
        c.execute('DROP TABLE users_old;')
        conn.commit()
    except Exception as e:
        print("users table 迁移失败，已回滚：", e)
        conn.rollback()
    finally:
        conn.close()
    return True


def create_uid_db():
    conn = sqlite3.connect(USERS_DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id from users')
    rows = c.fetchall()
    user_ids = [row[0] for row in rows]
    conn.close()
    conn = sqlite3.connect(ADMIN_DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id from admins')
    rows = c.fetchall()
    admin_ids = [row[0] for row in rows]
    conn.close()
    user_count = len(user_ids)
    admin_count = len(admin_ids)

    conn = sqlite3.connect(UID_DB_PATH)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS uid_map '
    '(id INTEGER PRIMARY KEY AUTOINCREMENT)')
    conn.commit()
    c.executemany("INSERT INTO uid_map DEFAULT VALUES;", [() for _ in range(user_count)])
    conn.commit()
    c.executemany("INSERT INTO uid_map DEFAULT VALUES;", [() for _ in range(admin_count)])
    conn.commit()
    c.execute("SELECT MAX(id) FROM uid_map;")
    last_id = c.fetchone()[0]
    new_admin_ids = list(range(last_id - admin_count + 1, last_id + 1))
    conn.close()

    conn = sqlite3.connect(ADMIN_DB_PATH)
    c = conn.cursor()
    c.execute('SELECT username FROM admins')
    rows = c.fetchall()
    admin_usernames = [row[0] for row in rows]
    for idx, username in enumerate(admin_usernames):
        c.execute('UPDATE admins SET id=? WHERE username=?;',
                  (new_admin_ids[idx], username))
    conn.commit()
    conn.close()





def main_merge_action(param_tab):
    migrate_old_db()
    create_uid_db()

__main_merge_action__ = main_merge_action
