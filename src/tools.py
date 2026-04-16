"""
工具注册表与执行器

定义 Harness agent 可调用的所有工具，每个工具包含：
- JSON Schema 描述（传给 API 的 tools 字段）
- execute() 函数（实际执行逻辑）

工具执行统一通过 run_tool() 分发，返回字符串结果。
"""
import subprocess
from pathlib import Path
from typing import Any

# ── 工具执行函数 ────────────────────────────────────────────

def _read_file(path: str) -> str:
    """读取文件内容，超过 50,000 字时截断"""
    p = Path(path)
    if not p.exists():
        return "错误：文件不存在 → " + path
    if not p.is_file():
        return "错误：路径不是文件 → " + path
    try:
        content = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return "错误：无法以 UTF-8 读取（可能是二进制文件）→ " + path

    limit = 50_000
    if len(content) > limit:
        suffix = "\n\n[内容已截断，原始长度 " + str(len(content)) + " 字符，仅显示前 " + str(limit) + " 字符]"
        return content[:limit] + suffix
    return content


def _write_file(path: str, content: str) -> str:
    """写入文件，自动创建父目录"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return "已写入 " + path + "（" + str(len(content)) + " 字符）"


def _run_shell(command: str, timeout: int = 30) -> str:
    """执行 shell 命令，返回 stdout + stderr，超时时返回错误"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += result.stderr
        if result.returncode != 0:
            output += "\n[退出码：" + str(result.returncode) + "]"
        return output.strip() or "（命令执行完成，无输出）"
    except subprocess.TimeoutExpired:
        return "错误：命令超时（" + str(timeout) + "s）→ " + command


def _edit_file(path: str, old_string: str, new_string: str) -> str:
    """
    精准替换文件中的指定字符串。

    唯一性约束：old_string 在文件中必须有且仅有一处匹配。
    - 匹配数 = 0 → 报错，提示内容不存在
    - 匹配数 > 1 → 报错，要求提供更多上下文使其唯一
    - 匹配数 = 1 → 执行替换，自动对齐 new_string 的首行缩进
    """
    p = Path(path)
    if not p.exists():
        return "错误：文件不存在 → " + path
    if not p.is_file():
        return "错误：路径不是文件 → " + path

    try:
        content = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return "错误：无法以 UTF-8 读取 → " + path

    count = content.count(old_string)
    if count == 0:
        return "错误：未找到匹配内容，请确认 old_string 与文件内容完全一致（包括空格和换行）"
    if count > 1:
        return "错误：找到 " + str(count) + " 处匹配，old_string 必须唯一，请提供更多上下文"

    # 自动对齐：提取 old_string 首行的前导空白，应用到 new_string 各行
    old_first_line = old_string.split("\n")[0]
    leading = old_first_line[: len(old_first_line) - len(old_first_line.lstrip())]
    if leading and not new_string.startswith(leading):
        new_string = "\n".join(
            leading + line if line.strip() else line
            for line in new_string.split("\n")
        )

    new_content = content.replace(old_string, new_string, 1)
    p.write_text(new_content, encoding="utf-8")
    return "已替换 " + path + "（1 处）"


# ── 工具注册表 ──────────────────────────────────────────────
# 格式遵循 OpenAI function calling 规范

TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取指定路径文件的完整内容，超过 50,000 字时自动截断",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要读取的文件路径（相对或绝对路径）",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "将内容写入文件，文件不存在时自动创建，已存在时全量覆盖",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要写入的文件路径",
                    },
                    "content": {
                        "type": "string",
                        "description": "写入的完整文件内容",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "精准替换文件中的一段内容。old_string 必须在文件中唯一匹配，用于小范围修改；需要全文重写时改用 write_file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要修改的文件路径",
                    },
                    "old_string": {
                        "type": "string",
                        "description": "要被替换的原始内容，必须与文件中完全一致（含缩进和换行）",
                    },
                    "new_string": {
                        "type": "string",
                        "description": "替换后的新内容",
                    },
                },
                "required": ["path", "old_string", "new_string"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "执行一条 shell 命令并返回输出，默认超时 30 秒",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "要执行的完整 shell 命令",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "超时秒数，默认 30",
                        "default": 30,
                    },
                },
                "required": ["command"],
            },
        },
    },
]

# 工具名称 → 执行函数的映射表
_TOOL_EXECUTORS: dict[str, Any] = {
    "read_file":  lambda args: _read_file(args["path"]),
    "write_file": lambda args: _write_file(args["path"], args["content"]),
    "edit_file":  lambda args: _edit_file(args["path"], args["old_string"], args["new_string"]),
    "run_shell":  lambda args: _run_shell(args["command"], args.get("timeout", 30)),
}


def run_tool(name: str, arguments: dict) -> str:
    """
    统一工具分发入口。

    Args:
        name:      工具名称，必须在 TOOLS 中注册
        arguments: 工具参数字典，来自模型的 tool_calls

    Returns:
        工具执行结果字符串，失败时返回错误描述
    """
    executor = _TOOL_EXECUTORS.get(name)
    if executor is None:
        return "错误：未知工具 → " + name
    try:
        return executor(arguments)
    except KeyError as e:
        return "错误：缺少必要参数 " + str(e) + " → 工具 " + name
    except Exception as e:
        return "错误：工具执行失败 → " + name + ": " + str(e)
