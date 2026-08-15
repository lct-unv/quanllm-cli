@echo off
REM 在 Windows 本机构建 quanllm-cli.exe 单文件可执行程序
REM 需要先安装 Python 3.10+（https://www.python.org/downloads/）
cd /d "%~dp0\.."

python -m venv .build-venv
call .build-venv\Scripts\activate.bat
pip install -q openai sympy pyinstaller
pyinstaller --onefile --name quanllm-cli --clean --noconfirm src\quanllm_cli.py

echo.
echo 构建完成：dist\quanllm-cli.exe
echo 将 dist\quanllm-cli.exe 与 APIKEY.example、使用说明.txt 放在同一目录分发即可。
pause
