from __future__ import annotations

import logging
import sqlite3
from typing import Annotated, Union

from fastapi import APIRouter, File, HTTPException, UploadFile

from novel_edit.api.deps import Conn
from novel_edit.api.schemas import CreateProjectBody, OutlineBody, RunCheckBody
from novel_edit.services.project_handlers import (
    ProjectNotFoundError,
    svc_create_project,
    svc_put_outline,
    svc_read_project,
    svc_run_checks,
    svc_upload_chapters,
)

logger = logging.getLogger(__name__)

api_router = APIRouter(prefix="/api")


@api_router.post("/projects", summary="新建工程", tags=["工程"])
def create_project(body: CreateProjectBody, conn: Conn):
    return svc_create_project(conn, body.title, body.qimao_category)


@api_router.get("/projects/{project_id}", summary="查询工程", tags=["工程"])
def read_project(project_id: str, conn: Conn):
    try:
        return svc_read_project(conn, project_id)
    except ProjectNotFoundError:
        raise HTTPException(404, "工程不存在") from None


@api_router.put("/projects/{project_id}/outline", summary="上传大纲", tags=["工程"])
def put_outline(project_id: str, body: OutlineBody, conn: Conn):
    try:
        return svc_put_outline(conn, project_id, body.raw_text)
    except ProjectNotFoundError:
        raise HTTPException(404, "工程不存在") from None


@api_router.post("/projects/{project_id}/chapters", summary="导入章节", tags=["工程"])
async def upload_chapters(
    project_id: str,
    conn: Conn,
    files: Annotated[
        Union[list[UploadFile], UploadFile],
        File(..., description="可多选"),
    ],
):
    """multipart 字段名须为 `files`；单文件时解析器可能给出单个 UploadFile。"""
    file_list: list[UploadFile] = files if isinstance(files, list) else [files]

    if not file_list:
        raise HTTPException(400, "未上传文件")

    items: list[tuple[str, bytes]] = []
    for uf in file_list:
        data = await uf.read()
        items.append((uf.filename or "chapter.txt", data))

    try:
        return svc_upload_chapters(conn, project_id, items)
    except ProjectNotFoundError:
        raise HTTPException(404, "工程不存在") from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except sqlite3.ProgrammingError as e:
        logger.exception("upload_chapters sqlite thread")
        raise HTTPException(
            status_code=503,
            detail=(
                "SQLite 线程限制：请结束旧 uvicorn 进程后重新启动 API，"
                "确保已加载 check_same_thread=False（当前代码 db.connect）。"
            ),
        ) from e
    except Exception as e:
        logger.exception("upload_chapters")
        raise HTTPException(status_code=500, detail=str(e)) from e


@api_router.post("/projects/{project_id}/run", summary="运行质检", tags=["质检"])
def run_check(project_id: str, body: RunCheckBody, conn: Conn):
    try:
        return svc_run_checks(conn, project_id, body.package.value)
    except ProjectNotFoundError:
        raise HTTPException(404, "工程不存在") from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
