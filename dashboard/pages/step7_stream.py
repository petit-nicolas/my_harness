"""
Step 7 — 流式输出页
可视化体验：流式 vs 非流式 + chunk 累加原理 + token 统计
"""
import sys
import pathlib
import time
import json

ROOT = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from src.agent import AgentSession, run_agent

# ── 页面初始化 ─────────────────────────────────────────────
st.title("Step 7 · 流式输出")
st.caption("能力阶段 — stream=True 让回复逐字呈现，大幅改善交互体验")

with st.expander("学习目标", expanded=False):
    st.markdown("""
- 理解流式与非流式 API 的本质区别（SSE vs 完整 JSON）
- 掌握 `tool_calls` delta 累加原理（分片 → 组装完整参数）
- 观察流式模式对"响应延迟感"的改善
- 了解 `on_text_chunk` 回调如何实现逐字显示
""")

tab1, tab2, tab3 = st.tabs(["⚡ 流式对话体验", "🔬 chunk 累加原理", "📊 流式 vs 非流式"])

# ── Tab 1：流式对话体验 ────────────────────────────────────
with tab1:
    st.subheader("流式对话体验")
    st.info("每个 token 到达时立即更新，感受与非流式的延迟差异")

    if "stream_session" not in st.session_state:
        st.session_state.stream_session = AgentSession()
    if "stream_history" not in st.session_state:
        st.session_state.stream_history = []

    # 展示历史消息
    for msg in st.session_state.stream_history:
        role = msg["role"]
        if role == "user":
            with st.chat_message("user"):
                st.markdown(msg["content"])
        elif role == "assistant":
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(msg["content"])
        elif role == "tool_call":
            with st.chat_message("assistant", avatar="🔧"):
                st.code(msg["content"], language="text")
        elif role == "tool_result":
            with st.chat_message("assistant", avatar="📤"):
                st.caption(msg["content"][:200])

    user_input = st.chat_input("输入消息体验流式输出...")

    if user_input:
        st.session_state.stream_history.append({"role": "user", "content": user_input})

        with st.chat_message("user"):
            st.markdown(user_input)

        # 流式输出容器
        with st.chat_message("assistant", avatar="🤖"):
            output_placeholder = st.empty()
            chunk_box = [""]

            def on_chunk(c: str) -> None:
                chunk_box[0] += c
                output_placeholder.markdown(chunk_box[0] + "▌")

            tool_events = []

            def on_tool_call(name: str, args: dict) -> None:
                tool_events.append({"role": "tool_call",
                                    "content": f"⚙ {name}({json.dumps(args, ensure_ascii=False)[:80]})"})

            def on_tool_result(name: str, result: str) -> None:
                tool_events.append({"role": "tool_result",
                                    "content": f"↳ {result[:150]}"})

            t0 = time.time()
            try:
                run_agent(
                    session=st.session_state.stream_session,
                    user_input=user_input,
                    stream=True,
                    on_text_chunk=on_chunk,
                    on_tool_call=on_tool_call,
                    on_tool_result=on_tool_result,
                )
                elapsed = time.time() - t0
                final_text = chunk_box[0]
                output_placeholder.markdown(final_text)
                st.caption(f"⏱ {elapsed:.2f}s · 流式传输")
            except Exception as e:
                final_text = f"错误：{e}"
                output_placeholder.error(final_text)

        # 插入工具事件
        for ev in tool_events:
            st.session_state.stream_history.append(ev)

        st.session_state.stream_history.append({"role": "assistant", "content": chunk_box[0]})
        st.rerun()

    col_reset, _ = st.columns([1, 4])
    with col_reset:
        if st.button("清空对话", use_container_width=True):
            st.session_state.stream_session = AgentSession()
            st.session_state.stream_history = []
            st.rerun()

# ── Tab 2：chunk 累加原理 ──────────────────────────────────
with tab2:
    st.subheader("tool_calls delta 累加原理")
    st.markdown("""
流式模式下，一次工具调用会被拆成多个 chunk 分批发送。
每个 chunk 只携带**增量**内容（类似于打字机逐字输入参数）。
""")

    st.markdown("**模拟：read_file 调用被拆成 4 个 chunk**")

    chunks_demo = [
        {"chunk": 1, "delta.tool_calls[0]": '{"index":0, "id":"call_abc", "function":{"name":"read_file","arguments":""}}',
         "累加后arguments": ""},
        {"chunk": 2, "delta.tool_calls[0]": '{"index":0, "function":{"arguments":\'{"pa\'}}',
         "累加后arguments": '{"pa'},
        {"chunk": 3, "delta.tool_calls[0]": '{"index":0, "function":{"arguments":\'th":"src/\'}  }',
         "累加后arguments": '{"path":"src/'},
        {"chunk": 4, "delta.tool_calls[0]": '{"index":0, "function":{"arguments":\'tools.py"}\'}}',
         "累加后arguments": '{"path":"src/tools.py"}'},
    ]
    st.table(chunks_demo)

    st.markdown("**`_collect_stream()` 的累加逻辑（核心代码）**")
    st.code("""\
tc_map: dict[int, dict] = {}   # index → 工具调用字典

for chunk in stream:
    for tc_chunk in (delta.tool_calls or []):
        idx = tc_chunk.index
        if idx not in tc_map:
            tc_map[idx] = {"id": tc_chunk.id, "function": {
                "name": tc_chunk.function.name or "",
                "arguments": tc_chunk.function.arguments or "",
            }}
        else:
            # 累加 arguments 字符串（JSON 被切成多段）
            tc_map[idx]["function"]["arguments"] += tc_chunk.function.arguments or ""

# 按 index 排序，得到完整的 tool_calls 列表
tool_calls_list = [tc_map[i] for i in sorted(tc_map)]
""", language="python")

    st.success("累加完成后，`arguments` 是合法 JSON，可直接 `json.loads()` 解析参数")

# ── Tab 3：流式 vs 非流式 对比 ────────────────────────────
with tab3:
    st.subheader("流式 vs 非流式 — 核心差异")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**非流式（stream=False）**")
        st.code("""\
response = client.chat.completions.create(
    model="qwen-plus",
    messages=[...],
    stream=False,          # 等待完整响应
)
# ⚠ 用户等待 N 秒后突然看到完整文本
text = response.choices[0].message.content
""", language="python")
        st.error("体验：等待 → 一次性出现全文\n时延感：强（尤其长回复时）")

    with col_b:
        st.markdown("**流式（stream=True）**")
        st.code("""\
stream = client.chat.completions.create(
    model="qwen-plus",
    messages=[...],
    stream=True,           # SSE 流式传输
)
for chunk in stream:
    delta = chunk.choices[0].delta
    if delta.content:
        print(delta.content, end="", flush=True)
# ✓ 用户看到文字一边"打印"一边出现
""", language="python")
        st.success("体验：逐字显示，感觉更快\n实际网络传输时间相同，但首字节更早")

    st.divider()
    st.markdown("#### 为什么流式感觉更快？")
    st.markdown("""
| 指标 | 非流式 | 流式 |
|------|--------|------|
| 首字节延迟（TTFB） | 需生成完整响应 | 生成第一个 token 就返回 |
| 总传输时间 | 相同 | 相同 |
| 用户感知延迟 | 高（等待全文） | 低（立即看到内容） |
| 实现复杂度 | 简单 | 需 chunk 累加逻辑 |

> 流式的本质是把**等待时间**变成了**阅读时间**，总时长不变，但体验完全不同。
""")
