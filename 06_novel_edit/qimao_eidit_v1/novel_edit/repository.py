from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any

from novel_edit.db import connect, init_schema, new_project_id


@dataclass
class ProjectRow:
    id: str
    title: str
    qimao_category: str
    created_at: str


@dataclass
class ChapterRow:
    id: int
    project_id: str
    chapter_no: int
    title: str
    body: str


def ensure_db(db_path: Any) -> sqlite3.Connection:
    conn = connect(db_path)
    init_schema(conn)
    return conn


def insert_project(conn: sqlite3.Connection, title: str, qimao_category: str = "") -> str:
    pid = new_project_id()
    conn.execute(
        "INSERT INTO projects (id, title, qimao_category) VALUES (?, ?, ?)",
        (pid, title, qimao_category),
    )
    conn.execute(
        "INSERT INTO outlines (project_id, raw_text) VALUES (?, ?)",
        (pid, ""),
    )
    return pid


def upsert_outline(conn: sqlite3.Connection, project_id: str, raw_text: str) -> None:
    conn.execute(
        """UPDATE outlines SET raw_text = ?, updated_at = datetime('now') WHERE project_id = ?""",
        (raw_text, project_id),
    )


def upsert_chapter(conn: sqlite3.Connection, project_id: str, chapter_no: int, title: str, body: str) -> None:
    conn.execute(
        """
        INSERT INTO chapters (project_id, chapter_no, title, body)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(project_id, chapter_no) DO UPDATE SET
            title = excluded.title,
            body = excluded.body
        """,
        (project_id, chapter_no, title, body),
    )


def list_projects(conn: sqlite3.Connection) -> list[ProjectRow]:
    rows = conn.execute(
        "SELECT * FROM projects ORDER BY datetime(created_at) DESC",
    ).fetchall()
    return [
        ProjectRow(
            id=r["id"],
            title=r["title"],
            qimao_category=r["qimao_category"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


def get_project(conn: sqlite3.Connection, project_id: str) -> ProjectRow | None:
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not row:
        return None
    return ProjectRow(id=row["id"], title=row["title"], qimao_category=row["qimao_category"], created_at=row["created_at"])


def get_outline(conn: sqlite3.Connection, project_id: str) -> str:
    row = conn.execute("SELECT raw_text FROM outlines WHERE project_id = ?", (project_id,)).fetchone()
    return row["raw_text"] if row else ""


def list_chapters(conn: sqlite3.Connection, project_id: str) -> list[ChapterRow]:
    rows = conn.execute(
        "SELECT * FROM chapters WHERE project_id = ? ORDER BY chapter_no",
        (project_id,),
    ).fetchall()
    return [
        ChapterRow(
            id=r["id"],
            project_id=r["project_id"],
            chapter_no=r["chapter_no"],
            title=r["title"],
            body=r["body"],
        )
        for r in rows
    ]


def delete_project(conn: sqlite3.Connection, project_id: str) -> bool:
    cur = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    return cur.rowcount > 0


def delete_chapter(conn: sqlite3.Connection, project_id: str, chapter_no: int) -> bool:
    cur = conn.execute(
        "DELETE FROM chapters WHERE project_id = ? AND chapter_no = ?",
        (project_id, chapter_no),
    )
    return cur.rowcount > 0


def get_chapters_up_to(conn: sqlite3.Connection, project_id: str, max_chapter: int) -> list[ChapterRow]:
    rows = conn.execute(
        "SELECT * FROM chapters WHERE project_id = ? AND chapter_no <= ? ORDER BY chapter_no",
        (project_id, max_chapter),
    ).fetchall()
    return [
        ChapterRow(
            id=r["id"],
            project_id=r["project_id"],
            chapter_no=r["chapter_no"],
            title=r["title"],
            body=r["body"],
        )
        for r in rows
    ]
