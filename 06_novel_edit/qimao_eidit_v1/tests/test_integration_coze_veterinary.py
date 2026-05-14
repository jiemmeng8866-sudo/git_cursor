"""用仓库内《全村就我一个兽医》样例文件夹做端到端校验（存在则跑）。"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from novel_edit.import_parse.drop_scan import scan_dropped_paths
from novel_edit.repository import ensure_db
from novel_edit.services.project_handlers import (
    svc_create_project,
    svc_put_outline,
    svc_run_checks,
    svc_upload_chapters,
)

_COZE_VET = (
    Path(__file__).resolve().parents[2]
    / "02_1_coze_novel"
    / "03_全村就我一个兽医"
)


@pytest.mark.skipif(not _COZE_VET.is_dir(), reason="coze veterinary sample folder not in workspace")
def test_scan_import_run_first_ten(tmp_path):
    os.environ["NOVEL_EDIT_DB"] = str(tmp_path / "e2e.db")

    scan = scan_dropped_paths([str(_COZE_VET)])
    assert scan.outline_text and len(scan.outline_text) > 100
    assert len(scan.chapter_files) == 10
    assert not scan.skipped_names

    conn = ensure_db(Path(os.environ["NOVEL_EDIT_DB"]))
    try:
        pid = svc_create_project(conn, "兽医 E2E", "都市")["id"]
        svc_put_outline(conn, pid, scan.outline_text)
        imp = svc_upload_chapters(conn, pid, scan.chapter_files)
        assert len(imp["imported"]) == 10
        rep = svc_run_checks(conn, pid, "first_ten")
        assert rep["package"] == "first_ten"
        assert "criteria_hits" in rep and "modification_suggestions" in rep
    finally:
        conn.close()
