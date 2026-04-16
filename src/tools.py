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
