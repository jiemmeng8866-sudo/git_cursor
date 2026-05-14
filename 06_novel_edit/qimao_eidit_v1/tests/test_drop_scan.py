from pathlib import Path

from novel_edit.import_parse.drop_scan import scan_dropped_paths


def test_scan_folder_outline_and_chapters(tmp_path: Path):
    root = tmp_path / "novel"
    root.mkdir()
    (root / "大纲.md").write_text("# 总纲\n卷一：开局\n", encoding="utf-8")
    (root / "第2章_反转.md").write_text("第2章 反转\n\n正文\n", encoding="utf-8")

    r = scan_dropped_paths([str(root)])
    assert r.outline_text and "总纲" in r.outline_text
    assert len(r.chapter_files) == 1
    assert r.chapter_files[0][0].endswith(".md")


def test_scan_skips_non_chapter(tmp_path: Path):
    (tmp_path / "笔记.txt").write_text("随便记点东西", encoding="utf-8")
    r = scan_dropped_paths([str(tmp_path / "笔记.txt")])
    assert not r.outline_text
    assert not r.chapter_files
    assert len(r.skipped_names) >= 1
