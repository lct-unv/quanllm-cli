## QuanLLM-qm 命令行客户端 v0.5.0 (0819)

本版本重点改善复杂公式输入的可靠性、答案审核与学生学习体验，并扩展了通用数学验证能力。

### 本版更新

- 新增多行粘贴模式：输入 `:paste` 后粘贴内容，以 `:send` 提交、`:cancel` 取消；统一处理 `\n`、`\r`、`\r\n` 与 `\n\r` 行尾，避免一段题目被拆成多轮
- 每个问题默认生成工具增强初稿并执行不可关闭的第二次模型审核；确定性检查未通过时最多审核三轮
- 对疑似复制损坏的公式，模型会比较不超过三个候选，结合量纲、极限与通用数学工具验证；仍有歧义时明确提醒用户
- 扩展 SymPy 工具：定积分、极限、级数、常微分方程、表达式等价性、SI 量纲、矩阵谱、对易/反对易关系、期望值、方差以及角动量系数
- 增加重复工具调用熔断与未求值结果检测，减少无效 Token 消耗并避免把未完成计算当作答案
- 温度固定为 `0.2`，兼顾输出稳定性与解释能力
- 增加自适应教学深度：简单问题保持简洁，概念、推导、计算与证明题保留直观含义、步骤理由、适用条件、结果检查与常见误区
- `你：`只在等待用户输入时显示；最终答案以`助手：`开头
- 初稿、工具调用、审核与重试的 Token 用量在内部累计，并在最终答案结束后统一显示一次

### 下载

| 平台 | 文件 |
|------|------|
| Windows (x86_64) | quanllm-cli-v0.5.0-windows-x86_64.zip |
| macOS (Apple Silicon) | quanllm-cli-v0.5.0-macos-arm64.zip |
| Linux (x86_64) | quanllm-cli-v0.5.0-linux-x86_64.zip |

### 使用方法

1. 解压后将 `APIKEY.example` 重命名为 `APIKEY`，写入你的 API Key（单独一行，不加引号）
2. 运行程序：Windows 双击 `quanllm-cli.exe`；macOS / Linux 终端执行 `./quanllm-cli`
3. 直接输入问题开始对话；多行内容使用 `:paste`

对话指令：`:paste` 输入多行消息，`:sessions` 查看历史会话，`:load [编号]` 恢复会话，`:clear` 清空上下文，`:quit` 退出。

### 注意

- 程序内不含任何密钥，仅从同目录 `APIKEY` 文件读取
- 强制审核至少产生两次模型请求，Token 用量会高于未审核流程
- macOS 首次运行如提示无法验证开发者：`xattr -d com.apple.quarantine quanllm-cli`
- Windows SmartScreen 可能对未签名程序弹出提示，属正常现象
- Linux 版要求 glibc 2.31+（Ubuntu 20.04+ 等）

---

## QuanLLM-qm CLI Client v0.5.0 (0819)

This release focuses on reliable complex-formula input, mandatory answer review, and a better learning experience for students, while expanding general-purpose mathematical verification.

### What's New

- Added multi-line paste mode: enter `:paste`, submit with `:send`, or cancel with `:cancel`; `\n`, `\r`, `\r\n`, and `\n\r` line endings are normalized so one prompt is not split into multiple turns
- Every question now receives a tool-enhanced draft and a mandatory second-pass model review; deterministic checks may trigger up to three review attempts
- Suspected copy-damaged formulas are reconstructed through up to three candidates and checked with dimensions, limits, and general-purpose math tools; unresolved ambiguity is disclosed to the user
- Expanded SymPy tools for definite integrals, limits, series, ODEs, expression equivalence, SI dimensions, matrix spectra, commutators and anticommutators, expectation values, variances, and angular-momentum coefficients
- Added repeated-tool-call protection and unevaluated-result detection to reduce wasted tokens and prevent incomplete calculations from being presented as answers
- Fixed temperature at `0.2` for a balance of stability and explanatory quality
- Added adaptive teaching depth: simple questions remain concise, while concepts, derivations, calculations, and proofs retain intuition, step rationale, validity conditions, result checks, and common pitfalls
- `你：` is shown only while waiting for user input; reviewed answers start with `助手：`
- Token usage from drafts, tool calls, reviews, and retries is accumulated internally and reported once after the final answer

### Downloads

| Platform | File |
|----------|------|
| Windows (x86_64) | quanllm-cli-v0.5.0-windows-x86_64.zip |
| macOS (Apple Silicon) | quanllm-cli-v0.5.0-macos-arm64.zip |
| Linux (x86_64) | quanllm-cli-v0.5.0-linux-x86_64.zip |

### Quick Start

1. After extracting, rename `APIKEY.example` to `APIKEY` and paste your API key inside (a single line, no quotes)
2. Run the program: double-click `quanllm-cli.exe` on Windows; run `./quanllm-cli` in a terminal on macOS / Linux
3. Type your question to start chatting; use `:paste` for multi-line input

In-chat commands: `:paste` for a multi-line message, `:sessions` to list past sessions, `:load [n]` to restore one, `:clear` to reset context, `:quit` to exit.

### Notes

- The binary contains no keys; it only reads the `APIKEY` file in the same directory
- Mandatory review makes at least two model requests, so Token usage is higher than in an unreviewed workflow
- If macOS says the developer cannot be verified on first launch: `xattr -d com.apple.quarantine quanllm-cli`
- Windows SmartScreen may warn about the unsigned binary; this is expected
- The Linux build requires glibc 2.31+ (e.g. Ubuntu 20.04+)
