import sys
import os
import shutil
import re
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
                             QPushButton, QLabel, QLineEdit, QCheckBox, QStackedWidget,
                             QComboBox, QSpinBox, QSplitter, QFileDialog, QMessageBox,
                             QProgressBar, QGroupBox, QFormLayout, QListWidget, QListWidgetItem,
                             QTextEdit)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QIcon

# ================= 尝试导入第三方媒体库 =================
try:
    from tinytag import TinyTag
    HAS_TINYTAG = True
except ImportError:
    HAS_TINYTAG = False

# ================= 数据模型 =================
class FileRecord:
    """单个文件记录模型"""
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
        
        # 预存媒体信息
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
            except Exception:
                pass

# ================= 规则引擎 =================
class RenameEngine:
    """命名规则执行引擎"""
    @staticmethod
    def apply_rules(record, index, rules):
        name = record.original_name
        ext = record.ext

        # 0. 多媒体变量替换 (P1)
        if rules.get('use_media'):
            template = rules.get('media_template', '')
            if template:
                name = template.replace('{artist}', record.media_info['artist']) \
                               .replace('{title}', record.media_info['title']) \
                               .replace('{album}', record.media_info['album']) \
                               .replace('{duration}', record.media_info['duration'])

        # 1. 替换规则
        if rules.get('replace_old'):
            new_str = rules.get('replace_new', '')
            if rules.get('replace_regex'):
                try:
                    name = re.sub(rules['replace_old'], new_str, name)
                except:
                    pass
            else:
                name = name.replace(rules['replace_old'], new_str)

        # 2. 截取与删除
        if rules.get('del_start', 0) > 0:
            name = name[rules['del_start']:]
        if rules.get('del_end', 0) > 0:
            name = name[:-rules['del_end']] if len(name) > rules['del_end'] else ""

        # 3. 大小写转换
        case_mode = rules.get('case_mode', '不转换')
        if case_mode == '全大写':
            name = name.upper()
        elif case_mode == '全小写':
            name = name.lower()
        elif case_mode == '首字母大写':
            name = name.title()

        # 4. 前后缀与序号
        prefix = rules.get('prefix', '')
        suffix = rules.get('suffix', '')
        
        if rules.get('use_seq'):
            seq_num = rules.get('seq_start', 1) + index * rules.get('seq_step', 1)
            padding = rules.get('seq_padding', 1)
            seq_str = f"{seq_num:0{padding}d}"
            
            seq_pos = rules.get('seq_pos', '前缀')
            if seq_pos == '前缀':
                prefix = seq_str + rules.get('seq_sep', '') + prefix
            elif seq_pos == '后缀':
                suffix = suffix + rules.get('seq_sep', '') + seq_str

        name = f"{prefix}{name}{suffix}"

        # 5. 清理非法字符 (P1兜底)
        if rules.get('clean_illegal'):
            name = re.sub(r'[\\/:*?"<>|]', '', name)
            
        # 防止清空导致无文件名
        if not name.strip():
            name = "未命名文件"

        # 6. 扩展名处理
        if rules.get('change_ext') and rules.get('new_ext'):
            ext = rules.get('new_ext')
            if not ext.startswith('.'):
                ext = '.' + ext

        return name + ext

# ================= 自定义拖拽表格 =================
class FileDropTable(QTableWidget):
    """支持拖拽的表格组件"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            paths = [url.toLocalFile() for url in urls]
            # 传递给主窗口处理
            main_win = self.window()
            if hasattr(main_win, 'handle_dropped_files'):
                main_win.handle_dropped_files(paths)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

# ================= 主窗口 =================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("批量文件命名与管理专家 V3.0 (现代柔和交互版)")
        self.resize(1350, 850)
        self.file_records = []
        self.history_stack = [] 
        self.app_logs = [] 
        
        self.apply_organic_light_theme()
        self.init_ui()
        
    def apply_organic_light_theme(self):
        """参考柔和、有机、大圆角卡片(Soft/Organic)交互风格 QSS"""
        light_stylesheet = """
        QMainWindow { background-color: #EFEBE6; /* 暖灰/米色背景 */ }
        QWidget { color: #1C1C1C; font-family: "Microsoft YaHei", "Segoe UI", sans-serif; font-size: 13px; }
        
        /* 左侧导航栏 */
        QListWidget { 
            background-color: transparent; 
            border: none; 
            font-size: 14px; 
            outline: none;
            padding-top: 15px;
        }
        QListWidget::item { 
            padding: 16px 15px; 
            border-radius: 22px; /* 胶囊圆角 */
            margin: 6px 10px; 
            color: #5A5A5A; 
            background-color: #E5E0D8; /* 未选中状态更深的米色 */
        }
        QListWidget::item:hover { 
            background-color: #FFFFFF; 
            color: #1C1C1C; 
        }
        QListWidget::item:selected { 
            background-color: #DDF247; /* 参考图的亮黄绿色点缀 */
            color: #1C1C1C; 
            font-weight: bold;
        }
        
        /* 右侧表格 */
        QTableWidget { 
            background-color: #FFFFFF; 
            alternate-background-color: #F9F8F6;
            gridline-color: #EFEBE6; 
            border: none; 
            border-radius: 20px;
            selection-background-color: #F1F8B0;
            selection-color: #1C1C1C;
        }
        QHeaderView::section { 
            background-color: #FFFFFF; 
            padding: 12px; 
            border: none;
            border-bottom: 2px solid #EFEBE6;
            font-weight: bold; 
            color: #8A8A8A;
        }
        
        /* 输入控件 */
        QLineEdit, QSpinBox, QComboBox, QTextEdit { 
            background-color: #F5F3F0; 
            border: 2px solid transparent; 
            border-radius: 12px; 
            padding: 8px 12px; 
            color: #1C1C1C; 
        }
        QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QTextEdit:focus { 
            border: 2px solid #DDF247; 
            background-color: #FFFFFF;
        }
        
        /* 按钮通用样式 */
        QPushButton { 
            background-color: #FFFFFF; 
            border-radius: 20px; /* 胶囊形状 */
            padding: 8px 18px; 
            color: #4A4A4A; 
            border: 1px solid #E5E0D8; 
            font-weight: bold;
        }
        QPushButton:hover { background-color: #F5F3F0; border-color: #DDF247; }
        QPushButton:pressed { background-color: #E5E0D8; }
        
        /* 核心行为按钮 */
        .primary-btn { 
            background-color: #2D2D2D; /* 参考图中的深黑色按钮 */
            color: #FFFFFF; 
            border: none; 
            font-size: 14px; 
            border-radius: 20px;
        }
        .primary-btn:hover { background-color: #404040; }
        
        .accent-btn { 
            background-color: #DDF247; /* 亮黄绿色强调按钮 */
            color: #1C1C1C; 
            border: none; 
            border-radius: 20px;
        }
        .accent-btn:hover { background-color: #CFE822; }
        
        /* 分组框卡片 (模拟白色纯净卡片效果) */
        QGroupBox { 
            border: none; 
            border-radius: 24px; 
            margin-top: 35px; 
            padding-top: 25px; 
            padding-bottom: 15px;
            background-color: #FFFFFF;
        }
        QGroupBox::title { 
            subcontrol-origin: margin; 
            subcontrol-position: top left;
            left: 20px; 
            top: 0px;
            color: #1C1C1C; 
            font-weight: bold;
            font-size: 16px;
            background-color: transparent;
        }
        
        /* 进度条 */
        QProgressBar {
            border: none;
            border-radius: 6px;
            background-color: #E5E0D8;
            color: transparent;
            max-height: 12px;
        }
        QProgressBar::chunk {
            background-color: #DDF247;
            border-radius: 6px;
        }
        """
        self.setStyleSheet(light_stylesheet)
        
    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 15, 15)
        main_layout.setSpacing(0)
        
        # 1. 最左侧导航菜单
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(170) # 稍微放宽以容纳更大的圆角
        menu_items = ["📝 基础命名", "✂️ 精细截取", "🎵 多媒体属性", "📂 去套娃移动", "🛡️ 安全与日志"]
        self.sidebar.addItems(menu_items)
        self.sidebar.setCurrentRow(0)
        main_layout.addWidget(self.sidebar)
        
        # 2. 中间的卡片内容区 (适中宽度)
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setFixedWidth(320) # 控制为320px，保证输入框宽裕且不占大空间
        
        self.stacked_widget.addWidget(self.create_basic_rule_panel())
        self.stacked_widget.addWidget(self.create_cut_rule_panel())
        self.stacked_widget.addWidget(self.create_media_panel())
        self.stacked_widget.addWidget(self.create_flatten_panel())
        self.stacked_widget.addWidget(self.create_security_log_panel())
        
        self.sidebar.currentRowChanged.connect(self.stacked_widget.setCurrentIndex)
        
        center_container = QWidget()
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(20, 10, 15, 10)
        center_layout.addWidget(self.stacked_widget)
        main_layout.addWidget(center_container)
        
        # 3. 右侧主体表格与操作区 (释放更多空间)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 15, 0, 0)
        
        # 顶部工具栏
        toolbar = QHBoxLayout()
        btn_add_files = QPushButton("➕ 添加文件")
        btn_add_folder = QPushButton("📁 添加文件夹")
        btn_clear = QPushButton("🗑️ 清空列表")
        btn_undo = QPushButton("↩️ 撤销上一步")
        btn_undo.setProperty("class", "primary-btn") # 使用深色按钮，符合参考图设计
        
        btn_add_files.clicked.connect(self.add_files)
        btn_add_folder.clicked.connect(self.add_folder)
        btn_clear.clicked.connect(self.clear_files)
        btn_undo.clicked.connect(self.undo_last_action)
        
        toolbar.addWidget(btn_add_files)
        toolbar.addWidget(btn_add_folder)
        toolbar.addWidget(btn_clear)
        toolbar.addStretch()
        toolbar.addWidget(btn_undo)
        right_layout.addLayout(toolbar)
        
        # 文件展示表格
        self.table = FileDropTable(0, 7)
        self.table.setHorizontalHeaderLabels(["√", "原文件名", "新文件名预览", "状态", "大小(KB)", "修改时间", "原路径"])
        
        # 增加行高，让表格更有呼吸感，符合留白设计
        self.table.verticalHeader().setDefaultSectionSize(45)
        
        # ⭐ 核心修复：解决表头显示不全问题，动态自适应列宽 ⭐
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # 选择框自适应
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)          # 原文件名拉伸填充
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)          # 预览文件名拉伸填充
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # 状态自适应
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents) # 大小自适应
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents) # 时间自适应
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)      # 路径可手动拖拽(防止过长占满屏幕)
        
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False) # 移除网格线，让视觉更干净
        self.table.verticalHeader().setVisible(False)
        right_layout.addWidget(self.table)
        
        # 底部执行栏
        bottom_bar = QHBoxLayout()
        self.chk_test_mode = QCheckBox("仅测试 (模拟运行)")
        self.chk_test_mode.setChecked(False)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.lbl_status = QLabel("就绪 | 0 个文件 | 冲突: 0")
        self.lbl_status.setStyleSheet("color: #5A5A5A; font-weight: bold;")
        
        self.btn_execute = QPushButton("立即执行批量任务")
        self.btn_execute.setProperty("class", "primary-btn") # 使用深黑色核心按钮
        self.btn_execute.setMinimumSize(180, 45)
        self.btn_execute.clicked.connect(self.execute_rename)
        
        bottom_bar.addWidget(self.chk_test_mode)
        bottom_bar.addWidget(self.progress)
        bottom_bar.addWidget(self.lbl_status)
        bottom_bar.addWidget(self.btn_execute)
        right_layout.addLayout(bottom_bar)
        
        main_layout.addWidget(right_panel)
        main_layout.setStretchFactor(right_panel, 1) # 让右侧尽可能大

    # ================= 规则设置面板区 =================
    def create_basic_rule_panel(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        grp_replace = QGroupBox("文本替换与正则")
        form_rep = QFormLayout(grp_replace)
        self.txt_rep_old = QLineEdit()
        self.txt_rep_new = QLineEdit()
        self.chk_rep_regex = QCheckBox("使用正则表达式替换")
        form_rep.addRow("查找内容:", self.txt_rep_old)
        form_rep.addRow("替换为:", self.txt_rep_new)
        form_rep.addRow("", self.chk_rep_regex)
        layout.addWidget(grp_replace)
        
        grp_fix = QGroupBox("快捷前后缀")
        form_fix = QFormLayout(grp_fix)
        self.txt_prefix = QLineEdit()
        self.txt_suffix = QLineEdit()
        form_fix.addRow("添加前缀:", self.txt_prefix)
        form_fix.addRow("添加后缀:", self.txt_suffix)
        layout.addWidget(grp_fix)
        
        grp_seq = QGroupBox("智能序号生成")
        form_seq = QFormLayout(grp_seq)
        self.chk_use_seq = QCheckBox("启用智能序号")
        self.spin_seq_start = QSpinBox(); self.spin_seq_start.setRange(0, 9999); self.spin_seq_start.setValue(1)
        self.spin_seq_step = QSpinBox(); self.spin_seq_step.setRange(1, 100); self.spin_seq_step.setValue(1)
        self.spin_seq_pad = QSpinBox(); self.spin_seq_pad.setRange(1, 10); self.spin_seq_pad.setValue(3)
        self.cmb_seq_pos = QComboBox(); self.cmb_seq_pos.addItems(["前缀", "后缀"])
        form_seq.addRow("", self.chk_use_seq)
        form_seq.addRow("起始序号:", self.spin_seq_start)
        form_seq.addRow("递增步长:", self.spin_seq_step)
        form_seq.addRow("补零位数:", self.spin_seq_pad)
        form_seq.addRow("插入位置:", self.cmb_seq_pos)
        layout.addWidget(grp_seq)

        grp_other = QGroupBox("扩展选项")
        form_other = QFormLayout(grp_other)
        self.cmb_case = QComboBox(); self.cmb_case.addItems(["不转换", "全大写", "全小写", "首字母大写"])
        self.chk_change_ext = QCheckBox("覆写扩展名")
        self.txt_new_ext = QLineEdit()
        form_other.addRow("大小写转换:", self.cmb_case)
        form_other.addRow(self.chk_change_ext, self.txt_new_ext)
        layout.addWidget(grp_other)
        
        layout.addStretch()
        
        # 绑定实时预览
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
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        grp_del = QGroupBox("精确定长裁剪")
        form_del = QFormLayout(grp_del)
        self.spin_del_start = QSpinBox(); self.spin_del_start.setRange(0, 999)
        self.spin_del_end = QSpinBox(); self.spin_del_end.setRange(0, 999)
        form_del.addRow("删除开头N字符:", self.spin_del_start)
        form_del.addRow("删除结尾N字符:", self.spin_del_end)
        layout.addWidget(grp_del)
        
        layout.addStretch()
        self.spin_del_start.valueChanged.connect(self.update_preview)
        self.spin_del_end.valueChanged.connect(self.update_preview)
        return widget

    def create_media_panel(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        grp = QGroupBox("音视频属性重命名")
        form = QFormLayout(grp)
        
        lbl_info = QLabel("读取文件内置的媒体 ID3 标签。\n(需运行环境安装 tinytag 库)")
        lbl_info.setStyleSheet("color: #8b949e; font-size: 12px; margin-bottom: 5px;")
        if not HAS_TINYTAG:
            lbl_info.setText("⚠ 未检测到 tinytag 库，功能受限。\n执行 pip install tinytag 开启")
            lbl_info.setStyleSheet("color: #d29922; font-size: 12px; font-weight: bold; margin-bottom: 5px;")
            
        self.chk_use_media = QCheckBox("启用多媒体格式化")
        self.txt_media_template = QLineEdit("{artist} - {title}")
        self.txt_media_template.setPlaceholderText("例如: {artist} - {title}")
        
        lbl_vars = QLabel("支持的变量词典:\n {artist} 歌手名 \n {title} 歌曲/视频名\n {album} 所属专辑\n {duration} 时长(分秒)")
        lbl_vars.setStyleSheet("color: #58a6ff; font-size: 12px;")
        
        form.addRow(lbl_info)
        form.addRow("", self.chk_use_media)
        form.addRow("命名模板:", self.txt_media_template)
        form.addRow("", lbl_vars)
        layout.addWidget(grp)
        layout.addStretch()
        
        self.chk_use_media.stateChanged.connect(self.update_preview)
        self.txt_media_template.textChanged.connect(self.update_preview)
        return widget

    def create_flatten_panel(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        grp = QGroupBox("多级目录去套娃")
        vbox = QVBoxLayout(grp)
        
        lbl = QLabel("一键将所选根目录下所有深层子文件夹内的文件，全部移动到指定的统一目录内。\n系统自动重命名防覆盖。")
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color: #8A8A8A; margin-bottom: 10px; line-height: 1.5;")
        vbox.addWidget(lbl)
        
        self.btn_select_flatten_src = QPushButton("1. 指定源目标目录")
        self.lbl_flatten_src = QLabel("未选择")
        self.lbl_flatten_src.setStyleSheet("color: #D93838;")
        
        self.btn_select_flatten_dest = QPushButton("2. 指定提取到何处")
        self.lbl_flatten_dest = QLabel("未选择")
        self.lbl_flatten_dest.setStyleSheet("color: #D93838;")
        
        self.btn_select_flatten_src.clicked.connect(lambda: self.select_dir(self.lbl_flatten_src))
        self.btn_select_flatten_dest.clicked.connect(lambda: self.select_dir(self.lbl_flatten_dest))
        
        vbox.addWidget(self.btn_select_flatten_src)
        vbox.addWidget(self.lbl_flatten_src)
        vbox.addSpacing(5)
        vbox.addWidget(self.btn_select_flatten_dest)
        vbox.addWidget(self.lbl_flatten_dest)
        vbox.addSpacing(15)
        
        self.btn_execute_flatten = QPushButton("开始去套娃提取")
        self.btn_execute_flatten.setProperty("class", "primary-btn")
        self.btn_execute_flatten.setMinimumHeight(40)
        self.btn_execute_flatten.clicked.connect(self.execute_flatten)
        vbox.addWidget(self.btn_execute_flatten)
        
        layout.addWidget(grp)
        layout.addStretch()
        return widget

    def create_security_log_panel(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        grp_sec = QGroupBox("安全与规则防御")
        form_sec = QFormLayout(grp_sec)
        self.chk_clean_illegal = QCheckBox("强制清理系统非法字符 (\\/:*?\"<>|)")
        self.chk_clean_illegal.setChecked(True)
        form_sec.addRow("", self.chk_clean_illegal)
        layout.addWidget(grp_sec)
        
        grp_log = QGroupBox("控制台操作日志")
        log_layout = QVBoxLayout(grp_log)
        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        log_layout.addWidget(self.txt_logs)
        
        btn_export_log = QPushButton("导出日志至本地")
        btn_export_log.clicked.connect(self.export_logs)
        log_layout.addWidget(btn_export_log)
        
        layout.addWidget(grp_log)
        
        self.chk_clean_illegal.stateChanged.connect(self.update_preview)
        return widget

    def select_dir(self, label):
        d = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if d: 
            label.setText(d)
            label.setStyleSheet("color: #258C46;") # 浅色背景下使用更深的绿色

    # ================= 文件列表与拖拽处理 =================
    def handle_dropped_files(self, paths):
        for path in paths:
            if os.path.isfile(path):
                self.add_single_file(path)
            elif os.path.isdir(path):
                self.add_directory_files(path)
        self.refresh_table()

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择文件")
        for f in files: self.add_single_file(f)
        self.refresh_table()

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            self.add_directory_files(folder)
            self.refresh_table()

    def add_directory_files(self, folder):
        for root, dirs, files in os.walk(folder):
            for f in files:
                self.add_single_file(os.path.join(root, f))

    def add_single_file(self, path):
        if not any(r.original_path == path for r in self.file_records):
            self.file_records.append(FileRecord(path))

    def clear_files(self):
        self.file_records.clear()
        self.refresh_table()

    def refresh_table(self):
        self.table.setRowCount(len(self.file_records))
        self.update_preview()

    # ================= 核心预览引擎 =================
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
            
            # 冲突检测
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

    def render_table(self):
        conflict_count = 0
        self.table.setRowCount(len(self.file_records))
        for row, record in enumerate(self.file_records):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Checked if record.checked else Qt.CheckState.Unchecked)
            self.table.setItem(row, 0, chk)
            
            self.table.setItem(row, 1, QTableWidgetItem(record.original_fullname))
            
            preview_item = QTableWidgetItem(record.new_fullname)
            if record.has_conflict:
                preview_item.setForeground(QColor("#D93838")) # 浅色背景适合暗红色预警
                preview_item.setText(f"{record.new_fullname} [冲突!]")
                conflict_count += 1
            elif record.original_fullname != record.new_fullname:
                preview_item.setForeground(QColor("#258C46")) # 浅色背景适合深绿色高亮
            self.table.setItem(row, 2, preview_item)
            
            self.table.setItem(row, 3, QTableWidgetItem(record.status))
            self.table.setItem(row, 4, QTableWidgetItem(f"{record.size / 1024:.1f}"))
            
            mtime_str = datetime.fromtimestamp(record.mtime).strftime('%Y-%m-%d %H:%M')
            self.table.setItem(row, 5, QTableWidgetItem(mtime_str))
            self.table.setItem(row, 6, QTableWidgetItem(record.original_path))

        self.lbl_status.setText(f"就绪状态 | 共读取 {len(self.file_records)} 个文件 | 潜在冲突: {conflict_count} 个")

    # ================= 执行重命名与日志 (P1) =================
    def add_log(self, msg):
        time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{time_str}] {msg}"
        self.app_logs.append(log_entry)
        self.txt_logs.append(log_entry)

    def export_logs(self):
        if not self.app_logs:
            QMessageBox.information(self, "提示", "暂无日志可导出")
            return
        path, _ = QFileDialog.getSaveFileName(self, "保存日志", "rename_logs.txt", "Text Files (*.txt)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write("\n".join(self.app_logs))
            QMessageBox.information(self, "成功", "日志已导出！")

    def execute_rename(self):
        if not self.file_records:
            return
            
        conflicts = [r for r in self.file_records if r.has_conflict]
        if conflicts:
            QMessageBox.warning(self, "执行拦截", f"检测到 {len(conflicts)} 个文件存在重名风险，已触发安全拦截机制！\n请修改规则避免红色冲突项。")
            return

        is_test = self.chk_test_mode.isChecked()
        confirm_msg = "目前处于【测试模拟模式】，不会对系统硬盘做真实修改。" if is_test else "即将对列表内文件进行真实写入重命名，确认执行吗？"
        reply = QMessageBox.question(self, "执行确认", confirm_msg)
        if reply != QMessageBox.StandardButton.Yes: return

        self.progress.setMaximum(len(self.file_records))
        self.progress.setValue(0)
        
        success_cnt, fail_cnt = 0, 0
        current_action_history = []
        self.add_log(f"--- 开始批量执行任务 (模拟模式:{is_test}) ---")

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
                    self.add_log(f"[写入异常] {old_path} 原因: {str(e)}")

            self.table.setItem(row, 3, QTableWidgetItem(record.status))
            self.progress.setValue(row + 1)
            QApplication.processEvents()

        if not is_test and current_action_history:
            self.history_stack.append(current_action_history)

        self.add_log(f"--- 任务批处理结束 | 成功: {success_cnt} | 失败: {fail_cnt} ---\n")
        QMessageBox.information(self, "任务汇报", f"本次任务处理完毕！\n\n成功写入: {success_cnt} 份\n处理失败: {fail_cnt} 份")
        self.update_preview()

    def undo_last_action(self):
        if not self.history_stack:
            QMessageBox.information(self, "防错兜底", "当前状态没有可用于撤销的历史记录。")
            return
            
        reply = QMessageBox.question(self, "紧急撤销", "系统将尝试逆向恢复上一次物理重命名的所有文件为原名称，确定操作吗？")
        if reply != QMessageBox.StandardButton.Yes: return

        last_actions = self.history_stack.pop()
        success, fail = 0, 0
        self.add_log("--- 触发紧急逆向撤销操作 ---")
        
        for current_path, old_path in last_actions:
            try:
                os.rename(current_path, old_path)
                success += 1
                self.add_log(f"[成功恢复] {current_path} 还原至 {os.path.basename(old_path)}")
            except Exception as e:
                fail += 1
                self.add_log(f"[恢复拦截] {current_path} 原因: {str(e)}")
                
        self.file_records.clear()
        QMessageBox.information(self, "兜底完成", f"反向恢复执行完毕。\n\n成功挽回: {success} 个文件\n挽回失败: {fail} 个文件\n\n列表已安全清空。")
        self.refresh_table()

    # ================= 文件夹去套娃扁平化 (P0) =================
    def execute_flatten(self):
        src = self.lbl_flatten_src.text()
        dest = self.lbl_flatten_dest.text()
        
        if not os.path.isdir(src) or not os.path.isdir(dest):
            QMessageBox.warning(self, "安全拦截", "非法目录！请正确配置需要处理的源目录和目标目录。")
            return
            
        reply = QMessageBox.question(self, "同名防覆盖警告", f"系统将提取 [{src}] 内所有层级的深层文件到 [{dest}] 中。\n\n如遇重名文件，系统将自动追加父文件夹名称防止发生物理覆盖。确认启动吗？")
        if reply != QMessageBox.StandardButton.Yes: return
        
        files_to_move = []
        for root, _, files in os.walk(src):
            for f in files:
                files_to_move.append((os.path.join(root, f), root, f))
                
        success = 0
        self.add_log("--- 启动目录去套娃扁平化引击 ---")
        for old_path, root, filename in files_to_move:
            target_path = os.path.join(dest, filename)
            
            # 冲突兜底
            if os.path.exists(target_path) and old_path != target_path:
                name, ext = os.path.splitext(filename)
                parent_dir = os.path.basename(root)
                target_path = os.path.join(dest, f"{name}_{parent_dir}{ext}")
                
                if os.path.exists(target_path):
                    target_path = os.path.join(dest, f"{name}_{parent_dir}_{int(datetime.now().timestamp())}{ext}")
            
            try:
                shutil.move(old_path, target_path)
                success += 1
                self.add_log(f"[智能提取] {old_path} -> {target_path}")
            except Exception as e:
                self.add_log(f"[提取异常] {old_path} 原因: {str(e)}")
                
        QMessageBox.information(self, "提取完成", f"去套娃深度解析操作成功！\n成功提取并移动文件: {success} 个。")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())