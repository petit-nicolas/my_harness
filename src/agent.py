"""
Agent 主循环

协调提示词、API 调用、工具执行三者的工作流。
核心结构：

    构建消息
      ↓
    调用 API
      ↓
    while True:
      有 tool_calls → 执行工具 → 追加结果 → 再次调用 API
      无 tool_calls → 输出文本 → break
"""
import json
import os
import signal
import threading
from dataclasses import dataclass, field
from typing import Callable

from src.client import chat, DEFAULT_MODEL
from src.permissions import PermissionCache, assess_tool_call
from src.prompt import build_system_prompt
from src.tools import TOOLS, run_tool


# ── 会话状态 ────────────────────────────────────────────────

@dataclass
class TokenUsage:
    """累计 Token 用量"""
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def add(self, usage) -> None:
        """从 API 响应的 usage 对象累加"""
        if usage:
            self.prompt_tokens += usage.prompt_tokens or 0
            self.completion_tokens += usage.completion_tokens or 0


@dataclass
class AgentSession:
    """单次 Agent 会话的完整状态"""
    messages: list[dict] = field(default_factory=list)
    usage: TokenUsage = field(default_factory=TokenUsage)
    cwd: str = field(default_factory=os.getcwd)
    perm_cache: PermissionCache = field(default_factory=PermissionCache)

    def add_user(self, text: str) -> None:
        self.messages.append({"role": "user", "content": text})

    def add_assistant(self, msg) -> None:
        """追加 assistant 消息（含或不含 tool_calls）"""
        # openai SDK 的 message 对象需要转成 dict
        entry: dict = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            entry["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        self.messages.append(entry)

    def add_tool_result(self, tool_call_id: str, result: str) -> None:
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": result,
        })


# ── 主循环 ──────────────────────────────────────────────────

def run_agent(
    session: AgentSession,
    user_input: str,
    model: str = DEFAULT_MODEL,
    on_text: Callable[[str], None] | None = None,
    on_tool_call: Callable[[str, dict], None] | None = None,
    on_tool_result: Callable[[str, str], None] | None = None,
    confirm_fn: Callable[[str, str, dict], bool] | None = None,
    stop_event: threading.Event | None = None,
) -> str:
    """
    执行一轮完整的 Agent 对话。

    Args:
        session:        当前会话状态（消息历史、Token 用量、授权缓存）
        user_input:     本轮用户输入
        model:          使用的模型名称
        on_text:        收到模型文本时的回调（用于实时打印）
        on_tool_call:   工具被触发时的回调（工具名, 参数）
        on_tool_result: 工具执行完成时的回调（工具名, 结果）
        confirm_fn:     危险操作确认回调 (tool_name, risk_reason, arguments) → bool
                        返回 True=继续执行，False=跳过。
                        为 None 时跳过安全检查（--yolo 模式）。
        stop_event:     Ctrl+C 中断信号，置位后跳出循环

    Returns:
        模型最终的文本回复
    """
    # 第一轮：加入系统提示 + 用户消息
    system_prompt = build_system_prompt(session.cwd)
    full_messages = [
        {"role": "system", "content": system_prompt},
        *session.messages,
    ]
    session.add_user(user_input)
    full_messages.append({"role": "user", "content": user_input})

    final_text = ""

    while True:
        # 检查中断信号
        if stop_event and stop_event.is_set():
            return "[已中断]"

        # 调用 API
        response = chat(full_messages, model=model, tools=TOOLS)
        session.usage.add(response.usage)

        msg = response.choices[0].message
        finish_reason = response.choices[0].finish_reason

        # 追加到会话历史
        session.add_assistant(msg)
        full_messages.append({
            "role": "assistant",
            "content": msg.content or "",
            **({"tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ]} if msg.tool_calls else {}),
        })

        # 有工具调用 → 执行并追加结果，继续循环
        if finish_reason == "tool_calls" and msg.tool_calls:
            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    arguments = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}

                if on_tool_call:
                    on_tool_call(name, arguments)

                # 安全检查：confirm_fn=None 表示 yolo 模式，直接执行
                if confirm_fn is not None:
                    risk = assess_tool_call(name, arguments, session.perm_cache)
                    if risk.is_risky:
                        allowed = confirm_fn(name, risk.reason, arguments)
                        if allowed:
                            # 缓存授权，本轮同样操作不再询问
                            target = arguments.get("command") or arguments.get("path", "")
                            session.perm_cache.approve(name, target)
                        else:
                            result = "[已跳过：用户拒绝执行 " + name + "（" + risk.reason + "）]"
                            if on_tool_result:
                                on_tool_result(name, result)
                            session.add_tool_result(tc.id, result)
                            full_messages.append({
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "content": result,
                            })
                            continue

                result = run_tool(name, arguments)

                if on_tool_result:
                    on_tool_result(name, result)

                session.add_tool_result(tc.id, result)
                full_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
            continue  # 继续循环，把工具结果送回给模型

        # 无工具调用 → 这是最终文本回复
        final_text = msg.content or ""
        if on_text:
            on_text(final_text)
        break

    return final_text
