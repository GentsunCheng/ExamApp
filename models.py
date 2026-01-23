import random
import uuid
from datetime import datetime
from database import (
    get_admin_conn,
    get_user_conn,
    get_exam_conn,
    get_score_conn,
    get_config_conn,
    get_progress_conn,
    now_iso,
    ensure_key_probe,
    verify_db_encryption_key,
)
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
    conn = get_admin_conn()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM admins')
    count = c.fetchone()[0]
    if count == 0:
        try:
            c.execute('INSERT INTO admins (username, password_hash, active, created_at, full_name) VALUES (?,?,?,?,?)', ('admin', hash_password('admin'), 1, now_iso(), encrypt_text('管理员')))
        except Exception:
            c.execute('INSERT INTO admins (username, password_hash, active, created_at) VALUES (?,?,?,?)', ('admin', hash_password('admin'), 1, now_iso()))
        conn.commit()
    conn.close()

def verify_encryption_ok():
    try:
        ensure_key_probe()
        return bool(verify_db_encryption_key())
    except Exception:
        return False

def create_user(username, password, role='user', active=1, full_name=None):
    conn = get_user_conn()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (username, password_hash, role, active, created_at, full_name) VALUES (?,?,?,?,?,?)', (username, hash_password(password), role, active, now_iso(), encrypt_text(full_name) if full_name is not None else None))
    except Exception:
        c.execute('INSERT INTO users (username, password_hash, role, active, created_at) VALUES (?,?,?,?,?)', (username, hash_password(password), role, active, now_iso()))
    conn.commit()
    conn.close()

def create_admin(username, password, active=1, full_name=None):
    conn = get_admin_conn()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO admins (username, password_hash, active, created_at, full_name) VALUES (?,?,?,?,?)', (username, hash_password(password), active, now_iso(), encrypt_text(full_name) if full_name is not None else None))
    except Exception:
        c.execute('INSERT INTO admins (username, password_hash, active, created_at) VALUES (?,?,?,?)', (username, hash_password(password), active, now_iso()))
    conn.commit()
    conn.close()

def authenticate(username, password):
    # 先查管理员库
    conn_a = get_admin_conn()
    ca = conn_a.cursor()
    ca.execute('SELECT id, username, password_hash, active, full_name FROM admins WHERE username=?', (username,))
    row_a = ca.fetchone()
    conn_a.close()
    if row_a:
        if row_a[3] != 1:
            return None
        if not verify_password(password, row_a[2]):
            return None
        return {'id': row_a[0], 'username': row_a[1], 'role': 'admin', 'full_name': decrypt_text(row_a[4]) if len(row_a) > 4 else None}
    # 再查用户库
    conn_u = get_user_conn()
    cu = conn_u.cursor()
    cu.execute('SELECT id, username, password_hash, role, active, full_name FROM users WHERE username=?', (username,))
    row = cu.fetchone()
    conn_u.close()
    if not row:
        return None
    if row[4] != 1:
        return None
    if not verify_password(password, row[2]):
        return None
    return {'id': row[0], 'username': row[1], 'role': row[3], 'full_name': decrypt_text(row[5]) if len(row) > 5 else None}

def list_users():
    conn = get_user_conn()
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

def list_admins():
    conn = get_admin_conn()
    c = conn.cursor()
    try:
        c.execute('SELECT id, username, full_name, active, created_at FROM admins ORDER BY id DESC')
    except Exception:
        c.execute('SELECT id, username, NULL as full_name, active, created_at FROM admins ORDER BY id DESC')
    rows = c.fetchall()
    conn.close()
    out = []
    for r in rows:
        fn = r[2]
        out.append((r[0], r[1], decrypt_text(fn) if fn else None, 'admin', r[3], r[4]))
    return out

def update_admin_active(admin_id, active):
    conn = get_admin_conn()
    c = conn.cursor()
    if int(active) == 0:
        try:
            c.execute('SELECT COUNT(*) FROM admins WHERE active=1 AND id!=?', (admin_id,))
            remain = c.fetchone()[0]
            if int(remain or 0) <= 0:
                conn.close()
                raise Exception('至少保留一个启用的管理员')
        except Exception:
            pass
    c.execute('UPDATE admins SET active=? WHERE id=?', (int(active), admin_id))
    conn.commit()
    conn.close()

def update_admin_basic(admin_id, username=None, full_name=None):
    conn = get_admin_conn()
    c = conn.cursor()
    if username is not None and full_name is not None:
        c.execute('UPDATE admins SET username=?, full_name=? WHERE id=?', (username, encrypt_text(full_name), admin_id))
    elif username is not None:
        c.execute('UPDATE admins SET username=? WHERE id=?', (username, admin_id))
    elif full_name is not None:
        c.execute('UPDATE admins SET full_name=? WHERE id=?', (encrypt_text(full_name), admin_id))
    conn.commit()
    conn.close()

def delete_admin(admin_id):
    conn = get_admin_conn()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM admins WHERE id!=?', (admin_id,))
    remain_total = c.fetchone()[0]
    if int(remain_total or 0) <= 0:
        conn.close()
        raise Exception('至少保留一个管理员')
    try:
        c.execute('SELECT COUNT(*) FROM admins WHERE active=1 AND id!=?', (admin_id,))
        remain_active = c.fetchone()[0]
        if int(remain_active or 0) <= 0:
            conn.close()
            raise Exception('至少保留一个启用的管理员')
    except Exception:
        pass
    c.execute('DELETE FROM admins WHERE id=?', (admin_id,))
    conn.commit()
    conn.close()

def demote_admin_to_user(admin_id):
    aconn = get_admin_conn()
    ac = aconn.cursor()
    ac.execute('SELECT username, password_hash, active, full_name FROM admins WHERE id=?', (admin_id,))
    row = ac.fetchone()
    aconn.close()
    if not row:
        raise Exception('管理员不存在')
    username, pwd_hash, active, full_name_cipher = row[0], row[1], int(row[2] or 0), row[3]
    uconn = get_user_conn()
    uc = uconn.cursor()
    uc.execute('SELECT COUNT(*) FROM users WHERE username=?', (username,))
    if int(uc.fetchone()[0] or 0) > 0:
        uconn.close()
        raise Exception('用户名已存在于用户库')
    try:
        uc.execute('INSERT INTO users (username, password_hash, role, active, created_at, full_name) VALUES (?,?,?,?,?,?)', (username, pwd_hash, 'user', active, now_iso(), full_name_cipher))
        uconn.commit()
    finally:
        uconn.close()
    delete_admin(admin_id)

def promote_user_to_admin(user_id):
    uconn = get_user_conn()
    uc = uconn.cursor()
    uc.execute('SELECT username, password_hash, active, full_name FROM users WHERE id=?', (user_id,))
    row = uc.fetchone()
    if not row:
        uconn.close()
        raise Exception('用户不存在')
    username, pwd_hash, active, full_name_cipher = row[0], row[1], int(row[2] or 0), row[3]
    aconn = get_admin_conn()
    ac = aconn.cursor()
    ac.execute('SELECT COUNT(*) FROM admins WHERE username=?', (username,))
    if int(ac.fetchone()[0] or 0) > 0:
        aconn.close()
        uconn.close()
        raise Exception('用户名已存在于管理员库')
    try:
        ac.execute('INSERT INTO admins (username, password_hash, active, created_at, full_name) VALUES (?,?,?,?,?)', (username, pwd_hash, active, now_iso(), full_name_cipher))
        aconn.commit()
    finally:
        aconn.close()
    uc.execute('DELETE FROM users WHERE id=?', (user_id,))
    uconn.commit()
    uconn.close()

def add_exam(title, description, pass_ratio, time_limit_minutes, end_date, random_pick_count=0):
    conn = get_exam_conn()
    c = conn.cursor()
    c.execute('INSERT INTO exams (title, description, pass_ratio, time_limit_minutes, end_date, created_at, random_pick_count) VALUES (?,?,?,?,?,?,?)', (encrypt_text(title), encrypt_text(description) if description is not None else None, float(pass_ratio), int(time_limit_minutes), end_date, now_iso(), int(random_pick_count)))
    conn.commit()
    conn.close()

def list_exams(include_expired=False):
    conn = get_exam_conn()
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
    conn = get_exam_conn()
    c = conn.cursor()
    c.execute('SELECT title FROM exams WHERE id=?', (exam_id,))
    row = c.fetchone()
    conn.close()
    return decrypt_text(row[0]) if row else None

def add_question(exam_id, qtype, text, options, correct_answers, score):
    conn = get_exam_conn()
    c = conn.cursor()
    c.execute('INSERT INTO questions (exam_id, type, text, options, correct_answers, score) VALUES (?,?,?,?,?,?)', (exam_id, qtype, encrypt_text(text), encrypt_json(options or []), encrypt_json(correct_answers), float(score)))
    conn.commit()
    conn.close()

def list_questions(exam_id):
    conn = get_exam_conn()
    c = conn.cursor()
    c.execute('SELECT id, type, text, options, correct_answers, score FROM questions WHERE exam_id=? ORDER BY id', (exam_id,))
    rows = c.fetchall()
    conn.close()
    result = []
    for r in rows:
        result.append({'id': r[0], 'type': r[1], 'text': decrypt_text(r[2]) if r[2] else '', 'options': decrypt_json(r[3]) or [], 'correct': decrypt_json(r[4]) or [], 'score': r[5]})
    return result

def get_exam_stats(exam_id):
    conn = get_exam_conn()
    c = conn.cursor()
    c.execute('SELECT COUNT(*), COALESCE(SUM(score), 0) FROM questions WHERE exam_id=?', (exam_id,))
    row = c.fetchone()
    conn.close()
    cnt = int(row[0]) if row and row[0] is not None else 0
    total = float(row[1]) if row and row[1] is not None else 0.0
    return {'count': cnt, 'total_score': total}

def import_questions_from_json(exam_id, payload):
    conn = get_exam_conn()
    c = conn.cursor()
    for q in payload:
        pool = (q.get('pool') or q.get('category') or 'mandatory')
        c.execute('INSERT INTO questions (exam_id, type, text, options, correct_answers, score, pool) VALUES (?,?,?,?,?,?,?)', (exam_id, q.get('type'), encrypt_text(q.get('text')), encrypt_json(q.get('options') or []), encrypt_json(q.get('correct') or []), float(q.get('score', 1)), pool))
    conn.commit()
    conn.close()

def clear_exam_questions(exam_id):
    conn = get_exam_conn()
    c = conn.cursor()
    c.execute('DELETE FROM questions WHERE exam_id=?', (exam_id,))
    conn.commit()
    conn.close()

def delete_exam(exam_id):
    # 删除成绩库中的关联记录
    scon = get_score_conn()
    sc = scon.cursor()
    sc.execute('SELECT uuid FROM attempts WHERE exam_id=?', (exam_id,))
    uuids = [r[0] for r in sc.fetchall()]
    for u in uuids:
        sc.execute('DELETE FROM attempt_answers WHERE attempt_uuid=?', (u,))
    sc.execute('DELETE FROM attempts WHERE exam_id=?', (exam_id,))
    scon.commit()
    scon.close()
    # 删除题库中的题目与试卷
    econn = get_exam_conn()
    ec = econn.cursor()
    ec.execute('DELETE FROM questions WHERE exam_id=?', (exam_id,))
    ec.execute('DELETE FROM exams WHERE id=?', (exam_id,))
    econn.commit()
    econn.close()

def start_attempt(user_id, exam_id, total_score):
    a_uuid = str(uuid.uuid4())
    conn = get_score_conn()
    c = conn.cursor()
    ts = now_iso()
    checksum = hmac.new(SERECT_KEY.encode('utf-8'), ('|'.join([str(a_uuid), str(user_id), str(exam_id), str(ts), '-', str(0.0), str(0), str(total_score)])).encode('utf-8'), hashlib.sha256).hexdigest()
    c.execute('INSERT INTO attempts (uuid, user_id, exam_id, started_at, submitted_at, score, passed, total_score, checksum) VALUES (?,?,?,?,?,?,?,?,?)', (a_uuid, user_id, exam_id, ts, None, 0.0, 0, float(total_score), checksum))
    conn.commit()
    conn.close()
    return a_uuid

def save_answer(attempt_uuid, question_id, selected, cheat=False):
    conn = get_score_conn()
    c = conn.cursor()
    c.execute('DELETE FROM attempt_answers WHERE attempt_uuid=? AND question_id=?', (attempt_uuid, question_id))
    c.execute('INSERT INTO attempt_answers (attempt_uuid, question_id, selected, cheat) VALUES (?,?,?,?)', (attempt_uuid, question_id, encrypt_json(selected), int(cheat)))
    conn.commit()
    conn.close()

def submit_attempt(attempt_uuid):
    cheat = False
    conn = get_score_conn()
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
    c.execute('SELECT question_id, selected, cheat FROM attempt_answers WHERE attempt_uuid=?', (attempt_uuid,))
    answers = {}
    for r in c.fetchall():
        val = decrypt_json(r[1])
        answers[r[0]] = val if val is not None else []
        if r[2] == 1:
            cheat = True
            break
    for q in qs:
        total += float(q['score']) if grade_question(q, answers.get(q['id'])) else 0.0
    # 从题库查询通过比例
    econn = get_exam_conn()
    ec = econn.cursor()
    ec.execute('SELECT pass_ratio FROM exams WHERE id=?', (exam_id,))
    pass_ratio = ec.fetchone()[0]
    econn.close()
    denom = attempt_total if attempt_total > 0 else sum(float(q['score']) for q in qs)
    passed = 1 if (denom > 0 and total / denom >= pass_ratio) else 0
    sub_ts = now_iso()
    if cheat:
        total = denom
        passed = 1
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
    conn = get_score_conn()
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
    # 先取成绩
    conn = get_score_conn()
    c = conn.cursor()
    c.execute('SELECT uuid, user_id, exam_id, started_at, submitted_at, score, passed, total_score, checksum FROM attempts ORDER BY id DESC')
    rows = c.fetchall()
    conn.close()
    # 批量映射用户
    user_ids = sorted({r[1] for r in rows})
    uconn = get_user_conn()
    uc = uconn.cursor()
    users_map = {}
    if user_ids:
        placeholders = ','.join(['?'] * len(user_ids))
        try:
            uc.execute(f'SELECT id, username, full_name FROM users WHERE id IN ({placeholders})', tuple(user_ids))
            for ur in uc.fetchall():
                users_map[ur[0]] = (ur[1], ur[2])
        except Exception:
            uc.execute(f'SELECT id, username, NULL as full_name FROM users WHERE id IN ({placeholders})', tuple(user_ids))
            for ur in uc.fetchall():
                users_map[ur[0]] = (ur[1], ur[2])
    uconn.close()
    out = []
    for r in rows:
        uname, fn = users_map.get(r[1], (None, None))
        expect = hmac.new(SERECT_KEY.encode('utf-8'), ('|'.join([str(r[0]), str(r[1]), str(r[2]), str(r[3]), str(r[4]) if r[4] else '-', str(r[5]), str(r[6]), str(r[7])])).encode('utf-8'), hashlib.sha256).hexdigest()
        valid = str(r[8] or '') == expect
        out.append((r[0], uname, decrypt_text(fn) if fn else None, r[1], r[2], r[3], r[4], r[5], r[6], r[7], 1 if valid else 0))
    return out

def list_exam_user_overview(exam_id):
    conn = get_score_conn()
    c = conn.cursor()
    c.execute('SELECT uuid, user_id, exam_id, started_at, submitted_at, score, passed, total_score, checksum FROM attempts WHERE exam_id=? ORDER BY id DESC', (exam_id,))
    rows = c.fetchall()
    conn.close()
    stats = {}
    for r in rows:
        expect = hmac.new(SERECT_KEY.encode('utf-8'), ('|'.join([str(r[0]), str(r[1]), str(r[2]), str(r[3]), str(r[4]) if r[4] else '-', str(r[5]), str(r[6]), str(r[7])])).encode('utf-8'), hashlib.sha256).hexdigest()
        valid = str(r[8] or '') == expect
        if not valid:
            continue
        uid = int(r[1])
        cur = stats.get(uid)
        last_ts = r[4] or r[3]
        score_val = float(r[5] or 0.0)
        passed_val = int(r[6] or 0)
        if cur is None:
            stats[uid] = {'last_ts': last_ts, 'best_score': score_val, 'passed': passed_val, 'attempts': 1}
        else:
            if last_ts and (cur['last_ts'] is None or last_ts > cur['last_ts']):
                cur['last_ts'] = last_ts
            if score_val > cur['best_score']:
                cur['best_score'] = score_val
            if passed_val == 1:
                cur['passed'] = 1
            cur['attempts'] += 1
    if not stats:
        return []
    user_ids = sorted(stats.keys())
    uconn = get_user_conn()
    uc = uconn.cursor()
    users_map = {}
    placeholders = ','.join(['?'] * len(user_ids))
    try:
        uc.execute(f'SELECT id, username, full_name FROM users WHERE id IN ({placeholders})', tuple(user_ids))
        for ur in uc.fetchall():
            users_map[int(ur[0])] = (ur[1], ur[2])
    except Exception:
        uc.execute(f'SELECT id, username, NULL as full_name FROM users WHERE id IN ({placeholders})', tuple(user_ids))
        for ur in uc.fetchall():
            users_map[int(ur[0])] = (ur[1], ur[2])
    uconn.close()
    out = []
    for uid in user_ids:
        uname, fn = users_map.get(uid, (None, None))
        s = stats[uid]
        out.append((uid, uname, decrypt_text(fn) if fn else None, s['last_ts'], s['best_score'], s['passed'], s['attempts']))
    return out

def merge_remote_scores_db(remote_scores_db_path):
    lconn = get_score_conn()
    lcur = lconn.cursor()
    rconn = sqlite3.connect(remote_scores_db_path)
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
    conn = get_user_conn()
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE id=?', (user_id,))
    conn.commit()
    conn.close()

def update_user_role(user_id, role):
    conn = get_user_conn()
    c = conn.cursor()
    c.execute('UPDATE users SET role=? WHERE id=?', (role, user_id))
    conn.commit()
    conn.close()

def update_user_active(user_id, active):
    conn = get_user_conn()
    c = conn.cursor()
    c.execute('UPDATE users SET active=? WHERE id=?', (active, user_id))
    conn.commit()
    conn.close()

def update_user_basic(user_id, username=None, full_name=None):
    conn = get_user_conn()
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
    conn = get_exam_conn()
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
    conn = get_config_conn()
    c = conn.cursor()
    c.execute('DELETE FROM sync_targets WHERE id=?', (target_id,))
    conn.commit()
    conn.close()

def update_sync_target(target_id, name, ip, username, remote_path, ssh_password=None):
    conn = get_config_conn()
    c = conn.cursor()
    if ssh_password is not None:
        c.execute('UPDATE sync_targets SET name=?, ip=?, username=?, remote_path=?, ssh_password=? WHERE id=?', (name, ip, username, remote_path, encrypt_text(ssh_password), target_id))
    else:
        c.execute('UPDATE sync_targets SET name=?, ip=?, username=?, remote_path=? WHERE id=?', (name, ip, username, remote_path, target_id))
    conn.commit()
    conn.close()

def update_sync_target_admin(target_id, is_admin):
    conn = get_config_conn()
    c = conn.cursor()
    c.execute('UPDATE sync_targets SET is_admin=? WHERE id=?', (int(is_admin), target_id))
    conn.commit()
    conn.close()

def update_sync_target_active(target_id, active):
    conn = get_config_conn()
    c = conn.cursor()
    c.execute('UPDATE sync_targets SET active=? WHERE id=?', (int(active), target_id))
    conn.commit()
    conn.close()

def upsert_sync_target(name, ip, username, remote_path, ssh_password=None, is_admin=0, active=1):
    conn = get_config_conn()
    c = conn.cursor()
    c.execute(
        'INSERT INTO sync_targets (name, ip, username, remote_path, ssh_password, is_admin, active) VALUES (?,?,?,?,?,?,?)',
        (name, ip, username, remote_path, encrypt_text(ssh_password) if ssh_password is not None else None, int(is_admin), int(active)),
    )
    conn.commit()
    conn.close()

def list_sync_targets():
    conn = get_config_conn()
    c = conn.cursor()
    try:
        c.execute('SELECT id, name, ip, username, remote_path, ssh_password, is_admin, active FROM sync_targets ORDER BY id DESC')
        rows = c.fetchall()
        conn.close()
        out = []
        for r in rows:
            out.append((r[0], r[1], r[2], r[3], r[4], decrypt_text(r[5]) if r[5] else None, int(r[6] or 0), int(r[7] if len(r) > 7 else 1)))
        return out
    except Exception:
        c.execute('SELECT id, name, ip, username, remote_path, ssh_password FROM sync_targets ORDER BY id DESC')
        rows = c.fetchall()
        conn.close()
        out = []
        for r in rows:
            out.append((r[0], r[1], r[2], r[3], r[4], decrypt_text(r[5]) if r[5] else None, 0, 1))
        return out

def list_questions_by_pool(exam_id, pool):
    conn = get_exam_conn()
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
    conn = get_exam_conn()
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
    conn = get_exam_conn()
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

PROGRESS_STATUS_NOT_STARTED = 0
PROGRESS_STATUS_IN_PROGRESS = 1
PROGRESS_STATUS_COMPLETED = 2

def list_progress_modules():
    conn = get_progress_conn()
    c = conn.cursor()
    c.execute('SELECT id, name, created_at FROM progress_modules ORDER BY id ASC')
    rows = c.fetchall()
    conn.close()
    return rows

def upsert_progress_module(name):
    conn = get_progress_conn()
    c = conn.cursor()
    c.execute('SELECT id FROM progress_modules WHERE name=?', (name,))
    row = c.fetchone()
    if row:
        conn.close()
        return int(row[0])
    c.execute('INSERT INTO progress_modules (name, created_at) VALUES (?,?)', (name, now_iso()))
    conn.commit()
    module_id = int(c.lastrowid)
    conn.close()
    return module_id

def delete_progress_module(module_id):
    conn = get_progress_conn()
    c = conn.cursor()
    c.execute('SELECT id FROM progress_tasks WHERE module_id=?', (module_id,))
    task_ids = [int(r[0]) for r in c.fetchall()]
    for tid in task_ids:
        c.execute('DELETE FROM user_task_progress WHERE task_id=?', (tid,))
    c.execute('DELETE FROM progress_tasks WHERE module_id=?', (module_id,))
    c.execute('DELETE FROM progress_modules WHERE id=?', (module_id,))
    conn.commit()
    conn.close()

def list_progress_tasks(module_id=None):
    conn = get_progress_conn()
    c = conn.cursor()
    if module_id is None:
        c.execute('SELECT id, module_id, title, description, sort_order, created_at FROM progress_tasks ORDER BY module_id ASC, sort_order ASC, id ASC')
        rows = c.fetchall()
        conn.close()
        return rows
    c.execute('SELECT id, module_id, title, description, sort_order, created_at FROM progress_tasks WHERE module_id=? ORDER BY sort_order ASC, id ASC', (module_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def upsert_progress_task(module_id, title, description=None, sort_order=0):
    conn = get_progress_conn()
    c = conn.cursor()
    c.execute('SELECT id FROM progress_tasks WHERE module_id=? AND title=?', (module_id, title))
    row = c.fetchone()
    if row:
        task_id = int(row[0])
        c.execute('UPDATE progress_tasks SET description=?, sort_order=? WHERE id=?', (description, int(sort_order), task_id))
        conn.commit()
        conn.close()
        return task_id
    c.execute('INSERT INTO progress_tasks (module_id, title, description, sort_order, created_at) VALUES (?,?,?,?,?)', (int(module_id), title, description, int(sort_order), now_iso()))
    conn.commit()
    task_id = int(c.lastrowid)
    conn.close()
    return task_id

def delete_progress_task(task_id):
    conn = get_progress_conn()
    c = conn.cursor()
    c.execute('DELETE FROM user_task_progress WHERE task_id=?', (task_id,))
    c.execute('DELETE FROM progress_tasks WHERE id=?', (task_id,))
    conn.commit()
    conn.close()

def set_user_task_progress(user_id, task_id, status, updated_by=None):
    status_int = int(status)
    if status_int not in (PROGRESS_STATUS_NOT_STARTED, PROGRESS_STATUS_IN_PROGRESS, PROGRESS_STATUS_COMPLETED):
        raise Exception('无效的任务状态')
    conn = get_progress_conn()
    c = conn.cursor()
    c.execute('DELETE FROM user_task_progress WHERE user_id=? AND task_id=?', (int(user_id), int(task_id)))
    c.execute('INSERT INTO user_task_progress (user_id, task_id, status, updated_at, updated_by) VALUES (?,?,?,?,?)', (int(user_id), int(task_id), status_int, now_iso(), updated_by))
    conn.commit()
    conn.close()

def get_user_task_progress_map(user_id):
    conn = get_progress_conn()
    c = conn.cursor()
    c.execute('SELECT task_id, status, updated_at, updated_by FROM user_task_progress WHERE user_id=?', (int(user_id),))
    rows = c.fetchall()
    conn.close()
    out = {}
    for r in rows:
        out[int(r[0])] = {'status': int(r[1] or 0), 'updated_at': r[2], 'updated_by': r[3]}
    return out

def get_user_progress_tree(user_id):
    modules = list_progress_modules()
    tasks = list_progress_tasks(None)
    status_map = get_user_task_progress_map(user_id)
    modules_map = {}
    result = []
    for m in modules:
        md = {'module_id': int(m[0]), 'module_name': m[1], 'tasks': []}
        modules_map[int(m[0])] = md
        result.append(md)
    for t in tasks:
        tid = int(t[0])
        mid = int(t[1])
        md = modules_map.get(mid)
        if md is None:
            continue
        st = status_map.get(tid, {'status': PROGRESS_STATUS_NOT_STARTED, 'updated_at': None, 'updated_by': None})
        md['tasks'].append({
            'task_id': tid,
            'title': t[2],
            'description': t[3],
            'sort_order': int(t[4] or 0),
            'status': int(st.get('status') or 0),
            'updated_at': st.get('updated_at'),
            'updated_by': st.get('updated_by'),
        })
    for md in result:
        try:
            md['tasks'].sort(key=lambda x: (int(x.get('sort_order') or 0), int(x.get('task_id') or 0)))
        except Exception:
            pass
    return result
