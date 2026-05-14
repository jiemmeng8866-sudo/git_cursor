from __future__ import annotations


def decode_bytes(data: bytes) -> str:
    """本地小说常见 UTF-8 / GBK；优先带 BOM 的 UTF-8。"""
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")
