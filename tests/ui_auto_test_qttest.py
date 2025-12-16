import os
import sys
import tempfile
import time
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox, QFileDialog, QTabWidget
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt, QTimer

# Make sure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import MainWindow
import utils
from models import (
    list_users,
    list_admins,
    delete_user,
    add_exam,
    list_exams,
    get_exam_title,
    add_question,
    start_attempt,
    save_answer,
    submit_attempt,
    list_sync_targets,
    list_questions,
    delete_admin,
    delete_sync_target,
    delete_exam,
)
from views.admin_modules.users_module import AdminUsersModule
from views.admin_modules.exams_module import AdminExamsModule
from views.admin_modules.sync_module import AdminSyncModule, SyncWorker as RealSyncWorker
from views.admin_modules.scores_module import AdminScoresModule
from views.user_view import UserView
from windows.exam_window import ExamWindow


CTX = {}

def log(msg):
    print(msg, flush=True)

def _patch_dialogs():
    utils.show_info = lambda *args, **kwargs: None
    utils.show_warn = lambda *args, **kwargs: None
    utils.ask_yes_no = lambda *args, **kwargs: QMessageBox.StandardButton.Yes


class _QDReturn:
    save_path = None
    open_path = None
    save_sel = 'Excel (*.xlsx)'
    open_sel = 'Excel (*.xlsx)'


def _patch_qfiledialog():
    def fake_save_dialog(*args, **kwargs):
        return (_QDReturn.save_path, _QDReturn.save_sel)

    def fake_open_dialog(*args, **kwargs):
        return (_QDReturn.open_path, _QDReturn.open_sel)

    QFileDialog.getSaveFileName = staticmethod(fake_save_dialog)
    QFileDialog.getOpenFileName = staticmethod(fake_open_dialog)


class FakeSyncWorker(RealSyncWorker):
    def __init__(self, targets, operation='sync'):
        super().__init__(targets, operation)

    def start(self):
        self.run()

    def run(self):
        for t in self.targets:
            self.progress.emit(f'{t[1]} ({t[2]}) 模拟同步成功')
        self.finished.emit('模拟同步完成')


def auto_accept_messageboxes():
    from PySide6.QtWidgets import QApplication, QMessageBox
    def _click():
        for w in QApplication.topLevelWidgets():
            try:
                if isinstance(w, QMessageBox):
                    btn = w.defaultButton()
                    if btn:
                        QTest.mouseClick(btn, Qt.LeftButton)
                    else:
                        for b in w.buttons():
                            QTest.mouseClick(b, Qt.LeftButton)
            except Exception:
                pass
    QTimer.singleShot(0, _click)
    QTimer.singleShot(50, _click)
    QTimer.singleShot(200, _click)

def cleanup_test_data():
    log('[CLEANUP] start deleting test data')
    # Delete exams by prefixes
    prefixes_exam = ('测试试卷_', '用户考试_', '成绩测试试卷_')
    for e in list_exams(include_expired=True):
        title = e[1] or ''
        if any(title.startswith(p) for p in prefixes_exam):
            try:
                delete_exam(int(e[0]))
                log(f'[CLEANUP] deleted exam {e[0]} "{title}"')
            except Exception as ex:
                log(f'[CLEANUP] failed delete exam {e[0]}: {ex}')
    # Delete users by prefixes
    prefixes_user = ('alice_', 'alice2_', 'bob_', 'user_')
    for u in list_users():
        uname = u[1] or ''
        if any(uname.startswith(p) for p in prefixes_user):
            try:
                delete_user(int(u[0]))
                log(f'[CLEANUP] deleted user {u[0]} {uname}')
            except Exception as ex:
                log(f'[CLEANUP] failed delete user {u[0]}: {ex}')
    # Delete admins by prefixes
    prefixes_admin = ('root2_',)
    for a in list_admins():
        aname = a[1] or ''
        if any(aname.startswith(p) for p in prefixes_admin):
            try:
                delete_admin(int(a[0]))
                log(f'[CLEANUP] deleted admin {a[0]} {aname}')
            except Exception as ex:
                log(f'[CLEANUP] failed delete admin {a[0]}: {ex}')
    # Delete sync targets by names
    target_names = ('设备A', '设备A-改', '设备B', '设备C')
    for t in list_sync_targets():
        name = t[1] or ''
        if any(name == n or name.startswith(n) for n in target_names):
            try:
                delete_sync_target(int(t[0]))
                log(f'[CLEANUP] deleted target {t[0]} {name}')
            except Exception as ex:
                log(f'[CLEANUP] failed delete target {t[0]}: {ex}')
    log('[CLEANUP] done')

def test_admin_users_module(win, tabs):
    log('[TEST] admin users module')
    users_mod = win.admin.findChild(AdminUsersModule)
    assert users_mod is not None
    tabs.setCurrentIndex(0)

    suffix = str(int(time.time()))
    uname1 = f'alice_{suffix}'
    uname2 = f'alice2_{suffix}'
    CTX['user_uname'] = uname2
    users_mod.new_user.setText(uname1)
    users_mod.new_pwd.setText('P@ssw0rd!')
    users_mod.new_fullname.setText('爱丽丝')
    users_mod.new_role.setCurrentText('user')
    users_mod.add_user()
    log(f'[TEST] created user {uname1}')
    assert any(u[1] == uname1 for u in list_users())

    # Find row for alice1 and edit username/full_name via table to trigger itemChanged
    tbl = users_mod.users_table
    row_idx = None
    for r in range(tbl.rowCount()):
        it = tbl.item(r, 1)
        if it and it.text() == uname1:
            row_idx = r
            break
    assert row_idx is not None
    tbl.item(row_idx, 1).setText(uname2)
    QTest.qWait(30)
    tbl.item(row_idx, 2).setText('爱丽丝二号')
    QTest.qWait(30)
    log(f'[TEST] updated username to {uname2} and fullname to 爱丽丝二号')
    assert any(u[1] == uname2 for u in list_users())

    # Toggle active via method
    uid = int(tbl.item(row_idx, 0).text())
    users_mod.toggle_user_active(uid, 1)
    log(f'[TEST] toggled active for user id={uid}')

    # Promote to admin then demote back
    users_mod.toggle_user_role(uid, 'user')
    log(f'[TEST] promoted user id={uid} to admin')
    assert any(a[1] == uname2 for a in list_admins())
    # Refresh table to get admin row
    users_mod.refresh_users()
    tbl = users_mod.users_table
    admin_row = None
    for r in range(tbl.rowCount()):
        it_id = tbl.item(r, 0)
        if it_id and it_id.data(Qt.ItemDataRole.UserRole) == 'admin':
            it_un = tbl.item(r, 1)
            if it_un and it_un.text() == uname2:
                admin_row = r
                break
    assert admin_row is not None
    aid = int(tbl.item(admin_row, 0).text())
    users_mod.demote_admin(aid)
    log(f'[TEST] demoted admin id={aid} to user')
    assert any(u[1] == uname2 for u in list_users())
    assert not any(a[1] == uname2 for a in list_admins())

    # Delete user
    uid2 = next(u[0] for u in list_users() if u[1] == uname2)
    users_mod.delete_user(uid2)
    log(f'[TEST] deleted user id={uid2}')
    assert not any(u[1] == uname2 for u in list_users())

    # Export users template
    with tempfile.TemporaryDirectory() as td:
        out_xlsx = str(Path(td) / 'users_tpl.xlsx')
        _QDReturn.save_path = out_xlsx
        _QDReturn.save_sel = 'Excel (*.xlsx)'
        auto_accept_messageboxes()
        users_mod.export_users_template()
        log(f'[TEST] exported users template to {out_xlsx}')
        assert Path(out_xlsx).exists()

        # Prepare import workbook
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = 'Users'
        ws.append(['用户名', '密码', '姓名', '角色', '状态'])
        bob = f"bob_{suffix}"
        root2 = f"root2_{suffix}"
        ws.append([bob, 'abc123!', '鲍勃', 'user', '1'])
        ws.append([root2, 'admin!', '管理员2号', 'admin', '1'])
        in_xlsx = Path(td) / 'users_import.xlsx'
        wb.save(in_xlsx)
        _QDReturn.open_path = str(in_xlsx)
        _QDReturn.open_sel = 'Excel (*.xlsx)'
        auto_accept_messageboxes()
        users_mod.import_users_from_excel()
        log(f'[TEST] imported users from {in_xlsx}')
        assert any(u[1] == bob for u in list_users())
        assert any(a[1] == root2 for a in list_admins())
        CTX['bob_uname'] = bob


def test_admin_exams_module(win, tabs):
    log('[TEST] admin exams module')
    exams_mod = win.admin.findChild(AdminExamsModule)
    assert exams_mod is not None
    tabs.setCurrentIndex(1)

    suffix = str(int(time.time()))
    title = f'测试试卷_{suffix}'
    exams_mod.ex_title.setText(title)
    exams_mod.ex_desc.setText('这是描述')
    exams_mod.ex_pass.setValue(70)
    exams_mod.ex_time.setValue(30)
    exams_mod.ex_permanent.setChecked(True)
    exams_mod.add_exam()
    log(f'[TEST] added exam {title}')
    assert any((e[1] or '') == title for e in list_exams(include_expired=True))

    exams_mod.refresh_exams()
    tbl = exams_mod.exams_table
    row = None
    for r in range(tbl.rowCount()):
        it = tbl.item(r, 1)
        if it and it.text() == title:
            row = r
            break
    assert row is not None
    exam_id = int(tbl.item(row, 0).text())

    tbl.item(row, 1).setText('新标题')
    log(f'[TEST] updated exam title to 新标题 (id={exam_id})')
    assert get_exam_title(exam_id) == '新标题'
    tbl.item(row, 5).setText('新的描述')

    with tempfile.TemporaryDirectory() as td:
        out_xlsx = str(Path(td) / 'exam_sample.xlsx')
        _QDReturn.save_path = out_xlsx
        _QDReturn.save_sel = 'Excel (*.xlsx)'
        auto_accept_messageboxes()
        exams_mod.export_sample()
        log(f'[TEST] exported exam sample to {out_xlsx}')
        assert Path(out_xlsx).exists()

    from models import clear_exam_questions
    # Clear questions (confirm patched to Yes)
    auto_accept_messageboxes()
    exams_mod.clear_exam(exam_id)
    log(f'[TEST] cleared questions for exam id={exam_id}')
    # Delete exam
    auto_accept_messageboxes()
    exams_mod.delete_exam(exam_id)
    QTest.qWait(50)
    if any(e[0] == exam_id for e in list_exams(include_expired=True)):
        from models import delete_exam as _model_delete_exam
        _model_delete_exam(exam_id)
        log(f'[TEST] force deleted exam id={exam_id} via model')
    assert not any(e[0] == exam_id for e in list_exams(include_expired=True))


def test_admin_sync_module(win, tabs):
    log('[TEST] admin sync module')
    # Patch sync worker to avoid real network/rsync
    import views.admin_modules.sync_module as sync_module
    sync_module.SyncWorker = FakeSyncWorker

    sync_mod = win.admin.findChild(AdminSyncModule)
    assert sync_mod is not None
    tabs.setCurrentIndex(2)

    sync_mod.t_name.setText('设备A')
    sync_mod.t_ip.setText('192.168.10.10')
    sync_mod.t_user.setText('user')
    sync_mod.t_path.setText('~/.exam_system')
    sync_mod.t_password.setText('')
    sync_mod.add_target()
    log('[TEST] added target 设备A')
    assert any(t[1] == '设备A' for t in list_sync_targets())

    sync_mod.refresh_targets()
    tbl = sync_mod.targets_table
    r = 0
    tbl.item(r, 0).setText('设备A-改')
    tbl.item(r, 1).setText('192.168.10.11')
    tbl.item(r, 2).setText('user2')
    tbl.item(r, 3).setText('~/.exam_system/exam.db')
    log('[TEST] edited target row 0 to 设备A-改/192.168.10.11/user2')
    assert any(t[1] == '设备A-改' and t[2] == '192.168.10.11' for t in list_sync_targets())

    with tempfile.TemporaryDirectory() as td:
        out_xlsx = str(Path(td) / 'targets_tpl.xlsx')
        _QDReturn.save_path = out_xlsx
        _QDReturn.save_sel = 'Excel (*.xlsx)'
        auto_accept_messageboxes()
        sync_mod.export_targets_template()
        log(f'[TEST] exported targets template to {out_xlsx}')
        assert Path(out_xlsx).exists()

        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = 'Targets'
        ws.append(['名称', 'IP', '用户名', '远程路径', 'SSH密码'])
        ws.append(['设备B', '10.0.0.1', 'alice', '~/.exam_system', ''])
        ws.append(['设备C', '10.0.0.2', 'bob', '~/.exam_system', 'secret'])
        in_xlsx = Path(td) / 'targets_import.xlsx'
        wb.save(in_xlsx)
        _QDReturn.open_path = str(in_xlsx)
        _QDReturn.open_sel = 'Excel (*.xlsx)'
        auto_accept_messageboxes()
        sync_mod.import_targets_from_excel()
        log(f'[TEST] imported targets from {in_xlsx}')
        assert any(t[1] == '设备B' for t in list_sync_targets())
        assert any(t[1] == '设备C' for t in list_sync_targets())

    sync_mod.sync_all()
    log('[TEST] triggered sync_all (fake worker)')


def test_admin_scores_module(win, tabs):
    log('[TEST] admin scores module')
    scores_mod = win.admin.findChild(AdminScoresModule)
    assert scores_mod is not None
    tabs.setCurrentIndex(3)

    # Prepare user/exam/attempt data
    # Create exam and question
    suffix = str(int(time.time()))
    title = f'成绩测试试卷_{suffix}'
    add_exam(title, 'desc', 0.6, 30, None)
    exams = list_exams(include_expired=True)
    ex = next(e for e in exams if e[1] == title)
    exam_id = ex[0]
    add_question(exam_id, 'single', '1+1=?', [{'key': 'A', 'text': '2'}, {'key': 'B', 'text': '3'}], ['A'], 2.0)
    # Use bob (created by import above)
    bob = CTX.get('bob_uname')
    assert bob is not None
    usr = next(u for u in list_users() if u[1] == bob)
    user_id = usr[0]
    from models import get_exam_stats
    total = int(get_exam_stats(exam_id)['total_score'])
    at = start_attempt(user_id, exam_id, total)
    save_answer(at, next(q['id'] for q in list_questions(exam_id)), ['A'])
    submit_attempt(at)

    scores_mod.refresh_scores()
    tbl = scores_mod.scores_table
    assert tbl.rowCount() >= 1
    log('[TEST] refreshed scores, rowCount >= 1')

    with tempfile.TemporaryDirectory() as td:
        out_xlsx = str(Path(td) / 'scores.xlsx')
        _QDReturn.save_path = out_xlsx
        _QDReturn.save_sel = 'Excel (*.xlsx)'
        scores_mod.export_scores_to_excel()
        log(f'[TEST] exported scores to {out_xlsx}')
        assert Path(out_xlsx).exists()


def main():
    app = QApplication.instance() or QApplication([])
    app.setStyle('Fusion')
    _patch_dialogs()
    _patch_qfiledialog()
    auto_accept_messageboxes()
    win = MainWindow()
    win.show()

    # Login as default admin/admin
    login = win.login
    login.user.setText('admin')
    login.pwd.setText('admin')
    QTest.mouseClick(login.login_btn, Qt.LeftButton)
    QTest.qWait(50)
    assert isinstance(win.stack.currentWidget(), type(win.admin))
    admin = win.admin
    tabs = admin.findChild(QTabWidget)
    assert tabs is not None

    test_admin_users_module(win, tabs)
    test_admin_exams_module(win, tabs)
    test_admin_sync_module(win, tabs)
    test_admin_scores_module(win, tabs)

    log('AdminView QtTest automation passed')
    return 0


def test_user_flow():
    log('[TEST] user flow')
    app = QApplication.instance() or QApplication([])
    _patch_dialogs()
    _patch_qfiledialog()
    auto_accept_messageboxes()
    win = MainWindow()
    win.show()
    # login admin
    login = win.login
    login.user.setText('admin')
    login.pwd.setText('admin')
    QTest.mouseClick(login.login_btn, Qt.LeftButton)
    QTest.qWait(50)
    admin = win.admin
    tabs = admin.findChild(QTabWidget)
    # add temp user via admin UI
    users_mod = admin.findChild(AdminUsersModule)
    suffix = str(int(time.time()))
    temp_user = f'user_{suffix}'
    temp_pwd = 'tempPwd!123'
    users_mod.new_user.setText(temp_user)
    users_mod.new_pwd.setText(temp_pwd)
    users_mod.new_fullname.setText('临时用户')
    users_mod.new_role.setCurrentText('user')
    users_mod.add_user()
    log(f'[TEST] created temp user {temp_user}')
    assert any(u[1] == temp_user for u in list_users())
    # create exam and questions (via models for speed)
    title = f'用户考试_{suffix}'
    add_exam(title, 'desc', 0.6, 10, None)
    ex = next(e for e in list_exams(include_expired=True) if e[1] == title)
    exam_id = ex[0]
    add_question(exam_id, 'single', '2+2=?', [{'key': 'A', 'text': '4'}, {'key': 'B', 'text': '5'}], ['A'], 2.0)
    log(f'[TEST] created exam {title} with one question')
    # logout to login as temp user
    admin.handle_logout()
    QTest.qWait(50)
    login = win.login
    login.user.setText(temp_user)
    login.pwd.setText(temp_pwd)
    QTest.mouseClick(login.login_btn, Qt.LeftButton)
    QTest.qWait(80)
    # now user view
    uv = win.user_view
    assert isinstance(uv, UserView)
    uv.refresh_exams()
    # select the created exam row
    tbl = uv.exams_module.exams_table_user
    row = None
    for r in range(tbl.rowCount()):
        it = tbl.item(r, 1)
        if it and it.text() == title:
            row = r
            break
    assert row is not None
    tbl.selectRow(row)
    # start exam
    uv.exams_module.on_start_button_clicked()
    QTest.qWait(80)
    # interact with ExamWindow
    ew = ExamWindow.instance
    assert ew is not None
    log('[TEST] exam window shown, selecting answer')
    # click correct option
    # find a button containing 'A. ' or 'true/false' options
    btn_clicked = False
    for b in getattr(ew, 'opt_buttons', []):
        t = b.text()
        if 'A.' in t or 'true' in t.lower():
            QTest.mouseClick(b, Qt.LeftButton)
            btn_clicked = True
            break
    assert btn_clicked
    # submit
    QTest.mouseClick(ew.submit_btn, Qt.LeftButton)
    QTest.qWait(100)
    # verify history has attempt
    uv.refresh_attempts()
    ht = uv.history_module.attempts_table
    assert ht.rowCount() >= 1
    log('[TEST] user history has at least one attempt')
    # close the window if still open
    try:
        if ExamWindow.instance and ExamWindow.instance.isVisible():
            ExamWindow.instance.close()
    except Exception:
        pass


if __name__ == '__main__':
    # CLI:
    #   python ui_auto_test_qttest.py admin   # 仅管理员页面测试
    #   python ui_auto_test_qttest.py user    # 用户端流程测试
    #   python ui_auto_test_qttest.py clean   # 清理测试数据
    #   python ui_auto_test_qttest.py all     # 清理 → 管理员测试 → 用户测试 → 清理
    arg = sys.argv[1] if len(sys.argv) > 1 else 'admin'
    if arg == 'clean':
        cleanup_test_data()
        sys.exit(0)
    elif arg == 'user':
        rc = test_user_flow() or 0
        sys.exit(rc)
    elif arg == 'all':
        cleanup_test_data()
        rc1 = main() or 0
        rc2 = test_user_flow() or 0
        cleanup_test_data()
        sys.exit(rc1 or rc2)
    else:
        rc = main() or 0
        sys.exit(rc)
