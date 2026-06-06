import os
import random
import uuid
from io import BytesIO
from datetime import datetime, UTC
from PIL import Image
from PySide6.QtGui import QImage
from database import (
    get_uid_conn,
    get_admin_conn,
    get_user_conn,
    get_exam_conn,
    get_score_conn,
    get_config_conn,
    get_progress_conn,
    get_kb_conn,
    now_iso,
    ensure_key_probe,
    verify_db_encryption_key,
    RESOURCE_PATH,
    FILES_DIR,
)
from utils import hash_password, verify_password
import sqlite3
from crypto_util import encrypt_text, decrypt_text, encrypt_json, decrypt_json, aes_bytesio
import hashlib
import hmac
import json
try:
    from conf.secret_key import SECRET_KEY
except Exception:
    SECRET_KEY = 'example'

DELETE_IDENTIFIER = '␡'

import hashlib
import os
import shutil
import mimetypes


def make_exam_uuid(exam_id):
    """使用 exam.id 作为种子生成确定性 UUID v5"""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"exam:{exam_id}"))


def get_exam_uuid(exam_id):
    """从 exams 表查询 uuid，若不存在则用 id 生成"""
    conn = get_exam_conn()
    c = conn.cursor()
    c.execute('SELECT uuid FROM exams WHERE id=?', (exam_id,))
    row = c.fetchone()
    conn.close()
    if row and row[0]:
        return row[0]
    return make_exam_uuid(exam_id)


def get_file_path(sha1):
    """根据 SHA1 在 FILES_DIR 中查找文件（支持带扩展名的文件）"""
    for fname in os.listdir(FILES_DIR):
        if fname.startswith(sha1):
            return os.path.join(FILES_DIR, fname)
    return None


def save_task_file(source_path):
    """保存任务附件到 FILES_DIR，返回文件元数据 dict"""
    if not os.path.exists(source_path):
        return None
    sha1 = hashlib.sha1()
    with open(source_path, 'rb') as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            sha1.update(chunk)
    sha1_hex = sha1.hexdigest()
    _, ext = os.path.splitext(source_path)
    dest = os.path.join(FILES_DIR, sha1_hex + ext)
    if not os.path.exists(dest):
        shutil.copy2(source_path, dest)
    stat = os.stat(dest)
    original_name = os.path.basename(source_path)
    mime_type, _ = mimetypes.guess_type(original_name)
    if not mime_type:
        mime_type = 'application/octet-stream'
    return {
        'sha1': sha1_hex,
        'original_name': original_name,
        'size': stat.st_size,
        'mime': mime_type,
        'uploaded_at': str(now_iso(timestamp=True)),
    }


def delete_task_file(sha1):
    """从 FILES_DIR 删除指定 SHA1 的文件"""
    path = get_file_path(sha1)
    if path and os.path.exists(path):
        os.remove(path)



def create_admin_if_absent():
    uid_conn = get_uid_conn()
    conn = get_user_conn()
    c = conn.cursor()
    uid_c = uid_conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    count_user = c.fetchone()[0]
    conn.close()
    conn = get_admin_conn()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM admins')
    count_admin = c.fetchone()[0]
    if int(count_admin) + int(count_user) == 0:
        try:
            uid_c.execute('INSERT INTO uid_map DEFAULT VALUES')
            uid_conn.commit()
            new_id = uid_c.lastrowid
            uid_conn.close()
            c.execute('INSERT INTO admins (id, username, password_hash, active, created_at, full_name) VALUES (?,?,?,?,?,?)', (new_id, 'admin', hash_password('admin'), 1, now_iso(), encrypt_text('管理员')))
        except Exception:
            uid_c.execute('INSERT INTO uid_map DEFAULT VALUES')
            uid_conn.commit()
            new_id = uid_c.lastrowid
            uid_conn.close()
            c.execute('INSERT INTO admins (id, username, password_hash, active, created_at) VALUES (?,?,?,?,?)', (new_id, 'admin', hash_password('admin'), 1, now_iso()))
        conn.commit()
    conn.close()

def verify_encryption_ok():
    try:
        ensure_key_probe()
        return bool(verify_db_encryption_key())
    except Exception:
        return False

def create_user(username, password, role='user', active=1, full_name=None):
    uid_conn = get_uid_conn()
    conn = get_user_conn()
    c = conn.cursor()
    uid_c = uid_conn.cursor()
    cur_ts = str(now_iso(timestamp=True))
    try:
        uid_c.execute('INSERT INTO uid_map DEFAULT VALUES')
        uid_conn.commit()
        new_id = uid_c.lastrowid
        uid_conn.close()
        c.execute('INSERT INTO users (id, username, password_hash, role, active, created_at, full_name, edit_at) VALUES (?,?,?,?,?,?,?,?)', (new_id, username, hash_password(password), role, active, now_iso(), encrypt_text(full_name) if full_name is not None else None, cur_ts))
    except Exception:
        uid_c.execute('INSERT INTO uid_map DEFAULT VALUES')
        uid_conn.commit()
        new_id = uid_c.lastrowid
        uid_conn.close()
        c.execute('INSERT INTO users (id, username, password_hash, role, active, created_at, edit_at) VALUES (?,?,?,?,?,?,?)', (new_id, username, hash_password(password), role, active, now_iso(), cur_ts))
    conn.commit()
    conn.close()

def create_admin(username, password, active=1, full_name=None):
    uid_conn = get_uid_conn()
    conn = get_admin_conn()
    c = conn.cursor()
    uid_c = uid_conn.cursor()
    cur_ts = str(now_iso(timestamp=True))
    try:
        uid_c.execute('INSERT INTO uid_map DEFAULT VALUES')
        uid_conn.commit()
        new_id = uid_c.lastrowid
        uid_conn.close()
        c.execute('INSERT INTO admins (id, username, password_hash, active, created_at, full_name, edit_at) VALUES (?,?,?,?,?,?,?)', (new_id, username, hash_password(password), active, now_iso(), encrypt_text(full_name) if full_name is not None else None, cur_ts))
    except Exception:
        uid_c.execute('INSERT INTO uid_map DEFAULT VALUES')
        uid_conn.commit()
        new_id = uid_c.lastrowid
        uid_conn.close()
        c.execute('INSERT INTO admins (id, username, password_hash, active, created_at, edit_at) VALUES (?,?,?,?,?,?)', (new_id, username, hash_password(password), active, now_iso(), cur_ts))
    conn.commit()
    conn.close()

def authenticate(username, password):
    # 先查管理员库
    conn_a = get_admin_conn()
    ca = conn_a.cursor()
    ca.execute('SELECT id, username, password_hash, active, full_name, shadow_delete FROM admins WHERE username=?', (username,))
    row_a = ca.fetchone()
    conn_a.close()
    if row_a:
        if row_a[5] == 1:
            return None
        if row_a[3] != 1:
            return None
        if not verify_password(password, row_a[2]):
            return None
        return {'id': row_a[0], 'username': row_a[1], 'role': 'admin', 'full_name': decrypt_text(row_a[4]) if len(row_a) > 4 else None}
    # 再查用户库
    conn_u = get_user_conn()
    cu = conn_u.cursor()
    cu.execute('SELECT id, username, password_hash, active, full_name, shadow_delete FROM users WHERE username=?', (username,))
    row = cu.fetchone()
    conn_u.close()
    if not row:
        return None
    if row[5] == 1:
        return None
    if row[3] != 1:
        return None
    if not verify_password(password, row[2]):
        return None
    return {'id': row[0], 'username': row[1], 'role': 'user', 'full_name': decrypt_text(row[4]) if len(row) > 5 else None}

def list_users():
    conn = get_user_conn()
    c = conn.cursor()
    try:
        c.execute('SELECT id, username, full_name, role, active, created_at FROM users WHERE shadow_delete=0 ORDER BY id DESC')
    except Exception:
        c.execute('SELECT id, username, NULL as full_name, role, active, created_at FROM users WHERE shadow_delete=0 ORDER BY id DESC')
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
        c.execute('SELECT id, username, full_name, active, created_at FROM admins WHERE shadow_delete=0 ORDER BY id DESC')
    except Exception:
        c.execute('SELECT id, username, NULL as full_name, active, created_at FROM admins WHERE shadow_delete=0 ORDER BY id DESC')
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
    current_time = now_iso(timestamp=True)
    if int(active) == 0:
        try:
            c.execute('SELECT COUNT(*) FROM admins WHERE active=1 AND id!=?', (admin_id,))
            remain = c.fetchone()[0]
            if int(remain or 0) <= 0:
                conn.close()
                raise Exception('至少保留一个启用的管理员')
        except Exception:
            pass
    c.execute(f'UPDATE admins '
    f'SET active=?, edit_at="{current_time}" WHERE id=?', 
    (int(active), admin_id))
    conn.commit()
    conn.close()

def update_admin_basic(admin_id, username=None, full_name=None, password=None):
    conn = get_admin_conn()
    c = conn.cursor()
    current_time = now_iso(timestamp=True)
    updates = []
    params = []
    if username is not None:
        updates.append("username=?")
        params.append(username)
    if full_name is not None:
        updates.append("full_name=?")
        params.append(encrypt_text(full_name))
    if password is not None and password.strip():
        updates.append("password_hash=?")
        params.append(hash_password(password))
    
    if not updates:
        conn.close()
        return
        
    params.append(admin_id)
    updates.append(f"edit_at='{current_time}'")
    query = f"UPDATE admins SET {', '.join(updates)} WHERE id=?"
    c.execute(query, tuple(params))
    conn.commit()
    conn.close()

def delete_admin(admin_id, force=False):
    conn = get_admin_conn()
    c = conn.cursor()
    current_time = now_iso(timestamp=True)
    c.execute('SELECT COUNT(*) FROM admins WHERE id!=? AND WHERE shadow_delete=0', (admin_id,))
    remain_total = c.fetchone()[0]
    if int(remain_total or 0) <= 0:
        conn.close()
        raise Exception('至少保留一个管理员')
    try:
        c.execute('SELECT COUNT(*) FROM admins WHERE active=1 AND id!=? AND WHERE shadow_delete=0', (admin_id,))
        remain_active = c.fetchone()[0]
        if int(remain_active or 0) <= 0:
            conn.close()
            raise Exception('至少保留一个启用的管理员')
    except Exception:
        pass
    c.execute('SELECT username FROM admins WHERE id=?', (admin_id,))
    username = c.fetchone()[0]
    if force:
        c.execute('DELETE FROM admins WHERE id=?', (admin_id,))
    else:
        delete_username = f"{str(uuid.uuid4())}_{username}_{DELETE_IDENTIFIER}"
        c.execute(f'UPDATE admins SET username="{delete_username}", shadow_delete=1, edit_at="{current_time}" WHERE id=?', (admin_id,))
    conn.commit()
    conn.close()

def demote_admin_to_user(admin_id):
    current_time = now_iso(timestamp=True)
    aconn = get_admin_conn()
    ac = aconn.cursor()
    ac.execute('SELECT username, password_hash, active, full_name, edit_at FROM admins WHERE id=?', (admin_id,))
    row = ac.fetchone()
    aconn.close()
    if not row:
        raise Exception('管理员不存在')
    username, pwd_hash, active, full_name_cipher, edit_at = row[0], row[1], int(row[2] or 0), row[3], row[4]
    uconn = get_user_conn()
    uc = uconn.cursor()
    uc.execute('SELECT COUNT(*) FROM users WHERE username=?', (username,))
    if int(uc.fetchone()[0] or 0) > 0:
        uconn.close()
        raise Exception('用户名已存在于用户库')
    try:
        uc.execute('INSERT INTO '
        'users (id, username, password_hash, role, active, '
        'created_at, full_name, edit_at) VALUES '
        '(?,?,?,?,?,?,?,?)',
        (admin_id, username, pwd_hash, 'user', active,
        now_iso(), full_name_cipher, str(current_time)))
        uconn.commit()
    finally:
        uconn.close()
    delete_admin(admin_id, force=True)

def promote_user_to_admin(user_id):
    current_time = now_iso(timestamp=True)
    uconn = get_user_conn()
    uc = uconn.cursor()
    uc.execute('SELECT username, password_hash, active, full_name, edit_at FROM users WHERE id=?', (user_id,))
    row = uc.fetchone()
    if not row:
        uconn.close()
        raise Exception('用户不存在')
    username, pwd_hash, active, full_name_cipher, edit_at = row[0], row[1], int(row[2] or 0), row[3], row[4]
    aconn = get_admin_conn()
    ac = aconn.cursor()
    ac.execute('SELECT COUNT(*) FROM admins WHERE username=?', (username,))
    if int(ac.fetchone()[0] or 0) > 0:
        aconn.close()
        uconn.close()
        raise Exception('用户名已存在于管理员库')
    try:
        ac.execute('INSERT INTO '
        'admins (id, username, password_hash, active, '
        'created_at, full_name, edit_at) VALUES '
        '(?,?,?,?,?,?,?)',
        (user_id, username, pwd_hash, active,
        now_iso(), full_name_cipher, str(current_time)))
        aconn.commit()
    finally:
        aconn.close()
    uc.execute('DELETE FROM users WHERE id=?', (user_id,))
    uconn.commit()
    uconn.close()

def add_exam(title, description, pass_ratio, time_limit_minutes, end_date, random_pick_count=0):
    conn = get_exam_conn()
    c = conn.cursor()
    exam_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"exam:{uuid.uuid4()}"))
    c.execute('INSERT INTO exams (uuid, title, description, pass_ratio, time_limit_minutes, end_date, created_at, random_pick_count) VALUES (?,?,?,?,?,?,?,?)', (exam_uuid, encrypt_text(title), encrypt_text(description) if description is not None else None, float(pass_ratio), int(time_limit_minutes), end_date, now_iso(), int(random_pick_count)))
    conn.commit()
    conn.close()

def list_exams(include_expired=False):
    conn = get_exam_conn()
    c = conn.cursor()
    if include_expired:
        c.execute('SELECT id, title, description, pass_ratio, time_limit_minutes, end_date, uuid FROM exams ORDER BY id DESC')
    else:
        c.execute('SELECT id, title, description, pass_ratio, time_limit_minutes, end_date, uuid FROM exams WHERE (end_date>=? OR end_date IS NULL) ORDER BY id DESC', (datetime.now(UTC).isoformat(),))
    rows = c.fetchall()
    conn.close()
    out = []
    for r in rows:
        out.append((r[0], decrypt_text(r[1]) if r[1] else None, decrypt_text(r[2]) if r[2] else None, r[3], r[4], r[5], r[6]))
    return out

def get_exam_title(exam_id):
    conn = get_exam_conn()
    c = conn.cursor()
    c.execute('SELECT title FROM exams WHERE id=?', (exam_id,))
    row = c.fetchone()
    conn.close()
    return decrypt_text(row[0]) if row else None

def add_question(exam_uuid, qtype, text, options, correct_answers, score):
    conn = get_exam_conn()
    c = conn.cursor()
    c.execute('INSERT INTO questions (exam_uuid, type, text, options, correct_answers, score) VALUES (?,?,?,?,?,?)', (exam_uuid, qtype, encrypt_text(text), encrypt_json(options or []), encrypt_json(correct_answers), float(score)))
    conn.commit()
    conn.close()

def list_questions(exam_uuid):
    conn = get_exam_conn()
    c = conn.cursor()
    c.execute('SELECT id, type, text, options, correct_answers, score, pictures FROM questions WHERE exam_uuid=? ORDER BY id', (exam_uuid,))
    rows = c.fetchall()
    conn.close()
    result = []
    for r in rows:
        result.append({
            'id': r[0], 
            'type': r[1], 
            'text': decrypt_text(r[2]) if r[2] else '', 
            'options': decrypt_json(r[3]) or [], 
            'correct': decrypt_json(r[4]) or [], 
            'score': r[5],
            'pictures': r[6]
        })
    return result

def get_exam_stats(exam_uuid):
    conn = get_exam_conn()
    c = conn.cursor()
    c.execute('SELECT COUNT(*), COALESCE(SUM(score), 0) FROM questions WHERE exam_uuid=?', (exam_uuid,))
    row = c.fetchone()
    conn.close()
    cnt = int(row[0]) if row and row[0] is not None else 0
    total = float(row[1]) if row and row[1] is not None else 0.0
    return {'count': cnt, 'total_score': total}

def import_questions_from_json(exam_uuid, payload):
    conn = get_exam_conn()
    c = conn.cursor()
    for q in payload:
        pool = (q.get('pool') or q.get('category') or 'mandatory')
        c.execute('INSERT INTO questions (exam_uuid, type, text, options, correct_answers, score, pictures, pool) VALUES (?,?,?,?,?,?,?,?)', (exam_uuid, q.get('type'), encrypt_text(q.get('text')), encrypt_json(q.get('options') or []), encrypt_json(q.get('correct') or []), float(q.get('score', 1)), q.get('pictures'), pool))
    conn.commit()
    conn.close()

def clear_exam_questions(exam_uuid):
    conn = get_exam_conn()
    c = conn.cursor()
    c.execute("SELECT pictures FROM questions WHERE exam_uuid = ?", (exam_uuid,))
    rows = c.fetchall()
    pic_list = []
    for row in rows:
       if row[0]:
            pic_l = json.loads(row[0])
            pic_list += pic_l
    for p in pic_list:
        picture_path = os.path.join(RESOURCE_PATH, p)
        if os.path.exists(picture_path):
            os.remove(picture_path)
    c.execute('DELETE FROM questions WHERE exam_uuid=?', (exam_uuid,))
    conn.commit()
    conn.close()

def delete_exam(exam_id):
    # 获取 exam_uuid
    exam_uuid = get_exam_uuid(exam_id)
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
    ec.execute("SELECT pictures FROM questions WHERE exam_uuid = ?", (exam_uuid,))
    rows = ec.fetchall()
    pic_list = []
    for row in rows:
       if row[0]:
            pic_l = json.loads(row[0])
            pic_list += pic_l
    for p in pic_list:
        picture_path = os.path.join(RESOURCE_PATH, p)
        if os.path.exists(picture_path):
            os.remove(picture_path)
    ec.execute('DELETE FROM questions WHERE exam_uuid=?', (exam_uuid,))
    ec.execute('DELETE FROM exams WHERE id=?', (exam_id,))
    econn.commit()
    econn.close()

def save_pic(img_io):
    if not os.path.exists(RESOURCE_PATH):
        return False
    img_io.seek(0)
    sha256 = hashlib.sha256()
    sha256.update(img_io.read())
    sha_str = sha256.hexdigest()
    try:
        img_bytes_io = BytesIO()
        img = Image.open(img_io)
        img.save(img_bytes_io, format="PNG")
        img_bytes_encrypted = aes_bytesio(img_bytes_io, secret_key=SECRET_KEY, operation="encrypt")
        with open(os.path.join(RESOURCE_PATH, sha_str), 'wb') as f:
            f.write(img_bytes_encrypted.read())
        return sha_str
    except Exception as e:
        print(f"Save_pic error: {e}")
        return False

def get_pic(sha_str, max_dim=1080):
    filepath = os.path.join(RESOURCE_PATH, sha_str)
    if not os.path.exists(filepath):
        return None
    io_file_encrypted = None
    with open(filepath, 'rb') as f:
        io_file_encrypted = BytesIO(f.read())
    if not io_file_encrypted:
        return None
    io_file = aes_bytesio(io_file_encrypted, secret_key=SECRET_KEY, operation="decrypt")
    img = Image.open(io_file)
    if img.mode not in ("RGB", "RGBA", "L"):
        img = img.convert("RGB")
    width, height = img.size
    if width > max_dim or height > max_dim:
        scale = max_dim / max(width, height)
        new_size = (int(width * scale), int(height * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    data = img.tobytes("raw", img.mode)
    if img.mode == "RGB":
        fmt = QImage.Format.Format_RGB888
    elif img.mode == "RGBA":
        fmt = QImage.Format.Format_RGBA8888
    else:
        fmt = QImage.Format.Format_Grayscale8
    bytes_per_line = len(data) // img.height
    qt_img = QImage(data, img.width, img.height, bytes_per_line, fmt)
    return qt_img


def start_attempt(user_id, exam_id, total_score):
    a_uuid = str(uuid.uuid4())
    conn = get_score_conn()
    c = conn.cursor()
    ts = now_iso()
    checksum = hmac.new(SECRET_KEY.encode('utf-8'), ('|'.join([str(a_uuid), str(user_id), str(exam_id), str(ts), '-', str(0.0), str(0), str(total_score)])).encode('utf-8'), hashlib.sha256).hexdigest()
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
    exam_uuid = get_exam_uuid(exam_id)
    started_at = row[2]
    attempt_total = float(row[3] or 0.0)
    qs = list_questions(exam_uuid)
    total = 0.0
    c.execute('SELECT question_id, selected, cheat, reviewed, manual_score FROM attempt_answers WHERE attempt_uuid=?', (attempt_uuid,))
    answers = {}
    manual_scores = {}
    for r in c.fetchall():
        val = decrypt_json(r[1])
        answers[r[0]] = val if val is not None else []
        manual_scores[r[0]] = float(r[4] or 0.0) if r[3] == 1 else 0.0
        if r[2] == 1:
            cheat = True
            break
    for q in qs:
        if q['type'] == 'essay':
            total += min(manual_scores.get(q['id'], 0.0), float(q['score']))
        else:
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
        checksum = hmac.new(SECRET_KEY.encode('utf-8'), ('|'.join([str(attempt_uuid), str(row[1]), str(exam_id), str(started_at), str(sub_ts), str(total), str(passed), str(attempt_total)])).encode('utf-8'), hashlib.sha256).hexdigest()
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
    if q['type'] == 'fill':
        if sel is None or len(sel) == 0 or not sel[0]:
            return False
        user_ans = str(sel[0]).strip().lower()
        correct_list = [str(a).strip().lower() for a in (q.get('correct') or [])]
        return user_ans in correct_list
    if q['type'] == 'essay':
        # 简答题不能自动评分
        return False
    return False

def list_attempts(user_id=None, username=None):
    history_user_id_list = []
    if username:
        user_conn = get_user_conn()
        uc = user_conn.cursor()
        uc.execute("SELECT id FROM users WHERE username LIKE ? ESCAPE '\\'",
        (f"%\\_{username}\\_%",))
        history_user_id_list = [r[0] for r in uc.fetchall()]
        user_conn.close()
    score_conn = get_score_conn()
    sc = score_conn.cursor()
    if user_id and history_user_id_list:
        all_id = history_user_id_list
        all_id.append(user_id)
        sc.execute('SELECT uuid, user_id, exam_id, started_at, submitted_at, score, passed, total_score, checksum '
        'FROM attempts WHERE user_id IN ({}) ORDER BY id DESC'
        .format(','.join(['?'] * len(all_id))),
         tuple(all_id))
    elif not user_id and history_user_id_list:
        sc.execute(
            'SELECT uuid, user_id, exam_id, started_at, submitted_at, score, passed, total_score, checksum '
            'FROM attempts WHERE user_id IN ({}) ORDER BY id DESC'
            .format(','.join(['?'] * len(history_user_id_list))), 
            tuple(history_user_id_list))
    elif user_id and not history_user_id_list:
        sc.execute('SELECT uuid, user_id, exam_id, started_at, submitted_at, score, passed, total_score, checksum '
        'FROM attempts WHERE user_id=? ORDER BY id DESC', 
        (user_id,))
    else:
        sc.execute('SELECT uuid, user_id, exam_id, started_at, submitted_at, score, passed, total_score, checksum '
        'FROM attempts ORDER BY id DESC')
    rows = sc.fetchall()
    score_conn.close()
    out = []
    for r in rows:
        expect = hmac.new(SECRET_KEY.encode('utf-8'), ('|'.join([str(r[0]), str(r[1]), str(r[2]), str(r[3]), str(r[4]) if r[4] else '-', str(r[5]), str(r[6]), str(r[7])])).encode('utf-8'), hashlib.sha256).hexdigest()
        valid = str(r[8] or '') == expect
        out.append((r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], 1 if valid else 0))
    return out

def get_attempt_answers(attempt_uuid):
    conn = get_score_conn()
    c = conn.cursor()
    c.execute('SELECT question_id, selected, cheat, reviewed, reviewed_by, reviewed_at, manual_score, review_comment FROM attempt_answers WHERE attempt_uuid=?', (attempt_uuid,))
    rows = c.fetchall()
    conn.close()
    result = {}
    for r in rows:
        result[r[0]] = {
            'selected': decrypt_json(r[1]),
            'cheat': bool(r[2]),
            'reviewed': bool(r[3]),
            'reviewed_by': r[4],
            'reviewed_at': r[5],
            'manual_score': float(r[6] or 0.0),
            'review_comment': decrypt_text(r[7]) if r[7] else None,
        }
    return result

def get_attempt(attempt_uuid):
    conn = get_score_conn()
    c = conn.cursor()
    c.execute('SELECT uuid, user_id, exam_id, started_at, submitted_at, score, passed, total_score, checksum FROM attempts WHERE uuid=?', (attempt_uuid,))
    r = c.fetchone()
    conn.close()
    if not r:
        return None
    expect = hmac.new(SECRET_KEY.encode('utf-8'), ('|'.join([str(r[0]), str(r[1]), str(r[2]), str(r[3]), str(r[4]) if r[4] else '-', str(r[5]), str(r[6]), str(r[7])])).encode('utf-8'), hashlib.sha256).hexdigest()
    valid = str(r[8] or '') == expect
    return {
        'uuid': r[0],
        'user_id': r[1],
        'exam_id': r[2],
        'started_at': r[3],
        'submitted_at': r[4],
        'score': r[5],
        'passed': bool(r[6]),
        'total_score': r[7],
        'valid': valid
    }


def save_manual_review(attempt_uuid, question_id, reviewed_by, manual_score, review_comment=None):
    """保存管理员对简答题的批阅"""
    conn = get_score_conn()
    c = conn.cursor()
    c.execute('UPDATE attempt_answers SET reviewed=1, reviewed_by=?, reviewed_at=?, manual_score=?, review_comment=? WHERE attempt_uuid=? AND question_id=?',
              (reviewed_by, now_iso(), float(manual_score), encrypt_text(review_comment) if review_comment else None, attempt_uuid, question_id))
    conn.commit()
    conn.close()


def recalculate_attempt_score(attempt_uuid):
    """重新计算一次attempt的总分（含简答题人工评分）并更新通过状态"""
    conn = get_score_conn()
    c = conn.cursor()
    c.execute('SELECT exam_id, user_id, started_at, total_score FROM attempts WHERE uuid=?', (attempt_uuid,))
    row = c.fetchone()
    if not row:
        conn.close()
        return 0.0, 0
    exam_id = row[0]
    exam_uuid = get_exam_uuid(exam_id)
    started_at = row[2]
    attempt_total = float(row[3] or 0.0)

    qs = list_questions(exam_uuid)
    c.execute('SELECT question_id, selected, cheat, reviewed, manual_score FROM attempt_answers WHERE attempt_uuid=?', (attempt_uuid,))
    answers = {}
    manual_scores = {}
    for r in c.fetchall():
        val = decrypt_json(r[1])
        answers[r[0]] = val if val is not None else []
        manual_scores[r[0]] = float(r[4] or 0.0) if r[3] == 1 else 0.0

    total = 0.0
    for q in qs:
        if q['type'] == 'essay':
            total += min(manual_scores.get(q['id'], 0.0), float(q['score']))
        else:
            total += float(q['score']) if grade_question(q, answers.get(q['id'])) else 0.0

    # 查询通过比例
    econn = get_exam_conn()
    ec = econn.cursor()
    ec.execute('SELECT pass_ratio FROM exams WHERE id=?', (exam_id,))
    pass_ratio = ec.fetchone()[0]
    econn.close()

    denom = attempt_total if attempt_total > 0 else sum(float(q['score']) for q in qs)
    passed = 1 if (denom > 0 and total / denom >= pass_ratio) else 0

    c.execute('SELECT started_at, submitted_at FROM attempts WHERE uuid=?', (attempt_uuid,))
    attempt_row = c.fetchone()
    sub_ts = attempt_row[1]

    c.execute('UPDATE attempts SET score=?, passed=? WHERE uuid=?', (total, passed, attempt_uuid))
    try:
        checksum = hmac.new(SECRET_KEY.encode('utf-8'), ('|'.join([str(attempt_uuid), str(row[1]), str(exam_id), str(started_at), str(sub_ts) if sub_ts else '-', str(total), str(passed), str(attempt_total)])).encode('utf-8'), hashlib.sha256).hexdigest()
        c.execute('UPDATE attempts SET checksum=? WHERE uuid=?', (checksum, attempt_uuid))
    except Exception:
        pass
    conn.commit()
    conn.close()
    return total, passed


def get_unreviewed_essays(exam_id=None):
    """获取所有待批阅的简答题答案"""
    score_conn = get_score_conn()
    sc = score_conn.cursor()
    exam_conn = get_exam_conn()
    ec = exam_conn.cursor()

    if exam_id:
        ec.execute('SELECT id, uuid FROM exams WHERE id=?', (exam_id,))
    else:
        ec.execute('SELECT id, uuid FROM exams')
    exams = ec.fetchall()

    results = []
    for eid, euuid in exams:
        questions = list_questions(euuid)
        essay_qs = [q for q in questions if q['type'] == 'essay']
        if not essay_qs:
            continue
        essay_q_ids = [q['id'] for q in essay_qs]

        placeholders = ','.join(['?'] * len(essay_q_ids))
        sc.execute(f'''
            SELECT aa.id, aa.attempt_uuid, aa.question_id, aa.selected,
                   a.user_id
            FROM attempt_answers aa
            JOIN attempts a ON aa.attempt_uuid = a.uuid
            WHERE aa.question_id IN ({placeholders})
              AND a.exam_id = ?
              AND aa.reviewed = 0
        ''', tuple(essay_q_ids) + (eid,))

        q_map = {q['id']: q for q in essay_qs}
        for r in sc.fetchall():
            results.append({
                'answer_id': r[0],
                'attempt_uuid': r[1],
                'question_id': r[2],
                'selected': decrypt_json(r[3]) or [],
                'exam_id': eid,
                'user_id': r[4],
                'question': q_map.get(r[2]),
            })

    exam_conn.close()
    score_conn.close()
    return results


def has_unreviewed_essay(attempt_uuid):
    """检查一次考试尝试是否有未批阅的简答题"""
    score_conn = get_score_conn()
    sc = score_conn.cursor()
    sc.execute('SELECT exam_id FROM attempts WHERE uuid=?', (attempt_uuid,))
    row = sc.fetchone()
    if not row:
        score_conn.close()
        return False
    exam_id = row[0]
    exam_uuid = get_exam_uuid(exam_id)
    questions = list_questions(exam_uuid)
    essay_ids = [q['id'] for q in questions if q['type'] == 'essay']
    if not essay_ids:
        score_conn.close()
        return False
    placeholders = ','.join(['?'] * len(essay_ids))
    sc.execute(f'SELECT reviewed FROM attempt_answers WHERE attempt_uuid=? AND question_id IN ({placeholders})', (attempt_uuid, *essay_ids))
    for r in sc.fetchall():
        if r[0] == 0:
            score_conn.close()
            return True
    score_conn.close()
    return False


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
                username = ur[1]
                full_name = ur[2]
                if username and username.endswith(DELETE_IDENTIFIER):
                    username = username.split('_')[1]
                users_map[ur[0]] = (username, full_name)
        except Exception:
            uc.execute(f'SELECT id, username, NULL as full_name FROM users WHERE id IN ({placeholders})', tuple(user_ids))
            for ur in uc.fetchall():
                username = ur[1]
                if username and username.endswith(DELETE_IDENTIFIER):
                    username = username.split('_')[1]
                users_map[ur[0]] = (username, None)
    uconn.close()
    out = []
    for r in rows:
        uname, fn = users_map.get(r[1], (None, None))
        expect = hmac.new(SECRET_KEY.encode('utf-8'), ('|'.join([str(r[0]), str(r[1]), str(r[2]), str(r[3]), str(r[4]) if r[4] else '-', str(r[5]), str(r[6]), str(r[7])])).encode('utf-8'), hashlib.sha256).hexdigest()
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
        expect = hmac.new(SECRET_KEY.encode('utf-8'), ('|'.join([str(r[0]), str(r[1]), str(r[2]), str(r[3]), str(r[4]) if r[4] else '-', str(r[5]), str(r[6]), str(r[7])])).encode('utf-8'), hashlib.sha256).hexdigest()
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
            try:
                rcur2.execute('SELECT question_id, selected, cheat, reviewed, reviewed_by, reviewed_at, manual_score, review_comment FROM attempt_answers WHERE attempt_uuid=?', (a[0],))
                for aa in rcur2.fetchall():
                    lcur.execute('INSERT INTO attempt_answers (attempt_uuid, question_id, selected, cheat, reviewed, reviewed_by, reviewed_at, manual_score, review_comment) VALUES (?,?,?,?,?,?,?,?,?)', (a[0], aa[0], aa[1], aa[2], aa[3], aa[4], aa[5], aa[6], aa[7]))
            except Exception:
                rcur2.execute('SELECT question_id, selected FROM attempt_answers WHERE attempt_uuid=?', (a[0],))
                for aa in rcur2.fetchall():
                    lcur.execute('INSERT INTO attempt_answers (attempt_uuid, question_id, selected) VALUES (?,?,?)', (a[0], aa[0], aa[1]))
    lconn.commit()
    rconn.close()
    lconn.close()

def merge_exam_databases(remote_exams_db_path):
    """Merge exams.db by uuid: if uuid exists locally, keep local; if new uuid from remote, insert it."""
    lconn = get_exam_conn()
    lcur = lconn.cursor()
    rconn = sqlite3.connect(remote_exams_db_path)
    rcur = rconn.cursor()

    # 1. Merge exams table: compare by uuid, insert only new ones
    rcur.execute('SELECT id, uuid, title, description, pass_ratio, time_limit_minutes, end_date, created_at, random_pick_count FROM exams')
    remote_exams = rcur.fetchall()
    new_uuids = []
    for exam_row in remote_exams:
        exam_uuid = exam_row[1]
        lcur.execute('SELECT COUNT(*) FROM exams WHERE uuid=?', (exam_uuid,))
        if lcur.fetchone()[0] == 0:
            lcur.execute('INSERT INTO exams (uuid, title, description, pass_ratio, time_limit_minutes, end_date, created_at, random_pick_count) VALUES (?,?,?,?,?,?,?,?)',
                         (exam_row[1], exam_row[2], exam_row[3], exam_row[4], exam_row[5], exam_row[6], exam_row[7], exam_row[8]))
            new_uuids.append(exam_uuid)

    # 2. Merge questions table: insert questions belonging to newly added exams
    if new_uuids:
        for exam_uuid in new_uuids:
            rcur.execute('SELECT exam_uuid, type, text, options, correct_answers, score, pictures, pool FROM questions WHERE exam_uuid=?', (exam_uuid,))
            for q_row in rcur.fetchall():
                lcur.execute('INSERT INTO questions (exam_uuid, type, text, options, correct_answers, score, pictures, pool) VALUES (?,?,?,?,?,?,?,?)', q_row)

    lconn.commit()
    rconn.close()
    lconn.close()


def merge_admin_databases(remote_admin_db_path):
    lconn = get_admin_conn()
    lcur = lconn.cursor()
    rconn = sqlite3.connect(remote_admin_db_path)
    rcur = rconn.cursor()

    rcur.execute('PRAGMA table_info(admins)')
    cols = [info[1] for info in rcur.fetchall()]
    col_str = ', '.join(cols)
    placeholders = ', '.join(['?'] * len(cols))
    
    rcur.execute(f'SELECT {col_str} FROM admins')
    remote_rows = rcur.fetchall()
    
    for row in remote_rows:
        data = dict(zip(cols, row))
        username = data['username']
        remote_edit_at = int(data['edit_at'] or 0)
        remote_shadow_delete = int(data.get('shadow_delete', 0))
        
        # 处理删除同步逻辑：如果远程是已删除记录，尝试同步删除本地活跃记录
        if remote_shadow_delete == 1:
            parts = username.split('_')
            if len(parts) >= 3 and parts[-1] == DELETE_IDENTIFIER:
                original_username = '_'.join(parts[1:-1])
                lcur.execute('SELECT id, edit_at FROM admins WHERE username=? AND shadow_delete=0', (original_username,))
                lrow_active = lcur.fetchone()
                if lrow_active:
                    local_id, local_edit_at = lrow_active[0], int(lrow_active[1] or 0)
                    if remote_edit_at > local_edit_at:
                        # 远程删除时间更晚，本地也标记为删除
                        current_time = str(now_iso(timestamp=True))
                        delete_username = f"{str(uuid.uuid4())}_{original_username}_{DELETE_IDENTIFIER}"
                        lcur.execute('UPDATE admins SET username=?, shadow_delete=1, edit_at=? WHERE id=?', (delete_username, current_time, local_id))
        
        lcur.execute('SELECT edit_at FROM admins WHERE username=?', (username,))
        lrow = lcur.fetchone()
        
        if not lrow:
            # 不存在则插入
            lcur.execute(f'INSERT INTO admins ({col_str}) VALUES ({placeholders})', row)
        else:
            local_edit_at = int(lrow[0] or 0)
            if remote_edit_at > local_edit_at:
                # 远程更晚则更新
                set_clause = ', '.join([f"{c}=?" for c in cols])
                lcur.execute(f'UPDATE admins SET {set_clause} WHERE username=?', row + (username,))
                
    lconn.commit()
    rconn.close()
    lconn.close()

def merge_user_databases(remote_user_db_path):
    lconn = get_user_conn()
    lcur = lconn.cursor()
    rconn = sqlite3.connect(remote_user_db_path)
    rcur = rconn.cursor()
    
    rcur.execute('PRAGMA table_info(users)')
    cols = [info[1] for info in rcur.fetchall()]
    col_str = ', '.join(cols)
    placeholders = ', '.join(['?'] * len(cols))
    
    rcur.execute(f'SELECT {col_str} FROM users')
    remote_rows = rcur.fetchall()
    
    for row in remote_rows:
        data = dict(zip(cols, row))
        username = data['username']
        remote_edit_at = int(data['edit_at'] or 0)
        remote_shadow_delete = int(data.get('shadow_delete', 0))
        
        # 处理删除同步逻辑：如果远程是已删除记录，尝试同步删除本地活跃记录
        if remote_shadow_delete == 1:
            parts = username.split('_')
            if len(parts) >= 3 and parts[-1] == DELETE_IDENTIFIER:
                original_username = '_'.join(parts[1:-1])
                lcur.execute('SELECT id, edit_at FROM users WHERE username=? AND shadow_delete=0', (original_username,))
                lrow_active = lcur.fetchone()
                if lrow_active:
                    local_id, local_edit_at = lrow_active[0], int(lrow_active[1] or 0)
                    if remote_edit_at > local_edit_at:
                        # 远程删除时间更晚，本地也标记为删除
                        current_time = str(now_iso(timestamp=True))
                        delete_username = f"{str(uuid.uuid4())}_{original_username}_{DELETE_IDENTIFIER}"
                        lcur.execute('UPDATE users SET username=?, shadow_delete=1, edit_at=? WHERE id=?', (delete_username, current_time, local_id))
        
        lcur.execute('SELECT edit_at FROM users WHERE username=?', (username,))
        lrow = lcur.fetchone()
        
        if not lrow:
            # 不存在则插入
            lcur.execute(f'INSERT INTO users ({col_str}) VALUES ({placeholders})', row)
        else:
            local_edit_at = int(lrow[0] or 0)
            if remote_edit_at > local_edit_at:
                # 远程更晚则更新
                set_clause = ', '.join([f"{c}=?" for c in cols])
                lcur.execute(f'UPDATE users SET {set_clause} WHERE username=?', row + (username,))
                
    lconn.commit()
    rconn.close()
    lconn.close()

def delete_user(user_id):
    conn = get_user_conn()
    c = conn.cursor()
    current_time = now_iso(timestamp=True)
    c.execute('SELECT username FROM users WHERE id=?', (user_id,))
    username = c.fetchone()[0]
    delete_username = f"{str(uuid.uuid4())}_{username}_{DELETE_IDENTIFIER}"
    c.execute(f'UPDATE users SET username="{delete_username}", shadow_delete=1, edit_at="{current_time}" WHERE id=?', (user_id,))
    conn.commit()
    conn.close()

def update_user_role(user_id, role):
    conn = get_user_conn()
    c = conn.cursor()
    current_time = now_iso(timestamp=True)
    c.execute(f'UPDATE users SET role="{role}", edit_at="{current_time}" WHERE id=?', (user_id,))
    conn.commit()
    conn.close()

def update_user_active(user_id, active):
    conn = get_user_conn()
    c = conn.cursor()
    current_time = now_iso(timestamp=True)
    c.execute(f'UPDATE users SET active={int(active)}, edit_at="{current_time}" WHERE id=?', (user_id,))
    conn.commit()
    conn.close()

def update_user_basic(user_id, username=None, full_name=None, password=None):
    conn = get_user_conn()
    c = conn.cursor()
    current_time = now_iso(timestamp=True)
    updates = []
    params = []
    if username is not None:
        updates.append("username=?")
        params.append(username)
    if full_name is not None:
        updates.append("full_name=?")
        params.append(encrypt_text(full_name))
    if password is not None and password.strip():
        updates.append("password_hash=?")
        params.append(hash_password(password))
    
    if not updates:
        conn.close()
        return
        
    params.append(user_id)
    updates.append(f"edit_at='{current_time}'")
    query = f"UPDATE users SET {', '.join(updates)} WHERE id=?"
    c.execute(query, tuple(params))
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

def list_questions_by_pool(exam_uuid, pool):
    conn = get_exam_conn()
    c = conn.cursor()
    try:
        c.execute('SELECT id, type, text, options, correct_answers, score, pictures FROM questions WHERE exam_uuid=? AND (pool=? OR (pool IS NULL AND ?="mandatory")) ORDER BY id', (exam_uuid, pool, pool))
    except Exception:
        c.execute('SELECT id, type, text, options, correct_answers, score, pictures FROM questions WHERE exam_uuid=? ORDER BY id', (exam_uuid,))
    rows = c.fetchall()
    conn.close()
    out = []
    for r in rows:
        out.append({'id': r[0], 'type': r[1], 'text': decrypt_text(r[2]) if r[2] else '', 'options': decrypt_json(r[3]) or [], 'correct': decrypt_json(r[4]) or [], 'score': r[5], 'pictures': r[6]})
    return out

def get_exam_random_pick_count(exam_uuid):
    conn = get_exam_conn()
    c = conn.cursor()
    try:
        c.execute('SELECT random_pick_count FROM exams WHERE uuid=?', (exam_uuid,))
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

def build_exam_questions_for_attempt(exam_uuid):
    mandatory = list_questions_by_pool(exam_uuid, 'mandatory')
    random_pool = list_questions_by_pool(exam_uuid, 'random')
    pick = get_exam_random_pick_count(exam_uuid)
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

def set_user_task_progress(user_id, task_id, status, updated_by=None, files=None):
    status_int = int(status)
    if status_int not in (PROGRESS_STATUS_NOT_STARTED, PROGRESS_STATUS_IN_PROGRESS, PROGRESS_STATUS_COMPLETED):
        raise Exception('无效的任务状态')
    conn = get_progress_conn()
    c = conn.cursor()
    c.execute('DELETE FROM user_task_progress WHERE user_id=? AND task_id=?', (int(user_id), int(task_id)))
    files_json = json.dumps(files) if files else None
    c.execute('INSERT INTO user_task_progress (user_id, task_id, status, updated_at, updated_by, files) VALUES (?,?,?,?,?,?)', (int(user_id), int(task_id), status_int, now_iso(), updated_by, files_json))
    conn.commit()
    conn.close()

def get_user_task_progress_map(user_id):
    conn = get_progress_conn()
    c = conn.cursor()
    c.execute('SELECT task_id, status, updated_at, updated_by, files FROM user_task_progress WHERE user_id=?', (int(user_id),))
    rows = c.fetchall()
    conn.close()
    out = {}
    for r in rows:
        files_data = json.loads(r[4]) if r[4] else None
        out[int(r[0])] = {'status': int(r[1] or 0), 'updated_at': r[2], 'updated_by': r[3], 'files': files_data}
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
        st = status_map.get(tid, {'status': PROGRESS_STATUS_NOT_STARTED, 'updated_at': None, 'updated_by': None, 'files': None})
        md['tasks'].append({
            'task_id': tid,
            'title': t[2],
            'description': t[3],
            'sort_order': int(t[4] or 0),
            'status': int(st.get('status') or 0),
            'updated_at': st.get('updated_at'),
            'updated_by': st.get('updated_by'),
            'files': st.get('files'),
        })
    for md in result:
        try:
            md['tasks'].sort(key=lambda x: (int(x.get('sort_order') or 0), int(x.get('task_id') or 0)))
        except Exception:
            pass
    return result


# ===== 知识库 =====

def save_knowledge_file(source_path, user_id, username, category, keywords):
    """保存文件到知识库，返回文件元数据"""
    if not os.path.exists(source_path):
        return None
    sha1 = hashlib.sha1()
    with open(source_path, 'rb') as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            sha1.update(chunk)
    sha1_hex = sha1.hexdigest()
    _, ext = os.path.splitext(source_path)
    dest = os.path.join(FILES_DIR, sha1_hex + ext)
    if not os.path.exists(dest):
        shutil.copy2(source_path, dest)
    original_name = os.path.basename(source_path)
    conn = get_kb_conn()
    c = conn.cursor()
    # 检查 sha1 是否已存在
    c.execute('SELECT id FROM knowledge_base WHERE sha1=?', (sha1_hex,))
    existing = c.fetchone()
    now = now_iso()
    if existing:
        # 如果已删除则恢复
        file_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f'kb:{existing[0]}'))
        c.execute("UPDATE knowledge_base SET deleted=0, edit_at=? WHERE id=?", (now, existing[0]))
    else:
        c.execute('INSERT INTO knowledge_base (user_id, username, filename, sha1, category, keywords, uploaded_at, edit_at) VALUES (?,?,?,?,?,?,?,?)',
                  (user_id, username, original_name, sha1_hex, category, keywords, now, now))
        conn.commit()
        # 为刚插入的记录生成 uuid
        c.execute('SELECT id FROM knowledge_base WHERE uuid IS NULL ORDER BY id DESC LIMIT 1')
        row = c.fetchone()
        if row:
            file_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f'kb:{row[0]}'))
            c.execute("UPDATE knowledge_base SET uuid=? WHERE id=?", (file_uuid, row[0]))
    conn.commit()
    conn.close()
    return {'sha1': sha1_hex, 'filename': original_name}


def list_knowledge_files(keyword=None, category=None, uploader=None, show_deleted=False):
    """查询知识库文件，支持按关键词/分类/上传者筛选"""
    conn = get_kb_conn()
    c = conn.cursor()
    conditions = []
    params = []
    if not show_deleted:
        conditions.append('deleted=0')
    if keyword:
        conditions.append('(filename LIKE ? OR keywords LIKE ?)')
        params.extend([f'%{keyword}%', f'%{keyword}%'])
    if category:
        conditions.append('category=?')
        params.append(category)
    if uploader:
        conditions.append('(username LIKE ? OR user_id=?)')
        params.extend([f'%{uploader}%', uploader])
    where = ' WHERE ' + ' AND '.join(conditions) if conditions else ''
    c.execute(f'SELECT id, uuid, user_id, username, filename, sha1, category, keywords, uploaded_at, edit_at, deleted FROM knowledge_base{where} ORDER BY id DESC')
    rows = c.fetchall()
    conn.close()
    return [{
        'id': r[0],
        'uuid': r[1],
        'user_id': r[2],
        'username': r[3],
        'filename': r[4],
        'sha1': r[5],
        'category': r[6] or '',
        'keywords': r[7] or '',
        'uploaded_at': r[8],
        'edit_at': r[9],
        'deleted': r[10],
    } for r in rows]


def list_knowledge_categories():
    """获取所有分类（排除已删除）"""
    conn = get_kb_conn()
    c = conn.cursor()
    c.execute('SELECT DISTINCT category FROM knowledge_base WHERE category!=\'\' AND deleted=0 ORDER BY category')
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]


def list_knowledge_uploaders():
    """获取所有上传者用户名（排除已删除）"""
    conn = get_kb_conn()
    c = conn.cursor()
    c.execute('SELECT DISTINCT username FROM knowledge_base WHERE deleted=0 ORDER BY username')
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]


def delete_knowledge_file(kb_id, user_id=None, is_admin=False):
    """软删除知识库记录（标记 deleted=1）"""
    conn = get_kb_conn()
    c = conn.cursor()
    c.execute('SELECT user_id FROM knowledge_base WHERE id=?', (kb_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return False
    if not is_admin and row[0] != user_id:
        conn.close()
        return False
    now = now_iso()
    c.execute('UPDATE knowledge_base SET deleted=1, edit_at=? WHERE id=?', (now, kb_id))
    conn.commit()
    conn.close()
    return True


def get_knowledge_file_path(sha1):
    """获取知识库文件的完整路径"""
    return get_file_path(sha1)


def merge_knowledge_databases(remote_kb_path):
    """合并远程 knowledge.db（按 uuid 和 edit_at 去重）"""
    if not os.path.exists(remote_kb_path):
        return
    lconn = get_kb_conn()
    rconn = sqlite3.connect(remote_kb_path)
    lc = lconn.cursor()
    rc = rconn.cursor()
    try:
        rc.execute('SELECT id, uuid, user_id, username, filename, sha1, category, keywords, uploaded_at, edit_at, deleted FROM knowledge_base')
        remote_rows = rc.fetchall()
    except Exception:
        rconn.close()
        return

    for row in remote_rows:
        (rid, ruuid, user_id, username, filename, sha1, category, keywords,
         uploaded_at, edit_at, deleted) = row
        if not ruuid:
            ruuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f'kb:{rid}'))
        # 查本地是否有同 uuid
        lc.execute('SELECT id, edit_at, deleted FROM knowledge_base WHERE uuid=?', (ruuid,))
        local = lc.fetchone()
        now = now_iso()
        if local:
            local_id, local_edit_at, local_deleted = local
            # 比较 edit_at：保留最新的
            remote_time = edit_at or ''
            local_time = local_edit_at or ''
            if remote_time > local_time:
                lc.execute('''UPDATE knowledge_base SET
                    user_id=?, username=?, filename=?, sha1=?, category=?,
                    keywords=?, uploaded_at=?, edit_at=?, deleted=?
                    WHERE id=?''',
                    (user_id, username, filename, sha1, category, keywords,
                     uploaded_at, edit_at, deleted, local_id))
        else:
            # 新记录直接插入
            lc.execute('''INSERT INTO knowledge_base
                (uuid, user_id, username, filename, sha1, category, keywords, uploaded_at, edit_at, deleted)
                VALUES (?,?,?,?,?,?,?,?,?,?)''',
                (ruuid, user_id, username, filename, sha1, category, keywords,
                 uploaded_at or now, edit_at or now, deleted))
    lconn.commit()
    rconn.close()
    lconn.close()
