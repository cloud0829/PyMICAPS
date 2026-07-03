@echo off
title PyMICAPS 可视化终端
echo =======================================================
echo          PyMICAPS 可视化配置终端 - 启动脚本
echo =======================================================
echo.

:: 切换到脚本所在的目录
cd /d "%~dp0"

:: 检查虚拟环境是否存在
if not exist ".venv\Scripts\python.exe" (
    echo [错误] 未找到 Python 虚拟环境 (.venv)。
    echo 请确认项目依赖是否已经正确安装和部署。
    echo.
    pause
    exit /b 1
)

echo [INFO] 正在启动后台服务...
echo [INFO] 请勿关闭此窗口，关闭窗口将停止服务。
echo.

:: 异步打开浏览器（延迟2秒以确保服务器已经启动完毕）
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:5000"

:: 使用虚拟环境中的 Python 启动服务
".venv\Scripts\python.exe" Main.py --server

pause