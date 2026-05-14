"""章节 multipart 上传（async 路由 + SQLite 同连接跨线程场景）。"""

import pytest
from fastapi.testclient import TestClient

from novel_edit.api.app import create_app
from novel_edit.api.deps import get_conn
from novel_edit.repository import ensure_db


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "db.sqlite"

    def override_conn():
        conn = ensure_db(db_path)
        try:
            yield conn
        finally:
            conn.close()

    app = create_app()
    app.dependency_overrides[get_conn] = override_conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_upload_chapters_multipart(client: TestClient):
    r = client.post("/api/projects", json={"title": "百年道途", "qimao_category": "都市异能"})
    assert r.status_code == 200
    pid = r.json()["id"]

    body = "第1章 序幕\n\n正文一行。"
    r2 = client.post(
        f"/api/projects/{pid}/chapters",
        files=[("files", ("第1章.md", body.encode("utf-8")))],
    )
    assert r2.status_code == 200, r2.text
    data = r2.json()
    assert data["ok"] is True
    assert len(data["imported"]) == 1

    r3 = client.get(f"/api/projects/{pid}")
    assert r3.status_code == 200
    meta = r3.json()
    assert len(meta["chapters"]) == 1
    assert meta["chapters"][0]["chapter_no"] == 1
