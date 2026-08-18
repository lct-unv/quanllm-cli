# QuanLLM CLI

量子力学专家模型 QuanLLM-qm 的自适应命令行客户端。**开盒即用，无需安装 Python。**

## 功能特性

- 流式输出，思考模式（思维链）实时可见
- SymPy 符号计算工具调用（求导、积分、解方程，结果精确不口算）
- 支持定积分、极限、级数、微分方程、表达式等价性、矩阵/算符、角动量系数与 SI 量纲检查，未求值结果不会冒充答案
- 每轮默认执行不可关闭的第二次模型审核；公式损坏时最多比较三个候选并进行通用工具验证
- 面向学生自适应讲解：简单问题简答，概念、推导、计算与证明问题保留必要的理解支架
- 多行粘贴模式（`:paste`，以 `:send` 提交），避免一段提示被拆成多轮
- 多轮对话，历史会话自动持久化，可查看 / 恢复
- 行编辑：↑ / ↓ 调出历史输入（跨重启保留），← / → 移动光标，任意位置退格 / 删除
- 最终答案结束后统一显示 Token 用量：本轮全部请求 / 本会话累计 / 本机累计（按 API Key 分别统计，持久化在 `usage_stats.json`）
- API Key 额度耗尽（429）时给出明确中文提示
- 网关地址固定内置、源码无明文，不提供切换入口

## 下载

前往 [Releases](https://github.com/lct-unv/quanllm-cli/releases) 下载对应平台的压缩包（当前版本 v0.5.0）：

| 平台 | 文件 |
|------|------|
| Windows (x86_64) | `quanllm-cli-v0.5.0-windows-x86_64.zip` |
| macOS (Apple Silicon) | `quanllm-cli-v0.5.0-macos-arm64.zip` |
| Linux (x86_64) | `quanllm-cli-v0.5.0-linux-x86_64.zip` |

## 三步上手

1. 解压后把 `APIKEY.example` 重命名为 `APIKEY`，写入自己的 Key（单独一行，不加引号）。
2. 运行程序：Windows 双击 `quanllm-cli.exe`；macOS / Linux 终端执行 `./quanllm-cli`。
3. 直接输入问题开始对话。

对话指令：`:paste` 输入多行消息，`:sessions` 查看历史会话，`:load [编号]` 恢复会话，`:clear` 清空上下文，`:quit` 退出。

`你：`只在等待用户输入时出现；最终终稿以`助手：`开头，随后才显示该轮合并 Token 统计。

强制审核会产生至少两次模型请求，因此单轮 Token 用量会高于未审核模式；CLI 会累计所有实际用量，并在最终答案结束后统一显示。

程序内不含任何密钥；密钥只会从同目录下的 `APIKEY` 文件读取。对话历史保存在同目录的 `chat_history.jsonl`。

## 注意事项

- macOS 首次运行可能提示"无法验证开发者"：在终端执行
  `xattr -d com.apple.quarantine quanllm-cli` 即可（未做 Apple 开发者签名）。
- Windows Defender / SmartScreen 可能对未签名 exe 弹提示，属正常现象。
- Linux 版要求 glibc 2.31+（Ubuntu 20.04+ 等）。

## 从源码运行 / 构建

```bash
pip install openai sympy
pip install pyreadline3   # 仅 Windows 需要（行编辑支持）
python src/quanllm_cli.py          # 直接运行

pip install pyinstaller
pyinstaller --onefile --name quanllm-cli src/quanllm_cli.py   # 打包单文件可执行程序
```

仓库内置两套 GitHub Actions：`build.yml` 按需构建三平台产物；`release.yml` 构建并上传带版本号的发行包到指定 Release。

## 许可证

本仓库代码以 [MIT License](LICENSE) 开源，版权归 MeaWorm Corp. 所有。

注意：**QuanLLM 名称、标识及相关品牌资产不在 MIT 许可证的授权范围内**。你可以自由使用、修改和再分发本代码，但不得以 QuanLLM 名义或可能造成混淆的方式分发修改版本。


---

# QuanLLM CLI

The self-adaptive command-line client for QuanLLM-qm, the quantum mechanics expert model. **Ready out of the box—no Python installation required.**

## Features

- Streaming output with visible thinking mode (chain of thought)
- SymPy symbolic-computation tool calls (derivatives, integrals, equation solving — exact results, no mental math)
- Definite integrals, limits, series, ODEs, expression equivalence, matrix/operator calculations, angular-momentum coefficients, and SI dimensional checks; unevaluated expressions are reported as failures
- A mandatory second-pass model review on every turn; damaged formulas are checked through up to three candidate reconstructions and general-purpose tools
- Adaptive student-oriented explanations: concise for simple facts, sufficiently scaffolded for concepts, derivations, calculations, and proofs
- Multi-line paste mode (`:paste`, submit with `:send`) so one prompt is not split into several turns
- Multi-turn conversation with automatic persistent history you can list / restore
- Line editing: ↑ / ↓ recall previous inputs (kept across restarts), ← / → move the cursor, backspace / delete at any position
- Consolidated token usage after the final answer: all requests in this turn / session totals / machine totals (counted per API key, persisted in `usage_stats.json`)
- Clear Chinese error message when the API key runs out of quota (HTTP 429)
- Gateway address fixed at build time, no plaintext in the source, no override option

## Downloads

Get the package for your platform from [Releases](https://github.com/lct-unv/quanllm-cli/releases) (current version: v0.5.0):

| Platform | File |
|----------|------|
| Windows (x86_64) | `quanllm-cli-v0.5.0-windows-x86_64.zip` |
| macOS (Apple Silicon) | `quanllm-cli-v0.5.0-macos-arm64.zip` |
| Linux (x86_64) | `quanllm-cli-v0.5.0-linux-x86_64.zip` |

## Quick Start

1. After extracting, rename `APIKEY.example` to `APIKEY` and paste your Key into it (single line, no quotes).
2. Run the program: double-click `quanllm-cli.exe` on Windows; run `./quanllm-cli` in a terminal on macOS / Linux.
3. Type your question to start chatting.

In-chat commands: `:paste` for a multi-line message, `:sessions` to list past sessions, `:load [n]` to restore one, `:clear` to reset context, `:quit` to exit.

`你：` appears only while waiting for user input. The reviewed final answer starts with `助手：`, followed by the consolidated Token report.

The mandatory review makes at least two model requests per turn, so Token usage is higher than in an unreviewed workflow. The CLI accumulates every request and reports the consolidated usage after the final answer.

No key is embedded in the program; the key is only read from the `APIKEY` file in the same directory. Conversation history is saved to `chat_history.jsonl` in the same directory.

## Notes

- On macOS, the first launch may warn that the developer cannot be verified. Run
  `xattr -d com.apple.quarantine quanllm-cli` in a terminal (the binary is not signed with an Apple Developer certificate).
- Windows Defender / SmartScreen may flag the unsigned exe; this is expected.
- The Linux build requires glibc 2.31+ (Ubuntu 20.04+, etc.).

## Run / Build from Source

```bash
pip install openai sympy
pip install pyreadline3   # Windows only (line-editing support)
python src/quanllm_cli.py          # run directly

pip install pyinstaller
pyinstaller --onefile --name quanllm-cli src/quanllm_cli.py   # build a single-file executable
```

Two GitHub Actions are included: `build.yml` builds on-demand artifacts for all three platforms; `release.yml` builds and uploads versioned packages to a given Release.

## License

The code in this repository is open sourced under the [MIT License](LICENSE), Copyright (c) 2026 MeaWorm Corp.

Note: **the QuanLLM name, logo, and related brand assets are NOT covered by the MIT License.** You are free to use, modify, and redistribute the code, but you may not distribute modified versions under the QuanLLM name or in any way that could cause confusion.
