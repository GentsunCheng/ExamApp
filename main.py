import json
import os
import pathlib
import yaml
import toml
import random
from datetime import datetime
from PySide6.QtCore import QTimer, Qt, QThread, Signal, QSize
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QStackedWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem, QTextEdit, QFormLayout, QSpinBox, QDoubleSpinBox, QDateTimeEdit, QFileDialog, QTabWidget, QTableWidget, QTableWidgetItem, QGroupBox, QHeaderView, QCheckBox, QComboBox, QMessageBox, QProgressDialog, QListView
from database import ensure_db, DB_PATH
from models import create_admin_if_absent, authenticate, list_users, create_user, add_exam, list_exams, add_question, import_questions_from_json, list_questions, start_attempt, save_answer, submit_attempt, list_attempts, upsert_sync_target, list_sync_targets, delete_user, update_user_role, update_user_active, delete_sync_target, update_sync_target
from sync import rsync_push, rsync_pull
from exam_interface import ModernTimer, ModernProgressBar
from status_indicators import LoadingIndicator
from icon_manager import get_icon, get_action_indicator, get_type_indicator
from theme_manager import theme_manager

class SyncWorker(QThread):
    progress = Signal(str)
    finished = Signal(str)
    error = Signal(str)
    
    def __init__(self, targets, operation='push'):
        super().__init__()
        self.targets = targets
        self.operation = operation
    
    def run(self):
        results = []
        for t in self.targets:
            try:
                # t structure: (id, name, ip, username, remote_path, ssh_password)
                ssh_password = t[5] if len(t) > 5 else None
                
                if self.operation == 'push':
                    code, out, err = rsync_push(t[2], t[3], t[4], ssh_password)
                    if code == 0:
                        result = f'{t[1]} ({t[2]}) 推送成功'
                    else:
                        result = f'{t[1]} ({t[2]}) 推送失败: {err or "未知错误"}'
                else:  # pull
                    base_dir = os.path.join(os.path.dirname(DB_PATH), 'pulled')
                    os.makedirs(base_dir, exist_ok=True)
                    ip = t[2]
                    dest_dir = os.path.join(base_dir, ip)
                    os.makedirs(dest_dir, exist_ok=True)
                    code, out, err = rsync_pull(ip, t[3], t[4], dest_dir, ssh_password)
                    
                    if code == 0:
                        result = f'{t[1]} ({ip}) 拉取成功'
                        rp = os.path.join(dest_dir, os.path.basename(t[4]))
                        try:
                            from models import merge_remote_db
                            merge_remote_db(rp)
                            result += ' (成绩已合并)'
                        except Exception as me:
                            result += f' (合并失败: {str(me)})'
                    else:
                        result = f'{t[1]} ({ip}) 拉取失败: {err or "未知错误"}'
                
                results.append(result)
                self.progress.emit(result)
                
            except Exception as e:
                error_msg = f'{t[1]} 错误: {str(e)}'
                results.append(error_msg)
                self.error.emit(error_msg)
        
        self.finished.emit('\n'.join(results))

class LoginView(QWidget):
    def __init__(self, on_login):
        super().__init__()
        self.on_login = on_login
        colors = theme_manager.get_theme_colors()
        bkg = 'background' + '-color'
        col = 'co' + 'lor'
        bd = 'bor' + 'der'
        pd = 'pad' + 'ding'
        fs = 'font' + '-size'
        ff = 'font' + '-family'
        br = 'border' + '-radius'
        
        ss = (
            f"QWidget {{ {bkg}:{colors['background']}; {ff}:\"PingFang SC\",sans-serif; }}\n"
            f"QLabel {{ {fs}:16px; {col}:{colors['text_primary']}; }}\n"
            f"QLineEdit {{ {pd}:8px; {bd}:1px solid {colors['input_border']}; {br}:8px; {fs}:14px; {bkg}:{colors['input_background']}; }}\n"
            f"QLineEdit:focus {{ {bd}-color:{colors['primary']}; }}\n"
            f"QPushButton {{ {bkg}:{colors['button_primary']}; {col}:{colors['text_inverse']}; {pd}:8px 16px; border:none; {br}:8px; {fs}:14px; }}\n"
            f"QPushButton:hover {{ {bkg}:{colors['button_primary_hover']}; }}\n"
            f"QPushButton:pressed {{ {bkg}:{colors['primary']}; }}\n"
        )
        self.setStyleSheet(ss)
        main = QVBoxLayout()
        main.setAlignment(Qt.AlignCenter)
        card = QGroupBox()
        card.setFixedWidth(320)
        card.setStyleSheet(f"QGroupBox {{ border:1px solid {colors['border']}; border-radius:12px; padding:24px; background-color:{colors['card_background']}; }}")
        lay = QVBoxLayout()
        title = QLabel('📝 登录')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:20px; font-weight:bold; margin-bottom:16px;")
        self.user = QLineEdit()
        self.user.setPlaceholderText('用户名')
        self.pwd = QLineEdit()
        self.pwd.setEchoMode(QLineEdit.Password)
        self.pwd.setPlaceholderText('密码')
        btn = QPushButton('登录')
        btn.setDefault(True)
        btn.clicked.connect(self.handle_login)
        lay.addWidget(title)
        lay.addWidget(self.user)
        lay.addWidget(self.pwd)
        lay.addWidget(btn)
        lay.setSpacing(12)
        card.setLayout(lay)
        main.addWidget(card)
        self.setLayout(main)
    def handle_login(self):
        u = authenticate(self.user.text().strip(), self.pwd.text())
        if not u:
            QMessageBox.warning(self, '错误', '用户名或密码错误')
            return
        self.on_login(u)

class AdminView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        colors = theme_manager.get_theme_colors()
        bkg = 'background' + '-color'
        col = 'co' + 'lor'
        bd = 'bor' + 'der'
        pd = 'pad' + 'ding'
        fs = 'font' + '-size'
        ff = 'font' + '-family'
        br = 'border' + '-radius'
        ss_admin = (
            f"QWidget {{ {bkg}:{colors['background']}; {ff}:\"PingFang SC\",sans-serif; }}\n"
            f"QTabWidget::pane {{ {bd}:1px solid {colors['border']}; {bkg}:{colors['card_background']}; {br}:8px; }}\n"
            f"QTabBar::tab {{ {bkg}:{colors['border_light']}; {pd}:10px 16px; margin-right:2px; {br}:8px; }}\n"
            f"QTabBar::tab:selected {{ {bkg}:{colors['primary']}; {col}:{colors['text_inverse']}; }}\n"
            f"QGroupBox {{ font-weight:bold; {bd}:1px solid {colors['border']}; {br}:8px; margin-top:8px; padding-top:8px; }}\n"
            f"QPushButton {{ {bkg}:{colors['button_primary']}; {col}:{colors['text_inverse']}; {pd}:6px 12px; border:none; {br}:8px; }}\n"
            f"QPushButton:hover {{ {bkg}:{colors['button_primary_hover']}; }}\n"
            f"QTableWidget {{ {bd}:1px solid {colors['border']}; {br}:8px; {bkg}:{colors['card_background']}; }}\n"
            f"QTableWidget::item:hover {{ {bkg}:{colors['border_light']}; }}\n"
            f"QTableWidget::item:selected {{ {bkg}:{colors['primary']}; {col}:{colors['text_inverse']}; }}\n"
            f"QHeaderView::section {{ {bkg}:{colors['border_light']}; {col}:{colors['text_secondary']}; font-weight:600; {pd}:6px 8px; {bd}:none; {bd}-right:1px solid {colors['border']}; }}\n"
            f"QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QDateTimeEdit {{ {pd}:6px; {bd}:1px solid {colors['input_border']}; {br}:8px; {bkg}:{colors['input_background']}; }}\n"
            f"QLineEdit:focus, QTextEdit:focus {{ {bd}-color:{colors['primary']}; }}\n"
            f"QComboBox {{ {pd}:6px 8px; {bd}:1px solid {colors['input_border']}; {br}:8px; {bkg}:{colors['input_background']}; {col}:{colors['text_primary']}; }}\n"
            f"QComboBox:focus {{ {bd}-color:{colors['primary']}; }}\n"
            f"QComboBox::drop-down {{ width:24px; border:none; }}\n"
            f"QComboBox QAbstractItemView {{ {bkg}:{colors['card_background']}; {bd}:1px solid {colors['border']}; {pd}:4px; outline:0; }}\n"
        )
        self.setStyleSheet(ss_admin)
        tabs = QTabWidget()
        tabs.addTab(self.users_tab(), '用户')
        tabs.addTab(self.exams_tab(), '试题')
        tabs.addTab(self.sync_tab(), '同步')
        tabs.addTab(self.scores_tab(), '成绩')
        tabs.setTabIcon(0, get_icon('user'))
        tabs.setTabIcon(1, get_icon('exam'))
        tabs.setTabIcon(2, get_icon('sync'))
        tabs.setTabIcon(3, get_icon('score'))
        layout = QVBoxLayout()
        topbar = QHBoxLayout()
        title = QLabel('管理后台')
        title.setStyleSheet("font-size:18px; font-weight:bold;")
        topbar.addWidget(title)
        topbar.addStretch()
        logout_btn = QPushButton('退出登录')
        logout_btn.setIcon(get_icon('confirm'))
        logout_btn.clicked.connect(self.handle_logout)
        topbar.addWidget(logout_btn)
        layout.addLayout(topbar)
        layout.addWidget(tabs)
        self.setLayout(layout)
    def handle_logout(self):
        p = self.parent()
        while p is not None and not hasattr(p, 'logout'):
            p = p.parent()
        if p is not None:
            p.logout()
    def show_sync_progress(self, message):
        if hasattr(self, 'sync_progress_dialog') and getattr(self, 'sync_progress_dialog'):
            try:
                self.sync_progress_dialog.close()
            except Exception:
                pass
        dlg = QProgressDialog(message, '', 0, 0, self)
        dlg.setWindowTitle('同步中')
        dlg.setCancelButton(None)
        dlg.setMinimumDuration(0)
        dlg.setAutoClose(False)
        dlg.setAutoReset(False)
        dlg.setModal(True)
        dlg.show()
        self.sync_progress_dialog = dlg
    def make_tag(self, text, bg, fg):
        lab = QLabel(text)
        lab.setAlignment(Qt.AlignCenter)
        lab.setStyleSheet(f"QLabel {{ background-color:{bg}; color:{fg}; border-radius:10px; padding:2px 8px; font-size:12px; }}")
        return lab
    def users_tab(self):
        w = QWidget()
        lay = QVBoxLayout()
        gb = QGroupBox('用户列表')
        vb = QVBoxLayout()
        
        # Create table for users with delete and role management
        self.users_table = QTableWidget(0, 7)
        self.users_table.setHorizontalHeaderLabels(['ID', '用户名', '姓名', '角色', '状态', '创建时间', '操作'])
        self.users_table.horizontalHeader().setStretchLastSection(True)
        self.users_table.setAlternatingRowColors(True)
        self.refresh_users()
        vb.addWidget(self.users_table)
        gb.setLayout(vb)
        lay.addWidget(gb)
        
        gb2 = QGroupBox('新增用户')
        form = QFormLayout()
        self.new_user = QLineEdit()
        self.new_user.setPlaceholderText('用户名')
        self.new_pwd = QLineEdit()
        self.new_pwd.setEchoMode(QLineEdit.Password)
        self.new_pwd.setPlaceholderText('密码')
        self.new_fullname = QLineEdit()
        self.new_fullname.setPlaceholderText('姓名(可选)')
        
        # Role selection for new user
        self.new_role = QComboBox()
        colors = theme_manager.get_theme_colors()
        self.new_role.setStyleSheet(
            f"QComboBox {{ padding:6px 10px; border:1px solid {colors['input_border']}; border-radius:12px; background-color:{colors['input_background']}; color:{colors['text_primary']}; min-height:32px; }}\n"
            f"QComboBox:focus {{ border-color:{colors['primary']}; }}\n"
            f"QComboBox::drop-down {{ width:28px; border:none; }}\n"
            f"QComboBox QAbstractItemView {{ background-color:{colors['card_background']}; border:1px solid {colors['border']}; padding:6px; outline:0; }}\n"
            f"QComboBox QAbstractItemView::item {{ padding:6px 10px; height:28px; color:{colors['text_primary']}; }}\n"
            f"QComboBox QAbstractItemView::item:hover {{ background-color:{colors['border_light']}; }}\n"
            f"QComboBox QAbstractItemView::item:selected {{ background-color:{colors['primary']}; color:{colors['text_inverse']}; }}"
        )
        role_view = QListView()
        role_view.setStyleSheet(
            f"QListView {{ background-color:{colors['card_background']}; border:1px solid {colors['border']}; padding:6px; }}\n"
            f"QListView::item {{ padding:6px 10px; height:28px; color:{colors['text_primary']}; }}\n"
            f"QListView::item:hover {{ background-color:{colors['border_light']}; }}\n"
            f"QListView::item:selected {{ background-color:{colors['primary']}; color:{colors['text_inverse']}; }}"
        )
        self.new_role.setView(role_view)
        self.new_role.setIconSize(QSize(16, 16))
        self.new_role.addItem(get_icon('user'), 'user')
        self.new_role.addItem(get_icon('user_admin'), 'admin')
        
        add_btn = QPushButton('新增用户')
        add_btn.clicked.connect(self.add_user)
        form.addRow('用户名', self.new_user)
        form.addRow('密码', self.new_pwd)
        form.addRow('姓名', self.new_fullname)
        form.addRow('角色', self.new_role)
        form.addRow(add_btn)
        gb2.setLayout(form)
        lay.addWidget(gb2)
        lay.addStretch()
        w.setLayout(lay)
        return w
    def refresh_users(self):
        self.users_table = getattr(self, 'users_table', QTableWidget(0, 7))
        self.users_table.setRowCount(0)
        for u in list_users():
            row = self.users_table.rowCount()
            self.users_table.insertRow(row)
            
            # Add user data
            self.users_table.setItem(row, 0, QTableWidgetItem(str(u[0])))  # ID
            self.users_table.setItem(row, 1, QTableWidgetItem(u[1] or '')) # Username
            self.users_table.setItem(row, 2, QTableWidgetItem((u[2] or '') if u[2] else '')) # Full name
            role_text = '管理员' if u[3] == 'admin' else '普通用户'
            role_bg = '#e1f3d8' if u[3] == 'admin' else '#d9ecff'
            role_fg = '#67c23a' if u[3] == 'admin' else '#409eff'
            self.users_table.setCellWidget(row, 3, self.make_tag(role_text, role_bg, role_fg))
            status_text = '活跃' if u[4] == 1 else '禁用'
            status_bg = '#e1f3d8' if u[4] == 1 else '#fde2e2'
            status_fg = '#67c23a' if u[4] == 1 else '#f56c6c'
            self.users_table.setCellWidget(row, 4, self.make_tag(status_text, status_bg, status_fg))
            self.users_table.setItem(row, 5, QTableWidgetItem(u[5]))       # Created at
            it_id = self.users_table.item(row, 0)
            it_ct = self.users_table.item(row, 5)
            if it_id:
                it_id.setTextAlignment(Qt.AlignCenter)
            if it_ct:
                it_ct.setTextAlignment(Qt.AlignCenter)
            
            # Create action buttons
            action_widget = QWidget()
            action_layout = QHBoxLayout()
            action_layout.setContentsMargins(4, 4, 4, 4)
            
            # Delete button
            delete_btn = QPushButton('删除')
            delete_btn.setIcon(get_icon('delete'))
            delete_btn.setStyleSheet("QPushButton { background-color:#f56c6c; color:#fff; padding:4px 8px; font-size:12px; border-radius:6px; }")
            delete_btn.clicked.connect(lambda checked, uid=u[0]: self.delete_user(uid))
            action_layout.addWidget(delete_btn)
            
            # Role toggle button
            role_btn = QPushButton('设为管理员' if u[3] == 'user' else '设为普通用户')
            role_btn.setIcon(get_icon('user_edit'))
            role_btn.setStyleSheet("QPushButton { background-color:#67c23a; color:#fff; padding:4px 8px; font-size:12px; border-radius:6px; }")
            role_btn.clicked.connect(lambda checked, uid=u[0], current_role=u[3]: self.toggle_user_role(uid, current_role))
            action_layout.addWidget(role_btn)
            
            # Active toggle button
            active_btn = QPushButton('禁用' if u[4] == 1 else '启用')
            active_btn.setIcon(get_icon('user_active' if u[4] == 1 else 'user_inactive'))
            active_btn.setStyleSheet("QPushButton { background-color:#e6a23c; color:#fff; padding:4px 8px; font-size:12px; border-radius:6px; }")
            active_btn.clicked.connect(lambda checked, uid=u[0], current_active=u[4]: self.toggle_user_active(uid, current_active))
            action_layout.addWidget(active_btn)
            
            action_widget.setLayout(action_layout)
            self.users_table.setCellWidget(row, 6, action_widget)
    def add_user(self):
        name = self.new_user.text().strip()
        pwd = self.new_pwd.text()
        role = self.new_role.currentText()
        if not name or not pwd:
            QMessageBox.warning(self, '错误', '请输入用户名和密码')
            return
        try:
            full_name = self.new_fullname.text().strip() or None
            create_user(name, pwd, role, 1, full_name)
            self.refresh_users()
            self.new_user.clear()
            self.new_pwd.clear()
            self.new_fullname.clear()
            QMessageBox.information(self, '成功', '用户已创建')
        except Exception as e:
            QMessageBox.warning(self, '错误', str(e))
    
    def delete_user(self, user_id):
        reply = QMessageBox.question(self, '确认', '确定要删除该用户吗？', QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                delete_user(user_id)
                self.refresh_users()
                QMessageBox.information(self, '成功', '用户已删除')
            except Exception as e:
                QMessageBox.warning(self, '错误', str(e))
    
    def toggle_user_role(self, user_id, current_role):
        new_role = 'admin' if current_role == 'user' else 'user'
        try:
            update_user_role(user_id, new_role)
            self.refresh_users()
            QMessageBox.information(self, '成功', f'用户角色已更新为{new_role}')
        except Exception as e:
            QMessageBox.warning(self, '错误', str(e))
    
    def toggle_user_active(self, user_id, current_active):
        new_active = 0 if current_active == 1 else 1
        try:
            update_user_active(user_id, new_active)
            self.refresh_users()
            status = '启用' if new_active == 1 else '禁用'
            QMessageBox.information(self, '成功', f'用户已{status}')
        except Exception as e:
            QMessageBox.warning(self, '错误', str(e))
    def exams_tab(self):
        w = QWidget()
        lay = QHBoxLayout()
        gb1 = QGroupBox('试题列表')
        vb1 = QVBoxLayout()
        self.exams_table = QTableWidget(0, 7)
        self.exams_table.setHorizontalHeaderLabels(['ID', '标题', '及格比例', '限时(分钟)', '截止', '描述', '操作'])
        self.exams_table.horizontalHeader().setStretchLastSection(True)
        self.exams_table.setAlternatingRowColors(True)
        self.refresh_exams()
        vb1.addWidget(self.exams_table)
        gb1.setLayout(vb1)
        gb2 = QGroupBox('新建试题')
        vb2 = QVBoxLayout()
        form = QFormLayout()
        self.ex_title = QLineEdit()
        self.ex_title.setPlaceholderText('标题')
        self.ex_desc = QTextEdit()
        self.ex_desc.setPlaceholderText('描述')
        self.ex_desc.setMaximumHeight(80)
        self.ex_pass = QSpinBox()
        self.ex_pass.setRange(0, 100)
        self.ex_pass.setValue(60)
        colors_inputs = theme_manager.get_theme_colors()
        spin_style = (
            f"QSpinBox {{ padding:6px 10px; border:1px solid {colors_inputs['input_border']}; border-radius:12px; background-color:{colors_inputs['input_background']}; color:{colors_inputs['text_primary']}; }}\n"
            f"QSpinBox:focus {{ border-color:{colors_inputs['primary']}; }}\n"
            f"QSpinBox::up-button, QSpinBox::down-button {{ width:20px; border:none; background-color:{colors_inputs['border_light']}; border-radius:8px; }}\n"
            f"QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background-color:{colors_inputs['button_primary_hover']}; }}"
        )
        self.ex_pass.setStyleSheet(spin_style)
        self.ex_time = QSpinBox()
        self.ex_time.setRange(1, 600)
        self.ex_time.setValue(60)
        self.ex_time.setStyleSheet(spin_style)
        self.ex_end = QDateTimeEdit()
        self.ex_end.setDateTime(datetime.now())
        self.ex_end.setDisplayFormat('yyyy-MM-dd HH:mm')
        self.ex_end.setCalendarPopup(True)
        dt_style = (
            f"QDateTimeEdit {{ padding:6px 10px; border:1px solid {colors_inputs['input_border']}; border-radius:12px; background-color:{colors_inputs['input_background']}; color:{colors_inputs['text_primary']}; }}\n"
            f"QDateTimeEdit:focus {{ border-color:{colors_inputs['primary']}; }}\n"
            f"QDateTimeEdit::up-button, QDateTimeEdit::down-button {{ width:22px; border:none; background-color:{colors_inputs['border_light']}; border-radius:10px; margin:2px; }}\n"
            f"QDateTimeEdit::up-button:hover, QDateTimeEdit::down-button:hover {{ background-color:{colors_inputs['button_primary_hover']}; }}\n"
            f"QDateTimeEdit::up-button:pressed, QDateTimeEdit::down-button:pressed {{ background-color:{colors_inputs['primary']}; }}\n"
            f"QDateTimeEdit::up-arrow, QDateTimeEdit::down-arrow {{ width: 0; height: 0; }}"
        )
        self.ex_end.setStyleSheet(dt_style)
        cal = self.ex_end.calendarWidget()
        cal.setStyleSheet(
            f"QCalendarWidget {{ background-color:{colors_inputs['card_background']}; border:1px solid {colors_inputs['border']}; border-radius:8px; }}\n"
            f"QCalendarWidget QWidget#qt_calendar_navigationbar {{ background-color:{colors_inputs['card_background']}; border:none; padding:6px; }}\n"
            f"QCalendarWidget QToolButton#qt_calendar_prevmonth, QCalendarWidget QToolButton#qt_calendar_nextmonth {{ background-color:{colors_inputs['button_primary']}; color:{colors_inputs['text_inverse']}; border:none; border-radius:6px; padding:4px 8px; }}\n"
            f"QCalendarWidget QToolButton#qt_calendar_prevmonth:hover, QCalendarWidget QToolButton#qt_calendar_nextmonth:hover {{ background-color:{colors_inputs['button_primary_hover']}; }}\n"
            f"QCalendarWidget QToolButton#qt_calendar_monthbutton {{ background-color:{colors_inputs['border_light']}; color:{colors_inputs['text_primary']}; border:none; border-radius:6px; padding:4px 10px; }}\n"
            f"QCalendarWidget QToolButton#qt_calendar_monthbutton:hover {{ background-color:{colors_inputs['button_primary_hover']}; color:{colors_inputs['text_inverse']}; }}\n"
            f"QCalendarWidget QSpinBox#qt_calendar_yearspinbox {{ background-color:{colors_inputs['input_background']}; color:{colors_inputs['text_primary']}; border:1px solid {colors_inputs['input_border']}; border-radius:6px; padding:2px 6px; }}\n"
            f"QCalendarWidget QTableView {{ background-color:{colors_inputs['card_background']}; alternate-background-color:{colors_inputs['border_light']}; selection-background-color:{colors_inputs['primary']}; selection-color:{colors_inputs['text_inverse']}; gridline-color:{colors_inputs['border']}; }}\n"
            f"QCalendarWidget QTableView::item {{ padding:4px; }}\n"
            f"QCalendarWidget QTableView::item:hover {{ background-color:{colors_inputs['border_light']}; }}\n"
            f"QCalendarWidget QTableView::item:selected {{ background-color:{colors_inputs['primary']}; color:{colors_inputs['text_inverse']}; }}"
        )
        self.ex_permanent = QCheckBox('永久有效')
        colors_perm = theme_manager.get_theme_colors()
        self.ex_permanent.setStyleSheet(
            f"QCheckBox {{ color:{colors_perm['text_primary']}; font-size:14px; }}\n"
            f"QCheckBox::indicator {{ width:40px; height:22px; border-radius:11px; }}\n"
            f"QCheckBox::indicator:unchecked {{ background-color:{colors_perm['border_light']}; border:1px solid {colors_perm['border']}; }}\n"
            f"QCheckBox::indicator:checked {{ background-color:{colors_perm['primary']}; border:1px solid {colors_perm['primary']}; }}"
        )
        def on_perm_changed(state):
            checked = state == Qt.Checked
            self.ex_end.setEnabled(not checked)
            self.ex_end.setReadOnly(checked)
            if not checked:
                self.ex_end.setFocus()
        self.ex_permanent.stateChanged.connect(on_perm_changed)
        form.addRow('标题', self.ex_title)
        form.addRow('描述', self.ex_desc)
        form.addRow('及格比例%', self.ex_pass)
        form.addRow('限时(分钟)', self.ex_time)
        form.addRow('结束日期', self.ex_end)
        form.addRow('', self.ex_permanent)
        add_btn = QPushButton('新增试题')
        add_btn.setIcon(get_icon('exam_add'))
        add_btn.clicked.connect(self.add_exam)
        import_btn = QPushButton('导入题目')
        import_btn.setIcon(get_icon('exam_import'))
        import_btn.clicked.connect(self.import_questions)
        export_btn = QPushButton('导出题目示例')
        export_btn.setIcon(get_icon('exam_export'))
        export_btn.clicked.connect(self.export_sample)
        vb2.addLayout(form)
        hb = QHBoxLayout()
        hb.addWidget(add_btn)
        hb.addWidget(import_btn)
        hb.addWidget(export_btn)
        vb2.addLayout(hb)
        gb2.setLayout(vb2)
        lay.addWidget(gb1, 1)
        lay.addWidget(gb2, 1)
        w.setLayout(lay)
        return w
    def refresh_exams(self):
        tbl = getattr(self, 'exams_table', None)
        if tbl is None:
            return
        tbl.setRowCount(0)
        for e in list_exams(include_expired=True):
            r = tbl.rowCount()
            tbl.insertRow(r)
            tbl.setItem(r, 0, QTableWidgetItem(str(e[0])))
            tbl.setItem(r, 1, QTableWidgetItem(e[1] or ''))
            tbl.setItem(r, 2, QTableWidgetItem(f"{int(float(e[3])*100)}%"))
            tbl.setItem(r, 3, QTableWidgetItem(str(e[4])))
            tbl.setItem(r, 4, QTableWidgetItem(e[5] if e[5] else '永久'))
            tbl.setItem(r, 5, QTableWidgetItem(e[2] or ''))
            opw = QWidget()
            hb = QHBoxLayout()
            hb.setContentsMargins(0,0,0,0)
            btn_clear = QPushButton('清空')
            btn_clear.setIcon(get_icon('delete'))
            btn_del = QPushButton('删除')
            btn_del.setIcon(get_icon('exam_delete'))
            exam_id = e[0]
            btn_clear.clicked.connect(lambda _, x=exam_id: self.clear_exam(x))
            btn_del.clicked.connect(lambda _, x=exam_id: self.delete_exam(x))
            hb.addWidget(btn_clear)
            hb.addWidget(btn_del)
            hb.addStretch()
            opw.setLayout(hb)
            tbl.setCellWidget(r, 6, opw)
    def add_exam(self):
        title = self.ex_title.text().strip()
        desc = self.ex_desc.toPlainText().strip()
        pass_ratio = self.ex_pass.value() / 100.0
        tl = self.ex_time.value()
        end = None if self.ex_permanent.isChecked() else self.ex_end.dateTime().toString(Qt.ISODate)
        if not title:
            QMessageBox.warning(self, '错误', '请输入标题')
            return
        add_exam(title, desc, pass_ratio, tl, end)
        self.refresh_exams()
        QMessageBox.information(self, '成功', '试题已新增')
    def get_selected_exam_id(self):
        tbl = getattr(self, 'exams_table', None)
        if tbl is None:
            return None
        r = tbl.currentRow()
        if r < 0:
            return None
        it = tbl.item(r, 0)
        return int(it.text()) if it and it.text() else None
    def import_questions(self):
        exam_id = self.get_selected_exam_id()
        if not exam_id:
            QMessageBox.warning(self, '错误', '请选择试题')
            return
        fn, sel = QFileDialog.getOpenFileName(self, '选择题目文件', os.getcwd(), 'JSON (*.json);;YAML (*.yaml *.yml);;TOML (*.toml)')
        if not fn:
            return
        try:
            with open(fn, 'r', encoding='utf-8') as f:
                text = f.read()
            ext = os.path.splitext(fn)[1].lower()
            data = None
            if (sel and sel.startswith('JSON')) or ext == '.json' or ext == '':
                data = json.loads(text)
            elif (sel and sel.startswith('YAML')) or ext in ('.yaml', '.yml'):
                data = yaml.safe_load(text)
                if isinstance(data, dict) and 'questions' in data:
                    data = data['questions']
                if not isinstance(data, list):
                    QMessageBox.warning(self, '错误', 'YAML 格式不正确: 需要为题目列表')
                    return
            elif (sel and sel.startswith('TOML')) or ext == '.toml':
                obj = toml.loads(text)
                qs = obj.get('questions') or []
                if not isinstance(qs, list):
                    QMessageBox.warning(self, '错误', 'TOML 格式不正确: 需要 questions 为列表')
                    return
                data = []
                for q in qs:
                    item = {
                        'type': q.get('type'),
                        'text': q.get('text'),
                        'score': float(q.get('score') or 1),
                        'options': q.get('options') or [],
                        'correct': q.get('correct') or []
                    }
                    data.append(item)
            else:
                data = json.loads(text)
            import_questions_from_json(exam_id, data)
            QMessageBox.information(self, '成功', '题目已导入')
        except Exception as e:
            QMessageBox.warning(self, '错误', str(e))

    def clear_exam(self, exam_id):
        reply = QMessageBox.question(self, '确认', '确定要清空该试题的所有题目吗？此操作不可恢复', QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        try:
            from models import clear_exam_questions
            clear_exam_questions(exam_id)
            QMessageBox.information(self, '成功', '题目已清空')
        except Exception as e:
            QMessageBox.warning(self, '错误', str(e))

    def delete_exam(self, exam_id):
        reply = QMessageBox.question(self, '确认', '确定要删除该试题吗？相关的考试尝试与答案也将被删除', QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        try:
            from models import delete_exam
            delete_exam(exam_id)
            self.refresh_exams()
            QMessageBox.information(self, '成功', '试题已删除')
        except Exception as e:
            QMessageBox.warning(self, '错误', str(e))
    
    def export_sample(self):
        data = [
            {"type":"single","text":"2+2=?","options":[{"key":"A","text":"4"},{"key":"B","text":"3"}],"correct":["A"],"score":2},
            {"type":"multiple","text":"下列哪些是偶数?","options":[{"key":"A","text":"2"},{"key":"B","text":"3"},{"key":"C","text":"4"}],"correct":["A","C"],"score":3},
            {"type":"truefalse","text":"Python是解释型语言","correct":[True],"score":1}
        ]
        suggested = os.path.join(str(pathlib.Path.home()), 'Documents/exam')
        fn, sel = QFileDialog.getSaveFileName(self, '导出题目示例', suggested, 'JSON (*.json);;YAML (*.yaml);;TOML (*.toml)')
        if not fn:
            return
        try:
            def ensure_ext(path, ext):
                return path if path.lower().endswith(ext) else path + ext
            ext = os.path.splitext(fn)[1].lower()
            if (sel and sel.startswith('JSON')) or ext == '.json' or ext == '':
                out = ensure_ext(fn, '.json')
                with open(out, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            elif (sel and sel.startswith('YAML')) or ext in ('.yaml', '.yml'):
                out = ensure_ext(fn, '.yaml')
                lines = []
                for item in data:
                    lines.append('-')
                    lines.append(f'  type: {item["type"]}')
                    lines.append(f'  text: "{item["text"]}"')
                    lines.append(f'  score: {item["score"]}')
                    if item.get('options'):
                        lines.append('  options:')
                        for opt in item['options']:
                            lines.append('    - key: ' + opt['key'])
                            lines.append(f'      text: "{opt["text"]}"')
                    if item.get('correct') is not None:
                        lines.append('  correct:')
                        for v in item['correct']:
                            if isinstance(v, bool):
                                lines.append('    - ' + ('true' if v else 'false'))
                            else:
                                lines.append('    - ' + str(v))
                with open(out, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines) + '\n')
            elif (sel and sel.startswith('TOML')) or ext == '.toml':
                out = ensure_ext(fn, '.toml')
                lines = []
                for item in data:
                    lines.append('[[questions]]')
                    lines.append(f'type = "{item["type"]}"')
                    lines.append(f'text = "{item["text"]}"')
                    lines.append(f'score = {item["score"]}')
                    if item.get('options'):
                        for opt in item['options']:
                            lines.append('[[questions.options]]')
                            lines.append(f'key = "{opt["key"]}"')
                            lines.append(f'text = "{opt["text"]}"')
                    if item.get('correct') is not None:
                        arr = []
                        for v in item['correct']:
                            if isinstance(v, bool):
                                arr.append('true' if v else 'false')
                            elif isinstance(v, (int, float)):
                                arr.append(str(v))
                            else:
                                arr.append('"' + str(v) + '"')
                        lines.append(f'correct = [{", ".join(arr)}]')
                with open(out, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines) + '\n')
            QMessageBox.information(self, '成功', '示例已导出')
        except Exception as e:
            QMessageBox.warning(self, '错误', str(e))
    def sync_tab(self):
        w = QWidget()
        lay = QVBoxLayout()
        gb1 = QGroupBox('设备列表')
        vb1 = QVBoxLayout()
        self.targets_table = QTableWidget(0, 6)
        self.targets_table.setHorizontalHeaderLabels(['名称', 'IP', '用户名', '远程路径', 'SSH密码', '操作'])
        self.targets_table.horizontalHeader().setStretchLastSection(True)
        self.refresh_targets()
        vb1.addWidget(self.targets_table)
        gb1.setLayout(vb1)
        lay.addWidget(gb1)
        gb2 = QGroupBox('添加设备')
        form = QFormLayout()
        self.t_name = QLineEdit()
        self.t_name.setPlaceholderText('设备名称')
        self.t_ip = QLineEdit()
        self.t_ip.setPlaceholderText('192.168.x.x')
        self.t_user = QLineEdit()
        self.t_user.setPlaceholderText('用户名')
        self.t_path = QLineEdit()
        self.t_path.setText('~/.exam_system/exam.db')
        self.t_password = QLineEdit()
        self.t_password.setPlaceholderText('SSH密码（可选）')
        self.t_password.setEchoMode(QLineEdit.Password)
        add_btn = QPushButton('添加设备')
        add_btn.clicked.connect(self.add_target)
        form.addRow('名称', self.t_name)
        form.addRow('IP', self.t_ip)
        form.addRow('用户名', self.t_user)
        form.addRow('远程路径', self.t_path)
        form.addRow('SSH密码', self.t_password)
        form.addRow(add_btn)
        gb2.setLayout(form)
        lay.addWidget(gb2)
        hb = QHBoxLayout()
        self.push_btn = QPushButton('同步题库到设备')
        self.push_btn.setIcon(get_icon('push'))
        self.push_btn.clicked.connect(self.push_all)
        self.pull_btn = QPushButton('拉取成绩')
        self.pull_btn.setIcon(get_icon('pull'))
        self.pull_btn.clicked.connect(self.pull_all)
        hb.addWidget(self.push_btn)
        hb.addWidget(self.pull_btn)
        lay.addLayout(hb)
        self.sync_spinner = LoadingIndicator(self)
        self.sync_spinner.hide()
        lay.addWidget(self.sync_spinner)
        from PySide6.QtWidgets import QListWidget
        self.sync_log = QListWidget()
        self.sync_log.setMinimumHeight(120)
        lay.addWidget(self.sync_log)
        lay.addStretch()
        w.setLayout(lay)
        return w
    def refresh_targets(self):
        targets = list_sync_targets()
        self.targets_table.setRowCount(0)
        for t in targets:
            r = self.targets_table.rowCount()
            self.targets_table.insertRow(r)
            self.targets_table.setItem(r, 0, QTableWidgetItem(t[1]))  # Name
            self.targets_table.setItem(r, 1, QTableWidgetItem(t[2]))  # IP
            self.targets_table.setItem(r, 2, QTableWidgetItem(t[3]))  # Username
            self.targets_table.setItem(r, 3, QTableWidgetItem(t[4]))  # Remote path
            
            # SSH password (show asterisks if exists)
            password_text = '******' if t[5] else ''
            self.targets_table.setItem(r, 4, QTableWidgetItem(password_text))
            
            # Create action buttons
            action_widget = QWidget()
            action_layout = QHBoxLayout()
            action_layout.setContentsMargins(4, 4, 4, 4)
            
            # Edit button
            edit_btn = QPushButton('编辑')
            edit_btn.setStyleSheet("QPushButton { background-color:#409eff; color:#fff; padding:4px 8px; font-size:12px; border-radius:6px; }")
            edit_btn.clicked.connect(lambda checked, tid=t[0]: self.edit_target(tid))
            action_layout.addWidget(edit_btn)
            
            # Delete button
            delete_btn = QPushButton('删除')
            delete_btn.setStyleSheet("QPushButton { background-color:#f56c6c; color:#fff; padding:4px 8px; font-size:12px; }")
            delete_btn.clicked.connect(lambda checked, tid=t[0]: self.delete_target(tid))
            action_layout.addWidget(delete_btn)
            
            action_widget.setLayout(action_layout)
            self.targets_table.setCellWidget(r, 5, action_widget)
    def add_target(self):
        name = self.t_name.text().strip()
        ip = self.t_ip.text().strip()
        user = self.t_user.text().strip()
        path = self.t_path.text().strip()
        password = self.t_password.text().strip()
        if not name or not ip or not user or not path:
            QMessageBox.warning(self, '错误', '请完整填写设备信息')
            return
        upsert_sync_target(name, ip, user, path, password if password else None)
        self.refresh_targets()
        self.t_name.clear()
        self.t_ip.clear()
        self.t_user.clear()
        self.t_path.clear()
        self.t_password.clear()
        QMessageBox.information(self, '成功', '设备已添加')
    
    def edit_target(self, target_id):
        # Get current target data
        targets = list_sync_targets()
        target = None
        for t in targets:
            if t[0] == target_id:
                target = t
                break
        
        if not target:
            return
        
        # Create edit dialog
        from PySide6.QtWidgets import QDialog, QDialogButtonBox
        dialog = QDialog(self)
        dialog.setWindowTitle('编辑设备')
        dialog.setFixedSize(400, 300)
        
        layout = QFormLayout()
        
        name_edit = QLineEdit(target[1])
        ip_edit = QLineEdit(target[2])
        user_edit = QLineEdit(target[3])
        path_edit = QLineEdit(target[4])
        password_edit = QLineEdit()
        password_edit.setPlaceholderText('留空保持原密码')
        password_edit.setEchoMode(QLineEdit.Password)
        
        layout.addRow('名称', name_edit)
        layout.addRow('IP', ip_edit)
        layout.addRow('用户名', user_edit)
        layout.addRow('远程路径', path_edit)
        layout.addRow('SSH密码', password_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        def save_changes():
            new_name = name_edit.text().strip()
            new_ip = ip_edit.text().strip()
            new_user = user_edit.text().strip()
            new_path = path_edit.text().strip()
            new_password = password_edit.text().strip()
            
            if not new_name or not new_ip or not new_user or not new_path:
                QMessageBox.warning(dialog, '错误', '请完整填写设备信息')
                return
            
            try:
                update_sync_target(target_id, new_name, new_ip, new_user, new_path, 
                                 new_password if new_password else None)
                self.refresh_targets()
                dialog.accept()
                QMessageBox.information(self, '成功', '设备已更新')
            except Exception as e:
                QMessageBox.warning(dialog, '错误', str(e))
        
        buttons.accepted.connect(save_changes)
        buttons.rejected.connect(dialog.reject)
        dialog.exec()
    
    def delete_target(self, target_id):
        reply = QMessageBox.question(self, '确认', '确定要删除该设备吗？', QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                delete_sync_target(target_id)
                self.refresh_targets()
                QMessageBox.information(self, '成功', '设备已删除')
            except Exception as e:
                QMessageBox.warning(self, '错误', str(e))
    def push_all(self):
        targets = list_sync_targets()
        if not targets:
            QMessageBox.information(self, '提示', '没有配置任何设备')
            return
        
        # Disable sync buttons during operation
        self.set_sync_buttons_enabled(False)
        if hasattr(self, 'push_btn'):
            self.push_btn.setEnabled(False)
        if hasattr(self, 'pull_btn'):
            self.pull_btn.setEnabled(False)
        if hasattr(self, 'sync_spinner'):
            self.sync_spinner.show()
        
        # Create and start worker thread
        self.sync_worker = SyncWorker(targets, 'push')
        self.sync_worker.finished.connect(self.on_sync_finished)
        self.sync_worker.error.connect(self.on_sync_error)
        self.sync_worker.progress.connect(lambda msg: self.sync_log.addItem(msg))
        self.sync_worker.start()
        
        self.show_sync_progress('正在同步题库到设备，请稍候...')
    
    def pull_all(self):
        targets = list_sync_targets()
        if not targets:
            QMessageBox.information(self, '提示', '没有配置任何设备')
            return
        
        # Disable sync buttons during operation
        self.set_sync_buttons_enabled(False)
        if hasattr(self, 'push_btn'):
            self.push_btn.setEnabled(False)
        if hasattr(self, 'pull_btn'):
            self.pull_btn.setEnabled(False)
        if hasattr(self, 'sync_spinner'):
            self.sync_spinner.show()
        
        # Create and start worker thread
        self.sync_worker = SyncWorker(targets, 'pull')
        self.sync_worker.finished.connect(self.on_sync_finished)
        self.sync_worker.error.connect(self.on_sync_error)
        self.sync_worker.progress.connect(lambda msg: self.sync_log.addItem(msg))
        self.sync_worker.start()
        
        self.show_sync_progress('正在拉取成绩，请稍候...')
    
    def set_sync_buttons_enabled(self, enabled):
        # Find and disable/enable sync buttons
        for i in range(self.targets_table.rowCount()):
            widget = self.targets_table.cellWidget(i, 5)
            if widget:
                for child in widget.findChildren(QPushButton):
                    child.setEnabled(enabled)
        if hasattr(self, 'push_btn'):
            self.push_btn.setEnabled(enabled)
        if hasattr(self, 'pull_btn'):
            self.pull_btn.setEnabled(enabled)
    
    def on_sync_finished(self, results):
        self.set_sync_buttons_enabled(True)
        if hasattr(self, 'sync_worker'):
            self.sync_worker.deleteLater()
        if hasattr(self, 'sync_spinner'):
            self.sync_spinner.hide()
        if hasattr(self, 'sync_progress_dialog') and getattr(self, 'sync_progress_dialog'):
            try:
                self.sync_progress_dialog.close()
            except Exception:
                pass
            self.sync_progress_dialog = None
        
        # Refresh scores after pull operation
        if '拉取' in results:
            self.refresh_scores()
        
        QMessageBox.information(self, '完成', f'操作完成:\n{results}')
    
    def on_sync_error(self, error):
        self.set_sync_buttons_enabled(True)
        if hasattr(self, 'sync_worker'):
            self.sync_worker.deleteLater()
        if hasattr(self, 'sync_spinner'):
            self.sync_spinner.hide()
        if hasattr(self, 'sync_progress_dialog') and getattr(self, 'sync_progress_dialog'):
            try:
                self.sync_progress_dialog.close()
            except Exception:
                pass
            self.sync_progress_dialog = None
        QMessageBox.warning(self, '错误', f'同步错误:\n{error}')
    def scores_tab(self):
        w = QWidget()
        lay = QVBoxLayout()
        gb = QGroupBox('成绩列表')
        vb = QVBoxLayout()
        self.scores_table = QTableWidget(0, 8)
        self.scores_table.setHorizontalHeaderLabels(['尝试UUID', '用户名', '姓名', '用户ID', '试题ID', '开始', '提交', '分数/通过'])
        self.scores_table.horizontalHeader().setStretchLastSection(True)
        self.scores_table.setAlternatingRowColors(True)
        self.refresh_scores()
        vb.addWidget(self.scores_table)
        gb.setLayout(vb)
        lay.addWidget(gb)
        w.setLayout(lay)
        return w
    def refresh_scores(self):
        self.scores_table = getattr(self, 'scores_table', QTableWidget(0, 8))
        self.scores_table.setRowCount(0)
        from models import list_attempts_with_user
        for a in list_attempts_with_user():
            r = self.scores_table.rowCount()
            self.scores_table.insertRow(r)
            self.scores_table.setItem(r, 0, QTableWidgetItem(a[0]))
            self.scores_table.setItem(r, 1, QTableWidgetItem(a[1] or ''))
            self.scores_table.setItem(r, 2, QTableWidgetItem(a[2] or ''))
            self.scores_table.setItem(r, 3, QTableWidgetItem(str(a[3])))
            self.scores_table.setItem(r, 4, QTableWidgetItem(str(a[4])))
            self.scores_table.setItem(r, 5, QTableWidgetItem(a[5] or ''))
            self.scores_table.setItem(r, 6, QTableWidgetItem(a[6] or ''))
            passed_text = '通过' if a[8] == 1 else '未通过'
            badge_bg = '#e1f3d8' if a[8] == 1 else '#fde2e2'
            badge_fg = '#67c23a' if a[8] == 1 else '#f56c6c'
            self.scores_table.setCellWidget(r, 7, self.make_tag(f'{a[7]} / {passed_text}', badge_bg, badge_fg))
            for c in (3,4):
                it = self.scores_table.item(r, c)
                if it:
                    it.setTextAlignment(Qt.AlignCenter)

class UserView(QWidget):
    def __init__(self, user, parent=None):
        super().__init__(parent)
        colors = theme_manager.get_theme_colors()
        bkg = 'background' + '-color'
        col = 'co' + 'lor'
        bd = 'bor' + 'der'
        pd = 'pad' + 'ding'
        br = 'border' + '-radius'
        
        ss_user = (
            f"QWidget {{ {bkg}:{colors['background']}; font-family:\"PingFang SC\",sans-serif; }}\n"
            f"QGroupBox {{ font-weight:bold; {bd}:1px solid {colors['border']}; {br}:8px; margin-top:8px; padding-top:8px; }}\n"
            f"QListWidget {{ {bd}:1px solid {colors['border']}; {br}:8px; {bkg}:{colors['card_background']}; }}\n"
            f"QPushButton {{ {bkg}:{colors['button_primary']}; {col}:{colors['text_inverse']}; {pd}:6px 12px; border:none; {br}:8px; }}\n"
            f"QPushButton:hover {{ {bkg}:{colors['button_primary_hover']}; }}\n"
            f"QTableWidget {{ {bd}:1px solid {colors['border']}; {br}:8px; {bkg}:{colors['card_background']}; }}\n"
            f"QTableWidget::item:hover {{ {bkg}:{colors['border_light']}; }}\n"
            f"QTableWidget::item:selected {{ {bkg}:{colors['primary']}; {col}:{colors['text_inverse']}; }}\n"
            f"QHeaderView::section {{ {bkg}:{colors['border_light']}; {col}:{colors['text_secondary']}; font-weight:600; {pd}:6px 8px; {bd}:none; {bd}-right:1px solid {colors['border']}; }}\n"
            f"QComboBox {{ {pd}:6px 8px; {bd}:1px solid {colors['input_border']}; {br}:8px; {bkg}:{colors['input_background']}; {col}:{colors['text_primary']}; }}\n"
            f"QComboBox:focus {{ {bd}-color:{colors['primary']}; }}\n"
            f"QComboBox::drop-down {{ width:24px; border:none; }}\n"
            f"QComboBox QAbstractItemView {{ {bkg}:{colors['card_background']}; {bd}:1px solid {colors['border']}; {pd}:4px; outline:0; }}\n"
        )
        self.setStyleSheet(ss_user)
        self.user = user
        layout = QVBoxLayout()
        topbar = QHBoxLayout()
        name_display = user.get('full_name')
        user_label = QLabel(f'当前用户: {user["username"]}' + (f'（{name_display}）' if name_display else ''))
        topbar.addWidget(user_label)
        topbar.addStretch()
        logout_btn = QPushButton('退出登录')
        logout_btn.clicked.connect(self.handle_logout)
        topbar.addWidget(logout_btn)
        layout.addLayout(topbar)
        content = QHBoxLayout()
        gb1 = QGroupBox('可选试题')
        vb1 = QVBoxLayout()
        self.exams_table_user = QTableWidget(0, 4)
        self.exams_table_user.setHorizontalHeaderLabels(['ID', '标题', '限时(分钟)', '操作'])
        self.exams_table_user.horizontalHeader().setStretchLastSection(True)
        self.exams_table_user.setAlternatingRowColors(True)
        self.refresh_exams()
        vb1.addWidget(self.exams_table_user)
        gb1.setLayout(vb1)
        gb2 = QGroupBox('历史成绩')
        vb2 = QVBoxLayout()
        self.attempts_table = QTableWidget(0, 5)
        self.attempts_table.setHorizontalHeaderLabels(['尝试UUID', '试题ID', '开始', '提交', '分数/通过'])
        self.attempts_table.horizontalHeader().setStretchLastSection(True)
        self.attempts_table.setAlternatingRowColors(True)
        self.refresh_attempts()
        vb2.addWidget(self.attempts_table)
        gb2.setLayout(vb2)
        content.addWidget(gb1, 1)
        content.addWidget(gb2, 1)
        layout.addLayout(content)
        self.setLayout(layout)
    def refresh_exams(self):
        tbl = getattr(self, 'exams_table_user', None)
        if tbl is None:
            return
        tbl.setRowCount(0)
        for e in list_exams(include_expired=False):
            r = tbl.rowCount()
            tbl.insertRow(r)
            tbl.setItem(r, 0, QTableWidgetItem(str(e[0])))
            tbl.setItem(r, 1, QTableWidgetItem(e[1] or ''))
            tbl.setItem(r, 2, QTableWidgetItem(str(e[4])))
            opw = QWidget()
            hb = QHBoxLayout()
            hb.setContentsMargins(0,0,0,0)
            btn = QPushButton('开始考试')
            btn.setIcon(get_icon('exam_start'))
            exam_id = e[0]
            btn.clicked.connect(lambda _, x=exam_id: self.start_exam(x))
            hb.addWidget(btn)
            hb.addStretch()
            opw.setLayout(hb)
            tbl.setCellWidget(r, 3, opw)
    def refresh_attempts(self):
        self.attempts_table.setRowCount(0)
        for a in list_attempts(self.user['id']):
            r = self.attempts_table.rowCount()
            self.attempts_table.insertRow(r)
            self.attempts_table.setItem(r, 0, QTableWidgetItem(a[0]))
            self.attempts_table.setItem(r, 1, QTableWidgetItem(str(a[2])))
            self.attempts_table.setItem(r, 2, QTableWidgetItem(a[3] or ''))
            self.attempts_table.setItem(r, 3, QTableWidgetItem(a[4] or ''))
            ucell = QTableWidgetItem(f'{a[5]} / {"通过" if a[6]==1 else "未通过"}')
            if a[6] == 1:
                ucell.setBackground(QColor('#e1f3d8'))
            else:
                ucell.setBackground(QColor('#fde2e2'))
            self.attempts_table.setItem(r, 4, ucell)
    def start_exam(self, exam_id=None):
        if exam_id is None:
            tbl = getattr(self, 'exams_table_user', None)
            if tbl is None:
                QMessageBox.warning(self, '错误', '请选择试题')
                return
            r = tbl.currentRow()
            if r < 0:
                QMessageBox.warning(self, '错误', '请选择试题')
                return
            it = tbl.item(r, 0)
            exam_id = int(it.text()) if it and it.text() else None
        if not exam_id:
            QMessageBox.warning(self, '错误', '请选择试题')
            return
        ExamWindow(self.user, exam_id, self).show()
    def handle_logout(self):
        p = self.parent()
        while p is not None and not hasattr(p, 'logout'):
            p = p.parent()
        if p is not None:
            p.logout()

class ExamWindow(QMainWindow):
    def __init__(self, user, exam_id, parent=None):
        super().__init__(parent)
        self.user = user
        self.exam_id = exam_id
        questions = list_questions(exam_id)
        questions_len = len(questions)
        self.questions = []
        self.total_score = 0
        for _ in range(questions_len):
            rand_q = random.choice(questions)
            self.questions.append(rand_q)
            self.total_score += rand_q["score"]
            questions.remove(rand_q)
        self.attempt_uuid = start_attempt(user['id'], exam_id)
        self.current_index = 0
        self.setWindowTitle(f'考试进行中, 总分: {self.total_score}')
        colors = theme_manager.get_theme_colors()
        bkg = 'background' + '-color'
        col = 'co' + 'lor'
        bd = 'bor' + 'der'
        pd = 'pad' + 'ding'
        fs = 'font' + '-size'
        br = 'border' + '-radius'
        ss_exam = (
            f"QMainWindow {{ {bkg}:{colors['background']}; }}\n"
            f"QLabel {{ {fs}:16px; {col}:{colors['text_primary']}; }}\n"
            f"QPushButton {{ {bkg}:{colors['button_primary']}; {col}:{colors['text_inverse']}; {pd}:8px 16px; border:none; {br}:8px; {fs}:14px; }}\n"
            f"QPushButton:hover {{ {bkg}:{colors['button_primary_hover']}; }}\n"
            f"QPushButton:disabled {{ {bkg}:{colors['border_light']}; {col}:{colors['text_inverse']}; }}\n"
            f"QListWidget {{ {bd}:1px solid {colors['border']}; {br}:8px; {pd}:4px; }}\n"
            f"QListWidget::item {{ {pd}:6px; }}\n"
            f"QListWidget::item:selected {{ {bkg}:{colors['primary']}; {col}:{colors['text_inverse']}; }}\n"
        )
        self.setStyleSheet(ss_exam)
        central = QWidget()
        lay = QVBoxLayout()
        self.timer_widget = ModernTimer()
        lay.addWidget(self.timer_widget)
        self.progress_bar = ModernProgressBar()
        self.progress_bar.setRange(0, max(1, len(self.questions)))
        self.progress_bar.setValue(1)
        lay.addWidget(self.progress_bar)
        gb = QGroupBox()
        gb.setStyleSheet(f"QGroupBox {{ border:1px solid {colors['border']}; border-radius:8px; padding:12px; }}")
        vb = QVBoxLayout()
        self.q_title = QLabel('')
        self.q_title.setWordWrap(True)
        self.q_title.setStyleSheet("font-size:16px; margin-bottom:8px;")
        self.q_opts = QListWidget()
        self.q_opts.itemChanged.connect(self.on_option_changed)
        vb.addWidget(self.q_title)
        vb.addWidget(self.q_opts)
        gb.setLayout(vb)
        lay.addWidget(gb)
        hb = QHBoxLayout()
        self.prev_btn = QPushButton('上一题')
        self.next_btn = QPushButton('下一题')
        self.submit_btn = QPushButton('提交')
        self.submit_btn.setIcon(get_icon('submit'))
        self.next_btn.setDefault(True)
        self.submit_btn.setEnabled(False)
        self.prev_btn.clicked.connect(self.prev_q)
        self.next_btn.clicked.connect(self.next_q)
        self.submit_btn.clicked.connect(self.submit)
        hb.addWidget(self.prev_btn)
        hb.addWidget(self.next_btn)
        hb.addStretch()
        hb.addWidget(self.submit_btn)
        lay.addLayout(hb)
        central.setLayout(lay)
        self.setCentralWidget(central)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.answers = {}
        tl = 0
        for e in list_exams(include_expired=True):
            if e[0] == exam_id:
                tl = int(e[4])
                break
        self.remaining = tl * 60
        self.timer.start(1000)
        self.timer_widget.start_timer(self.remaining)
        self.render_q()
    def all_answered(self):
        for q in self.questions:
            sel = self.answers.get(q['id'])
            if q['type'] in ('single', 'truefalse'):
                if not sel or len(sel) != 1:
                    return False
            elif q['type'] == 'multiple':
                if not sel or len(sel) == 0:
                    return False
            else:
                if not sel:
                    return False
        return True
    def update_buttons_state(self):
        self.prev_btn.setEnabled(self.current_index > 0)
        self.next_btn.setEnabled(self.current_index < len(self.questions) - 1)
        self.submit_btn.setEnabled(self.all_answered())
    def tick(self):
        self.remaining -= 1
        if self.remaining <= 0:
            self.submit()
            return
        self.progress_bar.setValue(min(len(self.questions), self.current_index + 1))
    def render_q(self):
        if self.current_index < 0:
            self.current_index = 0
        if self.current_index >= len(self.questions):
            self.current_index = len(self.questions) - 1
        q = self.questions[self.current_index]
        self.q_title.setText(f'{self.current_index+1}/{len(self.questions)} {q["text"]} ({q["type"]} 分值:{q["score"]})')
        self.q_opts.blockSignals(True)
        self.q_opts.clear()
        if q['type'] == 'truefalse':
            for opt in ['True', 'False']:
                item = QListWidgetItem(opt)
                item.setCheckState(Qt.Unchecked)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.q_opts.addItem(item)
        else:
            for opt in q['options']:
                item = QListWidgetItem(f'{opt.get("key")}. {opt.get("text")}')
                item.setCheckState(Qt.Unchecked)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.q_opts.addItem(item)
        sel = self.answers.get(q['id'])
        if sel:
            if q['type'] == 'truefalse' and len(sel) == 1:
                for i in range(self.q_opts.count()):
                    it = self.q_opts.item(i)
                    if it.text() == 'True':
                        it.setCheckState(Qt.Checked if sel[0] is True else Qt.Unchecked)
                    elif it.text() == 'False':
                        it.setCheckState(Qt.Checked if sel[0] is False else Qt.Unchecked)
            else:
                sset = set(sel)
                for i in range(self.q_opts.count()):
                    it = self.q_opts.item(i)
                    key = it.text().split('.', 1)[0]
                    it.setCheckState(Qt.Checked if key in sset else Qt.Unchecked)
        self.q_opts.blockSignals(False)
        self.update_buttons_state()
        self.progress_bar.setValue(self.current_index + 1)
    def collect_selected(self):
        q = self.questions[self.current_index]
        selected = []
        for i in range(self.q_opts.count()):
            it = self.q_opts.item(i)
            if it.checkState() == Qt.Checked:
                txt = it.text()
                if q['type'] == 'truefalse':
                    selected = [txt == 'True']
                else:
                    key = txt.split('.', 1)[0]
                    selected.append(key)
        if q['type'] == 'single':
            selected = selected[:1]
        return selected
    def save_current(self):
        q = self.questions[self.current_index]
        sel = self.collect_selected()
        if q['type'] == 'truefalse':
            save_answer(self.attempt_uuid, q['id'], sel)
        elif q['type'] == 'single':
            save_answer(self.attempt_uuid, q['id'], sel)
        else:
            save_answer(self.attempt_uuid, q['id'], sel)
        self.answers[q['id']] = sel
        self.update_buttons_state()
    def on_option_changed(self, item):
        q = self.questions[self.current_index]
        if item.checkState() == Qt.Checked and q['type'] in ('single', 'truefalse'):
            self.q_opts.blockSignals(True)
            for i in range(self.q_opts.count()):
                it = self.q_opts.item(i)
                if it is not item:
                    it.setCheckState(Qt.Unchecked)
            self.q_opts.blockSignals(False)
        sel = self.collect_selected()
        self.answers[q['id']] = sel
        self.update_buttons_state()
    def next_q(self):
        self.save_current()
        self.current_index += 1
        if self.current_index >= len(self.questions):
            self.current_index = len(self.questions) - 1
        self.render_q()
    def prev_q(self):
        self.save_current()
        self.current_index -= 1
        if self.current_index < 0:
            self.current_index = 0
        self.render_q()
    def submit(self):
        self.save_current()
        self.timer.stop()
        score, passed = submit_attempt(self.attempt_uuid)
        QMessageBox.information(self, '结果', f'得分:{score} {"通过" if passed==1 else "未通过"}')
        p = self.parent()
        if p is not None and hasattr(p, 'refresh_attempts'):
            p.refresh_attempts()
        self.close()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        ensure_db()
        create_admin_if_absent()
        self.setWindowTitle('本地考试系统')
        self.setMinimumSize(900, 600)
        self.resize(1440, 960)
        colors = theme_manager.get_theme_colors()
        bkg = 'background' + '-color'
        self.setStyleSheet(f"QMainWindow {{ {bkg}:{colors['background']}; }}")
        self.stack = QStackedWidget()
        self.login = LoginView(self.on_login)
        self.stack.addWidget(self.login)
        self.setCentralWidget(self.stack)
    def on_login(self, user):
        if user['role'] == 'admin':
            self.admin = AdminView(self)
            self.stack.addWidget(self.admin)
            self.stack.setCurrentWidget(self.admin)
        else:
            self.user_view = UserView(user, self)
            self.stack.addWidget(self.user_view)
            self.stack.setCurrentWidget(self.user_view)
    def logout(self):
        for i in range(1, self.stack.count()):
            w = self.stack.widget(i)
            self.stack.removeWidget(w)
            w.deleteLater()
        self.stack.setCurrentWidget(self.login)

def run():
    app = QApplication([])
    app.setStyle('Fusion')
    win = MainWindow()
    win.show()
    app.exec()

if __name__ == '__main__':
    run()