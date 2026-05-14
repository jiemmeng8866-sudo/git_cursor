from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from novel_edit.import_parse.text_encoding import decode_bytes


@dataclass
class ChapterFile:
    chapter_no: int
    title: str
    body: str
    source_name: str


# 常见：第12章、chapter 3
_FILENAME_RE = re.compile(
    r"(?:第\s*(\d+)\s*章)|(?:chapter\s*(\d+))",
    re.IGNORECASE,
)
# 01_第一章_标题.md、12_第12章_x.md（序号_第…章）
_LEADING_INDEX_CHAPTER = re.compile(r"^(\d{1,4})_第", re.UNICODE)
# 文件名中含「第一章」「第十一章」等（无阿拉伯数字时）
_CN_CHAPTER_IN_NAME = re.compile(r"第\s*([一二三四五六七八九十百千〇零两]+)\s*章")

_FIRST_LINE_ARABIC = re.compile(
    r"^\s*(?:第\s*(\d+)\s*章)\s*[\.．、:\：\-—]?\s*(.*)$",
)
_FIRST_LINE_CN = re.compile(
    r"^\s*第\s*([一二三四五六七八九十百千〇零两]+)\s*章\s*[\.．、:\：\-—]?\s*(.*)$",
)


def parse_cn_chapter_token(s: str) -> int | None:
    """解析「一」～「九十九」级章节序号（用于文件名/首行）。"""
    s = s.strip().replace("〇", "零").replace("两", "二")
    if not s:
        return None
    if s.isdigit():
        return int(s)
    digit = "零一二三四五六七八九"
    if s == "十":
        return 10
    if len(s) == 1 and s in digit and s != "零":
        return digit.index(s)
    # 十一～十九
    if len(s) == 2 and s[0] == "十" and s[1] in digit:
        return 10 + digit.index(s[1])
    # 二十、三十…九十
    if len(s) == 2 and s[1] == "十" and s[0] in digit and s[0] != "零":
        return digit.index(s[0]) * 10
    # 二十一～九十九
    if len(s) == 3 and s[1] == "十" and s[0] in digit and s[2] in digit:
        return digit.index(s[0]) * 10 + digit.index(s[2])
    # 一百以内「十」结尾已在上方覆盖；百章以上书名较少见，略
    return None


def normalize_upload_filename(name: str) -> str:
    """去掉路径、NFKC 规范化（全角数字/符号），避免浏览器/系统传入奇怪形态。"""
    n = unicodedata.normalize("NFKC", (name or "").strip())
    return Path(n.replace("\\", "/")).name


def extract_chapter_no_from_name(name: str) -> int | None:
    norm = normalize_upload_filename(name)
    stem = Path(norm).stem
    m = _LEADING_INDEX_CHAPTER.match(stem)
    if m:
        n = int(m.group(1))
        # 避免把 2024_第一章 里的年份当成章节号
        if not (1900 <= n <= 2100):
            return n
    m = _FILENAME_RE.search(norm)
    if m:
        return int(next(g for g in m.groups() if g is not None))
    m = _CN_CHAPTER_IN_NAME.search(stem)
    if m:
        n = parse_cn_chapter_token(m.group(1))
        if n is not None:
            return n
    return None


def parse_chapter_body(first_lines: str) -> tuple[int | None, str]:
    """正文首行：第N章（阿拉伯或中文）。"""
    first = first_lines.splitlines()[0] if first_lines.strip() else ""
    m = _FIRST_LINE_ARABIC.match(first)
    if m:
        return int(m.group(1)), (m.group(2) or "").strip()
    m = _FIRST_LINE_CN.match(first)
    if m:
        n = parse_cn_chapter_token(m.group(1))
        if n is not None:
            return n, (m.group(2) or "").strip()
    return None, ""


def load_chapter_from_bytes(filename: str, data: bytes) -> ChapterFile:
    filename = normalize_upload_filename(filename)
    text = decode_bytes(data)
    no = extract_chapter_no_from_name(filename)
    inner_no, inner_title = parse_chapter_body(text)
    if no is None and inner_no is not None:
        no = inner_no
    if no is None:
        raise ValueError(f"无法从文件名或正文首行解析章节号: {filename}")

    lines = text.splitlines()
    title = inner_title
    if not title and lines:
        title = Path(filename).stem
    body = "\n".join(lines[1:] if inner_no is not None else lines).strip()
    return ChapterFile(chapter_no=no, title=title, body=body, source_name=filename)
