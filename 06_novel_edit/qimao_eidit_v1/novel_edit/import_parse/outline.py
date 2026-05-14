from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class OutlineChapterRef:
    """大纲里解析出的章节标题线索（启发式）。"""

    title: str
    line_hint: int


_CHAPTER_LINE_RE = re.compile(
    r"^\s*(?:第\s*(\d+)\s*章|第(\d+)\s*节|chapter\s*(\d+))\s*[\.．、:\：\-—]?\s*(.*)$",
    re.IGNORECASE,
)


def parse_outline_markdown(text: str) -> tuple[list[OutlineChapterRef], list[str]]:
    """从 Markdown / 纯文本大纲中提取章节线索与二级标题。"""
    lines = text.splitlines()
    refs: list[OutlineChapterRef] = []
    headings: list[str] = []

    for idx, line in enumerate(lines):
        s = line.strip()
        if s.startswith("#"):
            inner = s.lstrip("#").strip()
            if inner:
                headings.append(inner)
        m = _CHAPTER_LINE_RE.match(line)
        if m:
            num = next(g for g in m.groups()[:3] if g is not None)
            tail = (m.group(4) or "").strip()
            title = tail or f"第{num}章"
            refs.append(OutlineChapterRef(title=title, line_hint=idx + 1))

    if not refs and headings:
        for i, h in enumerate(headings[:200]):
            refs.append(OutlineChapterRef(title=h, line_hint=i + 1))

    return refs, headings
