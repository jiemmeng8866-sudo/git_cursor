"""从数据库拼装发给大模型的正文节选（控制长度）。"""
from __future__ import annotations

import sqlite3

from novel_edit.repository import get_outline, list_chapters


def build_deepseek_user_bundle(
    conn: sqlite3.Connection,
    project_id: str,
    package_label: str,
    *,
    max_outline_chars: int = 14000,
    max_chapter_chars: int = 5000,
    max_chapters: int = 20,
) -> str:
    outline = get_outline(conn, project_id)
    chs = list_chapters(conn, project_id)
    parts: list[str] = [
        f"【当前质检套餐】{package_label}\n",
        "【任务】请作为网络小说主编，从可读性、节奏、人设、对话、节奏钩子等方面给出修改意见；"
        "若文本过长请优先点评前半与关键问题。输出使用简体中文，分「大纲」「按章节」两部分。\n\n",
        "【大纲节选】\n",
        (outline or "（无）")[:max_outline_chars],
        "\n\n【正文节选】\n",
    ]
    for c in chs[:max_chapters]:
        body = (c.body or "")[:max_chapter_chars]
        parts.append(f"\n--- 第{c.chapter_no} 章 {c.title} ---\n{body}\n")
    if not chs:
        parts.append("（尚未导入章节）\n")
    return "".join(parts)
