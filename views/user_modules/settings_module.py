from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QGroupBox, QFormLayout
from icon_manager import IconManager
from theme_manager import theme_manager
from language import tr
from models import update_user_basic, authenticate
from utils import show_info, show_warn

class UserSettingsModule(QWidget):
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.icon_manager = IconManager()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Basic Info Group
        basic_group = QGroupBox(tr('settings.basic_info'))
        basic_layout = QFormLayout()
        basic_layout.setContentsMargins(15, 20, 15, 15)
        basic_layout.setSpacing(10)

        self.username_label = QLabel(self.user.get('username', ''))
        self.full_name_edit = QLineEdit(self.user.get('full_name', ''))
        self.full_name_edit.setPlaceholderText(tr('admin.users.full_name_ph'))

        basic_layout.addRow(tr('settings.username') + ":", self.username_label)
        basic_layout.addRow(tr('settings.full_name') + ":", self.full_name_edit)
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Change Password Group
        pwd_group = QGroupBox(tr('settings.change_password'))
        pwd_layout = QFormLayout()
        pwd_layout.setContentsMargins(15, 20, 15, 15)
        pwd_layout.setSpacing(10)

        self.old_pwd_edit = QLineEdit()
        self.old_pwd_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pwd_edit = QLineEdit()
        self.new_pwd_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_pwd_edit = QLineEdit()
        self.confirm_pwd_edit.setEchoMode(QLineEdit.EchoMode.Password)

        pwd_layout.addRow(tr('settings.old_password') + ":", self.old_pwd_edit)
        pwd_layout.addRow(tr('settings.new_password') + ":", self.new_pwd_edit)
        pwd_layout.addRow(tr('settings.confirm_password') + ":", self.confirm_pwd_edit)
        pwd_group.setLayout(pwd_layout)
        layout.addWidget(pwd_group)

        # Save Button
        save_btn = QPushButton(tr('settings.save'))
        save_btn.setIcon(self.icon_manager.get_icon('confirm'))
        save_btn.setFixedWidth(150)
        save_btn.clicked.connect(self.save_settings)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        layout.addStretch()
        self.setLayout(layout)

    def save_settings(self):
        full_name = self.full_name_edit.text().strip()
        old_pwd = self.old_pwd_edit.text()
        new_pwd = self.new_pwd_edit.text()
        confirm_pwd = self.confirm_pwd_edit.text()

        # Check password change if any password field is filled
        if old_pwd or new_pwd or confirm_pwd:
            if not old_pwd or not new_pwd or not confirm_pwd:
                show_warn(self, tr('common.error'), tr('error.input_username_password'))
                return
            
            if new_pwd != confirm_pwd:
                show_warn(self, tr('common.error'), tr('error.password_mismatch'))
                return
            
            # Verify old password
            user_auth = authenticate(self.user['username'], old_pwd)
            if not user_auth:
                show_warn(self, tr('common.error'), tr('error.old_password_wrong'))
                return

        try:
            update_user_basic(
                self.user['id'], 
                full_name=full_name if full_name else None, 
                password=new_pwd if new_pwd else None
            )
            
            # Update local user object
            if full_name:
                self.user['full_name'] = full_name
            
            show_info(self, tr('common.success'), tr('info.settings_saved'))
            
            # Clear password fields
            self.old_pwd_edit.clear()
            self.new_pwd_edit.clear()
            self.confirm_pwd_edit.clear()
            
            # Optionally refresh user name display in parent view
            p = self.parent()
            while p and not hasattr(p, 'user'):
                p = p.parent()
            if p and hasattr(p, 'user'):
                # This is likely UserView, we might need a method to refresh the top bar
                if hasattr(p, 'refresh_user_info'):
                    p.refresh_user_info()

        except Exception as e:
            show_warn(self, tr('common.error'), str(e))
