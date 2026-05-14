"""DeepSeek（OpenAI 兼容）聊天接口；密钥来自环境变量，不写死。"""
from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from typing import Any

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"


def _post_json(url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float = 120.0) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def deepseek_chat_completion(
    user_prompt: str,
    *,
    system_prompt: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    timeout: float = 120.0,
) -> str:
    """
    返回 assistant 的文本内容。
    环境变量：NOVEL_EDIT_DEEPSEEK_API_KEY（必填）、NOVEL_EDIT_DEEPSEEK_BASE_URL、NOVEL_EDIT_DEEPSEEK_MODEL。
    """
    key = api_key or os.environ.get("NOVEL_EDIT_DEEPSEEK_API_KEY", "").strip()
    if not key:
        raise ValueError("未配置 API：请设置环境变量 NOVEL_EDIT_DEEPSEEK_API_KEY")

    root = (base_url or os.environ.get("NOVEL_EDIT_DEEPSEEK_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    mdl = (model or os.environ.get("NOVEL_EDIT_DEEPSEEK_MODEL") or DEFAULT_MODEL).strip()

    url = f"{root}/v1/chat/completions"
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    body = {
        "model": mdl,
        "messages": messages,
        "temperature": 0.3,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    }
    try:
        out = _post_json(url, headers, body, timeout=timeout)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")[:800]
        raise ValueError(f"DeepSeek HTTP {e.code}: {err_body}") from e
    except OSError as e:
        raise ValueError(f"网络错误：{e}") from e

    try:
        choices = out.get("choices") or []
        if not choices:
            raise ValueError(f"响应无 choices：{json.dumps(out, ensure_ascii=False)[:500]}")
        msg = choices[0].get("message") or {}
        content = (msg.get("content") or "").strip()
        if not content:
            raise ValueError(f"空回复：{json.dumps(out, ensure_ascii=False)[:500]}")
        return content
    except (KeyError, IndexError, TypeError) as e:
        raise ValueError(f"解析响应失败：{out}") from e
