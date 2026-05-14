@echo off
chcp 65001 >nul
color 0A
title 批量文件管理专家 - 一键打包工具

echo =========================================
echo        正在准备打包环境...
echo =========================================
echo.

:: 检查并安装 pyinstaller
echo [1/3] 检查打包核心工具 PyInstaller...
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo 未检测到 PyInstaller，正在为您自动安装...
    pip install pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple
) else (
    echo PyInstaller 已就绪。
)

echo.
echo [2/3] 开始打包 BatchFileMaster_v3.py ...
echo (正在编译中，这可能需要 1-3 分钟，请耐心等待...)
echo.

:: 执行打包命令
:: -F 表示打包成单个独立的 exe 文件
:: -w 表示以窗口模式运行（隐藏背后黑色的 cmd 控制台窗口）
:: --clean 表示清理每次打包的临时缓存，防止出错
pyinstaller --clean -F -w BatchFileMaster_v3.py

echo.
echo =========================================
if exist "dist\BatchFileMaster_v3.exe" (
    echo [3/3] 打包大功告成！
    echo.
    echo 请在当前目录新生成的 【dist】 文件夹中查找你的 exe 程序！
) else (
    echo [!] 打包似乎遇到了问题，请向上滚动查看红色的报错信息。
)
echo =========================================
echo.
pause