"""
Description: Database simple iter config dictionary
Author: GentsunCheng
"""
import os
import sqlite3
from database import (
    DB_DIR,
    ADMIN_DB_PATH,
    USERS_DB_PATH,
    EXAMS_DB_PATH,
    SCORES_DB_PATH,
    CONFIG_DB_PATH,
    PROGRESS_DB_PATH,
    DB_VERFILE_PATH,
)

# 版本过度标识
VER_TRAIN = {"all": "all"}

# 自定义代码片段
ITER_DICT = {
    "origin": [
        (ADMIN_DB_PATH, 'admins', 'edit_at', 'TEXT', 'NULL'),
        (USERS_DB_PATH, 'users', 'edit_at', 'TEXT', 'NULL'),
        (ADMIN_DB_PATH, 'admins', 'shadow_delete', 'INTEGER NOT NULL', '0'),
        (USERS_DB_PATH, 'users', 'shadow_delete', 'INTEGER NOT NULL', '0')
    ]
}

__all_db__ = [ADMIN_DB_PATH, USERS_DB_PATH, EXAMS_DB_PATH, SCORES_DB_PATH, CONFIG_DB_PATH, PROGRESS_DB_PATH]
__first_boot__ = all(not os.path.exists(db) for db in __all_db__)

TYPE_DEFAULT_DICT = {
    'TEXT': 'NULL',
    'INTEGER': '0',
    'REAL': '0.0',
    'BLOB': 'NULL',
}


def iter_columns_model(db_path, table_name, column_name, column_type, default_value=None):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(f'PRAGMA table_info({table_name})')
    columns = [row[1] for row in c.fetchall()]
    if column_name not in columns:
        default_value = TYPE_DEFAULT_DICT.get(column_type, 'NULL') if default_value is None else default_value
        c.execute(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type} DEFAULT {default_value}')
        conn.commit()
    conn.close()


def iter_columns(iter_list):
    if __first_boot__:
        return
    for iter_data in iter_list:
        db_path, table_name, column_name, column_type, default_value = iter_data
        if not os.path.exists(db_path):
            continue
        iter_columns_model(db_path, table_name, column_name, column_type, default_value)


__simple_columns_iter__ = iter_columns
