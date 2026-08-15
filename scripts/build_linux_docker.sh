#!/usr/bin/env bash
# 在 macOS (Apple Silicon) 上用 Docker 构建 Linux x86_64 版 quanllm-cli
# 依赖：colima + docker（brew install colima docker）
# 注意：Rosetta 下容器内访问挂载目录会报 "Resource deadlock avoided"，
#       因此用 docker cp 传入源码、传出产物，构建全程在容器内文件系统完成。
set -euo pipefail
cd "$(dirname "$0")/.."

IMAGE="python:3.11-bullseye"

# 首次使用先启动 colima（启用 Rosetta 以模拟 x86_64）
if ! docker info > /dev/null 2>&1; then
  colima start --vm-type=vz --vz-rosetta --cpu 4 --memory 8
fi

docker rm -f qlbuild 2>/dev/null || true
docker create --platform linux/amd64 --name qlbuild "$IMAGE" bash -c \
  "cd /tmp && pip install -q openai sympy pyinstaller \
   && pyinstaller --onefile --name quanllm-cli --clean --noconfirm \
      --distpath /tmp/dist --workpath /tmp/bp --specpath /tmp quanllm_cli.py"
docker cp src/quanllm_cli.py qlbuild:/tmp/quanllm_cli.py
docker start -a qlbuild

mkdir -p dist-linux
docker cp qlbuild:/tmp/dist/quanllm-cli dist-linux/quanllm-cli
docker rm -f qlbuild > /dev/null

echo ""
echo "构建完成：dist-linux/quanllm-cli (Linux x86_64)"
echo "将 dist-linux/quanllm-cli 与 APIKEY.example、使用说明.txt 放在同一目录分发即可。"
