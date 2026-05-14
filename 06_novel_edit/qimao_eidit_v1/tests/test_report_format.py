from types import SimpleNamespace

from novel_edit.services.report_format import (
    format_chapter_index,
    format_chapters_preview_markdown,
    format_merge_report_readable,
    format_project_summary,
)


def test_format_merge_report_readable_lists_suggestions():
    rep = {
        "report_id": "rpt-test",
        "package": "outline_only",
        "standards_enabled": ["H1"],
        "criteria_hits": [{"severity": "yellow", "rule_id": "H1", "location": "大纲"}],
        "modification_suggestions": [
            {
                "severity": "yellow",
                "rule_id": "H1",
                "location": "大纲§1",
                "direction": "补充冲突设计",
                "evidence": "…",
            }
        ],
    }
    txt = format_merge_report_readable(rep)
    assert "按章节归类" in txt or "大纲" in txt
    assert "H1" in txt
    assert "补充冲突" in txt


def test_format_merge_report_groups_by_chapter():
    rep = {
        "report_id": "x",
        "package": "first_ten",
        "standards_enabled": ["C1"],
        "criteria_hits": [],
        "modification_suggestions": [
            {"severity": "yellow", "rule_id": "A", "location": "第3章 中段", "direction": "改1", "evidence": ""},
            {"severity": "red", "rule_id": "B", "location": "第3章 末", "direction": "改2", "evidence": ""},
            {"severity": "yellow", "rule_id": "H", "location": "大纲 冲突", "direction": "改3", "evidence": ""},
        ],
    }
    txt = format_merge_report_readable(rep)
    assert "第 3 章" in txt
    assert "改1" in txt and "改2" in txt
    assert "大纲" in txt or "结构" in txt


def test_format_chapter_index():
    data = {
        "chapters": [
            {"chapter_no": 2, "title": "bb", "chars": 10},
            {"chapter_no": 1, "title": "aa", "chars": 20},
        ]
    }
    txt = format_chapter_index(data)
    assert "第 1 章" in txt and "aa" in txt
    assert "第 2 章" in txt


def test_format_project_summary():
    s = format_project_summary(
        {"title": "T", "qimao_category": "都市", "outline_chars": 100, "id": "uuid", "chapters": [{}]}
    )
    assert "T" in s and "100" in s and "uuid" in s


def test_format_chapters_preview_markdown():
    chs = [
        SimpleNamespace(chapter_no=2, title="B", body="第二 **粗体**"),
        SimpleNamespace(chapter_no=1, title="A", body=""),
    ]
    md = format_chapters_preview_markdown(chs)
    assert "## 第 1 章" in md and "## 第 2 章" in md
    assert "**粗体**" in md
    assert "---" in md
