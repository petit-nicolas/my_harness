"""
Hooks 扩展机制

在工具执行前/后插入自定义回调，类似 Claude Code 的 hooks 系统。

设计目标：
- pre_tool_use  钩子：执行前检查/日志/审计；返回 False 可阻止执行
- post_tool_use 钩子：执行后处理/转换/记录结果

使用方式：
    from src.hooks import HOOKS, HookEvent

    # 注册一个日志钩子
    @HOOKS.pre_tool_use
    def my_logger(event: HookEvent) -> bool | None:
        print(f"[pre] {event.tool_name}({event.arguments})")
        return True   # 或 None，表示允许继续

    # 注册一个结果转换钩子
    @HOOKS.post_tool_use
    def my_post(event: HookEvent) -> str | None:
        if event.tool_name == "run_shell":
            return "[已记录] " + (event.result or "")
        return None   # None 表示不修改结果

典型内置钩子（通过 register_defaults() 注册）：
- audit_log：将每次工具调用追加到 ~/.harness/audit.log
- stats_counter：统计各工具调用次数（本次会话）
"""
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

# ── 数据结构 ──────────────────────────────────────────────────

@dataclass
class HookEvent:
    """
    钩子事件，携带工具调用的上下文。
    pre 阶段 result=None；post 阶段 result 为工具实际返回值。
    """
    tool_name: str
    arguments: dict
    result: str | None = None         # post 阶段填充
    phase: str = "pre"                # "pre" | "post"
    timestamp: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )
    metadata: dict = field(default_factory=dict)  # 供钩子间传递数据


# 钩子函数类型
# pre 钩子：返回 False 阻止工具执行；返回 True / None 允许继续
# post 钩子：返回字符串则替换原始结果；返回 None 保持原结果
PreHookFn  = Callable[[HookEvent], bool | None]
PostHookFn = Callable[[HookEvent], str | None]


# ── 钩子注册表 ────────────────────────────────────────────────

class HookRegistry:
    """
    全局钩子注册表。

    通常只使用单例 HOOKS，也可在测试中实例化独立注册表。
    """
    def __init__(self) -> None:
        self._pre:  list[PreHookFn]  = []
        self._post: list[PostHookFn] = []

    # ── 装饰器风格注册 ────────────────────────────────────────

    def pre_tool_use(self, fn: PreHookFn) -> PreHookFn:
        """将函数注册为 pre_tool_use 钩子（可作装饰器使用）"""
        self._pre.append(fn)
        return fn

    def post_tool_use(self, fn: PostHookFn) -> PostHookFn:
        """将函数注册为 post_tool_use 钩子（可作装饰器使用）"""
        self._post.append(fn)
        return fn

    # ── 函数式注册（不使用装饰器时） ────────────────────────

    def register_pre(self, fn: PreHookFn) -> None:
        self._pre.append(fn)

    def register_post(self, fn: PostHookFn) -> None:
        self._post.append(fn)

    def clear(self) -> None:
        """清空所有注册的钩子（主要用于测试）"""
        self._pre.clear()
        self._post.clear()

    # ── 执行 ─────────────────────────────────────────────────

    def run_pre(self, tool_name: str, arguments: dict) -> tuple[bool, str]:
        """
        运行所有 pre_tool_use 钩子。

        Returns:
            (allowed, reason)
            allowed=False 时 reason 说明哪个钩子阻止了执行
        """
        event = HookEvent(tool_name=tool_name, arguments=arguments, phase="pre")
        for fn in self._pre:
            try:
                result = fn(event)
                if result is False:
                    return False, f"[hook:{fn.__name__}] 阻止执行 {tool_name}"
            except Exception as e:
                # 钩子异常不中断 agent，仅记录
                _log_hook_error(fn.__name__, "pre", e)
        return True, ""

    def run_post(self, tool_name: str, arguments: dict, result: str) -> str:
        """
        运行所有 post_tool_use 钩子，允许链式修改结果。

        Returns:
            最终工具结果字符串（经过所有钩子处理后）
        """
        event = HookEvent(tool_name=tool_name, arguments=arguments, result=result, phase="post")
        current = result
        for fn in self._post:
            try:
                modified = fn(event)
                if modified is not None:
                    current = modified
                    event.result = current   # 让下一个钩子看到最新结果
            except Exception as e:
                _log_hook_error(fn.__name__, "post", e)
        return current

    @property
    def pre_count(self) -> int:
        return len(self._pre)

    @property
    def post_count(self) -> int:
        return len(self._post)


def _log_hook_error(hook_name: str, phase: str, exc: Exception) -> None:
    """钩子异常不中断流程，静默记录到日志"""
    try:
        _AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with _AUDIT_LOG.open("a", encoding="utf-8") as f:
            f.write(
                f"[{datetime.now().isoformat(timespec='seconds')}]"
                f" HOOK_ERROR phase={phase} hook={hook_name} err={exc}\n"
            )
    except Exception:
        pass


# ── 全局单例 ──────────────────────────────────────────────────

HOOKS = HookRegistry()

_AUDIT_LOG = Path.home() / ".harness" / "audit.log"
_SESSION_STATS: dict[str, int] = {}   # tool_name → 调用次数


# ── 内置默认钩子 ──────────────────────────────────────────────

def _audit_log_pre(event: HookEvent) -> None:
    """记录每次工具调用到 ~/.harness/audit.log"""
    try:
        _AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        # 参数中的长字符串截断，避免日志膨胀
        args_preview = {
            k: (v[:120] + "…" if isinstance(v, str) and len(v) > 120 else v)
            for k, v in event.arguments.items()
        }
        line = (
            f"[{event.timestamp}] PRE  {event.tool_name}"
            f" args={json.dumps(args_preview, ensure_ascii=False)}\n"
        )
        with _AUDIT_LOG.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def _audit_log_post(event: HookEvent) -> None:
    """记录工具执行结果摘要到 audit.log"""
    try:
        result_preview = (event.result or "")[:80].replace("\n", "\\n")
        line = (
            f"[{event.timestamp}] POST {event.tool_name}"
            f" result_len={len(event.result or '')} preview={result_preview!r}\n"
        )
        with _AUDIT_LOG.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def _stats_counter_pre(event: HookEvent) -> None:
    """统计本次会话各工具调用次数"""
    _SESSION_STATS[event.tool_name] = _SESSION_STATS.get(event.tool_name, 0) + 1


def register_defaults() -> None:
    """
    注册内置默认钩子。
    由 cli.py / main.py 在启动时调用一次。
    """
    HOOKS.register_pre(_audit_log_pre)
    HOOKS.register_pre(_stats_counter_pre)
    HOOKS.register_post(_audit_log_post)


def get_session_stats() -> dict[str, int]:
    """返回本次会话工具调用统计（副本）"""
    return dict(_SESSION_STATS)


def reset_session_stats() -> None:
    """清空统计（用于 /clear 命令）"""
    _SESSION_STATS.clear()


def audit_log_path() -> Path:
    """返回 audit.log 路径（供 UI 展示）"""
    return _AUDIT_LOG
