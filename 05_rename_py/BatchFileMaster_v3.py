# =============================================================================
# 批量文件管理专家 V6.0 — 高性能多线程重构版
# 功能：批量重命名 / 精细截取 / 音视频标签重命名 / 多级目录去套娃 / 安全与日志
# 架构：PyQt6 桌面应用，双栏布局（左=规则面板，右=文件列表），支持明暗主题切换
# =============================================================================

import sys
import os
import shutil
import re
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
                             QPushButton, QLabel, QLineEdit, QCheckBox, QStackedWidget,
                             QComboBox, QFileDialog, QMessageBox, QGridLayout, QButtonGroup,
                             QProgressBar, QGroupBox, QFormLayout, QTextEdit, QGraphicsDropShadowEffect,
                             QSplitter, QSizePolicy, QScrollArea, QFrame, QDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QSettings
from PyQt6.QtGui import QColor, QFont, QDragEnterEvent, QDropEvent

# ================= 尝试导入第三方媒体库（tinytag 用于读取音视频 ID3 标签）=================
try:
    from tinytag import TinyTag
    HAS_TINYTAG = True
except ImportError:
    HAS_TINYTAG = False

# ================= 后台工作线程 (解决 UI 假死) =================
# ================= 后台线程区：所有耗时操作放入子线程，避免 UI 卡死 =================

class FileLoaderThread(QThread):
    """【文件加载线程】在后台递归扫描文件夹、解析文件属性，每攒满 50 条 emit 一批给主线程"""
    batch_loaded = pyqtSignal(list)
    progress_updated = pyqtSignal(int)
    finished_loading = pyqtSignal(int)

    def __init__(self, paths, existing_paths, recursive=True):
        super().__init__()
        self.paths = paths
        self.existing_paths = set(existing_paths)
        self.recursive = recursive

    def run(self):
        batch = []
        count = 0

        def process_file(file_path):
            nonlocal count, batch
            if file_path not in self.existing_paths:
                self.existing_paths.add(file_path)
                record = FileRecord(file_path)
                batch.append(record)
                count += 1
                if len(batch) >= 50:
                    self.batch_loaded.emit(batch)
                    batch = []
                    self.progress_updated.emit(count)

        for path in self.paths:
            if os.path.isfile(path):
                process_file(path)
            elif os.path.isdir(path):
                if self.recursive:
                    for root, _, files in os.walk(path):
                        for f in files:
                            process_file(os.path.join(root, f))
                else:
                    try:
                        for f in os.listdir(path):
                            full_p = os.path.join(path, f)
                            if os.path.isfile(full_p):
                                process_file(full_p)
                    except Exception:
                        pass

        if batch:
            self.batch_loaded.emit(batch)
            self.progress_updated.emit(count)

        self.finished_loading.emit(count)

class RenameWorker(QThread):
    """【重命名执行线程】遍历待处理列表，逐文件执行 rename（或模拟），emit 进度给主线程刷新 UI"""
    item_processed = pyqtSignal(int, str, str, str)
    log_msg = pyqtSignal(str)
    finished_task = pyqtSignal(int, int, list)

    def __init__(self, records_snapshot, is_test):
        super().__init__()
        self.records = records_snapshot
        self.is_test = is_test

    def run(self):
        success_cnt, fail_cnt = 0, 0
        current_action_history = []

        self.log_msg.emit(f"--- 启动批量任务 (测试模式:{self.is_test}) ---")

        for row, record_data in enumerate(self.records):
            if not record_data['checked'] or record_data['original_fullname'] == record_data['new_fullname']:
                continue

            old_path = record_data['original_path']
            new_path = os.path.join(record_data['dir_name'], record_data['new_fullname'])
            new_fullname = record_data['new_fullname']

            if self.is_test:
                status = "✅ 模拟成功"
                success_cnt += 1
                self.log_msg.emit(f"[模拟通过] {record_data['original_fullname']} -> {new_fullname}")
                self.item_processed.emit(row, status, old_path, new_fullname)
            else:
                try:
                    os.rename(old_path, new_path)
                    status = "✅ 写入成功"
                    current_action_history.append((new_path, old_path))
                    success_cnt += 1
                    self.log_msg.emit(f"[物理写入] {old_path} -> {new_path}")
                    self.item_processed.emit(row, status, new_path, new_fullname)
                except Exception as e:
                    status = f"❌ 失败: {str(e)}"
                    fail_cnt += 1
                    self.log_msg.emit(f"[写入异常] {old_path} 因: {str(e)}")
                    self.item_processed.emit(row, status, old_path, record_data['original_fullname'])

        self.log_msg.emit(f"--- 任务结束 | 成功: {success_cnt} | 失败: {fail_cnt} ---\n")
        self.finished_task.emit(success_cnt, fail_cnt, current_action_history)

class FlattenWorker(QThread):
    """【去套娃提取线程】遍历源目录所有嵌套文件，shutil.move 到目标目录，重名时自动追加父文件夹名"""
    log_msg = pyqtSignal(str)
    finished_task = pyqtSignal(int)

    def __init__(self, src, dest):
        super().__init__()
        self.src = src
        self.dest = dest

    def run(self):
        files_to_move = []
        for root, _, files in os.walk(self.src):
            for f in files:
                files_to_move.append((os.path.join(root, f), root, f))

        success = 0
        self.log_msg.emit("--- 启动目录去套娃引击 ---")

        for old_path, root, filename in files_to_move:
            target_path = os.path.join(self.dest, filename)

            if os.path.exists(target_path) and old_path != target_path:
                name, ext = os.path.splitext(filename)
                parent_dir = os.path.basename(root)
                target_path = os.path.join(self.dest, f"{name}_{parent_dir}{ext}")

                if os.path.exists(target_path):
                    target_path = os.path.join(self.dest, f"{name}_{parent_dir}_{int(datetime.now().timestamp())}{ext}")

            try:
                shutil.move(old_path, target_path)
                success += 1
                self.log_msg.emit(f"[提取] {old_path} -> {target_path}")
            except Exception as e:
                self.log_msg.emit(f"[提取失败] {old_path} 因: {str(e)}")

        self.finished_task.emit(success)

# ================= 现代化自定义步进器 =================
# ================= 自定义组件：ModernStepper（带主题色的 +/- 步进器）=================
class ModernStepper(QWidget):
    """【自定义步进器】含 - 按钮、数字输入框、+ 按钮，支持主题色切换，emit valueChanged 信号"""
    valueChanged = pyqtSignal(int)

    def __init__(self, value=0, min_val=0, max_val=9999, step=1):
        super().__init__()
        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        self._value = value
        self._colors = None
        self.setFixedHeight(32)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.btn_minus = QPushButton("-")
        self.btn_plus = QPushButton("+")
        self.line_edit = QLineEdit(str(self._value))
        self.line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.line_edit.setFixedHeight(30)
        self.line_edit.setFixedWidth(45)

        self.btn_minus.setFixedSize(30, 30)
        self.btn_plus.setFixedSize(30, 30)

        layout.addWidget(self.btn_minus)
        layout.addWidget(self.line_edit)
        layout.addWidget(self.btn_plus)

        self.btn_minus.clicked.connect(self.decrement)
        self.btn_plus.clicked.connect(self.increment)
        self.line_edit.editingFinished.connect(self.validate_input)

    def set_theme_colors(self, c):
        """c: dict of color tokens from MainWindow.COLORS[theme]"""
        self._colors = c
        btn_style = f"""
            QPushButton {{ background-color: {c['bg_step']}; color: {c['text_secondary']}; border: 1px solid {c['border_main']}; border-radius: 6px; font-weight: bold; font-size: 16px; }}
            QPushButton:hover {{ background-color: {c['nav_hover_bg']}; border-color: {c['border_hover']}; color: {c['nav_hover_text']}; }}
            QPushButton:pressed {{ background-color: {c['border_hover']}; }}
        """
        self.btn_minus.setStyleSheet(btn_style)
        self.btn_plus.setStyleSheet(btn_style)
        self.line_edit.setStyleSheet(f"""
            QLineEdit {{ background-color: {c['bg_input']}; border: 1px solid {c['border_main']}; border-radius: 6px; padding: 0; font-weight: bold; color: {c['stepper_text']}; }}
            QLineEdit:focus {{ border: 2px solid {c['border_focus']}; }}
        """)

    def value(self): return self._value
    def setValue(self, val):
        val = max(self.min_val, min(self.max_val, val))
        self._value = val
        self.line_edit.setText(str(self._value))
        self.valueChanged.emit(self._value)
    def increment(self): self.setValue(self._value + self.step)
    def decrement(self): self.setValue(self._value - self.step)
    def validate_input(self):
        try: self.setValue(int(self.line_edit.text()))
        except ValueError: self.line_edit.setText(str(self._value))
    def setRange(self, min_val, max_val):
        self.min_val = min_val; self.max_val = max_val; self.setValue(self._value)

# ================= 数据模型 & 规则引擎（业务逻辑层，与 UI 解耦）=================
class FileRecord:
    """【文件记录】存储单个文件的原始路径、名称、扩展名、大小、修改时间、媒体信息等"""
    def __init__(self, path):
        self.original_path = path
        self.dir_name = os.path.dirname(path)
        self.original_fullname = os.path.basename(path)
        self.original_name, self.ext = os.path.splitext(self.original_fullname)
        self.new_fullname = self.original_fullname
        self.size = os.path.getsize(path)
        self.mtime = os.path.getmtime(path)
        self.status = "待处理"
        self.checked = True
        self.has_conflict = False
        self.media_info = {'artist': '', 'title': '', 'album': '', 'duration': ''}
        self._load_media_info(path)

    def _load_media_info(self, path):
        if HAS_TINYTAG and self.ext.lower() in ['.mp3', '.wav', '.flac', '.m4a', '.ogg', '.mp4']:
            try:
                tag = TinyTag.get(path)
                self.media_info['artist'] = tag.artist or '未知歌手'
                self.media_info['title'] = tag.title or '未知歌名'
                self.media_info['album'] = tag.album or '未知专辑'
                if tag.duration:
                    m, s = divmod(int(tag.duration), 60)
                    self.media_info['duration'] = f"{m:02d}分{s:02d}秒"
            except Exception: pass

class RenameEngine:
    """【规则引擎】根据用户设定的规则字典，对单个 FileRecord 生成新的文件名（纯计算，不操作硬盘）"""
    @staticmethod
    def apply_rules(record, index, rules):
        name = record.original_name
        ext = record.ext

        if rules.get('use_media'):
            template = rules.get('media_template', '')
            if template:
                name = template.replace('{artist}', record.media_info['artist']) \
                               .replace('{title}', record.media_info['title']) \
                               .replace('{album}', record.media_info['album']) \
                               .replace('{duration}', record.media_info['duration'])

        if rules.get('replace_old'):
            new_str = rules.get('replace_new', '')
            if rules.get('replace_regex'):
                try: name = re.sub(rules['replace_old'], new_str, name)
                except: pass
            else: name = name.replace(rules['replace_old'], new_str)

        if rules.get('del_start', 0) > 0: name = name[rules['del_start']:]
        if rules.get('del_end', 0) > 0: name = name[:-rules['del_end']] if len(name) > rules['del_end'] else ""

        case_mode = rules.get('case_mode', '不转换')
        if case_mode == '全大写': name = name.upper()
        elif case_mode == '全小写': name = name.lower()
        elif case_mode == '首字母大写': name = name.title()

        prefix = rules.get('prefix', '')
        suffix = rules.get('suffix', '')

        if rules.get('use_seq'):
            seq_num = rules.get('seq_start', 1) + index * rules.get('seq_step', 1)
            padding = rules.get('seq_padding', 1)
            seq_str = f"{seq_num:0{padding}d}"
            seq_pos = rules.get('seq_pos', '前缀')
            if seq_pos == '前缀': prefix = seq_str + rules.get('seq_sep', '') + prefix
            elif seq_pos == '后缀': suffix = suffix + rules.get('seq_sep', '') + seq_str

        name = f"{prefix}{name}{suffix}"

        if rules.get('clean_illegal'): name = re.sub(r'[\\/:*?"<>|]', '', name)
        if not name.strip(): name = "未命名文件"
        if rules.get('change_ext') and rules.get('new_ext'):
            ext = rules.get('new_ext')
            if not ext.startswith('.'): ext = '.' + ext

        return name + ext

# ================= 自定义拖拽表格 =================
# ================= 自定义拖拽表格：支持从系统资源管理器拖入文件/文件夹 =================
class FileDropTable(QTableWidget):
    """【可拖放表格】重写 drag/drop 事件，将拖入的文件路径转交给 MainWindow 处理"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
        else: super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
        else: super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            paths = [url.toLocalFile() for url in urls]
            main_win = self.window()
            if hasattr(main_win, 'handle_dropped_files'):
                main_win.handle_dropped_files(paths)
            event.acceptProposedAction()
        else: super().dropEvent(event)

# ================= 主窗口 =================
# ================= 主窗口：全局状态管理 + UI 构建 + 业务调度 =================
class MainWindow(QMainWindow):
    # ---- 主题色映射表：light/dark 两套配色，40+ 语义 token ----
    COLORS = {
        'light': {
            'bg_main': '#F2F3F5', 'bg_card': '#FFFFFF', 'bg_input': '#FFFFFF',
            'bg_group': '#FAFAFB', 'bg_hover': '#F7F8FA', 'bg_selected': '#E8F3FF',
            'bg_header': '#F7F8FA', 'bg_step': '#F2F3F5', 'bg_tag': '#E5E6EB',
            'text_primary': '#1D2129', 'text_secondary': '#4E5969', 'text_muted': '#86909C',
            'text_placeholder': '#C9CDD4', 'text_brand': '#165DFF',
            'border_main': '#E5E6EB', 'border_hover': '#C9CDD4', 'border_focus': '#165DFF',
            'border_tag': '#BFE0FF', 'table_border': '#F2F3F5',
            'brand': '#165DFF', 'brand_hover': '#4080FF', 'brand_disabled': '#94BFFF',
            'brand_light': '#E8F3FF',
            'success': '#00B42A', 'success_hover': '#23C343', 'success_disabled': '#7BE188',
            'btn_success_text': '#1D2129',
            'danger_text': '#F53F3F', 'danger_bg': '#FFECE8', 'danger_border': '#FDCEC5',
            'danger_hover_bg': '#F53F3F', 'danger_disabled_text': '#F89898',
            'exec_btn_start': '#165DFF', 'exec_btn_end': '#4080FF',
            'exec_btn_hover_start': '#4080FF', 'exec_btn_hover_end': '#6AA1FF',
            'exec_disabled': '#C9CDD4',
            'progress_bg': '#E5E6EB',
            'scrollbar': '#C9CDD4', 'scrollbar_hover': '#86909C',
            'conflict': '#F53F3F', 'changed': '#165DFF', 'file_inactive': '#C9CDD4',
            'nav_hover_bg': '#E5E6EB', 'nav_hover_text': '#1D2129',
            'stepper_text': '#1D2129', 'stepper_pressed': '#C9CDD4',
            'shadow_alpha': '15',
        },
        'dark': {
            'bg_main': '#1A1A1E', 'bg_card': '#252528', 'bg_input': '#2D2D31',
            'bg_group': '#222225', 'bg_hover': '#303034', 'bg_selected': '#1A3A5C',
            'bg_header': '#2A2A2E', 'bg_step': '#2D2D31', 'bg_tag': '#38383C',
            'text_primary': '#D0D0D4', 'text_secondary': '#9898A0', 'text_muted': '#707078',
            'text_placeholder': '#505058', 'text_brand': '#5098FF',
            'border_main': '#3A3A3E', 'border_hover': '#525258', 'border_focus': '#5098FF',
            'border_tag': '#2A5280', 'table_border': '#2E2E32',
            'brand': '#4080FF', 'brand_hover': '#6098FF', 'brand_disabled': '#2A4A78',
            'brand_light': '#1A3050',
            'success': '#2EA043', 'success_hover': '#3FB950', 'success_disabled': '#1A5C28',
            'btn_success_text': '#FFFFFF',
            'danger_text': '#E05555', 'danger_bg': '#3A1C20', 'danger_border': '#5A3038',
            'danger_hover_bg': '#E05555', 'danger_disabled_text': '#6A3838',
            'exec_btn_start': '#3568C0', 'exec_btn_end': '#6098FF',
            'exec_btn_hover_start': '#5080E0', 'exec_btn_hover_end': '#80B0FF',
            'exec_disabled': '#48484C',
            'progress_bg': '#353538',
            'scrollbar': '#48484C', 'scrollbar_hover': '#606068',
            'conflict': '#E05555', 'changed': '#5098FF', 'file_inactive': '#585860',
            'nav_hover_bg': '#353538', 'nav_hover_text': '#D0D0D4',
            'stepper_text': '#D0D0D4', 'stepper_pressed': '#525258',
            'shadow_alpha': '50',
        },
    }

    # ---- 初始化：窗口属性、状态变量、主题加载、UI 构建 ----
    def __init__(self):
        super().__init__()
        self.setWindowTitle("批量文件管理专家 V6.0 (高性能多线程重构版)")
        self.resize(1380, 880)
        self.setMinimumSize(1000, 600)
        self.setAcceptDrops(True)

        self.file_records = []
        self.history_stack = []
        self.app_logs = []
        self._steppers = []
        self._subtitles = []

        self._settings = QSettings("BatchFileMaster", "AppSettings")
        self._theme = self._settings.value("theme", "light")

        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self._do_update_preview)

        self._apply_theme()
        self.init_ui()

    # ---- 主题系统：颜色取值、全局 CSS 生成、主题应用与切换 ----
    def _c(self, token):
        """获取当前主题下指定 token 的颜色值"""
        return self.COLORS[self._theme][token]

    def _build_stylesheet(self):
        """生成全局 Qt CSS 样式表，所有颜色通过 c(token) 动态注入"""
        c = lambda t: self.COLORS[self._theme][t]
        return f"""
        QMainWindow, QDialog, QMessageBox {{ background-color: {c('bg_main')}; }}
        QWidget {{ color: {c('text_primary')}; font-family: "Segoe UI", "Microsoft YaHei", sans-serif; font-size: 13px; }}

        QMessageBox {{ background-color: {c('bg_card')}; border-radius: 8px; }}
        QMessageBox QLabel {{ color: {c('text_primary')}; font-size: 14px; font-weight: 500; background: transparent; }}
        QMessageBox QPushButton {{
            background-color: {c('brand')}; color: #FFFFFF; border: none;
            border-radius: 6px; padding: 8px 20px; font-weight: bold; min-width: 70px; min-height: 20px;
        }}
        QMessageBox QPushButton:hover {{ background-color: {c('brand_hover')}; }}
        QMessageBox QPushButton:pressed {{ background-color: {c('brand')}; }}

        QLineEdit, QComboBox, QTextEdit {{ background-color: {c('bg_input')}; border: 1px solid {c('border_main')}; border-radius: 6px; padding: 8px 12px; color: {c('text_primary')}; }}
        QLineEdit:hover, QComboBox:hover {{ border: 1px solid {c('border_hover')}; }}
        QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{ border: 2px solid {c('border_focus')}; background-color: {c('bg_input')}; }}

        QPushButton[cssClass="nav-chip"] {{ background-color: {c('bg_step')}; color: {c('text_secondary')}; border: 1px solid transparent; border-radius: 10px; padding: 10px 14px; font-weight: bold; font-size: 13px; }}
        QPushButton[cssClass="nav-chip"]:hover {{ background-color: {c('nav_hover_bg')}; color: {c('nav_hover_text')}; }}
        QPushButton[cssClass="nav-chip"]:checked {{ background-color: {c('brand_light')}; color: {c('text_brand')}; border: 1px solid {c('text_brand')}; }}

        QPushButton[cssClass="btn-primary"] {{ background-color: {c('brand')}; color: #FFFFFF; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold; }}
        QPushButton[cssClass="btn-primary"]:hover {{ background-color: {c('brand_hover')}; }}
        QPushButton[cssClass="btn-primary"]:disabled {{ background-color: {c('brand_disabled')}; color: #FFFFFF; }}

        QPushButton[cssClass="btn-success"] {{ background-color: {c('success')}; color: {c('btn_success_text')}; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold; }}
        QPushButton[cssClass="btn-success"]:hover {{ background-color: {c('success_hover')}; color: {c('btn_success_text')}; }}
        QPushButton[cssClass="btn-success"]:disabled {{ background-color: {c('success_disabled')}; color: {c('btn_success_text')}; }}

        QPushButton[cssClass="btn-secondary"] {{ background-color: {c('bg_card')}; color: {c('text_secondary')}; border: 1px solid {c('border_main')}; border-radius: 6px; padding: 8px 16px; font-weight: bold; }}
        QPushButton[cssClass="btn-secondary"]:hover {{ background-color: {c('bg_step')}; border-color: {c('border_hover')}; color: {c('text_primary')}; }}
        QPushButton[cssClass="btn-secondary"]:disabled {{ background-color: {c('bg_step')}; color: {c('text_placeholder')}; border-color: {c('border_main')}; }}

        QPushButton[cssClass="btn-danger"] {{ background-color: {c('danger_bg')}; color: {c('danger_text')}; border: 1px solid {c('danger_border')}; border-radius: 6px; padding: 8px 16px; font-weight: bold; }}
        QPushButton[cssClass="btn-danger"]:hover {{ background-color: {c('danger_hover_bg')}; color: #FFFFFF; border-color: {c('danger_hover_bg')}; }}
        QPushButton[cssClass="btn-danger"]:disabled {{ background-color: {c('danger_bg')}; color: {c('danger_disabled_text')}; border-color: {c('danger_disabled_text')}; }}

        QPushButton[cssClass="btn-execute"] {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {c('exec_btn_start')}, stop:1 {c('exec_btn_end')}); color: #FFFFFF; border: none; font-size: 16px; border-radius: 12px; font-weight: bold; }}
        QPushButton[cssClass="btn-execute"]:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {c('exec_btn_hover_start')}, stop:1 {c('exec_btn_hover_end')}); }}
        QPushButton[cssClass="btn-execute"]:disabled {{ background: {c('exec_disabled')}; color: #FFFFFF; }}

        QPushButton[cssClass="btn-theme"] {{ background-color: {c('bg_step')}; color: {c('text_secondary')}; border: 1px solid {c('border_main')}; border-radius: 6px; padding: 6px 10px; font-size: 15px; }}
        QPushButton[cssClass="btn-theme"]:hover {{ background-color: {c('nav_hover_bg')}; border-color: {c('border_hover')}; }}

        QFrame#CardPanel {{ background-color: {c('bg_card')}; border-radius: 14px; border: 1px solid {c('border_main')}; }}

        QGroupBox {{ border: 1px solid {c('border_main')}; border-radius: 8px; margin-top: 18px; padding: 20px 15px 15px 15px; background-color: {c('bg_group')}; }}
        QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; left: 12px; top: 0px; color: {c('text_brand')}; font-weight: bold; font-size: 14px; padding: 4px 10px; background-color: {c('bg_selected')}; border-radius: 6px; border: 1px solid {c('border_tag')}; }}

        QTableWidget {{ background-color: {c('bg_card')}; gridline-color: transparent; border: 1px solid {c('border_main')}; border-radius: 8px; outline: none; }}
        QTableWidget::item {{ border-bottom: 1px solid {c('table_border')}; padding: 5px; }}
        QTableView::item:hover {{ background-color: {c('bg_hover')}; }}
        QTableView::item:selected {{ background-color: {c('bg_selected')}; color: {c('text_brand')}; }}

        QHeaderView::section {{ background-color: {c('bg_header')}; padding: 12px; border: none; border-bottom: 2px solid {c('border_main')}; font-weight: bold; color: {c('text_secondary')}; text-align: left; }}

        QProgressBar {{ border: none; border-radius: 4px; background-color: {c('progress_bg')}; color: transparent; max-height: 8px; }}
        QProgressBar::chunk {{ background-color: {c('success')}; border-radius: 4px; }}

        QSplitter::handle {{ background: transparent; width: 16px; }}
        QScrollBar:vertical {{ border: none; background: transparent; width: 14px; margin: 0px 6px 0px 0px; }}
        QScrollBar::handle:vertical {{ background: {c('scrollbar')}; min-height: 30px; border-radius: 4px; }}
        QScrollBar::handle:vertical:hover {{ background: {c('scrollbar_hover')}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ border: none; background: none; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
        """

    def _apply_theme(self):
        """重新注入全局 CSS 并逐控件刷新 inline style（解决部分控件不跟随主题的问题）"""
        self.setStyleSheet(self._build_stylesheet())

        # Steppers
        c = self.COLORS[self._theme]
        for stepper in self._steppers:
            stepper.set_theme_colors(c)

        for subtitle in self._subtitles:
            subtitle.setStyleSheet(f"color: {c['text_muted']}; font-size: 12px; margin-bottom: 8px;")

        # Inline-colored widgets (re-apply if they've been created)
        if hasattr(self, 'lbl_top_info'):
            self.lbl_top_info.setStyleSheet(f"color: {c['text_secondary']}; font-size: 13px; font-weight: bold;")
        if hasattr(self, '_empty_lbl'):
            self._empty_lbl.setStyleSheet(f"color: {c['text_placeholder']}; font-size: 15px; font-weight: bold; line-height: 1.5;")
        if hasattr(self, 'chk_test_mode'):
            self.chk_test_mode.setStyleSheet(f"color: {c['text_secondary']}; font-weight: bold;")
        if hasattr(self, 'lbl_status'):
            self.lbl_status.setStyleSheet(f"color: {c['text_muted']}; margin-left: 10px;")
        if hasattr(self, 'lbl_flatten_src'):
            has_path = self.lbl_flatten_src.text() and self.lbl_flatten_src.text() != "等待选择..."
            color = c['text_brand'] if has_path else c['text_muted']
            weight = "font-weight: bold;" if has_path else ""
            self.lbl_flatten_src.setStyleSheet(f"color: {color}; {weight}")
        if hasattr(self, 'lbl_flatten_dest'):
            has_path = self.lbl_flatten_dest.text() and self.lbl_flatten_dest.text() != "等待选择..."
            color = c['text_brand'] if has_path else c['text_muted']
            weight = "font-weight: bold;" if has_path else ""
            self.lbl_flatten_dest.setStyleSheet(f"color: {color}; {weight}")
        if hasattr(self, 'txt_logs'):
            back = c['bg_input']; bord = c['border_main']
            self.txt_logs.setStyleSheet(f"font-size: 12px; background: {back}; border: 1px solid {bord};")
        if hasattr(self, 'lbl_warn_media'):
            self.lbl_warn_media.setStyleSheet(f"color: {c['danger_text']}; font-size: 12px; font-weight: bold; margin-bottom: 5px;")
        if hasattr(self, 'lbl_vars_media'):
            self.lbl_vars_media.setStyleSheet(f"color: {c['text_secondary']}; font-size: 12px; background: {c['bg_tag']}; padding: 12px; border-radius: 8px; margin-top: 10px;")

    def _toggle_theme(self):
        """切换明暗主题，持久化到 QSettings，更新按钮图标"""
        self._theme = "dark" if self._theme == "light" else "light"
        self._settings.setValue("theme", self._theme)
        self._apply_theme()
        self.btn_theme.setText("🌙" if self._theme == "light" else "☀️")
        self.trigger_preview_update()

    def add_shadow(self, widget):
        """给 CardPanel 添加阴影效果，alpha 值跟随主题"""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        alpha = int(self.COLORS[self._theme]['shadow_alpha'])
        shadow.setColor(QColor(0, 0, 0, alpha))
        shadow.setOffset(0, 4)
        widget.setGraphicsEffect(shadow)

    # ---- UI 构建：双栏布局（左规则面板 + 右文件列表）----
    def init_ui(self):
        """构建完整 UI：左侧可滚动规则面板 + 右侧文件表格与执行栏"""
        c = self.COLORS[self._theme]
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # ================= 1. 左侧面板设置 =================
        left_card = QFrame()
        left_card.setObjectName("CardPanel")
        self.add_shadow(left_card)
        left_card.setMinimumWidth(380)
        left_card.setMaximumWidth(550)
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(20, 20, 30, 20)
        left_layout.setSpacing(15)

        nav_widget = QWidget()
        nav_layout = QGridLayout(nav_widget)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(10)

        self.nav_group = QButtonGroup(self)
        menu_items = ["📝 基础重命名", "✂️ 精细截取", "🎵 音视频属性", "📂 多级去套娃", "🛡️ 安全与日志"]
        for i, text in enumerate(menu_items):
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setProperty("cssClass", "nav-chip")
            self.nav_group.addButton(btn, i)
            if i == 4: nav_layout.addWidget(btn, i//2, i%2, 1, 2)
            else: nav_layout.addWidget(btn, i//2, i%2)
        self.nav_group.button(0).setChecked(True)
        left_layout.addWidget(nav_widget)

        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background-color: transparent;")
        self.stacked_widget.addWidget(self.create_basic_rule_panel())
        self.stacked_widget.addWidget(self.create_cut_rule_panel())
        self.stacked_widget.addWidget(self.create_media_panel())
        self.stacked_widget.addWidget(self.create_flatten_panel())
        self.stacked_widget.addWidget(self.create_security_log_panel())
        self.nav_group.idClicked.connect(self.stacked_widget.setCurrentIndex)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")
        scroll_area.viewport().setStyleSheet("background-color: transparent;")
        scroll_area.setWidget(self.stacked_widget)

        # 给 QScrollArea 套一层容器，右侧额外留白，让滚动条与卡片边框有呼吸空间
        scroll_wrapper = QWidget()
        scroll_wrapper.setStyleSheet("background: transparent;")
        sw_layout = QVBoxLayout(scroll_wrapper)
        sw_layout.setContentsMargins(0, 0, 18, 0)
        sw_layout.addWidget(scroll_area)

        left_layout.addWidget(scroll_wrapper)
        splitter.addWidget(left_card)

        # ================= 2. 右侧主体区域 =================
        right_card = QFrame()
        right_card.setObjectName("CardPanel")
        self.add_shadow(right_card)
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(15)

        top_bar = QHBoxLayout()
        self.btn_add_files = QPushButton("➕ 添加文件"); self.btn_add_files.setProperty("cssClass", "btn-primary")
        self.btn_add_folder = QPushButton("📁 添加文件夹"); self.btn_add_folder.setProperty("cssClass", "btn-primary")
        self.btn_clear = QPushButton("🗑️ 清空列表"); self.btn_clear.setProperty("cssClass", "btn-danger")
        self.btn_undo = QPushButton("↩️ 撤销上一步"); self.btn_undo.setProperty("cssClass", "btn-secondary")

        self.btn_add_files.clicked.connect(self.add_files)
        self.btn_add_folder.clicked.connect(self.add_folder)
        self.btn_clear.clicked.connect(self.clear_files)
        self.btn_undo.clicked.connect(self.undo_last_action)

        for btn in [self.btn_add_files, self.btn_add_folder, self.btn_clear, self.btn_undo]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            top_bar.addWidget(btn)
        top_bar.addStretch()

        self.lbl_top_info = QLabel("当前导入: 0 个文件 | 选定待处理: 0 个")
        self.lbl_top_info.setStyleSheet(f"color: {c['text_secondary']}; font-size: 13px; font-weight: bold;")
        top_bar.addWidget(self.lbl_top_info)
        top_bar.addSpacing(8)

        self.btn_theme = QPushButton("🌙" if self._theme == "light" else "☀️")
        self.btn_theme.setProperty("cssClass", "btn-theme")
        self.btn_theme.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_theme.setFixedSize(36, 32)
        self.btn_theme.clicked.connect(self._toggle_theme)
        top_bar.addWidget(self.btn_theme)
        right_layout.addLayout(top_bar)

        self.table_stack = QStackedWidget()

        empty_page = QWidget()
        empty_layout = QVBoxLayout(empty_page)
        self._empty_lbl = QLabel("📂\n\n暂无待处理文件\n点击上方按钮或直接将文件/文件夹拖拽至此")
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setStyleSheet(f"color: {c['text_placeholder']}; font-size: 15px; font-weight: bold; line-height: 1.5;")
        empty_layout.addWidget(self._empty_lbl)
        self.table_stack.addWidget(empty_page)

        self.table = FileDropTable(0, 7)
        self.table.setHorizontalHeaderLabels(["", "原文件名", "新文件名预览", "状态", "大小(KB)", "修改时间", "原路径"])
        self.table.verticalHeader().setDefaultSectionSize(45)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_stack.addWidget(self.table)
        right_layout.addWidget(self.table_stack)

        bottom_bar = QHBoxLayout()
        self.chk_test_mode = QCheckBox("仅测试 (模拟执行，不改硬盘文件)")
        self.chk_test_mode.setStyleSheet(f"color: {c['text_secondary']}; font-weight: bold;")

        self.progress = QProgressBar()
        self.lbl_status = QLabel("就绪")
        self.lbl_status.setStyleSheet(f"color: {c['text_muted']}; margin-left: 10px;")

        self.btn_execute = QPushButton("立即执行批量任务")
        self.btn_execute.setProperty("cssClass", "btn-execute")
        self.btn_execute.setMinimumSize(220, 48)
        self.btn_execute.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_execute.clicked.connect(self.execute_rename)

        bottom_bar.addWidget(self.chk_test_mode)
        bottom_bar.addWidget(self.progress)
        bottom_bar.addWidget(self.lbl_status)
        bottom_bar.addStretch()
        bottom_bar.addWidget(self.btn_execute)

        right_layout.addLayout(bottom_bar)
        splitter.addWidget(right_card)
        splitter.setSizes([400, 980])

    def _create_subtitle(self, text):
        """创建统一风格的小标题 QLabel，注册到 _subtitles 以便主题切换时刷新"""
        c = self._c
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {c('text_muted')}; font-size: 12px; margin-bottom: 8px;")
        lbl.setWordWrap(True)
        self._subtitles.append(lbl)
        return lbl

    def _make_stepper(self, *args, **kwargs):
        """创建 ModernStepper 并注册到 _steppers 列表，主题切换时统一刷新"""
        s = ModernStepper(*args, **kwargs)
        s.set_theme_colors(self.COLORS[self._theme])
        self._steppers.append(s)
        return s

    # ================= 5 个左侧规则面板：每个返回一个 QWidget，放入 QStackedWidget =================
    def create_basic_rule_panel(self):
        """面板1：文本查找替换 + 前后缀 + 序号生成 + 大小写/扩展名"""
        widget = QWidget()
        widget.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 10, 0)
        layout.setSpacing(15)

        grp_replace = QGroupBox("🔍 文本查找与替换")
        form_rep = QFormLayout(grp_replace)
        form_rep.setVerticalSpacing(12)
        self.txt_rep_old = QLineEdit(); self.txt_rep_new = QLineEdit()
        self.chk_rep_regex = QCheckBox("开启正则表达式匹配")
        form_rep.addRow("查找内容:", self.txt_rep_old)
        form_rep.addRow("替换为:", self.txt_rep_new)
        form_rep.addRow("", self.chk_rep_regex)
        layout.addWidget(grp_replace)

        grp_fix = QGroupBox("➕ 快捷插入前后缀")
        form_fix = QFormLayout(grp_fix)
        form_fix.setVerticalSpacing(12)
        self.txt_prefix = QLineEdit(); self.txt_suffix = QLineEdit()
        form_fix.addRow("添加前缀:", self.txt_prefix)
        form_fix.addRow("添加后缀:", self.txt_suffix)
        layout.addWidget(grp_fix)

        grp_seq = QGroupBox("🔢 智能序号生成")
        seq_layout = QVBoxLayout(grp_seq)
        seq_layout.setSpacing(12)
        self.chk_use_seq = QCheckBox("为此批文件生成连续序号")
        seq_layout.addWidget(self.chk_use_seq)
        grid = QGridLayout()
        grid.setSpacing(10)
        self.spin_seq_start = self._make_stepper(value=1, min_val=0, max_val=9999)
        self.spin_seq_step = self._make_stepper(value=1, min_val=1, max_val=100)
        self.spin_seq_pad = self._make_stepper(value=3, min_val=1, max_val=10)
        self.cmb_seq_pos = QComboBox()
        self.cmb_seq_pos.addItems(["前缀", "后缀"])
        self.cmb_seq_pos.setFixedHeight(32)

        grid.addWidget(QLabel("起始:"), 0, 0)
        grid.addWidget(self.spin_seq_start, 0, 1)
        grid.addWidget(QLabel("步长:"), 0, 2)
        grid.addWidget(self.spin_seq_step, 0, 3)
        grid.addWidget(QLabel("补零:"), 1, 0)
        grid.addWidget(self.spin_seq_pad, 1, 1)
        grid.addWidget(QLabel("位置:"), 1, 2)
        grid.addWidget(self.cmb_seq_pos, 1, 3)
        seq_layout.addLayout(grid)
        layout.addWidget(grp_seq)

        grp_other = QGroupBox("⚙️ 进阶选项")
        form_other = QFormLayout(grp_other)
        form_other.setVerticalSpacing(12)
        self.cmb_case = QComboBox(); self.cmb_case.addItems(["不转换", "全大写", "全小写", "首字母大写"])
        self.cmb_case.setFixedHeight(32)
        self.chk_change_ext = QCheckBox("强制覆写扩展名")
        self.txt_new_ext = QLineEdit()
        form_other.addRow("大小写:", self.cmb_case)
        form_other.addRow(self.chk_change_ext, self.txt_new_ext)
        layout.addWidget(grp_other)
        layout.addStretch()

        controls = [self.txt_rep_old, self.txt_rep_new, self.txt_prefix, self.txt_suffix, self.txt_new_ext,
                    self.chk_rep_regex, self.chk_use_seq, self.chk_change_ext,
                    self.spin_seq_start, self.spin_seq_step, self.spin_seq_pad, self.cmb_seq_pos, self.cmb_case]
        for c in controls:
            if hasattr(c, 'textChanged'): c.textChanged.connect(self.trigger_preview_update)
            if hasattr(c, 'stateChanged'): c.stateChanged.connect(self.trigger_preview_update)
            if hasattr(c, 'valueChanged'): c.valueChanged.connect(self.trigger_preview_update)
            if hasattr(c, 'currentIndexChanged'): c.currentIndexChanged.connect(self.trigger_preview_update)

        return widget

    def create_cut_rule_panel(self):
        """面板2：删除开头/结尾 N 字符"""
        widget = QWidget()
        widget.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 10, 0)

        grp_del = QGroupBox("✂️ 精确定长裁剪")
        form_del = QFormLayout(grp_del)
        form_del.setVerticalSpacing(12)
        self.spin_del_start = self._make_stepper(value=0, min_val=0, max_val=999)
        self.spin_del_end = self._make_stepper(value=0, min_val=0, max_val=999)
        form_del.addRow("删除开头N字符:", self.spin_del_start)
        form_del.addRow("删除结尾N字符:", self.spin_del_end)
        layout.addWidget(grp_del)
        layout.addStretch()
        self.spin_del_start.valueChanged.connect(self.trigger_preview_update)
        self.spin_del_end.valueChanged.connect(self.trigger_preview_update)
        return widget

    def create_media_panel(self):
        """面板3：基于音视频 ID3 标签（歌手/歌名/专辑/时长）格式化文件名"""
        c = self.COLORS[self._theme]
        widget = QWidget()
        widget.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 10, 0)

        grp = QGroupBox("🎵 音视频媒体属性重命名")
        vbox = QVBoxLayout(grp)
        vbox.addWidget(self._create_subtitle("读取文件内置的媒体 ID3 标签并提取元数据作为文件名。(环境需安装 tinytag 支持库)"))

        if not HAS_TINYTAG:
            self.lbl_warn_media = QLabel("⚠ 未检测到 tinytag 库，功能受限。\n执行 pip install tinytag 开启全功能")
            self.lbl_warn_media.setStyleSheet(f"color: {c['danger_text']}; font-size: 12px; font-weight: bold; margin-bottom: 5px;")
            vbox.addWidget(self.lbl_warn_media)

        row1 = QHBoxLayout()
        self.chk_use_media = QCheckBox("启用格式化")
        self.txt_media_template = QLineEdit("{artist} - {title}")
        row1.addWidget(self.chk_use_media)
        row1.addWidget(self.txt_media_template, 1)
        vbox.addLayout(row1)

        self.lbl_vars_media = QLabel("可用变量:\n {artist} 歌手 \n {title} 歌曲/视频名\n {album} 所属专辑\n {duration} 时长(分秒)")
        self.lbl_vars_media.setStyleSheet(f"color: {c['text_secondary']}; font-size: 12px; background: {c['bg_tag']}; padding: 12px; border-radius: 8px; margin-top: 10px;")
        vbox.addWidget(self.lbl_vars_media)
        layout.addWidget(grp)
        layout.addStretch()

        self.chk_use_media.stateChanged.connect(self.trigger_preview_update)
        self.txt_media_template.textChanged.connect(self.trigger_preview_update)
        return widget

    def create_flatten_panel(self):
        """面板4：递归多级目录去套娃——将深层文件平铺提取到统一目录"""
        c = self.COLORS[self._theme]
        widget = QWidget()
        widget.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 10, 0)

        grp = QGroupBox("📂 递归多级目录去套娃")
        vbox = QVBoxLayout(grp)
        vbox.addWidget(self._create_subtitle("将指定根目录下所有深层子文件夹内的文件，一键平铺提取到统一目录中。若遇重名自动追加父级文件夹名称防覆盖。"))

        self.btn_select_flatten_src = QPushButton("1. 选择嵌套源目录"); self.btn_select_flatten_src.setProperty("cssClass", "btn-secondary")
        self.lbl_flatten_src = QLabel("等待选择..."); self.lbl_flatten_src.setStyleSheet(f"color: {c['text_muted']};")

        self.btn_select_flatten_dest = QPushButton("2. 选择提取目标地"); self.btn_select_flatten_dest.setProperty("cssClass", "btn-secondary")
        self.lbl_flatten_dest = QLabel("等待选择..."); self.lbl_flatten_dest.setStyleSheet(f"color: {c['text_muted']};")

        self.btn_select_flatten_src.clicked.connect(lambda: self.select_dir(self.lbl_flatten_src))
        self.btn_select_flatten_dest.clicked.connect(lambda: self.select_dir(self.lbl_flatten_dest))

        vbox.addSpacing(10)
        vbox.addWidget(self.btn_select_flatten_src); vbox.addWidget(self.lbl_flatten_src)
        vbox.addSpacing(10)
        vbox.addWidget(self.btn_select_flatten_dest); vbox.addWidget(self.lbl_flatten_dest)
        vbox.addSpacing(20)

        btn_frame = QFrame()
        btn_frame.setObjectName("CardPanel")
        btn_frame_layout = QVBoxLayout(btn_frame)
        btn_frame_layout.setContentsMargins(16, 16, 16, 16)

        self.btn_execute_flatten = QPushButton("🚀 确认执行去套娃平铺")
        self.btn_execute_flatten.setProperty("cssClass", "btn-success")
        self.btn_execute_flatten.setMinimumHeight(45)
        self.btn_execute_flatten.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_execute_flatten.clicked.connect(self.execute_flatten)
        btn_frame_layout.addWidget(self.btn_execute_flatten)

        vbox.addWidget(btn_frame)
        layout.addWidget(grp)
        layout.addStretch()
        return widget

    def create_security_log_panel(self):
        """面板5：非法字符清理开关 + 操作日志查看/导出"""
        c = self.COLORS[self._theme]
        widget = QWidget()
        widget.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 10, 0)

        grp_sec = QGroupBox("🛡️ 安全与拦截防御")
        form_sec = QFormLayout(grp_sec)
        self.chk_clean_illegal = QCheckBox("强制清理系统非法字符 (\\/:*?\"<>|)")
        self.chk_clean_illegal.setChecked(True)
        form_sec.addRow("", self.chk_clean_illegal)
        layout.addWidget(grp_sec)

        grp_log = QGroupBox("📝 操作执行日志")
        log_layout = QVBoxLayout(grp_log)
        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setStyleSheet(f"font-size: 12px; background: {c['bg_input']}; border: 1px solid {c['border_main']};")
        log_layout.addWidget(self.txt_logs)

        btn_export_log = QPushButton("导出日志文件")
        btn_export_log.setProperty("cssClass", "btn-secondary")
        btn_export_log.clicked.connect(self.export_logs)
        log_layout.addWidget(btn_export_log)
        layout.addWidget(grp_log)

        self.chk_clean_illegal.stateChanged.connect(self.trigger_preview_update)
        return widget

    # ---- 通用工具方法 ----
    def select_dir(self, label):
        """弹出文件夹选择对话框，将路径写入指定 QLabel，颜色改为 brand 色"""
        d = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if d:
            label.setText(d)
            label.setStyleSheet(f"color: {self._c('text_brand')}; font-weight: bold;")

    def _show_confirm_dialog(self, title, text, buttons):
        """通用确认弹窗：支持 primary/secondary/danger 风格按钮，返回点击的按钮文本"""
        c = self._c
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.setMinimumWidth(420)
        dlg.setStyleSheet(f"QDialog {{ background-color: {c('bg_card')}; border-radius: 8px; }}")

        layout = QVBoxLayout(dlg)
        layout.setSpacing(20)
        layout.setContentsMargins(28, 24, 28, 20)

        msg_label = QLabel(text)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet(f"""
            QLabel {{
                color: {c('text_primary')}; font-size: 14px; font-weight: 500;
                background: transparent;
            }}
        """)
        layout.addWidget(msg_label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()

        style_map = {
            'primary': f"""
                QPushButton {{ background-color: {c('brand')}; color: #FFFFFF; border: none;
                    border-radius: 6px; padding: 8px 16px; font-weight: bold; }}
                QPushButton:hover {{ background-color: {c('brand_hover')}; }}
            """,
            'secondary': f"""
                QPushButton {{ background-color: {c('bg_card')}; color: {c('text_secondary')}; border: 1px solid {c('border_main')};
                    border-radius: 6px; padding: 8px 16px; font-weight: bold; }}
                QPushButton:hover {{ background-color: {c('bg_step')}; border-color: {c('border_hover')}; color: {c('text_primary')}; }}
            """,
            'danger': f"""
                QPushButton {{ background-color: {c('danger_bg')}; color: {c('danger_text')};
                    border: 1px solid {c('danger_border')}; border-radius: 6px; padding: 8px 16px; font-weight: bold; }}
                QPushButton:hover {{ background-color: {c('danger_hover_bg')}; color: #FFFFFF; border-color: {c('danger_hover_bg')}; }}
            """,
        }

        clicked = []
        for btn_text, style_class in buttons:
            btn = QPushButton(btn_text)
            btn.setStyleSheet(style_map.get(style_class, style_map['secondary']))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumWidth(100)
            btn.clicked.connect(lambda checked, t=btn_text: (clicked.append(t), dlg.accept()))
            btn_layout.addWidget(btn)

        layout.addLayout(btn_layout)
        dlg.exec()
        return clicked[0] if clicked else None

    # ================= 异步文件加载管理 =================
    def handle_dropped_files(self, paths):
        self._start_async_file_loading(paths)

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择文件")
        if files: self._start_async_file_loading(files)

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            result = self._show_confirm_dialog(
                title="导入模式选择",
                text="是否连同子文件夹中的文件一起导入？\n\n[包含子文件夹]：递归读取内部所有文件\n[仅当前文件夹]：只读取选中目录下的文件",
                buttons=[
                    ("包含子文件夹", "primary"),
                    ("仅当前文件夹", "secondary"),
                    ("取消", "danger"),
                ],
            )
            if result == "取消" or result is None:
                return

            recursive = (result == "包含子文件夹")
            self._start_async_file_loading([folder], recursive=recursive)

    def _start_async_file_loading(self, paths, recursive=True):
        self.set_ui_loading_state(True, "正在疯狂扫描与读取文件，请稍候...")
        existing = [r.original_path for r in self.file_records]

        self.loader_thread = FileLoaderThread(paths, existing, recursive)
        self.loader_thread.batch_loaded.connect(self._on_loader_batch_received)
        self.loader_thread.progress_updated.connect(lambda cnt: self.lbl_status.setText(f"🚀 已急速读取 {cnt} 个文件..."))
        self.loader_thread.finished_loading.connect(self._on_loader_finished)
        self.loader_thread.start()

    def _on_loader_batch_received(self, batch_records):
        self.file_records.extend(batch_records)

    def _on_loader_finished(self, total_added):
        self.set_ui_loading_state(False)
        self.trigger_preview_update()
        if total_added > 0:
            self.add_log(f"成功扫入 {total_added} 个新文件到列表。")

    def clear_files(self):
        self.file_records.clear()
        self.table.setRowCount(0)
        self.trigger_preview_update()

    def set_ui_loading_state(self, is_loading, msg="就绪"):
        self.btn_execute.setEnabled(not is_loading)
        self.btn_add_files.setEnabled(not is_loading)
        self.btn_add_folder.setEnabled(not is_loading)
        self.btn_clear.setEnabled(not is_loading)
        self.lbl_status.setText(msg)
        if is_loading:
            self.lbl_status.setStyleSheet(f"color: {self._c('text_brand')}; font-weight: bold;")
        else:
            self.lbl_status.setStyleSheet(f"color: {self._c('text_muted')};")

    def update_top_status(self):
        total = len(self.file_records)
        selected = sum(1 for r in self.file_records if r.checked)
        self.lbl_top_info.setText(f"当前导入: {total} 个文件  |  勾选待处理: {selected} 个")

        if total == 0:
            self.table_stack.setCurrentIndex(0)
            self.btn_execute.setText("立即执行批量任务")
            self.btn_execute.setEnabled(False)
        else:
            self.table_stack.setCurrentIndex(1)
            self.btn_execute.setEnabled(True)
            self.btn_execute.setText(f"立即处理选中的 {selected} 个文件")

    # ================= 防抖更新与高性能差量渲染 =================
    # ---- 预览系统：300ms 防抖 → 规则引擎计算 → 差量渲染表格 ----
    def trigger_preview_update(self):
        """防抖触发器：任何规则变更后 300ms 内只触发一次实际更新"""
        self.preview_timer.start(300)

    def _do_update_preview(self):
        """遍历 file_records，用 RenameEngine 计算新文件名，检测冲突，刷新表格"""
        rules = self.get_current_rules()
        active_index = 0
        new_names_pool = {}

        for idx, record in enumerate(self.file_records):
            if not record.checked:
                record.new_fullname = record.original_fullname
                record.has_conflict = False
                continue

            new_name = RenameEngine.apply_rules(record, active_index, rules)
            record.new_fullname = new_name
            active_index += 1

            target_path = os.path.join(record.dir_name, new_name)
            record.has_conflict = False

            if os.path.exists(target_path) and target_path != record.original_path:
                record.has_conflict = True

            if target_path in new_names_pool:
                record.has_conflict = True
                self.file_records[new_names_pool[target_path]].has_conflict = True
            else:
                new_names_pool[target_path] = idx

        self.render_table_optimized()
        self.update_top_status()

    def on_checkbox_clicked(self, row, state):
        self.file_records[row].checked = (state == Qt.CheckState.Checked)
        self.trigger_preview_update()

    def render_table_optimized(self):
        c = self._c
        self.table.blockSignals(True)

        if self.table.rowCount() != len(self.file_records):
            self.table.setRowCount(len(self.file_records))

        conflict_count = 0

        for row, record in enumerate(self.file_records):
            chk = self.table.item(row, 0)
            if not chk:
                chk = QTableWidgetItem()
                chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                self.table.setItem(row, 0, chk)
            chk.setCheckState(Qt.CheckState.Checked if record.checked else Qt.CheckState.Unchecked)

            item_orig = self.table.item(row, 1)
            if not item_orig:
                item_orig = QTableWidgetItem()
                item_orig.setForeground(QColor(c('text_secondary')))
                self.table.setItem(row, 1, item_orig)
            if item_orig.text() != record.original_fullname:
                item_orig.setText(record.original_fullname)

            preview_item = self.table.item(row, 2)
            if not preview_item:
                preview_item = QTableWidgetItem()
                self.table.setItem(row, 2, preview_item)

            if record.has_conflict:
                preview_item.setForeground(QColor(c('conflict')))
                preview_item.setText(f"⚠ {record.new_fullname} [冲突!]")
                conflict_count += 1
            elif record.original_fullname != record.new_fullname:
                preview_item.setForeground(QColor(c('changed')))
                preview_item.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Bold))
                preview_item.setText(record.new_fullname)
            else:
                preview_item.setForeground(QColor(c('text_secondary')))
                preview_item.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Normal))
                preview_item.setText(record.new_fullname)

            status_item = self.table.item(row, 3)
            if not status_item:
                status_item = QTableWidgetItem()
                self.table.setItem(row, 3, status_item)
            status_item.setText(record.status)

            size_item = self.table.item(row, 4)
            if not size_item:
                size_item = QTableWidgetItem(f"{record.size / 1024:.1f}")
                self.table.setItem(row, 4, size_item)

            time_item = self.table.item(row, 5)
            if not time_item:
                mtime_str = datetime.fromtimestamp(record.mtime).strftime('%Y-%m-%d %H:%M')
                time_item = QTableWidgetItem(mtime_str)
                self.table.setItem(row, 5, time_item)

            path_item = self.table.item(row, 6)
            if not path_item:
                path_item = QTableWidgetItem(record.original_path)
                path_item.setForeground(QColor(c('file_inactive')))
                self.table.setItem(row, 6, path_item)

        self.table.blockSignals(False)

        try: self.table.itemChanged.disconnect()
        except TypeError: pass
        self.table.itemChanged.connect(lambda item: self.on_checkbox_clicked(item.row(), item.checkState()) if item.column() == 0 else None)

        if conflict_count > 0:
            self.lbl_status.setText(f"⚠ 发现 {conflict_count} 个重名冲突！请调整规则")
            self.lbl_status.setStyleSheet(f"color: {c('conflict')}; font-weight: bold; margin-left:10px;")
        else:
            self.lbl_status.setText("规则防抖校验通过，无冲突")
            self.lbl_status.setStyleSheet(f"color: {c('success')}; margin-left:10px;")

    def get_current_rules(self):
        """收集所有面板控件当前值，打包为规则字典传给 RenameEngine"""
        return {
            'replace_old': self.txt_rep_old.text(), 'replace_new': self.txt_rep_new.text(),
            'replace_regex': self.chk_rep_regex.isChecked(), 'prefix': self.txt_prefix.text(), 'suffix': self.txt_suffix.text(),
            'use_seq': self.chk_use_seq.isChecked(), 'seq_start': self.spin_seq_start.value(),
            'seq_step': self.spin_seq_step.value(), 'seq_padding': self.spin_seq_pad.value(),
            'seq_pos': self.cmb_seq_pos.currentText(), 'case_mode': self.cmb_case.currentText(),
            'change_ext': self.chk_change_ext.isChecked(), 'new_ext': self.txt_new_ext.text(),
            'del_start': self.spin_del_start.value(), 'del_end': self.spin_del_end.value(),
            'use_media': self.chk_use_media.isChecked(), 'media_template': self.txt_media_template.text(),
            'clean_illegal': self.chk_clean_illegal.isChecked()
        }

    # ================= 执行重命名与异步日志 =================
    def add_log(self, msg):
        time_str = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{time_str}] {msg}"
        self.app_logs.append(log_entry)
        self.txt_logs.append(log_entry)

    def export_logs(self):
        if not self.app_logs:
            QMessageBox.information(self, "提示", "暂无日志可导出")
            return
        path, _ = QFileDialog.getSaveFileName(self, "保存日志", "BatchRename_Logs.txt", "Text Files (*.txt)")
        if path:
            with open(path, 'w', encoding='utf-8') as f: f.write("\n".join(self.app_logs))
            QMessageBox.information(self, "成功", "操作日志已成功导出至本地！")

    # ---- 执行入口：启动 RenameWorker 后台线程 ----
    def execute_rename(self):
        """批量重命名入口：校验冲突 → 确认弹窗 → 创建 RenameWorker 线程执行"""

        conflicts = [r for r in self.file_records if r.has_conflict]
        if conflicts:
            QMessageBox.warning(self, "安全拦截", f"检测到 {len(conflicts)} 个文件重名风险，已触发防御拦截。\n请修改规则避免红色高亮项。")
            return

        selected = sum(1 for r in self.file_records if r.checked)
        if selected == 0: return

        is_test = self.chk_test_mode.isChecked()
        confirm_msg = "本次处于【模拟测试模式】，不会修改您的实际文件。" if is_test else f"即将对选中的 {selected} 个文件进行真实的物理重命名写入。\n此操作可能无法完全撤销，确认执行吗？"
        reply = QMessageBox.question(self, "执行确认", confirm_msg)
        if reply != QMessageBox.StandardButton.Yes: return

        snapshot = []
        for r in self.file_records:
            snapshot.append({
                'checked': r.checked, 'original_fullname': r.original_fullname,
                'original_path': r.original_path, 'dir_name': r.dir_name, 'new_fullname': r.new_fullname
            })

        self.progress.setMaximum(len(self.file_records))
        self.progress.setValue(0)
        self.set_ui_loading_state(True, "任务执行中...")
        self.btn_execute.setText("后台处理中...")

        self.rename_worker = RenameWorker(snapshot, is_test)
        self.rename_worker.log_msg.connect(self.add_log)
        self.rename_worker.item_processed.connect(self._on_rename_item_processed)
        self.rename_worker.finished_task.connect(lambda s, f, h: self._on_rename_finished(s, f, h, is_test))
        self.rename_worker.start()

    def _on_rename_item_processed(self, row, status, current_path, new_fullname):
        record = self.file_records[row]
        record.status = status
        record.original_path = current_path
        record.original_fullname = new_fullname
        record.original_name, record.ext = os.path.splitext(new_fullname)

        self.table.item(row, 3).setText(status)
        self.progress.setValue(row + 1)

    def _on_rename_finished(self, success_cnt, fail_cnt, history, is_test):
        if not is_test and history:
            self.history_stack.append(history)

        self.set_ui_loading_state(False)
        QMessageBox.information(self, "处理汇报", f"本次任务完毕！\n\n成功: {success_cnt} 份\n失败: {fail_cnt} 份")
        self.trigger_preview_update()

    def undo_last_action(self):
        if not self.history_stack:
            QMessageBox.information(self, "防错兜底", "当前状态没有可用于撤销的历史记录。")
            return

        reply = QMessageBox.question(self, "高危撤销确认", "系统将尝试逆向恢复上一次真实重命名的所有文件为原名称。\n请确保文件在此期间未被移动，确定操作吗？")
        if reply != QMessageBox.StandardButton.Yes: return

        last_actions = self.history_stack.pop()
        success, fail = 0, 0
        self.add_log("--- 启动紧急逆向撤销 ---")

        for current_path, old_path in last_actions:
            try:
                os.rename(current_path, old_path)
                success += 1
                self.add_log(f"[逆向恢复] {current_path} -> {os.path.basename(old_path)}")
            except Exception as e:
                fail += 1
                self.add_log(f"[恢复失败] {current_path} 因: {str(e)}")

        self.file_records.clear()
        QMessageBox.information(self, "兜底完成", f"反向恢复执行完毕。\n\n成功挽回: {success} 份\n挽回失败: {fail} 份\n\n为保证数据安全，列表已清空。")
        self.table.setRowCount(0)
        self.trigger_preview_update()

    # ================= 异步去套娃扁平化 =================
    # ---- 去套娃执行入口 ----
    def execute_flatten(self):
        src = self.lbl_flatten_src.text()
        dest = self.lbl_flatten_dest.text()

        if not os.path.isdir(src) or not os.path.isdir(dest):
            QMessageBox.warning(self, "拦截提示", "非法目录！请正确配置源目录和目标提取目录。")
            return

        reply = QMessageBox.question(self, "防覆盖警告", f"将提取 [{src}] 内所有层级的深层文件到 [{dest}] 中。\n\n如遇重名，系统将自动追加父文件夹名防覆盖。启动吗？")
        if reply != QMessageBox.StandardButton.Yes: return

        self.set_ui_loading_state(True, "正在进行海量文件平铺，切勿关闭软件...")
        self.btn_execute_flatten.setText("提取中...")
        self.btn_execute_flatten.setEnabled(False)

        self.flatten_worker = FlattenWorker(src, dest)
        self.flatten_worker.log_msg.connect(self.add_log)
        self.flatten_worker.finished_task.connect(self._on_flatten_finished)
        self.flatten_worker.start()

    def _on_flatten_finished(self, success_cnt):
        self.set_ui_loading_state(False)
        self.btn_execute_flatten.setEnabled(True)
        self.btn_execute_flatten.setText("🚀 确认执行去套娃平铺")
        QMessageBox.information(self, "完成", f"去套娃深度解析操作成功！\n共提取文件: {success_cnt} 个。")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())
