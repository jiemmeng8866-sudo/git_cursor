from __future__ import annotations

import sys
from pathlib import Path

# 允许直接运行本文件或从 IDE 启动：包根目录为 novel_edit 的上一级（含 novel_edit 文件夹）
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from novel_edit.client.bridge import ApiBridge


def main() -> int:
    import os

    from novel_edit.config import load_env_local

    load_env_local()

    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

    app = QApplication(sys.argv)
    app.setApplicationName("七猫预审工作台")
    app.setOrganizationName("novel_edit")

    engine = QQmlApplicationEngine()
    bridge = ApiBridge()
    engine.rootContext().setContextProperty("backend", bridge)

    qml_path = Path(__file__).resolve().parent / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        return 1

    bridge.pingServer()
    bridge.refreshProjectList()
    return int(app.exec())


if __name__ == "__main__":
    raise SystemExit(main())
