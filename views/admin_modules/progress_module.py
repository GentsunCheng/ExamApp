import os
import pathlib

from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill, Alignment, Font, Border, Side
from openpyxl.utils import get_column_letter

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QComboBox, QPushButton, QFileDialog, QScrollArea, QTableWidget, QTableWidgetItem, QCheckBox, QMessageBox

from icon_manager import get_icon
from theme_manager import theme_manager
from utils import show_info, show_warn, ask_yes_no
from language import tr

from models import (
    list_users,
    PROGRESS_STATUS_NOT_STARTED,
    PROGRESS_STATUS_IN_PROGRESS,
    PROGRESS_STATUS_COMPLETED,
    upsert_progress_module,
    upsert_progress_task,
    list_progress_modules,
    list_progress_tasks,
    delete_progress_module,
    get_user_progress_tree,
    set_user_task_progress,
)


_RESERVED_SHEET_NAMES = {'说明', '_meta', 'meta'}


def export_progress_template(file_path):
    out = _ensure_xlsx(file_path)
    wb = Workbook()
    ws = wb.active
    ws.title = '说明'
    ws.append(['字段', '说明', '示例'])
    ws.append(['任务名', '必填；模块内唯一', '观看第一章视频'])
    ws.append(['描述', '可选', '时长约 20 分钟'])
    ws.append(['顺序', '可选；整数；用于排序', '1'])
    _apply_table_style(ws, header_fill_color='FF409EFF')
    ws.freeze_panes = 'A2'

    sample = wb.create_sheet('示例模块')
    sample.append(['任务名', '描述', '顺序'])
    sample.append(['任务1', '示例描述1', 1])
    sample.append(['任务2', '示例描述2', 2])
    _apply_table_style(sample, header_fill_color='FF409EFF')
    sample.freeze_panes = 'A2'

    wb.save(out)
    return out


def export_progress_modules_to_excel(file_path):
    out = _ensure_xlsx(file_path)
    wb = Workbook()
    default = wb.active
    wb.remove(default)
    modules = list_progress_modules()
    tasks = list_progress_tasks(None)
    tasks_by_module = {}
    for t in tasks:
        tasks_by_module.setdefault(int(t[1]), []).append(t)
    for m in modules:
        mid = int(m[0])
        name = m[1] or ''
        ws = wb.create_sheet(_safe_sheet_name(name) or f'Module_{mid}')
        ws.append(['任务名', '描述', '顺序'])
        rows = tasks_by_module.get(mid, [])
        for t in rows:
            ws.append([t[2] or '', t[3] or '', int(t[4] or 0)])
        _apply_table_style(ws, header_fill_color='FF409EFF')
        ws.freeze_panes = 'A2'
    if not wb.sheetnames:
        ws = wb.create_sheet('Tasks')
        ws.append(['任务名', '描述', '顺序'])
        _apply_table_style(ws, header_fill_color='FF409EFF')
        ws.freeze_panes = 'A2'
    wb.save(out)
    return out


def import_progress_from_excel(file_path, replace=False):
    wb = load_workbook(file_path)
    summary = {'modules': 0, 'tasks': 0, 'skipped_sheets': 0}
    for ws in wb.worksheets:
        sheet_name = (ws.title or '').strip()
        if not sheet_name or sheet_name in _RESERVED_SHEET_NAMES:
            summary['skipped_sheets'] += 1
            continue
        header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), None)
        header = [str(x).strip() if x is not None else '' for x in (header_row or [])]
        col_title = _find_header_index(header, {'任务名', '任务名称', 'title', '任务'})
        if col_title is None:
            raise Exception(f'工作表 {sheet_name} 缺少列: 任务名')
        col_desc = _find_header_index(header, {'描述', '任务描述', 'desc', 'description'})
        col_order = _find_header_index(header, {'顺序', '排序', 'order', 'sort'})

        if replace:
            try:
                module_id = upsert_progress_module(sheet_name)
                delete_progress_module(module_id)
            except Exception:
                pass
        module_id = upsert_progress_module(sheet_name)
        summary['modules'] += 1
        for r in ws.iter_rows(min_row=2, values_only=True):
            title = _cell_str(r, col_title)
            if not title:
                continue
            desc = _cell_str(r, col_desc) if col_desc is not None else None
            order_val = _cell_int(r, col_order) if col_order is not None else 0
            upsert_progress_task(module_id, title, desc, order_val)
            summary['tasks'] += 1
    return summary


def export_user_progress_to_excel(user_id, file_path):
    out = _ensure_xlsx(file_path)
    tree = get_user_progress_tree(user_id)
    wb = Workbook()
    default = wb.active
    wb.remove(default)
    for md in tree:
        module_name = md.get('module_name') or ''
        ws = wb.create_sheet(_safe_sheet_name(module_name) or 'Progress')
        ws.append(['任务名', '描述', '顺序', '状态', '更新时间', '更新人'])
        for t in md.get('tasks') or []:
            status = int(t.get('status') or 0)
            ws.append([
                t.get('title') or '',
                t.get('description') or '',
                int(t.get('sort_order') or 0),
                _status_text(status),
                t.get('updated_at'),
                t.get('updated_by'),
            ])
        _apply_table_style(ws, header_fill_color='FF409EFF')
        _apply_status_color(ws, status_col=4)
        ws.freeze_panes = 'A2'
    if not wb.sheetnames:
        ws = wb.create_sheet('Progress')
        ws.append(['任务名', '描述', '顺序', '状态', '更新时间', '更新人'])
        _apply_table_style(ws, header_fill_color='FF409EFF')
        ws.freeze_panes = 'A2'
    wb.save(out)
    return out


class AdminProgressModule(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout()

        header = QGroupBox('学习进度')
        hb = QHBoxLayout()

        self.user_select = QComboBox()
        self.user_select.setMinimumWidth(260)
        self.user_select.currentIndexChanged.connect(self.refresh_progress_view)
        hb.addWidget(self.user_select)

        self.replace_import = QCheckBox('覆盖导入')
        hb.addWidget(self.replace_import)

        btn_export_tpl = QPushButton('导出模板')
        btn_export_tpl.setIcon(get_icon('exam_export'))
        btn_export_tpl.clicked.connect(self.export_template)
        hb.addWidget(btn_export_tpl)

        btn_import = QPushButton('导入模板')
        btn_import.setIcon(get_icon('exam_import'))
        btn_import.clicked.connect(self.import_template)
        hb.addWidget(btn_import)

        btn_export_user = QPushButton('导出用户进度')
        btn_export_user.setIcon(get_icon('exam_export'))
        btn_export_user.clicked.connect(self.export_user_progress)
        hb.addWidget(btn_export_user)

        btn_refresh = QPushButton('刷新')
        btn_refresh.setIcon(get_icon('confirm'))
        btn_refresh.clicked.connect(self.refresh_users_and_view)
        hb.addWidget(btn_refresh)

        hb.addStretch()
        header.setLayout(hb)
        lay.addWidget(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout()
        self.content_widget.setLayout(self.content_layout)
        self.scroll.setWidget(self.content_widget)
        lay.addWidget(self.scroll)

        lay.addStretch()
        self.setLayout(lay)

        self.refresh_users_and_view()

    def refresh_users_and_view(self):
        current_id = self.get_selected_user_id()
        self.user_select.blockSignals(True)
        self.user_select.clear()
        users = list_users()
        for u in users:
            label = u[1] if not u[2] else f'{u[1]} ({u[2]})'
            self.user_select.addItem(label, int(u[0]))
        self.user_select.blockSignals(False)
        if current_id is not None:
            idx = self.user_select.findData(int(current_id))
            if idx >= 0:
                self.user_select.setCurrentIndex(idx)
        self.refresh_progress_view()

    def get_selected_user_id(self):
        try:
            v = self.user_select.currentData()
            return int(v) if v is not None else None
        except Exception:
            return None

    def export_template(self):
        suggested = os.path.join(str(pathlib.Path.home()), 'Documents/progress_template')
        fn, sel = QFileDialog.getSaveFileName(self, '导出学习进度模板', suggested, 'Excel (*.xlsx)')
        if not fn:
            return
        try:
            out = export_progress_template(fn)
            show_info(self, tr('common.success'), f'已导出: {out}')
        except Exception as e:
            show_warn(self, tr('common.error'), str(e))

    def import_template(self):
        suggested = os.path.join(str(pathlib.Path.home()), 'Documents')
        fn, sel = QFileDialog.getOpenFileName(self, '导入学习进度模板', suggested, 'Excel (*.xlsx)')
        if not fn:
            return
        replace = bool(self.replace_import.isChecked())
        if replace:
            reply = ask_yes_no(self, tr('common.hint'), '覆盖导入将清空同名模块下的任务与进度记录，是否继续？', default_yes=False)
            if reply != QMessageBox.StandardButton.Yes:
                return
        try:
            summary = import_progress_from_excel(fn, replace=replace)
            self.refresh_progress_view()
            show_info(self, tr('common.success'), f'导入模块:{summary["modules"]} 任务:{summary["tasks"]} 跳过表:{summary["skipped_sheets"]}')
        except Exception as e:
            show_warn(self, tr('common.error'), str(e))

    def export_user_progress(self):
        user_id = self.get_selected_user_id()
        if user_id is None:
            show_warn(self, tr('common.error'), '请选择用户')
            return
        suggested = os.path.join(str(pathlib.Path.home()), 'Documents/user_progress')
        fn, sel = QFileDialog.getSaveFileName(self, '导出用户学习进度', suggested, 'Excel (*.xlsx)')
        if not fn:
            return
        try:
            out = export_user_progress_to_excel(user_id, fn)
            show_info(self, tr('common.success'), f'已导出: {out}')
        except Exception as e:
            show_warn(self, tr('common.error'), str(e))

    def refresh_progress_view(self):
        self._clear_layout(self.content_layout)
        user_id = self.get_selected_user_id()
        if user_id is None:
            return
        tree = get_user_progress_tree(user_id)
        for md in tree:
            gb = QGroupBox(md.get('module_name') or '')
            vb = QVBoxLayout()
            tbl = QTableWidget(0, 4)
            tbl.setHorizontalHeaderLabels(['任务名', '描述', '顺序', '状态'])
            tbl.setColumnWidth(0, 240)
            tbl.setColumnWidth(1, 520)
            tbl.setColumnWidth(2, 80)
            tbl.setColumnWidth(3, 120)
            tbl.horizontalHeader().setStretchLastSection(True)
            tbl.setAlternatingRowColors(True)
            tbl.setShowGrid(False)
            tasks = md.get('tasks') or []
            tbl.setRowCount(len(tasks))
            for r, t in enumerate(tasks):
                it_title = QTableWidgetItem(t.get('title') or '')
                it_title.setData(Qt.ItemDataRole.UserRole, int(t.get('task_id') or 0))
                tbl.setItem(r, 0, it_title)
                tbl.setItem(r, 1, QTableWidgetItem(t.get('description') or ''))
                it_order = QTableWidgetItem(str(int(t.get('sort_order') or 0)))
                it_order.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                it_order.setFlags(it_order.flags() & ~Qt.ItemFlag.ItemIsEditable)
                tbl.setItem(r, 2, it_order)

                cb = QComboBox()
                cb.addItem('未开始', PROGRESS_STATUS_NOT_STARTED)
                cb.addItem('进行中', PROGRESS_STATUS_IN_PROGRESS)
                cb.addItem('已完成', PROGRESS_STATUS_COMPLETED)
                cb.setProperty('task_id', int(t.get('task_id') or 0))
                cb.setProperty('user_id', int(user_id))
                status = int(t.get('status') or 0)
                idx = cb.findData(status)
                cb.blockSignals(True)
                cb.setCurrentIndex(idx if idx >= 0 else 0)
                cb.blockSignals(False)
                self._apply_status_style(cb, status)
                cb.currentIndexChanged.connect(self.on_status_changed)
                tbl.setCellWidget(r, 3, cb)
            vb.addWidget(tbl)
            gb.setLayout(vb)
            self.content_layout.addWidget(gb)
        self.content_layout.addStretch()

    def on_status_changed(self, _index):
        cb = self.sender()
        if cb is None:
            return
        try:
            user_id = int(cb.property('user_id'))
            task_id = int(cb.property('task_id'))
            status = int(cb.currentData())
        except Exception:
            return
        try:
            set_user_task_progress(user_id, task_id, status, updated_by='admin')
            self._apply_status_style(cb, status)
        except Exception as e:
            show_warn(self, tr('common.error'), str(e))

    def _apply_status_style(self, widget, status):
        colors = theme_manager.get_theme_colors()
        if int(status) == PROGRESS_STATUS_COMPLETED:
            bg = '#67c23a'
            fg = '#ffffff'
        elif int(status) == PROGRESS_STATUS_IN_PROGRESS:
            bg = colors.get('primary') or '#409eff'
            fg = '#ffffff'
        else:
            bg = '#909399'
            fg = '#ffffff'
        widget.setStyleSheet(f"QComboBox {{ background-color:{bg}; color:{fg}; padding:4px 10px; border-radius:10px; }}")

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
                continue
            child_layout = item.layout()
            if child_layout is not None:
                self._clear_layout(child_layout)


def _status_text(status):
    if int(status) == PROGRESS_STATUS_COMPLETED:
        return '已完成'
    if int(status) == PROGRESS_STATUS_IN_PROGRESS:
        return '进行中'
    return '未开始'


def _status_fill(status):
    if int(status) == PROGRESS_STATUS_COMPLETED:
        return PatternFill(start_color='FF67C23A', end_color='FF67C23A', fill_type='solid')
    if int(status) == PROGRESS_STATUS_IN_PROGRESS:
        return PatternFill(start_color='FF409EFF', end_color='FF409EFF', fill_type='solid')
    return PatternFill(start_color='FF909399', end_color='FF909399', fill_type='solid')


def _apply_status_color(ws, status_col):
    if ws.max_row < 2:
        return
    for r in range(2, ws.max_row + 1):
        cell = ws.cell(row=r, column=status_col)
        raw = str(cell.value).strip() if cell.value is not None else ''
        if raw == '已完成':
            fill = _status_fill(PROGRESS_STATUS_COMPLETED)
        elif raw == '进行中':
            fill = _status_fill(PROGRESS_STATUS_IN_PROGRESS)
        else:
            fill = _status_fill(PROGRESS_STATUS_NOT_STARTED)
        cell.fill = fill
        cell.font = Font(color='FFFFFFFF')
        cell.alignment = Alignment(horizontal='center', vertical='center')


def _apply_table_style(ws, header_fill_color='FF409EFF'):
    header_fill = PatternFill(start_color=header_fill_color, end_color=header_fill_color, fill_type='solid')
    header_font = Font(bold=True, color='FFFFFFFF', size=13)
    data_font = Font(size=12)
    center = Alignment(horizontal='center', vertical='center', wrap_text=True)
    left = Alignment(horizontal='left', vertical='center', wrap_text=True)
    thin = Side(style='thin', color='FFDDDDDD')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    for c in range(1, ws.max_column + 1):
        cell = ws.cell(row=1, column=c)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center
        cell.border = border
    ws.row_dimensions[1].height = 26
    for r in range(2, ws.max_row + 1):
        ws.row_dimensions[r].height = 22
        for c in range(1, ws.max_column + 1):
            cell = ws.cell(row=r, column=c)
            cell.border = border
            cell.font = data_font
            if c == 1:
                cell.alignment = left
            else:
                cell.alignment = center
    widths = [0] * ws.max_column
    for row in ws.iter_rows(values_only=True):
        for idx, val in enumerate(row):
            l = len(str(val)) if val is not None else 0
            widths[idx] = max(widths[idx], l)
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = max(16, min(64, w + 6))


def _ensure_xlsx(path):
    ext = os.path.splitext(path)[1].lower().strip()
    return path if ext == '.xlsx' else path + '.xlsx'


def _safe_sheet_name(name):
    n = str(name).strip()
    if not n:
        return ''
    bad = ['\\', '/', '*', '[', ']', ':', '?']
    for ch in bad:
        n = n.replace(ch, ' ')
    n = n.strip()
    if len(n) > 31:
        n = n[:31]
    return n


def _find_header_index(header, candidates):
    for idx, h in enumerate(header):
        if not h:
            continue
        if str(h).strip() in candidates:
            return idx
    return None


def _cell_str(row, idx):
    if idx is None or idx >= len(row):
        return None
    v = row[idx]
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def _cell_int(row, idx):
    if idx is None or idx >= len(row):
        return 0
    v = row[idx]
    if v is None or str(v).strip() == '':
        return 0
    try:
        return int(v)
    except Exception:
        try:
            return int(float(v))
        except Exception:
            return 0
