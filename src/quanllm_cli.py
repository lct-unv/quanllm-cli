from openai import OpenAI
import sympy as sp
import json
import os
import sys
from datetime import datetime


def base_dir() -> str:
    """程序所在目录：打包后为 exe 所在目录，源码运行时为脚本所在目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def load_api_key() -> str:
    """从程序同目录的 APIKEY 文件中读取密钥；文件不存在时生成模板并退出。"""
    key_path = os.path.join(base_dir(), "APIKEY")
    if not os.path.exists(key_path):
        try:
            with open(key_path, "w", encoding="utf-8") as f:
                f.write("# 请将你的 API Key 粘贴到本行下方（仅保留 Key 本身，不要加引号）\n")
        except OSError:
            pass
        print(f"[未找到 API Key] 已在程序同目录生成模板文件：{key_path}")
        print("请将你的 API Key 写入该文件（单独一行），然后重新启动程序。")
        sys.exit(1)
    with open(key_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                return line
    print(f"[API Key 为空] 请将 API Key 写入文件：{key_path}（单独一行）")
    sys.exit(1)


client = OpenAI(
    api_key=load_api_key(),
    #base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    base_url="http://47.97.46.74:3000/v1"
)

MODEL = "QuanLLM-v1.0-qm"  # 网关侧模型重定向名（上游为 qwen3-8b-7801b26b3ddc），大小写敏感
ENABLE_THINKING = True            # 思考模式开关；若所用模型不支持思考模式下的工具调用，可改为 False


def sympy_calculate(expression: str, operation: str, symbol: str = "x") -> str:
    """
    使用 SymPy 进行符号计算。
    :param expression: 数学表达式，如 "x**2 + sin(x)"
    :param operation: 操作类型，可选 'eval', 'diff', 'integrate'
    :param symbol: 自变量符号，默认为 'x'
    :return: 计算结果（字符串）
    """
    try:
        x = sp.symbols(symbol)
        expr = sp.sympify(expression)
        if operation == "eval":
            return str(expr)
        elif operation == "diff":
            result = sp.diff(expr, x)
            return str(result)
        elif operation == "integrate":
            result = sp.integrate(expr, x)
            return str(result)
        else:
            return f"不支持的操作: {operation}"
    except Exception as e:
        return f"计算错误: {str(e)}"


# 工具2：解方程
def sympy_solve(equation: str, symbol: str = "x") -> str:
    """
    解方程。
    :param equation: 方程字符串，如 "x**2 - 4 = 0" 或 "x**2 - 4" （默认=0）
    :param symbol: 未知数符号
    :return: 解集（字符串）
    """
    try:
        x = sp.symbols(symbol)
        if "=" in equation:
            lhs, rhs = equation.split("=")
            expr = sp.sympify(lhs) - sp.sympify(rhs)
        else:
            expr = sp.sympify(equation)
        solutions = sp.solve(expr, x)
        return str(solutions)
    except Exception as e:
        return f"解方程错误: {str(e)}"


# ================= 定义工具描述（给模型看） =================

tools = [
    {
        "type": "function",
        "function": {
            "name": "sympy_calculate",
            "description": "使用 SymPy 进行符号计算，包括表达式求值（返回表达式本身）、求导、积分。",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "数学表达式，例如 'x**2 + sin(x)'"
                    },
                    "operation": {
                        "type": "string",
                        "enum": ["eval", "diff", "integrate"],
                        "description": "操作类型：eval-求值（返回表达式），diff-求导，integrate-积分"
                    },
                    "symbol": {
                        "type": "string",
                        "description": "自变量符号，默认为 'x'",
                        "default": "x"
                    }
                },
                "required": ["expression", "operation"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sympy_solve",
            "description": "解方程，支持一元方程。",
            "parameters": {
                "type": "object",
                "properties": {
                    "equation": {
                        "type": "string",
                        "description": "方程字符串，例如 'x**2 - 4 = 0' 或 'x**2 - 4'（默认为=0）"
                    },
                    "symbol": {
                        "type": "string",
                        "description": "未知数符号，默认为 'x'",
                        "default": "x"
                    }
                },
                "required": ["equation"]
            }
        }
    }
]


# ================= 流式请求封装 =================

# 本会话 Token 用量累计（网关 usage 字段回填）
SESSION_USAGE = {"prompt": 0, "completion": 0}


def stream_request(messages, use_tools: bool = False) -> dict:
    """
    发起一次流式对话请求：
    - 实时打印思考过程（reasoning_content）与正式回答（content）
    - 增量累积 tool_calls 分片
    - 通过 stream_options 让网关回传本轮 Token 用量并打印
    返回可追加进 messages 的 assistant 消息字典。
    """
    kwargs = dict(
        model=MODEL,
        messages=messages,
        stream=True,
        stream_options={"include_usage": True},  # 让网关在最后一个分片回传 usage
        extra_body={"enable_thinking": ENABLE_THINKING},
    )
    if use_tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"  # 让模型自动决定

    stream = client.chat.completions.create(**kwargs)

    content_parts = []
    tool_call_slots = {}  # index -> {"id": str, "name": str, "arguments": str}
    thinking_started = False
    answer_started = False
    usage_info = None

    for chunk in stream:
        # 用量分片（通常为最后一个 chunk，此时 choices 为空）
        if getattr(chunk, "usage", None):
            usage_info = chunk.usage
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta

        # 思考过程（思考模式下由 reasoning_content 字段返回）
        reasoning_chunk = getattr(delta, "reasoning_content", None)
        if reasoning_chunk:
            if not thinking_started:
                print("【思考过程】", end="", flush=True)
                thinking_started = True
            print(reasoning_chunk, end="", flush=True)

        # 正式回答
        if delta.content:
            if not answer_started:
                print("\n【回答】" if thinking_started else "【回答】", end="", flush=True)
                answer_started = True
            print(delta.content, end="", flush=True)
            content_parts.append(delta.content)

        # 工具调用分片累积
        if delta.tool_calls:
            for tc in delta.tool_calls:
                slot = tool_call_slots.setdefault(
                    tc.index, {"id": "", "name": "", "arguments": ""}
                )
                if tc.id:
                    slot["id"] = tc.id
                if tc.function:
                    if tc.function.name:
                        slot["name"] = tc.function.name
                    if tc.function.arguments:
                        slot["arguments"] += tc.function.arguments

    print()  # 流式输出结束后换行

    # 打印本轮 Token 用量并累计到会话级
    if usage_info:
        prompt = usage_info.prompt_tokens or 0
        completion = usage_info.completion_tokens or 0
        SESSION_USAGE["prompt"] += prompt
        SESSION_USAGE["completion"] += completion
        print(f"[Token] 本轮 输入 {prompt} · 输出 {completion}"
              f" ｜ 本会话累计 输入 {SESSION_USAGE['prompt']} · 输出 {SESSION_USAGE['completion']}")
        log_event({
            "type": "usage",
            "time": datetime.now().isoformat(timespec="seconds"),
            "prompt_tokens": prompt,
            "completion_tokens": completion,
        })

    content = "".join(content_parts)
    assistant_message = {"role": "assistant", "content": content or None}
    if tool_call_slots:
        assistant_message["tool_calls"] = [
            {
                "id": slot["id"],
                "type": "function",
                "function": {"name": slot["name"], "arguments": slot["arguments"]},
            }
            for slot in tool_call_slots.values()
            if slot["name"]
        ]
    return assistant_message


# ================= 主函数：处理单轮查询（含工具调用循环） =================

def chat_with_tools(messages: list) -> str:
    """在既有对话历史上继续对话；模型可能连续多轮调用工具，直到给出最终回答。"""
    while True:
        # 流式输出思考过程/回答，并让模型决定是否调用工具
        assistant_message = stream_request(messages, use_tools=True)
        append_message(messages, assistant_message)

        # 没有调用工具，返回最终回答
        if not assistant_message.get("tool_calls"):
            return assistant_message["content"] or ""

        # 处理每个工具调用
        for tool_call in assistant_message["tool_calls"]:
            function_name = tool_call["function"]["name"]
            function_args = json.loads(tool_call["function"]["arguments"] or "{}")
            print(f"[调用工具] {function_name}({function_args})")

            if function_name == "sympy_calculate":
                result = sympy_calculate(
                    expression=function_args.get("expression"),
                    operation=function_args.get("operation"),
                    symbol=function_args.get("symbol", "x"),
                )
            elif function_name == "sympy_solve":
                result = sympy_solve(
                    equation=function_args.get("equation"),
                    symbol=function_args.get("symbol", "x"),
                )
            else:
                result = f"未知工具: {function_name}"

            print(f"[工具结果] {result}")
            append_message(messages, {
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": result,
            })


# ================= 多轮对话 CLI =================

SYSTEM_PROMPT = (
    "你是 QuanLLM-qm，QuanLLM 主产品在量子力学教学与应用方向的领域专家模型。你的定位与要求：\n"
    "1. 备考导向：围绕期末考试高频考点（概念解释、公式推导、计算题、证明题）给出结构化的规范回答，步骤完整，符合考试书写要求。\n"
    "2. 通用问答：解释量子力学概念、对比不同表象、讨论物理图像与常见误区，帮助用户建立物理直觉。\n"
    "3. 符号规范：正确使用狄拉克符号与算符记法，推导逐步展开、不跳步，物理含义说清楚。\n"
    "4. 工具使用：凡涉及求导、积分、解方程等符号计算，必须调用 SymPy 工具获得精确结果，不要凭记忆口算；拿到工具结果后再组织成完整推导。\n"
    "默认使用清晰的中文回答；用户用其他语言提问时，用相应语言回答。"
)

# 会话历史持久化文件（JSONL，每行一条记录），保存在程序同目录
HISTORY_FILE = os.path.join(base_dir(), "chat_history.jsonl")


def log_event(event: dict):
    """向历史文件追加一条 JSONL 记录（消息或会话标记）。"""
    try:
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except OSError:
        pass  # 历史写失败不影响对话


def new_session():
    """开始一段新会话：写入 session_start 标记并返回初始 messages。"""
    SESSION_USAGE["prompt"] = SESSION_USAGE["completion"] = 0  # 新会话用量归零
    log_event({
        "type": "session_start",
        "time": datetime.now().isoformat(timespec="seconds"),
    })
    return [{"role": "system", "content": SYSTEM_PROMPT}]


def append_message(messages: list, message: dict):
    """追加消息到对话历史，同时写入 JSONL 持久化文件。"""
    messages.append(message)
    log_event({"type": "message", **message})


def list_sessions() -> list:
    """解析历史文件，返回 [(start_time, [messages...]), ...]，只保留含消息的会话。"""
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return []

    sessions = []  # [(start_time, [messages...]), ...]
    current = None
    for line in lines:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("type") == "session_start":
            current = (record.get("time"), [])
            sessions.append(current)
        elif record.get("type") == "message" and current is not None:
            record.pop("type", None)
            current[1].append(record)

    return [(t, msgs) for t, msgs in sessions if msgs]


def load_session(index: int = None) -> list:
    """
    恢复历史会话：index 为 :sessions 列表中的编号（从 1 开始）；
    不传则恢复最近一次会话。找不到时返回 None。
    """
    sessions = list_sessions()
    if not sessions:
        return None
    if index is None:
        start_time, msgs = sessions[-1]
    elif 1 <= index <= len(sessions):
        start_time, msgs = sessions[index - 1]
    else:
        print(f"[编号超出范围，当前共 {len(sessions)} 段会话]")
        return None
    print(f"[已恢复 {start_time} 的会话，共 {len(msgs)} 条消息]")
    return [{"role": "system", "content": SYSTEM_PROMPT}] + msgs


def print_sessions():
    """列出所有历史会话：编号、开始时间、消息数、首个问题。"""
    sessions = list_sessions()
    if not sessions:
        print("[没有历史会话]")
        return
    print("历史会话：")
    for i, (start_time, msgs) in enumerate(sessions, 1):
        first_question = next(
            (m["content"] for m in msgs if m.get("role") == "user"), "(无用户消息)"
        )
        preview = first_question.replace("\n", " ")[:40]
        print(f"  {i}. [{start_time}] {len(msgs)} 条消息 | {preview}")


def main():
    messages = new_session()
    print("QuanLLM-qm · 量子力学专家模型 CLI（流式 + 思考模式 + SymPy 工具）")
    print("输入问题进行对话；:sessions 查看历史会话，:load [编号] 恢复会话，:clear 清空上下文，:quit 退出。")
    print(f"历史记录保存在 {HISTORY_FILE}\n")

    while True:
        try:
            user_input = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue
        if user_input in (":quit", ":q", "exit", "quit"):
            print("再见！")
            break
        if user_input == ":clear":
            messages = new_session()
            print("[上下文已清空，已开始新会话]\n")
            continue
        if user_input == ":sessions":
            print_sessions()
            print()
            continue
        if user_input == ":load" or user_input.startswith(":load "):
            # :load 恢复最近一次；:load 编号 恢复指定会话
            index = None
            parts = user_input.split()
            if len(parts) == 2:
                if not parts[1].isdigit():
                    print("[用法] :load 或 :load 编号（编号见 :sessions）\n")
                    continue
                index = int(parts[1])
            loaded = load_session(index)
            if loaded:
                messages = loaded
            else:
                if index is None:
                    print("[没有找到可恢复的历史会话]")
            print()
            continue

        append_message(messages, {"role": "user", "content": user_input})
        try:
            chat_with_tools(messages)
        except Exception as e:
            # 请求失败时移除这条用户消息，避免历史里留下没有回应的一轮
            messages.pop()
            msg = str(e)
            if "insufficient_user_quota" in msg or "429" in msg:
                print("[额度已用完] 当前 API Key 的额度已耗尽，请联系发放方充值或申请追加额度。")
            else:
                print(f"[请求出错] {e}")
        print()


if __name__ == "__main__":
    main()
