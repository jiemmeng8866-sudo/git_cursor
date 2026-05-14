from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from novel_edit.engine.orchestrator import CheckPackage

OPENAPI_TAGS = [
    {"name": "系统", "description": "健康检查。"},
    {"name": "工程", "description": "工程、大纲与章节。"},
    {"name": "质检", "description": "套餐编排与合并报告。"},
]

APP_DESCRIPTION = "本地预审 HTTP 服务：规则引擎 H / A / B / C，供桌面客户端或 Swagger 调试。"


class OutlineBody(BaseModel):
    model_config = ConfigDict(title="大纲正文")

    raw_text: str = Field(default="", description="Markdown 或纯文本。")


class CreateProjectBody(BaseModel):
    model_config = ConfigDict(title="新建工程")

    title: str = Field(..., min_length=1, max_length=200, description="书名。")
    qimao_category: str = Field(
        default="",
        max_length=64,
        description="七猫子类（大纲关键词弱匹配）。",
    )


class RunCheckBody(BaseModel):
    model_config = ConfigDict(title="运行质检")

    package: CheckPackage = Field(
        default=CheckPackage.first_five,
        description=(
            "outline_only / outline_plus_chapter_1 / golden_three / "
            "first_five / first_ten"
        ),
    )
