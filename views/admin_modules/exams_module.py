import os
import pathlib
import json
import yaml
from PySide6.QtCore import Qt, QDateTime
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout, QLineEdit, QTextEdit, QSpinBox, QDateTimeEdit, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem, QAbstractItemView, QCheckBox
from PySide6.QtWidgets import QMessageBox
from icon_manager import get_icon
from theme_manager import theme_manager
from language import tr
from utils import show_info, show_warn, ask_yes_no
from models import list_exams, add_exam, import_questions_from_json, get_exam_stats, update_exam_title_desc
from openpyxl import load_workbook, Workbook
from openpyxl.styles import PatternFill, Alignment, Font, Border, Side
from openpyxl.utils import get_column_letter


class AdminExamsModule(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout()
        gb1 = QGroupBox(tr('admin.exams_group'))
        vb1 = QVBoxLayout()
        self.exams_table = QTableWidget(0, 9)
        self.exams_table.setHorizontalHeaderLabels([tr('admin.exams.headers.id'), tr('admin.exams.headers.title'), tr('admin.exams.headers.pass_ratio'), tr('admin.exams.headers.time_limit'), tr('admin.exams.headers.deadline'), tr('admin.exams.headers.description'), tr('admin.exams.headers.q_count'), tr('admin.exams.headers.total'), tr('admin.exams.headers.actions')])
        self.exams_table.setColumnWidth(0, 50)
        self.exams_table.setColumnWidth(1, 120)
        self.exams_table.setColumnWidth(2, 120)
        self.exams_table.setColumnWidth(3, 120)
        self.exams_table.setColumnWidth(4, 120)
        self.exams_table.setColumnWidth(5, 480)
        self.exams_table.setColumnWidth(6, 80)
        self.exams_table.setColumnWidth(7, 80)
        self.exams_table.setColumnWidth(8, 150)
        self.exams_table.horizontalHeader().setStretchLastSection(True)
        self.exams_table.setAlternatingRowColors(True)
        self.exams_table.setShowGrid(False)
        self.exams_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.exams_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.refresh_exams()
        vb1.addWidget(self.exams_table)
        self.exams_table.itemChanged.connect(self.on_exam_item_changed)
        gb1.setLayout(vb1)
        gb2 = QGroupBox(tr('admin.new_exam_group'))
        vb2 = QVBoxLayout()
        form = QFormLayout()
        self.ex_title = QLineEdit()
        self.ex_title.setPlaceholderText(tr('admin.exams.form.title'))
        self.ex_desc = QTextEdit()
        self.ex_desc.setPlaceholderText(tr('admin.exams.form.description'))
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
        self.ex_end.setDateTime(QDateTime.currentDateTime())
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
        self.ex_permanent = QCheckBox(tr('admin.exams.permanent_checkbox'))
        colors_perm = theme_manager.get_theme_colors()
        self.ex_permanent.setStyleSheet(
            f"QCheckBox {{ color:{colors_perm['text_primary']}; font-size:14px; }}\n"
            f"QCheckBox::indicator {{ width:40px; height:22px; border-radius:11px; }}\n"
            f"QCheckBox::indicator:unchecked {{ background-color:{colors_perm['border_light']}; border:1px solid {colors_perm['border']}; }}\n"
            f"QCheckBox::indicator:checked {{ background-color:{colors_perm['primary']}; border:1px solid {colors_perm['primary']}; }}"
        )
        def on_perm_changed(state):
            checked = state == Qt.CheckState.Checked
            self.ex_end.setEnabled(not checked)
            self.ex_end.setReadOnly(checked)
            if not checked:
                self.ex_end.setFocus()
        self.ex_permanent.stateChanged.connect(on_perm_changed)
        form.addRow(tr('admin.exams.form.title'), self.ex_title)
        form.addRow(tr('admin.exams.form.description'), self.ex_desc)
        form.addRow(tr('admin.exams.form.pass_ratio'), self.ex_pass)
        form.addRow(tr('admin.exams.form.time_limit'), self.ex_time)
        form.addRow(tr('admin.exams.form.end_date'), self.ex_end)
        form.addRow('', self.ex_permanent)
        add_btn = QPushButton(tr('admin.exams.add_btn'))
        add_btn.setIcon(get_icon('exam_add'))
        add_btn.clicked.connect(self.add_exam)
        import_btn = QPushButton(tr('admin.import_questions'))
        import_btn.setIcon(get_icon('exam_import'))
        import_btn.clicked.connect(self.import_questions)
        export_btn = QPushButton(tr('admin.export_sample'))
        export_btn.setIcon(get_icon('exam_export'))
        export_btn.clicked.connect(self.export_sample)
        vb2.addLayout(form)
        hb = QHBoxLayout()
        hb.addWidget(add_btn)
        hb.addWidget(import_btn)
        hb.addWidget(export_btn)
        vb2.addLayout(hb)
        gb2.setLayout(vb2)
        lay.addWidget(gb1, 3)
        lay.addWidget(gb2, 1)
        self.setLayout(lay)
    def refresh_exams(self):
        tbl = getattr(self, 'exams_table', None)
        if tbl is None:
            return
        tbl.blockSignals(True)
        tbl.setRowCount(0)
        for e in list_exams(include_expired=True):
            r = tbl.rowCount()
            tbl.insertRow(r)
            it_id = QTableWidgetItem(str(e[0]))
            it_id.setFlags(it_id.flags() & ~Qt.ItemFlag.ItemIsEditable)
            tbl.setItem(r, 0, it_id)
            tbl.setItem(r, 1, QTableWidgetItem(e[1] or ''))
            tbl.setItem(r, 2, QTableWidgetItem(f"{int(float(e[3])*100)}%"))
            it_time = QTableWidgetItem(str(e[4]))
            it_time.setFlags(it_time.flags() & ~Qt.ItemFlag.ItemIsEditable)
            tbl.setItem(r, 3, it_time)
            it_end = QTableWidgetItem(e[5] if e[5] else tr('common.permanent'))
            it_end.setFlags(it_end.flags() & ~Qt.ItemFlag.ItemIsEditable)
            tbl.setItem(r, 4, it_end)
            tbl.setItem(r, 5, QTableWidgetItem(e[2] or ''))
            try:
                stats = get_exam_stats(int(e[0]))
            except Exception:
                stats = {'count': 0, 'total_score': 0}
            it_cnt = QTableWidgetItem(str(int(stats['count']) if stats and 'count' in stats else 0))
            it_cnt.setFlags(it_cnt.flags() & ~Qt.ItemFlag.ItemIsEditable)
            tbl.setItem(r, 6, it_cnt)
            it_total = QTableWidgetItem(str(int(stats['total_score']) if stats and 'total_score' in stats else 0))
            it_total.setFlags(it_total.flags() & ~Qt.ItemFlag.ItemIsEditable)
            tbl.setItem(r, 7, it_total)
            opw = QWidget()
            hb = QHBoxLayout()
            hb.setContentsMargins(0,0,0,0)
            btn_clear = QPushButton(tr('common.clear'))
            btn_clear.setIcon(get_icon('delete'))
            btn_del = QPushButton(tr('common.delete'))
            btn_del.setIcon(get_icon('exam_delete'))
            exam_id = e[0]
            btn_clear.clicked.connect(lambda _, x=exam_id: self.clear_exam(x))
            btn_del.clicked.connect(lambda _, x=exam_id: self.delete_exam(x))
            hb.addWidget(btn_clear)
            hb.addWidget(btn_del)
            hb.addStretch()
            opw.setLayout(hb)
            tbl.setCellWidget(r, 8, opw)
        try:
            for r in range(tbl.rowCount()):
                for c in range(tbl.columnCount()):
                    it = tbl.item(r, c)
                    if it:
                        it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        except Exception:
            pass
        tbl.blockSignals(False)
    def on_exam_item_changed(self, item):
        row = item.row()
        col = item.column()
        try:
            exam_id = int(self.exams_table.item(row, 0).text())
        except Exception:
            return
        if col == 1:
            title = item.text().strip()
            if not title:
                show_warn(self, tr('common.error'), '标题不能为空')
                self.refresh_exams()
                return
            update_exam_title_desc(exam_id, title=title)
            self.refresh_exams()
        elif col == 5:
            desc = item.text().strip()
            update_exam_title_desc(exam_id, description=desc)
            self.refresh_exams()
    def add_exam(self):
        title = self.ex_title.text().strip()
        desc = self.ex_desc.toPlainText().strip()
        pass_ratio = self.ex_pass.value() / 100.0
        tl = self.ex_time.value()
        end = None if self.ex_permanent.isChecked() else self.ex_end.dateTime().toString(Qt.DateFormat.ISODate)
        if not title:
            show_warn(self, tr('common.error'), tr('error.title_required'))
            return
        add_exam(title, desc, pass_ratio, tl, end)
        self.refresh_exams()
        show_info(self, tr('common.success'), tr('info.exam_added'))
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
            show_warn(self, tr('common.error'), tr('error.select_exam'))
            return
        suggested = os.path.join(str(pathlib.Path.home()), 'Documents')
        fn, sel = QFileDialog.getOpenFileName(self, tr('admin.import.title'), suggested, 'Excel (*.xlsx);;JSON (*.json);;YAML (*.yaml *.yml)')
        if not fn:
            return
        try:
            ext = os.path.splitext(fn)[1].lower().strip()
            is_zip = False
            try:
                with open(fn, 'rb') as f:
                    head = f.read(4)
                    is_zip = head.startswith(b'PK')
            except Exception:
                is_zip = False
            if (sel and sel.startswith('Excel')) or ext in ('.xlsx', '.xlsm', '.xltx', '.xltm') or is_zip:
                wb = load_workbook(fn)
                rand_count = None
                def parse_sheet(ws):
                    header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
                    header = [str(x).strip() if x else '' for x in header_row]
                    def idx(name):
                        try:
                            return header.index(name)
                        except Exception:
                            return -1
                    itype = idx('类型'); icontent = idx('内容'); icorrect = idx('正确答案'); iscore = idx('分数')
                    start_opts = None
                    for i, h in enumerate(header):
                        if h.startswith('选项'):
                            start_opts = i
                            break
                    base_cols = [x for x in (itype, icontent, icorrect, iscore) if x >= 0]
                    if min(itype, icontent, icorrect) < 0:
                        return []
                    if start_opts is None:
                        start_opts = (max(base_cols) + 1) if base_cols else 3
                    data_local = []
                    for row in ws.iter_rows(min_row=2, values_only=True):
                        tval = (str(row[itype]).strip().lower() if row[itype] is not None else '')
                        qtype = None
                        if tval in ('单选', 'single'):
                            qtype = 'single'
                        elif tval in ('多选', 'multiple'):
                            qtype = 'multiple'
                        elif tval in ('判断', 'truefalse', '判断题'):
                            qtype = 'truefalse'
                        else:
                            continue
                        text = (str(row[icontent]).strip() if row[icontent] is not None else '')
                        if not text:
                            continue
                        correct_cell = (str(row[icorrect]).strip() if row[icorrect] is not None else '')
                        correct = []
                        if qtype == 'truefalse':
                            lc = correct_cell.lower()
                            if lc in ('true', 'false'):
                                correct = [True] if lc == 'true' else [False]
                            else:
                                continue
                        else:
                            parts = [p.strip().upper() for p in correct_cell.replace('，', ',').replace(';', ',').split(',') if p.strip()]
                            correct = parts[:1] if qtype == 'single' else parts
                        options = []
                        if qtype != 'truefalse':
                            letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                            cidx = start_opts
                            key_index = 0
                            while cidx < len(row):
                                val = row[cidx]
                                if val is None or str(val).strip() == '':
                                    break
                                key = letters[key_index] if key_index < len(letters) else str(key_index+1)
                                options.append({'key': key, 'text': str(val).strip()})
                                cidx += 1
                                key_index += 1
                            if not options and qtype != 'truefalse':
                                continue
                        sc = 1.0
                        if iscore >= 0 and iscore < len(row):
                            try:
                                v = row[iscore]
                                if v is not None and str(v).strip() != '':
                                    sc = float(str(v).strip())
                            except Exception:
                                sc = 1.0
                        item = {'type': qtype, 'text': text, 'score': sc, 'options': options, 'correct': correct}
                        data_local.append(item)
                    return data_local
                data_mand = []
                data_rand = []
                if '配置选项' in wb.sheetnames:
                    ws_cfg = wb['配置选项']
                    cfg_header = next(ws_cfg.iter_rows(min_row=1, max_row=1, values_only=True))
                    cfg = {str(cfg_header[i]).strip(): (ws_cfg.cell(row=2, column=i+1).value) for i in range(len(cfg_header)) if cfg_header[i] is not None}
                    if '随机抽取数量' in cfg:
                        try:
                            rand_count = int(str(cfg['随机抽取数量']).strip())
                        except Exception:
                            rand_count = None
                if '必考题库' in wb.sheetnames:
                    data_mand = parse_sheet(wb['必考题库'])
                if '随机题库' in wb.sheetnames:
                    data_rand = parse_sheet(wb['随机题库'])
                if not data_mand and not data_rand:
                    show_warn(self, tr('common.error'), '缺少新格式工作表：请提供“必考题库”或“随机题库”（至少之一），可选“配置选项”设置随机抽取数量')
                    return
                data = {'mandatory': data_mand, 'random': data_rand, 'config': {}}
                if rand_count is not None:
                    data['config']['random_pick_count'] = rand_count
            else:
                def read_text_with_fallback(path):
                    with open(path, 'rb') as f:
                        raw = f.read()
                    try:
                        return raw.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            return raw.decode('gb18030')
                        except UnicodeDecodeError:
                            return None
                text = read_text_with_fallback(fn)
                if text is None:
                    show_warn(self, tr('common.error'), tr('admin.import.error.file_decode'))
                    return
                data = None
                if (sel and sel.startswith('JSON')) or ext == '.json':
                    data = json.loads(text)
                elif (sel and sel.startswith('YAML')) or ext in ('.yaml', '.yml'):
                    data = yaml.safe_load(text)
                else:
                    try:
                        data = json.loads(text)
                    except Exception:
                        try:
                            data_yaml = yaml.safe_load(text)
                            data = data_yaml
                        except Exception:
                            show_warn(self, tr('common.error'), tr('admin.import.error.not_supported'))
                            return
            if data is None:
                show_warn(self, tr('common.error'), tr('admin.import.error.no_data'))
                return
            valid = []
            errs = []
            def validate_list(lst, pool_name):
                base_index = len(valid)
                for idx, q in enumerate(lst, start=1):
                    t = (q.get('type') or '').strip().lower()
                    if t not in ('single','multiple','truefalse'):
                        errs.append(f'{pool_name} 第{idx}题: 类型无效')
                        continue
                    corr = q.get('correct') or []
                    if t in ('single','multiple'):
                        opts = q.get('options') or []
                        keys = {str(o.get('key')).strip().upper() for o in opts if o.get('key')}
                        if not keys:
                            errs.append(f'{pool_name} 第{idx}题: 缺少选项')
                            continue
                        corr = [str(x).strip().upper() for x in corr if str(x).strip() != '']
                        if not corr or not set(corr).issubset(keys):
                            errs.append(f'{pool_name} 第{idx}题: 正确答案不在选项中')
                            continue
                        if t == 'single' and len(corr) != 1:
                            errs.append(f'{pool_name} 第{idx}题: 单选需1个答案')
                            continue
                        q['correct'] = corr
                    else:
                        if not corr or len(corr) != 1 or not isinstance(corr[0], bool):
                            errs.append(f'{pool_name} 第{idx}题: 判断题答案需为true/false')
                            continue
                    valid.append(q)
            if isinstance(data, dict):
                cfg = data.get('config') or {}
                from models import update_exam_random_pick_count
                if 'random_pick_count' in cfg:
                    try:
                        update_exam_random_pick_count(exam_id, int(cfg.get('random_pick_count') or 0))
                    except Exception:
                        pass
                mand = data.get('mandatory') or []
                rand = data.get('random') or []
                if not mand and not rand:
                    show_warn(self, tr('common.error'), tr('admin.import.error.jsonyaml_missing'))
                    return
                for x in mand:
                    x['pool'] = 'mandatory'
                for x in rand:
                    x['pool'] = 'random'
                validate_list(mand, '必考题库')
                validate_list(rand, '随机题库')
            else:
                show_warn(self, tr('common.error'), tr('admin.import.error.jsonyaml_dict'))
                return
            if not valid:
                detail = '\n'.join(errs[:20]) if errs else tr('admin.import.error.no_valid')
                show_warn(self, tr('common.error'), detail)
                return
            import_questions_from_json(exam_id, valid)
            self.refresh_exams()
            cnt_single = sum(1 for d in valid if d.get('type') == 'single')
            cnt_multiple = sum(1 for d in valid if d.get('type') == 'multiple')
            cnt_tf = sum(1 for d in valid if d.get('type') == 'truefalse')
            cnt_mand = sum(1 for d in valid if (d.get('pool') or 'mandatory') == 'mandatory')
            cnt_rand = sum(1 for d in valid if (d.get('pool') or 'mandatory') == 'random')
            extra = ''
            if errs:
                extra = '\n部分题目未导入:\n' + '\n'.join(errs[:10])
            show_info(self, tr('common.success'), tr('admin.import.success', single=cnt_single, multiple=cnt_multiple, truefalse=cnt_tf, mandatory=cnt_mand, random=cnt_rand, extra=(tr('admin.import.extra_prefix') + '\n'.join(errs[:10]) if errs else '')))
        except Exception as e:
            show_warn(self, tr('common.error'), str(e))
    def clear_exam(self, exam_id):
        reply = ask_yes_no(self, tr('common.hint'), tr('admin.exams.clear_confirm'), default_yes=False)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            from models import clear_exam_questions
            clear_exam_questions(exam_id)
            self.refresh_exams()
            show_info(self, tr('common.success'), tr('admin.exams.clear_done'))
        except Exception as e:
            show_warn(self, tr('common.error'), str(e))
    def delete_exam(self, exam_id):
        reply = ask_yes_no(self, tr('common.hint'), tr('admin.exams.delete_confirm'), default_yes=False)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            from models import delete_exam
            delete_exam(exam_id)
            self.refresh_exams()
            show_info(self, tr('common.success'), tr('admin.exams.delete_done'))
        except Exception as e:
            show_warn(self, tr('common.error'), str(e))
    def export_sample(self):
        suggested = os.path.join(str(pathlib.Path.home()), 'Documents/exam')
        fn, sel = QFileDialog.getSaveFileName(self, tr('admin.export.sample.title'), suggested, 'Excel (*.xlsx);;JSON (*.json);;YAML (*.yaml)')
        if not fn:
            return
        try:
            ext = os.path.splitext(fn)[1].lower()
            mand = [
                {"type":"single","text":"Python中获取列表长度的函数是?","options":[{"key":"A","text":"len(list)"},{"key":"B","text":"size(list)"},{"key":"C","text":"count(list)"},{"key":"D","text":"length(list)"}],"correct":["A"],"score":2},
                {"type":"multiple","text":"以下哪些是Linux常见包管理器?","options":[{"key":"A","text":"apt"},{"key":"B","text":"ls"},{"key":"C","text":"yum"},{"key":"D","text":"pacman"}],"correct":["A","C","D"],"score":3},
                {"type":"truefalse","text":"Python中的list是可变对象","correct":[True],"score":1},
                {"type":"single","text":"查看当前工作目录的Linux命令是?","options":[{"key":"A","text":"pwd"},{"key":"B","text":"cd"},{"key":"C","text":"ls"},{"key":"D","text":"echo"}],"correct":["A"],"score":2},
                {"type":"multiple","text":"以下哪些工具可用于创建Python虚拟环境?","options":[{"key":"A","text":"venv"},{"key":"B","text":"virtualenv"},{"key":"C","text":"pip"},{"key":"D","text":"conda"}],"correct":["A","B","D"],"score":3}
            ]
            rand = [
                {"type":"truefalse","text":"Linux中/etc目录通常存放系统配置文件","correct":[True],"score":1},
                {"type":"multiple","text":"以下哪些是Python中的可迭代对象?","options":[{"key":"A","text":"list"},{"key":"B","text":"dict"},{"key":"C","text":"int"},{"key":"D","text":"tuple"}],"correct":["A","B","D"],"score":3},
                {"type":"single","text":"Python字典取值且键不存在时不抛异常的方法是?","options":[{"key":"A","text":"d['k']"},{"key":"B","text":"d.get('k')"},{"key":"C","text":"d.k"},{"key":"D","text":"getattr(d,'k')"}],"correct":["B"],"score":2},
                {"type":"single","text":"Linux查看网络端口占用的命令是?","options":[{"key":"A","text":"ss -tuln"},{"key":"B","text":"ps aux"},{"key":"C","text":"top"},{"key":"D","text":"df -h"}],"correct":["A"],"score":2},
                {"type":"multiple","text":"以下哪些属于Python打包/分发相关工具?","options":[{"key":"A","text":"setuptools"},{"key":"B","text":"wheel"},{"key":"C","text":"pip"},{"key":"D","text":"twine"}],"correct":["A","B","D"],"score":3}
            ]
            if (sel and sel.startswith('Excel')) or ext == '.xlsx' or ext == '':
                out = fn if ext == '.xlsx' else fn + '.xlsx'
                wb = Workbook()
                ws_cfg = wb.active
                ws_cfg.title = '配置选项'
                ws_cfg.append(['随机抽取数量'])
                ws_cfg.append([4])
                def write_sheet(ws, rows):
                    ws.append(['类型', '内容', '正确答案', '分数', '选项A', '选项B', '选项C', '选项D'])
                    for item in rows:
                        if item['type'] == 'truefalse':
                            ws.append(['判断', item['text'], 'true' if item['correct'][0] else 'false', item['score']])
                        elif item['type'] == 'single':
                            ws.append(['单选', item['text'], ','.join(item['correct']), item['score']] + [opt['text'] for opt in item.get('options', [])])
                        else:
                            ws.append(['多选', item['text'], ','.join(item['correct']), item['score']] + [opt['text'] for opt in item.get('options', [])])
                ws_m = wb.create_sheet('必考题库')
                write_sheet(ws_m, mand)
                ws_r = wb.create_sheet('随机题库')
                write_sheet(ws_r, rand)
                header_fill = PatternFill(start_color='FF409EFF', end_color='FF409EFF', fill_type='solid')
                header_font = Font(bold=True, color='FFFFFFFF', size=13)
                data_font = Font(size=12)
                center = Alignment(horizontal='center', vertical='center')
                left = Alignment(horizontal='left', vertical='center')
                thin = Side(style='thin', color='FFDDDDDD')
                border = Border(left=thin, right=thin, top=thin, bottom=thin)
                for ws in [ws_m, ws_r]:
                    headers = ['类型', '内容', '正确答案', '分数', '选项A', '选项B', '选项C', '选项D']
                    for c in range(1, len(headers)+1):
                        cell = ws.cell(row=1, column=c)
                        cell.fill = header_fill
                        cell.font = header_font
                        cell.alignment = center
                    ws.row_dimensions[1].height = 26
                    for r in range(2, ws.max_row+1):
                        for c in range(1, len(headers)+1):
                            cell = ws.cell(row=r, column=c)
                            cell.border = border
                            cell.font = data_font
                        ws.cell(row=r, column=4).alignment = center
                        for c in (1,2,3,5,6,7,8):
                            ws.cell(row=r, column=c).alignment = left
                        ws.row_dimensions[r].height = 22
                    widths = [0] * len(headers)
                    for r in ws.iter_rows(values_only=True):
                        for idx, val in enumerate(r):
                            l = len(str(val)) if val is not None else 0
                            widths[idx] = max(widths[idx], l)
                    for i, w in enumerate(widths, start=1):
                        letter = get_column_letter(i)
                        ws.column_dimensions[letter].width = max(16, min(48, w + 6))
                    ws.freeze_panes = 'A2'
                    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{ws.max_row}"
                wb.save(out)
            elif (sel and sel.startswith('JSON')) or ext == '.json':
                out = fn if ext == '.json' else fn + '.json'
                payload = {"config": {"random_pick_count": 4}, "mandatory": mand, "random": rand}
                with open(out, 'w', encoding='utf-8') as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
            elif (sel and sel.startswith('YAML')) or ext in ('.yaml', '.yml'):
                out = fn if ext in ('.yaml', '.yml') else fn + '.yaml'
                lines = []
                lines.append('config:')
                lines.append('  random_pick_count: 4')
                def write_yaml_block(name, rows):
                    lines.append(f'{name}:')
                    for item in rows:
                        lines.append('  -')
                        lines.append(f'    type: {item["type"]}')
                        lines.append(f'    text: "{item["text"]}"')
                        lines.append(f'    score: {item["score"]}')
                        if item.get('options'):
                            lines.append('    options:')
                            for opt in item['options']:
                                lines.append('      - key: ' + opt['key'])
                                lines.append(f'        text: "{opt["text"]}"')
                        if item.get('correct') is not None:
                            lines.append('    correct:')
                            for v in item['correct']:
                                if isinstance(v, bool):
                                    lines.append('      - ' + ('true' if v else 'false'))
                                else:
                                    lines.append('      - ' + str(v))
                write_yaml_block('mandatory', mand)
                write_yaml_block('random', rand)
                with open(out, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines) + '\n')
            show_info(self, tr('common.success'), tr('admin.export.sample.done'))
        except Exception as e:
            show_warn(self, tr('common.error'), str(e))
