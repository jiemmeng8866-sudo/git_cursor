# 批量文件管理专家 V6.0 — 代码架构总览

## 1. 整体概览

| 维度 | 说明 |
|------|------|
| **语言** | Python 3 |
| **GUI 框架** | PyQt6 |
| **总行数** | ~1317 行（单文件） |
| **核心功能** | 批量重命名 / 精细截取 / 音视频标签重命名 / 多级目录去套娃 / 安全与日志 |
| **布局** | 双栏：左 = 规则面板（QScrollArea），右 = 文件表格 + 执行栏 |
| **主题** | 支持 明/暗 双主题切换（QSettings 持久化） |
| **线程模型** | 3 个 QThread 子类处理 I/O 密集操作，主线程只负责 UI 响应 |

---

## 2. 代码分层架构

```
┌─────────────────────────────────────────────────────┐
│  入口层 (1313-1317)                                  │
│  QApplication → MainWindow → show() → exec()        │
├─────────────────────────────────────────────────────┤
│  主窗口 MainWindow (344-1311)                        │
│  ┌───────────────┐ ┌───────────────┐ ┌────────────┐ │
│  │ 主题系统       │ │ UI 构建       │ │ 业务调度   │ │
│  │ COLORS / _c()  │ │ init_ui()     │ │ execute_*  │ │
│  │ _stylesheet()  │ │ 5 个面板工厂  │ │ add_files   │ │
│  │ _apply_theme() │ │ _create_*     │ │ undo_*     │ │
│  └───────────────┘ └───────────────┘ └────────────┘ │
├─────────────────────────────────────────────────────┤
│  业务逻辑层 (235-313)                                 │
│  FileRecord — 文件数据模型                            │
│  RenameEngine — 纯函数规则引擎 (不与硬盘交互)           │
├─────────────────────────────────────────────────────┤
│  自定义组件层 (170-340)                                │
│  ModernStepper — 带主题色的步进器                     │
│  FileDropTable — 支持拖放的 QTableWidget              │
├─────────────────────────────────────────────────────┤
│  后台线程层 (31-166)                                   │
│  FileLoaderThread — 递归扫描 + 批量 emit              │
│  RenameWorker   — 逐文件 rename + 进度报告            │
│  FlattenWorker  — shutil.move + 重名防覆盖            │
└─────────────────────────────────────────────────────┘
```

---

## 3. 核心类详解

### 3.1 后台工作线程（解决 UI 假死）

| 类名 | 文件位置 | 功能 | 关键信号 |
|------|---------|------|---------|
| `FileLoaderThread` | :31-80 | 递归扫描文件/文件夹，每 50 条批量 emit | `batch_loaded`, `progress_updated`, `finished_loading` |
| `RenameWorker` | :82-127 | 遍历待处理列表逐文件 rename，支持测试模式 | `item_processed`, `log_msg`, `finished_task` |
| `FlattenWorker` | :129-166 | 遍历源目录所有嵌套文件，`shutil.move` 到目标目录 | `log_msg`, `finished_task` |

### 3.2 自定义 UI 组件

| 组件 | 文件位置 | 功能 |
|------|---------|------|
| `ModernStepper` | :170-233 | 带 +/- 按钮和主题色的数值步进器，emit `valueChanged` |
| `FileDropTable` | :317-340 | 继承 QTableWidget，支持从系统资源管理器拖入文件/文件夹 |

### 3.3 数据模型 & 规则引擎

| 类名 | 文件位置 | 功能 |
|------|---------|------|
| `FileRecord` | :236-262 | 单文件数据模型：原始路径、名称、扩展名、大小、修改时间、媒体信息(tinytag)、冲突标记 |
| `RenameEngine` | :264-313 | **纯函数**规则引擎，根据规则字典生成新文件名。规则链：媒体模板 → 查找替换 → 删开头/结尾 → 大小写 → 前后缀 → 序号 → 清理非法字符 → 覆写扩展名 |

### 3.4 主窗口 MainWindow

| 方法 | 文件位置 | 功能 |
|------|---------|------|
| `__init__` | :398-419 | 窗口属性、状态变量初始化、主题加载、UI 构建 |
| `_c(token)` | :422-424 | 获取当前主题下指定 token 的颜色值 |
| `_build_stylesheet()` | :426-494 | 生成全局 Qt CSS 样式表，所有颜色通过 token 动态注入 |
| `_apply_theme()` | :496-533 | 重新注入 CSS + 逐控件刷新 inline style |
| `_toggle_theme()` | :535-541 | 切换明暗主题，持久化到 QSettings |
| `add_shadow()` | :543-550 | 给 CardPanel 添加主题感知阴影 |
| `init_ui()` | :553-694 | 构建完整双栏 UI（左规则面板 + 右文件表格） |
| `create_basic_rule_panel()` | :713-785 | 面板1：查找替换 + 前后缀 + 序号 + 大小写/扩展名 |
| `create_cut_rule_panel()` | :787-805 | 面板2：删除开头/结尾 N 字符 |
| `create_media_panel()` | :807-839 | 面板3：音视频 ID3 标签格式化文件名 |
| `create_flatten_panel()` | :841-883 | 面板4：多级目录去套娃平铺 |
| `create_security_log_panel()` | :885-914 | 面板5：非法字符清理 + 操作日志 |
| `_start_async_file_loading()` | :1007-1015 | 启动 FileLoaderThread 后台扫描 |
| `trigger_preview_update()` | :1058-1060 | **300ms 防抖触发器** |
| `_do_update_preview()` | :1062-1091 | 遍历所有 FileRecord，用 RenameEngine 计算新文件名，检测冲突 |
| `render_table_optimized()` | :1097-1174 | **差量渲染**：只更新有变化的单元格，不重建整表 |
| `execute_rename()` | :1207-1239 | 批量重命名入口：校验冲突 → 确认弹窗 → 启动 RenameWorker |
| `execute_flatten()` | :1287-1305 | 去套娃入口：校验目录 → 确认弹窗 → 启动 FlattenWorker |

---

## 4. 数据流

```
用户操作
  │
  ├─ 拖入/选择文件 ──→ _start_async_file_loading()
  │                      └─→ FileLoaderThread(QThread)
  │                            └─→ batch_loaded signal → file_records.append()
  │                            └─→ finished_loading → trigger_preview_update()
  │
  ├─ 修改规则控件 ──→ trigger_preview_update() [300ms debounce]
  │                    └─→ _do_update_preview()
  │                          ├─ get_current_rules() → dict
  │                          ├─ RenameEngine.apply_rules() → new_fullname
  │                          ├─ 冲突检测（文件系统 + 内存池）
  │                          └─ render_table_optimized() → 差量更新表格
  │
  └─ 点击执行按钮 ──→ execute_rename()
                       └─→ RenameWorker(QThread)
                             ├─ log_msg → txt_logs 追加
                             ├─ item_processed → 更新表格状态列
                             └─ finished_task → 保存撤销栈 + 刷新预览
```

---

## 5. 主题系统

### 5.1 颜色 Token 体系

`COLORS` 字典包含 `light` 和 `dark` 两套配色，共 **40+ 语义 token**，分为以下类别：

| 类别 | Token 示例 |
|------|-----------|
| 背景 | `bg_main`, `bg_card`, `bg_input`, `bg_group`, `bg_hover`, `bg_selected`, `bg_header` |
| 文本 | `text_primary`, `text_secondary`, `text_muted`, `text_placeholder`, `text_brand` |
| 边框 | `border_main`, `border_hover`, `border_focus`, `border_tag` |
| 品牌色 | `brand`, `brand_hover`, `brand_disabled`, `brand_light` |
| 成功色 | `success`, `success_hover`, `success_disabled`, `btn_success_text` |
| 危险色 | `danger_text`, `danger_bg`, `danger_border`, `danger_hover_bg` |
| 特殊 | `scrollbar`, `scrollbar_hover`, `stepper_text`, `shadow_alpha` |

### 5.2 主题刷新机制

```
_toggle_theme()
  ├─ _theme = "light" ⇄ "dark"
  ├─ QSettings.setValue("theme", ...)  ← 持久化
  ├─ _apply_theme()
  │    ├─ setStyleSheet(_build_stylesheet())  ← 全局 CSS 重注
  │    ├─ ModernStepper.set_theme_colors()    ← 步进器独立刷新
  │    └─ 逐个 inline-styled QLabel 刷新       ← 部分控件不受全局 CSS 控制
  └─ trigger_preview_update()
```

### 5.3 CardPanel 样式

```css
QFrame#CardPanel {
  background-color: {bg_card};
  border-radius: 14px;
  border: 1px solid {border_main};
}
```

左右主卡片、去套娃确认按钮容器均使用 `objectName="CardPanel"` 自动获得此样式。

---

## 6. 预览防抖与差量渲染

- **防抖**：任何规则控件变化 → `preview_timer.start(300)` → 300ms 内只触发一次 `_do_update_preview`
- **差量渲染**：`render_table_optimized()` 使用 `blockSignals(True/False)` 批量更新，仅创建缺失的 QTableWidgetItem，已有 item 只 setText — 避免全表重建造成的闪烁
- **冲突检测**：
  1. 新文件名是否与文件系统已有文件冲突
  2. 新文件名是否在本次改名池内重复（内存检测）

---

## 7. 撤销系统

```
execute_rename() 真实写入成功
  └─→ history_stack.append([(new_path, old_path), ...])

undo_last_action()
  ├─ history_stack.pop() 取最近一次
  ├─ os.rename(current_path, old_path) 逐文件逆向
  └─ 完成后清空 file_records（安全策略）
```

- 仅真实写入（非测试模式）才入栈
- 撤销后强制清空列表，防止数据不一致

---

## 8. 关键设计决策

| 决策 | 原因 |
|------|------|
| 单文件架构 | 快速原型迭代，避免过早拆分模块 |
| QThread 而非 asyncio | PyQt6 原生支持，信号槽自然衔接 UI |
| 批处理 emit（50条/批） | 平衡主线程负担和用户感知速度 |
| 纯函数引擎 RenameEngine | UI 与逻辑解耦，方便测试和替换规则 |
| 300ms 防抖 | 避免用户快速输入时触发大量规则计算 |
| 差量渲染 | 1000+ 文件时避免全表重建卡顿 |
| inline style 双轨制 | 全局 CSS 处理大部分控件，部分控件（QLabel 颜色、QTextEdit 背景）需单独 setStyleSheet |
| 主题 token 化 | 40+ 命名颜色替代硬编码色值，新增主题只需追加字典 key |
