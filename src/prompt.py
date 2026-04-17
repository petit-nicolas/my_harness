"""
提示词组装器

负责将 system_prompt.md 中的占位符替换为真实的运行时信息，
最终返回一个可以直接传给 API 的完整系统提示字符串。
"""
import os
import platform
import subprocess
from datetime import datetime
from pathlib import Path


# system_prompt.md 与本文件同目录
_TEMPLATE_PATH = Path(__file__).parent / "system_prompt.md"


def get_git_context(cwd: str | None = None) -> str:
    """
    获取指定目录（默认为当前目录）的 git 状态信息。
    读取的是 agent 正在工作的目标项目，而不是 Harness 源码目录。
    非 git 仓库时返回空字符串。
    """
    work_dir = cwd or os.getcwd()
    run = lambda args: subprocess.run(
        args, capture_output=True, text=True, timeout=3, cwd=work_dir
    )

    try:
        if run(["git", "rev-parse", "--is-inside-work-tree"]).returncode != 0:
            return ""

        user   = run(["git", "config", "user.name"]).stdout.strip()
        branch = run(["git", "branch", "--show-current"]).stdout.strip()
        log    = run(["git", "log", "--oneline", "-3"]).stdout.strip()
        status = run(["git", "status", "--short"]).stdout.strip()

        lines = ["## Git 上下文", ""]
        if user:
            lines.append(f"用户：{user}，当前分支：{branch}")
        if log:
            lines.append(f"\n最近提交：\n```\n{log}\n```")
        if status:
            lines.append(f"\n工作区变更：\n```\n{status}\n```")

        return "\n".join(lines)

    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def load_claude_md(start_dir: str | None = None) -> str:
    """
    从当前目录向上递归查找 CLAUDE.md，找到后返回其内容。
    找不到时返回空字符串。
    """
    search_dir = Path(start_dir or os.getcwd())

    # 向上最多搜索 5 层
    for _ in range(5):
        candidate = search_dir / "CLAUDE.md"
        if candidate.exists():
            content = candidate.read_text(encoding="utf-8").strip()
            return f"## 项目约定（来自 CLAUDE.md）\n\n{content}"
        parent = search_dir.parent
        if parent == search_dir:
            break
        search_dir = parent

    return ""


def load_memories_context() -> str:
    """
    读取 ~/.harness/memory/MEMORY.md 中的所有记忆，
    格式化为可注入 system prompt 的文本块。
    记忆库为空时返回空字符串。
    """
    try:
        from src.memory import load_memories, format_for_prompt
        entries = load_memories()
        return format_for_prompt(entries)
    except Exception:
        return ""


def build_system_prompt(cwd: str | None = None) -> str:
    """
    读取 system_prompt.md 模板，将所有占位符替换为实际值，
    返回完整的系统提示字符串。
    """
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")

    current_dir = cwd or os.getcwd()
    git_ctx = get_git_context(current_dir)   # 与 cwd 保持一致，读目标项目
    claude_md = load_claude_md(current_dir)
    memories = load_memories_context()

    replacements = {
        "{{cwd}}":         current_dir,
        "{{date}}":        datetime.now().strftime("%Y-%m-%d %H:%M"),
        "{{platform}}":    platform.system(),
        "{{shell}}":       os.environ.get("SHELL", "unknown"),
        "{{git_context}}": git_ctx,
        "{{memories}}":    memories,
        "{{claude_md}}":   claude_md,
    }

    result = template
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)

    # 清理多余空行（连续超过 2 个空行时压缩为 2 个）
    import re
    result = re.sub(r"\n{3,}", "\n\n", result)

    return result.strip()
