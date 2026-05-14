from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from novel_edit.import_parse.chapters import (
    extract_chapter_no_from_name,
    parse_chapter_body,
)
from novel_edit.import_parse.text_encoding import decode_bytes

SKIP_DIR_NAMES = frozenset({".git", ".svn", "__pycache__", ".venv", "node_modules", ".idea"})
TEXT_SUFFIXES = frozenset({".md", ".txt"})

# 文件名含以下关键词视为大纲（不含章节号文件名）
_OUTLINE_NAME_RE = re.compile(
    r"(大纲|outline|提纲|纲要|剧情规划|分卷|内容简介|简介|设定|世界观)",
    re.IGNORECASE,
)


@dataclass
class DropScanResult:
    outline_text: str | None
    outline_label: str | None
    chapter_files: list[tuple[str, bytes]]
    skipped_names: list[str]


def _iter_text_files(roots: list[Path]) -> list[Path]:
    out: list[Path] = []
    for root in roots:
        if root.is_file():
            if root.suffix.lower() in TEXT_SUFFIXES:
                out.append(root.resolve())
            continue
        if root.is_dir():
            for p in root.rglob("*"):
                if not p.is_file():
                    continue
                if p.suffix.lower() not in TEXT_SUFFIXES:
                    continue
                if any(part in SKIP_DIR_NAMES for part in p.parts):
                    continue
                out.append(p.resolve())
    # 去重保持顺序
    seen: set[Path] = set()
    uniq: list[Path] = []
    for p in out:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq


def _is_outline_file(path: Path) -> bool:
    if extract_chapter_no_from_name(path.name):
        return False
    return bool(_OUTLINE_NAME_RE.search(path.name))


def _chapter_sort_key(path: Path, data: bytes) -> tuple[int, str]:
    no = extract_chapter_no_from_name(path.name)
    if no is not None:
        return (no, path.name)
    head = decode_bytes(data[:8192])
    inner_no, _ = parse_chapter_body(head)
    if inner_no is not None:
        return (inner_no, path.name)
    return (10**9, path.name)


def _outline_priority(path: Path) -> tuple[int, int]:
    """越小越优先：精确「大纲」> 含大纲 > 其它关键词。"""
    n = path.name.lower()
    if n in ("大纲.md", "大纲.txt"):
        return (0, -len(path.parts))
    if "大纲" in path.name:
        return (1, -len(path.parts))
    if _OUTLINE_NAME_RE.search(path.name):
        return (2, -len(path.parts))
    return (9, 0)


def scan_dropped_paths(local_paths: list[str]) -> DropScanResult:
    """
    从拖入的文件或文件夹中收集 .md/.txt，区分大纲与章节。
    章节：文件名或正文首行可解析「第N章」。
    """
    roots = [Path(p) for p in local_paths if p.strip()]
    roots = [r for r in roots if r.exists()]
    if not roots:
        return DropScanResult(None, None, [], [])

    all_files = _iter_text_files(roots)
    outline_candidates: list[Path] = []
    chapter_paths: list[Path] = []
    ambiguous: list[Path] = []

    for p in all_files:
        if _is_outline_file(p):
            outline_candidates.append(p)
            continue
        data = p.read_bytes()
        no_name = extract_chapter_no_from_name(p.name)
        head = decode_bytes(data[:8192])
        inner_no, _ = parse_chapter_body(head)
        if no_name is not None or inner_no is not None:
            chapter_paths.append(p)
        else:
            ambiguous.append(p)

    outline_text: str | None = None
    outline_label: str | None = None
    if outline_candidates:
        outline_candidates.sort(key=_outline_priority)
        pieces: list[str] = []
        labels: list[str] = []
        for p in outline_candidates:
            raw = p.read_bytes()
            pieces.append(decode_bytes(raw).strip())
            labels.append(p.name)
        outline_text = "\n\n---\n\n".join(x for x in pieces if x)
        outline_label = "、".join(labels[:5]) + ("…" if len(labels) > 5 else "")

    chapter_files: list[tuple[str, bytes]] = []
    path_data: dict[Path, bytes] = {p: p.read_bytes() for p in chapter_paths}
    sorted_paths = sorted(chapter_paths, key=lambda p: _chapter_sort_key(p, path_data[p]))
    for p in sorted_paths:
        chapter_files.append((p.name, path_data[p]))

    skipped = [p.name for p in ambiguous]

    return DropScanResult(
        outline_text=outline_text,
        outline_label=outline_label,
        chapter_files=chapter_files,
        skipped_names=skipped,
    )
