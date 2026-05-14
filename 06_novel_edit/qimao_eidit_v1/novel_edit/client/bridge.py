from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Property, QSettings, QTimer, Signal, Slot
from PySide6.QtWidgets import QFileDialog, QMessageBox, QApplication

from novel_edit.config import get_db_path
from novel_edit.llm.deepseek_client import deepseek_chat_completion
from novel_edit.llm.review_bundle import build_deepseek_user_bundle
from novel_edit.repository import (
    delete_chapter,
    delete_project,
    ensure_db,
    get_outline,
    get_project,
    list_chapters,
    list_projects,
)
from novel_edit.services.report_format import (
    format_chapters_preview_markdown,
    format_merge_report_readable,
    format_project_summary,
)
from novel_edit.services.project_handlers import (
    ProjectNotFoundError,
    svc_create_project,
    svc_put_outline,
    svc_read_project,
    svc_run_checks,
    svc_upload_chapters,
)

_PACKAGE_LABELS: dict[str, str] = {
    "outline_only": "仅大纲",
    "outline_plus_chapter_1": "大纲+第1章",
    "golden_three": "黄金三章",
    "first_five": "前五章",
    "first_ten": "前十章",
}

_LLM_SYSTEM = (
    "你是中国网络小说驻站资深主编，熟悉起点/番茄/七猫等平台的爽点与毒点。"
    "请根据用户给出的大纲与章节节选，输出可执行的修改建议；"
    "不要编造未出现的情节；语言简洁、分点列出，避免空泛客套话。"
)


class ApiBridge(QObject):
    """内置 SQLite + 规则引擎；槽函数在工作线程中执行，通过信号回写 UI。"""

    statusChanged = Signal(str)
    projectSummaryChanged = Signal(str)
    chapterIndexChanged = Signal(str)
    chapterListJsonChanged = Signal(str)
    reportReadableChanged = Signal(str)
    llmReviewChanged = Signal(str)
    projectListJsonChanged = Signal(str)
    projectTitleChanged = Signal(str)
    activeProjectIndexChanged = Signal(int)
    serverOkChanged = Signal(bool)
    projectIdChanged = Signal(str)
    outlineLoaded = Signal(str)
    nightThemeChanged = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._project_id = ""
        self._project_order_ids: list[str] = []
        self._active_project_index: int = -1
        self._settings = QSettings("novel_edit", "Workbench")
        self._night_theme: bool = bool(self._settings.value("appearance/night_theme", True))

    @staticmethod
    def _open_db() -> sqlite3.Connection:
        return ensure_db(get_db_path())

    def get_projectId(self) -> str:
        return self._project_id

    projectId = Property(str, get_projectId, notify=projectIdChanged)

    def get_activeProjectIndex(self) -> int:
        return self._active_project_index

    activeProjectIndex = Property(int, get_activeProjectIndex, notify=activeProjectIndexChanged)

    def get_nightTheme(self) -> bool:
        return self._night_theme

    def set_nightTheme(self, value: object) -> None:
        v = bool(value)
        if self._night_theme == v:
            return
        self._night_theme = v
        self._settings.setValue("appearance/night_theme", v)
        self.nightThemeChanged.emit(v)

    nightTheme = Property(bool, get_nightTheme, set_nightTheme, notify=nightThemeChanged)

    @Slot()
    def toggleNightTheme(self) -> None:
        self.set_nightTheme(not self._night_theme)

    def _emit_empty_views(self) -> None:
        self.projectSummaryChanged.emit("")
        self.chapterIndexChanged.emit("")
        self.chapterListJsonChanged.emit("[]")

    def _emit_chapter_views(self, conn: sqlite3.Connection, project_id: str) -> None:
        chs = list_chapters(conn, project_id)
        self.chapterIndexChanged.emit(format_chapters_preview_markdown(chs))
        rows = [
            {
                "chapter_no": c.chapter_no,
                "title": (c.title or "").strip() or "（无标题）",
                "chars": len(c.body or ""),
            }
            for c in chs
        ]
        self.chapterListJsonChanged.emit(json.dumps(rows, ensure_ascii=False))

    @Slot()
    def pingServer(self) -> None:
        def work() -> None:
            try:
                conn = self._open_db()
                try:
                    conn.execute("SELECT 1").fetchone()
                finally:
                    conn.close()
                self.serverOkChanged.emit(True)
                self.statusChanged.emit("内置数据库就绪")
            except Exception as e:
                self.serverOkChanged.emit(False)
                self.statusChanged.emit(f"数据库不可用：{e}")

        threading.Thread(target=work, daemon=True).start()

    @Slot()
    def refreshProjectList(self) -> None:
        def work() -> None:
            conn = self._open_db()
            try:
                rows = list_projects(conn)
                self._project_order_ids = [r.id for r in rows]
                payload = [{"id": r.id, "title": (r.title or "（无标题）")} for r in rows]
                self.projectListJsonChanged.emit(json.dumps(payload, ensure_ascii=False))
                try:
                    idx = self._project_order_ids.index(self._project_id) if self._project_id else -1
                except ValueError:
                    idx = -1
                if self._active_project_index != idx:
                    self._active_project_index = idx
                    self.activeProjectIndexChanged.emit(idx)
            except Exception as e:
                self.statusChanged.emit(f"工程列表失败：{e}")
            finally:
                conn.close()

        threading.Thread(target=work, daemon=True).start()

    @Slot(int)
    def switchProjectByIndex(self, index: int) -> None:
        if index < 0 or index >= len(self._project_order_ids):
            return
        self.switchProject(self._project_order_ids[index])

    @Slot(str)
    def switchProject(self, project_id: str) -> None:
        pid = (project_id or "").strip()
        if not pid:
            return

        def work() -> None:
            conn = self._open_db()
            try:
                if pid == self._project_id:
                    return
                p = get_project(conn, pid)
                if not p:
                    self.statusChanged.emit("切换失败：工程不存在")
                    return
                outline = get_outline(conn, pid)
                self._project_id = pid
                self.projectIdChanged.emit(pid)
                self.outlineLoaded.emit(outline)
                self.projectTitleChanged.emit(p.title)
                self.reportReadableChanged.emit("")
                self.llmReviewChanged.emit("")
                try:
                    idx = self._project_order_ids.index(pid)
                except ValueError:
                    idx = -1
                if self._active_project_index != idx:
                    self._active_project_index = idx
                    self.activeProjectIndexChanged.emit(idx)
                data = svc_read_project(conn, pid)
                self.projectSummaryChanged.emit(format_project_summary(data))
                self._emit_chapter_views(conn, pid)
                self.statusChanged.emit(f"已切换到工程：{p.title}")
            except Exception as e:
                self.statusChanged.emit(f"切换失败：{e}")
            finally:
                conn.close()

        threading.Thread(target=work, daemon=True).start()

    @Slot(str)
    def createProject(self, title: str) -> None:
        title = (title or "").strip()
        if not title:
            self.statusChanged.emit("请先填写书名")
            return

        def work() -> None:
            conn = self._open_db()
            try:
                data = svc_create_project(conn, title, "")
                self._project_id = data["id"]
                self.projectIdChanged.emit(self._project_id)
                self.projectTitleChanged.emit(title)
                self.reportReadableChanged.emit("")
                self.llmReviewChanged.emit("")
                self.statusChanged.emit(f"工程已创建（id 前缀 {self._project_id[:8]}…）")
                self.refreshProject()
                self.refreshProjectList()
            except Exception as e:
                self.statusChanged.emit(f"创建失败：{e}")
            finally:
                conn.close()

        threading.Thread(target=work, daemon=True).start()

    @Slot(str)
    def saveOutline(self, text: str) -> None:
        if not self._project_id:
            self.statusChanged.emit("请先新建工程")
            return

        def work() -> None:
            conn = self._open_db()
            try:
                out = svc_put_outline(conn, self._project_id, text)
                self.statusChanged.emit(f"大纲已保存（{out['chars']} 字）")
                self.refreshProject()
            except ProjectNotFoundError:
                self.statusChanged.emit("保存失败：工程不存在")
            except Exception as e:
                self.statusChanged.emit(f"保存失败：{e}")
            finally:
                conn.close()

        threading.Thread(target=work, daemon=True).start()

    @staticmethod
    def _dialog_parent() -> object | None:
        w = QApplication.activeWindow()
        if w is not None:
            return w
        for tw in QApplication.topLevelWidgets():
            if tw.isVisible():
                return tw
        return None

    @Slot()
    def pickChapters(self) -> None:
        # 从 QML Menu 触发时若立刻弹 QFileDialog，菜单未完全关闭会导致 Win 上对话框不出现
        QTimer.singleShot(50, self._pick_chapters_deferred)

    def _pick_chapters_deferred(self) -> None:
        if not self._project_id:
            self.statusChanged.emit("请先新建工程")
            return

        paths, _ = QFileDialog.getOpenFileNames(
            self._dialog_parent(),
            "选择章节文件（可多选）",
            "",
            "Markdown / 文本 (*.md *.txt);;所有文件 (*.*)",
        )
        if not paths:
            return

        def work() -> None:
            conn = self._open_db()
            try:
                items = [(Path(p).name, Path(p).read_bytes()) for p in paths]
                data = svc_upload_chapters(conn, self._project_id, items)
                n = len(data.get("imported", []))
                self.statusChanged.emit(f"已导入 {n} 个章节文件")
                self.refreshProject()
            except ProjectNotFoundError:
                self.statusChanged.emit("导入失败：工程不存在")
            except ValueError as e:
                self.statusChanged.emit(f"导入失败：{e}")
            except sqlite3.ProgrammingError as e:
                self.statusChanged.emit(f"导入失败（SQLite）：{e}")
            except Exception as e:
                self.statusChanged.emit(f"导入失败：{e}")
            finally:
                conn.close()

        threading.Thread(target=work, daemon=True).start()

    @Slot()
    def pickChapterFolder(self) -> None:
        QTimer.singleShot(50, self._pick_folder_deferred)

    def _pick_folder_deferred(self) -> None:
        if not self._project_id:
            self.statusChanged.emit("请先新建工程")
            return
        folder = QFileDialog.getExistingDirectory(
            self._dialog_parent(),
            "选择含章节或大纲的文件夹",
            "",
        )
        if not folder:
            return
        self.importDroppedPathsJson(json.dumps([folder]))

    @Slot(str)
    def importDroppedPathsJson(self, paths_json: str) -> None:
        if not self._project_id:
            self.statusChanged.emit("请先新建工程，再将文件夹拖到下方区域")
            return
        try:
            paths: list[str] = json.loads(paths_json or "[]")
        except json.JSONDecodeError:
            self.statusChanged.emit("拖放路径解析失败")
            return
        paths = [p for p in paths if isinstance(p, str) and p.strip()]
        if not paths:
            return

        def work() -> None:
            from novel_edit.import_parse.drop_scan import scan_dropped_paths

            try:
                scan = scan_dropped_paths(paths)
            except OSError as e:
                self.statusChanged.emit(f"读取路径失败：{e}")
                return

            parts: list[str] = []
            conn = self._open_db()

            try:
                if scan.outline_text:
                    self.outlineLoaded.emit(scan.outline_text)
                    try:
                        svc_put_outline(conn, self._project_id, scan.outline_text)
                        label = scan.outline_label or "大纲"
                        parts.append(f"大纲已写入（{label}）")
                    except ProjectNotFoundError:
                        self.statusChanged.emit("大纲保存失败：工程不存在")
                        return
                    except Exception as e:
                        self.statusChanged.emit(f"大纲保存失败：{e}")
                        return

                if scan.chapter_files:
                    try:
                        data = svc_upload_chapters(conn, self._project_id, list(scan.chapter_files))
                        parts.append(f"章节已导入 {len(data.get('imported', []))} 个")
                    except ProjectNotFoundError:
                        self.statusChanged.emit("章节导入失败：工程不存在")
                        return
                    except ValueError as e:
                        self.statusChanged.emit(f"章节导入失败：{e}")
                        return
                    except sqlite3.ProgrammingError as e:
                        self.statusChanged.emit(f"章节导入失败（SQLite）：{e}")
                        return
                    except Exception as e:
                        self.statusChanged.emit(f"章节导入失败：{e}")
                        return

                if scan.skipped_names:
                    tail = "、".join(scan.skipped_names[:12])
                    if len(scan.skipped_names) > 12:
                        tail += "…"
                    parts.append(f"未识别文件 {len(scan.skipped_names)} 个（{tail}）")

                if not parts:
                    self.statusChanged.emit(
                        "未识别到大纲或章节：大纲文件名请含「大纲/outline/提纲」等；"
                        "章节文件名或正文首行请含「第N章」"
                    )
                    return

                self.statusChanged.emit("；".join(parts))
                self.refreshProject()
            finally:
                conn.close()

        threading.Thread(target=work, daemon=True).start()

    @Slot(str)
    def runCheck(self, package: str) -> None:
        if not self._project_id:
            self.statusChanged.emit("请先新建工程")
            return
        pkg = (package or "").strip()
        if not pkg:
            self.statusChanged.emit("请选择质检套餐")
            return

        def work() -> None:
            conn = self._open_db()
            try:
                rep = svc_run_checks(conn, self._project_id, pkg)
                self.reportReadableChanged.emit(format_merge_report_readable(rep))
                self.statusChanged.emit("质检完成")
            except ProjectNotFoundError:
                self.statusChanged.emit("质检失败：工程不存在")
            except ValueError as e:
                self.statusChanged.emit(f"质检失败：{e}")
            except Exception as e:
                self.statusChanged.emit(f"质检失败：{e}")
            finally:
                conn.close()

        threading.Thread(target=work, daemon=True).start()

    @Slot(str)
    def runLlmReview(self, package_key: str) -> None:
        """DeepSeek 点评（需环境变量 NOVEL_EDIT_DEEPSEEK_API_KEY）。"""
        if not self._project_id:
            self.statusChanged.emit("请先新建工程")
            return
        pkg_key = (package_key or "").strip() or "outline_only"
        label = _PACKAGE_LABELS.get(pkg_key, pkg_key)

        def work() -> None:
            conn = self._open_db()
            try:
                bundle = build_deepseek_user_bundle(conn, self._project_id, label)
                self.statusChanged.emit("正在请求 DeepSeek，请稍候…")
                text = deepseek_chat_completion(bundle, system_prompt=_LLM_SYSTEM)
                self.llmReviewChanged.emit(text)
                self.statusChanged.emit("DeepSeek 点评完成")
            except ValueError as e:
                self.llmReviewChanged.emit(
                    f"（未调用模型）{e}\n\n"
                    "请在系统环境变量中设置 NOVEL_EDIT_DEEPSEEK_API_KEY，"
                    "可选 NOVEL_EDIT_DEEPSEEK_BASE_URL（默认 https://api.deepseek.com）、"
                    "NOVEL_EDIT_DEEPSEEK_MODEL（默认 deepseek-chat）。"
                )
                self.statusChanged.emit("模型质检未执行（见右侧说明）")
            except Exception as e:
                self.llmReviewChanged.emit(f"模型调用失败：{e}")
                self.statusChanged.emit("DeepSeek 调用失败")
            finally:
                conn.close()

        threading.Thread(target=work, daemon=True).start()

    @Slot()
    def deleteCurrentProject(self) -> None:
        if not self._project_id:
            self.statusChanged.emit("没有可删除的工程")
            return
        ret = QMessageBox.question(
            None,
            "删除工程",
            "确定删除当前工程？大纲与章节将一并删除，不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ret != QMessageBox.StandardButton.Yes:
            return

        def work() -> None:
            pid = self._project_id
            conn = self._open_db()
            try:
                if not delete_project(conn, pid):
                    conn.rollback()
                    self.statusChanged.emit("删除失败：工程不存在")
                    return
                conn.commit()
                self._project_id = ""
                self.projectIdChanged.emit("")
                self.projectTitleChanged.emit("")
                self.outlineLoaded.emit("")
                self.reportReadableChanged.emit("")
                self.llmReviewChanged.emit("")
                self._emit_empty_views()
                self.statusChanged.emit("工程已删除")
                self.refreshProjectList()
            except Exception as e:
                self.statusChanged.emit(f"删除失败：{e}")
            finally:
                conn.close()

        threading.Thread(target=work, daemon=True).start()

    @Slot(int)
    def deleteChapterNumber(self, chapter_no: int) -> None:
        if not self._project_id:
            self.statusChanged.emit("请先新建工程")
            return
        n = int(chapter_no)
        if n < 1:
            self.statusChanged.emit("章节号无效")
            return

        def work() -> None:
            conn = self._open_db()
            try:
                if not delete_chapter(conn, self._project_id, n):
                    conn.rollback()
                    self.statusChanged.emit(f"未找到第 {n} 章")
                    return
                conn.commit()
                self.refreshProject()
                self.statusChanged.emit(f"已删除第 {n} 章")
            except Exception as e:
                self.statusChanged.emit(f"删除章节失败：{e}")
            finally:
                conn.close()

        threading.Thread(target=work, daemon=True).start()

    @Slot()
    def refreshProject(self) -> None:
        if not self._project_id:
            self._emit_empty_views()
            return

        pid = self._project_id

        def work() -> None:
            conn = self._open_db()
            try:
                data = svc_read_project(conn, pid)
                self.projectSummaryChanged.emit(format_project_summary(data))
                self._emit_chapter_views(conn, pid)
            except ProjectNotFoundError:
                self.statusChanged.emit("刷新失败：工程不存在")
                self._emit_empty_views()
            except Exception as e:
                self.statusChanged.emit(f"刷新工程失败：{e}")
            finally:
                conn.close()

        threading.Thread(target=work, daemon=True).start()
