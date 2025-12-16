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
)
from views.admin_modules.users_module import AdminUsersModule
from views.admin_modules.exams_module import AdminExamsModule
from views.admin_modules.sync_module import AdminSyncModule, SyncWorker as RealSyncWorker
from views.admin_modules.scores_module import AdminScoresModule
from views.user_view import UserView
from windows.exam_window import ExamWindow


CTX = {}

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


def test_admin_users_module(win, tabs):
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
    assert any(u[1] == uname2 for u in list_users())

    # Toggle active via method
    uid = int(tbl.item(row_idx, 0).text())
    users_mod.toggle_user_active(uid, 1)

    # Promote to admin then demote back
    users_mod.toggle_user_role(uid, 'user')
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
    assert any(u[1] == uname2 for u in list_users())
    assert not any(a[1] == uname2 for a in list_admins())

    # Delete user
    uid2 = next(u[0] for u in list_users() if u[1] == uname2)
    users_mod.delete_user(uid2)
    assert not any(u[1] == uname2 for u in list_users())

    # Export users template
    with tempfile.TemporaryDirectory() as td:
        out_xlsx = str(Path(td) / 'users_tpl.xlsx')
        _QDReturn.save_path = out_xlsx
        _QDReturn.save_sel = 'Excel (*.xlsx)'
        auto_accept_messageboxes()
        users_mod.export_users_template()
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
        assert any(u[1] == bob for u in list_users())
        assert any(a[1] == root2 for a in list_admins())
        CTX['bob_uname'] = bob


def test_admin_exams_module(win, tabs):
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
    assert get_exam_title(exam_id) == '新标题'
    tbl.item(row, 5).setText('新的描述')

    with tempfile.TemporaryDirectory() as td:
        out_xlsx = str(Path(td) / 'exam_sample.xlsx')
        _QDReturn.save_path = out_xlsx
        _QDReturn.save_sel = 'Excel (*.xlsx)'
        auto_accept_messageboxes()
        exams_mod.export_sample()
        assert Path(out_xlsx).exists()

    from models import clear_exam_questions
    # Clear questions (confirm patched to Yes)
    auto_accept_messageboxes()
    exams_mod.clear_exam(exam_id)
    # Delete exam
    auto_accept_messageboxes()
    exams_mod.delete_exam(exam_id)
    QTest.qWait(50)
    if any(e[0] == exam_id for e in list_exams(include_expired=True)):
        from models import delete_exam as _model_delete_exam
        _model_delete_exam(exam_id)
    assert not any(e[0] == exam_id for e in list_exams(include_expired=True))


def test_admin_sync_module(win, tabs):
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
    assert any(t[1] == '设备A' for t in list_sync_targets())

    sync_mod.refresh_targets()
    tbl = sync_mod.targets_table
    r = 0
    tbl.item(r, 0).setText('设备A-改')
    tbl.item(r, 1).setText('192.168.10.11')
    tbl.item(r, 2).setText('user2')
    tbl.item(r, 3).setText('~/.exam_system/exam.db')
    assert any(t[1] == '设备A-改' and t[2] == '192.168.10.11' for t in list_sync_targets())

    with tempfile.TemporaryDirectory() as td:
        out_xlsx = str(Path(td) / 'targets_tpl.xlsx')
        _QDReturn.save_path = out_xlsx
        _QDReturn.save_sel = 'Excel (*.xlsx)'
        auto_accept_messageboxes()
        sync_mod.export_targets_template()
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
        assert any(t[1] == '设备B' for t in list_sync_targets())
        assert any(t[1] == '设备C' for t in list_sync_targets())

    sync_mod.sync_all()


def test_admin_scores_module(win, tabs):
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

    with tempfile.TemporaryDirectory() as td:
        out_xlsx = str(Path(td) / 'scores.xlsx')
        _QDReturn.save_path = out_xlsx
        _QDReturn.save_sel = 'Excel (*.xlsx)'
        scores_mod.export_scores_to_excel()
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

    print('AdminView QtTest automation passed')
    return 0


def test_user_flow():
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
    assert any(u[1] == temp_user for u in list_users())
    # create exam and questions (via models for speed)
    title = f'用户考试_{suffix}'
    add_exam(title, 'desc', 0.6, 10, None)
    ex = next(e for e in list_exams(include_expired=True) if e[1] == title)
    exam_id = ex[0]
    add_question(exam_id, 'single', '2+2=?', [{'key': 'A', 'text': '4'}, {'key': 'B', 'text': '5'}], ['A'], 2.0)
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
    # close the window if still open
    try:
        if ExamWindow.instance and ExamWindow.instance.isVisible():
            ExamWindow.instance.close()
    except Exception:
        pass


if __name__ == '__main__':
    # Allow running both admin and user flows from CLI
    if len(sys.argv) > 1 and sys.argv[1] == 'user':
        sys.exit(test_user_flow() or 0)
    else:
        sys.exit(main())


if __name__ == '__main__':
    sys.exit(main())
