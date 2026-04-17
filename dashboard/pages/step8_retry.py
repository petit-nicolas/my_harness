"""
Step 8 — 错误重试 + 上下文压缩页
可视化体验：退避策略模拟 + 压缩前后对比 + token 阈值说明
"""
import sys
import pathlib
import time

ROOT = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from src.retry import _backoff_seconds, retry_error_type
from src.agent import estimate_tokens, compact_context, should_compact, AgentSession, _MODEL_MAX_TOKENS, _COMPACT_THRESHOLD

# ── 页面初始化 ─────────────────────────────────────────────
st.title("Step 8 · 错误重试 + 上下文压缩")
st.caption("能力阶段 — 让 Agent 面对 API 抖动时自动恢复，长对话时自动瘦身")

with st.expander("学习目标", expanded=False):
    st.markdown("""
- 理解指数退避的原理：为什么不应该立即重试？
- 掌握 `with_retry()` 的实现：可重试错误识别 + 抖动计算
- 理解上下文窗口限制和"遗忘"问题
- 观察 `compact_context()` 如何用摘要替代早期消息
""")

tab1, tab2, tab3 = st.tabs(["⏱ 重试策略", "📦 上下文压缩", "🔍 代码原理"])

# ── Tab 1：重试策略 ────────────────────────────────────────
with tab1:
    st.subheader("指数退避重试策略模拟")

    col_l, col_r = st.columns([1, 1])
    with col_l:
        max_attempts = st.slider("最大重试次数", 2, 5, 3)
        base_delay   = st.slider("基础等待时间（秒）", 0.5, 3.0, 1.0, 0.5)
        error_type   = st.selectbox("错误类型", ["429 速率限制", "5xx 服务器错误", "网络超时"])

    with col_r:
        st.markdown("**各次尝试等待时间**")
        rate_limited = error_type == "429 速率限制"
        data = []
        total = 0.0
        for attempt in range(max_attempts - 1):
            wait = _backoff_seconds(attempt, base_delay, rate_limited)
            # 去掉随机部分，只展示确定值
            det_wait = base_delay * (2 ** attempt) * (2.0 if rate_limited else 1.0)
            total += det_wait
            data.append({
                "尝试次数": f"第 {attempt + 1} 次失败后",
                "等待时间（确定部分）": f"{det_wait:.1f}s",
                "随机抖动": "0 ~ 0.5s",
            })
        st.table(data)
        st.caption(f"总等待（不含抖动）：{total:.1f}s  ·  最大单次等待上限：60s")

    st.divider()
    st.markdown("#### 为什么需要指数退避？")
    st.markdown("""
| 策略 | 问题 |
|------|------|
| 立即重试 | 服务器已过载，重试只会加重负担（惊群效应） |
| 固定间隔重试 | 多个客户端同步重试，制造周期性冲击波 |
| 指数退避 + 抖动 | 等待时间递增，随机错开重试时刻 |
""")

    st.markdown("#### 哪些错误值得重试？")
    col_a, col_b = st.columns(2)
    with col_a:
        st.success("""**可重试（临时性错误）**
- 429 Rate Limit（服务器繁忙）
- 500/502/503 服务器错误
- 网络连接超时""")
    with col_b:
        st.error("""**不重试（永久性错误）**
- 401 Unauthorized（API Key 无效）
- 403 Forbidden（无权限）
- 400 Bad Request（请求格式错误）""")

# ── Tab 2：上下文压缩 ──────────────────────────────────────
with tab2:
    st.subheader("上下文压缩 — 应对 Token 限制")

    # Token 用量可视化
    st.markdown("#### Token 窗口状态")
    threshold_tokens = int(_MODEL_MAX_TOKENS * _COMPACT_THRESHOLD)
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("模型上下文上限", f"{_MODEL_MAX_TOKENS:,} tokens")
    col_m2.metric("压缩触发阈值", f"{threshold_tokens:,} tokens ({int(_COMPACT_THRESHOLD*100)}%)")
    col_m3.metric("安全余量", f"{_MODEL_MAX_TOKENS - threshold_tokens:,} tokens")

    st.divider()
    st.markdown("#### 压缩前后对比模拟")

    # 构造模拟的消息历史
    if "sim_session" not in st.session_state:
        st.session_state.sim_session = None

    n_messages = st.slider("模拟历史消息条数", 4, 20, 10)
    if st.button("生成模拟消息历史", use_container_width=True):
        sim = AgentSession()
        for i in range(n_messages):
            if i % 3 == 0:
                sim.messages.append({"role": "user", "content": f"请帮我修改第 {i+1} 个功能，在 src/feature_{i}.py 中实现 process() 函数"})
            elif i % 3 == 1:
                sim.messages.append({"role": "assistant", "content": f"好的，我来读取并修改 src/feature_{i}.py 的 process() 函数实现"})
            else:
                sim.messages.append({"role": "tool", "content": f"已读取文件 src/feature_{i}.py，内容：def process(): return {i}"})
        st.session_state.sim_session = sim

    sim = st.session_state.sim_session
    if sim:
        est = estimate_tokens(sim.messages)
        col_p, col_a2 = st.columns(2)
        with col_p:
            st.markdown("**压缩前**")
            st.metric("消息条数", len(sim.messages))
            st.metric("估算 Token 数", est)
            for i, m in enumerate(sim.messages):
                role_icon = {"user": "👤", "assistant": "🤖", "tool": "🔧"}.get(m["role"], "?")
                content_preview = (m.get("content") or "")[:60]
                st.caption(f"{role_icon} [{i+1}] {content_preview}...")

        with col_a2:
            st.markdown("**压缩后**")
            if st.button("执行 compact_context（调用 LLM）", type="primary"):
                with st.spinner("调用 LLM 生成摘要..."):
                    import copy
                    sim_copy = AgentSession()
                    sim_copy.messages = copy.deepcopy(sim.messages)
                    summary = compact_context(sim_copy, keep_recent=4)
                    st.session_state.compact_result = sim_copy
                    st.session_state.compact_summary = summary

            if "compact_result" in st.session_state:
                cr = st.session_state.compact_result
                est_after = estimate_tokens(cr.messages)
                st.metric("消息条数", len(cr.messages),
                          delta=len(cr.messages) - len(sim.messages))
                st.metric("估算 Token 数", est_after, delta=est_after - est)
                for i, m in enumerate(cr.messages):
                    role_icon = {"user": "👤", "assistant": "🤖", "tool": "🔧"}.get(m["role"], "?")
                    content_preview = (m.get("content") or "")[:60]
                    st.caption(f"{role_icon} [{i+1}] {content_preview}...")

    st.divider()
    st.markdown("#### CLI 手动触发")
    st.code("""\
# 在 REPL 中任意时刻输入：
> /compact

# 输出示例：
#   当前消息数：18  估算 token：8,240
#   正在生成摘要...
#   压缩完成，剩余消息数：7
#   摘要预览：本次对话中，用户请求修改了...
""", language="text")

# ── Tab 3：代码原理 ────────────────────────────────────────
with tab3:
    st.subheader("核心代码解析")

    st.markdown("#### with_retry() — 通用重试包装")
    st.code("""\
def with_retry(fn, max_attempts=3, base_delay=1.0, on_retry=None):
    last_exc = None
    for attempt in range(max_attempts):
        try:
            return fn()              # 调用实际函数
        except Exception as exc:
            if not _is_retryable(exc):
                raise                # 不可重试 → 直接抛出
            last_exc = exc
            if attempt == max_attempts - 1:
                break                # 最后一次，不再等待
            wait = _backoff_seconds(attempt, base_delay, _is_rate_limit(exc))
            if on_retry:
                on_retry(attempt + 1, exc, wait)
            time.sleep(wait)
    raise last_exc

# 在 client.py 中使用：
return with_retry(lambda: client.chat.completions.create(**kwargs))
""", language="python")

    st.markdown("#### compact_context() — 上下文压缩流程")
    st.code("""\
def compact_context(session, model, keep_recent=6):
    msgs = session.messages
    to_compress = msgs[:-keep_recent]   # 早期消息
    recent = msgs[-keep_recent:]        # 保留最近 N 条

    # 调用 LLM 生成摘要
    resp = chat([
        {"role": "system", "content": "你是摘要助手..."},
        {"role": "user",   "content": f"压缩这段历史：{history_text}"},
    ], stream=False)
    summary = resp.choices[0].message.content

    # 重组：摘要 + 最近消息
    session.messages = [
        {"role": "assistant", "content": "[早期对话摘要]\\n" + summary},
        *recent,
    ]
    return summary

# 自动触发：在 run_agent 每轮循环开始时检查
if should_compact(session):
    compact_context(session, model=model)
""", language="python")

    st.markdown("#### should_compact() — 触发判断")
    st.code("""\
def should_compact(session):
    actual = session.usage.total        # API 返回的真实 token 数
    if actual > 0:
        return actual >= 32_000 * 0.75  # 超过 75% 上限

    # 无 usage 数据时用字符数估算
    return estimate_tokens(session.messages) >= 32_000 * 0.75
""", language="python")
