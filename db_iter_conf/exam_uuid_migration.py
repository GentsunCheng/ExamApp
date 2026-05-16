"""
Description: Migrate exam.exam_id to exam_uuid for questions table
Author: GentsunCheng
"""
import os
import sqlite3
import uuid
from database import (
    EXAMS_DB_PATH,
)

# 版本过度标识
VER_TRAIN = {"260516": "260518"}


def exam_uuid_migrate(param):
    """为已有 exams 生成 uuid，并将 questions 的 exam_id 迁移为 exam_uuid"""
    if not os.path.exists(EXAMS_DB_PATH):
        return
    conn = sqlite3.connect(EXAMS_DB_PATH)
    c = conn.cursor()
    # 1. 为 exams 生成 uuid
    c.execute('PRAGMA table_info(exams)')
    exam_cols = {row[1] for row in c.fetchall()}
    if 'uuid' in exam_cols:
        c.execute("SELECT id FROM exams WHERE uuid IS NULL")
        for row in c.fetchall():
            exam_id = row[0]
            exam_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"exam:{exam_id}"))
            c.execute("UPDATE exams SET uuid=? WHERE id=?", (exam_uuid, exam_id))
    # 2. 迁移 questions.exam_id → exam_uuid
    c.execute('PRAGMA table_info(questions)')
    q_cols = {row[1] for row in c.fetchall()}
    has_exam_id = 'exam_id' in q_cols
    has_exam_uuid = 'exam_uuid' in q_cols
    if has_exam_id and has_exam_uuid:
        c.execute("SELECT q.id, q.exam_id, e.uuid FROM questions q LEFT JOIN exams e ON q.exam_id=e.id WHERE q.exam_uuid IS NULL AND q.exam_id IS NOT NULL")
        rows = c.fetchall()
        for qid, eid, e_uuid in rows:
            if e_uuid:
                c.execute("UPDATE questions SET exam_uuid=? WHERE id=?", (e_uuid, qid))
            else:
                # exam 没有 uuid 时，用 exam_id 生成
                fallback = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"exam:{eid}"))
                c.execute("UPDATE questions SET exam_uuid=? WHERE id=?", (fallback, qid))
    conn.commit()
    conn.close()


__exam_uuid_migrate__ = exam_uuid_migrate
