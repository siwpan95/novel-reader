@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 综网终端 v3.0 - 因→果

REM 自动查找 Python（优先 PATH 中的 python，其次 py launcher，最后硬编码路径）
where python >nul 2>&1 && (
    python game.py
    goto :done
)
where py >nul 2>&1 && (
    py game.py
    goto :done
)
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" game.py
    goto :done
)

echo [ERROR] 未找到 Python！请安装 Python 3.13+ 并确保 python 或 py 命令可用。
pause
exit /b 1

:done
pause
