from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from typing import Literal

Severity = Literal["red", "yellow", "green"]


@dataclass
class Finding:
    rule_id: str
    severity: Severity
    module: str
    message: str
    evidence: str
    location: str


# 演示级敏感词；上线需替换为三级库 + AC 自动机
DEFAULT_SENSITIVE = {"赌博", "吸毒", "色情", "法轮功"}


def run_sensitive_scan(text: str, chapter_no: int | None = None) -> list[Finding]:
    findings: list[Finding] = []
    loc = f"第{chapter_no}章" if chapter_no else "全文"
    for w in DEFAULT_SENSITIVE:
        if w in text:
            idx = text.index(w)
            snippet = text[max(0, idx - 10) : idx + len(w) + 10].replace("\n", " ")
            findings.append(
                Finding(
                    rule_id="A1-SENS",
                    severity="red",
                    module="A",
                    message=f"命中敏感词表：{w}",
                    evidence=snippet,
                    location=loc,
                )
            )
    return findings


_LONG_PARA_CHARS = 420


def run_format_scan(text: str, chapter_no: int | None = None) -> list[Finding]:
    findings: list[Finding] = []
    loc = f"第{chapter_no}章" if chapter_no else "全文"
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    for i, p in enumerate(paras):
        if len(p) > _LONG_PARA_CHARS:
            findings.append(
                Finding(
                    rule_id="A2-PARA",
                    severity="yellow",
                    module="A",
                    message=f"段落过长（{len(p)} 字），建议拆段以利移动端阅读",
                    evidence=p[:80] + ("…" if len(p) > 80 else ""),
                    location=f"{loc} 段{i + 1}",
                )
            )
    return findings
