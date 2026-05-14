"""工程 / 大纲 / 章节 / 质检：供 FastAPI 路由与桌面客户端共用（无 HTTP 依赖）。"""
from __future__ import annotations

import sqlite3

from novel_edit.engine.orchestrator import CheckPackage, run_checks
from novel_edit.import_parse.chapters import load_chapter_from_bytes
from novel_edit.repository import (
    get_outline,
    get_project,
    insert_project,
    list_chapters,
    upsert_chapter,
    upsert_outline,
)


class ProjectNotFoundError(LookupError):
    """工程不存在。"""


def svc_create_project(conn: sqlite3.Connection, title: str, qimao_category: str) -> dict:
    pid = insert_project(conn, title, qimao_category)
    conn.commit()
    return {"id": pid, "title": title, "qimao_category": qimao_category}


def svc_read_project(conn: sqlite3.Connection, project_id: str) -> dict:
    p = get_project(conn, project_id)
    if not p:
        raise ProjectNotFoundError("工程不存在")
    chs = list_chapters(conn, project_id)
    return {
        "id": p.id,
        "title": p.title,
        "qimao_category": p.qimao_category,
        "created_at": p.created_at,
        "outline_chars": len(get_outline(conn, project_id)),
        "chapters": [{"chapter_no": c.chapter_no, "title": c.title, "chars": len(c.body)} for c in chs],
    }


def svc_put_outline(conn: sqlite3.Connection, project_id: str, raw_text: str) -> dict:
    p = get_project(conn, project_id)
    if not p:
        raise ProjectNotFoundError("工程不存在")
    upsert_outline(conn, project_id, raw_text)
    conn.commit()
    return {"ok": True, "chars": len(raw_text)}


def svc_upload_chapters(
    conn: sqlite3.Connection,
    project_id: str,
    items: list[tuple[str, bytes]],
) -> dict:
    """items: (filename, raw_bytes)"""
    p = get_project(conn, project_id)
    if not p:
        raise ProjectNotFoundError("工程不存在")
    if not items:
        raise ValueError("未上传文件")
    imported: list[dict] = []
    for filename, data in items:
        cf = load_chapter_from_bytes(filename, data)
        upsert_chapter(conn, project_id, cf.chapter_no, cf.title, cf.body)
        imported.append({"chapter_no": cf.chapter_no, "title": cf.title, "source": cf.source_name})
    conn.commit()
    return {"ok": True, "imported": imported}


def svc_run_checks(conn: sqlite3.Connection, project_id: str, package: str) -> dict:
    p = get_project(conn, project_id)
    if not p:
        raise ProjectNotFoundError("工程不存在")
    try:
        pkg = CheckPackage(package)
    except ValueError as e:
        raise ValueError(f"未知套餐：{package!r}") from e
    return run_checks(conn, project_id, pkg)
