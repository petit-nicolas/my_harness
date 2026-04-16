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


def get_git_context() -> str:
    """获取当前目录的 git 状态信息，非 git 仓库时返回空字符串"""
    try:
        # 检测是否在 git 仓库中
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode != 0:
            return ""

        # 获取用户名
        user = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True, text=True, timeout=3
        ).stdout.strip()

        # 获取当前分支
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, timeout=3
        ).stdout.strip()

        # 获取最近 3 条提交
        log = subprocess.run(
            ["git", "log", "--oneline", "-3"],
            capture_output=True, text=True, timeout=3
        ).stdout.strip()

        # 获取工作区状态摘要
        status = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True, text=True, timeout=3
        ).stdout.strip()

        lines = [f"## Git 上下文", f""]
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
            return f"## 项目上下文（来自 CLAUDE.md）\n\n{content}"
        parent = search_dir.parent
        if parent == search_dir:
            break
        search_dir = parent

    return ""


def build_system_prompt(cwd: str | None = None) -> str:
    """
    读取 system_prompt.md 模板，将所有占位符替换为实际值，
    返回完整的系统提示字符串。
    """
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")

    current_dir = cwd or os.getcwd()
    git_ctx = get_git_context()
    claude_md = load_claude_md(current_dir)

    replacements = {
        "{{cwd}}":         current_dir,
        "{{date}}":        datetime.now().strftime("%Y-%m-%d %H:%M"),
        "{{platform}}":    platform.system(),
        "{{shell}}":       os.environ.get("SHELL", "unknown"),
        "{{git_context}}": git_ctx,
        "{{claude_md}}":   claude_md,
    }

    result = template
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)

    # 清理多余空行（连续超过 2 个空行时压缩为 2 个）
    import re
    result = re.sub(r"\n{3,}", "\n\n", result)

    return result.strip()
