import base64
import hashlib

# 行编辑支持：↑/↓ 调出历史输入，←/→ 移动光标，任意位置退格/删除
# Unix/macOS 用内置 readline；Windows 用 pyreadline3（打包时已包含）
try:
    import readline
except ImportError:
    try:
        import pyreadline3 as readline
    except ImportError:
        readline = None

from openai import OpenAI
import sympy as sp
import json
import os
import re
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
            if line and not line.startswith("#") and not line.startswith("BASE_URL="):
                return line
    print(f"[API Key 为空] 请将 API Key 写入文件：{key_path}（单独一行）")
    sys.exit(1)


def load_base_url() -> str:
    """网关地址：固定内置（混淆存储，避免源码明文暴露），不提供切换入口。"""
    return base64.b64decode("aHR0cDovLzQ3Ljk3LjQ2Ljc0OjMwMDAvdjE=").decode("ascii")


API_KEY = load_api_key()

client = OpenAI(
    api_key=API_KEY,
    base_url=load_base_url()
)

MODEL = "QuanLLM-v1.0-qm"  # 网关侧模型重定向名（上游为 qwen3-8b-7801b26b3ddc），大小写敏感
ENABLE_THINKING = True            # 思考模式开关；若所用模型不支持思考模式下的工具调用，可改为 False
TEMPERATURE = 0.2                 # 经原始输出与完整审核链回归后确定
MAX_TOOL_ROUNDS = 4               # 防止模型反复调用工具而不结束
MAX_REVIEW_ATTEMPTS = 3            # 二审未通过确定性检查时最多再审两次


def _tool_result(ok: bool, result=None, error: str = None, warning: str = None) -> str:
    """统一工具返回格式，便于模型区分成功、失败和未完成计算。"""
    payload = {"ok": ok}
    if result is not None:
        payload["result"] = str(result)
    if error:
        payload["error"] = error
    if warning:
        payload["warning"] = warning
    return json.dumps(payload, ensure_ascii=False)


def _sympify_value(value, local_symbols=None):
    """解析表达式、积分上下限和极限点，兼容常用无穷记法。"""
    if value is None:
        return None
    aliases = {
        "inf": sp.oo,
        "+inf": sp.oo,
        "infinity": sp.oo,
        "+infinity": sp.oo,
        "oo": sp.oo,
        "+oo": sp.oo,
        "-inf": -sp.oo,
        "-infinity": -sp.oo,
        "-oo": -sp.oo,
    }
    if isinstance(value, str) and value.strip().lower() in aliases:
        return aliases[value.strip().lower()]
    return sp.sympify(value, locals=local_symbols or {})


def _unevaluated_result(result) -> bool:
    """识别 SymPy 保留下来的未求值运算，避免把 Integral(...) 当答案。"""
    if not isinstance(result, sp.Basic):
        return False
    unfinished = (sp.Integral, sp.Limit, sp.Derivative, sp.Sum, sp.Product)
    return any(result.has(kind) for kind in unfinished)


def _statistical_integral_fallback(expr, symbol, lower, upper):
    """处理 SymPy 常遗留未求值的玻色/费米型 0 到无穷积分。"""
    if lower != 0 or upper != sp.oo:
        return None

    coefficient = sp.Wild("coefficient", exclude=[symbol])
    power = sp.Wild("power", exclude=[symbol])
    scale = sp.Wild("scale", exclude=[symbol])
    for sign in (-1, 1):
        pattern = coefficient * symbol**power / (sp.exp(scale * symbol) + sign)
        match = expr.match(pattern)
        if not match:
            continue
        a = match[power]
        b = match[scale]
        c = match[coefficient]
        if not (a.is_real and a > 0 and b.is_real and b > 0):
            continue
        base = c * sp.gamma(a + 1) * sp.zeta(a + 1) / b ** (a + 1)
        if sign == 1:
            base *= 1 - 2 ** (-a)
        return sp.simplify(base)
    return None


def sympy_calculate(
    expression: str,
    operation: str,
    symbol: str = "x",
    lower_bound=None,
    upper_bound=None,
    point=None,
    direction: str = "+-",
    order: int = 6,
    precision: int = 30,
    positive_symbols=None,
    integer_symbols=None,
) -> str:
    """
    使用 SymPy 进行符号计算。
    :param expression: 数学表达式，如 "x**2 + sin(x)"
    :param operation: eval/simplify/numeric/diff/integrate/limit/series
    :param symbol: 自变量符号，默认为 'x'
    :return: 计算结果（字符串）
    """
    try:
        if not expression:
            return _tool_result(False, error="expression 不能为空")
        positive_names = set(positive_symbols or [])
        integer_names = set(integer_symbols or [])
        local_symbols = {}
        for name in positive_names | integer_names | {symbol}:
            assumptions = {}
            if name in positive_names:
                assumptions["positive"] = True
            if name in integer_names:
                assumptions["integer"] = True
            local_symbols[name] = sp.symbols(name, **assumptions)
        x = local_symbols[symbol]
        expr = sp.sympify(expression, locals=local_symbols)
        if operation == "eval":
            result = expr
        elif operation == "simplify":
            result = sp.simplify(expr)
        elif operation == "numeric":
            precision = max(2, min(int(precision), 100))
            result = sp.N(expr, precision)
        elif operation == "diff":
            result = sp.diff(expr, x)
        elif operation == "integrate":
            if (lower_bound is None) != (upper_bound is None):
                return _tool_result(False, error="定积分必须同时提供 lower_bound 和 upper_bound")
            if lower_bound is None:
                result = sp.integrate(expr, x)
            else:
                lower = _sympify_value(lower_bound, local_symbols)
                upper = _sympify_value(upper_bound, local_symbols)
                result = sp.integrate(
                    expr,
                    (x, lower, upper),
                )
                if _unevaluated_result(result):
                    fallback = _statistical_integral_fallback(expr, x, lower, upper)
                    if fallback is not None:
                        result = fallback
        elif operation == "limit":
            if point is None:
                return _tool_result(False, error="limit 操作必须提供 point")
            if direction not in ("+", "-", "+-"):
                return _tool_result(False, error="direction 只能是 +、- 或 +-")
            result = sp.limit(expr, x, _sympify_value(point, local_symbols), dir=direction)
        elif operation == "series":
            order = max(1, min(int(order), 30))
            expansion_point = _sympify_value(point, local_symbols) if point is not None else 0
            result = sp.series(expr, x, expansion_point, order)
        else:
            return _tool_result(False, error=f"不支持的操作: {operation}")

        if _unevaluated_result(result):
            return _tool_result(
                False,
                result=result,
                error="SymPy 未能完成计算，返回值仍含未求值运算",
            )
        return _tool_result(True, result=result)
    except Exception as e:
        return _tool_result(False, error=f"计算错误: {str(e)}")


# 工具2：解方程
def sympy_solve(equation: str, symbol: str = "x") -> str:
    """
    解方程。
    :param equation: 方程字符串，如 "x**2 - 4 = 0" 或 "x**2 - 4" （默认=0）
    :param symbol: 未知数符号
    :return: 解集（字符串）
    """
    try:
        if not equation:
            return _tool_result(False, error="equation 不能为空")
        x = sp.symbols(symbol)
        if "=" in equation:
            lhs, rhs = equation.split("=", 1)
            expr = sp.sympify(lhs) - sp.sympify(rhs)
        else:
            expr = sp.sympify(equation)
        solutions = sp.solve(expr, x)
        return _tool_result(True, result=solutions)
    except Exception as e:
        return _tool_result(False, error=f"解方程错误: {str(e)}")


def sympy_check_dimensions(expression: str, target_expression: str = None) -> str:
    """用 SymPy SI 单位检查表达式量纲，并可与目标表达式比较。"""
    try:
        import sympy.physics.units as units
        from sympy.physics.units.systems.si import SI
        from sympy.physics.units.util import check_dimensions

        unit_names = (
            "meter", "second", "kilogram", "ampere", "kelvin", "mole", "candela",
            "hertz", "joule", "electronvolt", "coulomb", "volt", "newton", "watt",
            "planck", "hbar", "boltzmann", "boltzmann_constant", "speed_of_light",
        )
        local_units = {
            name: getattr(units, name) for name in unit_names if hasattr(units, name)
        }
        local_units.update({
            "m": units.meter,
            "s": units.second,
            "kg": units.kilogram,
            "K": units.kelvin,
            "Hz": units.hertz,
            "J": units.joule,
            "eV": units.electronvolt,
            "h": units.planck,
            "c": units.speed_of_light,
            "k_B": units.boltzmann,
            "nu": units.hertz,
            "v": units.hertz,
            "T": units.kelvin,
            "energy_density": units.joule / units.meter**3,
            "spectral_energy_density": units.joule / units.meter**3 / units.hertz,
            "length": units.meter,
            "time": units.second,
            "mass": units.kilogram,
            "energy": units.joule,
            "volume": units.meter**3,
        })

        expr = sp.sympify(expression, locals=local_units)
        if expr.free_symbols:
            unknown = ", ".join(sorted(str(symbol) for symbol in expr.free_symbols))
            return _tool_result(
                False,
                error=f"表达式含未映射到单位的符号: {unknown}",
                warning="请把每个物理量替换成明确单位，例如 planck*hertz 或 joule/meter**3",
            )
        check_dimensions(expr)
        dimension_system = SI.get_dimension_system()

        def dependencies(value):
            dimensional_expr = SI.get_dimensional_expr(value)
            deps = dimension_system.get_dimensional_dependencies(dimensional_expr)
            return {str(key): str(val) for key, val in deps.items()}

        expr_dims = dependencies(expr)
        payload = {"dimensions": expr_dims}
        if target_expression:
            target = sp.sympify(target_expression, locals=local_units)
            if target.free_symbols:
                unknown = ", ".join(sorted(str(symbol) for symbol in target.free_symbols))
                return _tool_result(
                    False,
                    error=f"目标表达式含未映射到单位的符号: {unknown}",
                )
            check_dimensions(target)
            target_dims = dependencies(target)
            payload["target_dimensions"] = target_dims
            payload["equivalent"] = expr_dims == target_dims
        return _tool_result(True, result=json.dumps(payload, ensure_ascii=False))
    except Exception as e:
        return _tool_result(False, error=f"量纲检查错误: {str(e)}")


def sympy_compare_expressions(lhs: str, rhs: str) -> str:
    """通过符号化简检查两个标量表达式是否等价。"""
    try:
        if lhs is None or rhs is None:
            return _tool_result(False, error="lhs 和 rhs 均不能为空")
        left = sp.sympify(lhs)
        right = sp.sympify(rhs)
        difference = sp.simplify(left - right)
        equivalent = difference == 0
        return _tool_result(
            True,
            result=json.dumps(
                {"equivalent": equivalent, "simplified_difference": str(difference)},
                ensure_ascii=False,
            ),
        )
    except Exception as e:
        return _tool_result(False, error=f"表达式比较错误: {str(e)}")


def _parse_matrix(values):
    if not isinstance(values, list) or not values or not all(isinstance(row, list) for row in values):
        raise ValueError("矩阵必须是非空二维数组")
    width = len(values[0])
    if width == 0 or any(len(row) != width for row in values):
        raise ValueError("矩阵各行长度必须一致")
    return sp.Matrix([[sp.sympify(item) for item in row] for row in values])


def sympy_matrix_calculate(matrix, operation: str, other_matrix=None, state=None) -> str:
    """通用量子矩阵计算：谱、对易关系、厄米/幺正检查及态上的统计量。"""
    try:
        value = _parse_matrix(matrix)
        if operation == "eigenvalues":
            result = {str(key): multiplicity for key, multiplicity in value.eigenvals().items()}
        elif operation == "eigenvectors":
            result = [
                {
                    "eigenvalue": str(eigenvalue),
                    "multiplicity": multiplicity,
                    "vectors": [str(vector) for vector in vectors],
                }
                for eigenvalue, multiplicity, vectors in value.eigenvects()
            ]
        elif operation == "determinant":
            result = str(sp.simplify(value.det()))
        elif operation == "inverse":
            result = str(sp.simplify(value.inv()))
        elif operation == "trace":
            result = str(sp.simplify(value.trace()))
        elif operation == "rank":
            result = value.rank()
        elif operation == "hermitian":
            result = bool(value.is_hermitian)
        elif operation == "unitary":
            if value.rows != value.cols:
                return _tool_result(False, error="幺正性检查要求方阵")
            result = sp.simplify(value.H * value) == sp.eye(value.rows)
        elif operation in ("commutator", "anticommutator"):
            other = _parse_matrix(other_matrix)
            if value.shape != other.shape or value.rows != value.cols:
                return _tool_result(False, error="对易/反对易运算要求同阶方阵")
            product = value * other
            reverse = other * value
            result = str(sp.simplify(product - reverse if operation == "commutator" else product + reverse))
        elif operation in ("expectation", "variance"):
            vector = sp.Matrix([sp.sympify(item) for item in (state or [])])
            if vector.rows == 0 or vector.cols != 1 or value.rows != value.cols or value.cols != vector.rows:
                return _tool_result(False, error="期望值/方差要求方阵及维数匹配的非空态向量")
            norm = sp.simplify((vector.H * vector)[0])
            if norm == 0:
                return _tool_result(False, error="态向量范数不能为零")
            mean = sp.simplify((vector.H * value * vector)[0] / norm)
            if operation == "expectation":
                result = str(mean)
            else:
                second = sp.simplify((vector.H * value**2 * vector)[0] / norm)
                result = str(sp.simplify(second - mean**2))
        else:
            return _tool_result(False, error=f"不支持的矩阵操作: {operation}")
        return _tool_result(True, result=json.dumps(result, ensure_ascii=False) if isinstance(result, (dict, list)) else result)
    except Exception as e:
        return _tool_result(False, error=f"矩阵计算错误: {str(e)}")


def sympy_solve_ode(equation: str, function: str = "psi", variable: str = "x") -> str:
    """求解常微分方程，适用于定态波函数方程等问题。"""
    try:
        if not equation:
            return _tool_result(False, error="equation 不能为空")
        x = sp.symbols(variable)
        dependent = sp.Function(function)
        local_symbols = {variable: x, function: dependent}
        if "=" in equation:
            lhs, rhs = equation.split("=", 1)
            ode = sp.Eq(
                sp.sympify(lhs, locals=local_symbols),
                sp.sympify(rhs, locals=local_symbols),
            )
        else:
            ode = sp.Eq(sp.sympify(equation, locals=local_symbols), 0)
        result = sp.dsolve(ode, dependent(x))
        if _unevaluated_result(result):
            return _tool_result(False, result=result, error="SymPy 未能完成微分方程求解")
        return _tool_result(True, result=result)
    except Exception as e:
        return _tool_result(False, error=f"微分方程求解错误: {str(e)}")


def sympy_angular_momentum(operation: str, values: list) -> str:
    """精确计算 Clebsch–Gordan 与 Wigner 3j/6j 系数。"""
    try:
        from sympy.physics.wigner import clebsch_gordan, wigner_3j, wigner_6j

        parsed = [sp.sympify(value) for value in (values or [])]
        expected = {"clebsch_gordan": 6, "wigner_3j": 6, "wigner_6j": 6}
        if operation not in expected:
            return _tool_result(False, error=f"不支持的角动量操作: {operation}")
        if len(parsed) != expected[operation]:
            return _tool_result(False, error=f"{operation} 需要 6 个参数")
        functions = {
            "clebsch_gordan": clebsch_gordan,
            "wigner_3j": wigner_3j,
            "wigner_6j": wigner_6j,
        }
        result = sp.simplify(functions[operation](*parsed))
        return _tool_result(True, result=result)
    except Exception as e:
        return _tool_result(False, error=f"角动量系数计算错误: {str(e)}")


def has_suspicious_formula_text(text: str) -> bool:
    """识别网页复制后常见的指数、分母、箭头粘连，不尝试自动猜测具体公式。"""
    if "=" not in (text or ""):
        return False
    patterns = (
        r"[A-Za-zνλ]\d+[A-Za-zνλ]\d+",
        r"[A-Za-zνλ]\d{2,}[A-Za-zνλ]",
        r"-∞[A-Za-z0-9]",
        r"∞[A-Za-z0-9]",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def generic_formula_answer_issues(answer: str, suspicious_input: bool) -> list:
    """未知主题只检查是否继续照抄乱码；不在无依据时自动改公式。"""
    if not suspicious_input:
        return []
    issues = []
    if has_suspicious_formula_text(answer):
        issues.append("终稿仍包含疑似复制损坏的公式粘连串")
    if "=" not in (answer or ""):
        issues.append("终稿没有给出重建后的公式")
    return issues


def instruction_following_issues(user_text: str, answer: str) -> list:
    """只检查用户明确提出的通用交付要求，不绑定任何物理主题。"""
    request = (user_text or "").lower()
    response = answer or ""
    response_lower = response.lower()
    issues = []
    if re.search(r"逐步|推导|证明|derive|prove|step[- ]by[- ]step", request):
        if response.count("=") < 2 or len(response) < 180:
            issues.append("用户要求逐步推导或证明，但终稿缺少足够的中间等式与步骤")
    if re.search(r"量纲|dimension|unit check", request):
        if not re.search(r"量纲|单位|dimension|unit", response_lower):
            issues.append("用户要求量纲或单位检查，但终稿没有覆盖")
    if re.search(r"误区|常见错误|pitfall|misconception", request):
        if not re.search(r"误区|错误|pitfall|misconception", response_lower):
            issues.append("用户要求说明常见误区，但终稿没有覆盖")
    if re.search(r"极限|limit|经典极限", request):
        if not re.search(r"极限|趋于|limit|→|\\to", response_lower):
            issues.append("用户要求极限检查，但终稿没有覆盖")
    return issues


def teaching_completeness_issues(user_text: str, answer: str) -> list:
    """对明确需要讲解的非简单问题做通用教学完整性检查，不绑定学科主题。"""
    request = (user_text or "").lower()
    response = (answer or "").strip()
    issues = []
    explanation_requested = bool(re.search(
        r"通俗|易懂|详细|深入|帮助.{0,4}理解|解释|说明|物理含义|直观|什么是|何为|定义|概念|"
        r"explain|intuition|in detail|help.{0,8}understand|what is|define|meaning",
        request,
    ))
    substantial_task = bool(re.search(
        r"推导|证明|计算|求解|分析|比较|区别|为什么|如何|"
        r"derive|prove|calculate|solve|analy[sz]e|compare|why|how",
        request,
    ))
    if not (explanation_requested or substantial_task):
        return issues

    # 长度只作为明显欠缺的兜底信号；真正的完整性还由下方语义支架检查。
    if len(response) < 280:
        issues.append("该问题需要教学性讲解，但终稿明显过短，难以支撑学生理解")

    if explanation_requested:
        scaffolds = (
            r"是指|表示|描述|含义|意味着|物理图像|直观|means|represents|describes|intuition",
            r"因为|由于|原因|所以|因此|because|therefore|hence",
            r"条件|前提|适用|假设|其中|符号|condition|assumption|valid|where",
            r"误区|常见错误|容易混淆|注意|检验|检查|pitfall|mistake|check|verify",
            r"例如|例子|举例|总结|换句话说|也就是说|example|summary|in other words",
        )
        covered = sum(bool(re.search(pattern, response, re.IGNORECASE)) for pattern in scaffolds)
        if covered < 3:
            issues.append("终稿缺少足够的理解支架（直观含义、理由、适用条件、检查或例子）")
    return issues


# ================= 定义工具描述（给模型看） =================

tools = [
    {
        "type": "function",
        "function": {
            "name": "sympy_calculate",
            "description": "使用 SymPy 做精确符号计算。支持化简、数值化、求导、不定/定积分、极限和级数。定积分必须给出上下限；工具会明确报告未求值结果。",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "数学表达式，例如 'x**2 + sin(x)'"
                    },
                    "operation": {
                        "type": "string",
                        "enum": ["eval", "simplify", "numeric", "diff", "integrate", "limit", "series"],
                        "description": "操作类型"
                    },
                    "symbol": {
                        "type": "string",
                        "description": "自变量符号，默认为 'x'",
                        "default": "x"
                    },
                    "lower_bound": {
                        "type": "string",
                        "description": "定积分下限；可用 -oo。与 upper_bound 同时提供"
                    },
                    "upper_bound": {
                        "type": "string",
                        "description": "定积分上限；可用 oo。与 lower_bound 同时提供"
                    },
                    "point": {
                        "type": "string",
                        "description": "极限点或级数展开点；可用 oo、-oo"
                    },
                    "direction": {
                        "type": "string",
                        "enum": ["+", "-", "+-"],
                        "description": "极限方向",
                        "default": "+-"
                    },
                    "order": {
                        "type": "integer",
                        "description": "级数截断阶数，1 到 30",
                        "default": 6
                    },
                    "precision": {
                        "type": "integer",
                        "description": "数值计算精度，2 到 100 位",
                        "default": 30
                    },
                    "positive_symbols": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "应假设为正数的符号，如 [\"L\"]"
                    },
                    "integer_symbols": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "应假设为整数的符号，如 [\"n\"]"
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
    },
    {
        "type": "function",
        "function": {
            "name": "sympy_check_dimensions",
            "description": "检查物理表达式的 SI 量纲，并可与目标比较。只写单位表达式，不要写含未知物理变量的完整公式。例如用 planck*hertz 与 joule 比较；用 planck*hertz**3/speed_of_light**3 与 spectral_energy_density 比较。",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "用 SymPy 和单位名写出的待检表达式"
                    },
                    "target_expression": {
                        "type": "string",
                        "description": "可选的目标量纲表达式"
                    }
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sympy_compare_expressions",
            "description": "符号化简两个标量表达式之差，检查等式或两种推导结果是否严格等价。",
            "parameters": {
                "type": "object",
                "properties": {
                    "lhs": {"type": "string", "description": "等式左边或第一个表达式"},
                    "rhs": {"type": "string", "description": "等式右边或第二个表达式"}
                },
                "required": ["lhs", "rhs"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sympy_matrix_calculate",
            "description": "量子力学通用矩阵工具：本征值/本征向量、行列式、逆、迹、秩、厄米性、幺正性、对易子、反对易子、期望值与方差。矩阵元素使用 SymPy 字符串。",
            "parameters": {
                "type": "object",
                "properties": {
                    "matrix": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "string"}},
                        "description": "二维矩阵，例如 [[\"0\",\"1\"],[\"1\",\"0\"]]"
                    },
                    "operation": {
                        "type": "string",
                        "enum": ["eigenvalues", "eigenvectors", "determinant", "inverse", "trace", "rank", "hermitian", "unitary", "commutator", "anticommutator", "expectation", "variance"]
                    },
                    "other_matrix": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "string"}},
                        "description": "对易子或反对易子所需的第二个矩阵"
                    },
                    "state": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "期望值或方差所需的态向量；工具会自动除以范数"
                    }
                },
                "required": ["matrix", "operation"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sympy_solve_ode",
            "description": "精确求解常微分方程。调用前必须把 ψ′、ψ′′、dot 等排版记号转换成明确的 SymPy 写法，例如二阶导数写 diff(psi(x),x,2)，不得省略导数。",
            "parameters": {
                "type": "object",
                "properties": {
                    "equation": {"type": "string", "description": "微分方程；可写 lhs=rhs 或默认等于零"},
                    "function": {"type": "string", "description": "待求函数名", "default": "psi"},
                    "variable": {"type": "string", "description": "自变量", "default": "x"}
                },
                "required": ["equation"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sympy_angular_momentum",
            "description": "精确计算 Clebsch–Gordan、Wigner 3j 和 Wigner 6j 系数；半整数写作 1/2。",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["clebsch_gordan", "wigner_3j", "wigner_6j"]
                    },
                    "values": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 6,
                        "maxItems": 6,
                        "description": "按 SymPy 对应函数顺序提供 6 个参数"
                    }
                },
                "required": ["operation", "values"]
            }
        }
    }
]


# ================= 流式请求封装 =================

# 本会话 Token 用量累计（网关 usage 字段回填）
SESSION_USAGE = {"prompt": 0, "completion": 0}

# 当前用户轮次累计；每次模型请求只在内部记账，终稿输出后再统一展示。
TURN_USAGE = {"prompt": 0, "completion": 0, "requests": 0, "lifetime": None}

# 当前 API Key 的标识（不存储 Key 本体，仅存其散列前缀，用于按 Key 区分累计用量）
KEY_ID = hashlib.sha256(API_KEY.encode("utf-8")).hexdigest()[:16]

# Key 级累计用量持久化文件（本机统计），保存在程序同目录
USAGE_STATS_FILE = os.path.join(base_dir(), "usage_stats.json")


def bump_lifetime_usage(prompt: int, completion: int) -> dict:
    """把本轮用量累加进当前 Key 的本机持久化累计，并返回该 Key 的累计记录。

    本机文件只统计 INPUT/OUTPUT Token 数；Key 的权威额度数据以网关查询为准。
    """
    try:
        with open(USAGE_STATS_FILE, "r", encoding="utf-8") as f:
            store = json.load(f)
    except (OSError, ValueError):
        store = {}
    entry = store.get(KEY_ID) or {
        "prompt": 0,
        "completion": 0,
        "since": datetime.now().isoformat(timespec="seconds"),
    }
    entry["prompt"] += prompt
    entry["completion"] += completion
    store[KEY_ID] = entry
    try:
        with open(USAGE_STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False)
    except OSError:
        pass  # 写失败不影响对话
    return entry


def begin_turn_usage():
    """开始一个新的用户轮次，清空上一轮的临时用量。"""
    TURN_USAGE.update({"prompt": 0, "completion": 0, "requests": 0, "lifetime": None})


def print_turn_usage():
    """在本轮所有生成与审核结束后，一次性打印完整用量。"""
    if not TURN_USAGE["requests"]:
        return
    lifetime = TURN_USAGE.get("lifetime") or {}
    suffix = ""
    if lifetime:
        suffix = (
            f" ｜ 本机累计 输入 {lifetime.get('prompt', 0)} · 输出 {lifetime.get('completion', 0)}"
            f"（自 {str(lifetime.get('since', ''))[:10]} 起）"
        )
    print(
        f"Token：本轮 输入 {TURN_USAGE['prompt']} · 输出 {TURN_USAGE['completion']}"
        f"（共 {TURN_USAGE['requests']} 次模型请求）"
        f" ｜ 本会话累计 输入 {SESSION_USAGE['prompt']} · 输出 {SESSION_USAGE['completion']}"
        f"{suffix}"
    )


def stream_request(
    messages,
    use_tools: bool = False,
    display_reasoning: bool = True,
    display_content: bool = True,
    stage: str = "回答",
) -> dict:
    """
    发起一次流式对话请求：
    - 实时打印思考过程（reasoning_content）与正式回答（content）
    - 增量累积 tool_calls 分片
    - 通过 stream_options 让网关回传请求用量并在内部累计
    返回可追加进 messages 的 assistant 消息字典。
    """
    kwargs = dict(
        model=MODEL,
        messages=messages,
        temperature=TEMPERATURE,
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
            if display_reasoning and not thinking_started:
                print("【思考过程】", end="", flush=True)
                thinking_started = True
            if display_reasoning:
                print(reasoning_chunk, end="", flush=True)

        # 正式回答
        if delta.content:
            if display_content and not answer_started:
                print("\n【回答】" if thinking_started else "【回答】", end="", flush=True)
                answer_started = True
            if display_content:
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

    if thinking_started or answer_started:
        print()  # 流式输出结束后换行

    # 每个请求只在内部记账；整个用户轮次结束后再统一打印。
    if usage_info:
        prompt = usage_info.prompt_tokens or 0
        completion = usage_info.completion_tokens or 0
        SESSION_USAGE["prompt"] += prompt
        SESSION_USAGE["completion"] += completion
        lifetime = bump_lifetime_usage(prompt, completion)
        TURN_USAGE["prompt"] += prompt
        TURN_USAGE["completion"] += completion
        TURN_USAGE["requests"] += 1
        TURN_USAGE["lifetime"] = lifetime
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


# ================= 主函数：处理单轮查询（含工具调用与强制审核） =================

def execute_tool(function_name: str, function_args: dict) -> str:
    """分发工具调用，任何失败都以结构化结果返回给模型。"""
    if function_name == "sympy_calculate":
        return sympy_calculate(
            expression=function_args.get("expression"),
            operation=function_args.get("operation"),
            symbol=function_args.get("symbol", "x"),
            lower_bound=function_args.get("lower_bound"),
            upper_bound=function_args.get("upper_bound"),
            point=function_args.get("point"),
            direction=function_args.get("direction", "+-"),
            order=function_args.get("order", 6),
            precision=function_args.get("precision", 30),
            positive_symbols=function_args.get("positive_symbols"),
            integer_symbols=function_args.get("integer_symbols"),
        )
    if function_name == "sympy_solve":
        return sympy_solve(
            equation=function_args.get("equation"),
            symbol=function_args.get("symbol", "x"),
        )
    if function_name == "sympy_check_dimensions":
        return sympy_check_dimensions(
            expression=function_args.get("expression"),
            target_expression=function_args.get("target_expression"),
        )
    if function_name == "sympy_compare_expressions":
        return sympy_compare_expressions(
            lhs=function_args.get("lhs"),
            rhs=function_args.get("rhs"),
        )
    if function_name == "sympy_matrix_calculate":
        return sympy_matrix_calculate(
            matrix=function_args.get("matrix"),
            operation=function_args.get("operation"),
            other_matrix=function_args.get("other_matrix"),
            state=function_args.get("state"),
        )
    if function_name == "sympy_solve_ode":
        return sympy_solve_ode(
            equation=function_args.get("equation"),
            function=function_args.get("function", "psi"),
            variable=function_args.get("variable", "x"),
        )
    if function_name == "sympy_angular_momentum":
        return sympy_angular_momentum(
            operation=function_args.get("operation"),
            values=function_args.get("values"),
        )
    return _tool_result(False, error=f"未知工具: {function_name}")


def run_tool_conversation(messages: list, stage: str, show_reasoning: bool = False) -> str:
    """在临时消息列表中完成工具循环，不把中间草稿写入正式历史。"""
    seen_calls = set()
    for round_index in range(1, MAX_TOOL_ROUNDS + 1):
        assistant_message = stream_request(
            messages,
            use_tools=True,
            display_reasoning=show_reasoning,
            display_content=False,
            stage=stage,
        )
        messages.append(assistant_message)

        if not assistant_message.get("tool_calls"):
            answer = assistant_message.get("content") or ""
            return answer

        repeated_call = False
        for tool_call in assistant_message["tool_calls"]:
            function_name = tool_call["function"]["name"]
            try:
                function_args = json.loads(tool_call["function"]["arguments"] or "{}")
            except (TypeError, json.JSONDecodeError) as e:
                function_args = {}
                result = _tool_result(False, error=f"工具参数不是有效 JSON: {str(e)}")
            else:
                signature = (
                    function_name,
                    json.dumps(function_args, ensure_ascii=False, sort_keys=True),
                )
                if signature in seen_calls:
                    repeated_call = True
                    result = _tool_result(
                        False,
                        error="相同工具调用已经执行过，请使用已有结果完成答案",
                    )
                else:
                    seen_calls.add(signature)
                    result = execute_tool(function_name, function_args)

            print(f"[{stage}工具 {round_index}/{MAX_TOOL_ROUNDS}] {function_name}({function_args})")
            print(f"[工具结果] {result}")
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": result,
            })

        if repeated_call:
            messages.append({
                "role": "user",
                "content": "检测到重复工具调用。请立即使用已有工具结果完成答案，不得继续调用工具。",
            })
            assistant_message = stream_request(
                messages,
                use_tools=False,
                display_reasoning=show_reasoning,
                display_content=False,
                stage=stage,
            )
            messages.append(assistant_message)
            return assistant_message.get("content") or ""

    # 达到工具轮数上限后，强制模型停止调用工具并给出基于现有证据的结论。
    messages.append({
        "role": "user",
        "content": "工具调用已达到上限。请基于现有工具结果给出结论；无法确定的地方必须明确说明，不得继续调用工具。",
    })
    assistant_message = stream_request(
        messages,
        use_tools=False,
        display_reasoning=show_reasoning,
        display_content=False,
        stage=stage,
    )
    messages.append(assistant_message)
    answer = assistant_message.get("content") or ""
    return answer


def chat_with_tools(messages: list) -> str:
    """先生成工具增强初稿，再强制进行一次不可关闭的第二次审核。"""
    begin_turn_usage()
    working_messages = list(messages)
    current_user_text = next(
        (message.get("content", "") for message in reversed(messages) if message.get("role") == "user"),
        "",
    )
    suspicious_formula = has_suspicious_formula_text(current_user_text)

    print("[正在生成工具增强初稿…]")
    draft = run_tool_conversation(working_messages, stage="初稿", show_reasoning=False)
    if not draft:
        raise RuntimeError("模型未生成初稿")

    # 审核使用全新的 system 上下文，避免模型把原对话中的初稿或工具错误当成审核指令。
    reviewer_system = SYSTEM_PROMPT + "\n\n" + REVIEW_PROMPT
    reviewer_messages = [{"role": "system", "content": reviewer_system}]
    reviewer_messages.extend(
        message for message in messages if message.get("role") != "system"
    )
    reviewer_messages.append({"role": "assistant", "content": draft})
    reviewer_messages.append({
        "role": "user",
        "content": "请立即执行强制审核，并只给出可直接交付给用户的完整终稿。",
    })

    final_answer = ""
    issues = []
    for attempt in range(1, MAX_REVIEW_ATTEMPTS + 1):
        print(f"[正在进行强制二次审核 {attempt}/{MAX_REVIEW_ATTEMPTS}…]")
        final_answer = run_tool_conversation(
            reviewer_messages,
            stage=f"审核{attempt}",
            show_reasoning=ENABLE_THINKING,
        )
        if not final_answer:
            issues = ["模型审核后未返回内容"]
        else:
            issues = generic_formula_answer_issues(final_answer, suspicious_formula)
            issues.extend(instruction_following_issues(current_user_text, final_answer))
            issues.extend(teaching_completeness_issues(current_user_text, final_answer))
        if not issues:
            break
        if attempt < MAX_REVIEW_ATTEMPTS:
            print("[自动质检未通过，将重新审核] " + "；".join(issues))
            reviewer_messages.append({
                "role": "user",
                "content": (
                    "CLI 自动质检发现以下问题：" + "；".join(issues)
                    + "。请针对这些问题重写终稿；涉及损坏公式时，比较不超过三个候选并用通用数学工具验证，"
                    "仍无法唯一判断才说明歧义。不得为了变短而删除帮助学生理解的必要解释。"
                ),
            })

    if not final_answer:
        raise RuntimeError("模型审核后未返回内容")
    if issues:
        final_answer += "\n\n[CLI 校验提醒] 多轮审核后仍存在：" + "；".join(issues) + "。请核对原始公式。"

    print(f"助手：{final_answer}")

    append_message(messages, {"role": "assistant", "content": final_answer})
    print_turn_usage()
    return final_answer


# ================= 多轮对话 CLI =================

SYSTEM_PROMPT = (
    "你是 QuanLLM-qm，QuanLLM 主产品在量子力学教学与应用方向的领域专家模型。你的定位与要求：\n"
    "1. 备考导向：围绕期末考试高频考点（概念解释、公式推导、计算题、证明题）给出结构化的规范回答，步骤完整，符合考试书写要求。\n"
    "2. 通用问答：解释量子力学概念、对比不同表象、讨论物理图像与常见误区，帮助用户建立物理直觉。\n"
    "3. 符号规范：正确使用狄拉克符号与算符记法，推导逐步展开、不跳步，物理含义说清楚。\n"
    "4. 工具使用：凡涉及求导、积分、极限、级数、代数/微分方程、表达式等价性、矩阵谱、对易关系、期望值、角动量系数或量纲比较，先调用相应 SymPy 工具。工具返回 ok=false 时不得把未求值表达式当成结果。\n"
    "5. 公式纠错：输入公式疑似因复制而丢失分数线、指数、括号或箭头时，不要立即拒答。先结合上下文提出不超过三个候选解释，并用量纲、已知极限和工具结果排除；能唯一确定时说明采用的解释，仍有多解时才提醒用户确认。\n"
    "6. 自检：回答前核对关键等式、量纲、边界条件、低能/高能或经典极限；本征值问题必须排除平凡零解并写清量子数取值域。不要用无关的测不准原理、态叠加或算符术语填充解释。\n"
    "7. 教学深度：默认用户是正在学习相关内容的学生。先判断问题复杂度，再自适应组织答案：简单事实题直接回答；概念题兼顾直观图像、严谨定义、适用条件和易混点；推导、计算与证明题说明每一步做什么、为什么这样做，并在结尾检查结果或概括解题思路。不要用固定模板堆砌小标题，也不要仅因追求简洁而省略理解所需的中间环节。\n"
    "调用工具时先调用，不要在工具结果返回前输出正式答案。\n"
    "默认使用清晰的中文回答；用户用其他语言提问时，用相应语言回答。"
)

REVIEW_PROMPT = (
    "这是强制的第二次答案审核，不是新的学科问题。请审查上一条初稿并输出可直接交给用户的修订终稿。\n"
    "必须逐项检查：事实与物理因果、每一步代数、量纲、边界条件、对称性名称、低频/高频或经典极限，以及是否真正满足用户要求。\n"
    "遇到本征值或边界条件问题，必须检查是否错误保留了平凡零解，并明确量子数或解参数的允许范围。\n"
    "如果原始输入中的公式疑似复制损坏，先尝试不超过三个符合上下文的候选式，并调用计算、表达式等价性、矩阵或量纲工具比较。能唯一确定时，终稿开头要简短说明采用的修复解释；只有无法唯一判断时才提醒用户确认。不得默默照抄乱码，也不得凭空确定。\n"
    "工具返回 ok=false 或仍含未求值运算时，必须换一种验证方法或承认无法验证。需要工具时先调用工具，不要先输出答案。\n"
    "删除初稿中的空泛套话、机械重复和与题目无关的量子术语，但必须保留并在需要时补足能帮助学生理解的内容，包括直观含义、前置概念、步骤理由、公式适用条件、结果检查、常见误区和恰当的小例子。根据问题复杂度控制篇幅：简单问题不扩写成讲义，概念、推导、计算和证明问题不能压缩成只有结论的短答。终稿必须能够脱离初稿独立阅读：用户要求公式或逐步推导时，必须写出修正后的关键公式和逐步计算，不能只给概述，也不能用对称性等快捷论证替代用户点名要求的积分或证明；快捷论证只能用于复核。\n"
    "最终只输出修订后的完整答案，不要描述审核过程，也不要评价初稿。"
)

# 会话历史持久化文件（JSONL，每行一条记录），保存在程序同目录
HISTORY_FILE = os.path.join(base_dir(), "chat_history.jsonl")

# 键盘输入历史文件（↑/↓ 调出），同样保存在程序同目录，最多保留 1000 条
INPUT_HISTORY_FILE = os.path.join(base_dir(), ".input_history")


def init_input_history():
    """加载历史输入，使 ↑/↓ 可以调出上次运行时的输入；退出时自动保存。"""
    if readline is None:
        return
    try:
        # 支持 bracketed paste 的终端会把整段多行粘贴保留为一次输入，
        # 避免每个换行都被当成一次提交。
        readline.parse_and_bind("set enable-bracketed-paste on")
    except Exception:
        pass
    try:
        readline.read_history_file(INPUT_HISTORY_FILE)
    except OSError:
        pass  # 首次运行时文件不存在，忽略
    readline.set_history_length(1000)

    import atexit
    def _save():
        try:
            readline.write_history_file(INPUT_HISTORY_FILE)
        except OSError:
            pass
    atexit.register(_save)


def normalize_user_input(text: str) -> str:
    """统一行尾，保留有意义的换行结构。"""
    return text.replace("\r\n", "\n").replace("\n\r", "\n").replace("\r", "\n").strip()


def read_multiline_input():
    """读取一条多行消息；单独输入 :send 提交，:cancel 取消。"""
    print("[多行输入模式] 粘贴或输入内容；单独输入 :send 提交，:cancel 取消。")
    lines = []
    while True:
        try:
            line = input("... ")
        except EOFError:
            return normalize_user_input("\n".join(lines)) if lines else None
        except KeyboardInterrupt:
            print("\n[已取消多行输入]")
            return None

        if line == ":send":
            return normalize_user_input("\n".join(lines))
        if line == ":cancel":
            print("[已取消多行输入]")
            return None
        lines.append(line)


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
    init_input_history()
    messages = new_session()
    print("QuanLLM-qm · 量子力学专家模型 CLI（流式 + 思考模式 + SymPy 工具）")
    print("输入问题进行对话；:paste 输入多行消息，:sessions 查看历史会话，:load [编号] 恢复会话，:clear 清空上下文，:quit 退出。")
    print(f"历史记录保存在 {HISTORY_FILE}\n")

    while True:
        try:
            user_input = normalize_user_input(input("你："))
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
        if user_input == ":paste":
            user_input = read_multiline_input()
            if not user_input:
                continue
            is_multiline_message = True
        else:
            is_multiline_message = False
        if not is_multiline_message and user_input == ":sessions":
            print_sessions()
            print()
            continue
        if not is_multiline_message and (user_input == ":load" or user_input.startswith(":load ")):
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
            print_turn_usage()
        print()


if __name__ == "__main__":
    main()
