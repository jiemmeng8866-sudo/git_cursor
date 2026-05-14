from __future__ import annotations

from novel_edit.engine.rules_a import Finding
from novel_edit.import_parse.outline import parse_outline_markdown

# 七猫子类 → 期望在大纲/标题中出现的关键词（占位，Phase 2 接风格罗盘）
CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "都市异能": ("异能", "觉醒", "灵气", "都市", "系统"),
    "都市言情": ("婚", "总裁", "离婚", "爱你", "豪门"),
    "玄幻": ("修炼", "境界", "宗门", "灵气", "大陆"),
    "科幻": ("星", "舰", "文明", "末日", "基因"),
}

_HOOK_HINTS = ("钩子", "冲突", "反转", "爽点", "打脸", "高潮")
_STRUCTURE_HINTS = ("起", "承", "转", "合", "第一卷", "卷一")


def run_outline_scan(outline_text: str, qimao_category: str) -> list[Finding]:
    findings: list[Finding] = []
    refs, headings = parse_outline_markdown(outline_text)

    if len(refs) < 3 and len(headings) < 3:
        findings.append(
            Finding(
                rule_id="H1-LAYER",
                severity="yellow",
                module="H",
                message="大纲层级较单薄：解析到的章节/标题线索少于 3 条，建议细化卷章结构",
                evidence=outline_text[:200].replace("\n", " ") + ("…" if len(outline_text) > 200 else ""),
                location="大纲",
            )
        )

    kw = CATEGORY_KEYWORDS.get(qimao_category, ())
    blob = outline_text
    if kw and not any(k in blob for k in kw):
        findings.append(
            Finding(
                rule_id="H2-CAT",
                severity="yellow",
                module="H",
                message=f"大纲与所选子类「{qimao_category}」关键词重合度低（占位词表）",
                evidence=",".join(kw),
                location="大纲",
            )
        )

    low = outline_text.lower()
    if not any(h in outline_text for h in _HOOK_HINTS) and not any(
        s in outline_text for s in _STRUCTURE_HINTS
    ):
        findings.append(
            Finding(
                rule_id="H3-GOLD",
                severity="yellow",
                module="H",
                message="大纲前段未显式标注钩子/冲突/爽点或卷结构节点（启发式）",
                evidence=outline_text[:160].replace("\n", " ") + ("…" if len(outline_text) > 160 else ""),
                location="大纲前段",
            )
        )

    return findings


def run_outline_chapter_consistency(
    outline_text: str,
    chapter_titles: list[tuple[int, str]],
) -> list[Finding]:
    findings: list[Finding] = []
    blob = outline_text
    for no, title in chapter_titles:
        if title and len(title) > 1 and title not in blob and title[:4] not in blob:
            findings.append(
                Finding(
                    rule_id="H4-DEV",
                    severity="yellow",
                    module="H",
                    message=f"第{no}章标题与大纲文本字面重合度低，可能偏纲",
                    evidence=title[:60],
                    location=f"第{no}章",
                )
            )
    return findings
