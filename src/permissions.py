"""
权限与安全检查模块

在工具执行前进行风险评估，识别破坏性操作并返回风险描述。
外部调用者（CLI / Dashboard）决定是否继续。

设计原则：
- 只检测，不拦截 —— 决策权留给调用方
- 规则明确，误报率低 —— 宁可放过，不要频繁打扰
- 路径缓存 —— 用户对某个路径授权后本轮不再询问
"""
import re
from dataclasses import dataclass, field
from pathlib import Path


# ── 危险 shell 命令规则 ─────────────────────────────────────
# 每条规则：(风险描述, 编译后的正则)
# 顺序从高风险到低风险

_SHELL_RULES: list[tuple[str, re.Pattern]] = [
    (
        "递归强制删除文件",
        re.compile(r"\brm\b[^|]*-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r", re.IGNORECASE),
    ),
    (
        "删除文件或目录",
        re.compile(r"\brm\s+\S", re.IGNORECASE),
    ),
    (
        "磁盘低级写入（dd）",
        re.compile(r"\bdd\b.*\bof=", re.IGNORECASE),
    ),
    (
        "格式化磁盘（mkfs）",
        re.compile(r"\bmkfs\b", re.IGNORECASE),
    ),
    (
        "提权执行（sudo / su）",
        re.compile(r"\b(sudo|su)\b"),
    ),
    (
        "写入系统目录（/etc /usr /bin 等）",
        re.compile(r">\s*/(etc|usr|bin|sbin|boot|sys|dev|root)/"),
    ),
    (
        "管道到 shell 执行（curl | bash 等）",
        re.compile(r"\|\s*(bash|sh|zsh|fish)\b"),
    ),
    (
        "从网络直接执行脚本",
        re.compile(r"\b(curl|wget)\b.*\|\s*(bash|sh|python3?)\b", re.IGNORECASE),
    ),
    (
        "移动或重命名系统文件",
        re.compile(r"\bmv\b.*/(etc|usr|bin|sbin|boot)/", re.IGNORECASE),
    ),
    (
        "修改文件权限为全开放（chmod 7xx / a+w）",
        re.compile(r"\bchmod\b.*(7[0-7][0-7]|a\+[wx])", re.IGNORECASE),
    ),
]

# ── 危险文件路径（写操作检查）─────────────────────────────
_SENSITIVE_PATH_PREFIXES: tuple[str, ...] = (
    "/etc/", "/usr/", "/bin/", "/sbin/",
    "/boot/", "/sys/", "/dev/", "/proc/", "/root/",
)

_SENSITIVE_FILENAMES: set[str] = {
    ".env", ".ENV",
    ".bashrc", ".zshrc", ".bash_profile", ".profile",
    ".ssh/authorized_keys", ".ssh/id_rsa",
    ".gitconfig",
    "shadow", "passwd",   # /etc/ 下的高风险文件
}


# ── 检查函数 ─────────────────────────────────────────────────

@dataclass
class RiskResult:
    """检查结果"""
    is_risky: bool
    reason: str = ""           # 可读的风险原因，is_risky=False 时为空
    level: str = "low"         # "low" | "medium" | "high"


def check_shell_command(command: str) -> RiskResult:
    """
    检查 shell 命令是否含危险操作。

    Returns:
        RiskResult，is_risky=True 时包含 reason 和 level
    """
    for desc, pattern in _SHELL_RULES:
        if pattern.search(command):
            # 递归删除 / 磁盘操作 / 管道执行 → high；其余 → medium
            level = "high" if any(
                kw in desc for kw in ("递归", "磁盘", "管道", "脚本")
            ) else "medium"
            return RiskResult(is_risky=True, reason=desc, level=level)
    return RiskResult(is_risky=False)


def check_file_path(path: str, operation: str = "写入") -> RiskResult:
    """
    检查文件路径是否属于敏感位置。

    Args:
        path:      文件路径（绝对或相对）
        operation: 操作描述，用于组织提示文字
    """
    resolved = str(Path(path).resolve())
    # 同时保留原始路径用于匹配（macOS /etc → /private/etc 符号链接问题）
    original = str(Path(path))

    # 检查系统目录前缀
    for prefix in _SENSITIVE_PATH_PREFIXES:
        if resolved.startswith(prefix) or original.startswith(prefix):
            return RiskResult(
                is_risky=True,
                reason=f"{operation}系统目录文件：{resolved}",
                level="high",
            )

    # 检查敏感文件名
    filename = Path(path).name
    for sensitive in _SENSITIVE_FILENAMES:
        if filename == sensitive or path.endswith("/" + sensitive):
            return RiskResult(
                is_risky=True,
                reason=f"{operation}敏感配置文件：{path}",
                level="medium",
            )

    return RiskResult(is_risky=False)


# ── 路径授权缓存 ─────────────────────────────────────────────

@dataclass
class PermissionCache:
    """
    本轮会话的授权缓存。

    用户对某个工具+路径/命令组合授权后，本轮不再重复询问。
    使用 frozenset key = (tool_name, normalized_key)。
    """
    _approved: set[str] = field(default_factory=set)

    def _key(self, tool: str, target: str) -> str:
        return tool + ":" + target.strip()

    def is_approved(self, tool: str, target: str) -> bool:
        return self._key(tool, target) in self._approved

    def approve(self, tool: str, target: str) -> None:
        self._approved.add(self._key(tool, target))

    def clear(self) -> None:
        self._approved.clear()


# ── 统一入口 ─────────────────────────────────────────────────

def assess_tool_call(
    tool_name: str,
    arguments: dict,
    cache: PermissionCache | None = None,
) -> RiskResult:
    """
    评估一次工具调用的风险。

    Args:
        tool_name:  工具名称
        arguments:  工具参数
        cache:      授权缓存，命中时直接返回 is_risky=False

    Returns:
        RiskResult（is_risky=False 表示可直接执行）
    """
    if tool_name == "run_shell":
        command = arguments.get("command", "")
        result = check_shell_command(command)
        if result.is_risky:
            if cache and cache.is_approved("run_shell", command):
                return RiskResult(is_risky=False)
        return result

    if tool_name in ("write_file", "edit_file"):
        path = arguments.get("path", "")
        result = check_file_path(path)
        if result.is_risky:
            if cache and cache.is_approved(tool_name, path):
                return RiskResult(is_risky=False)
        return result

    return RiskResult(is_risky=False)
