## QuanLLM-qm 命令行客户端 v0.5.0 (0819)

本次同版本更新重点改善复杂公式输入、答案审核可靠性与学生学习体验，并扩展通用数学验证能力。

### 本版更新

- 新增多行粘贴模式：输入 `:paste` 后粘贴内容，以 `:send` 提交、`:cancel` 取消；统一处理 `\n`、`\r`、`\r\n` 与 `\n\r` 行尾，避免一段题目被拆成多轮
- 新增任务自适应独立参考解，只包含核心结论、必要推导、用户要求、禁用错误说法和具体工具核验任务；参考解与初稿、首次审核隔离，避免错误参考污染生成
- 审核流程固定为“初稿 → 强制审核 → 咨询判卷”；可靠重大意见最多触发一次定向重写，随后交付，不再反复重写与判卷
- 参考解、判卷和逐条语义裁决均为咨询型：结构化结果缺字段、缺编号或不可用时记录内部诊断，但不阻止已有答案交付
- 公式阶次、分母、量纲、矩阵/算符运算、本征问题、推导前提、适用范围和最终结论等问题按重大问题处理；工具核验必须对应正文中的实际公式或矩阵
- 所有模型阶段的原始思考过程按阶段显示，仅增加清晰分隔；程序调试日志与工具参数/结果仍保持隐藏
- 新增 `:again`，可将最近一次用户问题作为新一轮重新运行
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

对话指令：`:again` 重新运行上一问题，`:paste` 输入多行消息，`:sessions` 查看历史会话，`:load [编号]` 恢复会话，`:clear` 清空上下文，`:quit` 退出。

### 注意

- 程序内不含任何密钥，仅从同目录 `APIKEY` 文件读取
- 审核链会产生多次模型请求；全部用量在最终答案后统一显示
- macOS 首次运行如提示无法验证开发者：`xattr -d com.apple.quarantine quanllm-cli`
- Windows SmartScreen 可能对未签名程序弹出提示，属正常现象
- Linux 版要求 glibc 2.31+（Ubuntu 20.04+ 等）

---

## QuanLLM-qm CLI Client v0.5.0 (0819)

This same-version update focuses on reliable complex-formula input, safer answer review, and a better learning experience for students while expanding general-purpose mathematical verification.

### What's New

- Added multi-line paste mode: enter `:paste`, submit with `:send`, or cancel with `:cancel`; `\n`, `\r`, `\r\n`, and `\n\r` line endings are normalized so one prompt is not split into multiple turns
- Added a task-adaptive independent reference solution containing only core conclusions, necessary derivations, user requirements, forbidden claims, and concrete tool tasks; it is isolated from drafting and the first review to avoid contaminating generation
- The fixed pipeline is draft → mandatory review → advisory verification. Reliable major advice can trigger at most one targeted rewrite, after which an answer is delivered without repeated review loops
- Reference generation, verification, and per-issue adjudication are advisory. Missing fields, missing IDs, or unavailable structured output are recorded internally and never prevent delivery of an existing answer
- Formula order, denominators, dimensions, matrix/operator operations, eigenproblems, derivation premises, applicability, and final conclusions are treated as major issues; tool checks must correspond to formulas or matrices actually present in the answer
- Raw reasoning from every model stage is shown with clear stage separators, while program diagnostics and tool parameters/results remain hidden
- Added `:again` to rerun the most recent user question as a new turn
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

In-chat commands: `:again` to rerun the previous question, `:paste` for a multi-line message, `:sessions` to list past sessions, `:load [n]` to restore one, `:clear` to reset context, `:quit` to exit.

### Notes

- The binary contains no keys; it only reads the `APIKEY` file in the same directory
- The review chain can make several model requests; consolidated usage is shown after the final answer
- If macOS says the developer cannot be verified on first launch: `xattr -d com.apple.quarantine quanllm-cli`
- Windows SmartScreen may warn about the unsigned binary; this is expected
- The Linux build requires glibc 2.31+ (e.g. Ubuntu 20.04+)
