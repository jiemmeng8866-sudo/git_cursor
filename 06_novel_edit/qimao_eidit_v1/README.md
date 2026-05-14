# 七猫预审 — Phase 1（本地 API）

依据 `prd.md`：**SQLite 工程**、**大纲/章节导入**、**规则质检 H+A+B+C**、**首批套餐编排**、**合并报告 JSON**。

## 环境

Python 3.11+

```powershell
cd d:\00_cursor\06_novel_edit\qimao_eidit_v1
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
```

### 桌面客户端（PySide6 + QML）

**一键启动（Windows）：** 在 **`qimao_eidit_v1`**（本目录）双击 **`start-workbench.bat`**，或执行 **`python launch_desktop.py`** —— 直接打开工作台；**大纲 / 章节 / 质检均在进程内直连 SQLite**，默认数据库见下文 `NOVEL_EDIT_DB`，**无需单独启动 uvicorn**。

也可只启图形界面：

```powershell
pip install -r requirements-desktop.txt
python -m novel_edit.client
```

请在 **`qimao_eidit_v1` 目录**下执行上述命令（或将该目录设为 IDE 工作目录）。

- **当前工程**：下拉框列出本地库中的工程，可切换；与书籍「书名」字段同步。
- **浅色 / 深色**：工具栏右侧切换白天 / 夜间主题，保存在本机 Qt 设置（组织名 `novel_edit`，应用名 `Workbench`，键 `appearance/night_theme`）。
- **规则质检 / DeepSeek 点评**：右侧分两栏展示规则引擎（按章节归类）与模型点评；可在工程根目录复制 **`env.local.example`** 为 **`env.local`**，填入 **`NOVEL_EDIT_DEEPSEEK_API_KEY`**（启动时会自动加载）；亦可改用系统环境变量 **`NOVEL_EDIT_DEEPSEEK_API_KEY`**，可选 `NOVEL_EDIT_DEEPSEEK_BASE_URL`（默认 `https://api.deepseek.com`）、`NOVEL_EDIT_DEEPSEEK_MODEL`（默认 `deepseek-chat`）。未设置的环境变量才会被 `env.local` 写入。
- 功能：新建工程、编辑/保存大纲、多选导入章节、选套餐并运行质检、查看报告与工程信息。
- **拖放**：将**文件夹或若干文件**拖到主区域，自动扫描 `.md`/`.txt` 并识别大纲与章节。

### 可选：仅 HTTP 调试（Swagger）

本地开发与脚本联调时，可单独启动 FastAPI（与桌面端共用同一数据库文件及业务逻辑）：

```powershell
python -m uvicorn novel_edit.api.app:app --host 127.0.0.1 --port 8765
```

- 根路径 `/` 重定向至 Swagger。
- 健康检查：`GET http://127.0.0.1:8765/health`
- Swagger：`http://127.0.0.1:8765/docs`

数据库默认：`data/novel_edit.db`（可用环境变量 `NOVEL_EDIT_DB` 指向其它路径）。

## API 摘要

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/projects` | 新建工程 `{"title","qimao_category"}` |
| GET | `/api/projects/{id}` | 工程信息与章节列表 |
| PUT | `/api/projects/{id}/outline` | 上传大纲 `{"raw_text"}` |
| POST | `/api/projects/{id}/chapters` | multipart 上传多个 `.md`/`.txt`，文件名需含 `第N章` |
| POST | `/api/projects/{id}/run` | 质检 `{"package":"outline_only"|...}` |

`package`：`outline_only`、`outline_plus_chapter_1`、`golden_three`、`first_five`、`first_ten`。

响应即 PRD **合并报告**：`standards_enabled`、`criteria_hits`、`modification_suggestions`、`report_id`。

## 测试

```powershell
pytest tests -q
```

## 下一步（增强）

- 报告结构化视图（按红/黄/绿分类）、雷达图、拖拽大纲区域。
- 可选：把本地 API 嵌入同一进程（去掉 HTTP），便于离线打包。
