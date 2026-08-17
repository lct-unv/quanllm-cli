## QuanLLM-qm 命令行客户端 v0.3.0 (0815)

量子力学专家模型 QuanLLM 的自适应 CLI 客户端：流式输出、思考模式可见、SymPy 符号计算工具调用、多轮对话与历史会话持久化。

### 下载

| 平台 | 文件 |
|------|------|
| Windows (x86_64) | quanllm-cli-v0.3.0-windows-x86_64.zip |
| macOS (Apple Silicon) | quanllm-cli-v0.3.0-macos-arm64.zip |
| Linux (x86_64) | quanllm-cli-v0.3.0-linux-x86_64.zip |

### 使用方法

1. 解压后将 `APIKEY.example` 重命名为 `APIKEY`，写入你的 API Key（单独一行，不加引号）
2. 运行程序：Windows 双击 `quanllm-cli.exe`；macOS / Linux 终端执行 `./quanllm-cli`
3. 直接输入问题开始对话

对话指令：`:sessions` 查看历史会话，`:load [编号]` 恢复会话，`:clear` 清空上下文，`:quit` 退出。

### 注意

- 程序内不含任何密钥，仅从同目录 `APIKEY` 文件读取
- macOS 首次运行如提示无法验证开发者：`xattr -d com.apple.quarantine quanllm-cli`
- Windows SmartScreen 可能对未签名程序弹提示，属正常现象
- Linux 版要求 glibc 2.31+（Ubuntu 20.04+ 等）

---

## QuanLLM-qm CLI Client v0.3.0 (0815)

The self-adaptive CLI client for QuanLLM, the expert model for quantum mechanics: streaming output, visible thinking mode, SymPy symbolic-computation tool calls, multi-turn conversation and persistent chat history.

### Downloads

| Platform | File |
|----------|------|
| Windows (x86_64) | quanllm-cli-v0.3.0-windows-x86_64.zip |
| macOS (Apple Silicon) | quanllm-cli-v0.3.0-macos-arm64.zip |
| Linux (x86_64) | quanllm-cli-v0.3.0-linux-x86_64.zip |

### Quick Start

1. After extracting, rename `APIKEY.example` to `APIKEY` and paste your API key inside (a single line, no quotes)
2. Run the program: double-click `quanllm-cli.exe` on Windows; run `./quanllm-cli` in a terminal on macOS / Linux
3. Type your question to start chatting

In-chat commands: `:sessions` to list past sessions, `:load [n]` to restore one, `:clear` to reset context, `:quit` to exit.

### Notes

- The binary contains no keys; it only reads the `APIKEY` file in the same directory
- If macOS says the developer cannot be verified on first launch: `xattr -d com.apple.quarantine quanllm-cli`
- Windows SmartScreen may warn about the unsigned binary — this is expected
- The Linux build requires glibc 2.31+ (e.g. Ubuntu 20.04+)
