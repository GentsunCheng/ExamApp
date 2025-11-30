import random
import uuid
from datetime import datetime
from database import get_conn, now_iso, ensure_key_probe, verify_db_encryption_key
from utils import hash_password, verify_password
import sqlite3
from crypto_util import encrypt_text, decrypt_text, encrypt_json, decrypt_json
import hashlib
import hmac
try:
    from conf.serect_key import SERECT_KEY
except Exception:
    SERECT_KEY = 'example'

def create_admin_if_absent():
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users WHERE role=?', ('admin',))
    count = c.fetchone()[0]
    if count == 0:
        try:
            c.execute('INSERT INTO users (username, password_hash, role, active, created_at, full_name) VALUES (?,?,?,?,?,?)', ('admin', hash_password('admin'), 'admin', 1, now_iso(), encrypt_text('管理员')))
        except Exception:
            c.execute('INSERT INTO users (username, password_hash, role, active, created_at) VALUES (?,?,?,?,?)', ('admin', hash_password('admin'), 'admin', 1, now_iso()))
        conn.commit()
    conn.close()

def verify_encryption_ok():
    try:
        ensure_key_probe()
        return bool(verify_db_encryption_key())
    except Exception:
        return False

def create_user(username, password, role='user', active=1, full_name=None):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (username, password_hash, role, active, created_at, full_name) VALUES (?,?,?,?,?,?)', (username, hash_password(password), role, active, now_iso(), encrypt_text(full_name) if full_name is not None else None))
    except Exception:
        c.execute('INSERT INTO users (username, password_hash, role, active, created_at) VALUES (?,?,?,?,?)', (username, hash_password(password), role, active, now_iso()))
    conn.commit()
    conn.close()

def authenticate(username, password):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT id, username, password_hash, role, active, full_name FROM users WHERE username=?', (username,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    if row[4] != 1:
        return None
    if not verify_password(password, row[2]):
        return None
    return {'id': row[0], 'username': row[1], 'role': row[3], 'full_name': decrypt_text(row[5]) if len(row) > 5 else None}

def list_users():
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute('SELECT id, username, full_name, role, active, created_at FROM users ORDER BY id DESC')
    except Exception:
        c.execute('SELECT id, username, NULL as full_name, role, active, created_at FROM users ORDER BY id DESC')
    rows = c.fetchall()
    conn.close()
    out = []
    for r in rows:
        fn = r[2]
        out.append((r[0], r[1], decrypt_text(fn) if fn else None, r[3], r[4], r[5]))
    return out

def add_exam(title, description, pass_ratio, time_limit_minutes, end_date, random_pick_count=0):
    conn = get_conn()
    c = conn.cursor()
    c.execute('INSERT INTO exams (title, description, pass_ratio, time_limit_minutes, end_date, created_at, random_pick_count) VALUES (?,?,?,?,?,?,?)', (encrypt_text(title), encrypt_text(description) if description is not None else None, float(pass_ratio), int(time_limit_minutes), end_date, now_iso(), int(random_pick_count)))
    conn.commit()
    conn.close()

def list_exams(include_expired=False):
    conn = get_conn()
    c = conn.cursor()
    if include_expired:
        c.execute('SELECT id, title, description, pass_ratio, time_limit_minutes, end_date FROM exams ORDER BY id DESC')
    else:
        c.execute('SELECT id, title, description, pass_ratio, time_limit_minutes, end_date FROM exams WHERE (end_date>=? OR end_date IS NULL) ORDER BY id DESC', (datetime.utcnow().isoformat(),))
    rows = c.fetchall()
    conn.close()
    out = []
    for r in rows:
        out.append((r[0], decrypt_text(r[1]) if r[1] else None, decrypt_text(r[2]) if r[2] else None, r[3], r[4], r[5]))
    return out

def get_exam_title(exam_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT title FROM exams WHERE id=?', (exam_id,))
    row = c.fetchone()
    conn.close()
    return decrypt_text(row[0]) if row else None

def add_question(exam_id, qtype, text, options, correct_answers, score):
    conn = get_conn()
    c = conn.cursor()
    c.execute('INSERT INTO questions (exam_id, type, text, options, correct_answers, score) VALUES (?,?,?,?,?,?)', (exam_id, qtype, encrypt_text(text), encrypt_json(options or []), encrypt_json(correct_answers), float(score)))
    conn.commit()
    conn.close()

def list_questions(exam_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT id, type, text, options, correct_answers, score FROM questions WHERE exam_id=? ORDER BY id', (exam_id,))
    rows = c.fetchall()
    conn.close()
    result = []
    for r in rows:
        result.append({'id': r[0], 'type': r[1], 'text': decrypt_text(r[2]) if r[2] else '', 'options': decrypt_json(r[3]) or [], 'correct': decrypt_json(r[4]) or [], 'score': r[5]})
    return result

def get_exam_stats(exam_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT COUNT(*), COALESCE(SUM(score), 0) FROM questions WHERE exam_id=?', (exam_id,))
    row = c.fetchone()
    conn.close()
    cnt = int(row[0]) if row and row[0] is not None else 0
    total = float(row[1]) if row and row[1] is not None else 0.0
    return {'count': cnt, 'total_score': total}

def import_questions_from_json(exam_id, payload):
    conn = get_conn()
    c = conn.cursor()
    for q in payload:
        pool = (q.get('pool') or q.get('category') or 'mandatory')
        c.execute('INSERT INTO questions (exam_id, type, text, options, correct_answers, score, pool) VALUES (?,?,?,?,?,?,?)', (exam_id, q.get('type'), encrypt_text(q.get('text')), encrypt_json(q.get('options') or []), encrypt_json(q.get('correct') or []), float(q.get('score', 1)), pool))
    conn.commit()
    conn.close()

def clear_exam_questions(exam_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('DELETE FROM questions WHERE exam_id=?', (exam_id,))
    conn.commit()
    conn.close()

def delete_exam(exam_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT uuid FROM attempts WHERE exam_id=?', (exam_id,))
    uuids = [r[0] for r in c.fetchall()]
    for u in uuids:
        c.execute('DELETE FROM attempt_answers WHERE attempt_uuid=?', (u,))
    c.execute('DELETE FROM attempts WHERE exam_id=?', (exam_id,))
    c.execute('DELETE FROM questions WHERE exam_id=?', (exam_id,))
    c.execute('DELETE FROM exams WHERE id=?', (exam_id,))
    conn.commit()
    conn.close()

def start_attempt(user_id, exam_id, total_score):
    a_uuid = str(uuid.uuid4())
    conn = get_conn()
    c = conn.cursor()
    ts = now_iso()
    checksum = hmac.new(SERECT_KEY.encode('utf-8'), ('|'.join([str(a_uuid), str(user_id), str(exam_id), str(ts), '-', str(0.0), str(0), str(total_score)])).encode('utf-8'), hashlib.sha256).hexdigest()
    c.execute('INSERT INTO attempts (uuid, user_id, exam_id, started_at, submitted_at, score, passed, total_score, checksum) VALUES (?,?,?,?,?,?,?,?,?)', (a_uuid, user_id, exam_id, ts, None, 0.0, 0, float(total_score), checksum))
    conn.commit()
    conn.close()
    return a_uuid

def save_answer(attempt_uuid, question_id, selected):
    conn = get_conn()
    c = conn.cursor()
    c.execute('DELETE FROM attempt_answers WHERE attempt_uuid=? AND question_id=?', (attempt_uuid, question_id))
    c.execute('INSERT INTO attempt_answers (attempt_uuid, question_id, selected) VALUES (?,?,?)', (attempt_uuid, question_id, encrypt_json(selected)))
    conn.commit()
    conn.close()

def submit_attempt(attempt_uuid):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT exam_id, user_id, started_at, total_score FROM attempts WHERE uuid=?', (attempt_uuid,))
    row = c.fetchone()
    if not row:
        conn.close()
        return 0.0, 0
    exam_id = row[0]
    started_at = row[2]
    attempt_total = float(row[3] or 0.0)
    qs = list_questions(exam_id)
    total = 0.0
    c.execute('SELECT question_id, selected FROM attempt_answers WHERE attempt_uuid=?', (attempt_uuid,))
    answers = {}
    for r in c.fetchall():
        val = decrypt_json(r[1])
        answers[r[0]] = val if val is not None else []
    for q in qs:
        total += float(q['score']) if grade_question(q, answers.get(q['id'])) else 0.0
    c.execute('SELECT pass_ratio FROM exams WHERE id=?', (exam_id,))
    pass_ratio = c.fetchone()[0]
    denom = attempt_total if attempt_total > 0 else sum(float(q['score']) for q in qs)
    passed = 1 if (denom > 0 and total / denom >= pass_ratio) else 0
    sub_ts = now_iso()
    c.execute('UPDATE attempts SET submitted_at=?, score=?, passed=? WHERE uuid=?', (sub_ts, total, passed, attempt_uuid))
    try:
        checksum = hmac.new(SERECT_KEY.encode('utf-8'), ('|'.join([str(attempt_uuid), str(row[1]), str(exam_id), str(started_at), str(sub_ts), str(total), str(passed), str(attempt_total)])).encode('utf-8'), hashlib.sha256).hexdigest()
        c.execute('UPDATE attempts SET checksum=? WHERE uuid=?', (checksum, attempt_uuid))
    except Exception:
        pass
    conn.commit()
    conn.close()
    return total, passed

def grade_question(q, sel):
    if q['type'] == 'single':
        return sel is not None and sel == q['correct']
    if q['type'] == 'multiple':
        return sel is not None and sorted(sel) == sorted(q['correct'])
    if q['type'] == 'truefalse':
        return sel is not None and sel == q['correct']
    return False

def list_attempts(user_id=None):
    conn = get_conn()
    c = conn.cursor()
    if user_id:
        c.execute('SELECT uuid, user_id, exam_id, started_at, submitted_at, score, passed, total_score, checksum FROM attempts WHERE user_id=? ORDER BY id DESC', (user_id,))
    else:
        c.execute('SELECT uuid, user_id, exam_id, started_at, submitted_at, score, passed, total_score, checksum FROM attempts ORDER BY id DESC')
    rows = c.fetchall()
    conn.close()
    out = []
    for r in rows:
        expect = hmac.new(SERECT_KEY.encode('utf-8'), ('|'.join([str(r[0]), str(r[1]), str(r[2]), str(r[3]), str(r[4]) if r[4] else '-', str(r[5]), str(r[6]), str(r[7])])).encode('utf-8'), hashlib.sha256).hexdigest()
        valid = str(r[8] or '') == expect
        out.append((r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], 1 if valid else 0))
    return out

def list_attempts_with_user():
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute('SELECT a.uuid, u.username, u.full_name, a.user_id, a.exam_id, a.started_at, a.submitted_at, a.score, a.passed, a.total_score, a.checksum FROM attempts a JOIN users u ON a.user_id=u.id ORDER BY a.id DESC')
    except Exception:
        c.execute('SELECT a.uuid, u.username, NULL as full_name, a.user_id, a.exam_id, a.started_at, a.submitted_at, a.score, a.passed, a.total_score, a.checksum FROM attempts a JOIN users u ON a.user_id=u.id ORDER BY a.id DESC')
    rows = c.fetchall()
    conn.close()
    out = []
    for r in rows:
        fn = r[2]
        expect = hmac.new(SERECT_KEY.encode('utf-8'), ('|'.join([str(r[0]), str(r[3]), str(r[4]), str(r[5]), str(r[6]) if r[6] else '-', str(r[7]), str(r[8]), str(r[9])])).encode('utf-8'), hashlib.sha256).hexdigest()
        valid = str(r[10] or '') == expect
        out.append((r[0], r[1], decrypt_text(fn) if fn else None, r[3], r[4], r[5], r[6], r[7], r[8], r[9], 1 if valid else 0))
    return out

def merge_remote_db(remote_db_path):
    lconn = get_conn()
    lcur = lconn.cursor()
    rconn = sqlite3.connect(remote_db_path)
    rcur = rconn.cursor()
    rcur.execute('SELECT uuid, user_id, exam_id, started_at, submitted_at, score, passed, total_score, checksum FROM attempts')
    remote_rows = rcur.fetchall()
    for a in remote_rows:
        lcur.execute('SELECT COUNT(*) FROM attempts WHERE uuid=?', (a[0],))
        if lcur.fetchone()[0] == 0:
            lcur.execute('INSERT INTO attempts (uuid, user_id, exam_id, started_at, submitted_at, score, passed, total_score, checksum) VALUES (?,?,?,?,?,?,?,?,?)', a)
            rcur2 = rconn.cursor()
            rcur2.execute('SELECT question_id, selected FROM attempt_answers WHERE attempt_uuid=?', (a[0],))
            for aa in rcur2.fetchall():
                lcur.execute('INSERT INTO attempt_answers (attempt_uuid, question_id, selected) VALUES (?,?,?)', (a[0], aa[0], aa[1]))
    lconn.commit()
    rconn.close()
    lconn.close()

def delete_user(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE id=?', (user_id,))
    conn.commit()
    conn.close()

def update_user_role(user_id, role):
    conn = get_conn()
    c = conn.cursor()
    c.execute('UPDATE users SET role=? WHERE id=?', (role, user_id))
    conn.commit()
    conn.close()

def update_user_active(user_id, active):
    conn = get_conn()
    c = conn.cursor()
    c.execute('UPDATE users SET active=? WHERE id=?', (active, user_id))
    conn.commit()
    conn.close()

def update_user_basic(user_id, username=None, full_name=None):
    conn = get_conn()
    c = conn.cursor()
    if username is not None and full_name is not None:
        c.execute('UPDATE users SET username=?, full_name=? WHERE id=?', (username, encrypt_text(full_name), user_id))
    elif username is not None:
        c.execute('UPDATE users SET username=? WHERE id=?', (username, user_id))
    elif full_name is not None:
        c.execute('UPDATE users SET full_name=? WHERE id=?', (encrypt_text(full_name), user_id))
    conn.commit()
    conn.close()

def update_exam_title_desc(exam_id, title=None, description=None):
    conn = get_conn()
    c = conn.cursor()
    if title is not None and description is not None:
        c.execute('UPDATE exams SET title=?, description=? WHERE id=?', (encrypt_text(title), encrypt_text(description) if description is not None else None, exam_id))
    elif title is not None:
        c.execute('UPDATE exams SET title=? WHERE id=?', (encrypt_text(title), exam_id))
    elif description is not None:
        c.execute('UPDATE exams SET description=? WHERE id=?', (encrypt_text(description), exam_id))
    conn.commit()
    conn.close()

def delete_sync_target(target_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('DELETE FROM sync_targets WHERE id=?', (target_id,))
    conn.commit()
    conn.close()

def update_sync_target(target_id, name, ip, username, remote_path, ssh_password=None):
    conn = get_conn()
    c = conn.cursor()
    if ssh_password is not None:
        c.execute('UPDATE sync_targets SET name=?, ip=?, username=?, remote_path=?, ssh_password=? WHERE id=?', (name, ip, username, remote_path, encrypt_text(ssh_password), target_id))
    else:
        c.execute('UPDATE sync_targets SET name=?, ip=?, username=?, remote_path=? WHERE id=?', (name, ip, username, remote_path, target_id))
    conn.commit()
    conn.close()

def upsert_sync_target(name, ip, username, remote_path, ssh_password=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute('INSERT INTO sync_targets (name, ip, username, remote_path, ssh_password) VALUES (?,?,?,?,?)', (name, ip, username, remote_path, encrypt_text(ssh_password) if ssh_password is not None else None))
    conn.commit()
    conn.close()

def list_sync_targets():
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT id, name, ip, username, remote_path, ssh_password FROM sync_targets ORDER BY id DESC')
    rows = c.fetchall()
    conn.close()
    out = []
    for r in rows:
        out.append((r[0], r[1], r[2], r[3], r[4], decrypt_text(r[5]) if r[5] else None))
    return out

def list_questions_by_pool(exam_id, pool):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute('SELECT id, type, text, options, correct_answers, score FROM questions WHERE exam_id=? AND (pool=? OR (pool IS NULL AND ?="mandatory")) ORDER BY id', (exam_id, pool, pool))
    except Exception:
        c.execute('SELECT id, type, text, options, correct_answers, score FROM questions WHERE exam_id=? ORDER BY id', (exam_id,))
    rows = c.fetchall()
    conn.close()
    out = []
    for r in rows:
        out.append({'id': r[0], 'type': r[1], 'text': decrypt_text(r[2]) if r[2] else '', 'options': decrypt_json(r[3]) or [], 'correct': decrypt_json(r[4]) or [], 'score': r[5]})
    return out

def get_exam_random_pick_count(exam_id):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute('SELECT random_pick_count FROM exams WHERE id=?', (exam_id,))
        row = c.fetchone()
        conn.close()
        return int(row[0]) if row and row[0] is not None else 0
    except Exception:
        conn.close()
        return 0

def update_exam_random_pick_count(exam_id, count):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute('UPDATE exams SET random_pick_count=? WHERE id=?', (int(count), exam_id))
        conn.commit()
    except Exception:
        pass
    conn.close()

def build_exam_questions_for_attempt(exam_id):
    mandatory = list_questions_by_pool(exam_id, 'mandatory')
    random_pool = list_questions_by_pool(exam_id, 'random')
    pick = get_exam_random_pick_count(exam_id)
    if pick <= 0:
        sampled = random_pool
    else:
        n = min(int(pick), len(random_pool))
        try:
            sampled = random.sample(random_pool, n)
        except Exception:
            sampled = random_pool[:n]
    combined = list(mandatory) + list(sampled)
    try:
        random.shuffle(combined)
    except Exception:
        pass
    return combined
