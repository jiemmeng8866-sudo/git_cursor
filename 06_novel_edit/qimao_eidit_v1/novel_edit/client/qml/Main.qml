import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtCore

ApplicationWindow {
    id: root
    width: 1280
    height: 820
    visible: true
    title: "七猫预审工作台"
    minimumWidth: 960
    minimumHeight: 560

    property bool night: backend.nightTheme
    property bool hintsExpanded: false
    property bool mainSplitApplied: false

    Settings {
        id: uiSettings
        category: "split"
        property real mainLeftRatio: 0.44
    }

    onClosing: function(close) {
        if (splitMain.width > 80)
            uiSettings.mainLeftRatio = Math.min(0.78, Math.max(0.22, splitLeftCol.width / splitMain.width));
    }

    readonly property color cWin: night ? "#0f1419" : "#eef1f5"
    readonly property color cPanel: night ? "#1a2332" : "#ffffff"
    readonly property color cBorder: night ? "#3d5269" : "#c5cdd8"
    readonly property color cLblBar: night ? "#b8c5d6" : "#3d4754"
    readonly property color cLblSec: night ? "#9cb4d0" : "#4a5568"
    readonly property color cLblHint: night ? "#6a7a8e" : "#5c6570"
    readonly property color cLblMeta: night ? "#7a8a9e" : "#5c6570"
    readonly property color cStatus: night ? "#8b9cb3" : "#5c6570"
    readonly property color cSep: night ? "#3d5269" : "#c5cdd8"
    readonly property color cFieldTxt: night ? "#e7ecf3" : "#1a1d21"
    readonly property color cOutline: night ? "#e8eef7" : "#1a1d21"
    readonly property color cChapter: night ? "#dce6f2" : "#243040"
    readonly property color cReport: night ? "#dff7ea" : "#0f3d26"
    readonly property color cLlm: night ? "#e8e0ff" : "#4c1d95"
    readonly property color cMeta: night ? "#d0dce8" : "#243040"
    readonly property color cPh: night ? "#7a8a9e" : "#8896a6"

    color: cWin

    palette.window: cWin
    palette.windowText: cFieldTxt
    palette.base: cPanel
    palette.alternateBase: night ? "#151d2b" : "#f7f8fa"
    palette.text: cFieldTxt
    palette.button: night ? "#2a3548" : "#e2e6ec"
    palette.buttonText: cFieldTxt
    palette.highlight: "#2563eb"
    palette.highlightedText: "#ffffff"
    palette.mid: cBorder
    palette.dark: night ? "#0f1419" : "#dde2e8"

    ListModel {
        id: projModel
    }

    ListModel {
        id: chapterModel
    }

    function pathsFromDrop(drop) {
        var list = [];
        var i;
        for (i = 0; i < drop.urls.length; i++) {
            var u = drop.urls[i];
            var p = u.toLocalFile ? u.toLocalFile() : "";
            if (p.length === 0)
                p = String(u).replace(/^file:\/{3}/, "").replace(/^file:\/{2}/, "");
            if (p.length > 0)
                list.push(p);
        }
        return list;
    }

    component ToolBtn : Button {
        implicitHeight: 30
        hoverEnabled: true
        contentItem: Text {
            text: parent.text
            font.pixelSize: 13
            font.family: "Microsoft YaHei UI"
            color: root.night ? "#f8fafc" : "#0f172a"
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            implicitWidth: parent.implicitWidth
            implicitHeight: parent.implicitHeight
            radius: 4
            border.width: 1
            border.color: root.cBorder
            color: !parent.enabled ? (root.night ? "#1e293b" : "#cbd5e1") :
                                     parent.down ? (root.night ? "#475569" : "#94a3b8") :
                                     parent.hovered ? (root.night ? "#475569" : "#bfdbfe") :
                                     (root.night ? "#334155" : "#e2e8f0")
        }
    }

    component ToolBtnPrimary : Button {
        implicitHeight: 30
        hoverEnabled: true
        contentItem: Text {
            text: parent.text
            font.pixelSize: 13
            font.family: "Microsoft YaHei UI"
            font.bold: true
            color: "#ffffff"
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            implicitWidth: parent.implicitWidth
            implicitHeight: parent.implicitHeight
            radius: 4
            color: parent.down ? "#1d4ed8" : (parent.hovered ? "#3b82f6" : "#2563eb")
        }
    }

    component ToolBtnGhost : Button {
        implicitHeight: 30
        hoverEnabled: true
        contentItem: Text {
            text: parent.text
            font.pixelSize: 12
            font.family: "Microsoft YaHei UI"
            color: root.night ? "#e2e8f0" : "#334155"
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            implicitWidth: parent.implicitWidth
            implicitHeight: parent.implicitHeight
            radius: 4
            border.width: 1
            border.color: root.cBorder
            color: !parent.enabled ? (root.night ? "#1e293b" : "#e2e8f0") :
                   parent.hovered ? (root.night ? "#3d4f66" : "#e2e8f0") :
                   (root.night ? "#2a3648" : "#f1f5f9")
        }
    }

    component ToolCombo : ComboBox {
        implicitHeight: 30
        leftPadding: 8
        rightPadding: 28
        contentItem: Text {
            text: parent.displayText
            font.pixelSize: 13
            font.family: "Microsoft YaHei UI"
            color: root.cFieldTxt
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            color: root.cPanel
            border.color: root.cBorder
            border.width: 1
            radius: 4
        }
        indicator: Item {
            implicitWidth: 22
            implicitHeight: 22
            Text {
                anchors.centerIn: parent
                text: "▼"
                color: root.cLblBar
                font.pixelSize: 9
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8

        Item {
            id: toolBarBox
            Layout.fillWidth: true
            implicitHeight: toolFlow.implicitHeight

            Flow {
                id: toolFlow
                width: parent.width
                spacing: 8

                Label {
                    text: "当前工程"
                    color: cLblBar
                }
                Row {
                    spacing: 4
                    ToolCombo {
                        id: projectCombo
                        implicitWidth: 240
                        model: projModel
                        textRole: "title"
                    }
                    ToolBtn {
                        text: "删除工程"
                        ToolTip.visible: hovered
                        ToolTip.delay: 400
                        ToolTip.text: "删除当前选中工程（不可恢复）"
                        onClicked: backend.deleteCurrentProject()
                    }
                }

                ToolBtn {
                    text: "刷新列表"
                    onClicked: backend.refreshProjectList()
                }
                Rectangle {
                    width: 1
                    height: 24
                    color: cSep
                }
                Label {
                    text: "书名"
                    color: cLblBar
                }
                TextField {
                    id: titleField
                    width: 180
                    placeholderText: "请输入书名"
                    color: cFieldTxt
                    placeholderTextColor: cPh
                    selectByMouse: true
                    background: Rectangle {
                        implicitHeight: 32
                        color: cPanel
                        border.color: cBorder
                        radius: 4
                    }
                }
                ToolBtn {
                    text: "新建工程"
                    onClicked: backend.createProject(titleField.text)
                }
                ToolBtn {
                    text: "保存大纲"
                    onClicked: backend.saveOutline(outlineArea.text)
                }
                ToolBtn {
                    text: "导入章节…"
                    onClicked: backend.pickChapters()
                }
                ToolBtn {
                    text: "导入文件夹…"
                    onClicked: backend.pickChapterFolder()
                }
                Label {
                    text: "套餐"
                    color: cLblBar
                }
                ToolCombo {
                    id: pkgBox
                    implicitWidth: 130
                    model: ["仅大纲", "大纲+第1章", "黄金三章", "前五章", "前十章"]
                    readonly property var packages: ["outline_only", "outline_plus_chapter_1", "golden_three", "first_five", "first_ten"]
                    hoverEnabled: true
                    ToolTip.visible: hovered
                    ToolTip.delay: 400
                    ToolTip.text: "限定规则质检与 DeepSeek 扫描范围：仅大纲，或大纲加第1章、前三章、前五章、前十章正文。"
                }
                Label {
                    text: "扫描：" + pkgBox.displayText
                    color: cLblHint
                    font.pixelSize: 11
                }
                ToolBtnPrimary {
                    text: "规则质检"
                    onClicked: backend.runCheck(pkgBox.packages[pkgBox.currentIndex])
                }
                ToolBtn {
                    text: "DeepSeek 点评"
                    onClicked: backend.runLlmReview(pkgBox.packages[pkgBox.currentIndex])
                }
                ToolBtn {
                    text: "刷新工程"
                    onClicked: backend.refreshProject()
                }
                ToolBtnGhost {
                    text: "检测数据库"
                    onClicked: backend.pingServer()
                }
                ToolBtnGhost {
                    id: themeBtn
                    text: night ? "浅色模式" : "深色模式"
                    ToolTip.visible: themeBtn.hovered
                    ToolTip.delay: 300
                    ToolTip.text: "切换浅色/深色界面（设置会自动保存）"
                    onClicked: backend.toggleNightTheme()
                }
            }
        }

        Connections {
            target: projectCombo
            function onActivated() {
                if (projectCombo.currentIndex >= 0)
                    backend.switchProjectByIndex(projectCombo.currentIndex);
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            ColumnLayout {
                id: bodyColumn
                anchors.fill: parent
                spacing: 8

                Label {
                    id: statusLabel
                    text: "启动中…"
                    color: cStatus
                    font.pixelSize: 12
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }

                RowLayout {
                    id: statusHintRow
                    spacing: 6
                    Layout.fillWidth: true
                    ToolBtnGhost {
                        id: hintToggle
                        text: root.hintsExpanded ? "收起说明" : "展开说明"
                        onClicked: root.hintsExpanded = !root.hintsExpanded
                    }
                    Label {
                        id: shortHint
                        text: backend.projectId === "" ? "先新建或选择工程；工具栏会自动折行；右侧为主题切换。"
                                     : "规则质检与 DeepSeek 在右栏；底条可拖放导入。"
                        color: cLblHint
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
                Label {
                    visible: root.hintsExpanded
                    text: backend.projectId === "" ? "请先新建工程或从「当前工程」下拉框选择。左栏为章节列表 + Markdown 全文预览。"
                                 : "中间栏：规则质检（可滚轮浏览全文）→ DeepSeek 点评（紫色框）。下方横条可拖放导入。"
                    color: cLblHint
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 34
                    Rectangle {
                        anchors.fill: parent
                        radius: 4
                        color: night ? "#1e293b" : "#f1f5f9"
                        border.width: 1
                        border.color: cBorder
                    }
                    DropArea {
                        anchors.fill: parent
                        keys: ["text/uri-list"]
                        onEntered: function(drag) {
                            drag.acceptProposedAction();
                        }
                        onDropped: function(drop) {
                            var list = pathsFromDrop(drop);
                            if (list.length > 0)
                                backend.importDroppedPathsJson(JSON.stringify(list));
                        }
                    }
                }

                SplitView {
                    id: splitMain
                    orientation: Qt.Horizontal
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    SplitView {
                        id: splitLeftCol
                        orientation: Qt.Vertical
                        SplitView.minimumWidth: 300

                        ColumnLayout {
                            SplitView.minimumHeight: 200
                            spacing: 4
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Label {
                                text: "大纲（Markdown）"
                                color: cLblSec
                                font.pixelSize: 11
                            }
                            ScrollView {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                TextArea {
                                    id: outlineArea
                                    placeholderText: "编辑大纲，或使用工具栏「导入章节…」「导入文件夹…」、底部横条拖放…"
                                    placeholderTextColor: cPh
                                    wrapMode: TextEdit.Wrap
                                    selectByMouse: true
                                    color: cOutline
                                    font.family: "Microsoft YaHei UI"
                                    font.pixelSize: 13
                                    background: Rectangle {
                                        color: cPanel
                                        border.color: cBorder
                                        border.width: 1
                                        radius: 4
                                    }
                                }
                            }
                        }

                        ColumnLayout {
                            SplitView.preferredHeight: 200
                            SplitView.minimumHeight: 120
                            spacing: 4
                            Layout.fillWidth: true
                            Label {
                                text: "已导入章节（列表 · Markdown 预览）"
                                color: cLblSec
                                font.pixelSize: 11
                            }
                            RowLayout {
                                spacing: 8
                                Layout.fillWidth: true
                                SpinBox {
                                    id: delChapterSpin
                                    from: 1
                                    to: 9999
                                    value: 1
                                    editable: true
                                    implicitWidth: 120
                                    onValueChanged: {
                                        if (chapterList.currentIndex >= 0) {
                                            var cur = chapterModel.get(chapterList.currentIndex);
                                            if (cur && cur.chapter_no === value)
                                                return;
                                        }
                                        var j;
                                        for (j = 0; j < chapterModel.count; j++) {
                                            if (chapterModel.get(j).chapter_no === value) {
                                                chapterList.currentIndex = j;
                                                return;
                                            }
                                        }
                                    }
                                }
                                ToolBtn {
                                    text: "删除该章节"
                                    enabled: backend.projectId !== ""
                                    onClicked: backend.deleteChapterNumber(delChapterSpin.value)
                                }
                                Item {
                                    Layout.fillWidth: true
                                }
                            }
                            RowLayout {
                                spacing: 8
                                Layout.fillWidth: true
                                Layout.fillHeight: true

                                Rectangle {
                                    Layout.preferredWidth: 208
                                    Layout.minimumWidth: 160
                                    Layout.fillHeight: true
                                    radius: 4
                                    color: cPanel
                                    border.color: cBorder
                                    border.width: 1
                                    ListView {
                                        id: chapterList
                                        anchors.fill: parent
                                        anchors.margins: 2
                                        clip: true
                                        model: chapterModel
                                        boundsBehavior: Flickable.StopAtBounds
                                        ScrollBar.vertical: ScrollBar {}
                                        delegate: Rectangle {
                                            width: chapterList.width
                                            height: 64
                                            radius: 3
                                            color: chapterList.currentIndex === index ? (night ? "#334155" : "#dbeafe") : "transparent"
                                            border.width: chapterList.currentIndex === index ? 1 : 0
                                            border.color: cBorder
                                            MouseArea {
                                                anchors.fill: parent
                                                onClicked: chapterList.currentIndex = index
                                            }
                                            ColumnLayout {
                                                anchors.fill: parent
                                                anchors.margins: 6
                                                spacing: 2
                                                Label {
                                                    text: "第 " + model.chapter_no + " 章 · " + model.chars + " 字"
                                                    color: cLblSec
                                                    font.pixelSize: 10
                                                    Layout.fillWidth: true
                                                }
                                                Label {
                                                    text: model.title && model.title.length ? model.title : "（无标题）"
                                                    color: cFieldTxt
                                                    font.pixelSize: 12
                                                    wrapMode: Text.WordWrap
                                                    elide: Text.ElideRight
                                                    Layout.fillWidth: true
                                                }
                                            }
                                        }
                                        onCurrentIndexChanged: {
                                            if (currentIndex < 0)
                                                return;
                                            var row = chapterModel.get(currentIndex);
                                            if (row && delChapterSpin.value !== row.chapter_no)
                                                delChapterSpin.value = row.chapter_no;
                                        }
                                    }
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    radius: 4
                                    color: cPanel
                                    border.color: cBorder
                                    border.width: 1
                                    TextArea {
                                        id: chapterArea
                                        anchors.fill: parent
                                        anchors.margins: 1
                                        readOnly: true
                                        wrapMode: TextEdit.Wrap
                                        textFormat: TextEdit.MarkdownText
                                        text: ""
                                        selectByMouse: true
                                        color: cChapter
                                        font.family: "Microsoft YaHei UI"
                                        font.pixelSize: 12
                                        topPadding: 6
                                        bottomPadding: 8
                                        leftPadding: 8
                                        rightPadding: 8
                                        background: Rectangle {
                                            color: "transparent"
                                        }
                                    }
                                }
                            }
                        }
                    }

                    SplitView {
                        id: splitRightCol
                        orientation: Qt.Vertical
                        SplitView.minimumWidth: 340

                        ColumnLayout {
                            SplitView.minimumHeight: 180
                            spacing: 4
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Label {
                                text: "规则质检（按章节归类）"
                                color: cLblSec
                                font.pixelSize: 11
                            }
                            ScrollView {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                TextArea {
                                    id: reportReadableArea
                                    readOnly: true
                                    placeholderText: "点击「规则质检」后显示"
                                    placeholderTextColor: cPh
                                    wrapMode: TextEdit.Wrap
                                    selectByMouse: true
                                    color: cReport
                                    font.family: "Microsoft YaHei UI"
                                    font.pixelSize: 12
                                    background: Rectangle {
                                        color: cPanel
                                        border.color: cBorder
                                        border.width: 1
                                        radius: 4
                                    }
                                }
                            }
                        }

                        ColumnLayout {
                            SplitView.preferredHeight: 260
                            SplitView.minimumHeight: 140
                            spacing: 4
                            Layout.fillWidth: true
                            Label {
                                text: "DeepSeek 模型回复（内容在下面大方框内）"
                                color: cLblSec
                                font.pixelSize: 11
                                font.bold: true
                            }
                            Label {
                                text: "需环境变量 NOVEL_EDIT_DEEPSEEK_API_KEY；点工具栏「DeepSeek 点评」后，回复出现在下方。"
                                color: cLblHint
                                font.pixelSize: 10
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
                            ScrollView {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                TextArea {
                                    id: llmReviewArea
                                    readOnly: true
                                    placeholderText: "模型回复会出现在这里。若未配置 API Key，会先显示配置说明。"
                                    placeholderTextColor: cPh
                                    wrapMode: TextEdit.Wrap
                                    selectByMouse: true
                                    color: cLlm
                                    font.family: "Microsoft YaHei UI"
                                    font.pixelSize: 12
                                    background: Rectangle {
                                        color: cPanel
                                        border.color: night ? "#a78bfa" : "#7c3aed"
                                        border.width: 2
                                        radius: 4
                                    }
                                }
                            }
                        }
                    }
                }

                Label {
                    text: "工程概要"
                    color: cLblMeta
                    font.pixelSize: 11
                    Layout.topMargin: 4
                }
                ScrollView {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 84
                    TextArea {
                        id: metaArea
                        readOnly: true
                        placeholderText: "书名、大纲字数、章节数、工程 ID"
                        placeholderTextColor: cPh
                        wrapMode: TextEdit.Wrap
                        color: cMeta
                        font.family: "Microsoft YaHei UI"
                        font.pixelSize: 11
                        background: Rectangle {
                            color: cPanel
                            border.color: cBorder
                            border.width: 1
                            radius: 4
                        }
                    }
                }
            }
        }
    }

    Connections {
        target: splitMain
        function onWidthChanged() {
            if (root.mainSplitApplied || splitMain.width < 160)
                return;
            var r = uiSettings.mainLeftRatio;
            if (isNaN(r) || r < 0.18 || r > 0.82)
                r = 0.44;
            splitLeftCol.SplitView.preferredWidth = Math.floor(splitMain.width * r);
            root.mainSplitApplied = true;
        }
    }

    Connections {
        target: backend

        function onStatusChanged(msg) {
            statusLabel.text = msg;
        }

        function onProjectSummaryChanged(txt) {
            metaArea.text = txt;
        }

        function onChapterIndexChanged(txt) {
            chapterArea.text = txt;
        }

        function onChapterListJsonChanged(jsonStr) {
            chapterModel.clear();
            chapterList.currentIndex = -1;
            if (!jsonStr || jsonStr.length === 0)
                return;
            var arr = JSON.parse(jsonStr);
            var i;
            for (i = 0; i < arr.length; i++)
                chapterModel.append(arr[i]);
            if (chapterModel.count > 0) {
                chapterList.currentIndex = 0;
                delChapterSpin.value = chapterModel.get(0).chapter_no;
            } else {
                delChapterSpin.value = 1;
            }
        }

        function onReportReadableChanged(txt) {
            reportReadableArea.text = txt;
        }

        function onLlmReviewChanged(txt) {
            llmReviewArea.text = txt;
        }

        function onOutlineLoaded(txt) {
            outlineArea.text = txt;
        }

        function onProjectListJsonChanged(jsonStr) {
            projModel.clear();
            if (!jsonStr || jsonStr.length === 0)
                return;
            var arr = JSON.parse(jsonStr);
            var i;
            for (i = 0; i < arr.length; i++)
                projModel.append(arr[i]);
            projectCombo.currentIndex = backend.activeProjectIndex;
        }

        function onActiveProjectIndexChanged(idx) {
            if (idx >= 0 && idx < projectCombo.count)
                projectCombo.currentIndex = idx;
        }

        function onProjectTitleChanged(title) {
            titleField.text = title;
        }
    }
}
