# ==========================================
# 运行环境要求: Python 3.7+
# 依赖安装: pip install PySide6
# 运行方式: python qimao_workbench.py
# 
# 【PRD V2.6 功能实现】: 
# 1. 小说立项工作流: 支持解析大纲(Outline)与正文(Chapter)，实施分轨质检
# 2. 本地规则引擎完全映射: H(大纲), A(红线), B(AI味), C(节奏), G(投稿包)
# 3. 极速响应架构: PySide6 信号槽直连，无网络 I/O 损耗
# 4. 动态 UI: Canvas雷达图、三栏诊断面板 (依据 PRD 规范着色)
# ==========================================

import sys
import time
import os
import re
import urllib.parse
from PySide6.QtWidgets import QApplication, QFileDialog
from PySide6.QtCore import QObject, Signal, Slot, Property, QThread

# --- 初始化默认演示数据 (体现立项工作流：包含大纲与正文) ---
DEFAULT_FILES = [
    {
        "name": "记忆当铺_大纲.md",
        "type": "outline",
        "icon": "🕸️",
        "content": "# 书名：记忆当铺\n## 核心卖点\n都市异能，情绪交易。\n\n## 卷章划分\n第一卷：初识\n- 第1章 相遇\n- 第2章 交易\n\n## 黄金三章设计\n开篇直接进入雨夜当铺的神秘氛围，抛出女主角要‘卖记忆’的核心悬念，拉起期待。"
    },
    {
        "name": "第1章 记忆当铺.txt",
        "type": "chapter",
        "icon": "📄",
        "content": "雨水敲打着霓虹招牌，像是无数人在敲一扇不会开门的门。\n林默站在街角，指尖捏着一枚旧铜牌——上面刻着三个字：记忆当铺。\n\n这家店开在城市的夹缝里，没有门头，也没有灯。\n客人要来，靠的是“记得”。\n\n叮——\n风铃响起。\n一个女人走了进来，披着湿透的长发，眼睛红肿。\n“我想卖掉一段记忆。”她说。\n林默没有抬头，只是翻开一本账册：\n“代价，等价。”"
    },
    {
        "name": "第2章 充满AI味的一章.txt",
        "type": "chapter",
        "icon": "📄",
        "content": "然而，这并非是一件简单的事情。\n总而言之，林默不禁倒吸了一口凉气。可以说，这是他见过的最诡异的交易。毫无疑问，那个女人的眼神中透露着一种难以言喻的悲伤，宛如深渊一般。\n\n不出意外的话，马上就要出意外了。林默眉头微皱，心想这件事情恐怕没有那么简单。首当其冲的是那枚U盘，上面刻着奇异的花纹。\n 一段超长超长的说明文在这里展开，没有任何对话，只有平铺直叙的设定解说，如同流水账一般向读者灌输背景设定，极其枯燥。"
    }
]

# --- 异步任务线程：PRD 规则引擎分轨分析 ---
class CheckWorker(QThread):
    finished = Signal(dict)
    
    def __init__(self, text, file_type):
        super().__init__()
        self.text = text
        self.file_type = file_type # "outline" 或 "chapter"

    def run(self):
        time.sleep(0.8) # 模拟分析耗时
        issues = []
        radar = [1.0, 1.0, 1.0, 1.0, 1.0] # 默认满分，发现问题扣分
        text_length = len(self.text)
        
        if text_length == 0:
            issues.append({"status": "RED", "id_txt": "SYS", "desc": "文本为空，无法进行分析", "loc": "全局", "sColor": "#EF4444"})
            self.finished.emit({"radar": [0,0,0,0,0], "issues": issues, "stats": {"words": 0}})
            return

        # ==========================================
        # 轨道一：大纲结构评审 (PRD 模块 H)
        # ==========================================
        if self.file_type == "outline":
            radar = [0.9, 0.8, 0.9, 0.7, 1.0] # 大纲特有雷达初始值 [完整度, 冲突性, 卖点, 节奏规划, 清晰度]
            
            # H1: 层级与完整性
            if "第" not in self.text or "章" not in self.text:
                issues.append({"status": "YELLOW", "id_txt": "H1", "desc": "大纲层级缺失，未检测到明确的卷/章结构划分", "loc": "全局", "sColor": "#F59E0B"})
                radar[0] -= 0.3
            else:
                issues.append({"status": "GREEN", "id_txt": "H1", "desc": "卷章结构清晰完整", "loc": "结构", "sColor": "#10B981"})
                
            # H3: 黄金三章映射
            if "悬念" not in self.text and "冲突" not in self.text and "爽点" not in self.text:
                issues.append({"status": "YELLOW", "id_txt": "H3", "desc": "前段缺乏明确的「开篇钩子」或「冲突」事件描述，开篇易失控", "loc": "黄金三章", "sColor": "#F59E0B"})
                radar[3] -= 0.4
            else:
                issues.append({"status": "GREEN", "id_txt": "H3", "desc": "检测到核心卖点与悬念规划", "loc": "开篇", "sColor": "#10B981"})
                
        # ==========================================
        # 轨道二：正文规则引擎 (PRD 模块 A, B, C)
        # ==========================================
        else:
            # 基础合规 A1
            banned_words = ["血腥", "暴力", "涉黄", "自杀"]
            found_banned = [w for w in banned_words if w in self.text]
            if found_banned:
                issues.append({"status": "RED", "id_txt": "A1", "desc": f"【红线】触发敏感违禁词: {', '.join(found_banned)}", "loc": "正文", "sColor": "#EF4444"})
                radar[0] -= 0.8
            else:
                issues.append({"status": "GREEN", "id_txt": "A1", "desc": "合规检查通过", "loc": "全局", "sColor": "#10B981"})

            # 基础排版 A2
            if "\n " in self.text and "\n\u3000" not in self.text:
                issues.append({"status": "YELLOW", "id_txt": "A2", "desc": "段首使用了不规范的半角空格，建议替换为全角缩进", "loc": "排版", "sColor": "#F59E0B"})

            # AI味检测 B1 & B2
            ai_words = ["不禁", "然而", "总而言之", "毫无疑问", "可以说", "倒吸一口凉气", "宛如", "不出意外的话", "首当其冲"]
            ai_hits = [w for w in ai_words if self.text.count(w) > 0]
            if len(ai_hits) >= 3 or sum([self.text.count(w) for w in ai_words]) > 4:
                issues.append({"status": "RED", "id_txt": "B2", "desc": f"【致命】严重AI味/机翻腔，高频词堆砌: {', '.join(ai_hits)}", "loc": "多处", "sColor": "#EF4444"})
                radar[4] -= 0.7
            elif len(ai_hits) > 0:
                issues.append({"status": "YELLOW", "id_txt": "B1", "desc": f"存在轻微AI腔调词汇: {ai_hits[0]}，建议精简", "loc": "局部", "sColor": "#F59E0B"})
                radar[4] -= 0.3
            else:
                issues.append({"status": "GREEN", "id_txt": "B0", "desc": "行文自然流畅，无AI痕迹", "loc": "全局", "sColor": "#10B981"})

            # 节奏与枯燥度 C1 & C2
            quote_count = self.text.count('“') + self.text.count('”')
            dialogue_ratio = (quote_count * 12) / text_length if text_length > 0 else 0
            
            # C4 长段落检测(流水账倾向)
            paragraphs = self.text.split("\n")
            long_paras = [p for p in paragraphs if len(p) > 150]
            if len(long_paras) > 0:
                issues.append({"status": "YELLOW", "id_txt": "C4", "desc": "发现连续超长说明段落，缺乏分段，易产生流水账的枯燥感", "loc": "节奏分段", "sColor": "#F59E0B"})
                radar[3] -= 0.3

            if dialogue_ratio < 0.15:
                issues.append({"status": "YELLOW", "id_txt": "C3", "desc": f"对话占比极低(约{int(dialogue_ratio*100)}%)，互动不足", "loc": "节奏", "sColor": "#F59E0B"})
                radar[3] -= 0.2
            else:
                issues.append({"status": "GREEN", "id_txt": "C0", "desc": "剧情互动与节奏健康", "loc": "全局", "sColor": "#10B981"})

        # 保证雷达图不出现负数
        radar = [max(0.1, r) for r in radar]

        self.finished.emit({
            "radar": radar,
            "issues": sorted(issues, key=lambda x: {"RED": 0, "YELLOW": 1, "GREEN": 2}.get(x["status"], 3)),
            "stats": {"words": text_length}
        })

# --- Python 核心逻辑控制器 ---
class BackendEngine(QObject):
    editorTextChanged = Signal()
    isCheckingChanged = Signal()
    radarDataChanged = Signal()
    issuesChanged = Signal()
    activeTabChanged = Signal()
    chapterListChanged = Signal()
    currentFileMetaChanged = Signal()

    def __init__(self):
        super().__init__()
        self.files = list(DEFAULT_FILES)
        self.current_index = 0
        
        self._editor_text = self.files[0]["content"]
        self._is_checking = False
        self._active_tab = "修改意见"
        
        # 雷达图标签
        self._radar_labels_outline = ["完整度", "冲突性", "卖点", "节奏规划", "清晰度"]
        self._radar_labels_chapter = ["合规", "风格匹配", "人设", "节奏", "AI味"]
        
        self._radar_data = [0.9, 0.8, 0.9, 0.7, 1.0] 
        self._raw_issues = [
            {"status": "INFO", "id_txt": "SYS", "desc": "工程加载完毕。由于您选择了【大纲】，点击「运行质检」将执行模块 H 结构评审。", "loc": "系统", "sColor": "#3B82F6"}
        ]
        self._display_issues = list(self._raw_issues)
        self.worker = None

    @Property('QVariantList', notify=chapterListChanged)
    def chapterList(self):
        return [{"name": f["name"], "icon": f["icon"], "isActive": i == self.current_index} 
                for i, f in enumerate(self.files)]

    @Property(str, notify=editorTextChanged)
    def editorText(self):
        return self._editor_text

    @Property(bool, notify=isCheckingChanged)
    def isChecking(self):
        return self._is_checking

    @Property(list, notify=radarDataChanged)
    def radarData(self):
        return self._radar_data
        
    @Property(list, notify=currentFileMetaChanged)
    def radarLabels(self):
        if self.files[self.current_index]["type"] == "outline":
            return self._radar_labels_outline
        return self._radar_labels_chapter

    @Property(str, notify=currentFileMetaChanged)
    def currentFileName(self):
        return self.files[self.current_index]["name"]

    @Property('QVariantList', notify=issuesChanged)
    def currentIssues(self):
        return self._display_issues
        
    @Property(str, notify=activeTabChanged)
    def activeTab(self):
        return self._active_tab

    @Slot(str)
    def setEditorText(self, text):
        if self._editor_text != text:
            self._editor_text = text
            self.files[self.current_index]["content"] = text
            self.editorTextChanged.emit()

    @Slot(int)
    def loadChapter(self, index):
        if 0 <= index < len(self.files):
            self.current_index = index
            self._editor_text = self.files[index]["content"]
            self.editorTextChanged.emit()
            self.chapterListChanged.emit()
            self.currentFileMetaChanged.emit()
            
            f_type = self.files[index]["type"]
            msg = "执行模块 H 结构评审" if f_type == "outline" else "执行 A~G 正文排版与内容质检"
            
            self._display_issues = [{"status": "INFO", "id_txt": "SYS", "desc": f"已切换至新文档，请点击「运行质检」{msg}。", "loc": "-", "sColor": "#3B82F6"}]
            self.issuesChanged.emit()
            self._radar_data = [0.1, 0.1, 0.1, 0.1, 0.1]
            self.radarDataChanged.emit()

    @Slot()
    def openFileDialog(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(None, "导入文件 (大纲或章节)", "", "Text/Markdown (*.txt *.md);;All Files (*)")
        if file_path:
            self._import_file_local(file_path)

    @Slot(str)
    def dropFile(self, url_str):
        parsed = urllib.parse.urlparse(url_str)
        file_path = urllib.parse.unquote(parsed.path)
        if os.name == 'nt' and file_path.startswith('/'):
            file_path = file_path[1:]
        self._import_file_local(file_path)
            
    def _import_file_local(self, file_path):
        if not os.path.exists(file_path): return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            filename = os.path.basename(file_path)
            
            # PRD: 启发式识别大纲与正文
            is_outline = "大纲" in filename or filename.endswith(".md")
            f_type = "outline" if is_outline else "chapter"
            icon = "🕸️" if is_outline else "📄"
            
            self.files.append({"name": filename, "type": f_type, "icon": icon, "content": content})
            self.chapterListChanged.emit()
            self.loadChapter(len(self.files) - 1)
        except Exception as e:
            print(f"导入失败: {e}")

    @Slot()
    def runCheck(self):
        if self._is_checking: return
        self._is_checking = True
        self.isCheckingChanged.emit()
        
        f_type = self.files[self.current_index]["type"]
        self.worker = CheckWorker(self._editor_text, f_type)
        self.worker.finished.connect(self._on_check_finished)
        self.worker.start()

    def _on_check_finished(self, result):
        self._is_checking = False
        self.isCheckingChanged.emit()
        self._radar_data = result["radar"]
        self.radarDataChanged.emit()
        self._raw_issues = result["issues"]
        self.refreshTabDisplay()

    @Slot(str)
    def switchTab(self, tab_name):
        self._active_tab = tab_name
        self.activeTabChanged.emit()
        self.refreshTabDisplay()
        
    def refreshTabDisplay(self):
        # 对应 PRD 核心契约：评判标准、修改意见、合并报告/投稿包
        if self._active_tab == "评判标准":
            f_type = self.files[self.current_index]["type"]
            if f_type == "outline":
                self._display_issues = [
                    {"status": "INFO", "id_txt": "RULE_H1", "desc": "H1: 卷章层级与结构完整性校验", "loc": "大纲模块", "sColor": "#3B82F6"},
                    {"status": "INFO", "id_txt": "RULE_H3", "desc": "H3: 黄金三章核心冲突/悬念探测", "loc": "大纲模块", "sColor": "#3B82F6"}
                ]
            else:
                self._display_issues = [
                    {"status": "INFO", "id_txt": "RULE_A1", "desc": "A1: 七猫红线审核违禁词库", "loc": "合规模块", "sColor": "#3B82F6"},
                    {"status": "INFO", "id_txt": "RULE_B2", "desc": "B2: AI 翻译腔及高频过渡词库过滤 (阈值: >3次告警)", "loc": "行文质感", "sColor": "#3B82F6"},
                    {"status": "INFO", "id_txt": "RULE_C3", "desc": "C3: 角色互动与对话占比下限检测 (阈值: <15%)", "loc": "节奏模块", "sColor": "#3B82F6"}
                ]
        elif self._active_tab == "投稿包":
            word_count = len(self._editor_text)
            self._display_issues = [
                {"status": "GREEN" if word_count > 500 else "YELLOW", "id_txt": "G1", "desc": f"单章字数校验 (当前: {word_count} 字，建议 >500)", "loc": "物料", "sColor": "#10B981" if word_count > 500 else "#F59E0B"},
                {"status": "YELLOW", "id_txt": "G2", "desc": "未关联一句话卖点与书籍简介，建议补充", "loc": "物料", "sColor": "#F59E0B"}
            ]
        else:
            self._display_issues = self._raw_issues
        self.issuesChanged.emit()

# --- QML 界面代码 ---
QML_CONTENT = """
import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    visible: true
    width: 1440
    height: 900
    title: qsTr("七猫预审工作台 - 小说立项工作流")
    color: "#0B0F19" // PRD V2.6 色彩基调
    font.family: "Microsoft YaHei, PingFang SC, sans-serif"

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ==================== 1. 顶部导航栏 ====================
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 56
            color: "#111827"
            Rectangle { width: parent.width; height: 1; anchors.bottom: parent.bottom; color: "#1F2937" }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 20
                anchors.rightMargin: 20
                spacing: 16

                RowLayout {
                    spacing: 8
                    Rectangle {
                        width: 24; height: 24; radius: 4
                        gradient: Gradient { 
                            GradientStop { position: 0.0; color: "#2DD4BF" }
                            GradientStop { position: 1.0; color: "#3B82F6" } 
                        }
                        Text { text: "🧭"; color: "white"; anchors.centerIn: parent }
                    }
                    Text { text: "七猫预审工作台"; color: "#2DD4BF"; font.pixelSize: 18; font.bold: true }
                }

                Item { Layout.fillWidth: true }

                RowLayout {
                    spacing: 12
                    ButtonTemplate { text: "📁 导入大纲/正文"; onClicked: backend.openFileDialog() }
                    
                    Rectangle { width: 1; height: 16; color: "#374151" }
                    
                    ButtonTemplate { text: "📥 导出合并报告"; textColor: "#9CA3AF" } // PRD 验收要求项
                    
                    // 运行质检按钮
                    Rectangle {
                        width: 110; height: 32; radius: 6
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: backend.isChecking ? "#9A3412" : "#F97316" }
                            GradientStop { position: 1.0; color: backend.isChecking ? "#9A3412" : "#D97706" }
                        }
                        RowLayout {
                            anchors.centerIn: parent
                            Text { text: backend.isChecking ? "⏳" : "▶"; color: "white"; font.pixelSize: 12 }
                            Text { text: backend.isChecking ? "分析中..." : "运行质检"; color: "white"; font.pixelSize: 13; font.bold: true }
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: backend.isChecking ? Qt.WaitCursor : Qt.PointingHandCursor
                            onClicked: { if(!backend.isChecking) backend.runCheck() }
                        }
                    }
                }
            }
        }

        // ==================== 2. 主体区域 ====================
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            // 2.1 最左侧边栏
            Rectangle {
                Layout.preferredWidth: 64; Layout.fillHeight: true; color: "#0B0F19"; border.color: "#1F2937"; border.width: 1
                ColumnLayout {
                    anchors.top: parent.top; anchors.topMargin: 20; anchors.horizontalCenter: parent.horizontalCenter; spacing: 20
                    SidebarIcon { iconText: "📚"; label: "当前工程"; isActive: true }
                    SidebarIcon { iconText: "👥"; label: "人设卡" }
                    SidebarIcon { iconText: "🧭"; label: "风格罗盘" }
                }
            }

            // 2.2 目录与大纲面板 (PRD 模块 P)
            Rectangle {
                Layout.preferredWidth: 260; Layout.fillHeight: true; color: "#111827"; border.color: "#1F2937"; border.width: 1
                ColumnLayout {
                    anchors.fill: parent; spacing: 0
                    
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 40; color: "#161F33"
                        Text { text: "立项工程树"; color: "#D1D5DB"; font.pixelSize: 13; font.bold: true; anchors.verticalCenter: parent.verticalCenter; anchors.left: parent.left; anchors.leftMargin: 15 }
                    }
                    
                    ListView {
                        id: chapterList
                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                        model: backend.chapterList
                        delegate: Rectangle {
                            width: parent.width; height: 36
                            color: modelData.isActive ? "#133E43" : "transparent"
                            RowLayout {
                                anchors.fill: parent; anchors.leftMargin: 15
                                Text { text: modelData.icon; font.pixelSize: 14 }
                                Text { text: modelData.name; color: modelData.isActive ? "#2DD4BF" : "#9CA3AF"; font.pixelSize: 13; elide: Text.ElideRight; Layout.fillWidth: true }
                            }
                            MouseArea {
                                anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: backend.loadChapter(index)
                            }
                        }
                    }
                    
                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: "#1F2937" }
                    
                    // 拖拽导入区
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 120; color: "#0B0F19"
                        DropArea {
                            anchors.fill: parent
                            onDropped: function(drop) {
                                if (drop.hasUrls) {
                                    for (var i = 0; i < drop.urls.length; i++) backend.dropFile(drop.urls[i])
                                    drop.accept()
                                }
                            }
                            Rectangle {
                                anchors.fill: parent; anchors.margins: 15; color: parent.parent.containsDrag ? "#1F2937" : "#111827"
                                border.color: parent.parent.containsDrag ? "#2DD4BF" : "#374151"; border.width: 1; radius: 8
                                ColumnLayout {
                                    anchors.centerIn: parent; spacing: 5
                                    Text { text: "☁️"; font.pixelSize: 20; Layout.alignment: Qt.AlignHCenter }
                                    Text { text: "拖拽大纲 .md 或 首批章节\\n自动分类解析入库"; color: "#6B7280"; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter }
                                }
                            }
                        }
                    }
                }
            }

            // 2.3 中央编辑器区域
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true; color: "#161B22"
                ColumnLayout {
                    anchors.fill: parent; spacing: 0
                    
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 40; color: "#0B0F19"; border.color: "#1F2937"; border.width: 1
                        RowLayout {
                            anchors.fill: parent; spacing: 0
                            Rectangle {
                                width: backend.currentFileName.length * 14 + 40; height: 40; color: "#161B22"; border.color: "#1F2937"; border.width: 1
                                Text { text: backend.currentFileName; color: "#2DD4BF"; font.pixelSize: 13; anchors.centerIn: parent }
                            }
                            Item { Layout.fillWidth: true }
                        }
                    }
                    
                    RowLayout {
                        Layout.fillWidth: true; Layout.fillHeight: true; spacing: 0
                        Rectangle {
                            Layout.preferredWidth: 45; Layout.fillHeight: true; color: "#111827"; border.color: "#1F2937"; border.width: 1
                            Column {
                                anchors.top: parent.top; anchors.topMargin: 15; anchors.right: parent.right; anchors.rightMargin: 10; spacing: 8
                                Repeater { model: 30; Text { text: index + 1; color: "#4B5563"; font.pixelSize: 13; font.family: "Consolas" } }
                            }
                        }
                        ScrollView {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            TextArea {
                                id: mainEditor
                                text: backend.editorText
                                color: "#D1D5DB"; font.pixelSize: 14; font.family: "Microsoft YaHei"
                                background: Rectangle { color: "#161B22" }
                                padding: 15; wrapMode: TextEdit.Wrap; selectByMouse: true
                                onTextChanged: { if (mainEditor.activeFocus) backend.setEditorText(mainEditor.text) }
                            }
                        }
                    }
                }
            }

            // 2.4 右侧质检分析面板 (PRD 核心输出契约)
            Rectangle {
                Layout.preferredWidth: 480; Layout.fillHeight: true; color: "#111827"; border.color: "#1F2937"; border.width: 1
                ColumnLayout {
                    anchors.fill: parent; spacing: 0
                    
                    // 图表区
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 280; color: "#161F33"; border.color: "#1F2937"; border.width: 1
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 15
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "动态质检雷达图"; color: "#E5E7EB"; font.pixelSize: 14; font.bold: true }
                                Item { Layout.fillWidth: true }
                            }
                            
                            RowLayout {
                                Layout.fillWidth: true; Layout.fillHeight: true
                                
                                Canvas {
                                    id: radarCanvas
                                    Layout.preferredWidth: 220; Layout.fillHeight: true
                                    Connections {
                                        target: backend
                                        function onRadarDataChanged() { radarCanvas.requestPaint() }
                                    }
                                    
                                    onPaint: {
                                        var ctx = getContext("2d"); var w = width, h = height;
                                        ctx.clearRect(0, 0, w, h);
                                        var cx = w / 2, cy = h / 2 + 5; var radius = Math.min(w, h) / 2 - 25;
                                        var angles = [0, 72, 144, 216, 288].map(d => (d * Math.PI / 180) - Math.PI/2);
                                        
                                        var data = backend.radarData; 
                                        var p_labels = backend.radarLabels;
                                        
                                        ctx.strokeStyle = "#2E3A51"; ctx.lineWidth = 1;
                                        for(var step=0.2; step<=1.0; step+=0.2) {
                                            ctx.beginPath();
                                            for(var i=0; i<5; i++) {
                                                var x = cx + Math.cos(angles[i]) * radius * step; var y = cy + Math.sin(angles[i]) * radius * step;
                                                if(i===0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
                                            }
                                            ctx.closePath(); ctx.stroke();
                                        }
                                        
                                        ctx.font = "11px sans-serif"; ctx.fillStyle = "#94A3B8"; ctx.textAlign = "center";
                                        for(var j=0; j<5; j++) {
                                            ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(angles[j]) * radius, cy + Math.sin(angles[j]) * radius); ctx.stroke();
                                            var textLabel = p_labels[j] + " " + Math.round(data[j]*100);
                                            ctx.fillText(textLabel, cx + Math.cos(angles[j]) * (radius + 15), cy + Math.sin(angles[j]) * (radius + 15) + 4);
                                        }
                                        
                                        ctx.beginPath();
                                        for(var k=0; k<5; k++) {
                                            var dx = cx + Math.cos(angles[k]) * radius * data[k]; var dy = cy + Math.sin(angles[k]) * radius * data[k];
                                            if(k===0) ctx.moveTo(dx, dy); else ctx.lineTo(dx, dy);
                                        }
                                        ctx.closePath();
                                        ctx.fillStyle = backend.isChecking ? "rgba(100, 116, 139, 0.2)" : "rgba(45, 212, 191, 0.2)"; 
                                        ctx.fill();
                                        ctx.strokeStyle = backend.isChecking ? "#64748B" : "#2DD4BF"; 
                                        ctx.lineWidth = 2; ctx.stroke();
                                    }
                                }
                                
                                ColumnLayout {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    Text { text: "当前启用模型:"; color: "#9CA3AF"; font.pixelSize: 12 }
                                    Rectangle {
                                        color: "#1F2937"; radius: 4; Layout.preferredHeight: 24; Layout.fillWidth: true
                                        Text { text: backend.radarLabels[0] === "合规" ? "A~G正文规则集 v2.5" : "H大纲结构评审模型 v1.0"; color: "#2DD4BF"; font.pixelSize: 11; anchors.centerIn: parent }
                                    }
                                    Item { Layout.fillHeight: true }
                                }
                            }
                        }
                    }
                    
                    // PRD: 三 Tab 诊断面板
                    Rectangle {
                        Layout.fillWidth: true; Layout.fillHeight: true; color: "#0B0F19"
                        ColumnLayout {
                            anchors.fill: parent; spacing: 0
                            
                            Rectangle {
                                Layout.fillWidth: true; Layout.preferredHeight: 46; color: "#111827"; border.color: "#1F2937"; border.width: 1
                                RowLayout {
                                    anchors.fill: parent; spacing: 0
                                    TabButtonT { text: "评判标准" }
                                    TabButtonT { text: "修改意见" }
                                    TabButtonT { text: "投稿包" }
                                    Item { Layout.fillWidth: true }
                                }
                            }
                            
                            Rectangle {
                                Layout.fillWidth: true; Layout.preferredHeight: 32; color: "#161B22"
                                RowLayout {
                                    anchors.fill: parent; anchors.leftMargin: 10; anchors.rightMargin: 10
                                    Text { text: "评级"; color: "#6B7280"; font.pixelSize: 12; Layout.preferredWidth: 40 }
                                    Text { text: "规则"; color: "#6B7280"; font.pixelSize: 12; Layout.preferredWidth: 45 }
                                    Text { text: "诊断意见摘要"; color: "#6B7280"; font.pixelSize: 12; Layout.fillWidth: true }
                                    Text { text: "位置"; color: "#6B7280"; font.pixelSize: 12; Layout.preferredWidth: 60; horizontalAlignment: Text.AlignRight }
                                }
                            }
                            
                            ListView {
                                Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                                model: backend.currentIssues 
                                delegate: Rectangle {
                                    width: parent.width; height: 55; color: "transparent"
                                    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: "#1F2937" }
                                    RowLayout {
                                        anchors.fill: parent; anchors.leftMargin: 10; anchors.rightMargin: 10
                                        Rectangle {
                                            Layout.preferredWidth: 40; height: 20; radius: 4; color: modelData.sColor; opacity: 0.15
                                        }
                                        Text { text: modelData.status; color: modelData.sColor; font.pixelSize: 10; font.bold: true; anchors.verticalCenter: parent.verticalCenter; x: 15 }
                                        Text { text: modelData.id_txt; color: "#9CA3AF"; font.pixelSize: 12; font.family: "Consolas"; font.bold:true; Layout.preferredWidth: 45 }
                                        Text { text: modelData.desc; color: "#D1D5DB"; font.pixelSize: 12; Layout.fillWidth: true; wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight; lineHeight: 1.2 }
                                        Text { text: modelData.loc; color: "#6B7280"; font.pixelSize: 12; Layout.preferredWidth: 60; horizontalAlignment: Text.AlignRight }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // --- 组件 ---
    component ButtonTemplate : Rectangle {
        property string text: "Button"
        property string textColor: "#D1D5DB"
        signal clicked()
        width: btnText.width + 24; height: 32; radius: 6; color: "transparent"; border.color: "#374151"
        Text { id: btnText; text: parent.text; color: parent.textColor; font.pixelSize: 13; anchors.centerIn: parent }
        MouseArea { 
            anchors.fill: parent; cursorShape: Qt.PointingHandCursor; hoverEnabled: true; 
            onEntered: parent.color = "#1F2937"; onExited: parent.color = "transparent" 
            onClicked: parent.clicked()
        }
    }

    component SidebarIcon : Item {
        property string iconText: ""; property string label: ""; property bool isActive: false
        width: 48; height: 48
        Rectangle {
            anchors.fill: parent; radius: 12; color: isActive ? "#133E43" : "transparent"
            Column { 
                anchors.centerIn: parent; spacing: 2
                Text { text: parent.parent.iconText; font.pixelSize: 18; anchors.horizontalCenter: parent.horizontalCenter }
                Text { text: parent.parent.label; color: parent.parent.isActive ? "#2DD4BF" : "#6B7280"; font.pixelSize: 10; anchors.horizontalCenter: parent.horizontalCenter } 
            }
            Rectangle { visible: parent.parent.isActive; width: 4; height: 24; radius: 2; color: "#2DD4BF"; anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter }
        }
    }
    
    component TabButtonT : Rectangle {
        property string text: "Tab"
        property bool active: backend.activeTab === text
        width: 100; height: parent.height; color: "transparent"
        Text { text: parent.text; color: parent.active ? "#2DD4BF" : "#9CA3AF"; font.pixelSize: 13; font.bold: parent.active; anchors.centerIn: parent }
        Rectangle { visible: parent.active; width: parent.width; height: 2; color: "#2DD4BF"; anchors.bottom: parent.bottom }
        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: backend.switchTab(parent.text) }
    }
}
"""

if __name__ == "__main__":
    app = QApplication(sys.argv)
    from PySide6.QtQml import QQmlApplicationEngine
    backend_engine = BackendEngine()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend_engine)
    engine.loadData(QML_CONTENT.encode('utf-8'))
    if not engine.rootObjects():
        sys.exit(-1)
    sys.exit(app.exec())