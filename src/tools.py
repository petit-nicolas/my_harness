"""
工具注册表与执行器

定义 Harness agent 可调用的所有工具，每个工具包含：
- JSON Schema 描述（传给 API 的 tools 字段）
- execute() 函数（实际执行逻辑）

工具执行统一通过 run_tool() 分发，返回字符串结果。

Lazy Expansion（延迟展开）机制：
    模块级 _LAST_RESULTS 缓存每次工具调用的完整结果，键为 tool_call_id。
    agent.py 在写入历史时生成预览 + 缓存完整内容。
    模型若需要后续内容，调用 read_tool_result(call_id, offset) 从缓存取。
    缓存随进程生命周期存活，一次运行内均可复用。
"""
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

# ── Lazy Expansion 缓存 ─────────────────────────────────────

_LAST_RESULTS: dict[str, str] = {}


def cache_tool_result(call_id: str, content: str) -> None:
    """存入一次工具调用的完整结果（由 agent.py 在执行完毕后调用）"""
    if call_id:
        _LAST_RESULTS[call_id] = content


def get_cached_result(call_id: str) -> str | None:
    """读取缓存（不存在返回 None）"""
    return _LAST_RESULTS.get(call_id)


def clear_result_cache() -> None:
    """清空所有缓存（用于 /clear 或新会话）"""
    _LAST_RESULTS.clear()


def _read_tool_result(call_id: str, offset: int = 0, length: int = 3000) -> str:
    """
    从缓存读取某次工具调用的完整结果（指定偏移量和长度）。

    典型用法：模型在看到预览后，若想获取未见部分，调用本工具。
    """
    full = _LAST_RESULTS.get(call_id)
    if full is None:
        return (
            "错误：未找到缓存 → call_id=" + call_id
            + "\n（可用 call_id 仅限当前会话内已执行过的工具调用）"
        )

    total_len = len(full)
    if offset < 0:
        offset = 0
    if offset >= total_len:
        return "（偏移量 " + str(offset) + " 已超出内容总长度 " + str(total_len) + "）"

    end = min(offset + length, total_len)
    slice_text = full[offset:end]

    header = "[缓存片段 call_id=" + call_id + "  总长度 " + str(total_len) + " 字符  当前 " + str(offset) + "-" + str(end) + "]\n"
    if end < total_len:
        footer = "\n\n[后续还有 " + str(total_len - end) + " 字符，如需继续查看：read_tool_result(call_id=\"" + call_id + "\", offset=" + str(end) + ")]"
    else:
        footer = "\n\n[已读至末尾]"

    return header + slice_text + footer

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


_GREP_MAX_RESULTS = 100   # 单次搜索最多返回的匹配行数
_LIST_MAX_RESULTS = 200   # 单次列目录最多返回的文件数

# 列目录时忽略的目录/文件模式（精确目录名）
_LIST_EXCLUDES = {
    ".git", ".venv", "venv", "__pycache__", "node_modules",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist", "build",
    ".cursor",
}


def _grep_search(
    pattern: str,
    path: str = ".",
    case_sensitive: bool = True,
    include: str = "",
) -> str:
    """
    在指定目录或文件中搜索正则表达式匹配的行。

    优先使用 rg（ripgrep），不存在时回退到 Python re 逐行扫描。
    返回格式：filename:line_number:line_content，每行一条。
    """
    search_path = Path(path)
    if not search_path.exists():
        return "错误：路径不存在 → " + path

    # ── 尝试 rg ──────────────────────────────────────────────
    if shutil.which("rg"):
        cmd = ["rg", "--line-number", "--no-heading", "--color=never"]
        if not case_sensitive:
            cmd.append("--ignore-case")
        if include:
            cmd += ["--glob", include]
        cmd += [pattern, str(search_path)]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15
            )
            lines = result.stdout.splitlines()[:_GREP_MAX_RESULTS]
            if not lines:
                return "（未找到匹配）"
            suffix = ""
            if len(result.stdout.splitlines()) > _GREP_MAX_RESULTS:
                suffix = "\n[结果已截断，仅显示前 " + str(_GREP_MAX_RESULTS) + " 条]"
            return "\n".join(lines) + suffix
        except subprocess.TimeoutExpired:
            pass  # 超时则回退 Python 实现

    # ── Python re 回退实现 ────────────────────────────────────
    try:
        flags = 0 if case_sensitive else re.IGNORECASE
        compiled = re.compile(pattern, flags)
    except re.error as e:
        return "错误：无效正则表达式 → " + str(e)

    # 确定要扫描的文件列表
    if search_path.is_file():
        candidates = [search_path]
    else:
        glob_pat = include if include else "**/*"
        candidates = [p for p in search_path.glob(glob_pat) if p.is_file()]
        # 排除忽略目录
        candidates = [
            p for p in candidates
            if not any(part in _LIST_EXCLUDES for part in p.parts)
        ]

    results: list[str] = []
    for file_path in sorted(candidates):
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if compiled.search(line):
                results.append(str(file_path) + ":" + str(lineno) + ":" + line)
                if len(results) >= _GREP_MAX_RESULTS:
                    return "\n".join(results) + "\n[结果已截断，仅显示前 " + str(_GREP_MAX_RESULTS) + " 条]"

    return "\n".join(results) if results else "（未找到匹配）"


def _list_files(path: str = ".", pattern: str = "") -> str:
    """
    列出目录下的文件树，自动过滤常见无关目录（.git、.venv 等）。

    pattern：glob 过滤，如 "*.py"、"src/**/*.ts"。
    返回相对路径列表，超过 _LIST_MAX_RESULTS 条时截断。
    """
    root = Path(path)
    if not root.exists():
        return "错误：路径不存在 → " + path
    if root.is_file():
        return str(root)

    glob_pat = ("**/" + pattern) if pattern and "/" not in pattern else (pattern or "**/*")
    all_files: list[Path] = []

    for p in root.glob(glob_pat):
        if not p.is_file():
            continue
        # 过滤黑名单目录
        rel = p.relative_to(root)
        if any(part in _LIST_EXCLUDES for part in rel.parts):
            continue
        all_files.append(rel)

    all_files.sort()

    if not all_files:
        return "（目录为空或无匹配文件）"

    lines = [str(f) for f in all_files[:_LIST_MAX_RESULTS]]
    suffix = ""
    if len(all_files) > _LIST_MAX_RESULTS:
        suffix = "\n[已截断，共 " + str(len(all_files)) + " 个文件，仅显示前 " + str(_LIST_MAX_RESULTS) + " 个]"
    return "\n".join(lines) + suffix


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
            "name": "grep_search",
            "description": "在目录或文件中搜索正则表达式匹配的行，返回 filename:line:content 格式",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "要搜索的正则表达式（如 'def run_.*' 或字面字符串）",
                    },
                    "path": {
                        "type": "string",
                        "description": "搜索的目录或文件路径，默认当前目录",
                        "default": ".",
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "是否区分大小写，默认 true",
                        "default": True,
                    },
                    "include": {
                        "type": "string",
                        "description": "文件名 glob 过滤，如 '*.py'、'*.{ts,tsx}'",
                        "default": "",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "列出目录下的所有文件（自动过滤 .git、.venv、__pycache__ 等无关目录）",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要列出的目录路径，默认当前目录",
                        "default": ".",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "glob 过滤模式，如 '*.py'，默认列出所有文件",
                        "default": "",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_tool_result",
            "description": (
                "读取此前某次工具调用的完整缓存结果。"
                "当之前工具返回较大内容时，agent 只看到预览版本；若需要查看未显示的部分，"
                "使用本工具并指定该次调用的 call_id 和 offset。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "call_id": {
                        "type": "string",
                        "description": "要查询的工具调用 ID（从预览末尾的提示中获取）",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "起始字符偏移量，默认 0",
                        "default": 0,
                    },
                    "length": {
                        "type": "integer",
                        "description": "读取长度（字符数），默认 3000",
                        "default": 3000,
                    },
                },
                "required": ["call_id"],
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
    "read_file":   lambda args: _read_file(args["path"]),
    "write_file":  lambda args: _write_file(args["path"], args["content"]),
    "edit_file":   lambda args: _edit_file(args["path"], args["old_string"], args["new_string"]),
    "grep_search": lambda args: _grep_search(
        args["pattern"],
        args.get("path", "."),
        args.get("case_sensitive", True),
        args.get("include", ""),
    ),
    "list_files":  lambda args: _list_files(
        args.get("path", "."),
        args.get("pattern", ""),
    ),
    "read_tool_result": lambda args: _read_tool_result(
        args["call_id"],
        args.get("offset", 0),
        args.get("length", 3000),
    ),
    "run_shell":   lambda args: _run_shell(args["command"], args.get("timeout", 30)),
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
