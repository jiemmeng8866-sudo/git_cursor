from __future__ import annotations

from enum import Enum
from typing import Any

import sqlite3

from novel_edit.engine.rules_a import Finding, run_format_scan, run_sensitive_scan
from novel_edit.engine.rules_b import run_ai_flavor_scan
from novel_edit.engine.rules_c import run_pacing_scan
from novel_edit.engine.rules_h import run_outline_chapter_consistency, run_outline_scan
from novel_edit.repository import get_outline, get_project, list_chapters


class CheckPackage(str, Enum):
    outline_only = "outline_only"
    outline_plus_chapter_1 = "outline_plus_chapter_1"
    golden_three = "golden_three"
    first_five = "first_five"
    first_ten = "first_ten"


def package_max_chapter(pkg: CheckPackage) -> int | None:
    if pkg == CheckPackage.outline_only:
        return None
    if pkg == CheckPackage.outline_plus_chapter_1:
        return 1
    if pkg == CheckPackage.golden_three:
        return 3
    if pkg == CheckPackage.first_five:
        return 5
    if pkg == CheckPackage.first_ten:
        return 10
    return None


def enabled_standards(pkg: CheckPackage, has_outline: bool, max_ch: int | None) -> list[str]:
    std = []
    if has_outline:
        std.extend(["H1", "H2", "H3", "H4"])
    if max_ch:
        std.extend(["A1", "A2", "B1", "B2", "C1", "C4"])
    return std


def run_checks(
    conn: sqlite3.Connection,
    project_id: str,
    pkg: CheckPackage,
) -> dict[str, Any]:
    proj = get_project(conn, project_id)
    if not proj:
        raise ValueError("project not found")
    outline_text = get_outline(conn, project_id)
    max_ch = package_max_chapter(pkg)

    findings: list[Finding] = []

    if outline_text.strip():
        findings.extend(run_outline_scan(outline_text, proj.qimao_category))

    chapters = list_chapters(conn, project_id)
    if max_ch is not None:
        chapters = [c for c in chapters if c.chapter_no <= max_ch]

    if outline_text.strip() and chapters:
        findings.extend(
            run_outline_chapter_consistency(outline_text, [(c.chapter_no, c.title) for c in chapters])
        )

    for ch in chapters:
        body = ch.body
        findings.extend(run_sensitive_scan(body, ch.chapter_no))
        findings.extend(run_format_scan(body, ch.chapter_no))
        findings.extend(run_ai_flavor_scan(body, ch.chapter_no))
        findings.extend(
            run_pacing_scan(
                body,
                ch.chapter_no,
                is_first_chapter=(ch.chapter_no == 1),
            )
        )

    hits = [
        {
            "rule_id": f.rule_id,
            "severity": f.severity,
            "module": f.module,
            "message": f.message,
            "evidence": f.evidence,
            "location": f.location,
        }
        for f in findings
    ]

    hits_sorted = sorted(
        hits,
        key=lambda x: ({"red": 0, "yellow": 1, "green": 2}[x["severity"]], x["location"]),
    )

    suggestions = [
        {
            "rule_id": h["rule_id"],
            "severity": h["severity"],
            "location": h["location"],
            "direction": h["message"],
            "evidence": h["evidence"],
        }
        for h in hits_sorted
    ]

    report_id = f"rpt-{project_id[:8]}-{pkg.value}"

    merge_report = {
        "report_id": report_id,
        "project_id": project_id,
        "package": pkg.value,
        "standards_enabled": enabled_standards(pkg, bool(outline_text.strip()), max_ch),
        "criteria_hits": hits_sorted,
        "modification_suggestions": suggestions,
        "threshold_source": "builtin_phase1",
    }
    return merge_report
