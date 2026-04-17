"""
Agent 主循环

协调提示词、API 调用、工具执行三者的工作流。
核心结构：

    构建消息
      ↓
    调用 API（非流式 or 流式）
      ↓
    while True:
      有 tool_calls → 执行工具 → 追加结果 → 再次调用 API
      无 tool_calls → 输出文本 → break

流式模式（stream=True）：
  - 文本 delta 实时通过 on_text_chunk 回调推送
  - tool_calls delta 累加后再执行
  - token 用量从最后一个 chunk 的 usage 字段获取
"""
import json
import os
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

    def add_assistant_stream(self, text: str, tool_calls: list[dict]) -> None:
        """追加流式累加后的 assistant 消息"""
        entry: dict = {"role": "assistant", "content": text}
        if tool_calls:
            entry["tool_calls"] = tool_calls
        self.messages.append(entry)

    def add_tool_result(self, tool_call_id: str, result: str) -> None:
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": result,
        })


# ── 流式响应累加器 ───────────────────────────────────────────

def _collect_stream(
    stream,
    on_text_chunk: Callable[[str], None] | None = None,
    stop_event: threading.Event | None = None,
) -> tuple[str, list[dict], str, object]:
    """
    消费一个流式响应，累加文本和工具调用。

    Returns:
        (full_text, tool_calls_list, finish_reason, usage)

    tool_calls_list 格式与非流式一致：
        [{"id": ..., "type": "function", "function": {"name": ..., "arguments": ...}}]
    """
    text_parts: list[str] = []
    # index → 累加中的 tool call 字典
    tc_map: dict[int, dict] = {}
    finish_reason = "stop"
    last_usage = None

    for chunk in stream:
        if stop_event and stop_event.is_set():
            break

        choice = chunk.choices[0] if chunk.choices else None
        if not choice:
            continue

        if choice.finish_reason:
            finish_reason = choice.finish_reason

        delta = choice.delta

        # 文本块
        if delta.content:
            text_parts.append(delta.content)
            if on_text_chunk:
                on_text_chunk(delta.content)

        # 工具调用块：按 index 累加
        if delta.tool_calls:
            for tc_chunk in delta.tool_calls:
                idx = tc_chunk.index
                if idx not in tc_map:
                    tc_map[idx] = {
                        "id": tc_chunk.id or "",
                        "type": "function",
                        "function": {
                            "name": (tc_chunk.function.name or "") if tc_chunk.function else "",
                            "arguments": (tc_chunk.function.arguments or "") if tc_chunk.function else "",
                        },
                    }
                else:
                    if tc_chunk.id:
                        tc_map[idx]["id"] = tc_chunk.id
                    if tc_chunk.function:
                        if tc_chunk.function.name:
                            tc_map[idx]["function"]["name"] += tc_chunk.function.name
                        if tc_chunk.function.arguments:
                            tc_map[idx]["function"]["arguments"] += tc_chunk.function.arguments

        # 最后一个 chunk 通常带有 usage（需 stream_options={"include_usage": true}）
        if hasattr(chunk, "usage") and chunk.usage:
            last_usage = chunk.usage

    tool_calls_list = [tc_map[i] for i in sorted(tc_map.keys())]
    full_text = "".join(text_parts)
    return full_text, tool_calls_list, finish_reason, last_usage


# ── 主循环 ──────────────────────────────────────────────────

def run_agent(
    session: AgentSession,
    user_input: str,
    model: str = DEFAULT_MODEL,
    stream: bool = True,
    on_text: Callable[[str], None] | None = None,
    on_text_chunk: Callable[[str], None] | None = None,
    on_tool_call: Callable[[str, dict], None] | None = None,
    on_tool_result: Callable[[str, str], None] | None = None,
    confirm_fn: Callable[[str, str, dict], bool] | None = None,
    stop_event: threading.Event | None = None,
) -> str:
    """
    执行一轮完整的 Agent 对话（支持流式 / 非流式）。

    Args:
        session:        当前会话状态（消息历史、Token 用量、授权缓存）
        user_input:     本轮用户输入
        model:          使用的模型名称
        stream:         True=流式输出（默认），False=等待完整响应
        on_text:        收到完整文本时的回调（流式模式在结束后也会触发）
        on_text_chunk:  流式模式下每个文本 delta 的回调
        on_tool_call:   工具被触发时的回调（工具名, 参数）
        on_tool_result: 工具执行完成时的回调（工具名, 结果）
        confirm_fn:     危险操作确认回调；None 跳过检查（--yolo）
        stop_event:     Ctrl+C 中断信号

    Returns:
        模型最终的文本回复
    """
    system_prompt = build_system_prompt(session.cwd)
    full_messages = [
        {"role": "system", "content": system_prompt},
        *session.messages,
    ]
    session.add_user(user_input)
    full_messages.append({"role": "user", "content": user_input})

    final_text = ""

    while True:
        if stop_event and stop_event.is_set():
            return "[已中断]"

        # ── 调用 API ───────────────────────────────────────
        if stream:
            raw = chat(full_messages, model=model, tools=TOOLS, stream=True)
            full_text, tool_calls_list, finish_reason, usage = _collect_stream(
                raw, on_text_chunk=on_text_chunk, stop_event=stop_event
            )
            session.usage.add(usage)

            # 构建 assistant 消息并追加
            session.add_assistant_stream(full_text, tool_calls_list)
            assistant_msg: dict = {"role": "assistant", "content": full_text}
            if tool_calls_list:
                assistant_msg["tool_calls"] = tool_calls_list
            full_messages.append(assistant_msg)

        else:
            response = chat(full_messages, model=model, tools=TOOLS, stream=False)
            session.usage.add(response.usage)
            msg = response.choices[0].message
            finish_reason = response.choices[0].finish_reason

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
            # 非流式：将 tool_calls 统一为 list[dict] 格式供下方复用
            if msg.tool_calls:
                tool_calls_list = [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in msg.tool_calls
                ]
            else:
                tool_calls_list = []
            full_text = msg.content or ""

        # ── 处理工具调用 ───────────────────────────────────
        if finish_reason == "tool_calls" and tool_calls_list:
            for tc in tool_calls_list:
                name = tc["function"]["name"]
                try:
                    arguments = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    arguments = {}

                if on_tool_call:
                    on_tool_call(name, arguments)

                # 安全检查
                if confirm_fn is not None:
                    risk = assess_tool_call(name, arguments, session.perm_cache)
                    if risk.is_risky:
                        allowed = confirm_fn(name, risk.reason, arguments)
                        if allowed:
                            target = arguments.get("command") or arguments.get("path", "")
                            session.perm_cache.approve(name, target)
                        else:
                            result = "[已跳过：用户拒绝执行 " + name + "（" + risk.reason + "）]"
                            if on_tool_result:
                                on_tool_result(name, result)
                            session.add_tool_result(tc["id"], result)
                            full_messages.append({
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": result,
                            })
                            continue

                result = run_tool(name, arguments)

                if on_tool_result:
                    on_tool_result(name, result)

                session.add_tool_result(tc["id"], result)
                full_messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })
            continue  # 把工具结果送回模型

        # ── 最终文本回复 ───────────────────────────────────
        final_text = full_text
        if on_text:
            on_text(final_text)
        break

    return final_text
