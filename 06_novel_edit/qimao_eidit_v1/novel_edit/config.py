import os
from pathlib import Path

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "novel_edit.db"


def get_project_root() -> Path:
    """novel_edit 包上一级目录（06_novel_edit 工程根）。"""
    return Path(__file__).resolve().parent.parent


def load_env_local(*, override: bool = False) -> None:
    """
    读取工程根目录 env.local（KEY=value，一行一项，# 开头为注释）。
    默认不覆盖已在环境中的变量；override=True 时以文件为准。
    """
    path = get_project_root() / "env.local"
    if not path.is_file():
        return

    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError:
        return

    for raw in raw_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if not key:
            continue
        if not override and key in os.environ and os.environ[key].strip():
            continue
        os.environ[key] = val


def get_db_path() -> Path:
    return Path(os.environ.get("NOVEL_EDIT_DB", str(DEFAULT_DB_PATH)))
