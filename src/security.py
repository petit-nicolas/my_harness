"""
规则化安全策略模块（Step 11）

在 permissions.py（硬编码规则）基础上增加：
- 从 ~/.harness/settings.json 读取用户自定义规则
- Shell 命令白名单 / 黑名单（glob 模式匹配）
- 文件路径可信目录 / 写入黑名单
- 策略查询：assess_policy()，与 permissions.assess_tool_call 协同工作

settings.json 格式：
{
    "version": 1,
    "shell": {
        "allow": ["git *", "pytest *", "python *", "pip *"],
        "block": ["rm -rf *", "sudo *"],
        "always_confirm": []
    },
    "files": {
        "trusted_paths": ["/Users/me/projects/", "~/workspace/"],
        "block_write": ["/etc/*", "~/.ssh/*", "~/.aws/*"]
    }
}

策略优先级（从高到低）：
  1. files.block_write  → 强制拒绝（无法绕过，即使 --yolo）
  2. shell.block        → 强制拒绝
  3. shell.allow        → 直接放行（跳过 permissions.py 的危险检查）
  4. files.trusted_paths→ 文件操作直接放行
  5. 无匹配             → 交由 permissions.py 的原有逻辑判断
"""
import fnmatch
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

_SETTINGS_PATH = Path.home() / ".harness" / "settings.json"

# 默认设置（用户未配置时的兜底）
_DEFAULT_SETTINGS: dict = {
    "version": 1,
    "shell": {
        "allow": [
            "git *", "git status", "git log*", "git diff*",
            "pytest*", "python *", "python3 *", "pip *", "pip3 *",
            "ls *", "ls", "cat *", "echo *", "pwd", "which *",
            "rg *", "grep *", "find *", "head *", "tail *",
        ],
        "block": [],
        "always_confirm": [],
    },
    "files": {
        "trusted_paths": [],
        "block_write": [
            "/etc/*", "/usr/*", "/bin/*", "/sbin/*",
            "~/.ssh/*", "~/.aws/credentials",
        ],
    },
}


# ── 设置加载 ──────────────────────────────────────────────────

def load_settings() -> dict:
    """
    加载 ~/.harness/settings.json。
    文件不存在时返回默认设置；格式错误时同样回退到默认。
    """
    if not _SETTINGS_PATH.exists():
        return _DEFAULT_SETTINGS.copy()
    try:
        data = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        # 深度合并：用户只需填写想覆盖的字段
        return _deep_merge(_DEFAULT_SETTINGS, data)
    except Exception:
        return _DEFAULT_SETTINGS.copy()


def save_settings(settings: dict) -> None:
    """将设置写入 ~/.harness/settings.json"""
    _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_PATH.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def init_settings() -> None:
    """初始化 settings.json（仅在文件不存在时创建）"""
    if not _SETTINGS_PATH.exists():
        save_settings(_DEFAULT_SETTINGS)


def _deep_merge(base: dict, override: dict) -> dict:
    """递归合并，override 优先；list 类型直接替换（不追加）"""
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


# ── 策略判定 ──────────────────────────────────────────────────

class PolicyDecision(Enum):
    ALLOW   = "allow"    # 直接放行
    BLOCK   = "block"    # 强制拒绝
    CONFIRM = "confirm"  # 需要用户确认
    DEFER   = "defer"    # 无规则命中，交给 permissions.py 判断


@dataclass
class PolicyResult:
    decision: PolicyDecision
    reason: str = ""


def _glob_match(pattern: str, text: str) -> bool:
    """用 fnmatch 做 glob 匹配，支持 ~ 展开"""
    pattern = str(Path(pattern).expanduser()) if pattern.startswith("~") else pattern
    text    = str(Path(text).expanduser())    if text.startswith("~")    else text
    return fnmatch.fnmatch(text, pattern)


def _expand_path(p: str) -> str:
    return str(Path(p).expanduser().resolve())


def assess_shell_policy(command: str, settings: dict | None = None) -> PolicyResult:
    """
    根据 settings 中的 shell.allow / shell.block 规则判断策略。
    """
    s = settings or load_settings()
    shell_cfg = s.get("shell", {})

    # 1. 黑名单 → 强制 BLOCK
    for pattern in shell_cfg.get("block", []):
        if _glob_match(pattern, command) or fnmatch.fnmatch(command, pattern):
            return PolicyResult(PolicyDecision.BLOCK, f"命令匹配黑名单规则：{pattern}")

    # 2. 始终确认列表
    for pattern in shell_cfg.get("always_confirm", []):
        if _glob_match(pattern, command) or fnmatch.fnmatch(command, pattern):
            return PolicyResult(PolicyDecision.CONFIRM, f"命令需要确认（规则：{pattern}）")

    # 3. 白名单 → 直接放行
    for pattern in shell_cfg.get("allow", []):
        if fnmatch.fnmatch(command, pattern):
            return PolicyResult(PolicyDecision.ALLOW, f"命令匹配白名单规则：{pattern}")

    # 4. 无匹配 → 交给 permissions.py
    return PolicyResult(PolicyDecision.DEFER, "无策略规则匹配，交由内置检查")


def assess_file_policy(path: str, settings: dict | None = None) -> PolicyResult:
    """
    根据 settings 中的 files.block_write / trusted_paths 规则判断策略。
    """
    s = settings or load_settings()
    files_cfg = s.get("files", {})
    resolved = _expand_path(path)

    # 1. 写入黑名单 → 强制 BLOCK（优先级最高，--yolo 也不能跳过）
    for pattern in files_cfg.get("block_write", []):
        exp = str(Path(pattern).expanduser())
        if fnmatch.fnmatch(resolved, exp) or fnmatch.fnmatch(path, pattern):
            return PolicyResult(PolicyDecision.BLOCK, f"路径匹配写入黑名单：{pattern}")

    # 2. 可信目录 → 直接放行
    for trusted in files_cfg.get("trusted_paths", []):
        trusted_exp = _expand_path(trusted)
        if resolved.startswith(trusted_exp):
            return PolicyResult(PolicyDecision.ALLOW, f"路径在可信目录内：{trusted}")

    # 3. 无匹配 → 交给 permissions.py
    return PolicyResult(PolicyDecision.DEFER, "无策略规则匹配，交由内置检查")


def assess_policy(tool_name: str, arguments: dict) -> PolicyResult:
    """
    统一策略入口，供 agent.py 在 permissions.assess_tool_call 之前调用。

    Returns:
        PolicyResult
        - ALLOW  → 跳过后续 permissions 检查，直接执行
        - BLOCK  → 强制拒绝，不经过用户确认
        - CONFIRM→ 强制走确认流程
        - DEFER  → 交给 permissions.assess_tool_call 判断
    """
    if tool_name == "run_shell":
        return assess_shell_policy(arguments.get("command", ""))
    if tool_name in ("write_file", "edit_file"):
        return assess_file_policy(arguments.get("path", ""))
    return PolicyResult(PolicyDecision.DEFER, "非受控工具类型")


# ── 工具函数（供 UI / CLI 使用） ─────────────────────────────

def settings_path() -> Path:
    return _SETTINGS_PATH


def add_to_allow(pattern: str) -> None:
    """将命令模式添加到 shell.allow 白名单"""
    s = load_settings()
    s.setdefault("shell", {}).setdefault("allow", [])
    if pattern not in s["shell"]["allow"]:
        s["shell"]["allow"].append(pattern)
    save_settings(s)


def add_to_block(pattern: str) -> None:
    """将命令模式添加到 shell.block 黑名单"""
    s = load_settings()
    s.setdefault("shell", {}).setdefault("block", [])
    if pattern not in s["shell"]["block"]:
        s["shell"]["block"].append(pattern)
    save_settings(s)


def add_trusted_path(path: str) -> None:
    """将目录添加到 files.trusted_paths"""
    s = load_settings()
    s.setdefault("files", {}).setdefault("trusted_paths", [])
    expanded = str(Path(path).expanduser())
    if expanded not in s["files"]["trusted_paths"]:
        s["files"]["trusted_paths"].append(expanded)
    save_settings(s)
