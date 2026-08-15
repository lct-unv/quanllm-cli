# QuanLLM CLI 分发包

量子力学专家模型 QuanLLM-qm 的命令行客户端。流式输出、思考模式可见、SymPy 符号计算工具调用、多轮对话与历史会话持久化。**开盒即用，无需安装 Python。**

## 目录结构

```
quanllm-cli-dist/
├── releases/
│   ├── quanllm-cli-macos-arm64.zip      # macOS (Apple Silicon) 分发包，已实测
│   ├── quanllm-cli-linux-x86_64.zip     # Linux x86_64 分发包，已在容器中实测
│   ├── macos-arm64/                     # 解压后的原始目录
│   └── linux-x86_64/
├── src/quanllm_cli.py          # 源代码
├── scripts/
│   ├── build_unix.sh           # macOS / Linux 本机构建脚本
│   ├── build_windows.bat       # Windows 本机构建脚本
│   └── build_linux_docker.sh   # 在 macOS 上用 Docker 构建 Linux 版（本次实测所用方法）
├── .github/workflows/build.yml # 推送后自动构建全部四个平台
├── APIKEY.example
└── 使用说明.txt
```

## 用户侧：三步上手

1. 把 `APIKEY.example` 重命名为 `APIKEY`，写入自己的 Key（单独一行，不加引号）。
2. 运行 `quanllm-cli`（Windows 双击 `quanllm-cli.exe`）。
3. 直接输入问题开始对话；`:sessions` / `:load` / `:clear` / `:quit` 管理会话。

程序内不含任何密钥；密钥只从同目录的 `APIKEY` 文件读取。

## 注意事项

- macOS 版本的首次运行可能提示"无法验证开发者"：在终端执行
  `xattr -d com.apple.quarantine quanllm-cli` 即可（未做 Apple 开发者签名）。
- Windows  Defender / SmartScreen 可能对未签名 exe 弹提示，属正常现象。
- Linux 版请在 glibc 较新的发行版（Ubuntu 20.04+ 等）上运行。

## 许可证

本仓库代码以 [MIT License](LICENSE) 开源，版权归 MeaWorm Corp. 所有。

注意：**QuanLLM 名称、标识及相关品牌资产不在 MIT 许可证的授权范围内**。你可以自由使用、修改和再分发本代码，但不得以 QuanLLM 名义或可能造成混淆的方式分发修改版本。
