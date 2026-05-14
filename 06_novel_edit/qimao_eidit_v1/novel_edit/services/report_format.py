"""将合并质检报告格式化为界面可读文本。"""
from __future__ import annotations

import re

_LOC_CHAPTER = re.compile(r"第\s*(\d+)\s*章")


def _group_key_and_title(location: str) -> tuple[int, str]:
    """返回 (排序键, 分组标题)。大纲类在前用 -1；未识别章节号放最后。"""
    raw = location or ""
    m = _LOC_CHAPTER.search(raw)
    if m:
        n = int(m.group(1))
        return (n, f"第 {n} 章")
    if any(k in raw for k in ("大纲", "梗概", "卷首", "书名", "设定")):
        return (-1, "大纲 / 结构")
    if "outline" in raw.lower():
        return (-1, "大纲 / 结构")
    return (10**9, "其它 / 未标注位置")


def _sort_group_keys(keys: list[int]) -> list[int]:
    """大纲(-1)优先，其次按章节号，其它最后。"""

    def sk(k: int) -> tuple[int, int]:
        if k == -1:
            return (0, 0)
        if k == 10**9:
            return (2, 0)
        return (1, k)

    return sorted(keys, key=sk)


def format_merge_report_readable(rep: dict) -> str:
    lines: list[str] = []
    rid = rep.get("report_id", "")
    pkg = rep.get("package", "")
    stds = rep.get("standards_enabled") or []
    lines.append(f"【报告】{rid}")
    lines.append(f"套餐：{pkg}")
    lines.append(f"启用标准：{', '.join(stds) if stds else '（无）'}")
    lines.append("")

    hits = rep.get("criteria_hits") or []
    n_red = sum(1 for h in hits if h.get("severity") == "red")
    n_yellow = sum(1 for h in hits if h.get("severity") == "yellow")
    n_green = sum(1 for h in hits if h.get("severity") == "green")
    lines.append(f"规则命中：共 {len(hits)} 条（红 {n_red} / 黄 {n_yellow} / 绿 {n_green}）")
    lines.append("")

    sug = rep.get("modification_suggestions") or []
    lines.append("———— 修改意见（按章节归类）————")
    if not sug:
        lines.append("（暂无修改建议：可能未触发规则，或当前套餐/大纲·章节范围较窄。）")
    else:
        groups: dict[int, list[dict]] = {}
        titles: dict[int, str] = {}
        for s in sug:
            k, title = _group_key_and_title(s.get("location") or "")
            groups.setdefault(k, []).append(s)
            titles[k] = title

        for k in _sort_group_keys(list(groups.keys())):
            lines.append("")
            lines.append(f"═══ {titles[k]} ═══")
            for i, s in enumerate(groups[k], 1):
                sev = s.get("severity", "")
                loc = s.get("location", "")
                rule_id = s.get("rule_id", "")
                direction = s.get("direction", "")
                ev = s.get("evidence", "")
                lines.append(f"  {i}. [{sev}] {rule_id} ｜ {loc}")
                lines.append(f"     建议：{direction}")
                if ev:
                    lines.append(f"     片段：{ev}")

    return "\n".join(lines).rstrip()


def format_project_summary(data: dict) -> str:
    nch = len(data.get("chapters") or [])
    oc = data.get("outline_chars", 0)
    return "\n".join(
        [
            f"书名：{data.get('title', '')}",
            f"大纲字数：{oc} ｜ 已导入章节：{nch} 篇",
            f"工程 ID：{data.get('id', '')}",
        ]
    )


def format_chapter_index(data: dict) -> str:
    chs = sorted(data.get("chapters") or [], key=lambda c: c["chapter_no"])
    if not chs:
        return "（尚未导入章节。请使用工具栏「导入章节…」「导入文件夹…」或底部拖放条。）"
    lines: list[str] = []
    for c in chs:
        t = (c.get("title") or "").strip() or "（无标题）"
        lines.append(f"第 {c['chapter_no']} 章　{t}　{c.get('chars', 0)} 字")
    return "\n".join(lines)


def format_chapters_preview_markdown(chapters: list) -> str:
    """章节 Markdown 预览正文，供 Qt Text.MarkdownText 渲染。"""
    if not chapters:
        return "（尚未导入章节。请使用工具栏「导入章节…」「导入文件夹…」或底部拖放条。）"
    blocks: list[str] = []
    for c in sorted(chapters, key=lambda x: x.chapter_no):
        title = (c.title or "").strip() or "（无标题）"
        body = (c.body or "").strip()
        head = f"## 第 {c.chapter_no} 章　{title}"
        meta = f"*字数约 {len(c.body or '')}*"
        if body:
            blocks.append(f"{head}\n\n{meta}\n\n{body}")
        else:
            blocks.append(f"{head}\n\n{meta}\n\n*（正文为空）*")
    return "\n\n---\n\n".join(blocks)
