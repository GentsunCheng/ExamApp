import os
import pathlib
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout, QLineEdit,
    QPushButton, QComboBox, QSpinBox, QDoubleSpinBox, QFileDialog,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QLabel, QSplitter,
    QHeaderView, QWidget
)
from icon_manager import IconManager
from theme_manager import theme_manager
from language import tr
from utils import show_info, show_warn
from models import add_question
from ai_generator import (
    PROVIDER_OPENAI, PROVIDER_ANTHROPIC, DEFAULT_BASE_URLS, MAX_FILES,
    load_ai_config, save_ai_config, create_provider, prepare_file,
    generate_questions,
)


class ModelListThread(QThread):
    ok = Signal(list)
    failed = Signal(str)

    def __init__(self, provider, parent=None):
        super().__init__(parent)
        self.provider = provider

    def run(self):
        try:
            models = self.provider.list_models()
            self.ok.emit(models)
        except Exception as e:
            self.failed.emit(str(e))


class GenerateThread(QThread):
    ok = Signal(list, object)
    failed = Signal(str)
    retrying = Signal(str)

    def __init__(self, provider, model, counts, score, files, parent=None):
        super().__init__(parent)
        self.provider = provider
        self.model = model
        self.counts = counts
        self.score = score
        self.files = files

    def run(self):
        try:
            questions, err = generate_questions(
                self.provider, self.model, self.counts, self.score, self.files,
                on_retry=lambda reason: self.retrying.emit(reason),
            )
            if questions:
                self.ok.emit(questions, err)
            else:
                self.failed.emit(err or tr('ai.error.unknown'))
        except Exception as e:
            self.failed.emit(str(e))


class AIGenerateWindow(QDialog):
    TYPE_LABEL_KEYS = {
        'single': 'ai.count.single',
        'multiple': 'ai.count.multiple',
        'truefalse': 'ai.count.truefalse',
        'fill': 'ai.count.fill',
        'essay': 'ai.count.essay',
    }

    def __init__(self, exam_id, exam_uuid, exam_title, parent=None):
        super().__init__(parent)
        self.exam_id = exam_id
        self.exam_uuid = exam_uuid
        self.exam_title = exam_title
        self.icon_manager = IconManager()
        self.files = []          # prepare_file 结果列表
        self.generated = []      # 当前预览的题目
        self._model_thread = None
        self._gen_thread = None
        self.setWindowTitle(f"{tr('ai.window_title')} - {exam_title}")
        self.resize(1080, 720)
        self._build_ui()
        self._load_config()

    # ---------- UI ----------
    def _build_ui(self):
        colors = theme_manager.get_theme_colors()
        self.setStyleSheet(self._qss(colors))
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ===== 左栏：出题 =====
        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(10)

        # 资料文件
        file_group = QGroupBox(tr('ai.files_group'))
        f_lay = QVBoxLayout(file_group)
        f_lay.setContentsMargins(6, 8, 6, 6)
        f_lay.setSpacing(6)
        self.file_table = QTableWidget(0, 3)
        self.file_table.setHorizontalHeaderLabels([tr('ai.files.name'), tr('ai.files.size'), tr('ai.files.op')])
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.verticalHeader().setVisible(False)
        self.file_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.file_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.file_table.setMinimumHeight(110)
        f_lay.addWidget(self.file_table)
        add_file_btn = QPushButton(tr('ai.files.add'))
        add_file_btn.setIcon(self.icon_manager.get_icon('file'))
        add_file_btn.clicked.connect(self.on_add_files)
        f_btn_row = QHBoxLayout()
        f_btn_row.addWidget(add_file_btn)
        f_btn_row.addStretch()
        f_lay.addLayout(f_btn_row)
        left_lay.addWidget(file_group)

        # 题目配置
        cfg_group = QGroupBox(tr('ai.config_group'))
        c_lay = QFormLayout(cfg_group)
        c_lay.setContentsMargins(6, 8, 6, 6)
        c_lay.setSpacing(8)
        self.count_spins = {}
        row1 = QHBoxLayout()
        for t in ('single', 'multiple', 'truefalse'):
            lab = QLabel(tr(self.TYPE_LABEL_KEYS[t]))
            spin = QSpinBox()
            spin.setRange(0, 50)
            self.count_spins[t] = spin
            row1.addWidget(lab)
            row1.addWidget(spin)
        row1.addStretch()
        row2 = QHBoxLayout()
        for t in ('fill', 'essay'):
            lab = QLabel(tr(self.TYPE_LABEL_KEYS[t]))
            spin = QSpinBox()
            spin.setRange(0, 50)
            self.count_spins[t] = spin
            row2.addWidget(lab)
            row2.addWidget(spin)
        row2.addStretch()
        w1 = QWidget()
        w1.setLayout(row1)
        w2 = QWidget()
        w2.setLayout(row2)
        c_lay.addRow(w1)
        c_lay.addRow(w2)
        self.score_spin = QDoubleSpinBox()
        self.score_spin.setRange(0.5, 100.0)
        self.score_spin.setSingleStep(0.5)
        self.score_spin.setValue(2.0)
        self.pool_combo = QComboBox()
        self.pool_combo.addItem(tr('ai.pool.mandatory'), 'mandatory')
        self.pool_combo.addItem(tr('ai.pool.random'), 'random')
        c_lay.addRow(tr('ai.score_label'), self.score_spin)
        c_lay.addRow(tr('ai.pool_label'), self.pool_combo)
        left_lay.addWidget(cfg_group)

        # 生成按钮与状态
        gen_row = QHBoxLayout()
        self.gen_btn = QPushButton(tr('ai.generate_btn'))
        self.gen_btn.setObjectName('btn-primary')
        self.gen_btn.setIcon(self.icon_manager.get_icon('play'))
        self.gen_btn.clicked.connect(self.on_generate)
        self.status_label = QLabel('')
        self.status_label.setStyleSheet(f"color:{colors['text_secondary']}; font-size:13px;")
        gen_row.addWidget(self.gen_btn)
        gen_row.addWidget(self.status_label, 1)
        left_lay.addLayout(gen_row)

        # 预览表格
        prev_group = QGroupBox(tr('ai.preview_group'))
        p_lay = QVBoxLayout(prev_group)
        p_lay.setContentsMargins(6, 8, 6, 6)
        p_lay.setSpacing(6)
        self.preview_table = QTableWidget(0, 6)
        self.preview_table.setHorizontalHeaderLabels([
            tr('ai.preview.check'), tr('ai.preview.no'), tr('ai.preview.type'),
            tr('ai.preview.text'), tr('ai.preview.answer'), tr('ai.preview.score'),
        ])
        hh = self.preview_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.verticalHeader().setVisible(False)
        self.preview_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.preview_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        p_lay.addWidget(self.preview_table)
        import_row = QHBoxLayout()
        self.import_btn = QPushButton(tr('ai.import_btn'))
        self.import_btn.setObjectName('btn-success')
        self.import_btn.setIcon(self.icon_manager.get_icon('exam_import'))
        self.import_btn.setEnabled(False)
        self.import_btn.clicked.connect(self.on_import)
        import_row.addWidget(self.import_btn)
        import_row.addStretch()
        p_lay.addLayout(import_row)
        left_lay.addWidget(prev_group, 1)

        # ===== 右栏：设置 =====
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(10)
        set_group = QGroupBox(tr('ai.settings_group'))
        s_form = QFormLayout(set_group)
        s_form.setContentsMargins(6, 8, 6, 6)
        s_form.setSpacing(10)

        self.provider_combo = QComboBox()
        self.provider_combo.addItem('OpenAI (兼容接口)', PROVIDER_OPENAI)
        self.provider_combo.addItem('Anthropic (Claude)', PROVIDER_ANTHROPIC)
        self.provider_combo.currentIndexChanged.connect(self.on_provider_changed)

        self.base_url_edit = QLineEdit()
        self.base_url_edit.setPlaceholderText('https://api.openai.com/v1')

        key_row = QHBoxLayout()
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.eye_btn = QPushButton()
        self.eye_btn.setIcon(self.icon_manager.get_icon('search'))
        self.eye_btn.setFixedWidth(34)
        self.eye_btn.setCheckable(True)
        self.eye_btn.toggled.connect(self.on_eye_toggled)
        key_row.addWidget(self.api_key_edit, 1)
        key_row.addWidget(self.eye_btn)

        model_row = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.refresh_btn = QPushButton()
        self.refresh_btn.setIcon(self.icon_manager.get_icon('refresh'))
        self.refresh_btn.setFixedWidth(34)
        self.refresh_btn.setToolTip(tr('ai.refresh_models'))
        self.refresh_btn.clicked.connect(self.on_refresh_models)
        model_row.addWidget(self.model_combo, 1)
        model_row.addWidget(self.refresh_btn)

        s_form.addRow(tr('ai.provider_label'), self.provider_combo)
        s_form.addRow(tr('ai.base_url_label'), self.base_url_edit)
        s_form.addRow(tr('ai.api_key_label'), key_row)
        s_form.addRow(tr('ai.model_label'), model_row)

        self.save_cfg_btn = QPushButton(tr('ai.save_settings'))
        self.save_cfg_btn.setObjectName('btn-primary')
        self.save_cfg_btn.setIcon(self.icon_manager.get_icon('save'))
        self.save_cfg_btn.clicked.connect(self.on_save_config)
        s_form.addRow('', self.save_cfg_btn)

        right_lay.addWidget(set_group)
        right_lay.addStretch()

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([720, 360])
        root.addWidget(splitter, 1)

    def _qss(self, c):
        return (
            f"QDialog {{ background:{c['background']}; font-family:\"PingFang SC\",sans-serif; }}\n"
            f"QGroupBox {{ font-weight:bold; border:1px solid {c['border']}; border-radius:8px; margin-top:8px; padding-top:8px; }}\n"
            f"QGroupBox::title {{ subcontrol-origin: margin; left:10px; padding:0 4px; }}\n"
            f"QPushButton {{ background:{c['button_primary']}; color:{c['text_inverse']}; padding:6px 12px; border:none; border-radius:8px; }}\n"
            f"QPushButton:hover {{ background:{c['button_primary_hover']}; }}\n"
            f"QPushButton:disabled {{ background:{c['border_light']}; color:{c['text_secondary']}; }}\n"
            f"QPushButton#btn-primary {{ background:{c['primary']}; color:{c['text_inverse']}; }}\n"
            f"QPushButton#btn-primary:hover {{ background:{c['button_primary_hover']}; }}\n"
            f"QPushButton#btn-success {{ background:{c['success']}; color:{c['text_inverse']}; }}\n"
            f"QPushButton#btn-success:hover {{ background:#85ce61; }}\n"
            f"QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{ padding:6px; border:1px solid {c['input_border']}; border-radius:8px; background:{c['input_background']}; color:{c['text_primary']}; }}\n"
            f"QLineEdit:focus, QComboBox:focus {{ border-color:{c['primary']}; }}\n"
            f"QComboBox::drop-down {{ width:24px; border:none; }}\n"
            f"QComboBox QAbstractItemView {{ background:{c['card_background']}; border:1px solid {c['border']}; selection-background-color:{c['primary']}; }}\n"
            f"QTableWidget {{ border:1px solid {c['border']}; border-radius:8px; background:{c['card_background']}; color:{c['text_primary']}; }}\n"
            f"QTableWidget::item:hover {{ background:{c['border_light']}; }}\n"
            f"QTableWidget::item:selected {{ background:{c['primary']}; color:{c['text_inverse']}; }}\n"
            f"QHeaderView::section {{ background:{c['border_light']}; color:{c['text_secondary']}; font-weight:600; padding:6px 8px; border:none; }}\n"
            f"QLabel {{ color:{c['text_primary']}; }}\n"
            f"QSplitter::handle {{ background:{c['border']}; width:2px; }}"
        )

    # ---------- 配置 ----------
    def _current_provider(self):
        return self.provider_combo.currentData()

    def _load_config(self):
        cfg = load_ai_config()
        idx = self.provider_combo.findData(cfg['provider'])
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)
        if cfg['provider'] == PROVIDER_ANTHROPIC:
            self.base_url_edit.setText(cfg['base_url_anthropic'])
            self.api_key_edit.setText(cfg['api_key_anthropic'])
        else:
            self.base_url_edit.setText(cfg['base_url_openai'])
            self.api_key_edit.setText(cfg['api_key_openai'])
        if cfg['model']:
            self.model_combo.setEditText(cfg['model'])

    def _collect_config(self):
        provider = self._current_provider()
        cfg = load_ai_config()
        cfg['provider'] = provider
        if provider == PROVIDER_ANTHROPIC:
            cfg['base_url_anthropic'] = self.base_url_edit.text().strip() or DEFAULT_BASE_URLS[PROVIDER_ANTHROPIC]
            cfg['api_key_anthropic'] = self.api_key_edit.text().strip()
        else:
            cfg['base_url_openai'] = self.base_url_edit.text().strip() or DEFAULT_BASE_URLS[PROVIDER_OPENAI]
            cfg['api_key_openai'] = self.api_key_edit.text().strip()
        cfg['model'] = self.model_combo.currentText().strip()
        return cfg

    def on_provider_changed(self, _idx):
        provider = self._current_provider()
        cfg = load_ai_config()
        if provider == PROVIDER_ANTHROPIC:
            self.base_url_edit.setText(cfg['base_url_anthropic'] or DEFAULT_BASE_URLS[PROVIDER_ANTHROPIC])
            self.api_key_edit.setText(cfg['api_key_anthropic'])
        else:
            self.base_url_edit.setText(cfg['base_url_openai'] or DEFAULT_BASE_URLS[PROVIDER_OPENAI])
            self.api_key_edit.setText(cfg['api_key_openai'])
        self.model_combo.clear()

    def on_eye_toggled(self, checked):
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password)

    def on_save_config(self):
        save_ai_config(self._collect_config())
        show_info(self, tr('common.success'), tr('ai.settings_saved'))

    # ---------- 模型刷新 ----------
    def on_refresh_models(self):
        provider_name = self._current_provider()
        base_url = self.base_url_edit.text().strip() or DEFAULT_BASE_URLS[provider_name]
        api_key = self.api_key_edit.text().strip()
        if not api_key:
            show_warn(self, tr('common.error'), tr('ai.error.no_api_key'))
            return
        provider = create_provider(provider_name, base_url, api_key)
        self.refresh_btn.setEnabled(False)
        self.status_label.setText(tr('ai.status.fetching_models'))
        self._model_thread = ModelListThread(provider, self)
        self._model_thread.ok.connect(self._on_models_ok)
        self._model_thread.failed.connect(self._on_models_failed)
        self._model_thread.start()

    def _on_models_ok(self, models):
        self.refresh_btn.setEnabled(True)
        provider_name = self._current_provider()
        provider = create_provider(provider_name, '', '')
        capable = provider.filter_file_capable(models)
        current = self.model_combo.currentText().strip()
        self.model_combo.clear()
        self.model_combo.addItems(capable)
        if current and capable and current not in capable:
            self.model_combo.setEditText(current)
        elif current:
            self.model_combo.setEditText(current)
        self.status_label.setText(tr('ai.status.models_loaded', count=len(capable)))

    def _on_models_failed(self, err):
        self.refresh_btn.setEnabled(True)
        self.status_label.setText('')
        show_warn(self, tr('common.error'), f"{tr('ai.error.fetch_models')}: {err}")

    # ---------- 文件管理 ----------
    def on_add_files(self):
        if len(self.files) >= MAX_FILES:
            show_warn(self, tr('common.error'), tr('ai.error.max_files', count=MAX_FILES))
            return
        suggested = os.path.join(str(pathlib.Path.home()), 'Documents')
        fns, _ = QFileDialog.getOpenFileNames(
            self, tr('ai.files.add'), suggested,
            'PDF (*.pdf);;Images (*.png *.jpg *.jpeg *.webp *.gif);;'
            'Documents (*.docx *.pptx *.txt *.md *.csv *.json *.yaml *.yml)')
        if not fns:
            return
        for fn in fns:
            if len(self.files) >= MAX_FILES:
                break
            if any(f['path'] == fn for f in self.files):
                continue
            try:
                self.files.append(prepare_file(fn))
            except Exception as e:
                show_warn(self, tr('common.error'), f"{os.path.basename(fn)}: {e}")
        self._refresh_file_table()

    def _refresh_file_table(self):
        self.file_table.setRowCount(0)
        for i, f in enumerate(self.files):
            r = self.file_table.rowCount()
            self.file_table.insertRow(r)
            it_name = QTableWidgetItem(f['name'])
            it_name.setData(Qt.ItemDataRole.UserRole, i)
            self.file_table.setItem(r, 0, it_name)
            size = os.path.getsize(f['path']) if os.path.exists(f['path']) else 0
            self.file_table.setItem(r, 1, QTableWidgetItem(self._fmt_size(size)))
            del_btn = QPushButton(tr('common.delete'))
            del_btn.setObjectName('btn-danger')
            del_btn.clicked.connect(lambda _=False, idx=i: self._remove_file(idx))
            self.file_table.setCellWidget(r, 2, del_btn)

    def _remove_file(self, idx):
        if 0 <= idx < len(self.files):
            self.files.pop(idx)
            self._refresh_file_table()

    @staticmethod
    def _fmt_size(n):
        if n >= 1024 * 1024:
            return f"{n / 1024 / 1024:.1f} MB"
        if n >= 1024:
            return f"{n / 1024:.1f} KB"
        return f"{n} B"

    # ---------- 生成 ----------
    def on_generate(self):
        provider_name = self._current_provider()
        base_url = self.base_url_edit.text().strip() or DEFAULT_BASE_URLS[provider_name]
        api_key = self.api_key_edit.text().strip()
        model = self.model_combo.currentText().strip()
        if not api_key:
            show_warn(self, tr('common.error'), tr('ai.error.no_api_key'))
            return
        if not model:
            show_warn(self, tr('common.error'), tr('ai.error.no_model'))
            return
        counts = {t: spin.value() for t, spin in self.count_spins.items()}
        if sum(counts.values()) <= 0:
            show_warn(self, tr('common.error'), tr('ai.error.no_counts'))
            return
        if not self.files:
            show_warn(self, tr('common.error'), tr('ai.error.no_files'))
            return
        score = self.score_spin.value()
        provider = create_provider(provider_name, base_url, api_key)
        self.gen_btn.setEnabled(False)
        self.import_btn.setEnabled(False)
        self.status_label.setText(tr('ai.status.generating'))
        self._gen_thread = GenerateThread(provider, model, counts, score, self.files, self)
        self._gen_thread.ok.connect(self._on_generate_ok)
        self._gen_thread.failed.connect(self._on_generate_failed)
        self._gen_thread.retrying.connect(self._on_generate_retrying)
        self._gen_thread.start()

    def _on_generate_retrying(self, reason):
        self.status_label.setText(tr('ai.status.retrying', reason=reason))

    def _on_generate_ok(self, questions, partial_err):
        self.gen_btn.setEnabled(True)
        self.generated = questions
        self._refresh_preview()
        self.import_btn.setEnabled(True)
        msg = tr('ai.status.done', count=len(questions))
        if partial_err:
            msg += f"（{tr('ai.status.partial', reason=partial_err)}）"
        self.status_label.setText(msg)

    def _on_generate_failed(self, err):
        self.gen_btn.setEnabled(True)
        self.status_label.setText('')
        show_warn(self, tr('common.error'), f"{tr('ai.error.generate')}: {err}")

    # ---------- 预览 ----------
    def _refresh_preview(self):
        self.preview_table.setRowCount(0)
        type_names = {
            'single': tr('exam.type.single'),
            'multiple': tr('exam.type.multiple'),
            'truefalse': tr('exam.type.truefalse'),
            'fill': tr('exam.type.fill'),
            'essay': tr('exam.type.essay'),
        }
        for i, q in enumerate(self.generated):
            r = self.preview_table.rowCount()
            self.preview_table.insertRow(r)
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            chk.setCheckState(Qt.CheckState.Checked)
            self.preview_table.setItem(r, 0, chk)
            self.preview_table.setItem(r, 1, QTableWidgetItem(str(i + 1)))
            self.preview_table.setItem(r, 2, QTableWidgetItem(type_names.get(q['type'], q['type'])))
            text = q['text']
            if len(text) > 80:
                text = text[:80] + '…'
            self.preview_table.setItem(r, 3, QTableWidgetItem(text))
            self.preview_table.setItem(r, 4, QTableWidgetItem(self._fmt_answer(q)))
            self.preview_table.setItem(r, 5, QTableWidgetItem(f"{q['score']:g}"))

    @staticmethod
    def _fmt_answer(q):
        t = q['type']
        if t in ('single', 'multiple'):
            return ','.join(str(c) for c in q['correct'])
        if t == 'truefalse':
            return 'True' if q['correct'][0] else 'False'
        ans = q['correct'][0] if q['correct'] else ''
        if len(ans) > 40:
            ans = ans[:40] + '…'
        return ans

    # ---------- 导入 ----------
    def on_import(self):
        selected = []
        for r in range(self.preview_table.rowCount()):
            it = self.preview_table.item(r, 0)
            if it is not None and it.checkState() == Qt.CheckState.Checked:
                selected.append(self.generated[r])
        if not selected:
            show_warn(self, tr('common.error'), tr('ai.error.no_selection'))
            return
        pool = self.pool_combo.currentData()
        for q in selected:
            add_question(self.exam_uuid, q['type'], q['text'], q['options'],
                         q['correct'], q['score'], pool=pool)
        show_info(self, tr('common.success'), tr('ai.import_done', count=len(selected)))
        p = self.parent()
        while p is not None and not hasattr(p, 'refresh_exams'):
            p = p.parent()
        if p is not None:
            p.refresh_exams()
        self.accept()
