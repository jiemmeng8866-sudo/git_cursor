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
                             QSplitter, QSizePolicy, QScrollArea, QFrame)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QDragEnterEvent, QDropEvent

# ================= 尝试导入第三方媒体库 =================
try:
    from tinytag import TinyTag
    HAS_TINYTAG = True
except ImportError:
    HAS_TINYTAG = False

# ================= 现代化自定义步进器 =================
class ModernStepper(QWidget):
    """现代质感数字输入器"""
    valueChanged = pyqtSignal(int)
    
    def __init__(self, value=0, min_val=0, max_val=9999, step=1):
        super().__init__()
        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        self._value = value
        
        self.setFixedHeight(30)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        self.btn_minus = QPushButton("-")
        self.btn_plus = QPushButton("+")
        self.line_edit = QLineEdit(str(self._value))
        self.line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn_style = """
            QPushButton {
                background-color: #F0F2ED; color: #5C6658;
                border: none; border-radius: 6px; font-weight: bold; font-size: 16px;
            }
            QPushButton:hover { background-color: #E6EBE3; color: #2C332A; }
            QPushButton:pressed { background-color: #DCE0D9; }
        """
        self.btn_minus.setStyleSheet(btn_style)
        self.btn_plus.setStyleSheet(btn_style)
        self.btn_minus.setFixedSize(28, 28)
        self.btn_plus.setFixedSize(28, 28)
        
        self.line_edit.setStyleSheet("""
            QLineEdit {
                background-color: transparent; border: 1px solid #EAECE8;
                border-radius: 6px; padding: 0; font-weight: bold; color: #2C332A;
            }
            QLineEdit:focus { border: 1px solid #6D8764; }
        """)
        self.line_edit.setFixedHeight(28)
        self.line_edit.setFixedWidth(40) 
        
        layout.addWidget(self.btn_minus)
        layout.addWidget(self.line_edit)
        layout.addWidget(self.btn_plus)
        
        self.btn_minus.clicked.connect(self.decrement)
        self.btn_plus.clicked.connect(self.increment)
        self.line_edit.editingFinished.connect(self.validate_input)
        
    def value(self): return self._value
        
    def setValue(self, val):
        val = max(self.min_val, min(self.max_val, val))
        self._value = val
        self.line_edit.setText(str(self._value))
        self.valueChanged.emit(self._value)
        
    def increment(self): self.setValue(self._value + self.step)
    def decrement(self): self.setValue(self._value - self.step)
        
    def validate_input(self):
        try:
            val = int(self.line_edit.text())
            self.setValue(val)
        except ValueError:
            self.line_edit.setText(str(self._value))
            
    def setRange(self, min_val, max_val):
        self.min_val = min_val
        self.max_val = max_val
        self.setValue(self._value)

# ================= 数据模型与规则引擎 =================
class FileRecord:
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
class FileDropTable(QTableWidget):
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
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("批量文件管理专家 V4.8 (流畅自适应版)")
        self.resize(1380, 880)
        self.setMinimumSize(1000, 600)
        self.setAcceptDrops(True)
        
        self.file_records = []
        self.history_stack = [] 
        self.app_logs = [] 
        
        self.apply_morandi_theme()
        self.init_ui()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            paths = [url.toLocalFile() for url in event.mimeData().urls()]
            self.handle_dropped_files(paths)
            event.acceptProposedAction()
        
    def apply_morandi_theme(self):
        brand_color = "#6D8764" 
        bg_color = "#F5F6F4"    
        card_bg = "#FFFFFF"     
        
        stylesheet = f"""
        QMainWindow {{ background-color: {bg_color}; }}
        QWidget {{ background-color: {bg_color}; color: #2C332A; font-family: "Microsoft YaHei", "Segoe UI", sans-serif; font-size: 13px; }}
        
        QLineEdit, QComboBox, QTextEdit {{ 
            background-color: #F9FAF8; border: 1px solid #DCE0D9; border-radius: 8px; padding: 8px 12px; color: #2C332A; 
        }}
        QLineEdit:hover, QComboBox:hover {{ border: 1px solid #B0B8AC; }}
        QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{ border: 2px solid {brand_color}; background-color: #FFFFFF; }}
        
        .nav-chip {{ background-color: #EAECE8; color: #5C6658; border: none; border-radius: 14px; padding: 8px 14px; font-weight: bold; font-size: 13px; }}
        .nav-chip:hover {{ background-color: #DCE0D9; }}
        .nav-chip:checked {{ background-color: {brand_color}; color: #FFFFFF; }}
        
        .btn-primary {{ background-color: {brand_color}; color: #FFFFFF; border: none; border-radius: 8px; padding: 9px 18px; font-weight: bold; }}
        .btn-primary:hover {{ background-color: #5A7352; }}
        
        .btn-secondary {{ background-color: #FFFFFF; color: #5C6658; border: 1px solid #DCE0D9; border-radius: 8px; padding: 9px 18px; font-weight: bold; }}
        .btn-secondary:hover {{ background-color: #F0F2ED; border-color: #C5CCC0; }}
        
        .btn-danger {{ background-color: #FCF2F2; color: #C94A4A; border: 1px solid #F5D5D5; border-radius: 8px; padding: 9px 18px; font-weight: bold; }}
        .btn-danger:hover {{ background-color: #FAEOEO; border-color: #EBBBBB; }}
        
        .btn-execute {{ background-color: #2C332A; color: #FFFFFF; border: none; font-size: 15px; border-radius: 12px; font-weight: bold; }}
        .btn-execute:hover {{ background-color: {brand_color}; }}
        
        QGroupBox {{ border: 1px solid #EAECE8; border-radius: 16px; margin-top: 26px; padding: 15px 15px 10px 15px; background-color: {card_bg}; }}
        QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; left: 10px; top: 2px; color: #2C332A; font-weight: bold; font-size: 14px; padding: 0 5px; }}
        
        QTableWidget {{ background-color: {card_bg}; gridline-color: transparent; border: none; border-radius: 16px; outline: none; }}
        QTableWidget::item {{ border-bottom: 1px solid #F5F6F4; padding: 5px; }}
        QTableView::item:hover {{ background-color: #F9FAF8; }}
        QTableView::item:selected {{ background-color: #E6EBE3; color: #2C332A; }}
        
        QHeaderView::section {{ background-color: #F0F2ED; padding: 10px 12px; border: none; border-bottom: 2px solid #EAECE8; font-weight: bold; color: #5C6658; text-align: left; }}
        
        QProgressBar {{ border: none; border-radius: 6px; background-color: #EAECE8; color: transparent; max-height: 10px; }}
        QProgressBar::chunk {{ background-color: {brand_color}; border-radius: 6px; }}
        
        QSplitter::handle {{ background: transparent; width: 8px; }}
        
        /* 优化点：定制现代化的扁平滚动条 */
        QScrollBar:vertical {{
            border: none;
            background: transparent;
            width: 6px;
            margin: 0px 0px 0px 0px;
        }}
        QScrollBar::handle:vertical {{
            background: #DCE0D9;
            min-height: 30px;
            border-radius: 3px;
        }}
        QScrollBar::handle:vertical:hover {{ background: #B0B8AC; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ border: none; background: none; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
        """
        self.setStyleSheet(stylesheet)
        
    def add_shadow(self, widget):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 15)) 
        shadow.setOffset(0, 4)
        widget.setGraphicsEffect(shadow)

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 20, 20)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # ================= 1. 左侧面板设置 =================
        left_panel = QWidget()
        left_panel.setMinimumWidth(360)
        left_panel.setMaximumWidth(550) 
        
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 10, 0) 
        left_layout.setSpacing(15)
        
        nav_widget = QWidget()
        nav_layout = QGridLayout(nav_widget)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(8)
        
        self.nav_group = QButtonGroup(self)
        menu_items = ["📝 基础重命名", "✂️ 精细截取", "🎵 音视频属性", "📂 多级去套娃", "🛡️ 安全与日志"]
        
        for i, text in enumerate(menu_items):
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setProperty("class", "nav-chip")
            self.nav_group.addButton(btn, i)
            row = i // 2
            col = i % 2
            if i == 4: nav_layout.addWidget(btn, row, col, 1, 2)
            else: nav_layout.addWidget(btn, row, col)
                
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
        
        # ================= 优化点：引入透明美化的 QScrollArea =================
        # 使用 ScrollArea 承载 StackedWidget，防止窗口缩小时控件被过度挤压
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")
        scroll_area.setWidget(self.stacked_widget)
        # ======================================================================

        card_container = QWidget()
        card_container.setObjectName("CardContainer")
        card_container.setStyleSheet("QWidget#CardContainer { background: white; border-radius: 16px; }")
        card_layout = QVBoxLayout(card_container)
        card_layout.setContentsMargins(15, 10, 5, 15) # 右侧边距稍微留小一点给滚动条
        card_layout.addWidget(scroll_area) # 将 ScrollArea 放入卡片中
        self.add_shadow(card_container)
        
        left_layout.addWidget(card_container)
        splitter.addWidget(left_panel)
        
        # ================= 2. 右侧主体区域 =================
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 5, 0, 0)
        right_layout.setSpacing(15)
        
        top_bar = QHBoxLayout()
        btn_add_files = QPushButton("➕ 添加文件"); btn_add_files.setProperty("class", "btn-primary")
        btn_add_folder = QPushButton("📁 添加文件夹"); btn_add_folder.setProperty("class", "btn-primary")
        btn_clear = QPushButton("🗑️ 清空列表"); btn_clear.setProperty("class", "btn-danger")
        btn_undo = QPushButton("↩️ 撤销上一步"); btn_undo.setProperty("class", "btn-secondary") 
        
        btn_add_files.clicked.connect(self.add_files)
        btn_add_folder.clicked.connect(self.add_folder)
        btn_clear.clicked.connect(self.clear_files)
        btn_undo.clicked.connect(self.undo_last_action)
        
        for btn in [btn_add_files, btn_add_folder, btn_clear, btn_undo]: top_bar.addWidget(btn)
        top_bar.addStretch()
        
        self.lbl_top_info = QLabel("当前导入: 0 个文件 | 选定待处理: 0 个")
        self.lbl_top_info.setStyleSheet("color: #8A9386; font-size: 13px; font-weight: bold;")
        top_bar.addWidget(self.lbl_top_info)
        right_layout.addLayout(top_bar)
        
        self.table_stack = QStackedWidget()
        self.add_shadow(self.table_stack)
        
        empty_page = QWidget()
        empty_page.setStyleSheet("background-color: #FFFFFF; border-radius: 16px;")
        empty_layout = QVBoxLayout(empty_page)
        empty_lbl = QLabel("📂\n\n暂无待处理文件\n点击上方按钮或直接将文件/文件夹拖拽至此")
        empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_lbl.setStyleSheet("color: #A3ACA0; font-size: 15px; font-weight: bold; line-height: 1.5;")
        empty_layout.addWidget(empty_lbl)
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
        self.chk_test_mode.setStyleSheet("color: #5C6658; font-weight: bold;")
        
        self.progress = QProgressBar()
        self.lbl_status = QLabel("就绪")
        self.lbl_status.setStyleSheet("color: #8A9386; margin-left: 10px;")
        
        self.btn_execute = QPushButton("立即执行批量任务")
        self.btn_execute.setProperty("class", "btn-execute")
        self.btn_execute.setMinimumSize(200, 45)
        self.btn_execute.clicked.connect(self.execute_rename)
        
        bottom_bar.addWidget(self.chk_test_mode)
        bottom_bar.addWidget(self.progress)
        bottom_bar.addWidget(self.lbl_status)
        bottom_bar.addStretch()
        bottom_bar.addWidget(self.btn_execute)
        
        right_layout.addLayout(bottom_bar)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 980])

    def _create_subtitle(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #8A9386; font-size: 12px; margin-bottom: 8px;")
        lbl.setWordWrap(True)
        return lbl

    # ================= 规则设置面板区 =================
    def create_basic_rule_panel(self):
        widget = QWidget()
        # 优化点：设置最小高度，低于这个高度就会触发上面的 ScrollArea 滚动条，避免组件被压扁
        widget.setMinimumHeight(480) 
        widget.setStyleSheet("background-color: transparent;")
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 10, 0) # 右侧留一点给滚动条呼吸的空间
        layout.setSpacing(12) 
        
        grp_replace = QGroupBox("文本查找与替换")
        form_rep = QFormLayout(grp_replace)
        form_rep.setVerticalSpacing(12)
        self.txt_rep_old = QLineEdit(); self.txt_rep_new = QLineEdit()
        self.chk_rep_regex = QCheckBox("开启正则表达式匹配")
        form_rep.addRow("查找内容:", self.txt_rep_old)
        form_rep.addRow("替换为:", self.txt_rep_new)
        form_rep.addRow("", self.chk_rep_regex)
        layout.addWidget(grp_replace)
        
        grp_fix = QGroupBox("快捷插入前后缀")
        form_fix = QFormLayout(grp_fix)
        form_fix.setVerticalSpacing(12)
        self.txt_prefix = QLineEdit(); self.txt_suffix = QLineEdit()
        form_fix.addRow("添加前缀:", self.txt_prefix)
        form_fix.addRow("添加后缀:", self.txt_suffix)
        layout.addWidget(grp_fix)
        
        grp_seq = QGroupBox("智能序号生成")
        seq_layout = QVBoxLayout(grp_seq)
        seq_layout.setSpacing(12)
        
        self.chk_use_seq = QCheckBox("为此批文件生成连续序号")
        seq_layout.addWidget(self.chk_use_seq)
        
        grid = QGridLayout()
        grid.setSpacing(10)
        
        self.spin_seq_start = ModernStepper(value=1, min_val=0, max_val=9999)
        self.spin_seq_step = ModernStepper(value=1, min_val=1, max_val=100)
        self.spin_seq_pad = ModernStepper(value=3, min_val=1, max_val=10)
        
        self.cmb_seq_pos = QComboBox()
        self.cmb_seq_pos.addItems(["前缀", "后缀"])
        self.cmb_seq_pos.setFixedHeight(30)
        
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

        grp_other = QGroupBox("进阶选项")
        form_other = QFormLayout(grp_other)
        form_other.setVerticalSpacing(12)
        self.cmb_case = QComboBox(); self.cmb_case.addItems(["不转换", "全大写", "全小写", "首字母大写"])
        self.chk_change_ext = QCheckBox("强制覆写扩展名")
        self.txt_new_ext = QLineEdit()
        form_other.addRow("大小写:", self.cmb_case)
        form_other.addRow(self.chk_change_ext, self.txt_new_ext)
        layout.addWidget(grp_other)
        
        layout.addStretch() # 保持卡片内容靠上排列
        
        controls = [self.txt_rep_old, self.txt_rep_new, self.txt_prefix, self.txt_suffix, self.txt_new_ext,
                    self.chk_rep_regex, self.chk_use_seq, self.chk_change_ext,
                    self.spin_seq_start, self.spin_seq_step, self.spin_seq_pad, self.cmb_seq_pos, self.cmb_case]
        for c in controls:
            if hasattr(c, 'textChanged'): c.textChanged.connect(self.update_preview)
            if hasattr(c, 'stateChanged'): c.stateChanged.connect(self.update_preview)
            if hasattr(c, 'valueChanged'): c.valueChanged.connect(self.update_preview)
            if hasattr(c, 'currentIndexChanged'): c.currentIndexChanged.connect(self.update_preview)
            
        return widget

    def create_cut_rule_panel(self):
        widget = QWidget()
        widget.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 10, 0)
        
        grp_del = QGroupBox("精确定长裁剪")
        form_del = QFormLayout(grp_del)
        form_del.setVerticalSpacing(12)
        self.spin_del_start = ModernStepper(value=0, min_val=0, max_val=999)
        self.spin_del_end = ModernStepper(value=0, min_val=0, max_val=999)
        form_del.addRow("删除开头N字符:", self.spin_del_start)
        form_del.addRow("删除结尾N字符:", self.spin_del_end)
        layout.addWidget(grp_del)
        layout.addStretch()
        self.spin_del_start.valueChanged.connect(self.update_preview)
        self.spin_del_end.valueChanged.connect(self.update_preview)
        return widget

    def create_media_panel(self):
        widget = QWidget()
        widget.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 10, 0)
        
        grp = QGroupBox("音视频媒体属性重命名")
        vbox = QVBoxLayout(grp)
        vbox.addWidget(self._create_subtitle("读取文件内置的媒体 ID3 标签并提取元数据作为文件名。(环境需安装 tinytag 支持库)"))
        
        if not HAS_TINYTAG:
            lbl_warn = QLabel("⚠ 未检测到 tinytag 库，功能受限。\n执行 pip install tinytag 开启全功能")
            lbl_warn.setStyleSheet("color: #D88D3B; font-size: 12px; font-weight: bold; margin-bottom: 5px;")
            vbox.addWidget(lbl_warn)
            
        row1 = QHBoxLayout()
        self.chk_use_media = QCheckBox("启用格式化")
        self.txt_media_template = QLineEdit("{artist} - {title}")
        row1.addWidget(self.chk_use_media)
        row1.addWidget(self.txt_media_template, 1)
        vbox.addLayout(row1)
        
        lbl_vars = QLabel("可用变量:\n {artist} 歌手 \n {title} 歌曲/视频名\n {album} 所属专辑\n {duration} 时长(分秒)")
        lbl_vars.setStyleSheet("color: #8A9386; font-size: 12px; background: #F9FAF8; padding: 10px; border-radius: 6px; margin-top: 10px;")
        vbox.addWidget(lbl_vars)
        layout.addWidget(grp)
        layout.addStretch()
        
        self.chk_use_media.stateChanged.connect(self.update_preview)
        self.txt_media_template.textChanged.connect(self.update_preview)
        return widget

    def create_flatten_panel(self):
        widget = QWidget()
        widget.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 10, 0)
        
        grp = QGroupBox("多级目录去套娃")
        vbox = QVBoxLayout(grp)
        vbox.addWidget(self._create_subtitle("将指定根目录下所有深层子文件夹内的文件，一键平铺提取到统一目录中。若遇重名自动追加父级文件夹名称防覆盖。"))
        
        self.btn_select_flatten_src = QPushButton("1. 选择嵌套源目录"); self.btn_select_flatten_src.setProperty("class", "btn-secondary")
        self.lbl_flatten_src = QLabel("等待选择..."); self.lbl_flatten_src.setStyleSheet("color: #A3ACA0;")
        
        self.btn_select_flatten_dest = QPushButton("2. 选择提取目标地"); self.btn_select_flatten_dest.setProperty("class", "btn-secondary")
        self.lbl_flatten_dest = QLabel("等待选择..."); self.lbl_flatten_dest.setStyleSheet("color: #A3ACA0;")
        
        self.btn_select_flatten_src.clicked.connect(lambda: self.select_dir(self.lbl_flatten_src))
        self.btn_select_flatten_dest.clicked.connect(lambda: self.select_dir(self.lbl_flatten_dest))
        
        vbox.addSpacing(10)
        vbox.addWidget(self.btn_select_flatten_src); vbox.addWidget(self.lbl_flatten_src)
        vbox.addSpacing(10)
        vbox.addWidget(self.btn_select_flatten_dest); vbox.addWidget(self.lbl_flatten_dest)
        vbox.addSpacing(20)
        
        self.btn_execute_flatten = QPushButton("开始去套娃平铺")
        self.btn_execute_flatten.setProperty("class", "btn-primary")
        self.btn_execute_flatten.setMinimumHeight(40)
        self.btn_execute_flatten.clicked.connect(self.execute_flatten)
        vbox.addWidget(self.btn_execute_flatten)
        layout.addWidget(grp)
        layout.addStretch()
        return widget

    def create_security_log_panel(self):
        widget = QWidget()
        widget.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 10, 0)
        
        grp_sec = QGroupBox("安全与拦截防御")
        form_sec = QFormLayout(grp_sec)
        self.chk_clean_illegal = QCheckBox("强制清理系统非法字符 (\\/:*?\"<>|)")
        self.chk_clean_illegal.setChecked(True)
        form_sec.addRow("", self.chk_clean_illegal)
        layout.addWidget(grp_sec)
        
        grp_log = QGroupBox("操作执行日志")
        log_layout = QVBoxLayout(grp_log)
        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setStyleSheet("font-size: 11px;")
        log_layout.addWidget(self.txt_logs)
        
        btn_export_log = QPushButton("导出日志文件")
        btn_export_log.setProperty("class", "btn-secondary")
        btn_export_log.clicked.connect(self.export_logs)
        log_layout.addWidget(btn_export_log)
        layout.addWidget(grp_log)
        
        self.chk_clean_illegal.stateChanged.connect(self.update_preview)
        return widget

    def select_dir(self, label):
        d = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if d: label.setText(d); label.setStyleSheet("color: #6D8764; font-weight: bold;") 

    # ================= 文件列表管理 =================
    def handle_dropped_files(self, paths):
        for path in paths:
            if os.path.isfile(path): self.add_single_file(path)
            elif os.path.isdir(path): self.add_directory_files(path)
        self.refresh_table()

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择文件")
        for f in files: self.add_single_file(f)
        self.refresh_table()

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder: self.add_directory_files(folder); self.refresh_table()

    def add_directory_files(self, folder):
        for root, dirs, files in os.walk(folder):
            for f in files: self.add_single_file(os.path.join(root, f))

    def add_single_file(self, path):
        if not any(r.original_path == path for r in self.file_records):
            self.file_records.append(FileRecord(path))

    def clear_files(self):
        self.file_records.clear()
        self.refresh_table()

    def update_top_status(self):
        total = len(self.file_records)
        selected = sum(1 for r in self.file_records if r.checked)
        self.lbl_top_info.setText(f"当前导入: {total} 个文件  |  勾选待处理: {selected} 个")
        
        if total == 0:
            self.table_stack.setCurrentIndex(0)
            self.lbl_status.setText("就绪")
            self.btn_execute.setText("立即执行批量任务")
        else:
            self.table_stack.setCurrentIndex(1)
            self.btn_execute.setText(f"立即处理选中的 {selected} 个文件")

    def refresh_table(self):
        self.table.setRowCount(len(self.file_records))
        self.update_preview()
        self.update_top_status()

    # ================= 预览与表格渲染 =================
    def get_current_rules(self):
        return {
            'replace_old': self.txt_rep_old.text(),
            'replace_new': self.txt_rep_new.text(),
            'replace_regex': self.chk_rep_regex.isChecked(),
            'prefix': self.txt_prefix.text(),
            'suffix': self.txt_suffix.text(),
            'use_seq': self.chk_use_seq.isChecked(),
            'seq_start': self.spin_seq_start.value(),
            'seq_step': self.spin_seq_step.value(),
            'seq_pad': self.spin_seq_pad.value(),
            'seq_pos': self.cmb_seq_pos.currentText(),
            'case_mode': self.cmb_case.currentText(),
            'change_ext': self.chk_change_ext.isChecked(),
            'new_ext': self.txt_new_ext.text(),
            'del_start': self.spin_del_start.value(),
            'del_end': self.spin_del_end.value(),
            'use_media': self.chk_use_media.isChecked(),
            'media_template': self.txt_media_template.text(),
            'clean_illegal': self.chk_clean_illegal.isChecked()
        }

    def update_preview(self):
        rules = self.get_current_rules()
        active_index = 0
        new_names_pool = {}
        
        for idx, record in enumerate(self.file_records):
            if not record.checked:
                record.new_fullname = record.original_fullname
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

        self.render_table()
        self.update_top_status()

    def on_checkbox_clicked(self, row, state):
        self.file_records[row].checked = (state == Qt.CheckState.Checked)
        self.update_preview()

    def render_table(self):
        conflict_count = 0
        self.table.setRowCount(len(self.file_records))
        for row, record in enumerate(self.file_records):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Checked if record.checked else Qt.CheckState.Unchecked)
            self.table.setItem(row, 0, chk)
            
            item_orig = QTableWidgetItem(record.original_fullname)
            item_orig.setForeground(QColor("#5C6658"))
            self.table.setItem(row, 1, item_orig)
            
            preview_item = QTableWidgetItem(record.new_fullname)
            if record.has_conflict:
                preview_item.setForeground(QColor("#C94A4A")) 
                preview_item.setText(f"⚠ {record.new_fullname} [存在冲突!]")
                conflict_count += 1
            elif record.original_fullname != record.new_fullname:
                preview_item.setForeground(QColor("#6D8764")) 
                preview_item.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Bold))
            self.table.setItem(row, 2, preview_item)
            
            self.table.setItem(row, 3, QTableWidgetItem(record.status))
            self.table.setItem(row, 4, QTableWidgetItem(f"{record.size / 1024:.1f}"))
            mtime_str = datetime.fromtimestamp(record.mtime).strftime('%Y-%m-%d %H:%M')
            self.table.setItem(row, 5, QTableWidgetItem(mtime_str))
            
            item_path = QTableWidgetItem(record.original_path)
            item_path.setForeground(QColor("#A3ACA0"))
            self.table.setItem(row, 6, item_path)

        try: self.table.itemChanged.disconnect()
        except: pass
        self.table.itemChanged.connect(lambda item: self.on_checkbox_clicked(item.row(), item.checkState()) if item.column() == 0 else None)
        
        if conflict_count > 0:
            self.lbl_status.setText(f"⚠ 发现 {conflict_count} 个重名冲突！请调整规则")
            self.lbl_status.setStyleSheet("color: #C94A4A; font-weight: bold; margin-left:10px;")
        else:
            self.lbl_status.setText("规则校验通过，无冲突")
            self.lbl_status.setStyleSheet("color: #6D8764; margin-left:10px;")

    # ================= 执行重命名与日志 =================
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
            with open(path, 'w', encoding='utf-8') as f:
                f.write("\n".join(self.app_logs))
            QMessageBox.information(self, "成功", "操作日志已成功导出至本地！")

    def execute_rename(self):
        if not self.file_records: return
            
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

        self.progress.setMaximum(len(self.file_records))
        self.progress.setValue(0)
        self.btn_execute.setText("处理中...")
        self.btn_execute.setEnabled(False)
        
        success_cnt, fail_cnt = 0, 0
        current_action_history = []
        self.add_log(f"--- 启动批量任务 (测试模式:{is_test}) ---")

        for row, record in enumerate(self.file_records):
            if not record.checked or record.original_fullname == record.new_fullname:
                self.progress.setValue(row + 1)
                continue

            old_path = record.original_path
            new_path = os.path.join(record.dir_name, record.new_fullname)

            if is_test:
                record.status = "✅ 模拟成功"
                success_cnt += 1
                self.add_log(f"[模拟通过] {record.original_fullname} -> {record.new_fullname}")
            else:
                try:
                    os.rename(old_path, new_path)
                    record.status = "✅ 写入成功"
                    record.original_path = new_path
                    record.original_fullname = record.new_fullname
                    record.original_name, record.ext = os.path.splitext(record.new_fullname)
                    current_action_history.append((new_path, old_path))
                    success_cnt += 1
                    self.add_log(f"[物理写入] {old_path} -> {new_path}")
                except Exception as e:
                    record.status = f"❌ 失败: {str(e)}"
                    fail_cnt += 1
                    self.add_log(f"[写入异常] {old_path} 因: {str(e)}")

            self.table.setItem(row, 3, QTableWidgetItem(record.status))
            self.progress.setValue(row + 1)
            QApplication.processEvents()

        if not is_test and current_action_history:
            self.history_stack.append(current_action_history)

        self.add_log(f"--- 任务结束 | 成功: {success_cnt} | 失败: {fail_cnt} ---\n")
        self.btn_execute.setEnabled(True)
        self.btn_execute.setText("处理完毕")
        QMessageBox.information(self, "处理汇报", f"本次任务完毕！\n\n成功: {success_cnt} 份\n失败: {fail_cnt} 份")
        self.update_preview()

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
        self.refresh_table()

    # ================= 去套娃扁平化 =================
    def execute_flatten(self):
        src = self.lbl_flatten_src.text()
        dest = self.lbl_flatten_dest.text()
        
        if not os.path.isdir(src) or not os.path.isdir(dest):
            QMessageBox.warning(self, "拦截提示", "非法目录！请正确配置源目录和目标提取目录。")
            return
            
        reply = QMessageBox.question(self, "防覆盖警告", f"将提取 [{src}] 内所有层级的深层文件到 [{dest}] 中。\n\n如遇重名，系统将自动追加父文件夹名防覆盖。启动吗？")
        if reply != QMessageBox.StandardButton.Yes: return
        
        files_to_move = []
        for root, _, files in os.walk(src):
            for f in files:
                files_to_move.append((os.path.join(root, f), root, f))
                
        success = 0
        self.add_log("--- 启动目录去套娃引击 ---")
        for old_path, root, filename in files_to_move:
            target_path = os.path.join(dest, filename)
            
            if os.path.exists(target_path) and old_path != target_path:
                name, ext = os.path.splitext(filename)
                parent_dir = os.path.basename(root)
                target_path = os.path.join(dest, f"{name}_{parent_dir}{ext}")
                
                if os.path.exists(target_path):
                    target_path = os.path.join(dest, f"{name}_{parent_dir}_{int(datetime.now().timestamp())}{ext}")
            
            try:
                shutil.move(old_path, target_path)
                success += 1
                self.add_log(f"[提取] {old_path} -> {target_path}")
            except Exception as e:
                self.add_log(f"[提取失败] {old_path} 因: {str(e)}")
                
        QMessageBox.information(self, "完成", f"去套娃深度解析操作成功！\n共提取文件: {success} 个。")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())