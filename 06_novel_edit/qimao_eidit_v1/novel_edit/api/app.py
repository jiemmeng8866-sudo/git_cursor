from __future__ import annotations

from novel_edit.config import load_env_local

load_env_local()

from fastapi import FastAPI
from starlette.responses import RedirectResponse

from novel_edit.api.router import api_router
from novel_edit.api.schemas import APP_DESCRIPTION, OPENAPI_TAGS


def create_app() -> FastAPI:
    app = FastAPI(
        title="七猫预审本地 API",
        description=APP_DESCRIPTION,
        version="0.1.0",
        openapi_tags=OPENAPI_TAGS,
        docs_url="/docs",
        redoc_url=None,
        swagger_ui_parameters={
            "docExpansion": "list",
            "displayRequestDuration": True,
        },
    )

    app.include_router(api_router)

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse(url="/docs")

    @app.get("/health", summary="健康检查", tags=["系统"])
    def health():
        return {
            "status": "ok",
            "message": "服务运行中",
            "chapter_parser": "leading_cn+basename_v1",
        }

    return app


app = create_app()
