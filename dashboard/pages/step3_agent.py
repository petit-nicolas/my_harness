"""
Step 3 — Agent 循环页
可视化体验：实时对话 + 工具调用过程展示 + 消息历史
"""
import sys
import pathlib
import json
import time

ROOT = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from src.agent import AgentSession, run_agent

# ── 页面初始化 ─────────────────────────────────────────────
st.title("Step 3 · Agent 主循环")
st.caption("骨架阶段 — 理解 while True 循环如何协调 API 调用与工具执行")

with st.expander("学习目标", expanded=False):
    st.markdown("""
1. **循环结构**：`while True` 驱动，`tool_calls` 决定继续还是结束
2. **消息历史**：每轮对话追加 user / assistant / tool 三种角色的消息
3. **工具闭环**：模型触发工具 → 执行 → 结果追回历史 → 模型继续推理
4. **状态容器**：`AgentSession` 持有消息历史和 Token 累计，支持多轮对话
""")

st.divider()

# ── 架构图 ────────────────────────────────────────────────
with st.expander("Agent 循环架构图", expanded=True):
    st.code("""
构建消息（system + history + user）
          ↓
      调用 API
          ↓
    ┌─────────────────────────────────────────┐
    │           while True                    │
    │                                         │
    │  finish_reason == "tool_calls"          │
    │    → 执行工具 → 追加 tool 消息 → continue │
    │                                         │
    │  finish_reason == "stop"                │
    │    → 输出文本 → break                   │
    └─────────────────────────────────────────┘
""", language="text")

st.divider()

# ── 会话状态初始化 ─────────────────────────────────────────
if "agent_session" not in st.session_state:
    st.session_state.agent_session = AgentSession(cwd=str(ROOT))
if "chat_log" not in st.session_state:
    st.session_state.chat_log = []  # 展示用的日志（含工具调用详情）

session: AgentSession = st.session_state.agent_session

# ── 侧边栏控制 ────────────────────────────────────────────
with st.sidebar:
    st.subheader("会话控制")
    if st.button("清空对话", use_container_width=True):
        session.messages.clear()
        st.session_state.chat_log = []
        st.rerun()

    st.divider()
    st.caption("Token 用量")
    u = session.usage
    st.metric("Prompt", u.prompt_tokens)
    st.metric("Completion", u.completion_tokens)
    st.metric("Total", u.total)

    st.divider()
    st.caption("消息历史条数")
    st.metric("Messages", len(session.messages))

# ── 对话历史展示 ──────────────────────────────────────────
st.subheader("对话区")

for entry in st.session_state.chat_log:
    role = entry["role"]
    if role == "user":
        with st.chat_message("user"):
            st.markdown(entry["content"])
    elif role == "assistant":
        with st.chat_message("assistant"):
            st.markdown(entry["content"])
    elif role == "tool_call":
        with st.chat_message("assistant", avatar="🔧"):
            st.markdown(
                f"**调用工具**：`{entry['name']}`  \n"
                f"**参数**：`{json.dumps(entry['args'], ensure_ascii=False)}`"
            )
    elif role == "tool_result":
        with st.chat_message("assistant", avatar="📤"):
            preview = entry["content"][:300]
            suffix = "..." if len(entry["content"]) > 300 else ""
            st.markdown(f"**结果**：\n```\n{preview}{suffix}\n```")

# ── 输入框 ────────────────────────────────────────────────
user_input = st.chat_input("输入消息，Agent 会自动调用工具来完成任务...")

if user_input:
    # 立刻显示用户消息
    st.session_state.chat_log.append({"role": "user", "content": user_input})

    # 收集本轮工具调用和结果用于展示
    round_tool_calls = []
    round_tool_results = []

    def on_tool_call(name: str, args: dict) -> None:
        round_tool_calls.append({"name": name, "args": args})

    def on_tool_result(name: str, result: str) -> None:
        round_tool_results.append({"name": name, "content": result})

    reply_box = [""]   # 用列表存储，回调可直接修改元素，无需 nonlocal

    def on_text(text: str) -> None:
        reply_box[0] = text

    with st.spinner("Agent 运行中..."):
        t0 = time.time()
        try:
            run_agent(
                session=session,
                user_input=user_input,
                stream=False,
                on_text=on_text,
                on_tool_call=on_tool_call,
                on_tool_result=on_tool_result,
            )
        except Exception as e:
            reply_box[0] = f"错误：{e}"
        elapsed = time.time() - t0

    final_reply = reply_box[0]

    # 把工具调用/结果插入日志
    for tc, tr in zip(round_tool_calls, round_tool_results):
        st.session_state.chat_log.append({"role": "tool_call", **tc})
        st.session_state.chat_log.append({"role": "tool_result", **tr})

    # 追加 agent 最终回复
    st.session_state.chat_log.append({
        "role": "assistant",
        "content": final_reply + f"\n\n*({elapsed:.1f}s)*",
    })

    st.rerun()

# ── 核心代码 ──────────────────────────────────────────────
st.divider()
with st.expander("核心代码：src/agent.py — run_agent()"):
    agent_path = ROOT / "src" / "agent.py"
    if agent_path.exists():
        st.code(agent_path.read_text(encoding="utf-8"), language="python")
