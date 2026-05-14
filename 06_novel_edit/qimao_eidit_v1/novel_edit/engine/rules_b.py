from __future__ import annotations

import re
import statistics
from novel_edit.engine.rules_a import Finding

AI_TRANSITION = (
    "然而",
    "因此",
    "值得注意的是",
    "总而言之",
    "不仅如此",
    "与此同时",
    "换句话说",
    "综上所述",
)


def run_ai_flavor_scan(text: str, chapter_no: int | None = None) -> list[Finding]:
    findings: list[Finding] = []
    loc = f"第{chapter_no}章" if chapter_no else "全文"
    for w in AI_TRANSITION:
        count = text.count(w)
        if count >= 2:
            findings.append(
                Finding(
                    rule_id="B2-AIWORD",
                    severity="yellow",
                    module="B",
                    message=f"AI 高频过渡词「{w}」出现 {count} 次",
                    evidence=w,
                    location=loc,
                )
            )

    sentences = re.split(r"(?<=[。！？])", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if len(sentences) >= 5:
        lens = [len(s) for s in sentences]
        try:
            var = statistics.pvariance(lens)
        except statistics.StatisticsError:
            var = 0.0
        if var < 80:
            findings.append(
                Finding(
                    rule_id="B1-VAR",
                    severity="yellow",
                    module="B",
                    message="句长波动偏低，行文可能偏「平铺」",
                    evidence=f"句长方差≈{var:.1f}",
                    location=loc,
                )
            )
    return findings
