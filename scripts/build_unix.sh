#!/usr/bin/env bash
# 在 macOS / Linux 本机构建 quanllm-cli 单文件可执行程序
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m venv .build-venv
.build-venv/bin/pip install -q openai sympy pyinstaller
.build-venv/bin/pyinstaller --onefile --name quanllm-cli --clean --noconfirm src/quanllm_cli.py

echo ""
echo "构建完成：dist/quanllm-cli"
echo "将 dist/quanllm-cli 与 APIKEY.example、使用说明.txt 放在同一目录分发即可。"
