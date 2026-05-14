"""
一键启动：七猫预审桌面客户端（内置 SQLite + 质检引擎，无需单独起 HTTP）。

双击同目录下的 start-workbench.bat 即可。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    os.chdir(ROOT)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    py = Path(sys.executable)
    venv_py = ROOT / ".venv" / "Scripts" / "python.exe"
    if venv_py.is_file() and py.resolve() != venv_py.resolve():
        os.environ["PATH"] = str(venv_py.parent) + os.pathsep + os.environ.get("PATH", "")

    from novel_edit.client.gui_app import main as gui_main

    return int(gui_main())


if __name__ == "__main__":
    raise SystemExit(main())
