import os
import platform
import subprocess
import locale
import re
import importlib

_LANG = None

def _normalize(code):
    if not code:
        return 'zh-Hans'
    c = str(code)
    if c.startswith('zh-Hans') or c.startswith('zh-CN') or c.startswith('zh_SG') or c.startswith('zh_CN'):
        return 'zh-Hans'
    if c.startswith('zh'):
        return 'zh-Hans'
    if c.lower().startswith('en'):
        return 'en'
    return 'zh-Hans'

def get_system_language_codes():
    sysname = platform.system()
    out = []
    if sysname == 'Darwin':
        try:
            p = subprocess.run(['defaults', 'read', '-g', 'AppleLanguages'], capture_output=True, text=True, timeout=1)
            s = p.stdout or ''
            out = re.findall(r'"([^"]+)"', s)
        except Exception:
            out = []
        if not out:
            try:
                loc = locale.getdefaultlocale()
                if loc and loc[0]:
                    out = [loc[0]]
            except Exception:
                pass
            env = os.environ.get('LANG')
            if env:
                out.append(env)
    elif sysname == 'Windows':
        try:
            ctypes = importlib.import_module('ctypes')
            langid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            m = locale.windows_locale
            code = m.get(langid)
            if code:
                out = [code]
        except Exception:
            out = []
        if not out:
            try:
                winreg = importlib.import_module('winreg')
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Control Panel\International') as k:
                    name, _ = winreg.QueryValueEx(k, 'LocaleName')
                    if name:
                        out = [name]
            except Exception:
                pass
        if not out:
            try:
                loc = locale.getdefaultlocale()
                if loc and loc[0]:
                    out = [loc[0]]
            except Exception:
                pass
    else:
        for v in ('LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG'):
            val = os.environ.get(v)
            if val:
                out.append(val)
        if not out:
            try:
                loc = locale.getdefaultlocale()
                if loc and loc[0]:
                    out = [loc[0]]
            except Exception:
                pass
    return out or ['zh-Hans']

def detect_language():
    codes = get_system_language_codes()
    return _normalize(codes[0] if codes else None)

def set_language(code):
    global _LANG
    _LANG = _normalize(code)

def _current_lang():
    global _LANG
    if not _LANG:
        _LANG = detect_language()
    return _LANG

_DICT = {
    'zh-Hans': {
        'common.error': '错误',
        'common.success': '成功',
        'common.hint': '提示',
        'common.logout': '退出登录',
        'common.refresh': '刷新',
        'common.permanent': '永久',
        'login.title': '📝 登录',
        'login.username': '用户名',
        'login.password': '密码',
        'login.button': '登录',
        'login.decrypt_failed': '数据库解密失败，请联系管理员',
        'error.bad_credentials': '用户名或密码错误',
        'user.center': '用户中心',
        'user.current_user_prefix': '当前用户: ',
        'user.full_name_suffix': '（{name}）',
        'user.exams_tab': '试题列表',
        'user.history_tab': '历史成绩',
        'user.start_exam': '开始考试',
        'exams.id': 'ID',
        'exams.title': '标题',
        'exams.desc': '描述',
        'exams.time_limit': '限时(分钟)',
        'exams.deadline': '截止',
        'exams.pass_ratio': '及格比例%',
        'exams.q_count': '题目数量',
        'exams.total': '总分',
        'exams.best': '历史最高分',
        'attempts.uuid': 'UUID记录',
        'attempts.exam_title': '试题',
        'attempts.started': '开始',
        'attempts.submitted': '提交',
        'attempts.score_pass': '分数/通过',
        'attempts.score_total_pass': '分数/总分/通过',
        'attempts.data_invalid': '数据异常',
        'attempts.pass': '通过',
        'attempts.fail': '未通过',
        'error.select_exam': '请选择试题',
        'error.select_exam_single': '一次仅能选择一个试题',
        'error.no_questions': '该试题暂无题目，无法开始',
        'error.select_user': '请选择用户',
        'admin.dashboard': '管理后台',
        'admin.users_tab': '用户',
        'admin.exams_tab': '试题',
        'admin.sync_tab': '同步',
        'admin.scores_tab': '成绩',
        'admin.users_group': '用户列表',
        'admin.new_user_group': '新增用户',
        'admin.exams_group': '试题列表',
        'admin.new_exam_group': '新建试题',
        'admin.import_questions': '导入题目',
        'admin.export_sample': '导出题目示例',
        'admin.role.admin': '管理员',
        'admin.role.user': '普通用户',
        'admin.status.active': '活跃',
        'admin.status.inactive': '禁用',
        'admin.users.headers.id': 'ID',
        'admin.users.headers.username': '用户名',
        'admin.users.headers.full_name': '姓名',
        'admin.users.headers.role': '角色',
        'admin.users.headers.status': '状态',
        'admin.users.headers.created_at': '创建时间',
        'admin.users.headers.actions': '操作',
        'admin.users.username_ph': '用户名',
        'admin.users.password_ph': '密码',
        'admin.users.full_name_ph': '姓名(可选)',
        'admin.users.add_button': '新增用户',
        'admin.users.export_tpl': '导出用户Excel模板',
        'admin.users.import_excel': '从Excel导入用户',
        'admin.user.delete': '删除',
        'admin.user.set_admin': '设为管理员',
        'admin.user.set_user': '设为普通用户',
        'admin.user.disable': '禁用',
        'admin.user.enable': '启用',
        'error.input_username_password': '请输入用户名和密码',
        'error.username_format': '用户名格式错误：仅允许ASCII字母、数字、_@.-',
        'error.password_format': '密码格式错误：仅允许可见ASCII字符',
        'info.user_created': '用户已创建',
        'confirm.delete_user': '确定要删除该用户吗？',
        'info.user_deleted': '用户已删除',
        'info.user_role_updated': '用户角色已更新为{role}',
        'info.user_status_updated': '用户已{status}',
        'admin.exams.headers.id': 'ID',
        'admin.exams.headers.title': '标题',
        'admin.exams.headers.pass_ratio': '及格比例',
        'admin.exams.headers.time_limit': '限时(分钟)',
        'admin.exams.headers.deadline': '截止',
        'admin.exams.headers.description': '描述',
        'admin.exams.headers.q_count': '题目数量',
        'admin.exams.headers.total': '总分',
        'admin.exams.headers.actions': '操作',
        'admin.exams.form.title': '标题',
        'admin.exams.form.description': '描述',
        'admin.exams.form.pass_ratio': '及格比例%',
        'admin.exams.form.time_limit': '限时(分钟)',
        'admin.exams.form.end_date': '结束日期',
        'admin.exams.form.random_pick': '随机抽取数量(随机题库)',
        'admin.exams.permanent_checkbox': '永久有效',
        'admin.exams.add_btn': '新增试题',
        'common.clear': '清空',
        'common.delete': '删除',
        'error.title_required': '标题不能为空',
        'info.exam_added': '试题已新增',
        'admin.import.title': '选择题目文件',
        'admin.export.sample.title': '导出题目示例',
        'admin.export.sample.done': '示例已导出',
        'admin.import.error.file_decode': '文件解码失败：请使用UTF-8或GB18030编码',
        'admin.import.error.not_supported': '不支持的文件格式：请提供JSON/YAML/Excel',
        'admin.import.error.no_data': '未读取到数据',
        'admin.import.error.jsonyaml_missing': 'JSON/YAML 顶层需包含 mandatory 或 random',
        'admin.import.error.jsonyaml_dict': 'JSON/YAML 顶层必须为对象',
        'admin.import.error.no_valid': '没有任何有效题目',
        'admin.import.success': '导入成功：单选{single} 多选{multiple} 判断{truefalse}；必考{mandatory} 随机{random}{extra}',
        'admin.import.extra_prefix': '\n部分题目未导入：\n',
        'admin.exams.clear_confirm': '确定要清空该试题的所有题目吗？',
        'admin.exams.clear_done': '已清空该试题的所有题目',
        'admin.exams.delete_confirm': '确定要删除该试题吗？所有相关题目与成绩将一并删除',
        'admin.exams.delete_done': '试题已删除',
        'admin.export.users_tpl.title': '导出用户Excel模板',
        'admin.export.users_tpl.done': '用户模板已导出',
        'admin.import.users.title': '选择用户Excel',
        'admin.import.users.error.missing': '缺少必要列: 用户名/密码/角色/状态',
        'admin.import.users.result': '导入成功:{ok} 失败:{fail}',
        'admin.import.users.format_error': '格式错误',
        'admin.import.users.row_empty': '第{idx}行：用户名或密码为空',
        'admin.import.users.row_user_format': '第{idx}行：用户名格式错误',
        'admin.import.users.row_pwd_format': '第{idx}行：密码格式错误',
        'admin.targets.group': '设备列表',
        'admin.targets.headers.name': '名称',
        'admin.targets.headers.ip': 'IP',
        'admin.targets.headers.username': '用户名',
        'admin.targets.headers.remote_path': '远程路径',
        'admin.targets.headers.ssh_password': 'SSH密码',
        'admin.targets.add_group': '添加设备',
        'admin.targets.name_ph': '设备名称',
        'admin.targets.ip_ph': '192.168.x.x',
        'admin.targets.username_ph': '用户名',
        'admin.targets.remote_path_ph': '~/.exam_system/',
        'admin.targets.ssh_password_ph': 'SSH密码（可选）',
        'admin.targets.add_btn': '添加设备',
        'admin.targets.form.name': '名称',
        'admin.targets.form.ip': 'IP',
        'admin.targets.form.username': '用户名',
        'admin.targets.form.remote_path': '远程路径',
        'admin.targets.form.ssh_password': 'SSH密码',
        'admin.export.targets_tpl.title': '导出设备Excel模板',
        'admin.export.targets_tpl.done': '设备模板已导出',
        'admin.import.targets.title': '选择设备Excel',
        'admin.import.targets.error.missing': '缺少必要列: 名称/IP/用户名/远程路径',
        'admin.targets.edit.title': '编辑设备',
        'admin.targets.edit.keep_pwd': '留空保持原密码',
        'error.empty_device_info': '请完整填写设备信息',
        'info.device_updated': '设备已更新',
        'confirm.delete_device': '确定要删除该设备吗？',
        'info.device_deleted': '设备已删除',
        'info.device_added': '设备已添加',
        'sync.push_btn': '同步题库到设备',
        'sync.pull_btn': '拉取成绩',
        'sync.sync_btn': '同步数据',
        'sync.progress.title': '同步中',
        'sync.pushing_message': '正在同步题库到设备，请稍候...',
        'sync.pulling_message': '正在拉取成绩，请稍候...',
        'sync.syncing_message': '正在同步数据，请稍候...',
        'sync.status.success': '成功',
        'sync.status.fail': '失败',
        'sync.status.info': '信息',
        'sync.finished.title': '完成',
        'sync.operation_done': '操作完成:\n{results}',
        'sync.error.title': '错误',
        'sync.error.message': '同步错误:\n{error}',
        'scores.group': '成绩列表',
        'scores.headers.uuid': 'UUID记录',
        'scores.headers.username': '用户名',
        'scores.headers.full_name': '姓名',
        'scores.headers.user_id': '用户ID',
        'scores.headers.exam_title': '试题',
        'scores.headers.started': '开始',
        'scores.headers.submitted': '提交',
        'scores.headers.score_total_pass': '分数/满分/通过',
        'scores.export_excel': '导出成绩Excel',
        'scores.not_submitted': '未提交',
        'export.scores.done': '成绩已导出',
        'info.no_targets': '没有配置任何设备',
        'progress.group': '学习进度',
        'progress.replace_import': '覆盖导入',
        'progress.export_tpl': '导出模板',
        'progress.import_tpl': '导入模板',
        'progress.export_user_btn': '导出用户进度',
        'progress.headers.task_title': '任务名',
        'progress.headers.description': '描述',
        'progress.headers.order': '顺序',
        'progress.headers.status': '状态',
        'progress.headers.updated_at': '更新时间',
        'progress.headers.updated_by': '更新人',
        'progress.status.not_started': '未开始',
        'progress.status.in_progress': '进行中',
        'progress.status.completed': '已完成',
        'progress.export_tpl.title': '导出学习进度模板',
        'progress.export_tpl.done': '模板已导出: {path}',
        'progress.import_tpl.title': '导入学习进度模板',
        'progress.import_tpl.replace_confirm': '覆盖导入将清空同名模块下的任务与进度记录，是否继续？',
        'progress.import_tpl.result': '导入模块:{modules} 任务:{tasks} 跳过表:{skipped_sheets}',
        'progress.export_user.title': '导出用户学习进度',
        'progress.export_user.done': '用户进度已导出: {path}',
        'exam.in_progress': '考试进行中, 总分: {total}',
        'exam.prev': '上一题',
        'exam.next': '下一题',
        'exam.submit': '提交',
        'exam.result': '结果',
        'exam.finished_title': '考试完成 得分:{score}/{total} {passed}',
        'exam.pass_text': '通过',
        'exam.fail_text': '未通过',
        'exam.type.single': '单选题',
        'exam.type.multiple': '多选题',
        'exam.type.truefalse': '判断题',
        'exam.true': '正确',
        'exam.false': '错误',
        'exam.already_running': '已有考试正在进行',
        'exam.score_label': '得分',
        'exam.confirm_exit': '确定要退出考试吗？未作答的题目按0分，其他题目正常记分',
        'exam.exit_result': '已退出考试，得分:{score} {pass_text}',
        'exam.unanswered_note': '（未作答按0分）',
        'exam.question_title': '{index}/{total} {text}（{type} 分值:{score}）'
    },
    'en': {
        'common.error': 'Error',
        'common.success': 'Success',
        'common.hint': 'Hint',
        'common.logout': 'Logout',
        'common.refresh': 'Refresh',
        'common.permanent': 'Permanent',
        'login.title': '📝 Login',
        'login.username': 'Username',
        'login.password': 'Password',
        'login.button': 'Login',
        'login.decrypt_failed': 'Database decryption failed, please contact admin',
        'error.bad_credentials': 'Invalid username or password',
        'user.center': 'User Center',
        'user.current_user_prefix': 'Current user: ',
        'user.full_name_suffix': ' ({name})',
        'user.exams_tab': 'Exams',
        'user.history_tab': 'History',
        'user.start_exam': 'Start Exam',
        'exams.id': 'ID',
        'exams.title': 'Title',
        'exams.desc': 'Description',
        'exams.time_limit': 'Time Limit (min)',
        'exams.deadline': 'Deadline',
        'exams.pass_ratio': 'Pass Ratio %',
        'exams.q_count': 'Questions',
        'exams.total': 'Total Score',
        'exams.best': 'Best Score',
        'attempts.uuid': 'Attempt UUID',
        'attempts.exam_title': 'Exam',
        'attempts.started': 'Started',
        'attempts.submitted': 'Submitted',
        'attempts.score_pass': 'Score/Pass',
        'attempts.score_total_pass': 'Score/Total/Pass',
        'attempts.data_invalid': 'Data Invalid',
        'attempts.pass': 'Pass',
        'attempts.fail': 'Fail',
        'error.select_exam': 'Please select an exam',
        'error.select_exam_single': 'Select only one exam',
        'error.no_questions': 'No questions in this exam',
        'error.select_user': 'Please select a user',
        'admin.dashboard': 'Admin Dashboard',
        'admin.users_tab': 'Users',
        'admin.exams_tab': 'Exams',
        'admin.sync_tab': 'Sync',
        'admin.scores_tab': 'Scores',
        'admin.users_group': 'Users',
        'admin.new_user_group': 'Add User',
        'admin.exams_group': 'Exams',
        'admin.new_exam_group': 'New Exam',
        'admin.import_questions': 'Import Questions',
        'admin.export_sample': 'Export Sample',
        'admin.role.admin': 'Admin',
        'admin.role.user': 'User',
        'admin.status.active': 'Active',
        'admin.status.inactive': 'Disabled',
        'admin.users.headers.id': 'ID',
        'admin.users.headers.username': 'Username',
        'admin.users.headers.full_name': 'Full Name',
        'admin.users.headers.role': 'Role',
        'admin.users.headers.status': 'Status',
        'admin.users.headers.created_at': 'Created At',
        'admin.users.headers.actions': 'Actions',
        'admin.users.username_ph': 'Username',
        'admin.users.password_ph': 'Password',
        'admin.users.full_name_ph': 'Full Name (optional)',
        'admin.users.add_button': 'Add User',
        'admin.users.export_tpl': 'Export Users Excel Template',
        'admin.users.import_excel': 'Import Users from Excel',
        'admin.user.delete': 'Delete',
        'admin.user.set_admin': 'Set as Admin',
        'admin.user.set_user': 'Set as User',
        'admin.user.disable': 'Disable',
        'admin.user.enable': 'Enable',
        'error.input_username_password': 'Please enter username and password',
        'error.username_format': 'Invalid username: only ASCII letters, digits, _@.- allowed',
        'error.password_format': 'Invalid password: only visible ASCII characters allowed',
        'info.user_created': 'User created',
        'confirm.delete_user': 'Are you sure to delete this user?',
        'info.user_deleted': 'User deleted',
        'info.user_role_updated': 'User role updated to {role}',
        'info.user_status_updated': 'User {status}',
        'admin.exams.headers.id': 'ID',
        'admin.exams.headers.title': 'Title',
        'admin.exams.headers.pass_ratio': 'Pass Ratio',
        'admin.exams.headers.time_limit': 'Time Limit (min)',
        'admin.exams.headers.deadline': 'Deadline',
        'admin.exams.headers.description': 'Description',
        'admin.exams.headers.q_count': 'Questions',
        'admin.exams.headers.total': 'Total',
        'admin.exams.headers.actions': 'Actions',
        'admin.exams.form.title': 'Title',
        'admin.exams.form.description': 'Description',
        'admin.exams.form.pass_ratio': 'Pass Ratio %',
        'admin.exams.form.time_limit': 'Time Limit (min)',
        'admin.exams.form.end_date': 'End Date',
        'admin.exams.form.random_pick': 'Random pick count (random pool)',
        'admin.exams.permanent_checkbox': 'Permanent',
        'admin.exams.add_btn': 'Add Exam',
        'common.clear': 'Clear',
        'common.delete': 'Delete',
        'error.title_required': 'Title is required',
        'info.exam_added': 'Exam added',
        'admin.import.title': 'Select questions file',
        'admin.export.sample.title': 'Export sample',
        'admin.export.sample.done': 'Sample exported',
        'admin.import.error.file_decode': 'File decode failed: use UTF-8 or GB18030',
        'admin.import.error.not_supported': 'Unsupported format: provide JSON/YAML/Excel',
        'admin.import.error.no_data': 'No data read',
        'admin.import.error.jsonyaml_missing': 'JSON/YAML must include mandatory or random at top-level',
        'admin.import.error.jsonyaml_dict': 'JSON/YAML top-level must be an object',
        'admin.import.error.no_valid': 'No valid questions',
        'admin.import.success': 'Imported: Single {single} Multiple {multiple} True/False {truefalse}; Mandatory {mandatory} Random {random}{extra}',
        'admin.import.extra_prefix': '\nSome questions were not imported:\n',
        'admin.exams.clear_confirm': 'Clear all questions of this exam?',
        'admin.exams.clear_done': 'All questions of this exam have been cleared',
        'admin.exams.delete_confirm': 'Delete this exam? Related questions and scores will be removed',
        'admin.exams.delete_done': 'Exam deleted',
        'admin.export.users_tpl.title': 'Export Users Excel Template',
        'admin.export.users_tpl.done': 'Users template exported',
        'admin.import.users.title': 'Select Users Excel',
        'admin.import.users.error.missing': 'Missing required columns: Username/Password/Role/Status',
        'admin.import.users.result': 'Imported:{ok} Failed:{fail}',
        'admin.import.users.format_error': 'Format error',
        'admin.import.users.row_empty': 'Row {idx}: username or password empty',
        'admin.import.users.row_user_format': 'Row {idx}: invalid username',
        'admin.import.users.row_pwd_format': 'Row {idx}: invalid password',
        'admin.targets.group': 'Devices',
        'admin.targets.headers.name': 'Name',
        'admin.targets.headers.ip': 'IP',
        'admin.targets.headers.username': 'Username',
        'admin.targets.headers.remote_path': 'Remote Path',
        'admin.targets.headers.ssh_password': 'SSH Password',
        'admin.targets.add_group': 'Add Device',
        'admin.targets.name_ph': 'Device name',
        'admin.targets.ip_ph': '192.168.x.x',
        'admin.targets.username_ph': 'Username',
        'admin.targets.remote_path_ph': '~/.exam_system/',
        'admin.targets.ssh_password_ph': 'SSH Password (optional)',
        'admin.targets.add_btn': 'Add Device',
        'admin.targets.form.name': 'Name',
        'admin.targets.form.ip': 'IP',
        'admin.targets.form.username': 'Username',
        'admin.targets.form.remote_path': 'Remote Path',
        'admin.targets.form.ssh_password': 'SSH Password',
        'admin.export.targets_tpl.title': 'Export Devices Excel Template',
        'admin.export.targets_tpl.done': 'Devices template exported',
        'admin.import.targets.title': 'Select Devices Excel',
        'admin.import.targets.error.missing': 'Missing required columns: Name/IP/Username/Remote Path',
        'admin.targets.edit.title': 'Edit Device',
        'admin.targets.edit.keep_pwd': 'Leave empty to keep original password',
        'error.empty_device_info': 'Please fill in device information completely',
        'info.device_updated': 'Device updated',
        'confirm.delete_device': 'Delete this device?',
        'info.device_deleted': 'Device deleted',
        'info.device_added': 'Device added',
        'sync.push_btn': 'Push exam DB to devices',
        'sync.pull_btn': 'Pull scores',
        'sync.sync_btn': 'Sync Data',
        'sync.progress.title': 'Syncing',
        'sync.pushing_message': 'Pushing exam DB to devices, please wait...',
        'sync.pulling_message': 'Pulling scores, please wait...',
        'sync.syncing_message': 'Syncing data, please wait...',
        'sync.status.success': 'Success',
        'sync.status.fail': 'Fail',
        'sync.status.info': 'Info',
        'sync.finished.title': 'Done',
        'sync.operation_done': 'Operation completed:\n{results}',
        'sync.error.title': 'Error',
        'sync.error.message': 'Sync error:\n{error}',
        'scores.group': 'Scores',
        'scores.headers.uuid': 'Attempt UUID',
        'scores.headers.username': 'Username',
        'scores.headers.full_name': 'Full Name',
        'scores.headers.user_id': 'User ID',
        'scores.headers.exam_title': 'Exam',
        'scores.headers.started': 'Started',
        'scores.headers.submitted': 'Submitted',
        'scores.headers.score_total_pass': 'Score/Total/Pass',
        'scores.export_excel': 'Export Scores Excel',
        'scores.not_submitted': 'Not Submitted',
        'export.scores.done': 'Scores exported',
        'info.no_targets': 'No devices configured',
        'progress.group': 'Progress',
        'progress.replace_import': 'Replace Import',
        'progress.export_tpl': 'Export Template',
        'progress.import_tpl': 'Import Template',
        'progress.export_user_btn': 'Export User Progress',
        'progress.headers.task_title': 'Task',
        'progress.headers.description': 'Description',
        'progress.headers.order': 'Order',
        'progress.headers.status': 'Status',
        'progress.headers.updated_at': 'Updated At',
        'progress.headers.updated_by': 'Updated By',
        'progress.status.not_started': 'Not Started',
        'progress.status.in_progress': 'In Progress',
        'progress.status.completed': 'Completed',
        'progress.export_tpl.title': 'Export Progress Template',
        'progress.export_tpl.done': 'Template exported: {path}',
        'progress.import_tpl.title': 'Import Progress Template',
        'progress.import_tpl.replace_confirm': 'Replacing will clear tasks and records of modules with the same name. Continue?',
        'progress.import_tpl.result': 'Modules:{modules} Tasks:{tasks} Skipped sheets:{skipped_sheets}',
        'progress.export_user.title': 'Export User Progress',
        'progress.export_user.done': 'User progress exported: {path}',
        'exam.in_progress': 'Exam In Progress, Total: {total}',
        'exam.prev': 'Previous',
        'exam.next': 'Next',
        'exam.submit': 'Submit',
        'exam.result': 'Result',
        'exam.finished_title': 'Exam Finished Score:{score}/{total} {passed}',
        'exam.pass_text': 'Pass',
        'exam.fail_text': 'Fail',
        'exam.type.single': 'Single Choice',
        'exam.type.multiple': 'Multiple Choice',
        'exam.type.truefalse': 'True/False',
        'exam.true': 'True',
        'exam.false': 'False',
        'exam.already_running': 'An exam is already in progress',
        'exam.score_label': 'Score',
        'exam.confirm_exit': 'Are you sure to exit the exam? Unanswered questions will be scored as 0',
        'exam.exit_result': 'Exited. Score:{score} {pass_text}',
        'exam.unanswered_note': ' (Unanswered scored as 0)',
        'exam.question_title': '{index}/{total} {text} ({type} Score:{score})'
    }
}

def tr(key, **kwargs):
    lang = _current_lang()
    d = _DICT.get(lang) or _DICT['zh-Hans']
    text = d.get(key)
    if text is None:
        return key
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
