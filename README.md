# QuanLLM CLI

量子力学专家模型 QuanLLM-qm 的自适应命令行客户端。**开盒即用，无需安装 Python。**

## 功能特性

- 保留用户可见的完整原始思考过程：请求分类、独立参考解、初稿、审核、终稿判卷和逐条语义裁决的每次模型推理都按阶段原样展示；仅增加清晰的阶段分隔，不输出程序调试日志
- SymPy 符号计算工具调用（求导、积分、解方程，结果精确不口算）
- 支持定积分、极限、级数、微分方程、表达式等价性、矩阵/算符、角动量系数与 SI 量纲检查，未求值结果不会冒充答案
- 每轮先用只看原问题的一次模型请求建立任务自适应参考解，只包含核心结论、必要推导、用户要求、禁用错误说法和具体工具核验任务；参考解与初稿、首次强制审核完全隔离，只供后置咨询判卷使用
- 固定审核流程：初稿 → 首次强制审核 → 咨询判卷；可靠重大意见最多触发一次定向重写，随后无条件交付，不再反复重写与判卷。每条争议各用一次隔离模型请求裁决，程序不用自然语言正则、题目关键词或题型事实硬编码作语义裁决
- 结构化检查使用 JSON 输出模式，并记录不含正文的结束原因与字符数；整个参考解、判卷或裁决链均为咨询型，任何一环不可用时只记录内部诊断，不阻止初稿、审核稿或已有答案交付
- 轻微问题不触发定向重写，交付时最多披露两项简短提醒；公式层级或阶次、分母、量纲、矩阵/算符运算、本征问题、推导前提、适用范围和最终结论等问题一律作为重大问题处理
- 面向学生自适应讲解：简单问题简答，概念、推导、计算与证明问题保留必要的理解支架
- 多行粘贴模式（`:paste`，以 `:send` 提交），避免一段提示被拆成多轮
- `:again` 将最近一次用户问题作为新一轮再次运行
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

对话指令：`:again` 重新运行上一问题，`:paste` 输入多行消息，`:sessions` 查看历史会话，`:load [编号]` 恢复会话，`:clear` 清空上下文，`:quit` 退出。

`你：`只在等待用户输入时出现；处理过程中依次显示各阶段的原始“思考过程/思考结束”，再以`助手：`输出终稿，最后显示该轮合并 Token 统计。

审核链会产生多次模型请求；CLI 会累计所有实际用量，并在最终答案结束后统一显示。

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

- Complete raw reasoning from every model stage—classification, independent reference blueprint, drafting, review, verification, and per-issue adjudication—shown with clear stage separators
- SymPy symbolic-computation tool calls (derivatives, integrals, equation solving — exact results, no mental math)
- Definite integrals, limits, series, ODEs, expression equivalence, matrix/operator calculations, angular-momentum coefficients, and SI dimensional checks; unevaluated expressions are reported as failures
- A task-adaptive reference solution is generated from the question alone, containing only core conclusions, necessary derivations, user requirements, forbidden claims, and concrete tool-verification tasks. It is isolated from drafting and the first mandatory review and is used only by the later advisory verifier
- The fixed pipeline is draft → mandatory review → advisory verification. Reliable major advice can trigger at most one targeted rewrite, after which an answer is always delivered. Each disputed issue receives one isolated model adjudication without natural-language regex, topic keywords, or subject-fact hardcoding
- Structured checkpoints request JSON output and record only non-content metadata such as finish reason and character counts. The reference, verification, and adjudication chain is advisory throughout; any unavailable or malformed stage is recorded internally and never prevents delivery of a draft, reviewed answer, or existing answer
- Minor issues do not trigger a targeted rewrite and at most two are disclosed in a short note. Problems involving formula level/order, denominators, dimensions, matrix/operator operations, eigenproblems, derivation premises, applicability, or final conclusions are always treated as major
- Adaptive student-oriented explanations: concise for simple facts, sufficiently scaffolded for concepts, derivations, calculations, and proofs
- Multi-line paste mode (`:paste`, submit with `:send`) so one prompt is not split into several turns
- `:again` reruns the most recent user question as a new turn
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

In-chat commands: `:again` to rerun the previous question, `:paste` for a multi-line message, `:sessions` to list past sessions, `:load [n]` to restore one, `:clear` to reset context, `:quit` to exit.

`你：` appears only while waiting for user input. Raw reasoning from every stage is shown before the reviewed final answer, which starts with `助手：`; the consolidated Token report follows it.

The review chain can make several model requests per turn. The CLI accumulates every request and reports consolidated usage after the final answer is delivered.

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
