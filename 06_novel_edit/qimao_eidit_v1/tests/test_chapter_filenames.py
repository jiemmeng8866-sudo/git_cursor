"""章节号文件名扩展规则（序号_第一章 等）。"""

from novel_edit.import_parse.chapters import extract_chapter_no_from_name, load_chapter_from_bytes


def test_leading_index_chapter_filename():
    assert extract_chapter_no_from_name("01_第一章_百岁亡魂.md") == 1
    assert extract_chapter_no_from_name("12_第十二章_x.txt") == 12


def test_chinese_chapter_in_filename():
    assert extract_chapter_no_from_name("第一章_开端.md") == 1
    assert extract_chapter_no_from_name("第十一章_转折.md") == 11


def test_year_prefixed_not_used_as_chapter():
    """文件名前四位若为年份，不按序号章节解析。"""
    assert extract_chapter_no_from_name("2024_第一章_番外.md") == 1


def test_load_chapter_01_first_pattern():
    body = "# 标题\n\n正文"
    data = body.encode("utf-8")
    cf = load_chapter_from_bytes("03_第三章_测试.md", data)
    assert cf.chapter_no == 3
