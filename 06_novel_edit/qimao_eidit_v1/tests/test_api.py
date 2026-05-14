import pytest
from fastapi.testclient import TestClient

from novel_edit.api.app import create_app
from novel_edit.api.deps import get_conn
from novel_edit.repository import ensure_db


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "test.db"

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


def test_health(client: TestClient):
    data = client.get("/health").json()
    assert data["status"] == "ok"


def test_root_redirects_to_docs(client: TestClient):
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert r.headers.get("location", "").endswith("/docs")


def test_project_outline_run(client: TestClient):
    r = client.post("/api/projects", json={"title": "测试书", "qimao_category": "都市异能"})
    assert r.status_code == 200
    pid = r.json()["id"]

    outline = "# 卷一\n## 第1章 开局冲突\n修炼觉醒，打脸反派。\n"
    assert client.put(f"/api/projects/{pid}/outline", json={"raw_text": outline}).status_code == 200

    rep = client.post(f"/api/projects/{pid}/run", json={"package": "outline_only"}).json()
    assert rep["package"] == "outline_only"
    assert "criteria_hits" in rep
    assert "modification_suggestions" in rep
    assert "standards_enabled" in rep
