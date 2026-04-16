"""
Step 1 — API 对接页
可视化体验：连通性测试 + Tool Calling 演示
"""
import sys
import json
import time
import streamlit as st

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

import pathlib

ROOT = pathlib.Path(__file__).parent.parent.parent

st.title("Step 1 · 千问 API 对接")
st.caption("骨架阶段 — 验证 API 连通性与 Tool Calling 能力")

# ── 学习目标 ──────────────────────────────────────────────
with st.expander("学习目标", expanded=True):
    st.markdown("""
1. **API 封装**：用 OpenAI SDK 对接千问的 OpenAI 兼容 endpoint
2. **连通性验证**：普通对话 + 流式输出两条路径都能正常工作
3. **Tool Calling**：模型能主动触发工具，工具结果能正确回传继续对话
""")

# ── 核心代码展示 ───────────────────────────────────────────
with st.expander("核心代码：src/client.py"):
    client_path = ROOT / "src" / "client.py"
    if client_path.exists():
        st.code(client_path.read_text(encoding="utf-8"), language="python")

st.divider()

# ── Tab 1：连通性测试 ──────────────────────────────────────
tab1, tab2 = st.tabs(["连通性测试", "Tool Calling 演示"])

with tab1:
    st.subheader("发送自定义消息")

    user_input = st.text_input(
        "消息内容",
        value="你好，请用一句话介绍你自己。",
        key="chat_input",
    )
    use_stream = st.checkbox("启用流式输出", value=False)

    if st.button("发送", key="btn_chat", type="primary"):
        if not user_input.strip():
            st.warning("请输入消息内容")
        else:
            try:
                from src.client import chat, DEFAULT_MODEL

                messages = [{"role": "user", "content": user_input}]

                with st.spinner("请求中..."):
                    t0 = time.time()

                    if use_stream:
                        placeholder = st.empty()
                        stream = chat(messages, stream=True)
                        full_text = ""
                        for chunk in stream:
                            delta = chunk.choices[0].delta.content
                            if delta:
                                full_text += delta
                                placeholder.markdown(f"**模型回复（流式）：**\n\n{full_text}▌")
                        placeholder.markdown(f"**模型回复（流式）：**\n\n{full_text}")
                        elapsed = time.time() - t0
                        st.success(f"流式接收完成，{elapsed:.2f}s，共 {len(full_text)} 字")
                    else:
                        response = chat(messages)
                        elapsed = time.time() - t0
                        reply = response.choices[0].message.content
                        usage = response.usage

                        st.markdown(f"**模型回复：**\n\n{reply}")
                        col1, col2, col3 = st.columns(3)
                        col1.metric("耗时", f"{elapsed:.2f}s")
                        col2.metric("Prompt Tokens", usage.prompt_tokens)
                        col3.metric("Completion Tokens", usage.completion_tokens)

            except Exception as e:
                st.error(f"请求失败：{e}")

# ── Tab 2：Tool Calling 演示 ───────────────────────────────
with tab2:
    st.subheader("Tool Calling 完整流程演示")
    st.markdown("模拟 Agent 一轮完整工具调用：**触发 → 执行 → 回传 → 最终回答**")

    DEMO_TOOLS = [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "读取指定路径的文件内容",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件路径"}
                    },
                    "required": ["path"],
                },
            },
        }
    ]

    demo_prompt = st.text_input(
        "用户指令",
        value="帮我读取 README.md 文件的内容",
        key="tool_input",
    )

    fake_file_content = st.text_area(
        "模拟工具返回值（假装文件内容）",
        value="# Harness\n\n极简 Coding Agent 教学框架，基于阿里千问 API。",
        height=80,
        key="tool_result",
    )

    if st.button("运行工具调用流程", key="btn_tool", type="primary"):
        try:
            from src.client import chat

            steps = st.container()

            with steps:
                # 第 1 步：触发
                with st.spinner("第 1 步：发送请求，等待模型触发工具..."):
                    messages = [{"role": "user", "content": demo_prompt}]
                    resp1 = chat(messages, tools=DEMO_TOOLS)
                    msg = resp1.choices[0].message

                if not msg.tool_calls:
                    st.warning("模型没有触发工具调用，请换一个需要读取文件的问题。")
                else:
                    tc = msg.tool_calls[0]
                    args = json.loads(tc.function.arguments)

                    st.success(f"**第 1 步完成** — 模型触发工具：`{tc.function.name}`")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**tool_calls 原始结构：**")
                        st.json({
                            "id": tc.id,
                            "function": {
                                "name": tc.function.name,
                                "arguments": args,
                            },
                            "finish_reason": resp1.choices[0].finish_reason,
                        })

                    # 第 2 步：追加工具结果
                    messages.append(msg)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": fake_file_content,
                    })

                    with col2:
                        st.markdown("**追加到历史的工具结果：**")
                        st.json({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": fake_file_content[:80] + "...",
                        })

                    # 第 3 步：最终回答
                    with st.spinner("第 3 步：模型根据工具结果生成最终回答..."):
                        resp2 = chat(messages, tools=DEMO_TOOLS)
                        final = resp2.choices[0].message.content

                    st.success("**第 3 步完成** — 模型最终回答：")
                    st.markdown(f"> {final}")

        except Exception as e:
            st.error(f"演示失败：{e}")
