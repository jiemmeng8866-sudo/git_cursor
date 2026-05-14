from __future__ import annotations

import re

from novel_edit.engine.rules_a import Finding

# 开篇冲突 / 悬念线索（启发式，可配置）
_OPEN_HOOK_WORDS = (
    "死",
    "杀",
    "血",
    "尸",
    "报警",
    "离婚",
    "破产",
    "穿越",
    "重生",
    "系统",
    "离婚协议",
    "分手",
    "阴谋",
)
_CLIFF_ENDINGS = ("？", "……", "吗", "呢", "！」", "——")


def run_pacing_scan(
    text: str,
    chapter_no: int,
    is_first_chapter: bool,
    opening_chars: int = 600,
) -> list[Finding]:
    findings: list[Finding] = []
    loc = f"第{chapter_no}章"
    tail = text[-220:] if len(text) >= 220 else text

    if not any(e in tail for e in _CLIFF_ENDINGS):
        findings.append(
            Finding(
                rule_id="C1-CLIFF",
                severity="yellow",
                module="C",
                message="章末悬念/收尾张力偏弱（未检测到常见卡点标点或疑问语气）",
                evidence=tail[-40:].replace("\n", " "),
                location=loc + " 章末",
            )
        )

    if is_first_chapter:
        head = text[:opening_chars]
        if not any(k in head for k in _OPEN_HOOK_WORDS):
            findings.append(
                Finding(
                    rule_id="C4-OPEN",
                    severity="yellow",
                    module="C",
                    message=f"开篇前 {opening_chars} 字内未检测到强冲突/题材显性线索（启发式词表）",
                    evidence=head[:120].replace("\n", " ") + ("…" if len(head) > 120 else ""),
                    location=loc + " 开篇",
                )
            )
    return findings
